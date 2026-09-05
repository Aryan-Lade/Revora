from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.constants import (
    ACTOR_AGENT,
    CONTACT_CHANNELS,
    EMAIL,
    EVENT_CHANNEL_SELECTED,
    IN_APP,
    SMS,
    VOICE_AI,
)
from app.core.money import rupees
from app.database.models import ChannelAttempt, RecoveryCase
from app.ml.features import clamp
from app.services import audit

STRENGTH = {EMAIL: 0.55, SMS: 0.62, VOICE_AI: 0.78, IN_APP: 0.42}
COST = {EMAIL: 1.0, SMS: 3.0, VOICE_AI: 22.0, IN_APP: 0.5}
INTRUSION = {EMAIL: 0.10, SMS: 0.25, VOICE_AI: 0.45, IN_APP: 0.05}
PREFERENCE_BOOST = 1.15
FATIGUE_PENALTY = 0.12


@dataclass
class ChannelOption:
    channel: str
    score: float
    expected_value: float
    eligible: bool
    reason: str

    def as_dict(self) -> dict:
        return {
            "channel": self.channel,
            "score": self.score,
            "expected_value": self.expected_value,
            "eligible": self.eligible,
            "reason": self.reason,
        }


def channel_score(channel: str, context: dict) -> float:
    case = context["case"]
    customer = context["customer"]
    contact = context["contact_history"]
    engagement = 0.6 + 0.4 * customer["engagement_score"]
    preference = PREFERENCE_BOOST if customer["preferred_channel"] == channel else 1.0
    fatigue = 1 - FATIGUE_PENALTY * contact["contacts_in_window"]
    relationship = 1 - INTRUSION.get(channel, 0.2) * case["relationship_risk"]
    value = STRENGTH.get(channel, 0.4) * engagement * preference * fatigue * relationship
    return round(clamp(value), 4)


def expected_value(channel: str, context: dict, score: float) -> float:
    return rupees(context["case"]["expected_recovery"] * score - COST.get(channel, 1.0))


def rank(context: dict) -> list[ChannelOption]:
    available = set(context.get("available_channels", []))
    options = []
    for channel in CONTACT_CHANNELS:
        score = channel_score(channel, context)
        options.append(
            ChannelOption(
                channel=channel,
                score=score,
                expected_value=expected_value(channel, context, score),
                eligible=channel in available,
                reason="Allowed by policy" if channel in available else "Blocked by policy or consent",
            )
        )
    return sorted(options, key=lambda option: (option.eligible, option.expected_value), reverse=True)


def choose(options: list[ChannelOption], preferred: str | None = None) -> ChannelOption | None:
    eligible = [option for option in options if option.eligible]
    if not eligible:
        return None
    for option in eligible:
        if option.channel == preferred:
            return option
    return eligible[0]


def select(
    db: Session,
    case: RecoveryCase,
    context: dict,
    preferred: str | None = None,
) -> ChannelOption | None:
    options = rank(context)
    chosen = choose(options, preferred)
    for option in options:
        db.add(
            ChannelAttempt(
                recovery_case_id=case.id,
                channel=option.channel,
                score=option.score,
                expected_value=option.expected_value,
                eligible=option.eligible,
                selected=chosen is not None and option.channel == chosen.channel,
                reason=option.reason,
            )
        )
    db.flush()
    if chosen is None:
        return None
    audit.record(
        db,
        EVENT_CHANNEL_SELECTED,
        ACTOR_AGENT,
        case_id=case.id,
        action=chosen.channel,
        reason=(
            f"{chosen.channel} scored {chosen.score:.2f} with expected value "
            f"Rs {chosen.expected_value:,.0f}"
        ),
        meta={"selected": chosen.channel, "options": [option.as_dict() for option in options]},
    )
    return chosen
