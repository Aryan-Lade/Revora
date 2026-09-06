from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.database import get_db
from app.database import models
from app.api import schemas
from app.core import errors

router = APIRouter()


@router.get("/", response_model=List[schemas.PromiseToPay])
def get_promises(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    promises = db.query(models.PromiseToPay).offset(skip).limit(limit).all()
    return promises


@router.get("/{promise_id}", response_model=schemas.PromiseToPay)
def get_promise(promise_id: int, db: Session = Depends(get_db)):
    promise = db.query(models.PromiseToPay).filter(models.PromiseToPay.id == promise_id).first()
    if promise is None:
        raise HTTPException(status_code=404, detail="Promise to pay not found")
    return promise


@router.post("/", response_model=schemas.PromiseToPay, status_code=status.HTTP_201_CREATED)
def create_promise(promise: schemas.PromiseToPayCreate, db: Session = Depends(get_db)):
    # Check if there's already an active promise for the same recovery case
    existing_promise = db.query(models.PromiseToPay).filter(
        models.PromiseToPay.recovery_case_id == promise.recovery_case_id,
        models.PromiseToPay.status == models.PROMISE_ACTIVE
    ).first()
    if existing_promise:
        raise HTTPException(status_code=400, detail="An active promise-to-pay already exists for this recovery case")

    db_promise = models.PromiseToPay(**promise.dict())
    db.add(db_promise)
    db.commit()
    db.refresh(db_promise)
    return db_promise


@router.put("/{promise_id}", response_model=schemas.PromiseToPay)
def update_promise(promise_id: int, promise: schemas.PromiseToPayUpdate, db: Session = Depends(get_db)):
    db_promise = db.query(models.PromiseToPay).filter(models.PromiseToPay.id == promise_id).first()
    if db_promise is None:
        raise HTTPException(status_code=404, detail="Promise to pay not found")
    for key, value in promise.dict(exclude_unset=True).items():
        setattr(db_promise, key, value)
    db.commit()
    db.refresh(db_promise)
    return db_promise


@router.delete("/{promise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_promise(promise_id: int, db: Session = Depends(get_db)):
    db_promise = db.query(models.PromiseToPay).filter(models.PromiseToPay.id == promise_id).first()
    if db_promise is None:
        raise HTTPException(status_code=404, detail="Promise to pay not found")
    db.delete(db_promise)
    db.commit()
    return None