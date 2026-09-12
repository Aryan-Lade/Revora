from datetime import datetime, timedelta, timezone
from app.core.constants import EMAIL, PROMISE_ACTIVE, VOICE_AI
from app.database.models import PromiseToPay
from app.policy.engine import policy_engine
from app.services import context as context_service
from app.state import recovery_state
from app.voice import agent as voice_agent


def test_voice_call_during_quiet_hours_blocked(db, case):
    night_time = datetime(2026, 9, 12, 23, 30, tzinfo=timezone.utc)
    case.customer.quiet_hours_start = 22
    case.customer.quiet_hours_end = 8
    db.flush()

    ctx = context_service.build(db, case, now=night_time)
    policy_res = policy_engine.evaluate(ctx, VOICE_AI, now=night_time)
    assert policy_res.allowed is False
    assert policy_res.blocked_by == "quiet_hours"


def test_voice_call_outside_quiet_hours_allowed(db, case):
    day_time = datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc)
    ctx = context_service.build(db, case, now=day_time)
    policy_res = policy_engine.evaluate(ctx, VOICE_AI, now=day_time)
    assert policy_res.allowed is True


def test_promise_to_pay_blocks_future_outreach(db, case):
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    promise = PromiseToPay(
        customer_id=case.customer_id,
        recovery_case_id=case.id,
        amount=float(case.amount_at_risk),
        promised_date=tomorrow,
        channel=VOICE_AI,
        status=PROMISE_ACTIVE,
        source_quote="I will pay tomorrow.",
    )
    db.add(promise)
    case.status = recovery_state.PROMISE_TO_PAY
    db.flush()

    ctx = context_service.build(db, case)
    policy_res = policy_engine.evaluate(ctx, EMAIL)
    assert policy_res.allowed is False
    assert policy_res.blocked_by == "promise_to_pay"
