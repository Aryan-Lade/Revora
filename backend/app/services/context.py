from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import hours_between, start_of_ist_day, utcnow
from app.core.config import settings
from app.core.constants import (
    ATTEMPT_OPEN,
    DIRECTION_OUTBOUND,
    EMAIL,
    FAILURE_LABELS,
    IN_APP,
    PROMISE_ACTIVE,
    SMS,
    VOICE_AI,
)
from app.core.money import rupees
from app.database.models import (
    Communication,
    PromiseToPay,
    RecoveryAttempt,
    VoiceSession,
)
from app.ml import model
from app.policy.engine import policy_engine
from app.services import scoring
from app.state import payment_state, recovery_state

SETTLED_PAYMENTS = {
    payment_state.CAPTURED,
    payment_state.RECOVERED,
    payment_state.REFUNDED,
    payment_state.CANCELLED,
}
PHONE_CHANNELS = {SMS, VOICE_AI}


def active_promise(db: Session, customer_id: int, now: datetime) -> PromiseToPay | None:
    query = (
        select(PromiseToPay)
        .where(
            PromiseToPay.customer_id == customer_id,
            PromiseToPay.status == PROMISE_ACTIVE,
            PromiseToPay.promised_date >= now,
        )
        .order_by(PromiseToPay.promised_date)
        .limit(1)
    )
    return db.scalar(query)


def contact_history(db: Session, customer_id: int, now: datetime, promise=None) -> dict:
    window_start = now - timedelta(hours=settings.recovery_window_hours)
    day_start = start_of_ist_day(now)
    outbound = (
        select(func.count())
        .select_from(Communication)
        .where(
            Communication.customer_id == customer_id,
            Communication.direction == DIRECTION_OUTBOUND,
        )
    )

    def count(*conditions) -> int:
        return int(db.scalar(outbound.where(*conditions)) or 0)

    def today(channel: str) -> int:
        return count(Communication.sent_at >= day_start, Communication.channel == channel)

    voice_today = int(
        db.scalar(
            select(func.count())
            .select_from(VoiceSession)
            .where(VoiceSession.customer_id == customer_id, VoiceSession.started_at >= day_start)
        )
        or 0
    )
    last_contact_at = db.scalar(
        select(func.max(Communication.sent_at)).where(
            Communication.customer_id == customer_id,
            Communication.direction == DIRECTION_OUTBOUND,
        )
    )
    return {
        "contacts_in_window": count(Communication.sent_at >= window_start),
        "contacts_total": count(),
        "emails_today": today(EMAIL),
        "sms_today": today(SMS),
        "in_app_today": today(IN_APP),
        "voice_calls_today": voice_today,
        "responded_contacts": count(Communication.responded.is_(True)),
        "unanswered_contacts": count(
            Communication.responded.is_(False), Communication.sent_at >= window_start
        ),
        "last_contact_at": last_contact_at,
        "has_active_promise": promise is not None,
    }


def customer_section(customer) -> dict:
    return {
        "id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "lifetime_value": rupees(customer.lifetime_value),
        "total_spent": rupees(customer.total_spent),
        "successful_payments": customer.successful_payments,
        "failed_payments": customer.failed_payments,
        "successful_ratio": round(customer.successful_ratio, 4),
        "failed_ratio": round(customer.failed_ratio, 4),
        "recoveries_succeeded": customer.recoveries_succeeded,
        "recoveries_failed": customer.recoveries_failed,
        "complaints": customer.complaints,
        "engagement_score": round(float(customer.engagement_score), 4),
        "preferred_channel": customer.preferred_channel,
        "email_opt_in": customer.email_opt_in,
        "sms_opt_in": customer.sms_opt_in,
        "voice_opt_in": customer.voice_opt_in,
        "opted_out": customer.opted_out,
        "quiet_hours_start": customer.quiet_hours_start,
        "quiet_hours_end": customer.quiet_hours_end,
        "risk_segment": customer.risk_segment,
    }


def payment_section(payment) -> dict:
    return {
        "id": payment.id,
        "razorpay_payment_id": payment.razorpay_payment_id,
        "amount": rupees(payment.amount),
        "currency": payment.currency,
        "status": payment.status,
        "settled": payment.status in SETTLED_PAYMENTS,
        "method": payment.method,
        "failure_reason": payment.failure_reason,
        "failure_code": payment.failure_code,
        "attempt_number": payment.attempt_number,
        "created_at": payment.created_at,
    }


def subscription_section(subscription, now: datetime) -> dict | None:
    if subscription is None:
        return None
    return {
        "id": subscription.id,
        "external_id": subscription.external_id,
        "plan_name": subscription.plan_name,
        "amount": rupees(subscription.amount),
        "billing_cycle": subscription.billing_cycle,
        "status": subscription.status,
        "failed_attempts": subscription.failed_attempts,
        "age_days": round(scoring.subscription_age_days(subscription, now), 1),
        "next_billing_at": subscription.next_billing_at,
    }


def case_section(case, scores: dict) -> dict:
    return {
        "id": case.id,
        "reference": case.reference,
        "amount_at_risk": rupees(case.amount_at_risk),
        "failure_type": case.failure_type,
        "failure_label": FAILURE_LABELS.get(case.failure_type, case.failure_type),
        "status": case.status,
        "resolved": recovery_state.is_terminal(case.status),
        "attempt_count": case.attempt_count,
        "contact_count": case.contact_count,
        "risk_score": scores["risk_score"],
        "risk_level": scores["risk_level"],
        "relationship_risk": scores["relationship_risk"],
        "priority": scores["priority"],
        "recovery_probability": scores["recovery_probability"],
        "expected_recovery": scores["expected_recovery"],
        "hours_since_failure": scores["hours_since_failure"],
        "next_action_at": case.next_action_at,
        "detected_at": case.detected_at,
    }


def guardrail_section() -> dict:
    return {
        "max_automated_amount": settings.max_automated_amount,
        "max_retry_attempts": settings.max_retry_attempts,
        "min_ai_confidence": settings.min_ai_confidence,
        "recovery_window_hours": settings.recovery_window_hours,
        "max_contacts_per_window": settings.max_contacts_per_window,
        "quiet_hours_start": settings.quiet_hours_start,
        "quiet_hours_end": settings.quiet_hours_end,
    }


def promise_section(promise) -> dict | None:
    if promise is None:
        return None
    return {
        "id": promise.id,
        "amount": rupees(promise.amount),
        "promised_date": promise.promised_date,
        "channel": promise.channel,
        "status": promise.status,
        "source_quote": promise.source_quote,
    }


def open_attempt_exists(db: Session, case_id: int) -> bool:
    query = (
        select(func.count())
        .select_from(RecoveryAttempt)
        .where(
            RecoveryAttempt.recovery_case_id == case_id,
            RecoveryAttempt.status.in_(ATTEMPT_OPEN),
        )
    )
    return bool(db.scalar(query))


def ml_section(scores: dict) -> dict:
    metrics = model.metrics()
    return {
        "recovery_probability": scores["recovery_probability"],
        "features": scores["features"],
        "model": {
            "name": metrics["model_name"],
            "accuracy": metrics["accuracy"],
            "roc_auc": metrics["roc_auc"],
            "training_samples": metrics["training_samples"],
        },
    }


def eligible_channels(context: dict, now: datetime) -> list[str]:
    channels = policy_engine.available_channels(context, now)
    if not context["customer"]["phone"]:
        channels = [channel for channel in channels if channel not in PHONE_CHANNELS]
    return channels


def build(db: Session, case, now: datetime | None = None) -> dict:
    now = now or utcnow()
    customer = case.customer
    payment = case.payment
    subscription = case.subscription
    promise = active_promise(db, customer.id, now)
    contact = contact_history(db, customer.id, now, promise)
    scores = scoring.evaluate(case, customer, payment, subscription, contact, now)
    context = {
        "generated_at": now,
        "case": case_section(case, scores),
        "customer": customer_section(customer),
        "payment": payment_section(payment),
        "subscription": subscription_section(subscription, now),
        "contact_history": contact,
        "promise_to_pay": promise_section(promise),
        "ml": ml_section(scores),
        "guardrails": guardrail_section(),
        "pending_action_exists": open_attempt_exists(db, case.id),
        "scores": scores,
    }
    context["available_channels"] = eligible_channels(context, now)
    return context
