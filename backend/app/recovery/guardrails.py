from dataclasses import dataclass, field

from app.core.checks import Check
from app.core.config import settings
from app.core.constants import HUMAN_ESCALATION, PAYMENT_LINK, PAYMENT_RETRY


@dataclass
class GuardrailResult:
    allowed: bool
    action: str
    reason: str
    blocked_by: str | None = None
    checks: list[Check] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "action": self.action,
            "reason": self.reason,
            "blocked_by": self.blocked_by,
            "checks": [check.as_dict() for check in self.checks],
        }


FINANCIAL_ACTIONS = {PAYMENT_RETRY, PAYMENT_LINK}


class GuardrailEngine:
    def __init__(self, config=settings):
        self.config = config

    def evaluate(self, context: dict, action: str) -> GuardrailResult:
        case = context["case"]
        customer = context["customer"]
        payment = context["payment"]
        confidence = context.get("ai", {}).get("confidence", 0.0)
        amount = case["amount_at_risk"]
        checks = [
            Check(
                "retry_limit",
                "Retry Limit",
                case["attempt_count"] < self.config.max_retry_attempts,
                f"{case['attempt_count']} of {self.config.max_retry_attempts} attempts used",
            ),
            Check(
                "amount_threshold",
                "Amount Threshold",
                amount <= self.config.max_automated_amount,
                f"Rs {amount:,.0f} against a Rs {self.config.max_automated_amount:,.0f} automated limit",
            ),
            Check(
                "ai_confidence",
                "AI Confidence",
                confidence >= self.config.min_ai_confidence,
                f"{confidence:.0%} against a {self.config.min_ai_confidence:.0%} floor",
            ),
            Check(
                "recovery_window",
                "Recovery Window",
                case["hours_since_failure"] <= self.config.recovery_window_hours,
                f"{case['hours_since_failure']:.1f}h of a {self.config.recovery_window_hours}h window",
            ),
            Check(
                "duplicate_action",
                "Duplicate Check",
                not context.get("pending_action_exists", False),
                "No identical action is already in flight",
            ),
            Check(
                "payment_open",
                "Payment Not Settled",
                not payment["settled"],
                f"Payment is {payment['status']}",
            ),
            Check(
                "case_open",
                "Case Not Resolved",
                not case["resolved"],
                f"Case is {case['status']}",
            ),
            Check(
                "customer_consent",
                "Customer Consent",
                not customer["opted_out"],
                "Customer has not opted out of recovery contact",
            ),
        ]
        if action == HUMAN_ESCALATION:
            blocking = [check for check in checks if check.name in {"case_open"} and not check.passed]
        elif action in FINANCIAL_ACTIONS:
            blocking = [check for check in checks if not check.passed]
        else:
            exempt = {"retry_limit", "amount_threshold"}
            blocking = [check for check in checks if not check.passed and check.name not in exempt]
        if blocking:
            return GuardrailResult(
                allowed=False,
                action=action,
                reason="; ".join(f"{check.label}: {check.detail}" for check in blocking),
                blocked_by=blocking[0].name,
                checks=checks,
            )
        return GuardrailResult(
            allowed=True,
            action=action,
            reason="All guardrails passed",
            checks=checks,
        )


guardrail_engine = GuardrailEngine()
