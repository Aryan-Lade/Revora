from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict

from app.database.database import get_db
from app.ml import model as ml_model
from app.ml import dataset as ml_dataset

router = APIRouter()


@router.get("/metrics", response_model=Dict)
def get_ml_metrics(db: Session = Depends(get_db)):
    return ml_model.metrics()


@router.post("/train")
def train_model(db: Session = Depends(get_db)):
    accuracy = ml_model.train_model(db)
    return {"status": "model trained", "accuracy": accuracy}
