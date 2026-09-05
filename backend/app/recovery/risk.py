from app.core.constants import (
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    RISK_CRITICAL,
    RISK_HIGH,
    RISK_LOW,
    RISK_MEDIUM,
)
from app.ml.features import FAILURE_RECOVERABILITY, clamp

EXPECTED_REFERENCE = 25000.0
LTV_REFERENCE = 200000.0
AMOUNT_REFERENCE = 50000.0


def time_sensitivity(hours_since_failure: float) -> float:
    return clamp(1 - hours_since_failure / 72)


def risk_score(
    amount: float,
    failure_type: str,
    attempt_count: int,
    failed_ratio: float,
    hours_since_failure: float,
) -> float:
    recoverability = FAILURE_RECOVERABILITY.get(failure_type, 0.5)
    score = (
        0.35 * clamp(amount / AMOUNT_REFERENCE)
        + 0.25 * (1 - recoverability)
        + 0.15 * clamp(attempt_count / 3)
        + 0.15 * clamp(failed_ratio)
        + 0.10 * clamp(hours_since_failure / 72)
    )
    return round(clamp(score) * 100, 2)


def risk_level(score: float) -> str:
    if score >= 70:
        return RISK_CRITICAL
    if score >= 50:
        return RISK_HIGH
    if score >= 30:
        return RISK_MEDIUM
    return RISK_LOW


def relationship_risk(
    contacts_in_window: int,
    unanswered_contacts: int,
    complaints: int,
    responded_contacts: int,
    opted_out: bool,
    has_active_promise: bool,
) -> float:
    score = (
        0.10 * contacts_in_window
        + 0.09 * unanswered_contacts
        + 0.18 * complaints
        - 0.07 * responded_contacts
        + (0.35 if opted_out else 0)
        - (0.12 if has_active_promise else 0)
    )
    return round(clamp(score), 4)


def priority_score(
    expected: float,
    probability: float,
    lifetime_value: float,
    hours_since_failure: float,
    relationship: float,
) -> float:
    score = (
        0.45 * clamp(expected / EXPECTED_REFERENCE)
        + 0.25 * clamp(probability)
        + 0.15 * clamp(lifetime_value / LTV_REFERENCE)
        + 0.15 * time_sensitivity(hours_since_failure)
        - 0.10 * clamp(relationship)
    )
    return round(clamp(score), 4)


def priority(score: float) -> str:
    if score >= 0.62:
        return PRIORITY_CRITICAL
    if score >= 0.45:
        return PRIORITY_HIGH
    if score >= 0.28:
        return PRIORITY_MEDIUM
    return PRIORITY_LOW
