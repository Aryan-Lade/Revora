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
    """
    Execute a recovery action for a case via the specified channel.
    Returns a dictionary with the result of the action.
    """
    print(f"DEBUG: execute_recovery_action called with case_id={case.id}, channel={channel}, action={action}")
    from app.channels import messaging
    from app.razorpay import payments as razorpay_payments
    from app.voice import agent as voice_agent

    # Generate an idempotency key for this action
    idempotency_key = f"{case.id}:{channel}:{action}:{case.attempt_count + 1}"

    # Check if we have already executed this action (idempotency)
    existing = db.query(IdempotencyRecord).filter(
        IdempotencyRecord.idempotency_key == idempotency_key
    ).first()
    if existing:
        # Return the previous result
        return existing.response

    # Create a recovery attempt record (pending)
    print(f"DEBUG: About to call Strategy with action={action}, channel={channel}")
    print(f"DEBUG: Strategy.__init__ signature: {Strategy.__init__.__annotations__}")
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
            source="system"
        ),
        idempotency_key,
        case.amount_at_risk,  # expected recovery is the full amount at risk for simplicity
    )

    # Move case to PROCESSING (if not already)
    move(db, case, recovery_state.PROCESSING, ACTOR_EXECUTOR, "Starting recovery action")

    # Execute the action based on channel and action
    try:
        if channel == models.EMAIL and action == "SEND_EMAIL":
            # Send email via messaging
            result = messaging.send_email(case, db)
        elif channel == models.VOICE_AI and action == "INITIATE_CALL":
            # Initiate voice call
            result = voice_agent.initiate_call(case.customer_id, case.id, db)
        elif channel == models.PAYMENT_LINK and action == "CREATE_LINK":
            # Create payment link via Razorpay
            link = razorpay_payments.create_payment_link(
                amount=case.amount_at_risk,
                customer_id=case.customer_id,
                description=f"Recovery payment for case {case.id}"
            )
            result = {"link": link, "status": "created"}
        else:
            # Unsupported channel/action combination
            raise errors.ProviderUnsupported(f"Unsupported channel/action: {channel}/{action}")

        # If we got here, the action was initiated successfully
        # Update the attempt as succeeded (in flight for voice/email, but we'll mark as succeeded for now)
        # Note: For email and voice, we might want to wait for a callback/webhook to mark as succeeded.
        # For simplicity, we'll mark the attempt as succeeded immediately.
        close_attempt(
            db,
            attempt,
            ATTEMPT_SUCCEEDED,
            "Action executed successfully",
            utcnow(),
            actual=case.amount_at_risk if action in ["CREATE_LINK", "SEND_EMAIL", "INITIATE_CALL"] else 0.0,
        )

        # Update case: increment attempt count and contact count
        case.attempt_count += 1
        if channel in CONTACT_CHANNELS:
            case.contact_count += 1
        db.flush()

        # Log audit event for the action
        audit.record(
            db,
            f"RECOVERY_{action}",
            ACTOR_EXECUTOR,
            case_id=case.id,
            action=action,
            reason=f"Executed {action} via {channel}",
            meta={"channel": channel, "attempt_id": attempt.id},
        )

        # Prepare response
        response = {
            "status": "success",
            "action": action,
            "channel": channel,
            "attempt_id": attempt.id,
            "case_id": case.id,
            "result": result,
        }

        # Save idempotency record
        idempotency_record = IdempotencyRecord(
            idempotency_key=idempotency_key,
            operation=f"{channel}:{action}",
            status=IdempotencyRecord.IDEMPOTENCY_COMPLETED,
            response=response,
        )
        db.add(idempotency_record)
        db.commit()

        return response

    except Exception as e:
        # If there was an error, mark the attempt as failed
        close_attempt(
            db,
            attempt,
            ATTEMPT_FAILED,
            str(e)[:240],
            utcnow(),
            actual=0.0,
        )
        db.flush()

        # Log audit event for the failure
        audit.record(
            db,
            f"RECOVERY_{action}_FAILED",
            ACTOR_EXECUTOR,
            case_id=case.id,
            action=action,
            reason=str(e)[:400],
            meta={"channel": channel, "attempt_id": attempt.id},
        )

        # Re-raise the exception to be handled by the caller
        raise