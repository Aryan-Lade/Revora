import pytest

from app.core.config import settings
from app.core.constants import (
    EVENT_GATEWAY_FALLBACK,
    EVENT_IDEMPOTENT_REPLAY,
    EVENT_PAYMENT_LINK_CREATED,
    EVENT_PAYMENT_RECOVERED,
    EVENT_PAYMENT_RETRIED,
    GATEWAY_UNAVAILABLE,
)
from app.core.errors import ProviderUnavailable
from app.core.money import rupees
from app.gateway import pool
from app.razorpay import payments
from app.razorpay.client import (
    ATTEMPT_DECAY,
    BAD_REQUEST_ERROR,
    GATEWAY_TIMEOUT,
    MAX_LATENCY_MS,
    ChargeResult,
    DemoRazorpayClient,
    RazorpayClient,
    get_razorpay_client,
    success_odds,
)
from app.services import audit
from app.state import payment_state

SUCCESS = (True, None, None)


class ScriptedClient(RazorpayClient):
    name = "scripted"

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls: list[str] = []

    def charge(
        self,
        *,
        payment_id: str,
        amount: float,
        method: str,
        failure_type: str,
        attempt_number: int,
        gateway: str,
        probability: float | None = None,
    ) -> ChargeResult:
        self.calls.append(gateway)
        outcome = self.outcomes.pop(0) if self.outcomes else (False, BAD_REQUEST_ERROR, "Declined")
        success, code, reason = outcome
        return ChargeResult(
            success=success,
            amount=rupees(amount),
            provider=self.name,
            gateway=gateway,
            latency_ms=210,
            reference=f"pay_{gateway}_{attempt_number}",
            failure_code=code,
            failure_reason=reason,
        )


def events(db, case_id: int) -> list[str]:
    return [entry.event for entry in audit.timeline(db, case_id)]


def demo_charge(**overrides) -> ChargeResult:
    kwargs = {
        "payment_id": "pay_test_1",
        "amount": 4800.0,
        "method": "card",
        "failure_type": "CARD_EXPIRED",
        "attempt_number": 2,
        "gateway": "razorpay_primary",
    }
    return DemoRazorpayClient().charge(**{**kwargs, **overrides})


def test_demo_charge_is_deterministic():
    assert demo_charge(probability=0.6) == demo_charge(probability=0.6)
    assert demo_charge(attempt_number=1, probability=1.0).success is True
    declined = demo_charge(attempt_number=1, probability=0.0)
    assert declined.success is False
    assert declined.failure_code == BAD_REQUEST_ERROR
    assert declined.gateway_fault is False


def test_success_odds_fall_with_each_attempt():
    assert success_odds("TEMPORARY_BANK_TIMEOUT", "card", 1, 1.0) == 1.0
    assert success_odds("TEMPORARY_BANK_TIMEOUT", "card", 2, 1.0) == ATTEMPT_DECAY
    assert success_odds("CARD_EXPIRED", "card", 1) < success_odds("TEMPORARY_BANK_TIMEOUT", "card", 1)


def test_demo_charge_reports_gateway_faults():
    result = demo_charge(failure_type="TEMPORARY_BANK_TIMEOUT", probability=0.0)
    assert result.gateway_fault is True
    assert result.failure_code == GATEWAY_TIMEOUT
    assert result.latency_ms == MAX_LATENCY_MS


@pytest.mark.skipif(settings.live_razorpay, reason="live Razorpay credentials are configured")
def test_demo_client_is_used_without_live_credentials():
    assert get_razorpay_client().name == DemoRazorpayClient.name


def test_retry_recovers_a_failed_payment(db, case):
    response = payments.retry(db, case, client=ScriptedClient(SUCCESS))
    assert response["success"] is True
    assert response["payment_status"] == payment_state.RECOVERED
    assert response["attempt_number"] == 2
    assert response["recovered_amount"] == rupees(case.amount_at_risk)
    assert case.payment.status == payment_state.RECOVERED
    assert case.payment.failure_code is None
    assert EVENT_PAYMENT_RETRIED in events(db, case.id)
    assert EVENT_PAYMENT_RECOVERED in events(db, case.id)
    primary = pool.providers(db)[0]
    assert primary.success_count == 1
    assert primary.failure_count == 0


def test_retry_captures_an_abandoned_checkout(db, new_case):
    case = new_case(tag="abandoned", failure_type="CHECKOUT_ABANDONED", status=payment_state.PENDING)
    response = payments.retry(db, case, client=ScriptedClient(SUCCESS))
    assert response["payment_status"] == payment_state.CAPTURED
    assert case.payment.status == payment_state.CAPTURED


def test_retry_falls_back_to_the_next_gateway(db, case):
    client = ScriptedClient((False, GATEWAY_TIMEOUT, "Issuing bank did not respond in time"), SUCCESS)
    response = payments.retry(db, case, client=client)
    assert response["success"] is True
    assert response["gateway"] == "razorpay_secondary"
    assert client.calls == ["razorpay_primary", "razorpay_secondary"]
    assert len(response["charge"]["gateway_attempts"]) == 2
    assert EVENT_GATEWAY_FALLBACK in events(db, case.id)
    primary, secondary = pool.providers(db)[:2]
    assert primary.failure_count == 1
    assert secondary.success_count == 1


def test_customer_decline_does_not_fall_back(db, case):
    client = ScriptedClient((False, BAD_REQUEST_ERROR, "Insufficient balance in the customer account"))
    response = payments.retry(db, case, client=client)
    assert response["success"] is False
    assert response["recovered_amount"] == 0.0
    assert client.calls == ["razorpay_primary"]
    assert case.payment.status == payment_state.FAILED
    assert case.payment.failure_code == BAD_REQUEST_ERROR
    assert EVENT_GATEWAY_FALLBACK not in events(db, case.id)


def test_retry_replays_a_stored_response(db, case):
    client = ScriptedClient(SUCCESS)
    first = payments.retry(db, case, client=client, key="retry-case-1")
    second = payments.retry(db, case, client=client, key="retry-case-1")
    assert second == first
    assert client.calls == ["razorpay_primary"]
    assert case.payment.attempt_number == 2
    assert events(db, case.id).count(EVENT_PAYMENT_RETRIED) == 1
    assert EVENT_IDEMPOTENT_REPLAY in events(db, case.id)


def test_payment_link_is_recorded_and_replayed(db, case):
    client = DemoRazorpayClient()
    first = payments.create_link(db, case, client=client, key="link-case-1")
    assert first["link"]["id"].startswith("plink_")
    assert first["link"]["short_url"].startswith("https://rzp.io/i/")
    assert first["amount"] == rupees(case.amount_at_risk)
    assert first["link"]["reference"] == case.reference
    second = payments.create_link(db, case, client=client, key="link-case-1")
    assert second == first
    assert events(db, case.id).count(EVENT_PAYMENT_LINK_CREATED) == 1
    assert EVENT_IDEMPOTENT_REPLAY in events(db, case.id)


def test_charge_requires_an_available_gateway(db, case):
    for provider in pool.ensure_providers(db):
        provider.status = GATEWAY_UNAVAILABLE
    db.flush()
    with pytest.raises(ProviderUnavailable):
        payments.charge(db, case, ScriptedClient(SUCCESS))
