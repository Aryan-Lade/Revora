from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.database import get_db
from app.database import models
from app.api import schemas
from app.core.constants import PROMISE_ACTIVE

router = APIRouter()


@router.get("/", response_model=List[schemas.PromiseToPay])
def get_promises(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.PromiseToPay).order_by(models.PromiseToPay.id.desc()).offset(skip).limit(limit).all()


@router.get("/{promise_id}", response_model=schemas.PromiseToPay)
def get_promise(promise_id: int, db: Session = Depends(get_db)):
    promise = db.query(models.PromiseToPay).filter(models.PromiseToPay.id == promise_id).first()
    if promise is None:
        raise HTTPException(status_code=404, detail="Promise to pay not found")
    return promise


@router.put("/{promise_id}", response_model=schemas.PromiseToPay)
def update_promise(promise_id: int, promise: schemas.PromiseToPayUpdate, db: Session = Depends(get_db)):
    db_promise = db.query(models.PromiseToPay).filter(models.PromiseToPay.id == promise_id).first()
    if db_promise is None:
        raise HTTPException(status_code=404, detail="Promise to pay not found")
    for key, value in promise.model_dump(exclude_unset=True).items():
        setattr(db_promise, key, value)
    db.commit()
    db.refresh(db_promise)
    return db_promise
