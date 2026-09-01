from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.metrics_service import compute_batch_metrics

router = APIRouter(prefix="/metrics", tags=["Metrics"])

@router.get("")
def get_metrics(
    batch_id: Optional[str] = Query(None, description="Filter metrics by batch_id"),
    db: Session = Depends(get_db)
):
    return compute_batch_metrics(db, batch_id=batch_id)
