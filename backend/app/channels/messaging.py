from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.config import settings
from app.core.constants import (
    ACTOR_EXECUTOR,
    COMMUNICATION_SENT,
    DIRECTION_INBOUND,
    DIRECTION_OUTBOUND,
    EMAIL,
    EVENT_CONTACT_COMPLETED,
    EVENT_CONTACT_STARTED,
    IN_APP,
    SMS,
)
from app.core.seeded import token
from app.database.models import Communication, RecoveryCase
from app.services import audit

SUBJECTS = {
    EMAIL: "Action needed on your {plan} payment of Rs {amount:,.0f}",
    SMS: "Rs {amount:,.0f} payment pending",
    IN_APP: "Complete your Rs {amount:,.0f} payment",
}
SMS_LIMIT = 320
FOOTER = "Revora on behalf of your subscription provider. Reply STOP to opt out of payment reminders."


def provider_for(channel: str) -> str:
    if channel == EMAIL:
        return settings.email_provider
    return "demo"


def link_line(link: dict | None) -> str:
    if not link:
        return ""
    expires = datetime.fromisoformat(link["expires_at"])
    return f"Pay securely: {link['short_url']}\nThe link stays valid until {expires:%d %b %Y, %H:%M} UTC."


def compose(context: dict, channel: str, message: str, link: dict | None = None) -> tuple[str, str]:
    case = context["case"]
    subscription = context.get("subscription") or {}
    plan = subscription.get("plan_name") or "your subscription"
    template = SUBJECTS.get(channel, SUBJECTS[IN_APP])
    subject = template.format(plan=plan, amount=case["amount_at_risk"])
    parts = [message.strip(), link_line(link)]
    if channel == EMAIL:
        parts.append(FOOTER)
    body = "\n\n".join(part for part in parts if part)
    if channel == SMS:
        body = body[:SMS_LIMIT]
    return subject, body


def send(
    db: Session,
    case: RecoveryCase,
    channel: str,
    subject: str,
    body: str,
    *,
    actor: str = ACTOR_EXECUTOR,
    provider_ref: str | None = None,
    now: datetime | None = None,
) -> Communication:
    now = now or utcnow()
    provider = provider_for(channel)
    audit.record(
        db,
        EVENT_CONTACT_STARTED,
        actor,
        case_id=case.id,
        action=channel,
        reason=f"Sending {channel} message through {provider}",
        meta={"channel": channel, "provider": provider, "subject": subject},
    )
    communication = Communication(
        recovery_case_id=case.id,
        customer_id=case.customer_id,
        channel=channel,
        direction=DIRECTION_OUTBOUND,
        subject=subject[:200],
        body=body,
        status=COMMUNICATION_SENT,
        provider=provider,
        provider_ref=provider_ref or f"msg_{token(case.reference, channel, now.isoformat())}",
        sent_at=now,
    )
    db.add(communication)
    case.contact_count += 1
    db.flush()
    audit.record(
        db,
        EVENT_CONTACT_COMPLETED,
        actor,
        case_id=case.id,
        action=channel,
        reason=f"{channel} message delivered to {case.customer.email}",
        meta={
            "channel": channel,
            "provider": provider,
            "provider_ref": communication.provider_ref,
            "communication_id": communication.id,
            "contact_count": case.contact_count,
        },
    )
    return communication


def mark_responded(db: Session, communication: Communication, note: str = "") -> Communication:
    communication.responded = True
    if note:
        db.add(
            Communication(
                recovery_case_id=communication.recovery_case_id,
                customer_id=communication.customer_id,
                channel=communication.channel,
                direction=DIRECTION_INBOUND,
                subject="Customer response",
                body=note,
                status=COMMUNICATION_SENT,
                provider=communication.provider,
            )
        )
    db.flush()
    return communication


def latest(db: Session, case_id: int, channel: str | None = None) -> Communication | None:
    conditions = [
        Communication.recovery_case_id == case_id,
        Communication.direction == DIRECTION_OUTBOUND,
    ]
    if channel:
        conditions.append(Communication.channel == channel)
    query = select(Communication).where(*conditions).order_by(Communication.id.desc()).limit(1)
    return db.scalar(query)
