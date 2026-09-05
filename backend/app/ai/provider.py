from app.ai.prompts import SYSTEM_PROMPT, build_messages
from app.ai.schema import DECISION_SCHEMA, AiDecision, validate
from app.core.config import settings
from app.core.constants import (
    EMAIL,
    HUMAN_ESCALATION,
    IN_APP,
    PAYMENT_LINK,
    PAYMENT_RETRY,
    SMS,
    VOICE_AI,
)
from app.core.errors import ProviderUnavailable
from app.core.money import expected_recovery

DIAGNOSIS = {
    "TEMPORARY_BANK_TIMEOUT": "Temporary payment failure at the issuing bank",
    "GATEWAY_FAILURE": "Payment gateway rejected the charge before reaching the bank",
    "AUTHENTICATION_FAILURE": "Customer did not complete additional authentication",
    "RECURRING_MANDATE_FAILURE": "Recurring mandate could not be charged on renewal",
    "INSUFFICIENT_FUNDS": "Account balance was short at the time of the charge",
    "CARD_EXPIRED": "Saved card has expired and needs replacing",
    "CHECKOUT_ABANDONED": "Customer left checkout before authorising the payment",
    "OVERDUE_INVOICE": "Invoice has stayed unpaid past its due date",
}

DELAY_HOURS = {
    "INSUFFICIENT_FUNDS": 24.0,
    "CARD_EXPIRED": 6.0,
    "OVERDUE_INVOICE": 12.0,
    "AUTHENTICATION_FAILURE": 2.0,
    "CHECKOUT_ABANDONED": 1.0,
}

TRANSIENT = {"TEMPORARY_BANK_TIMEOUT", "GATEWAY_FAILURE"}


def delivery_channel(customer: dict, available: list[str]) -> str:
    preferred = customer.get("preferred_channel", EMAIL)
    if preferred in available:
        return preferred
    for channel in (EMAIL, SMS, IN_APP):
        if channel in available:
            return channel
    return IN_APP


def evidence_strength(customer: dict) -> float:
    observed = customer.get("successful_payments", 0) + customer.get("failed_payments", 0)
    return min(1.0, 0.6 + 0.05 * min(observed, 8))


class AiProvider:
    name = "base"

    def decide(self, context: dict) -> AiDecision:
        raise NotImplementedError


class DemoAiProvider(AiProvider):
    name = "demo"

    def decide(self, context: dict) -> AiDecision:
        case = context["case"]
        customer = context["customer"]
        guardrails = context["guardrails"]
        probability = context["ml"]["recovery_probability"]
        failure = case["failure_type"]
        amount = case["amount_at_risk"]
        available = context.get("available_channels", [])
        confidence = round(probability * (0.85 + 0.15 * evidence_strength(customer)), 4)

        blockers = []
        if amount > guardrails["max_automated_amount"]:
            blockers.append(f"amount exceeds the automated recovery limit of Rs {guardrails['max_automated_amount']:.0f}")
        if case["attempt_count"] >= guardrails["max_retry_attempts"]:
            blockers.append(f"{case['attempt_count']} recovery attempts already used")
        if confidence < guardrails["min_ai_confidence"]:
            blockers.append(f"confidence {confidence:.0%} is below the {guardrails['min_ai_confidence']:.0%} automation floor")

        if blockers:
            action, channel = HUMAN_ESCALATION, HUMAN_ESCALATION
            reasoning = "Automated recovery is not appropriate because " + "; ".join(blockers) + "."
        elif failure == "RECURRING_MANDATE_FAILURE" and case["attempt_count"] == 0:
            action, channel = PAYMENT_RETRY, IN_APP
            reasoning = (
                "The mandate failed on its first renewal attempt and the customer has a "
                f"{customer['successful_ratio']:.0%} success record, so a silent retry recovers the "
                "revenue without contacting the customer."
            )
        elif failure == "OVERDUE_INVOICE" and customer["voice_opt_in"] and VOICE_AI in available:
            action, channel = VOICE_AI, VOICE_AI
            reasoning = (
                "The invoice is past due and earlier written reminders were not acted on, so a "
                "short voice conversation is the most effective next step."
            )
        else:
            action = PAYMENT_LINK
            channel = delivery_channel(customer, available)
            reasoning = (
                f"{DIAGNOSIS.get(failure, 'Payment failure')} with a "
                f"{customer['successful_ratio']:.0%} historical success rate and "
                f"{probability:.0%} predicted recovery. A payment link over "
                f"{channel.lower()} lets the customer settle Rs {amount:,.0f} in one step."
            )

        delay = 0.0 if failure in TRANSIENT else DELAY_HOURS.get(failure, 2.0)
        payload = {
            "diagnosis": DIAGNOSIS.get(failure, "Payment failure requiring recovery"),
            "confidence": confidence,
            "recommended_action": action,
            "recommended_channel": channel,
            "expected_recovery": expected_recovery(amount, probability),
            "recommended_delay_hours": delay,
            "reasoning": reasoning,
            "customer_message": self.message(context, action),
        }
        return validate(payload, self.name)

    def message(self, context: dict, action: str) -> str:
        case = context["case"]
        customer = context["customer"]
        subscription = context.get("subscription") or {}
        plan = subscription.get("plan_name", "your subscription")
        amount = f"Rs {case['amount_at_risk']:,.0f}"
        issue = DIAGNOSIS.get(case["failure_type"], "the payment could not be completed")
        if action == HUMAN_ESCALATION:
            return (
                f"Hi {customer['name']}, we could not process the {amount} payment for {plan}. "
                "A member of our team will contact you directly to sort this out."
            )
        if action == PAYMENT_RETRY:
            return (
                f"Hi {customer['name']}, the {amount} renewal for {plan} did not go through because "
                f"{issue.lower()}. We will try the same payment method once more, and there is "
                "nothing you need to do."
            )
        if action == VOICE_AI:
            return (
                f"Hi {customer['name']}, this is Revora calling about the {amount} payment for "
                f"{plan}, which is still outstanding because {issue.lower()}. Would you like a "
                "payment link so you can complete it?"
            )
        return (
            f"Hi {customer['name']}, the {amount} payment for {plan} did not complete because "
            f"{issue.lower()}. You can settle it with the secure payment link below, and your "
            "subscription continues without interruption."
        )


class ClaudeAiProvider(AiProvider):
    name = "claude"

    def __init__(self):
        import anthropic

        self.sdk = anthropic
        self.client = anthropic.Anthropic(api_key=settings.ai_api_key)
        self.model = settings.ai_model

    def decide(self, context: dict) -> AiDecision:
        import json

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=build_messages(context),
                output_config={"format": {"type": "json_schema", "schema": DECISION_SCHEMA}},
            )
        except self.sdk.APIStatusError as exc:
            raise ProviderUnavailable(f"AI provider returned {exc.status_code}") from exc
        except self.sdk.APIConnectionError as exc:
            raise ProviderUnavailable("AI provider is unreachable") from exc
        if response.stop_reason == "refusal":
            raise ProviderUnavailable("AI provider declined the request")
        text = next((block.text for block in response.content if block.type == "text"), "")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderUnavailable("AI provider returned malformed JSON") from exc
        return validate(payload, self.name)


def get_ai_provider() -> AiProvider:
    if not settings.live_ai:
        return DemoAiProvider()
    try:
        return ClaudeAiProvider()
    except Exception:
        return DemoAiProvider()
