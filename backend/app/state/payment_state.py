from app.core.errors import InvalidTransition

PENDING = "PENDING"
AUTHORIZED = "AUTHORIZED"
CAPTURED = "CAPTURED"
FAILED = "FAILED"
RETRYING = "RETRYING"
RECOVERED = "RECOVERED"
REFUNDED = "REFUNDED"
CANCELLED = "CANCELLED"
EXPIRED = "EXPIRED"

SUCCESSFUL = {CAPTURED, RECOVERED}

TRANSITIONS = {
    PENDING: {AUTHORIZED, CAPTURED, FAILED, CANCELLED, EXPIRED},
    AUTHORIZED: {CAPTURED, FAILED, CANCELLED, EXPIRED},
    CAPTURED: {REFUNDED},
    FAILED: {RETRYING, RECOVERED, CANCELLED, EXPIRED},
    RETRYING: {RECOVERED, FAILED, EXPIRED, CANCELLED},
    RECOVERED: {REFUNDED},
    REFUNDED: set(),
    CANCELLED: set(),
    EXPIRED: {RECOVERED},
}


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, set())


def transition(current: str, target: str) -> str:
    if current == target:
        return target
    if not can_transition(current, target):
        raise InvalidTransition(
            f"Payment cannot move from {current} to {target}",
            {"from": current, "to": target, "allowed": sorted(TRANSITIONS.get(current, set()))},
        )
    return target


def is_successful(state: str) -> bool:
    return state in SUCCESSFUL
