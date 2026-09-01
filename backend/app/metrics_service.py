from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Transaction, Score, Cost, TestLabel

def compute_batch_metrics(db: Session, batch_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Computes precision, recall, F1 against separately-stored TestLabel ground truth (FR-11).
    Computes false-positive and false-negative exposure costs (FR-12).
    Computes rule vs LLM decision split (FR-13).
    """
    query = db.query(Transaction).join(Score, Transaction.transaction_id == Score.transaction_id)
    if batch_id:
        query = query.filter(Transaction.batch_id == batch_id)

    transactions = query.all()
    total_scored = len(transactions)

    if total_scored == 0:
        return {
            "total_scored": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "tp": 0, "fp": 0, "fn": 0, "tn": 0,
            "total_fp_cost_exposure": 0.0,
            "total_fn_cost_exposure": 0.0,
            "rule_decided_count": 0,
            "llm_decided_count": 0,
            "degraded_count": 0,
            "rule_percent": 0.0,
            "llm_percent": 0.0
        }

    # Fetch ground truth labels from TestLabel table (DR-1 compliant!)
    labels_map = {tl.transaction_id: tl.is_fraud for tl in db.query(TestLabel).all()}

    tp = fp = fn = tn = 0
    total_fp_cost = 0.0
    total_fn_cost = 0.0

    rule_count = 0
    llm_count = 0
    degraded_count = 0

    for tx in transactions:
        score_obj = tx.score_rel
        cost_obj = tx.cost_rel
        
        predicted_flagged = (score_obj.routing_outcome in ["auto-block", "review-queue"])
        actual_fraud = labels_map.get(tx.transaction_id, False)

        if score_obj.decided_by == "rule":
            rule_count += 1
        elif score_obj.decided_by == "llm":
            llm_count += 1
        elif score_obj.decided_by == "degraded_reasoning":
            degraded_count += 1

        if cost_obj:
            if predicted_flagged:
                total_fp_cost += cost_obj.fp_cost_estimate
            if score_obj.routing_outcome == "auto-clear":
                total_fn_cost += cost_obj.fn_cost_estimate

        if predicted_flagged and actual_fraud:
            tp += 1
        elif predicted_flagged and not actual_fraud:
            fp += 1
        elif not predicted_flagged and actual_fraud:
            fn += 1
        else:
            tn += 1

    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0

    rule_pct = round((rule_count / total_scored) * 100, 1)
    llm_pct = round(((llm_count + degraded_count) / total_scored) * 100, 1)

    return {
        "total_scored": total_scored,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "total_fp_cost_exposure": round(total_fp_cost, 2),
        "total_fn_cost_exposure": round(total_fn_cost, 2),
        "rule_decided_count": rule_count,
        "llm_decided_count": llm_count,
        "degraded_count": degraded_count,
        "rule_percent": rule_pct,
        "llm_percent": llm_pct
    }
