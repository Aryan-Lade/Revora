import json

from app.ai.schema import validate
from app.core.config import settings
from app.core.constants import (
    EMAIL, VOICE_AI, PAYMENT_LINK, SMS, HUMAN_ESCALATION,
    PAYMENT_RETRY, IN_APP,
)

DEMO_RECS = {
    "RC-DEMO-RAHUL": {
        "diagnosis": "Temporary bank timeout caused the payment to fail",
        "confidence": 0.87,
        "recommended_action": PAYMENT_LINK,
        "recommended_channel": EMAIL,
        "expected_recovery": 4349.13,
        "recommended_delay_hours": 0,
        "reasoning": "Strong payment history and a transient failure make this highly recoverable via payment link sent by email.",
        "customer_message": "Hi {name}, your ₹{amount} payment for your subscription failed due to a temporary bank issue. Please use the secure link below to complete it — it takes under a minute.",
        "provider": "demo",
    },
    "RC-DEMO-AMIT": {
        "diagnosis": "Insufficient funds with multiple prior failures",
        "confidence": 0.61,
        "recommended_action": HUMAN_ESCALATION,
        "recommended_channel": EMAIL,
        "expected_recovery": 0.0,
        "recommended_delay_hours": 0,
        "reasoning": "High amount, low probability, and 3 previous attempts make automated recovery risky. Human intervention required.",
        "customer_message": "",
        "provider": "demo",
    },
    "RC-DEMO-NEHA": {
        "diagnosis": "Customer has an active promise to pay",
        "confidence": 0.95,
        "recommended_action": PAYMENT_LINK,
        "recommended_channel": EMAIL,
        "expected_recovery": 4999.0,
        "recommended_delay_hours": 24,
        "reasoning": "Customer promised payment tomorrow. Wait for fulfilment before any outreach.",
        "customer_message": "Hi {name}, thank you for letting us know. We have noted your payment commitment and will not contact you until tomorrow.",
        "provider": "demo",
    },
    "RC-DEMO-ROHIT": {
        "diagnosis": "Payment failed at 11:30 PM — outside allowed contact window",
        "confidence": 0.80,
        "recommended_action": EMAIL,
        "recommended_channel": EMAIL,
        "expected_recovery": 3499.30,
        "recommended_delay_hours": 8.5,
        "reasoning": "Quiet hours are in effect. Schedule outreach for 08:00 AM.",
        "customer_message": "Hi {name}, your ₹{amount} payment failed late last night. We will follow up this morning with a recovery link.",
        "provider": "demo",
    },
}


def _default_payload(context: dict, probability: float) -> dict:
    amount = float(context["case"]["amount_at_risk"])
    failure = context["case"]["failure_label"]
    name = context["customer"]["name"]
    confidence = round(probability, 2)

    if amount > settings.max_automated_amount:
        action = HUMAN_ESCALATION
        channel = EMAIL
        reasoning = f"Amount ₹{amount:,.0f} exceeds automated recovery limit. Human review required."
    elif probability >= 0.80:
        action = PAYMENT_LINK
        channel = EMAIL
        reasoning = f"High recovery probability ({probability:.0%}) and {failure.lower()} failure. Payment link via email is optimal."
    elif probability >= 0.60:
        action = EMAIL
        channel = EMAIL
        reasoning = f"Moderate probability ({probability:.0%}). Email recovery recommended."
    else:
        action = HUMAN_ESCALATION
        channel = EMAIL
        reasoning = f"Low confidence ({probability:.0%}) makes automated recovery unsuitable."

    return {
        "diagnosis": f"{failure} caused the payment to fail",
        "confidence": confidence,
        "recommended_action": action,
        "recommended_channel": channel,
        "expected_recovery": round(amount * probability, 2),
        "recommended_delay_hours": 0.0,
        "reasoning": reasoning,
        "customer_message": (
            f"Hi {name}, your ₹{amount:,.0f} payment could not be processed due to {failure.lower()}. "
            f"Please use the link below to complete your payment and keep your subscription active."
        ),
        "provider": "demo",
    }


def _call_anthropic(context: dict, probability: float) -> dict:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ai_api_key)

        case = context["case"]
        customer = context["customer"]
        sub = context.get("subscription") or {}
        contact = context.get("contact_history", {})
        promise = context.get("promise_to_pay")

        system_prompt = (
            "You are an AI revenue recovery assistant. Analyse the recovery context and return a "
            "structured JSON recommendation. "
            "Allowed actions: PAYMENT_RETRY, PAYMENT_LINK, EMAIL, VOICE_AI, SMS, IN_APP, HUMAN_ESCALATION. "
            "Return ONLY valid JSON with these keys: "
            "diagnosis, confidence (0-1), recommended_action, recommended_channel, "
            "expected_recovery, recommended_delay_hours, reasoning, customer_message."
        )
        user_prompt = (
            f"Recovery context:\n"
            f"Customer: {customer['name']} | LTV: ₹{customer['lifetime_value']:,.0f} | "
            f"Success ratio: {customer['successful_ratio']:.1%}\n"
            f"Amount: ₹{case['amount_at_risk']:,.0f} | Failure: {case['failure_label']}\n"
            f"ML Recovery probability: {probability:.1%}\n"
            f"Attempts so far: {case['attempt_count']}\n"
            f"Hours since failure: {case['hours_since_failure']:.1f}\n"
            f"Active promise to pay: {'Yes' if promise else 'No'}\n"
            f"Contacts in window: {contact.get('contacts_in_window', 0)}\n"
            f"Subscription: {sub.get('plan_name', 'unknown')}\n"
            "Provide your structured recovery recommendation as JSON."
        )

        message = client.messages.create(
            model=settings.ai_model,
            max_tokens=512,
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt,
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        payload = json.loads(raw)
        payload["provider"] = "anthropic"
        return payload
    except Exception:
        fallback = _default_payload(context, probability)
        fallback["provider"] = "anthropic_fallback"
        return fallback


class AIProvider:
    def get_recovery_recommendation(self, context: dict, ml_probability: float):
        ref = context["case"]["reference"]

        if settings.demo_mode:
            payload = DEMO_RECS.get(ref)
            if payload is None:
                payload = _default_payload(context, ml_probability)
            else:
                payload = dict(payload)
                name = context["customer"]["name"]
                amount = float(context["case"]["amount_at_risk"])
                payload["customer_message"] = payload["customer_message"].format(
                    name=name, amount=f"{amount:,.0f}"
                )
            return validate(payload, payload["provider"])

        if settings.live_ai:
            payload = _call_anthropic(context, ml_probability)
            return validate(payload, payload["provider"])

        payload = _default_payload(context, ml_probability)
        return validate(payload, payload["provider"])


ai_provider = AIProvider()
