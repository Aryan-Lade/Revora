from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List

from app.database.database import get_db
from app.database import models
from app.state import recovery_state

router = APIRouter()


@router.get("/recovery-by-channel", response_model=List[Dict])
def get_recovery_by_channel(db: Session = Depends(get_db)):
    results = db.query(
        models.Communication.channel,
        func.sum(models.RecoveryCase.recovered_amount).label("amount")
    ).join(
        models.RecoveryCase, models.Communication.recovery_case_id == models.RecoveryCase.id
    ).filter(
        models.RecoveryCase.status == recovery_state.RECOVERED,
        models.Communication.status == "SENT"
    ).group_by(
        models.Communication.channel
    ).all()

    return [{"name": channel, "value": float(amount or 0)} for channel, amount in results]


@router.get("/recovery-by-reason", response_model=List[Dict])
def get_recovery_by_reason(db: Session = Depends(get_db)):
    results = db.query(
        models.RecoveryCase.failure_type,
        func.sum(models.RecoveryCase.recovered_amount).label("amount")
    ).filter(
        models.RecoveryCase.status == recovery_state.RECOVERED
    ).group_by(
        models.RecoveryCase.failure_type
    ).all()

    return [{"name": failure_type, "value": float(amount or 0)} for failure_type, amount in results]


@router.get("/recovery-by-segment", response_model=List[Dict])
def get_recovery_by_segment(db: Session = Depends(get_db)):
    results = db.query(
        models.Customer.risk_segment,
        func.count(models.RecoveryCase.id).label("count"),
        func.sum(models.RecoveryCase.recovered_amount).label("amount")
    ).join(
        models.RecoveryCase, models.Customer.id == models.RecoveryCase.customer_id
    ).filter(
        models.RecoveryCase.status == recovery_state.RECOVERED
    ).group_by(
        models.Customer.risk_segment
    ).all()

    return [
        {"name": segment, "count": int(count or 0), "value": float(amount or 0)}
        for segment, count, amount in results
    ]


@router.get("/summary", response_model=Dict)
def get_analytics_summary(db: Session = Depends(get_db)):
    total_cases = db.query(func.count(models.RecoveryCase.id)).scalar() or 0
    recovered = db.query(func.count(models.RecoveryCase.id)).filter(
        models.RecoveryCase.status == recovery_state.RECOVERED
    ).scalar() or 0
    escalated = db.query(func.count(models.RecoveryCase.id)).filter(
        models.RecoveryCase.status == recovery_state.ESCALATED
    ).scalar() or 0
    promises = db.query(func.count(models.PromiseToPay.id)).filter(
        models.PromiseToPay.status == "ACTIVE"
    ).scalar() or 0
    fulfilled = db.query(func.count(models.PromiseToPay.id)).filter(
        models.PromiseToPay.status == "FULFILLED"
    ).scalar() or 0
    total_recovered = db.query(func.sum(models.RecoveryCase.recovered_amount)).filter(
        models.RecoveryCase.status == recovery_state.RECOVERED
    ).scalar() or 0.0
    policy_blocks = db.query(func.count(models.PolicyDecision.id)).filter(
        models.PolicyDecision.allowed.is_(False)
    ).scalar() or 0

    return {
        "total_cases": total_cases,
        "recovered_cases": recovered,
        "escalated_cases": escalated,
        "promises_to_pay": promises,
        "promises_fulfilled": fulfilled,
        "total_recovered": float(total_recovered),
        "policy_block_rate": round(policy_blocks / max(total_cases, 1) * 100, 1),
        "escalation_rate": round(escalated / max(total_cases, 1) * 100, 1),
        "promise_fulfillment_rate": round(fulfilled / max(promises, 1) * 100, 1),
    }
