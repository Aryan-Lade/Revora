from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.core.checks import Check
from app.core.clock import in_quiet_hours, next_allowed_window, utcnow
from app.core.config import settings
from app.core.constants import EMAIL, IN_APP, SMS, VOICE_AI

INTRUSIVE_CHANNELS = {EMAIL, SMS, VOICE_AI}
OPT_IN_FIELD = {EMAIL: "email_opt_in", SMS: "sms_opt_in", VOICE_AI: "voice_opt_in"}
HIGH_TOUCH_CHANNELS = {VOICE_AI, SMS}


@dataclass
class PolicyResult:
    allowed: bool
    channel: str
    reason: str
    blocked_by: str | None = None
    next_contact_at: datetime | None = None
    checks: list[Check] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "channel": self.channel,
            "reason": self.reason,
            "blocked_by": self.blocked_by,
            "next_contact_at": self.next_contact_at,
            "checks": [check.as_dict() for check in self.checks],
        }


class PolicyEngine:
    def __init__(self, config=settings):
        self.config = config

    def quiet_hours_bounds(self, customer: dict) -> tuple[int, int]:
        return (
            customer.get("quiet_hours_start") or self.config.quiet_hours_start,
            customer.get("quiet_hours_end") or self.config.quiet_hours_end,
        )

    def evaluate(self, context: dict, channel: str, now: datetime | None = None) -> PolicyResult:
        now = now or utcnow()
        case = context["case"]
        customer = context["customer"]
        payment = context["payment"]
        contact = context["contact_history"]
        promise = context.get("promise_to_pay")
        start, end = self.quiet_hours_bounds(customer)
        quiet = in_quiet_hours(now, start, end)
        intrusive = channel in INTRUSIVE_CHANNELS
        opt_in_field = OPT_IN_FIELD.get(channel)
        promise_date = promise["promised_date"] if promise else None
        scheduled = case.get("next_action_at")

        checks = [
            Check(
                "customer_opt_out",
                "Customer Opt-out",
                not customer["opted_out"],
                "Customer accepts recovery contact" if not customer["opted_out"] else "Customer opted out",
            ),
            Check(
                "channel_opt_in",
                "Channel Consent",
                not opt_in_field or bool(customer[opt_in_field]),
                f"{channel} consent {'granted' if not opt_in_field or customer[opt_in_field] else 'withheld'}",
            ),
            Check(
                "promise_to_pay",
                "Promise to Pay",
                promise is None,
                "No active promise" if promise is None else f"Active promise until {promise_date:%d %b %Y}",
            ),
            Check(
                "quiet_hours",
                "Quiet Hours",
                not (intrusive and quiet),
                f"{start:02d}:00-{end:02d}:00 IST window {'active' if quiet else 'clear'}",
            ),
            Check(
                "contact_frequency",
                "Contact Frequency",
                contact["contacts_in_window"] < self.config.max_contacts_per_window,
                f"{contact['contacts_in_window']} of {self.config.max_contacts_per_window} contacts in {self.config.recovery_window_hours}h",
            ),
            Check(
                "channel_frequency",
                "Channel Frequency",
                self.channel_frequency_ok(channel, contact),
                self.channel_frequency_detail(channel, contact),
            ),
            Check(
                "recovery_window",
                "Recovery Window",
                case["hours_since_failure"] <= self.config.recovery_window_hours,
                f"{case['hours_since_failure']:.1f}h of {self.config.recovery_window_hours}h elapsed",
            ),
            Check(
                "payment_state",
                "Payment State",
                not payment["settled"],
                f"Payment is {payment['status']}",
            ),
            Check(
                "recovery_state",
                "Recovery State",
                not case["resolved"],
                f"Case is {case['status']}",
            ),
            Check(
                "relationship_risk",
                "Relationship Risk",
                case["relationship_risk"] < (0.6 if channel in HIGH_TOUCH_CHANNELS else 0.8),
                f"Relationship risk {case['relationship_risk']:.2f}",
            ),
            Check(
                "schedule",
                "Scheduled Window",
                not scheduled or scheduled <= now,
                "Ready now" if not scheduled or scheduled <= now else f"Next action at {scheduled:%d %b %H:%M} UTC",
            ),
        ]

        blocking = [check for check in checks if not check.passed]
        if not blocking:
            return PolicyResult(True, channel, f"{channel} contact allowed now", None, now, checks)
        first = blocking[0]
        return PolicyResult(
            allowed=False,
            channel=channel,
            reason="; ".join(f"{check.label}: {check.detail}" for check in blocking),
            blocked_by=first.name,
            next_contact_at=self.next_contact_at(first.name, context, channel, now, start, end),
            checks=checks,
        )

    def channel_frequency_ok(self, channel: str, contact: dict) -> bool:
        if channel == EMAIL:
            return contact["emails_today"] < self.config.max_email_per_day
        if channel == VOICE_AI:
            return contact["voice_calls_today"] < self.config.max_voice_per_day
        if channel == SMS:
            return contact["sms_today"] < self.config.max_email_per_day
        return True

    def channel_frequency_detail(self, channel: str, contact: dict) -> str:
        if channel == EMAIL:
            return f"{contact['emails_today']} of {self.config.max_email_per_day} emails in 24h"
        if channel == VOICE_AI:
            return f"{contact['voice_calls_today']} of {self.config.max_voice_per_day} voice calls in 24h"
        if channel == SMS:
            return f"{contact['sms_today']} of {self.config.max_email_per_day} messages in 24h"
        return f"{channel} has no per-day cap"

    def next_contact_at(
        self,
        blocked_by: str,
        context: dict,
        channel: str,
        now: datetime,
        start: int,
        end: int,
    ) -> datetime | None:
        if blocked_by in {"customer_opt_out", "channel_opt_in", "payment_state", "recovery_state"}:
            return None
        if blocked_by == "quiet_hours":
            return next_allowed_window(now, start, end)
        if blocked_by == "promise_to_pay":
            promise = context["promise_to_pay"]
            return promise["promised_date"] + timedelta(days=1)
        if blocked_by == "schedule":
            return context["case"]["next_action_at"]
        if blocked_by in {"contact_frequency", "channel_frequency"}:
            last = context["contact_history"].get("last_contact_at")
            base = (last or now) + timedelta(hours=24)
            return next_allowed_window(base, start, end)
        if blocked_by == "recovery_window":
            return None
        return next_allowed_window(now + timedelta(hours=12), start, end)

    def available_channels(self, context: dict, now: datetime | None = None) -> list[str]:
        now = now or utcnow()
        channels = []
        for channel in (EMAIL, SMS, VOICE_AI, IN_APP):
            if self.evaluate(context, channel, now).allowed:
                channels.append(channel)
        return channels


policy_engine = PolicyEngine()
