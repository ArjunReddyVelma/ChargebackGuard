from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, model_validator
from typing import Dict, Any

from app.database import get_db
from app.models import Config, User
from app.auth import get_current_user, require_role
from app.schemas import ThresholdConfigSchema, CostConfigSchema
from app.audit_log import log_audit_event

router = APIRouter(prefix="/config", tags=["Config"])

class FullConfigSchema(BaseModel):
    low_threshold: int = 30
    high_threshold: int = 70
    fp_cost_base: float = 500.0
    fn_cost_fee: float = 1500.0

    @model_validator(mode="after")
    def validate_full_config(self):
        # VR-5 / BR-6
        if not (0 <= self.low_threshold < self.high_threshold <= 100):
            raise ValueError("INVALID_THRESHOLD_CONFIG: Thresholds must satisfy 0 <= low_threshold < high_threshold <= 100.")
        # BR-5
        if self.fp_cost_base <= 0 or self.fn_cost_fee <= 0:
            raise ValueError("INVALID_COST_CONFIG: Cost assumptions must be strictly greater than zero.")
        return self

@router.get("")
def get_config(db: Session = Depends(get_db)):
    db_configs = db.query(Config).all()
    config_dict = {cfg.key: cfg.value for cfg in db_configs}
    
    return {
        "low_threshold": int(config_dict.get("low_threshold", 30)),
        "high_threshold": int(config_dict.get("high_threshold", 70)),
        "fp_cost_base": float(config_dict.get("fp_cost_base", 500.0)),
        "fn_cost_fee": float(config_dict.get("fn_cost_fee", 1500.0))
    }

@router.put("", status_code=status.HTTP_200_OK)
def update_config(
    body: FullConfigSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Risk Manager"]))  # AuthZ-2 enforcement!
):
    updates = {
        "low_threshold": str(body.low_threshold),
        "high_threshold": str(body.high_threshold),
        "fp_cost_base": str(body.fp_cost_base),
        "fn_cost_fee": str(body.fn_cost_fee)
    }

    old_config = get_config(db)

    for key, val in updates.items():
        cfg = db.query(Config).filter(Config.key == key).first()
        if cfg:
            cfg.value = val
            cfg.updated_by = current_user.email
        else:
            db.add(Config(key=key, value=val, updated_by=current_user.email))

    # Log config_change event to immutable audit log per FR-15
    audit_details = {
        "action": "config_change",
        "old_config": old_config,
        "new_config": body.model_dump(),
        "updated_by": current_user.email
    }
    log_audit_event(db, "config_change", current_user.email, current_user.role, audit_details)

    db.commit()

    return {
        "status": "success",
        "message": "Configuration updated successfully.",
        "config": body.model_dump()
    }
