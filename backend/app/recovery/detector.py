from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import hours_between, utcnow
from app.core.constants import (
    ACTOR_DETECTOR,
    EVENT_PAYMENT_DETECTED,
    EVENT_RISK_SCORED,
)
from app.core.money import rupees
from app.database.models import Payment, RecoveryCase
from app.services import audit, context, scoring
from app.state import payment_state, recovery_state

ABANDONED_AFTER_HOURS = 2.0
OVERDUE_AFTER_HOURS = 24.0

CODE_FAILURES = {
    "GATEWAY_TIMEOUT": "TEMPORARY_BANK_TIMEOUT",
    "GATEWAY_ERROR": "GATEWAY_FAILURE",
    "SERVER_ERROR": "GATEWAY_FAILURE",
    "BAD_REQUEST_ERROR": "INSUFFICIENT_FUNDS",
}
REASON_FAILURES = {
    "timeout": "TEMPORARY_BANK_TIMEOUT",
    "insufficient": "INSUFFICIENT_FUNDS",
    "balance": "INSUFFICIENT_FUNDS",
    "expired": "CARD_EXPIRED",
    "authentication": "AUTHENTICATION_FAILURE",
    "otp": "AUTHENTICATION_FAILURE",
    "3dsecure": "AUTHENTICATION_FAILURE",
    "mandate": "RECURRING_MANDATE_FAILURE",
    "gateway": "GATEWAY_FAILURE",
}


def classify(payment: Payment, now: datetime) -> str:
    reason = (payment.failure_reason or "").lower()
    for token, failure_type in REASON_FAILURES.items():
        if token in reason:
            return failure_type
    if payment.status == payment_state.PENDING:
        age = hours_between(now, payment.created_at)
        if payment.subscription_id and age >= OVERDUE_AFTER_HOURS:
            return "OVERDUE_INVOICE"
        return "CHECKOUT_ABANDONED"
    if payment.subscription_id and payment.method == "emandate":
        return "RECURRING_MANDATE_FAILURE"
    return CODE_FAILURES.get(payment.failure_code or "", "GATEWAY_FAILURE")


def reference_for(payment: Payment, now: datetime) -> str:
    return f"RC-{now:%y%m}-{payment.id:04d}"


def case_for(db: Session, payment_id: int) -> RecoveryCase | None:
    return db.scalar(select(RecoveryCase).where(RecoveryCase.payment_id == payment_id))


def is_at_risk(payment: Payment, now: datetime) -> bool:
    if payment.status == payment_state.FAILED:
        return True
    if payment.status == payment_state.PENDING:
        return hours_between(now, payment.created_at) >= ABANDONED_AFTER_HOURS
    return False


def at_risk_payments(db: Session, now: datetime) -> list[Payment]:
    query = (
        select(Payment)
        .where(Payment.status.in_([payment_state.FAILED, payment_state.PENDING]))
        .order_by(Payment.created_at.desc())
    )
    return [payment for payment in db.scalars(query) if is_at_risk(payment, now)]


def score(db: Session, case: RecoveryCase, now: datetime) -> dict:
    customer = case.customer
    promise = context.active_promise(db, customer.id, now)
    contact = context.contact_history(db, customer.id, now, promise)
    scores = scoring.evaluate(case, customer, case.payment, case.subscription, contact, now)
    scoring.apply(case, scores)
    db.flush()
    return scores


def open_case(db: Session, payment: Payment, now: datetime | None = None) -> RecoveryCase:
    now = now or utcnow()
    existing = case_for(db, payment.id)
    if existing:
        return existing
    case = RecoveryCase(
        reference=reference_for(payment, now),
        customer_id=payment.customer_id,
        payment_id=payment.id,
        subscription_id=payment.subscription_id,
        amount_at_risk=rupees(payment.amount),
        failure_type=classify(payment, now),
        status=recovery_state.DETECTED,
        detected_at=now,
    )
    db.add(case)
    db.flush()
    scores = score(db, case, now)
    audit.record(
        db,
        EVENT_PAYMENT_DETECTED,
        ACTOR_DETECTOR,
        case_id=case.id,
        action=case.failure_type,
        reason=f"Rs {float(case.amount_at_risk):,.0f} at risk on {payment.razorpay_payment_id}",
        meta={
            "payment_id": payment.id,
            "payment_status": payment.status,
            "failure_type": case.failure_type,
            "amount_at_risk": rupees(case.amount_at_risk),
        },
    )
    audit.record(
        db,
        EVENT_RISK_SCORED,
        ACTOR_DETECTOR,
        case_id=case.id,
        action=case.risk_level,
        reason=(
            f"Risk {scores['risk_score']:.0f} ({case.risk_level}), "
            f"recovery probability {scores['recovery_probability']:.0%}, "
            f"priority {case.priority}"
        ),
        meta={
            "risk_score": scores["risk_score"],
            "risk_level": scores["risk_level"],
            "recovery_probability": scores["recovery_probability"],
            "expected_recovery": scores["expected_recovery"],
            "priority": scores["priority"],
            "priority_score": scores["priority_score"],
        },
    )
    return case


def scan(db: Session, now: datetime | None = None) -> dict:
    now = now or utcnow()
    opened: list[RecoveryCase] = []
    skipped = 0
    for payment in at_risk_payments(db, now):
        if case_for(db, payment.id):
            skipped += 1
            continue
        opened.append(open_case(db, payment, now))
    return {
        "detected": len(opened),
        "skipped": skipped,
        "amount_at_risk": rupees(sum(float(case.amount_at_risk) for case in opened)),
        "expected_recovery": rupees(sum(float(case.expected_recovery) for case in opened)),
        "references": [case.reference for case in opened],
    }


def handle_failed_payment_webhook(payload: dict, db: Session) -> None:
    data = payload.get("payload", {}).get("payment", {}).get("entity", {})
    payment_id = data.get("id")
    if not payment_id:
        return
    payment = db.scalar(select(Payment).where(Payment.razorpay_payment_id == payment_id))
    if payment is None:
        return
    now = utcnow()
    payment.status = payment_state.FAILED
    payment.failure_reason = data.get("error_description", "")
    payment.failure_code = data.get("error_code", "")
    db.flush()
    open_case(db, payment, now)
    db.commit()


def handle_successful_payment_webhook(payload: dict, db: Session) -> None:
    data = payload.get("payload", {}).get("payment", {}).get("entity", {})
    payment_id = data.get("id")
    if not payment_id:
        return
    payment = db.scalar(select(Payment).where(Payment.razorpay_payment_id == payment_id))
    if payment is None:
        return
    payment.status = payment_state.CAPTURED
    payment.failure_reason = None
    payment.failure_code = None
    db.flush()
    recovery_case = case_for(db, payment.id)
    if recovery_case and recovery_case.status not in {recovery_state.RECOVERED, recovery_state.STOPPED}:
        from app.recovery.executor import mark_recovered
        mark_recovered(db, recovery_case, float(payment.amount), "razorpay_webhook",
                       f"Payment {payment_id} captured via Razorpay webhook")
    db.commit()
