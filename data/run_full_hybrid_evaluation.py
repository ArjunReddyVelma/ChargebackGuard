import os
import csv
from fastapi.testclient import TestClient
from main import app
from app.database import Base, engine, SessionLocal
from app.models import TestLabel, Transaction, Score, Cost
from app.metrics_service import compute_batch_metrics

client = TestClient(app)

def run_hybrid_evaluation():
    # 1. Reset database tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # 2. Seed TestLabel ground truth
    labels_csv = os.path.join(os.path.dirname(__file__), "synthetic_labels.csv")
    tx_csv = os.path.join(os.path.dirname(__file__), "synthetic_transactions.csv")

    db = SessionLocal()
    with open(labels_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            db.add(TestLabel(
                transaction_id=row["transaction_id"],
                is_fraud=(row["is_fraud"].lower() == "true")
            ))
    db.commit()
    db.close()

    # 3. Upload & Score Full Synthetic Batch via /batches endpoint
    with open(tx_csv, "rb") as f:
        response = client.post("/batches", files={"file": ("synthetic_transactions.csv", f, "text/csv")})

    assert response.status_code == 201, f"Batch upload failed: {response.text}"
    batch_res = response.json()
    batch_id = batch_res["batch_id"]

    # 4. Fetch /metrics endpoint
    db = SessionLocal()
    metrics = compute_batch_metrics(db, batch_id=batch_id)
    db.close()

    print("\n=======================================================")
    print("      FULL HYBRID SYSTEM METRICS EVALUATION OUTPUT     ")
    print("=======================================================")
    print(f"Batch ID: {batch_id}")
    print(f"Total Scored: {metrics['total_scored']}")
    print(f"Confusion Matrix: TP={metrics['confusion_matrix']['tp']}, FP={metrics['confusion_matrix']['fp']}, FN={metrics['confusion_matrix']['fn']}, TN={metrics['confusion_matrix']['tn']}")
    print(f"Precision: {metrics['precision']:.4f} ({metrics['precision']*100:.2f}%)")
    print(f"Recall:    {metrics['recall']:.4f} ({metrics['recall']*100:.2f}%)")
    print(f"F1 Score:  {metrics['f1_score']:.4f}")
    
    fp_rate = metrics['confusion_matrix']['fp'] / (metrics['confusion_matrix']['fp'] + metrics['confusion_matrix']['tn']) if (metrics['confusion_matrix']['fp'] + metrics['confusion_matrix']['tn']) > 0 else 0.0
    fn_rate = metrics['confusion_matrix']['fn'] / (metrics['confusion_matrix']['fn'] + metrics['confusion_matrix']['tp']) if (metrics['confusion_matrix']['fn'] + metrics['confusion_matrix']['tp']) > 0 else 0.0
    
    print(f"False Positive Rate (FPR): {fp_rate:.4f} ({fp_rate*100:.2f}%)")
    print(f"False Negative Rate (FNR): {fn_rate:.4f} ({fn_rate*100:.2f}%)")
    print(f"Total FP Cost Exposure: ₹{metrics['total_fp_cost_exposure']:,.2f}")
    print(f"Total FN Cost Exposure: ₹{metrics['total_fn_cost_exposure']:,.2f}")
    print(f"Decision Split: Rule={metrics['rule_percent']}% ({metrics['rule_decided_count']}), LLM/Fallback={metrics['llm_percent']}% ({metrics['llm_decided_count'] + metrics['degraded_count']})")
    print("=======================================================\n")

if __name__ == "__main__":
    run_hybrid_evaluation()
