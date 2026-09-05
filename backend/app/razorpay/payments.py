from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.constants import (
    ACTOR_EXECUTOR,
    ACTOR_GATEWAY,
    EVENT_GATEWAY_FALLBACK,
    EVENT_IDEMPOTENT_REPLAY,
    EVENT_PAYMENT_LINK_CREATED,
    EVENT_PAYMENT_RECOVERED,
    EVENT_PAYMENT_RETRIED,
    PAYMENT_LINK,
    PAYMENT_RETRY,
)
from app.core.errors import ProviderUnavailable
from app.core.money import rupees
from app.database.models import RecoveryCase
from app.gateway import pool
from app.razorpay.client import (
    LINK_TTL_HOURS,
    ChargeResult,
    RazorpayClient,
    get_razorpay_client,
)
from app.services import audit, idempotency
from app.state import payment_state

MAX_GATEWAY_ATTEMPTS = 2
RETRY_OPERATION = "payment_retry"
LINK_OPERATION = "payment_link"


@dataclass
class ChargeOutcome:
    result: ChargeResult
    gateway: str
    attempts: list[dict] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.result.success

    def as_dict(self) -> dict:
        return {**self.result.as_dict(), "gateway_attempts": self.attempts}


def success_state(current: str) -> str:
    for target in (payment_state.RECOVERED, payment_state.CAPTURED):
        if payment_state.can_transition(current, target):
            return target
    return current


def failure_state(current: str) -> str:
    if payment_state.can_transition(current, payment_state.FAILED):
        return payment_state.FAILED
    return current


def charge(db: Session, case: RecoveryCase, client: RazorpayClient | None = None) -> ChargeOutcome:
    client = client or get_razorpay_client()
    payment = case.payment
    probability = float(case.recovery_probability) if case.recovery_probability else None
    attempt_number = payment.attempt_number + 1
    tried: set[str] = set()
    attempts: list[dict] = []
    outcome: ChargeOutcome | None = None
    provider = pool.select_provider(db)
    while provider is not None:
        tried.add(provider.name)
        status_before = provider.status
        result = client.charge(
            payment_id=payment.razorpay_payment_id,
            amount=float(case.amount_at_risk),
            method=payment.method,
            failure_type=case.failure_type,
            attempt_number=attempt_number,
            gateway=provider.name,
            probability=probability,
        )
        if result.success:
            pool.record_success(db, provider, result.latency_ms)
        else:
            pool.record_failure(db, provider, result.latency_ms)
        attempts.append(
            {
                "gateway": provider.name,
                "gateway_status": status_before,
                "success": result.success,
                "latency_ms": result.latency_ms,
                "failure_code": result.failure_code,
            }
        )
        outcome = ChargeOutcome(result=result, gateway=provider.name, attempts=attempts)
        if result.success or not result.gateway_fault or len(tried) >= MAX_GATEWAY_ATTEMPTS:
            break
        fallback = pool.select_provider(db, exclude=tried)
        if fallback is None:
            break
        audit.record(
            db,
            EVENT_GATEWAY_FALLBACK,
            ACTOR_GATEWAY,
            case_id=case.id,
            action=result.failure_code or "",
            reason=f"{provider.label} returned {result.failure_reason}; retrying on {fallback.label}",
            meta={
                "from_gateway": provider.name,
                "to_gateway": fallback.name,
                "failure_code": result.failure_code,
                "latency_ms": result.latency_ms,
            },
        )
        provider = fallback
    if outcome is None:
        raise ProviderUnavailable("No payment gateway is available for this charge")
    return outcome


def settle(
    db: Session,
    case: RecoveryCase,
    amount: float,
    *,
    reason: str,
    action: str = "",
    reference: str = "",
    actor: str = ACTOR_EXECUTOR,
) -> dict:
    payment = case.payment
    payment.status = payment_state.transition(payment.status, success_state(payment.status))
    payment.failure_code = None
    payment.failure_reason = None
    db.flush()
    settled = rupees(amount)
    audit.record(
        db,
        EVENT_PAYMENT_RECOVERED,
        actor,
        case_id=case.id,
        action=action,
        reason=reason,
        meta={
            "payment_id": payment.id,
            "payment_status": payment.status,
            "amount": settled,
            "reference": reference,
        },
    )
    return {
        "success": True,
        "payment_id": payment.id,
        "payment_status": payment.status,
        "amount": settled,
        "reference": reference,
    }


def replayed(db: Session, key: str, action: str, actor: str, case_id: int) -> dict | None:
    record = idempotency.find(db, key)
    if record is None:
        return None
    audit.record(
        db,
        EVENT_IDEMPOTENT_REPLAY,
        actor,
        case_id=case_id,
        action=action,
        reason=f"Replayed {action} for idempotency key {key}",
        meta={"idempotency_key": key, "operation": record.operation},
    )
    return record.response


def retry(
    db: Session,
    case: RecoveryCase,
    *,
    client: RazorpayClient | None = None,
    key: str | None = None,
    actor: str = ACTOR_EXECUTOR,
) -> dict:
    payment = case.payment
    key = key or idempotency.build_key(RETRY_OPERATION, payment.id, payment.attempt_number + 1)
    replay = replayed(db, key, PAYMENT_RETRY, actor, case.id)
    if replay is not None:
        return replay
    if payment_state.can_transition(payment.status, payment_state.RETRYING):
        payment.status = payment_state.transition(payment.status, payment_state.RETRYING)
        db.flush()
    outcome = charge(db, case, client)
    amount = rupees(case.amount_at_risk)
    payment.attempt_number += 1
    if outcome.success:
        payment.status = payment_state.transition(payment.status, success_state(payment.status))
        payment.failure_code = None
        payment.failure_reason = None
    else:
        payment.status = payment_state.transition(payment.status, failure_state(payment.status))
        payment.failure_code = outcome.result.failure_code
        payment.failure_reason = outcome.result.failure_reason
    db.flush()
    response = {
        "action": PAYMENT_RETRY,
        "success": outcome.success,
        "payment_id": payment.id,
        "payment_status": payment.status,
        "attempt_number": payment.attempt_number,
        "amount": amount,
        "recovered_amount": amount if outcome.success else 0.0,
        "gateway": outcome.gateway,
        "charge": outcome.as_dict(),
        "idempotency_key": key,
    }
    verdict = "succeeded" if outcome.success else "failed"
    audit.record(
        db,
        EVENT_PAYMENT_RETRIED,
        actor,
        case_id=case.id,
        action=PAYMENT_RETRY,
        reason=f"Attempt {payment.attempt_number} for Rs {amount:,.0f} on {outcome.gateway} {verdict}",
        meta=response,
    )
    if outcome.success:
        audit.record(
            db,
            EVENT_PAYMENT_RECOVERED,
            actor,
            case_id=case.id,
            action=PAYMENT_RETRY,
            reason=f"Rs {amount:,.0f} recovered through {outcome.gateway}",
            meta={
                "gateway": outcome.gateway,
                "amount": amount,
                "reference": outcome.result.reference,
            },
        )
    idempotency.remember(db, key, RETRY_OPERATION, response)
    return response


def create_link(
    db: Session,
    case: RecoveryCase,
    *,
    description: str = "",
    client: RazorpayClient | None = None,
    key: str | None = None,
    actor: str = ACTOR_EXECUTOR,
    now: datetime | None = None,
) -> dict:
    now = now or utcnow()
    key = key or idempotency.build_key(LINK_OPERATION, case.id, case.attempt_count + 1)
    replay = replayed(db, key, PAYMENT_LINK, actor, case.id)
    if replay is not None:
        return replay
    client = client or get_razorpay_client()
    customer = case.customer
    payment = case.payment
    amount = rupees(case.amount_at_risk)
    expires_at = now + timedelta(hours=LINK_TTL_HOURS)
    link = client.create_link(
        reference=case.reference,
        amount=amount,
        description=description or f"Revora recovery for {payment.razorpay_payment_id}",
        customer={"name": customer.name, "email": customer.email, "phone": customer.phone},
        expires_at=expires_at,
    )
    response = {
        "action": PAYMENT_LINK,
        "success": True,
        "amount": amount,
        "link": link.as_dict(),
        "idempotency_key": key,
    }
    audit.record(
        db,
        EVENT_PAYMENT_LINK_CREATED,
        actor,
        case_id=case.id,
        action=PAYMENT_LINK,
        reason=f"Payment link for Rs {amount:,.0f} valid until {expires_at:%d %b %H:%M} UTC",
        meta=response,
    )
    idempotency.remember(db, key, LINK_OPERATION, response)
    return response
