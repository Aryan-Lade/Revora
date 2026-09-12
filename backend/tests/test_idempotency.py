from app.core.constants import EVENT_IDEMPOTENT_REPLAY, EVENT_PAYMENT_RETRIED
from app.database.models import AuditLog
from app.razorpay import payments
from app.razorpay.client import DemoRazorpayClient
from tests.conftest import SUCCESS, ScriptedClient


def test_payment_retry_idempotency(db, case):
    client = ScriptedClient(SUCCESS)
    first = payments.retry(db, case, client=client, key="idem-retry-1")
    second = payments.retry(db, case, client=client, key="idem-retry-1")

    assert second == first
    assert client.calls == ["razorpay_primary"]
    assert case.payment.attempt_number == 2

    retried_events = db.query(AuditLog).filter(
        AuditLog.recovery_case_id == case.id,
        AuditLog.event == EVENT_PAYMENT_RETRIED,
    ).count()
    assert retried_events == 1

    replay_events = db.query(AuditLog).filter(
        AuditLog.recovery_case_id == case.id,
        AuditLog.event == EVENT_IDEMPOTENT_REPLAY,
    ).count()
    assert replay_events == 1


def test_payment_link_idempotency(db, case):
    client = DemoRazorpayClient()
    first = payments.create_link(db, case, client=client, key="idem-link-1")
    second = payments.create_link(db, case, client=client, key="idem-link-1")

    assert second == first
    assert first["link"]["short_url"] == second["link"]["short_url"]

    replay_events = db.query(AuditLog).filter(
        AuditLog.recovery_case_id == case.id,
        AuditLog.event == EVENT_IDEMPOTENT_REPLAY,
    ).count()
    assert replay_events == 1
