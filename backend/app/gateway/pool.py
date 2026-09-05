from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.constants import GATEWAY_DEGRADED, GATEWAY_HEALTHY, GATEWAY_UNAVAILABLE
from app.database.models import GatewayProvider

PROVIDERS = [
    {"name": "razorpay_primary", "label": "Razorpay Primary", "priority": 1, "capacity": 120},
    {"name": "razorpay_secondary", "label": "Razorpay Secondary", "priority": 2, "capacity": 80},
    {"name": "upi_direct", "label": "UPI Direct Debit", "priority": 3, "capacity": 40},
]

DEGRADED_AFTER = 2
UNAVAILABLE_AFTER = 3
STATUS_RANK = {GATEWAY_HEALTHY: 0, GATEWAY_DEGRADED: 1, GATEWAY_UNAVAILABLE: 2}


def status_for(failure_count: int) -> str:
    if failure_count >= UNAVAILABLE_AFTER:
        return GATEWAY_UNAVAILABLE
    if failure_count >= DEGRADED_AFTER:
        return GATEWAY_DEGRADED
    return GATEWAY_HEALTHY


def providers(db: Session) -> list[GatewayProvider]:
    return list(db.scalars(select(GatewayProvider).order_by(GatewayProvider.priority)))


def ensure_providers(db: Session) -> list[GatewayProvider]:
    existing = {provider.name for provider in providers(db)}
    for spec in PROVIDERS:
        if spec["name"] not in existing:
            db.add(GatewayProvider(**spec, status=GATEWAY_HEALTHY, latency_ms=180))
    db.flush()
    return providers(db)


def select_provider(db: Session, exclude: set[str] | None = None) -> GatewayProvider | None:
    exclude = exclude or set()
    candidates = [
        provider
        for provider in ensure_providers(db)
        if provider.name not in exclude and provider.status != GATEWAY_UNAVAILABLE
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: (STATUS_RANK[p.status], p.priority))[0]


def record_success(db: Session, provider: GatewayProvider, latency_ms: int) -> GatewayProvider:
    provider.success_count += 1
    provider.failure_count = 0
    provider.latency_ms = latency_ms
    provider.status = GATEWAY_HEALTHY
    provider.last_success_at = utcnow()
    db.flush()
    return provider


def record_failure(db: Session, provider: GatewayProvider, latency_ms: int = 0) -> GatewayProvider:
    provider.failure_count += 1
    provider.latency_ms = latency_ms or provider.latency_ms
    provider.status = status_for(provider.failure_count)
    provider.last_failure_at = utcnow()
    db.flush()
    return provider


def as_dict(provider: GatewayProvider) -> dict:
    total = provider.success_count + provider.failure_count
    return {
        "name": provider.name,
        "label": provider.label,
        "status": provider.status,
        "priority": provider.priority,
        "capacity": provider.capacity,
        "latency_ms": provider.latency_ms,
        "success_count": provider.success_count,
        "failure_count": provider.failure_count,
        "success_rate": round(provider.success_count / total * 100, 2) if total else 100.0,
        "last_success_at": provider.last_success_at,
        "last_failure_at": provider.last_failure_at,
    }


def snapshot(db: Session) -> dict:
    rows = [as_dict(provider) for provider in ensure_providers(db)]
    healthy = [row for row in rows if row["status"] == GATEWAY_HEALTHY]
    usable = [row for row in rows if row["status"] != GATEWAY_UNAVAILABLE]
    if healthy:
        status = GATEWAY_HEALTHY
    elif usable:
        status = GATEWAY_DEGRADED
    else:
        status = GATEWAY_UNAVAILABLE
    return {
        "providers": rows,
        "healthy": len(healthy),
        "usable": len(usable),
        "total": len(rows),
        "status": status,
    }
