from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.database import get_db
from app.database import models
from app.api import schemas
from app.core import errors
from app.voice import agent as voice_agent

router = APIRouter()


@router.get("/sessions", response_model=List[schemas.VoiceSession])
def get_voice_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    sessions = db.query(models.VoiceSession).offset(skip).limit(limit).all()
    return sessions


@router.get("/sessions/{session_id}", response_model=schemas.VoiceSession)
def get_voice_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(models.VoiceSession).filter(models.VoiceSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Voice session not found")
    return session


@router.post("/start")
def start_voice_call(
    customer_id: int,
    recovery_case_id: int,
    db: Session = Depends(get_db)
):
    # Initiate a voice call
    result = voice_agent.initiate_call(customer_id, recovery_case_id, db)
    return result


@router.post("/response")
def handle_voice_response(
    session_id: int,
    customer_response: str,
    db: Session = Depends(get_db)
):
    # Handle customer response during voice call
    result = voice_agent.handle_customer_response(session_id, customer_response, db)
    return result


@router.get("/health")
def get_voice_health(db: Session = Depends(get_db)):
    # Get voice provider health
    health = voice_agent.get_provider_health(db)
    return health