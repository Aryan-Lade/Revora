from app.core.constants import (
    EVENT_GATEWAY_FALLBACK,
    GATEWAY_HEALTHY,
    GATEWAY_UNAVAILABLE,
)
from app.database.models import AuditLog
from app.gateway import pool
from app.razorpay import payments
from app.razorpay.client import GATEWAY_TIMEOUT
from tests.conftest import SUCCESS, ScriptedClient


def test_gateway_selection_skips_unavailable_provider(db):
    providers = pool.ensure_providers(db)
    primary = providers[0]
    secondary = providers[1]

    primary.status = GATEWAY_UNAVAILABLE
    secondary.status = GATEWAY_HEALTHY
    db.flush()

    selected = pool.select_provider(db)
    assert selected is not None
    assert selected.name == secondary.name


def test_gateway_fallback_on_failure(db, case):
    providers = pool.ensure_providers(db)
    providers[0].status = GATEWAY_HEALTHY
    providers[1].status = GATEWAY_HEALTHY
    db.flush()

    client = ScriptedClient(
        (False, GATEWAY_TIMEOUT, "Gateway timeout"),
        SUCCESS,
    )
    response = payments.retry(db, case, client=client)

    assert response["success"] is True
    assert response["gateway"] == "razorpay_secondary"
    assert client.calls == ["razorpay_primary", "razorpay_secondary"]

    fallback_logs = db.query(AuditLog).filter(
        AuditLog.recovery_case_id == case.id,
        AuditLog.event == EVENT_GATEWAY_FALLBACK,
    ).count()
    assert fallback_logs == 1
