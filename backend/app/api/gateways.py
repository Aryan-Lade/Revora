from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.database import get_db
from app.database import models
from app.api import schemas
from app.core import errors

router = APIRouter()


@router.get("/", response_model=List[schemas.GatewayProvider])
def get_gateways(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    gateways = db.query(models.GatewayProvider).offset(skip).limit(limit).all()
    return gateways


@router.get("/{gateway_id}", response_model=schemas.GatewayProvider)
def get_gateway(gateway_id: int, db: Session = Depends(get_db)):
    gateway = db.query(models.GatewayProvider).filter(models.GatewayProvider.id == gateway_id).first()
    if gateway is None:
        raise HTTPException(status_code=404, detail="Gateway provider not found")
    return gateway


@router.post("/", response_model=schemas.GatewayProvider, status_code=status.HTTP_201_CREATED)
def create_gateway(gateway: schemas.GatewayProviderCreate, db: Session = Depends(get_db)):
    db_gateway = models.GatewayProvider(**gateway.dict())
    db.add(db_gateway)
    db.commit()
    db.refresh(db_gateway)
    return db_gateway


@router.put("/{gateway_id}", response_model=schemas.GatewayProvider)
def update_gateway(gateway_id: int, gateway: schemas.GatewayProviderUpdate, db: Session = Depends(get_db)):
    db_gateway = db.query(models.GatewayProvider).filter(models.GatewayProvider.id == gateway_id).first()
    if db_gateway is None:
        raise HTTPException(status_code=404, detail="Gateway provider not found")
    for key, value in gateway.dict(exclude_unset=True).items():
        setattr(db_gateway, key, value)
    db.commit()
    db.refresh(db_gateway)
    return db_gateway


@router.delete("/{gateway_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gateway(gateway_id: int, db: Session = Depends(get_db)):
    db_gateway = db.query(models.GatewayProvider).filter(models.GatewayProvider.id == gateway_id).first()
    if db_gateway is None:
        raise HTTPException(status_code=404, detail="Gateway provider not found")
    db.delete(db_gateway)
    db.commit()
    return None


@router.post("/{gateway_id}/toggle")
def toggle_gateway(gateway_id: int, db: Session = Depends(get_db)):
    from app.core.constants import GATEWAY_HEALTHY, GATEWAY_UNAVAILABLE
    db_gateway = db.query(models.GatewayProvider).filter(models.GatewayProvider.id == gateway_id).first()
    if db_gateway is None:
        raise HTTPException(status_code=404, detail="Gateway provider not found")
    db_gateway.status = GATEWAY_UNAVAILABLE if db_gateway.status == GATEWAY_HEALTHY else GATEWAY_HEALTHY
    db.commit()
    db.refresh(db_gateway)
    return {"id": db_gateway.id, "name": db_gateway.name, "status": db_gateway.status}