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
    EMAIL,
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
from app.database.models import Escalation, GuardrailDecision, IdempotencyRecord, RecoveryAttempt, RecoveryCase
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


def execute_recovery_action(
    db: Session,
    case: RecoveryCase,
    channel: str,
    action: str,
) -> dict:
    from app.razorpay import payments as razorpay_payments
    from app.core.errors import ProviderUnavailable

    idempotency_key = f"{case.id}:{channel}:{action}:{case.attempt_count + 1}"
    existing = db.query(IdempotencyRecord).filter(
        IdempotencyRecord.idempotency_key == idempotency_key
    ).first()
    if existing:
        return existing.response

    attempt = open_attempt(
        db,
        case,
        Strategy(
            action=action,
            channel=channel,
            delay_hours=0.0,
            message=f"Executing {action} via {channel}",
            confidence=case.ai_confidence if case.ai_confidence is not None else 1.0,
            reason=f"Executing {action} via {channel}",
            source="system",
        ),
        idempotency_key,
        float(case.amount_at_risk),
    )

    move(db, case, recovery_state.PROCESSING, ACTOR_EXECUTOR, "Starting recovery action")

    try:
        if channel == EMAIL and action == "SEND_EMAIL":
            from app.services import context as context_service
            ctx = context_service.build(db, case)
            message = (
                f"Hi {case.customer.name}, your payment of ₹{float(case.amount_at_risk):,.0f} "
                f"could not be processed. Please use the payment link below to complete it."
            )
            subject = f"Action needed: ₹{float(case.amount_at_risk):,.0f} payment for your subscription"
            comm = messaging.send(db, case, EMAIL, subject, message)
            result = {"communication_id": comm.id, "status": "sent", "channel": EMAIL}
        elif channel == VOICE_AI and action == "INITIATE_CALL":
            result = voice_agent.initiate_call(case.customer_id, case.id, db)
        elif channel == PAYMENT_LINK and action == "CREATE_LINK":
            result = razorpay_payments.create_link(db=db, case=case)
        else:
            raise ProviderUnavailable(f"Unsupported channel/action: {channel}/{action}")

        close_attempt(db, attempt, ATTEMPT_SUCCEEDED, "Action executed successfully", utcnow(),
                      actual=float(case.amount_at_risk))
        case.attempt_count += 1
        if channel in CONTACT_CHANNELS:
            case.contact_count += 1
        db.flush()

        audit.record(db, f"RECOVERY_{action}", ACTOR_EXECUTOR, case_id=case.id, action=action,
                     reason=f"Executed {action} via {channel}",
                     meta={"channel": channel, "attempt_id": attempt.id})

        response = {
            "status": "success",
            "action": action,
            "channel": channel,
            "attempt_id": attempt.id,
            "case_id": case.id,
            "result": result,
        }
        db.add(IdempotencyRecord(
            idempotency_key=idempotency_key,
            operation=f"{channel}:{action}",
            status="COMPLETED",
            response=response,
        ))
        db.commit()
        return response

    except Exception as e:
        close_attempt(db, attempt, ATTEMPT_FAILED, str(e)[:240], utcnow(), actual=0.0)
        db.flush()
        audit.record(db, f"RECOVERY_{action}_FAILED", ACTOR_EXECUTOR, case_id=case.id, action=action,
                     reason=str(e)[:400], meta={"channel": channel, "attempt_id": attempt.id})
        raise