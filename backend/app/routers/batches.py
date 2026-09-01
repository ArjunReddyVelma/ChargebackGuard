import csv
import io
import json
import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models import Transaction, Score, ReasonChain, AuditLog
from app.schemas import TransactionIngestSchema
from app.rule_engine import evaluate_transaction_rules

router = APIRouter(prefix="/batches", tags=["Batches"])

@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_batch(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_FILE_TYPE", "message": "Uploaded file must be a CSV."}
        )

    content = await file.read()
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_ENCODING", "message": "File encoding must be UTF-8."}
        )

    csv_reader = csv.DictReader(io.StringIO(text_content))
    rows = list(csv_reader)

    if not rows:  # EC-3: empty batch handling
        return {
            "batch_id": str(uuid.uuid4()),
            "total_rows": 0,
            "valid_rows_count": 0,
            "quarantined_rows_count": 0,
            "quarantined_errors": [],
            "rule_decided_count": 0,
            "needs_llm_count": 0
        }

    batch_id = f"BATCH_{uuid.uuid4().hex[:8].upper()}"
    seen_tx_ids = set()
    quarantined_errors = []
    valid_transactions = []
    
    rule_decided_count = 0
    needs_llm_count = 0

    for idx, row in enumerate(rows, start=1):
        tx_id = row.get("transaction_id", "").strip()
        
        # VR-6: Duplicate transaction ID check
        if not tx_id:
            quarantined_errors.append({
                "row_number": idx,
                "transaction_id": None,
                "error_code": "MISSING_TRANSACTION_ID",
                "message": "Row is missing required transaction_id field."
            })
            continue

        if tx_id in seen_tx_ids:
            quarantined_errors.append({
                "row_number": idx,
                "transaction_id": tx_id,
                "error_code": "DUPLICATE_TRANSACTION_ID",
                "message": f"Duplicate transaction_id '{tx_id}' in batch."
            })
            continue

        seen_tx_ids.add(tx_id)

        # Validate schema & VR-1 to VR-4
        try:
            # Parse types
            raw_data = {
                "transaction_id": tx_id,
                "timestamp": row.get("timestamp", "").strip(),
                "amount": float(row.get("amount", 0)),
                "payment_method": row.get("payment_method", "").strip(),
                "device_id": row.get("device_id", "").strip(),
                "is_new_device": str(row.get("is_new_device", "")).strip().lower() == "true",
                "ip_country": row.get("ip_country", "").strip(),
                "billing_country": row.get("billing_country", "").strip(),
                "shipping_country": row.get("shipping_country", "").strip() or None,
                "account_age_days": int(row.get("account_age_days", 0)),
                "velocity_10min": int(row.get("velocity_10min", 0)),
                "avg_user_amount": float(row.get("avg_user_amount", 0)),
            }
            validated_schema = TransactionIngestSchema(**raw_data)
        except Exception as e:
            # Extract error code if present
            err_msg = str(e)
            err_code = "INVALID_FIELD_VALUE"
            if "INVALID_AMOUNT" in err_msg:
                err_code = "INVALID_AMOUNT"
            elif "INVALID_COUNTRY_CODE" in err_msg:
                err_code = "INVALID_COUNTRY_CODE"
            elif "INVALID_TIMESTAMP" in err_msg:
                err_code = "INVALID_TIMESTAMP"

            quarantined_errors.append({
                "row_number": idx,
                "transaction_id": tx_id,
                "error_code": err_code,
                "message": err_msg
            })
            continue

        # Evaluate Rule Engine
        status_tag, score, routing_outcome, rule_name, reason_bullets = evaluate_transaction_rules(validated_schema.model_dump())

        db_tx = Transaction(
            transaction_id=validated_schema.transaction_id,
            batch_id=batch_id,
            timestamp=validated_schema.timestamp,
            amount=validated_schema.amount,
            payment_method=validated_schema.payment_method,
            device_id=validated_schema.device_id,
            is_new_device=validated_schema.is_new_device,
            ip_country=validated_schema.ip_country,
            billing_country=validated_schema.billing_country,
            shipping_country=validated_schema.shipping_country,
            account_age_days=validated_schema.account_age_days,
            velocity_10min=validated_schema.velocity_10min,
            avg_user_amount=validated_schema.avg_user_amount,
            anomaly_flag="EXTREME_VELOCITY" if validated_schema.velocity_10min > 500 else None
        )
        db.add(db_tx)
        db.flush()

        if status_tag == "rule_decided":
            rule_decided_count += 1
            db_score = Score(
                transaction_id=validated_schema.transaction_id,
                score=score,
                routing_outcome=routing_outcome,
                decided_by="rule",
                rule_name=rule_name
            )
            db.add(db_score)

            db_reason = ReasonChain(
                transaction_id=validated_schema.transaction_id,
                reason_text="\n".join([f"• {r}" for r in reason_bullets]),
                referenced_fields=json.dumps(["velocity_10min", "is_new_device", "ip_country", "billing_country", "shipping_country"])
            )
            db.add(db_reason)
        else:
            needs_llm_count += 1

        valid_transactions.append(validated_schema.transaction_id)

    # Log audit entry for batch ingestion
    audit_entry = AuditLog(
        log_id=str(uuid.uuid4()),
        transaction_id=None,
        event_type="score",
        actor_id="System Account",
        actor_role="System",
        details=json.dumps({
            "action": "batch_upload",
            "batch_id": batch_id,
            "total_rows": len(rows),
            "valid_rows": len(valid_transactions),
            "quarantined_rows": len(quarantined_errors),
            "rule_decided_count": rule_decided_count,
            "needs_llm_count": needs_llm_count
        })
    )
    db.add(audit_entry)
    db.commit()

    return {
        "batch_id": batch_id,
        "total_rows": len(rows),
        "valid_rows_count": len(valid_transactions),
        "quarantined_rows_count": len(quarantined_errors),
        "quarantined_errors": quarantined_errors,
        "rule_decided_count": rule_decided_count,
        "needs_llm_count": needs_llm_count
    }
