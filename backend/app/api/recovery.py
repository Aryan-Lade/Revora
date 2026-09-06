from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from app.database.database import get_db
from app.database import models
from app.api import schemas
from app.core import errors
from app.services import context, scoring, audit
from app.recovery import detector, executor
from app.recovery.guardrails import guardrail_engine
from app.recovery.risk import risk_score, risk_level, relationship_risk, priority_score, priority
from app.recovery.strategies import Strategy, retry_allowed, delay_for, plan
from app.agent import agent  # Assuming we have an agent module
from app.ai.provider import ai_provider
from app.ml import model as ml_model
from app.policy.engine import policy_engine
from app.channels.selector import select as select_channel
from app.gateway import pool as gateway_pool
from app.voice import agent as voice_agent
from app.razorpay import client as razorpay_client

router = APIRouter()


@router.get("/", response_model=List[schemas.RecoveryCase])
def get_recovery_cases(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    cases = db.query(models.RecoveryCase).offset(skip).limit(limit).all()
    return cases


@router.post("/run")
def run_batch_recovery(db: Session = Depends(get_db)):
    # Trigger the batch recovery process
    # This would typically be a background task, but for simplicity we run it synchronously
    # In production, we would use a task queue like Celery
    result = detector.scan(db)
    return {"status": "batch recovery started", "result": result}


@router.get("/{case_id}", response_model=schemas.RecoveryCase)
def get_recovery_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    return case


@router.post("/{case_id}/execute")
def execute_recovery(case_id: int, db: Session = Depends(get_db)):
    # Execute the recovery action for a specific case
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    # Get context for AI decision and policy/guardrails checks
    ctx = context.build(db, case)

    # Transition to ANALYZING state
    from app.state import recovery_state
    from app.recovery import executor as recovery_executor
    from app.core import errors

    try:
        move(db, case, recovery_state.ANALYZING, "system", "Starting analysis")
    except errors.InvalidTransition as e:
        # If already in ANALYZING or later, continue
        pass

    # Get AI recommendation if not already present
    if not case.recommended_action:
        # Get ML probability
        ml_prob = ml_model.predict_recovery_probability(ctx)
        # Get AI recommendation
        ai_rec = ai_provider.get_recovery_recommendation(ctx, ml_prob)
        # Update case with AI recommendation
        case.recommended_action = ai_rec.recommended_action
        case.recommended_channel = ai_rec.recommended_channel
        case.recovery_probability = ai_rec.confidence
        case.expected_recovery = ai_rec.expected_recovery
        case.ai_confidence = ai_rec.confidence
        db.add(case)
        db.commit()
        db.refresh(case)

        # Transition to RECOMMENDED state
        try:
            move(db, case, recovery_state.RECOMMENDED, "system", "AI recommendation generated")
        except errors.InvalidTransition as e:
            # If already in RECOMMENDED or later, continue
            pass
    else:
        # Create an ai_rec-like object from the case for policy and guardrails checks
        class AIRec:
            def __init__(self, action, channel, confidence, expected_recovery):
                self.recommended_action = action
                self.recommended_channel = channel
                self.confidence = confidence
                self.expected_recovery = expected_recovery
        ai_rec = AIRec(case.recommended_action, case.recommended_channel, case.ai_confidence, case.expected_recovery)

    # Update context with AI information for policy and guardrails checks
    ctx["ai"] = {
        "recommended_action": ai_rec.recommended_action,
        "recommended_channel": ai_rec.recommended_channel,
        "confidence": ai_rec.confidence,
        "expected_recovery": ai_rec.expected_recovery
    }

    # Check policy using the recommended channel from AI
    policy_decision = policy_engine.evaluate(ctx, ai_rec.recommended_channel)
    if not policy_decision.allowed:
        raise errors.PolicyBlocked(message="Policy blocked", detail={"reason": policy_decision.reason})

    # Transition to POLICY_CHECK state
    try:
        move(db, case, recovery_state.POLICY_CHECK, "system", "Policy check passed")
    except errors.InvalidTransition as e:
        # If already in POLICY_CHECK or later, continue
        pass

    # Check guardrails using the recommended action from AI
    guardrail_decision = guardrail_engine.evaluate(ctx, ai_rec.recommended_action)
    if not guardrail_decision.allowed:
        raise errors.GuardrailBlocked(message="Guardrail blocked", detail={"reason": guardrail_decision.reason})

    # Transition to APPROVED state
    try:
        move(db, case, recovery_state.APPROVED, "system", "Guardrail check passed")
    except errors.InvalidTransition as e:
        # If already in APPROVED or later, continue
        pass

    # Select channel (this might override the AI recommendation, but we'll use the selector's choice)
    channel_selection = select_channel(db=db, case=case, context=ctx)
    if channel_selection is None:
        raise errors.GuardrailBlocked(message="No eligible channels available", detail={"reason": "All channels blocked by policy or consent"})

    # Determine the appropriate action based on the selected channel
    from app.core.constants import EMAIL, VOICE_AI, PAYMENT_LINK
    action_map = {
        EMAIL: "SEND_EMAIL",
        VOICE_AI: "INITIATE_CALL",
        PAYMENT_LINK: "CREATE_LINK"
    }
    action = action_map.get(channel_selection.channel)
    if action is None:
        raise errors.ProviderUnsupported(f"Unsupported channel: {channel_selection.channel}")

    # Transition to PROCESSING state
    try:
        move(db, case, recovery_state.PROCESSING, "system", "Starting recovery action")
    except errors.InvalidTransition as e:
        # If already in PROCESSING or later, continue
        pass

    # Execute the action via the recovery executor
    result = recovery_executor.execute_recovery_action(
        db=db,
        case=case,
        channel=channel_selection.channel,
        action=action
    )

    # Log audit event
    audit.log_action(
        case_id=case.id,
        event="RECOVERY_EXECUTED",
        agent="system",
        action=channel_selection.action,
        reason=f"Selected channel: {channel_selection.channel}",
        db=db
    )

    return result


@router.post("/{case_id}/stop")
def stop_recovery(case_id: int, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    case.status = models.recovery_state.STOPPED
    case.stop_reason = "User initiated stop"
    db.add(case)
    db.commit()

    audit.log_action(
        case_id=case.id,
        event="RECOVERY_STOPPED",
        agent="user",
        action="stop",
        reason="User initiated stop",
        db=db
    )

    return {"status": "recovery case stopped"}


@router.post("/{case_id}/escalate")
def escalate_recovery(case_id: int, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    # Create escalation record
    escalation = models.Escalation(
        recovery_case_id=case.id,
        reason="Escalated via API",
        triggered_by="user"
    )
    db.add(escalation)

    # Update case status
    case.status = models.recovery_state.ESCALATED
    db.add(case)
    db.commit()

    audit.log_action(
        case_id=case.id,
        event="RECOVERY_ESCALATED",
        agent="user",
        action="escalate",
        reason="User initiated escalation",
        db=db
    )

    return {"status": "recovery case escalated"}


@router.post("/{case_id}/contact")
def initiate_contact(case_id: int, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    # Select channel for contact
    channel_selection = channel_selector.select_channel(case, db)

    # Initiate contact via the appropriate channel
    if channel_selection.channel == models.EMAIL:
        # Use email provider
        pass  # Implementation depends on email provider
    elif channel_selection.channel == models.VOICE_AI:
        # Use voice agent
        voice_agent.initiate_call(case, db)
    elif channel_selection.channel == models.SMS:
        # Use SMS provider
        pass
    elif channel_selection.channel == models.PAYMENT_LINK:
        # Generate payment link
        link = razorpay_client.create_payment_link(
            amount=case.amount_at_risk,
            customer_id=case.customer_id,
            description=f"Recovery payment for case {case.id}"
        )
        # Send link via email or SMS as per channel selection
        # For now, we just return the link
        return {"payment_link": link}
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported channel: {channel_selection.channel}")

    # Log audit event
    audit.log_action(
        case_id=case.id,
        event="CONTACT_INITIATED",
        agent="system",
        action=channel_selection.channel,
        reason=f"Contact initiated via {channel_selection.channel}",
        db=db
    )

    return {"status": "contact initiated", "channel": channel_selection.channel}


@router.get("/{case_id}/prediction")
def get_prediction(case_id: int, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    # Build context for prediction
    ctx = context.build_case_context(case, db)
    ml_prob = ml_model.predict_recovery_probability(ctx)
    ai_rec = ai_provider.get_recovery_recommendation(ctx, ml_prob)

    return {
        "recovery_probability": ml_prob,
        "ai_confidence": ai_rec.confidence,
        "recommended_action": ai_rec.recommended_action,
        "recommended_channel": ai_rec.recommended_channel,
        "expected_recovery": ai_rec.expected_recovery,
        "reasoning": ai_rec.reasoning
    }


@router.get("/{case_id}/policy")
def get_policy_decision(case_id: int, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    policy_decision = policy_engine.check_policy(case, db)
    return policy_decision


@router.get("/{case_id}/timeline")
def get_case_timeline(case_id: int, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    # Get audit logs for this case
    audit_logs = db.query(models.AuditLog).filter(models.AuditLog.recovery_case_id == case_id).order_by(models.AuditLog.created_at).all()

    # Get recovery attempts
    attempts = db.query(models.RecoveryAttempt).filter(models.RecoveryAttempt.recovery_case_id == case_id).order_by(models.RecoveryAttempt.created_at).all()

    # Get communications
    communications = db.query(models.Communication).filter(models.Communication.recovery_case_id == case_id).order_by(models.Communication.sent_at).all()

    # Get promise to pay if any
    promise = db.query(models.PromiseToPay).filter(models.PromiseToPay.recovery_case_id == case_id).first()

    return {
        "audit_logs": audit_logs,
        "recovery_attempts": attempts,
        "communications": communications,
        "promise_to_pay": promise
    }


@router.post("/{case_id}/promise-to-pay", response_model=schemas.PromiseToPay)
def create_promise_to_pay(case_id: int, promise: schemas.PromiseToPayCreate, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    # Check if there's already an active promise
    existing_promise = db.query(models.PromiseToPay).filter(
        models.PromiseToPay.recovery_case_id == case_id,
        models.PromiseToPay.status == models.PROMISE_ACTIVE
    ).first()
    if existing_promise:
        raise HTTPException(status_code=400, detail="An active promise-to-pay already exists for this case")

    # Create promise-to-pay record
    db_promise = models.PromiseToPay(
        customer_id=case.customer_id,
        recovery_case_id=case.id,
        amount=promise.amount,
        promised_date=promise.promised_date,
        channel=promise.channel,
        source_quote=promise.source_quote
    )
    db.add(db_promise)

    # Update case status
    case.status = models.recovery_state.PROMISE_TO_PAY
    case.blocked_reason = "Active promise-to-pay"
    db.add(case)
    db.commit()

    audit.log_action(
        case_id=case.id,
        event="PROMISE_TO_PAY_CREATED",
        agent="system",
        action="create_promise_to_pay",
        reason=f"Promise to pay for {promise.amount} on {promise.promised_date}",
        db=db
    )

    return db_promise


# Webhook router for Razorpay
webhook_router = APIRouter()


@webhook_router.post("/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    # Verify webhook signature
    # In production, we would verify the signature using the webhook secret
    # For now, we assume the request is valid

    payload = await request.json()

    # Handle different event types
    event_type = payload.get("event")

    if event_type == "payment.failed":
        # Detect failed payment and create recovery case
        detector.handle_failed_payment_webhook(payload, db)
    elif event_type == "payment.captured":
        # Payment succeeded, update recovery case if any
        detector.handle_successful_payment_webhook(payload, db)
    # Add other event types as needed

    return {"status": "processed"}