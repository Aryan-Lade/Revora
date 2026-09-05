import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import IdempotencyRecord

MAX_KEY_LENGTH = 120


def build_key(operation: str, *parts) -> str:
    raw = ":".join([operation, *(str(part) for part in parts)])
    if len(raw) <= MAX_KEY_LENGTH:
        return raw
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"{raw[: MAX_KEY_LENGTH - 17]}#{digest}"


def find(db: Session, key: str) -> IdempotencyRecord | None:
    return db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == key))


def remember(db: Session, key: str, operation: str, response: dict) -> IdempotencyRecord:
    record = find(db, key)
    if record:
        return record
    record = IdempotencyRecord(idempotency_key=key, operation=operation, response=response)
    db.add(record)
    db.flush()
    return record
