from dataclasses import dataclass

from app.channels.selector import ChannelOption
from app.core.constants import (
    CONTACT_CHANNELS,
    HUMAN_ESCALATION,
    IN_APP,
    PAYMENT_LINK,
    PAYMENT_RETRY,
    VOICE_AI,
)

RETRYABLE_FAILURES = {
    "TEMPORARY_BANK_TIMEOUT",
    "GATEWAY_FAILURE",
    "RECURRING_MANDATE_FAILURE",
    "INSUFFICIENT_FUNDS",
}
TRANSIENT_FAILURES = {"TEMPORARY_BANK_TIMEOUT", "GATEWAY_FAILURE"}
CONTACT_ACTIONS = {PAYMENT_LINK, *CONTACT_CHANNELS}
SOURCE_AI = "ai_recommendation"
SOURCE_DOWNGRADE = "downgraded"
SOURCE_ESCALATION = "escalated"


@dataclass
class Strategy:
    action: str
    channel: str
    delay_hours: float
    message: str
    confidence: float
    reason: str
    source: str

    @property
    def silent(self) -> bool:
        return self.action == PAYMENT_RETRY

    @property
    def needs_link(self) -> bool:
        return self.action == PAYMENT_LINK

    @property
    def voice(self) -> bool:
        return self.action == VOICE_AI or self.channel == VOICE_AI

    def as_dict(self) -> dict:
        return {
            "action": self.action,
            "channel": self.channel,
            "delay_hours": self.delay_hours,
            "confidence": self.confidence,
            "reason": self.reason,
            "source": self.source,
        }


def retry_allowed(context: dict) -> bool:
    case = context["case"]
    guardrails = context["guardrails"]
    return (
        case["failure_type"] in RETRYABLE_FAILURES
        and case["attempt_count"] < guardrails["max_retry_attempts"]
        and case["amount_at_risk"] <= guardrails["max_automated_amount"]
        and not context["payment"]["settled"]
    )


def delay_for(context: dict, requested: float) -> float:
    if context["case"]["failure_type"] in TRANSIENT_FAILURES:
        return 0.0
    return round(max(requested, 0.0), 2)


def plan(context: dict, decision, options: list[ChannelOption]) -> Strategy:
    eligible = [option for option in options if option.eligible]
    action = decision.recommended_action
    channel = decision.recommended_channel
    source = SOURCE_AI
    reason = decision.reasoning

    if action == PAYMENT_RETRY and not retry_allowed(context):
        action = PAYMENT_LINK
        source = SOURCE_DOWNGRADE
        reason = "Retry is not available for this failure, so the customer is sent a payment link instead."

    if action in CONTACT_ACTIONS:
        allowed = {option.channel for option in eligible}
        if action in CONTACT_CHANNELS and action in allowed:
            channel = action
        elif channel not in allowed:
            if not eligible:
                return Strategy(
                    action=HUMAN_ESCALATION,
                    channel=HUMAN_ESCALATION,
                    delay_hours=0.0,
                    message=decision.customer_message,
                    confidence=decision.confidence,
                    reason="No contact channel is available under the current policy, so the case goes to a human.",
                    source=SOURCE_ESCALATION,
                )
            channel = eligible[0].channel
            source = SOURCE_DOWNGRADE
            reason = f"{decision.recommended_channel} is not available, so {channel} carries the message."
        if action in CONTACT_CHANNELS:
            action = channel

    if action == PAYMENT_RETRY:
        channel = IN_APP

    return Strategy(
        action=action,
        channel=channel,
        delay_hours=delay_for(context, decision.recommended_delay_hours),
        message=decision.customer_message,
        confidence=decision.confidence,
        reason=reason,
        source=source,
    )
