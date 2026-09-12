import pytest
from app.core.errors import InvalidTransition
from app.state import payment_state, recovery_state, voice_state


def test_valid_recovery_state_transitions():
    assert recovery_state.transition(recovery_state.DETECTED, recovery_state.ANALYZING) == recovery_state.ANALYZING
    assert recovery_state.transition(recovery_state.ANALYZING, recovery_state.RECOMMENDED) == recovery_state.RECOMMENDED
    assert recovery_state.transition(recovery_state.RECOMMENDED, recovery_state.POLICY_CHECK) == recovery_state.POLICY_CHECK
    assert recovery_state.transition(recovery_state.POLICY_CHECK, recovery_state.APPROVED) == recovery_state.APPROVED
    assert recovery_state.transition(recovery_state.APPROVED, recovery_state.PROCESSING) == recovery_state.PROCESSING
    assert recovery_state.transition(recovery_state.PROCESSING, recovery_state.CONTACTED) == recovery_state.CONTACTED
    assert recovery_state.transition(recovery_state.CONTACTED, recovery_state.PROMISE_TO_PAY) == recovery_state.PROMISE_TO_PAY
    assert recovery_state.transition(recovery_state.PROMISE_TO_PAY, recovery_state.RECOVERED) == recovery_state.RECOVERED


def test_invalid_recovery_state_transitions_raise_error():
    with pytest.raises(InvalidTransition):
        recovery_state.transition(recovery_state.DETECTED, recovery_state.RECOVERED)
    with pytest.raises(InvalidTransition):
        recovery_state.transition(recovery_state.RECOVERED, recovery_state.ANALYZING)


def test_payment_state_machine():
    assert payment_state.transition(payment_state.PENDING, payment_state.FAILED) == payment_state.FAILED
    assert payment_state.transition(payment_state.FAILED, payment_state.RETRYING) == payment_state.RETRYING
    assert payment_state.transition(payment_state.RETRYING, payment_state.RECOVERED) == payment_state.RECOVERED
    with pytest.raises(InvalidTransition):
        payment_state.transition(payment_state.RECOVERED, payment_state.PENDING)


def test_voice_state_machine():
    assert voice_state.transition(voice_state.INITIATED, voice_state.RINGING) == voice_state.RINGING
    assert voice_state.transition(voice_state.RINGING, voice_state.CONNECTED) == voice_state.CONNECTED
    assert voice_state.transition(voice_state.CONNECTED, voice_state.IDENTIFIED) == voice_state.IDENTIFIED
    assert voice_state.transition(voice_state.IDENTIFIED, voice_state.PAYMENT_CONTEXT_SHARED) == voice_state.PAYMENT_CONTEXT_SHARED
    assert voice_state.transition(voice_state.PAYMENT_CONTEXT_SHARED, voice_state.CUSTOMER_RESPONDING) == voice_state.CUSTOMER_RESPONDING
    assert voice_state.transition(voice_state.CUSTOMER_RESPONDING, voice_state.PROMISE_TO_PAY) == voice_state.PROMISE_TO_PAY
    assert voice_state.transition(voice_state.PROMISE_TO_PAY, voice_state.CALL_ENDED) == voice_state.CALL_ENDED
