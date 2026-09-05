from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import AuditLog


def record(
    db: Session,
    event: str,
    actor: str,
    *,
    case_id: int | None = None,
    action: str = "",
    reason: str = "",
    meta: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        recovery_case_id=case_id,
        event=event,
        actor=actor,
        action=action[:48],
        reason=reason[:400],
        meta=meta or {},
    )
    db.add(entry)
    db.flush()
    return entry


def timeline(db: Session, case_id: int) -> list[AuditLog]:
    query = select(AuditLog).where(AuditLog.recovery_case_id == case_id).order_by(AuditLog.id)
    return list(db.scalars(query))


def as_dict(entry: AuditLog) -> dict:
    return {
        "id": entry.id,
        "event": entry.event,
        "actor": entry.actor,
        "action": entry.action,
        "reason": entry.reason,
        "metadata": entry.meta,
        "created_at": entry.created_at,
    }
