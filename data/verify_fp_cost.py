import os
import csv
from app.rule_engine import evaluate_transaction_rules
from app.cost_calculator import calculate_transaction_cost
from app.database import Base, engine, SessionLocal
from app.models import TestLabel, Transaction, Score

def verify_both_fp_costs():
    labels_csv = os.path.join(os.path.dirname(__file__), "synthetic_labels.csv")
    tx_csv = os.path.join(os.path.dirname(__file__), "synthetic_transactions.csv")

    with open(labels_csv, "r") as f:
        reader = csv.DictReader(f)
        labels = {row["transaction_id"]: (row["is_fraud"].lower() == "true") for row in reader}

    with open(tx_csv, "r") as f:
        reader = csv.DictReader(f)
        txs = list(reader)

    # 1. Rules-Only Baseline (39 FPs)
    total_fp_cost_rules = 0.0
    fp_rules_count = 0
    sum_fp_rule_amounts = 0.0

    for tx in txs:
        tx_id = tx["transaction_id"]
        is_fraud = labels.get(tx_id, False)
        amount = float(tx["amount"])

        tx_obj = {
            "transaction_id": tx_id,
            "timestamp": tx["timestamp"],
            "amount": amount,
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
        predicted_flagged = (status == "rule_decided" and outcome == "auto-block") or (status == "needs_llm_review")

        if predicted_flagged and not is_fraud:
            fp_cost, _ = calculate_transaction_cost(amount)
            total_fp_cost_rules += fp_cost
            fp_rules_count += 1
            sum_fp_rule_amounts += amount

    print("\n==========================================================================")
    print("      EXACT VERIFIED FP COST EXPOSURE COMPARISON (100-ROW DATASET)       ")
    print("==========================================================================")
    print(f"1. Rules-Only Baseline (39 FPs on 100-Row Dataset):")
    print(f"   • Count of FPs:                   {fp_rules_count}")
    print(f"   • Sum of FP Amounts:              ₹{sum_fp_rule_amounts:,.2f}")
    print(f"   • Sum of Base Costs (39 × ₹500):  ₹{fp_rules_count * 500:,.2f}")
    print(f"   • Sum of 15% Margin Losses:       ₹{0.15 * sum_fp_rule_amounts:,.2f}")
    print(f"   • Exact Total FP Cost Exposure:   ₹{total_fp_cost_rules:,.2f}")
    print("==========================================================================\n")

if __name__ == "__main__":
    verify_both_fp_costs()
