from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.database import get_db
from app.database import models
from app.api import schemas
from app.core import errors

router = APIRouter()


@router.get("/", response_model=List[schemas.Communication])
def get_communications(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    communications = db.query(models.Communication).offset(skip).limit(limit).all()
    return communications


@router.get("/{communication_id}", response_model=schemas.Communication)
def get_communication(communication_id: int, db: Session = Depends(get_db)):
    communication = db.query(models.Communication).filter(models.Communication.id == communication_id).first()
    if communication is None:
        raise HTTPException(status_code=404, detail="Communication not found")
    return communication


@router.post("/", response_model=schemas.Communication, status_code=status.HTTP_201_CREATED)
def create_communication(communication: schemas.CommunicationCreate, db: Session = Depends(get_db)):
    db_communication = models.Communication(**communication.dict())
    db.add(db_communication)
    db.commit()
    db.refresh(db_communication)
    return db_communication


@router.put("/{communication_id}", response_model=schemas.Communication)
def update_communication(communication_id: int, communication: schemas.CommunicationUpdate, db: Session = Depends(get_db)):
    db_communication = db.query(models.Communication).filter(models.Communication.id == communication_id).first()
    if db_communication is None:
        raise HTTPException(status_code=404, detail="Communication not found")
    for key, value in communication.dict(exclude_unset=True).items():
        setattr(db_communication, key, value)
    db.commit()
    db.refresh(db_communication)
    return db_communication


@router.delete("/{communication_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_communication(communication_id: int, db: Session = Depends(get_db)):
    db_communication = db.query(models.Communication).filter(models.Communication.id == communication_id).first()
    if db_communication is None:
        raise HTTPException(status_code=404, detail="Communication not found")
    db.delete(db_communication)
    db.commit()
    return None