import os
import csv
import json
from fastapi.testclient import TestClient
from main import app
from app.database import Base, engine, SessionLocal
from app.models import TestLabel, Transaction, Score, ReasonChain
from app.metrics_service import compute_batch_metrics

client = TestClient(app)

def run_live_gemini_verification():
    labels_csv = os.path.join(os.path.dirname(__file__), "synthetic_labels.csv")
    tx_csv = os.path.join(os.path.dirname(__file__), "synthetic_transactions.csv")

    # 1. Reset database tables and seed test_labels
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    with open(labels_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            db.add(TestLabel(transaction_id=row["transaction_id"], is_fraud=(row["is_fraud"].lower() == "true")))
    db.commit()
    db.close()

    # 2. Ingest and score batch using REAL live Gemini API calls
    print("\n--- Starting Live Batch Scoring via Google Gemini API ---")
    with open(tx_csv, "rb") as f:
        response = client.post("/batches", files={"file": ("synthetic_transactions.csv", f, "text/csv")})

    assert response.status_code == 201, f"Batch scoring failed: {response.text}"
    batch_data = response.json()
    batch_id = batch_data["batch_id"]

    db = SessionLocal()
    metrics = compute_batch_metrics(db, batch_id=batch_id)

    # 3. Print 3 Real Transaction Raw Outputs
    llm_scores = db.query(Score).filter(Score.decided_by == "llm").limit(3).all()
    if not llm_scores:
        llm_scores = db.query(Score).filter(Score.decided_by == "degraded_reasoning").limit(3).all()

    print("\n==========================================================================")
    print("        LIVE GEMINI RESPONSE SAMPLES (3 Transactions)                     ")
    print("==========================================================================")
    for idx, s in enumerate(llm_scores, 1):
        tx = s.transaction
        rc = db.query(ReasonChain).filter(ReasonChain.transaction_id == s.transaction_id).first()
        reason_text = rc.reason_text if rc else "No reason chain recorded"
        try:
            reasons = json.loads(reason_text)
        except Exception:
            reasons = [reason_text]

        print(f"\nSample #{idx}:")
        print(f"  Transaction ID:  {s.transaction_id}")
        print(f"  Amount:          ₹{tx.amount:,.2f}" if tx else f"  Amount:          N/A")
        print(f"  Device / Geo:    NewDevice={tx.is_new_device}, IP={tx.ip_country}, Billing={tx.billing_country}" if tx else "")
        print(f"  Assigned Score:  {s.score}")
        print(f"  Routing Outcome: {s.routing_outcome}")
        print(f"  Decided By:      '{s.decided_by}'")
        print("  Reason Bullets:")
        for r in reasons:
            print(f"    • {r}")
    print("==========================================================================\n")

    # 4. Print Full Metrics Output
    tp = metrics['confusion_matrix']['tp']
    fp = metrics['confusion_matrix']['fp']
    fn = metrics['confusion_matrix']['fn']
    tn = metrics['confusion_matrix']['tn']

    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    print("==========================================================================")
    print("    LIVE HYBRID SYSTEM METRICS (Google Gemini API - Real Execution)       ")
    print("==========================================================================")
    print(f"Batch ID:                  {batch_id}")
    print(f"Total Scored Transactions: {metrics['total_scored']}")
    print(f"Confusion Matrix:          TP={tp}, FP={fp}, FN={fn}, TN={tn}")
    print(f"Precision:                 {metrics['precision']*100:.2f}%")
    print(f"Recall:                    {metrics['recall']*100:.2f}%")
    print(f"F1 Score:                  {metrics['f1_score']:.4f}")
    print(f"False Positive Rate (FPR): {fpr*100:.2f}%")
    print(f"False Negative Rate (FNR): {fnr*100:.2f}%")
    print(f"Total FP Cost Exposure:    ₹{metrics['total_fp_cost_exposure']:,.2f}")
    print(f"Total FN Cost Exposure:    ₹{metrics['total_fn_cost_exposure']:,.2f}")
    print(f"Decision Split:            Rule={metrics['rule_percent']}% ({metrics['rule_decided_count']}), LLM={metrics['llm_percent']}% ({metrics['llm_decided_count'] + metrics['degraded_count']})")
    print("==========================================================================\n")

    db.close()

if __name__ == "__main__":
    run_live_gemini_verification()
