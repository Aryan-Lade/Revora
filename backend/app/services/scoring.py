from datetime import datetime

from app.core.clock import hours_between, utcnow
from app.core.money import expected_recovery, rupees
from app.ml import model
from app.ml.features import build_features, features_dict
from app.recovery.risk import (
    priority,
    priority_score,
    relationship_risk,
    risk_level,
    risk_score,
)


def subscription_age_days(subscription, now: datetime) -> float:
    if subscription is None or subscription.started_at is None:
        return 0.0
    return max(hours_between(now, subscription.started_at) / 24, 0.0)


def feature_vector(case, customer, payment, subscription, now: datetime) -> list[float]:
    hours = max(hours_between(now, case.detected_at), 0.0)
    return build_features(
        amount=float(case.amount_at_risk),
        lifetime_value=float(customer.lifetime_value),
        successful_payments=customer.successful_payments,
        failed_payments=customer.failed_payments,
        recoveries_succeeded=customer.recoveries_succeeded,
        recoveries_failed=customer.recoveries_failed,
        attempt_number=case.attempt_count + 1,
        days_since_failure=hours / 24,
        failure_type=case.failure_type,
        method=payment.method,
        subscription_age_days=subscription_age_days(subscription, now),
        engagement=float(customer.engagement_score),
    )


def evaluate(case, customer, payment, subscription, contact: dict, now: datetime | None = None) -> dict:
    now = now or utcnow()
    hours = max(hours_between(now, case.detected_at), 0.0)
    vector = feature_vector(case, customer, payment, subscription, now)
    probability = model.predict(vector)
    amount = float(case.amount_at_risk)
    expected = expected_recovery(amount, probability)
    risk = risk_score(
        amount=amount,
        failure_type=case.failure_type,
        attempt_count=case.attempt_count,
        failed_ratio=customer.failed_ratio,
        hours_since_failure=hours,
    )
    relationship = relationship_risk(
        contacts_in_window=contact["contacts_in_window"],
        unanswered_contacts=contact["unanswered_contacts"],
        complaints=customer.complaints,
        responded_contacts=contact["responded_contacts"],
        opted_out=customer.opted_out,
        has_active_promise=contact["has_active_promise"],
    )
    ranking = priority_score(
        expected=expected,
        probability=probability,
        lifetime_value=float(customer.lifetime_value),
        hours_since_failure=hours,
        relationship=relationship,
    )
    return {
        "hours_since_failure": round(hours, 2),
        "recovery_probability": probability,
        "expected_recovery": expected,
        "risk_score": risk,
        "risk_level": risk_level(risk),
        "relationship_risk": relationship,
        "priority_score": ranking,
        "priority": priority(ranking),
        "features": features_dict(vector),
    }


def apply(case, scores: dict) -> None:
    case.risk_score = scores["risk_score"]
    case.risk_level = scores["risk_level"]
    case.recovery_probability = scores["recovery_probability"]
    case.expected_recovery = rupees(scores["expected_recovery"])
    case.relationship_risk = scores["relationship_risk"]
    case.priority = scores["priority"]
