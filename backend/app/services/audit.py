from sqlalchemy.orm import Session

from app.database.models import AuditLog


def record(db: Session, event: str, actor: str, *, case_id: int = None, action: str = "", reason: str = "", meta: dict = None) -> AuditLog:
    """
    Record an audit event.
    """
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
    """
    Log a specific action taken on a recovery case.
    All arguments must be passed as keyword arguments.
    """
    return record(
        db,
        event=event,
        actor=agent,
        case_id=case_id,
        action=action,
        reason=reason
    )
