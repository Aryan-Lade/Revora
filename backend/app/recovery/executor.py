from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.channels import messaging
from app.core.clock import utcnow
from app.core.constants import (
    ACTOR_EXECUTOR,
    ACTOR_GUARDRAIL,
    ATTEMPT_BLOCKED,
    ATTEMPT_FAILED,
    ATTEMPT_IN_FLIGHT,
    ATTEMPT_PENDING,
    ATTEMPT_SUCCEEDED,
    CONTACT_CHANNELS,
    ESCALATION_OPEN,
    EVENT_CASE_STOPPED,
    EVENT_ESCALATED,
    EVENT_GUARDRAIL_BLOCKED,
    EVENT_GUARDRAIL_CHECKED,
    EVENT_STATE_CHANGED,
    HUMAN_ESCALATION,
    PAYMENT_LINK,
    PAYMENT_RETRY,
    VOICE_AI,
)
from app.core.money import rupees
from app.database.models import Escalation, GuardrailDecision, RecoveryAttempt, RecoveryCase
from app.razorpay import payments
from app.recovery.guardrails import guardrail_engine
from app.recovery.strategies import Strategy
from app.services import audit, idempotency
from app.state import recovery_state
from app.voice import agent as voice_agent

STOP_BLOCKERS = {"customer_consent", "payment_open", "case_open"}
ESCALATE_BLOCKERS = {"amount_threshold", "retry_limit", "ai_confidence"}
RETRY_BACKOFF_HOURS = 12.0
FOLLOW_UP_HOURS = 24.0
LINK_ACTIONS = {PAYMENT_LINK, *CONTACT_CHANNELS}


def move(
    db: Session,
    case: RecoveryCase,
    target: str,
    actor: str,
    reason: str,
    meta: dict | None = None,
) -> str:
    previous = case.status
    case.status = recovery_state.transition(case.status, target)
    if recovery_state.is_terminal(case.status):
        case.resolved_at = case.resolved_at or utcnow()
    db.flush()
    if previous != case.status:
        audit.record(
            db,
            EVENT_STATE_CHANGED,
            actor,
            case_id=case.id,
            action=case.status,
            reason=reason,
            meta={"from": previous, "to": case.status, **(meta or {})},
        )
    return case.status


def schedule(db: Session, case: RecoveryCase, hours: float, now: datetime) -> datetime:
    case.next_action_at = now + timedelta(hours=hours)
    db.flush()
    return case.next_action_at


def mark_recovered(
    db: Session,
    case: RecoveryCase,
    amount: float,
    actor: str,
    reason: str,
    now: datetime,
) -> None:
    customer = case.customer
    case.recovered_amount = rupees(amount)
    case.next_action_at = None
    case.resolved_at = now
    customer.recoveries_succeeded += 1
    customer.successful_payments += 1
    customer.total_spent = rupees(float(customer.total_spent) + amount)
    move(db, case, recovery_state.RECOVERED, actor, reason, {"recovered_amount": rupees(amount)})


def escalate(
    db: Session,
    case: RecoveryCase,
    reason: str,
    actor: str = ACTOR_EXECUTOR,
    triggered_by: str = ACTOR_EXECUTOR,
) -> Escalation:
    escalation = Escalation(
        recovery_case_id=case.id,
        reason=reason[:240],
        triggered_by=triggered_by,
        status=ESCALATION_OPEN,
    )
    db.add(escalation)
    case.next_action_at = None
    db.flush()
    audit.record(
        db,
        EVENT_ESCALATED,
        actor,
        case_id=case.id,
        action=HUMAN_ESCALATION,
        reason=reason,
        meta={"escalation_id": escalation.id, "assigned_to": escalation.assigned_to},
    )
    move(db, case, recovery_state.ESCALATED, actor, reason)
    return escalation


def stop(db: Session, case: RecoveryCase, reason: str, actor: str = ACTOR_EXECUTOR) -> None:
    case.stop_reason = reason[:160]
    case.next_action_at = None
    case.customer.recoveries_failed += 1
    db.flush()
    audit.record(
        db,
        EVENT_CASE_STOPPED,
        actor,
        case_id=case.id,
        action=case.status,
        reason=reason,
        meta={"stop_reason": case.stop_reason},
    )
    move(db, case, recovery_state.STOPPED, actor, reason)


def open_attempt(
    db: Session,
    case: RecoveryCase,
    strategy: Strategy,
    key: str,
    expected: float,
) -> RecoveryAttempt:
    attempt = RecoveryAttempt(
        recovery_case_id=case.id,
        action=strategy.action,
        channel=strategy.channel,
        status=ATTEMPT_PENDING,
        reason=strategy.reason[:240],
        idempotency_key=key,
        attempt_number=case.attempt_count + 1,
        expected_recovery=rupees(expected),
    )
    db.add(attempt)
    db.flush()
    return attempt


def close_attempt(
    db: Session,
    attempt: RecoveryAttempt,
    status: str,
    reason: str,
    now: datetime,
    actual: float = 0.0,
) -> RecoveryAttempt:
    attempt.status = status
    attempt.reason = reason[:240]
    attempt.actual_recovery = rupees(actual)
    attempt.completed_at = now
    db.flush()
    return attempt
