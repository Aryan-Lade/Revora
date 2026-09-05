from app.core.errors import InvalidTransition

INITIATED = "INITIATED"
RINGING = "RINGING"
CONNECTED = "CONNECTED"
IDENTIFIED = "IDENTIFIED"
PAYMENT_CONTEXT_SHARED = "PAYMENT_CONTEXT_SHARED"
CUSTOMER_RESPONDING = "CUSTOMER_RESPONDING"
PROMISE_TO_PAY = "PROMISE_TO_PAY"
PAYMENT_COMPLETED = "PAYMENT_COMPLETED"
DECLINED = "DECLINED"
CALL_ENDED = "CALL_ENDED"
FAILED = "FAILED"
ESCALATED = "ESCALATED"

TERMINAL = {PAYMENT_COMPLETED, DECLINED, CALL_ENDED, FAILED, ESCALATED}

TRANSITIONS = {
    INITIATED: {RINGING, FAILED},
    RINGING: {CONNECTED, FAILED, CALL_ENDED},
    CONNECTED: {IDENTIFIED, DECLINED, CALL_ENDED, FAILED},
    IDENTIFIED: {PAYMENT_CONTEXT_SHARED, DECLINED, CALL_ENDED, ESCALATED},
    PAYMENT_CONTEXT_SHARED: {CUSTOMER_RESPONDING, DECLINED, CALL_ENDED, ESCALATED},
    CUSTOMER_RESPONDING: {
        PROMISE_TO_PAY,
        PAYMENT_COMPLETED,
        DECLINED,
        ESCALATED,
        CALL_ENDED,
        CUSTOMER_RESPONDING,
    },
    PROMISE_TO_PAY: {CALL_ENDED, PAYMENT_COMPLETED},
    PAYMENT_COMPLETED: {CALL_ENDED},
    DECLINED: {CALL_ENDED},
    ESCALATED: {CALL_ENDED},
    CALL_ENDED: set(),
    FAILED: set(),
}


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, set())


def transition(current: str, target: str) -> str:
    if current == target and current in TRANSITIONS.get(current, set()):
        return target
    if not can_transition(current, target):
        raise InvalidTransition(
            f"Voice session cannot move from {current} to {target}",
            {"from": current, "to": target, "allowed": sorted(TRANSITIONS.get(current, set()))},
        )
    return target
