import json
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, User
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/audit-log", tags=["Audit Log"])

@router.get("")
def list_audit_log(
    event_type: Optional[str] = Query(None, description="Filter by event_type: score, override, config_change"),
    actor_id: Optional[str] = Query(None, description="Filter by actor_id"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Risk Manager"]))  # AuthZ-3 / Risk Manager view
):
    query = db.query(AuditLog)

    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)

    query = query.order_by(AuditLog.timestamp.desc())

    total = query.count()
    items = query.offset(offset).limit(limit).all()

    result = []
    for item in items:
        try:
            parsed_details = json.loads(item.details)
        except Exception:
            parsed_details = item.details

        result.append({
            "log_id": item.log_id,
            "transaction_id": item.transaction_id,
            "event_type": item.event_type,
            "actor_id": item.actor_id,
            "actor_role": item.actor_role,
            "details": parsed_details,
            "timestamp": item.timestamp.isoformat()
        })

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": result
    }
