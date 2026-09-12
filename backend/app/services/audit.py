from sqlalchemy.orm import Session

from app.database.models import AuditLog


def record(db: Session, event: str, actor: str, *, case_id: int = None, action: str = "", reason: str = "", meta: dict = None) -> AuditLog:
    audit_log = AuditLog(
        recovery_case_id=case_id,
        event=event,
        actor=actor,
        action=action,
        reason=reason,
        meta=meta or {}
    )
    db.add(audit_log)
    db.flush()
    return audit_log


def log_action(*, db: Session, case_id: int, event: str, agent: str, action: str, reason: str) -> AuditLog:
    return record(
        db,
        event=event,
        actor=agent,
        case_id=case_id,
        action=action,
        reason=reason
    )


def timeline(db: Session, case_id: int) -> list[AuditLog]:
    return (
        db.query(AuditLog)
        .filter(AuditLog.recovery_case_id == case_id)
        .order_by(AuditLog.created_at.asc())
        .all()
    )
