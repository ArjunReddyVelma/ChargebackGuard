import os
import csv
from app.rule_engine import evaluate_transaction_rules

def compare_rules():
    labels_csv = os.path.join(os.path.dirname(__file__), "synthetic_labels.csv")
    tx_csv = os.path.join(os.path.dirname(__file__), "synthetic_transactions.csv")

    with open(labels_csv, "r") as f:
        labels = {row["transaction_id"]: (row["is_fraud"].lower() == "true") for row in csv.DictReader(f)}

    with open(tx_csv, "r") as f:
        txs_100 = list(csv.DictReader(f))

    # --- 1. Phase 1 Build-Gate Naive 3-Rule Definition on 100-row subset ---
    tp1 = fp1 = fn1 = tn1 = 0
    for row in txs_100:
        tx_id = row["transaction_id"]
        actual_fraud = labels[tx_id]
        velocity = int(row["velocity_10min"])
        is_new_dev = (row["is_new_device"].lower() == "true")
        ip_c = row["ip_country"]
        bill_c = row["billing_country"]
        amount = float(row["amount"])
        avg_amount = float(row["avg_user_amount"])

        flagged = (velocity >= 4) or (is_new_dev and ip_c != bill_c) or (avg_amount > 0 and amount > 4.0 * avg_amount)

        if flagged and actual_fraud: tp1 += 1
        elif flagged and not actual_fraud: fp1 += 1
        elif not flagged and actual_fraud: fn1 += 1
        else: tn1 += 1

    p1 = tp1 / (tp1 + fp1) if (tp1 + fp1) > 0 else 0
    r1 = tp1 / (tp1 + fn1) if (tp1 + fn1) > 0 else 0
    f1_1 = 2 * p1 * r1 / (p1 + r1) if (p1 + r1) > 0 else 0

    # --- 2. Production evaluate_transaction_rules (Rule Engine) on 100-row subset ---
    tp2 = fp2 = fn2 = tn2 = 0
    for row in txs_100:
        tx_id = row["transaction_id"]
        actual_fraud = labels[tx_id]
        tx_obj = {
            "transaction_id": tx_id,
            "timestamp": row["timestamp"],
            "amount": float(row["amount"]),
            "payment_method": row["payment_method"],
            "device_id": row["device_id"],
            "is_new_device": row["is_new_device"].lower() == "true",
            "ip_country": row["ip_country"],
            "billing_country": row["billing_country"],
            "shipping_country": row.get("shipping_country") or None,
            "account_age_days": int(row["account_age_days"]),
            "velocity_10min": int(row["velocity_10min"]),
            "avg_user_amount": float(row["avg_user_amount"])
        }
        status, score, outcome, rule_name, reasons = evaluate_transaction_rules(tx_obj)
        flagged = (status == "rule_decided" and outcome == "auto-block") or (status == "needs_llm_review")

        if flagged and actual_fraud: tp2 += 1
        elif flagged and not actual_fraud: fp2 += 1
        elif not flagged and actual_fraud: fn2 += 1
        else: tn2 += 1

    p2 = tp2 / (tp2 + fp2) if (tp2 + fp2) > 0 else 0
    r2 = tp2 / (tp2 + fn2) if (tp2 + fn2) > 0 else 0
    f1_2 = 2 * p2 * r2 / (p2 + r2) if (p2 + r2) > 0 else 0

    print("\n==========================================================================")
    print("      RULE DEFINITION COMPARISON ON THE 100-TRANSACTION DATASET           ")
    print("==========================================================================")
    print("Rule Logic Variant                          | Precision | Recall  | F1 Score | TP | FP | FN | TN")
    print("--------------------------------------------+-----------+---------+----------+----+----+----+---")
    print(f"Phase 1 Naive 3-Rule Heuristic              | {p1*100:5.2f}%   | {r1*100:5.2f}%  | {f1_1:.4f}   | {tp1:2d} | {fp1:2d} | {fn1:2d} | {tn1:2d}")
    print(f"Production Rule Engine (needs_llm_review)   | {p2*100:5.2f}%   | {r2*100:5.2f}%  | {f1_2:.4f}   | {tp2:2d} | {fp2:2d} | {fn2:2d} | {tn2:2d}")
    print("==========================================================================\n")

if __name__ == "__main__":
    compare_rules()
