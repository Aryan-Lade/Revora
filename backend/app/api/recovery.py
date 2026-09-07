from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.database.database import get_db
from app.database import models
from app.api import schemas
from app.core import errors
from app.core.constants import EMAIL, VOICE_AI, PAYMENT_LINK, PROMISE_ACTIVE
from app.services import context, audit
from app.recovery import detector, executor
from app.recovery.executor import mark_recovered, move
from app.recovery.guardrails import guardrail_engine
from app.ai.provider import ai_provider
from app.ml import model as ml_model
from app.policy.engine import policy_engine
from app.channels.selector import select as select_channel
from app.voice import agent as voice_agent
from app.state import recovery_state, payment_state

router = APIRouter()

ACTION_MAP = {
    EMAIL: "SEND_EMAIL",
    VOICE_AI: "INITIATE_CALL",
    PAYMENT_LINK: "CREATE_LINK",
}


@router.get("/", response_model=List[schemas.RecoveryCase])
def get_recovery_cases(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(models.RecoveryCase)
        .options(joinedload(models.RecoveryCase.customer))
        .order_by(models.RecoveryCase.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("/run")
def run_batch_recovery(db: Session = Depends(get_db)):
    result = detector.scan(db)
    return {"status": "batch recovery started", "result": result}


@router.get("/{case_id}", response_model=schemas.RecoveryCase)
def get_recovery_case(case_id: int, db: Session = Depends(get_db)):
    case = (
        db.query(models.RecoveryCase)
        .options(joinedload(models.RecoveryCase.customer))
        .filter(models.RecoveryCase.id == case_id)
        .first()
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    return case


@router.post("/{case_id}/execute")
def execute_recovery(case_id: int, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    ctx = context.build(db, case)

    try:
        move(db, case, recovery_state.ANALYZING, "system", "Starting analysis")
    except errors.InvalidTransition:
        pass

    if not case.recommended_action:
        ml_prob = ml_model.predict_recovery_probability(ctx)
        ai_rec = ai_provider.get_recovery_recommendation(ctx, ml_prob)
        case.recommended_action = ai_rec.recommended_action
        case.recommended_channel = ai_rec.recommended_channel
        case.recovery_probability = ai_rec.confidence
        case.expected_recovery = ai_rec.expected_recovery
        case.ai_confidence = ai_rec.confidence
        db.add(case)
        db.commit()
        db.refresh(case)
        try:
            move(db, case, recovery_state.RECOMMENDED, "system", "AI recommendation generated")
        except errors.InvalidTransition:
            pass
    else:
        class _Rec:
            def __init__(self, c):
                self.recommended_action = c.recommended_action
                self.recommended_channel = c.recommended_channel
                self.confidence = c.ai_confidence or 0.0
                self.expected_recovery = float(c.expected_recovery or 0)
                self.reasoning = ""
                self.customer_message = ""
                self.recommended_delay_hours = 0.0
        ai_rec = _Rec(case)

    ctx["ai"] = {
        "recommended_action": ai_rec.recommended_action,
        "recommended_channel": ai_rec.recommended_channel,
        "confidence": ai_rec.confidence,
        "expected_recovery": ai_rec.expected_recovery,
    }

    policy_decision = policy_engine.evaluate(ctx, ai_rec.recommended_channel)
    if not policy_decision.allowed:
        raise errors.PolicyBlocked(message="Policy blocked", detail={"reason": policy_decision.reason})

    try:
        move(db, case, recovery_state.POLICY_CHECK, "system", "Policy check passed")
    except errors.InvalidTransition:
        pass

    guardrail_decision = guardrail_engine.evaluate(ctx, ai_rec.recommended_action)
    if not guardrail_decision.allowed:
        raise errors.GuardrailBlocked(message="Guardrail blocked", detail={"reason": guardrail_decision.reason})

    try:
        move(db, case, recovery_state.APPROVED, "system", "Guardrail check passed")
    except errors.InvalidTransition:
        pass

    channel_selection = select_channel(db=db, case=case, context=ctx)
    if channel_selection is None:
        raise errors.GuardrailBlocked(
            message="No eligible channels available",
            detail={"reason": "All channels blocked by policy or consent"},
        )

    action = ACTION_MAP.get(channel_selection.channel)
    if action is None:
        raise errors.ProviderUnavailable(f"Unsupported channel: {channel_selection.channel}")

    result = executor.execute_recovery_action(
        db=db, case=case, channel=channel_selection.channel, action=action
    )

    audit.log_action(
        db=db, case_id=case.id, event="RECOVERY_EXECUTED",
        agent="system", action=channel_selection.channel,
        reason=f"Selected channel: {channel_selection.channel}",
    )

    return result


@router.post("/{case_id}/stop")
def stop_recovery(case_id: int, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    case.status = recovery_state.STOPPED
    case.stop_reason = "User initiated stop"
    db.add(case)
    db.commit()
    audit.log_action(db=db, case_id=case.id, event="RECOVERY_STOPPED",
                     agent="user", action="stop", reason="User initiated stop")
    return {"status": "recovery case stopped"}


@router.post("/{case_id}/escalate")
def escalate_recovery(case_id: int, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    escalation = models.Escalation(
        recovery_case_id=case.id,
        reason="Escalated via API",
        triggered_by="user",
    )
    db.add(escalation)
    case.status = recovery_state.ESCALATED
    db.add(case)
    db.commit()
    audit.log_action(db=db, case_id=case.id, event="RECOVERY_ESCALATED",
                     agent="user", action="escalate", reason="User initiated escalation")
    return {"status": "recovery case escalated"}


@router.post("/{case_id}/contact")
def initiate_contact(case_id: int, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    ctx = context.build(db, case)
    channel_selection = select_channel(db=db, case=case, context=ctx)
    if channel_selection is None:
        raise HTTPException(status_code=400, detail="No eligible channels available")
    if channel_selection.channel == VOICE_AI:
        result = voice_agent.initiate_call(case.customer_id, case.id, db)
    elif channel_selection.channel == PAYMENT_LINK:
        from app.razorpay import payments as rzp_payments
        result = rzp_payments.create_link(db=db, case=case)
    else:
        action = ACTION_MAP.get(channel_selection.channel, channel_selection.channel)
        result = executor.execute_recovery_action(
            db=db, case=case, channel=channel_selection.channel, action=action
        )
    audit.log_action(db=db, case_id=case.id, event="CONTACT_INITIATED",
                     agent="system", action=channel_selection.channel,
                     reason=f"Contact initiated via {channel_selection.channel}")
    return {"status": "contact initiated", "channel": channel_selection.channel, "result": result}


@router.get("/{case_id}/prediction")
def get_prediction(case_id: int, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    ctx = context.build(db, case)
    ml_prob = ml_model.predict_recovery_probability(ctx)
    ai_rec = ai_provider.get_recovery_recommendation(ctx, ml_prob)
    return {
        "recovery_probability": ml_prob,
        "ai_confidence": ai_rec.confidence,
        "recommended_action": ai_rec.recommended_action,
        "recommended_channel": ai_rec.recommended_channel,
        "expected_recovery": ai_rec.expected_recovery,
        "reasoning": ai_rec.reasoning,
    }


@router.get("/{case_id}/policy")
def get_policy_decision(case_id: int, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    ctx = context.build(db, case)
    channel = case.recommended_channel or EMAIL
    policy_decision = policy_engine.evaluate(ctx, channel)
    return policy_decision.as_dict()


@router.get("/{case_id}/timeline")
def get_case_timeline(case_id: int, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    audit_logs = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.recovery_case_id == case_id)
        .order_by(models.AuditLog.created_at)
        .all()
    )
    attempts = (
        db.query(models.RecoveryAttempt)
        .filter(models.RecoveryAttempt.recovery_case_id == case_id)
        .order_by(models.RecoveryAttempt.created_at)
        .all()
    )
    communications = (
        db.query(models.Communication)
        .filter(models.Communication.recovery_case_id == case_id)
        .order_by(models.Communication.sent_at)
        .all()
    )
    promise = (
        db.query(models.PromiseToPay)
        .filter(models.PromiseToPay.recovery_case_id == case_id)
        .first()
    )
    return {
        "audit_logs": audit_logs,
        "recovery_attempts": attempts,
        "communications": communications,
        "promise_to_pay": promise,
    }


@router.post("/{case_id}/promise-to-pay", response_model=schemas.PromiseToPay)
def create_promise_to_pay(case_id: int, promise: schemas.PromiseToPayRequest, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    existing_promise = db.query(models.PromiseToPay).filter(
        models.PromiseToPay.recovery_case_id == case_id,
        models.PromiseToPay.status == PROMISE_ACTIVE,
    ).first()
    if existing_promise:
        raise HTTPException(status_code=400, detail="An active promise-to-pay already exists for this case")
    db_promise = models.PromiseToPay(
        customer_id=case.customer_id,
        recovery_case_id=case.id,
        amount=promise.amount,
        promised_date=promise.promised_date,
        channel=promise.channel,
        source_quote=promise.source_quote,
    )
    db.add(db_promise)
    case.status = recovery_state.PROMISE_TO_PAY
    case.blocked_reason = "Active promise-to-pay"
    db.add(case)
    db.commit()
    audit.log_action(db=db, case_id=case.id, event="PROMISE_TO_PAY_CREATED", agent="system",
                     action="create_promise_to_pay",
                     reason=f"Promise to pay ₹{promise.amount} on {promise.promised_date}")
    return db_promise


@router.post("/{case_id}/simulate-payment")
def simulate_payment(case_id: int, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    if case.status == recovery_state.RECOVERED:
        return {"status": "already_recovered", "recovered_amount": float(case.recovered_amount)}

    from app.core.clock import utcnow
    payment = case.payment
    if payment:
        payment.status = payment_state.RECOVERED
        payment.failure_reason = None
        payment.failure_code = None
        db.flush()

    mark_recovered(db, case, float(case.amount_at_risk), "demo_simulation",
                   "Payment simulated via demo flow")

    active_promises = db.query(models.PromiseToPay).filter(
        models.PromiseToPay.recovery_case_id == case_id,
        models.PromiseToPay.status == PROMISE_ACTIVE,
    ).all()
    for p in active_promises:
        p.status = "FULFILLED"
    db.flush()

    audit.log_action(db=db, case_id=case.id, event="PAYMENT_RECOVERED", agent="demo_simulation",
                     action="simulate_payment",
                     reason=f"Demo payment simulation: ₹{float(case.amount_at_risk):,.0f} recovered")
    db.commit()

    return {
        "status": "recovered",
        "case_id": case_id,
        "recovered_amount": float(case.recovered_amount),
        "case_status": case.status,
    }


webhook_router = APIRouter()


@webhook_router.post("/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    event_type = payload.get("event")
    if event_type == "payment.failed":
        detector.handle_failed_payment_webhook(payload, db)
    elif event_type == "payment.captured":
        detector.handle_successful_payment_webhook(payload, db)
    return {"status": "processed"}
