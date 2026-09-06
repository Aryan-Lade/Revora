from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.database import get_db
from app.database import models
from app.core import errors
from app.ml import model as ml_model
from app.ml import dataset as ml_dataset
from app.api import schemas

router = APIRouter()


@router.get("/metrics", response_model=schemas.MlModelMetric)
def get_ml_metrics(db: Session = Depends(get_db)):
    # Get the most recent ML model metrics
    metrics = db.query(models.MlModelMetric).order_by(models.MlModelMetric.trained_at.desc()).first()
    if metrics is None:
        # If no metrics, return a default or raise an exception
        raise HTTPException(status_code=404, detail="ML model metrics not found")
    return metrics


@router.post("/train", status_code=status.HTTP_200_OK)
def train_model(db: Session = Depends(get_db)):
    # Trigger ML model training
    # In a production system, this would be a background task
    # For simplicity, we run it synchronously here
    ml_dataset.generate_synthetic_data(db)
    accuracy = ml_model.train_model(db)
    return {"status": "model trained", "accuracy": accuracy}