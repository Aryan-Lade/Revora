from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import register_error_handlers

app = FastAPI(
    title="Revora API",
    description="Autonomous AI Revenue Recovery Platform",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register error handlers
register_error_handlers(app)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "revora", "environment": settings.environment}


# Import and include routers here to avoid circular imports
from app.api import (
    customers,
    subscriptions,
    payments,
    recovery,
    promises,
    communications,
    voice,
    gateways,
    ml,
    audit,
    dashboard,
    analytics,
)

app.include_router(customers.router, prefix="/api/customers", tags=["customers"])
app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["subscriptions"])
app.include_router(payments.router, prefix="/api/payments", tags=["payments"])
app.include_router(recovery.router, prefix="/api/recovery", tags=["recovery"])
app.include_router(promises.router, prefix="/api/promises", tags=["promises"])
app.include_router(communications.router, prefix="/api/communications", tags=["communications"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(gateways.router, prefix="/api/gateways", tags=["gateways"])
app.include_router(ml.router, prefix="/api/ml", tags=["ml"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(recovery.webhook_router, prefix="/api/webhooks", tags=["webhooks"])