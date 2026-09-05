FEATURE_NAMES = [
    "amount",
    "lifetime_value",
    "successful_ratio",
    "failed_ratio",
    "previous_recovery_success",
    "previous_recovery_failures",
    "attempt_number",
    "days_since_failure",
    "failure_recoverability",
    "method_recoverability",
    "subscription_age",
    "engagement",
]

FAILURE_RECOVERABILITY = {
    "TEMPORARY_BANK_TIMEOUT": 0.95,
    "GATEWAY_FAILURE": 0.88,
    "AUTHENTICATION_FAILURE": 0.72,
    "RECURRING_MANDATE_FAILURE": 0.6,
    "CHECKOUT_ABANDONED": 0.55,
    "INSUFFICIENT_FUNDS": 0.45,
    "CARD_EXPIRED": 0.38,
    "OVERDUE_INVOICE": 0.3,
}

METHOD_RECOVERABILITY = {
    "upi": 0.9,
    "netbanking": 0.78,
    "card": 0.7,
    "wallet": 0.62,
    "emandate": 0.5,
}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def build_features(
    amount: float,
    lifetime_value: float,
    successful_payments: int,
    failed_payments: int,
    recoveries_succeeded: int,
    recoveries_failed: int,
    attempt_number: int,
    days_since_failure: float,
    failure_type: str,
    method: str,
    subscription_age_days: float,
    engagement: float,
) -> list[float]:
    total = successful_payments + failed_payments
    return [
        clamp(amount / 50000),
        clamp(lifetime_value / 200000),
        clamp(successful_payments / total) if total else 0.5,
        clamp(failed_payments / total) if total else 0.5,
        clamp(recoveries_succeeded / 5),
        clamp(recoveries_failed / 5),
        clamp((attempt_number - 1) / 3),
        clamp(days_since_failure / 7),
        FAILURE_RECOVERABILITY.get(failure_type, 0.5),
        METHOD_RECOVERABILITY.get(method, 0.65),
        clamp(subscription_age_days / 730),
        clamp(engagement),
    ]


def features_dict(vector: list[float]) -> dict:
    return dict(zip(FEATURE_NAMES, [round(value, 4) for value in vector]))
