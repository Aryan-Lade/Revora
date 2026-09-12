from datetime import datetime, timedelta, timezone
from app.core.constants import EMAIL, VOICE_AI, PROMISE_ACTIVE
from app.database.models import PromiseToPay
from app.policy.engine import policy_engine
from app.services import context as context_service
from app.state import payment_state, recovery_state

DAYTIME = datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc)


def test_active_promise_to_pay_blocks_outreach(db, case):
    tomorrow = DAYTIME + timedelta(days=1)
    promise = PromiseToPay(
        customer_id=case.customer_id,
        recovery_case_id=case.id,
        amount=float(case.amount_at_risk),
        promised_date=tomorrow,
        channel=VOICE_AI,
        status=PROMISE_ACTIVE,
    )
    db.add(promise)
    db.flush()

    ctx = context_service.build(db, case, now=DAYTIME)
    result = policy_engine.evaluate(ctx, EMAIL, now=DAYTIME)
    assert result.allowed is False
    assert result.blocked_by == "promise_to_pay"


def test_quiet_hours_blocks_voice_contact(db, case):
    night_time = datetime(2026, 9, 12, 23, 30, tzinfo=timezone.utc)
    case.customer.quiet_hours_start = 22
    case.customer.quiet_hours_end = 8
    db.flush()

    ctx = context_service.build(db, case, now=night_time)
    result = policy_engine.evaluate(ctx, VOICE_AI, now=night_time)
    assert result.allowed is False
    assert result.blocked_by == "quiet_hours"


def test_customer_opt_out_blocks_all_outbound_contact(db, case):
    case.customer.opted_out = True
    db.flush()

    ctx = context_service.build(db, case, now=DAYTIME)
    result_email = policy_engine.evaluate(ctx, EMAIL, now=DAYTIME)
    result_voice = policy_engine.evaluate(ctx, VOICE_AI, now=DAYTIME)
    assert result_email.allowed is False
    assert result_email.blocked_by == "customer_opt_out"
    assert result_voice.allowed is False
    assert result_voice.blocked_by == "customer_opt_out"


def test_maximum_contacts_exceeded_blocks_outreach(db, case):
    from app.channels import messaging
    for _ in range(3):
        messaging.send(db, case, EMAIL, "Subject", "Message", now=DAYTIME)
    db.flush()

    ctx = context_service.build(db, case, now=DAYTIME)
    result = policy_engine.evaluate(ctx, EMAIL, now=DAYTIME)
    assert result.allowed is False
    assert result.blocked_by in {"contact_frequency", "channel_frequency"}


def test_payment_recovered_stops_outreach(db, case):
    case.payment.status = payment_state.RECOVERED
    case.status = recovery_state.RECOVERED
    db.flush()

    ctx = context_service.build(db, case, now=DAYTIME)
    result = policy_engine.evaluate(ctx, EMAIL, now=DAYTIME)
    assert result.allowed is False
    assert any(c.name in {"payment_state", "recovery_state"} and not c.passed for c in result.checks)


def test_channel_consent_withheld_blocks_channel(db, case):
    case.customer.voice_opt_in = False
    db.flush()

    ctx = context_service.build(db, case, now=DAYTIME)
    result = policy_engine.evaluate(ctx, VOICE_AI, now=DAYTIME)
    assert result.allowed is False
    assert result.blocked_by == "channel_opt_in"
