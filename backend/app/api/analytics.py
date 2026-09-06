from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case, cast, Numeric
from typing import Dict, List

from app.database.database import get_db
from app.database import models
from app.core import errors

router = APIRouter()


@router.get("/recovery-by-channel", response_model=List[Dict])
def get_recovery_by_channel(db: Session = Depends(get_db)):
    """
    Get recovery amount grouped by channel.
    """
    # We'll join communications with recovery cases to get the channel used for successful recoveries
    # For simplicity, we'll assume that a communication with status 'SENT' and a recovered case indicates a successful channel
    # In a real system, we might have more detailed tracking.
    results = db.query(
        models.Communication.channel,
        func.sum(models.RecoveryCase.recovered_amount).label("amount")
    ).join(
        models.RecoveryCase, models.Communication.recovery_case_id == models.RecoveryCase.id
    ).filter(
        models.RecoveryCase.status == models.recovery_state.RECOVERED,
        models.Communication.status == "SENT"
    ).group_by(
        models.Communication.channel
    ).all()

    # Format the result as a list of dictionaries
    return [{"channel": channel, "amount": float(amount or 0)} for channel, amount in results]


@router.get("/recovery-by-reason", response_model=List[Dict])
def get_recovery_by_reason(db: Session = Depends(get_db)):
    """
    Get recovery amount grouped by failure reason (failure_type).
    """
    results = db.query(
        models.RecoveryCase.failure_type,
        func.sum(models.RecoveryCase.recovered_amount).label("amount")
    ).filter(
        models.RecoveryCase.status == models.recovery_state.RECOVERED
    ).group_by(
        models.RecoveryCase.failure_type
    ).all()

    # Format the result as a list of dictionaries
    return [{"failure_type": failure_type, "amount": float(amount or 0)} for failure_type, amount in results]