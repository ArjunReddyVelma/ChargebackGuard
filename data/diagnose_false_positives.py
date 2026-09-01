import os
import csv
from app.database import Base, engine, SessionLocal
from app.models import TestLabel, Transaction, Score, ReasonChain
from app.rule_engine import evaluate_transaction_rules

def diagnose_fps():
    labels_csv = os.path.join(os.path.dirname(__file__), "synthetic_labels.csv")
    tx_csv = os.path.join(os.path.dirname(__file__), "synthetic_transactions.csv")

    with open(labels_csv, "r") as f:
        reader = csv.DictReader(f)
        labels = {row["transaction_id"]: (row["is_fraud"].lower() == "true") for row in reader}

    with open(tx_csv, "r") as f:
        reader = csv.DictReader(f)
        txs = list(reader)

    print("\n--- FALSE POSITIVE DIAGNOSTIC INSPECTION ---")
    fp_count = 0
    for tx in txs:
        tx_id = tx["transaction_id"]
        is_fraud = labels.get(tx_id, False)
        
        # Format types for rule evaluation
        tx_obj = {
            "transaction_id": tx_id,
            "timestamp": tx["timestamp"],
            "amount": float(tx["amount"]),
            "payment_method": tx["payment_method"],
            "device_id": tx["device_id"],
            "is_new_device": tx["is_new_device"].lower() == "true",
            "ip_country": tx["ip_country"],
            "billing_country": tx["billing_country"],
            "shipping_country": tx.get("shipping_country") or None,
            "account_age_days": int(tx["account_age_days"]),
            "velocity_10min": int(tx["velocity_10min"]),
            "avg_user_amount": float(tx["avg_user_amount"])
        }

        status, score, outcome, rule_name, reasons = evaluate_transaction_rules(tx_obj)
        
        # If it's actual legitimate (is_fraud=False) but gets flagged as ambiguous/high-risk
        if not is_fraud and status == "needs_llm_review":
            fp_count += 1
            if fp_count <= 6:
                print(f"\n[FP Sample #{fp_count}] TxID: {tx_id}")
                print(f"  Amount: ₹{tx_obj['amount']} (Avg: ₹{tx_obj['avg_user_amount']})")
                print(f"  Account Age: {tx_obj['account_age_days']} days | Velocity(10m): {tx_obj['velocity_10min']}")
                print(f"  New Device: {tx_obj['is_new_device']} | IP: {tx_obj['ip_country']} | Billing: {tx_obj['billing_country']} | Shipping: {tx_obj['shipping_country']}")
                print(f"  Pre-Analyzed Signals: {reasons}")

if __name__ == "__main__":
    diagnose_fps()
