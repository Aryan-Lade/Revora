from datetime import datetime, timedelta
import calendar
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict

from app.core.clock import utcnow
from app.database.database import get_db
from app.database import models
from app.core.constants import PROMISE_ACTIVE
from app.state import recovery_state

router = APIRouter()


@router.get("/overview", response_model=Dict)
def get_dashboard_overview(db: Session = Depends(get_db)):
    active_statuses = [
        recovery_state.DETECTED,
        recovery_state.ANALYZING,
        recovery_state.RECOMMENDED,
        recovery_state.POLICY_CHECK,
        recovery_state.WAITING,
        recovery_state.APPROVED,
        recovery_state.PROCESSING,
        recovery_state.CONTACTED,
        recovery_state.PAYMENT_PENDING,
        recovery_state.PROMISE_TO_PAY,
    ]

    revenue_at_risk = db.query(func.sum(models.RecoveryCase.amount_at_risk)).filter(
        models.RecoveryCase.status.in_(active_statuses)
    ).scalar() or 0.0

    expected_recoverable = db.query(
        func.sum(models.RecoveryCase.amount_at_risk * models.RecoveryCase.recovery_probability)
    ).filter(
        models.RecoveryCase.status.in_(active_statuses)
    ).scalar() or 0.0

    recovered_revenue = db.query(func.sum(models.RecoveryCase.recovered_amount)).filter(
        models.RecoveryCase.status == recovery_state.RECOVERED
    ).scalar() or 0.0

    total_recoverable = recovered_revenue + revenue_at_risk
    recovery_rate = (recovered_revenue / total_recoverable * 100) if total_recoverable > 0 else 0.0

    active_cases = db.query(func.count(models.RecoveryCase.id)).filter(
        models.RecoveryCase.status.in_(active_statuses)
    ).scalar() or 0

    escalated_cases = db.query(func.count(models.RecoveryCase.id)).filter(
        models.RecoveryCase.status == recovery_state.ESCALATED
    ).scalar() or 0

    policy_blocks = db.query(func.count(models.PolicyDecision.id)).filter(
        models.PolicyDecision.allowed.is_(False)
    ).scalar() or db.query(func.count(models.AuditLog.id)).filter(
        models.AuditLog.event == "POLICY_BLOCKED"
    ).scalar() or 0

    promises_to_pay = db.query(func.count(models.PromiseToPay.id)).filter(
        models.PromiseToPay.status == PROMISE_ACTIVE
    ).scalar() or 0

    return {
        "revenue_at_risk": round(revenue_at_risk, 2),
        "expected_recoverable": round(expected_recoverable, 2),
        "recovered_revenue": round(recovered_revenue, 2),
        "recovery_rate": round(recovery_rate, 2),
        "active_cases": active_cases,
        "escalated_cases": escalated_cases,
        "policy_blocks": policy_blocks,
        "promises_to_pay": promises_to_pay,
    }


@router.get("/revenue", response_model=Dict)
def get_dashboard_revenue(db: Session = Depends(get_db)):
    active_statuses = [
        recovery_state.DETECTED,
        recovery_state.ANALYZING,
        recovery_state.RECOMMENDED,
        recovery_state.POLICY_CHECK,
        recovery_state.WAITING,
        recovery_state.APPROVED,
        recovery_state.PROCESSING,
        recovery_state.CONTACTED,
        recovery_state.PAYMENT_PENDING,
        recovery_state.PROMISE_TO_PAY,
    ]

    revenue_at_risk = db.query(func.sum(models.RecoveryCase.amount_at_risk)).filter(
        models.RecoveryCase.status.in_(active_statuses)
    ).scalar() or 0.0

    expected_recoverable = db.query(
        func.sum(models.RecoveryCase.amount_at_risk * models.RecoveryCase.recovery_probability)
    ).filter(
        models.RecoveryCase.status.in_(active_statuses)
    ).scalar() or 0.0

    eligible = db.query(func.sum(models.RecoveryCase.amount_at_risk)).filter(
        models.RecoveryCase.status.in_([
            recovery_state.APPROVED,
            recovery_state.PROCESSING,
        ])
    ).scalar() or 0.0

    intervention = db.query(func.sum(models.RecoveryCase.amount_at_risk)).filter(
        models.RecoveryCase.contact_count > 0,
        models.RecoveryCase.status.not_in([
            recovery_state.RECOVERED,
            recovery_state.FAILED,
            recovery_state.STOPPED,
            recovery_state.ESCALATED,
        ])
    ).scalar() or 0.0

    recovered = db.query(func.sum(models.RecoveryCase.recovered_amount)).filter(
        models.RecoveryCase.status == recovery_state.RECOVERED
    ).scalar() or 0.0

    return {
        "revenue_at_risk": round(revenue_at_risk, 2),
        "expected_recoverable": round(expected_recoverable, 2),
        "eligible": round(eligible, 2),
        "intervention": round(intervention, 2),
        "recovered": round(recovered, 2),
    }


@router.get("/trends", response_model=Dict)
def get_dashboard_trends(db: Session = Depends(get_db)):
    end_date = utcnow()
    labels = []
    monthly_recovered = []
    monthly_expected = []

    for i in range(5, -1, -1):
        m = end_date.month - i
        y = end_date.year
        while m <= 0:
            m += 12
            y -= 1
        label = f"{calendar.month_abbr[m]} {y}"
        labels.append(label)

        cases = (
            db.query(models.RecoveryCase)
            .filter(
                func.extract("month", models.RecoveryCase.created_at) == m,
                func.extract("year", models.RecoveryCase.created_at) == y,
            )
            .all()
        )
        rec = sum(float(c.recovered_amount or 0) for c in cases)
        exp = sum(float(c.expected_recovery or 0) for c in cases)
        monthly_recovered.append(round(rec, 2))
        monthly_expected.append(round(exp, 2))

    if sum(monthly_recovered) == 0 and sum(monthly_expected) == 0:
        total_rec = db.query(func.sum(models.RecoveryCase.recovered_amount)).scalar() or 0.0
        total_exp = db.query(func.sum(models.RecoveryCase.expected_recovery)).scalar() or 0.0
        monthly_recovered[-1] = round(float(total_rec), 2)
        monthly_expected[-1] = round(float(total_exp), 2)

    return {
        "monthly": {
            "labels": labels,
            "recovered": monthly_recovered,
            "expected": monthly_expected,
        }
    }