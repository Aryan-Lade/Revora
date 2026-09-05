from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class RevoraError(Exception):
    status_code = 400
    code = "revora_error"

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail or {}


class NotFound(RevoraError):
    status_code = 404
    code = "not_found"


class InvalidTransition(RevoraError):
    status_code = 409
    code = "invalid_state_transition"


class PolicyBlocked(RevoraError):
    status_code = 409
    code = "policy_blocked"


class GuardrailBlocked(RevoraError):
    status_code = 409
    code = "guardrail_blocked"


class ProviderUnavailable(RevoraError):
    status_code = 503
    code = "provider_unavailable"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RevoraError)
    async def revora_handler(_: Request, exc: RevoraError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "message": exc.message, "detail": exc.detail},
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_handler(_: Request, __: SQLAlchemyError):
        return JSONResponse(
            status_code=503,
            content={"error": "database_error", "message": "Database request could not be completed"},
        )

    @app.exception_handler(Exception)
    async def unexpected_handler(_: Request, __: Exception):
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "Unexpected server error"},
        )
