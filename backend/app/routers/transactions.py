import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models import Transaction, Score, ReasonChain, Cost, Decision, AuditLog
from app.schemas import DecisionSubmitSchema
from app.audit_log import log_audit_event

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.get("")
def list_transactions(
    routing_outcome: Optional[str] = Query(None, description="Filter by routing_outcome: review-queue, auto-clear, auto-block"),
    batch_id: Optional[str] = Query(None, description="Filter by batch_id"),
    decided_by: Optional[str] = Query(None, description="Filter by decided_by: rule, llm, degraded_reasoning"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(Transaction).join(Score, Transaction.transaction_id == Score.transaction_id)

    if routing_outcome:
        query = query.filter(Score.routing_outcome == routing_outcome)
    if batch_id:
        query = query.filter(Transaction.batch_id == batch_id)
    if decided_by:
        query = query.filter(Score.decided_by == decided_by)

    # Sort by descending risk score per FR-8
    query = query.order_by(Score.score.desc())

    total = query.count()
    items = query.offset(offset).limit(limit).all()

    result = []
    for tx in items:
        score_obj = tx.score_rel
        cost_obj = tx.cost_rel
        decision_obj = tx.decision_rel
        
        result.append({
            "transaction_id": tx.transaction_id,
            "batch_id": tx.batch_id,
            "timestamp": tx.timestamp,
            "amount": tx.amount,
            "payment_method": tx.payment_method,
            "device_id": tx.device_id,
            "is_new_device": tx.is_new_device,
            "ip_country": tx.ip_country,
            "billing_country": tx.billing_country,
            "shipping_country": tx.shipping_country,
            "account_age_days": tx.account_age_days,
            "velocity_10min": tx.velocity_10min,
            "avg_user_amount": tx.avg_user_amount,
            "score": score_obj.score if score_obj else None,
            "routing_outcome": score_obj.routing_outcome if score_obj else None,
            "decided_by": score_obj.decided_by if score_obj else None,
            "fp_cost_estimate": cost_obj.fp_cost_estimate if cost_obj else None,
            "fn_cost_estimate": cost_obj.fn_cost_estimate if cost_obj else None,
            "final_status": decision_obj.decision if decision_obj else (score_obj.routing_outcome if score_obj else "pending")
        })

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": result
    }


@router.get("/{transaction_id}")
def get_transaction_detail(transaction_id: str, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "TRANSACTION_NOT_FOUND", "message": f"Transaction '{transaction_id}' not found."}
        )

    score_obj = tx.score_rel
    reason_obj = tx.reason_chain_rel
    cost_obj = tx.cost_rel
    decision_obj = tx.decision_rel

    reason_bullets = []
    if reason_obj and reason_obj.reason_text:
        reason_bullets = [line.lstrip("• ").strip() for line in reason_obj.reason_text.split("\n") if line.strip()]

    return {
        "transaction_id": tx.transaction_id,
        "batch_id": tx.batch_id,
        "timestamp": tx.timestamp,
        "amount": tx.amount,
        "payment_method": tx.payment_method,
        "device_id": tx.device_id,
        "is_new_device": tx.is_new_device,
        "ip_country": tx.ip_country,
        "billing_country": tx.billing_country,
        "shipping_country": tx.shipping_country,
        "account_age_days": tx.account_age_days,
        "velocity_10min": tx.velocity_10min,
        "avg_user_amount": tx.avg_user_amount,
        "score": score_obj.score if score_obj else None,
        "routing_outcome": score_obj.routing_outcome if score_obj else None,
        "decided_by": score_obj.decided_by if score_obj else None,
        "rule_name": score_obj.rule_name if score_obj else None,
        "reason_bullets": reason_bullets,
        "fp_cost_estimate": cost_obj.fp_cost_estimate if cost_obj else None,
        "fn_cost_estimate": cost_obj.fn_cost_estimate if cost_obj else None,
        "decision": {
            "decision": decision_obj.decision,
            "reason_text": decision_obj.reason_text,
            "actor_id": decision_obj.actor_id,
            "actor_role": decision_obj.actor_role,
            "timestamp": decision_obj.timestamp.isoformat()
        } if decision_obj else None
    }


@router.post("/{transaction_id}/decision", status_code=status.HTTP_200_OK)
def submit_analyst_decision(
    transaction_id: str, 
    body: DecisionSubmitSchema, 
    db: Session = Depends(get_db)
):
    # 1. Fetch transaction
    tx = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "TRANSACTION_NOT_FOUND", "message": f"Transaction '{transaction_id}' not found."}
        )

    score_obj = tx.score_rel
    original_score = score_obj.score if score_obj else None
    original_outcome = score_obj.routing_outcome if score_obj else "unknown"

    # 2. EC-5 Concurrent Decision Check (First Write Wins!)
    existing_decision = db.query(Decision).filter(Decision.transaction_id == transaction_id).first()
    if existing_decision:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "ALREADY_DECIDED",
                "message": f"Transaction '{transaction_id}' has already received a decision ({existing_decision.decision}) by {existing_decision.actor_id}."
            }
        )

    # 3. Create Decision record
    actor_id = "analyst_demo@chargebackguard.io"
    actor_role = "Analyst"

    db_decision = Decision(
        transaction_id=transaction_id,
        actor_id=actor_id,
        actor_role=actor_role,
        decision=body.decision,
        reason_text=body.reason_text
    )
    db.add(db_decision)
    db.flush()

    # 4. Write to Append-Only Audit Log (FR-10, BR-1)
    audit_details = {
        "action": "analyst_decision",
        "transaction_id": transaction_id,
        "original_score": original_score,
        "original_routing_outcome": original_outcome,
        "human_decision": body.decision,
        "reason_text": body.reason_text,
        "actor_id": actor_id,
        "actor_role": actor_role
    }
    log_audit_event(db, "override", actor_id, actor_role, audit_details, transaction_id=transaction_id)

    db.commit()

    return {
        "status": "success",
        "transaction_id": transaction_id,
        "final_decision": body.decision,
        "reason_text": body.reason_text,
        "message": f"Decision '{body.decision}' recorded successfully."
    }
