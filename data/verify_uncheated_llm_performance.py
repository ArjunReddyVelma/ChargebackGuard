import os
import csv
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from app.database import Base, engine, SessionLocal
from app.models import TestLabel, Transaction, Score, Cost
from app.metrics_service import compute_batch_metrics

client = TestClient(app)

def uncheated_feature_only_llm_mock(scoped_tx, rule_reasons):
    """
    STRICTLY FEATURE-BASED LLM MOCK (Zero Label Leakage).
    Does NOT look at is_fraud or LABEL_MAP in any way.
    Evaluates risk based purely on transaction features:
    - Geo mismatch + new device + recent account age
    - High transaction amount relative to user historical average
    - Account age & velocity patterns
    """
    amount = float(scoped_tx.get("amount", 0))
    avg_user_amount = float(scoped_tx.get("avg_user_amount", 0))
    account_age_days = int(scoped_tx.get("account_age_days", 0))
    is_new_device = bool(scoped_tx.get("is_new_device", False))
    ip_country = (scoped_tx.get("ip_country") or "").upper()
    billing_country = (scoped_tx.get("billing_country") or "").upper()
    velocity = int(scoped_tx.get("velocity_10min", 0))

    geo_mismatch = (ip_country != billing_country)
    
    score = 25
    reasons = []

    if is_new_device:
        score += 20
        reasons.append("Transaction originated from an unrecognized new device.")

    if geo_mismatch:
        score += 25
        reasons.append(f"Geographic location mismatch: IP in {ip_country}, billing in {billing_country}.")

    if account_age_days < 14:
        score += 15
        reasons.append(f"Account is newly created ({account_age_days} days old).")

    if avg_user_amount > 0 and amount > (2.5 * avg_user_amount):
        ratio = amount / avg_user_amount
        score += 20
        reasons.append(f"Transaction amount (₹{amount:.2f}) is {ratio:.1f}x higher than user's baseline average (₹{avg_user_amount:.2f}).")

    if velocity >= 3:
        score += 15
        reasons.append(f"Elevated velocity of {velocity} transactions in 10 minutes.")

    # Clamp score
    final_score = max(0, min(100, score))

    if not reasons:
        reasons.append("Standard transaction parameters within normal bounds.")

    return (final_score, reasons, "llm")

def run_uncheated_evaluation():
    labels_csv = os.path.join(os.path.dirname(__file__), "synthetic_labels.csv")
    tx_csv = os.path.join(os.path.dirname(__file__), "synthetic_transactions.csv")

    # 1. Reset database tables and seed test_labels (stored separately)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    with open(labels_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            db.add(TestLabel(transaction_id=row["transaction_id"], is_fraud=(row["is_fraud"].lower() == "true")))
    db.commit()
    db.close()

    # 2. Run scoring with feature-only uncheated LLM layer
    with patch("app.scoring_service.generate_llm_reasoning", side_effect=uncheated_feature_only_llm_mock):
        with open(tx_csv, "rb") as f:
            res = client.post("/batches", files={"file": ("synthetic_transactions.csv", f, "text/csv")})

    db = SessionLocal()
    metrics = compute_batch_metrics(db)
    db.close()

    tp = metrics['confusion_matrix']['tp']
    fp = metrics['confusion_matrix']['fp']
    fn = metrics['confusion_matrix']['fn']
    tn = metrics['confusion_matrix']['tn']

    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    print("\n==========================================================================")
    print("   UNCHEATED FULL HYBRID SYSTEM METRICS (Feature-Grounded LLM Layer)    ")
    print("==========================================================================")
    print(f"Total Scored Transactions: {metrics['total_scored']}")
    print(f"Confusion Matrix: TP={tp}, FP={fp}, FN={fn}, TN={tn}")
    print(f"Precision:                {metrics['precision']*100:.2f}%")
    print(f"Recall:                   {metrics['recall']*100:.2f}%")
    print(f"F1 Score:                 {metrics['f1_score']:.4f}")
    print(f"False Positive Rate (FPR): {fpr*100:.2f}%")
    print(f"False Negative Rate (FNR): {fnr*100:.2f}%")
    print(f"Decision Split:            Rule={metrics['rule_percent']}% ({metrics['rule_decided_count']}), LLM={metrics['llm_percent']}% ({metrics['llm_decided_count']})")
    print("==========================================================================\n")

    # Show 5 individual transaction-level results
    print("--- 5 Sample Individual Transaction Results (Feature-Only Scoring) ---")
    db = SessionLocal()
    labels = {tl.transaction_id: tl.is_fraud for tl in db.query(TestLabel).all()}
    sample_txs = db.query(Transaction).limit(5).all()
    for tx in sample_txs:
        score_obj = tx.score_rel
        actual = labels.get(tx.transaction_id)
        print(f"TxID: {tx.transaction_id} | Score: {score_obj.score:2d} | Outcome: {score_obj.routing_outcome:12s} | DecidedBy: {score_obj.decided_by:5s} | Actual Fraud: {actual}")
    db.close()

if __name__ == "__main__":
    run_uncheated_evaluation()
