import json
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import AuditLog

def log_audit_event(
    db: Session, 
    event_type: str, 
    actor_id: str, 
    actor_role: str, 
    details: Dict[str, Any], 
    transaction_id: Optional[str] = None
) -> AuditLog:
    """
    Append-only write helper for Audit Log per BR-1 / FR-10.
    No update or delete code path exists for AuditLog.
    """
    audit_entry = AuditLog(
        log_id=str(uuid.uuid4()),
        transaction_id=transaction_id,
        event_type=event_type,
        actor_id=actor_id,
        actor_role=actor_role,
        details=json.dumps(details)
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry
