from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.database import get_db
from app.database import models
from app.api import schemas
from app.core import errors

router = APIRouter()


@router.get("/", response_model=List[schemas.AuditLog])
def get_audit_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    audit_logs = db.query(models.AuditLog).offset(skip).limit(limit).all()
    return audit_logs


@router.get("/{audit_log_id}", response_model=schemas.AuditLog)
def get_audit_log(audit_log_id: int, db: Session = Depends(get_db)):
    audit_log = db.query(models.AuditLog).filter(models.AuditLog.id == audit_log_id).first()
    if audit_log is None:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return audit_log


@router.post("/", response_model=schemas.AuditLog, status_code=status.HTTP_201_CREATED)
def create_audit_log(audit_log: schemas.AuditLogCreate, db: Session = Depends(get_db)):
    db_audit_log = models.AuditLog(**audit_log.dict())
    db.add(db_audit_log)
    db.commit()
    db.refresh(db_audit_log)
    return db_audit_log


@router.put("/{audit_log_id}", response_model=schemas.AuditLog)
def update_audit_log(audit_log_id: int, audit_log: schemas.AuditLogUpdate, db: Session = Depends(get_db)):
    db_audit_log = db.query(models.AuditLog).filter(models.AuditLog.id == audit_log_id).first()
    if db_audit_log is None:
        raise HTTPException(status_code=404, detail="Audit log not found")
    for key, value in audit_log.dict(exclude_unset=True).items():
        setattr(db_audit_log, key, value)
    db.commit()
    db.refresh(db_audit_log)
    return db_audit_log


@router.delete("/{audit_log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_audit_log(audit_log_id: int, db: Session = Depends(get_db)):
    db_audit_log = db.query(models.AuditLog).filter(models.AuditLog.id == audit_log_id).first()
    if db_audit_log is None:
        raise HTTPException(status_code=404, detail="Audit log not found")
    db.delete(db_audit_log)
    db.commit()
    return None