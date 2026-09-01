import os
import csv
from app.rule_engine import evaluate_transaction_rules
from app.scoring_service import assign_routing_outcome

def run_100row_comparison():
    labels_csv = os.path.join(os.path.dirname(__file__), "synthetic_labels.csv")
    tx_csv = os.path.join(os.path.dirname(__file__), "synthetic_transactions.csv")

    with open(labels_csv, "r") as f:
        reader = csv.DictReader(f)
        labels = {row["transaction_id"]: (row["is_fraud"].lower() == "true") for row in reader}

    with open(tx_csv, "r") as f:
        reader = csv.DictReader(f)
        txs = list(reader)

    total_count = len(txs)
    actual_fraud_count = sum(1 for tx in txs if labels.get(tx["transaction_id"], False))

    print(f"\n=======================================================")
    print(f"  DATASET STATISTICAL RIGOR INSPECTION (100-Row Subset) ")
    print(f"=======================================================")
    print(f"Total Transactions in Subset: {total_count}")
    print(f"Actual Fraud Transactions (is_fraud=True): {actual_fraud_count}")
    print(f"Actual Legit Transactions (is_fraud=False): {total_count - actual_fraud_count}")
    print(f"Base Fraud Prevalence: {actual_fraud_count / total_count * 100:.1f}%\n")

    # --- 1. RULES-ONLY BASELINE ON THE 100-ROW DATASET ---
    # Rules-only baseline treats any rule-triggered flag OR ambiguous 'needs_llm_review' as FLAGGED
    tp_rules = 0
    fp_rules = 0
    fn_rules = 0
    tn_rules = 0

    for tx in txs:
        tx_id = tx["transaction_id"]
        is_fraud = labels.get(tx_id, False)

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

        # Naive rules baseline: if rules flagged or sent to needs_llm_review -> predicted_flagged = True
        predicted_flagged = (status == "rule_decided" and outcome == "auto-block") or (status == "needs_llm_review")

        if predicted_flagged and is_fraud:
            tp_rules += 1
        elif predicted_flagged and not is_fraud:
            fp_rules += 1
        elif not predicted_flagged and is_fraud:
            fn_rules += 1
        else:
            tn_rules += 1

    prec_rules = tp_rules / (tp_rules + fp_rules) if (tp_rules + fp_rules) > 0 else 0.0
    rec_rules = tp_rules / (tp_rules + fn_rules) if (tp_rules + fn_rules) > 0 else 0.0
    f1_rules = 2 * (prec_rules * rec_rules) / (prec_rules + rec_rules) if (prec_rules + rec_rules) > 0 else 0.0
    fpr_rules = fp_rules / (fp_rules + tn_rules) if (fp_rules + tn_rules) > 0 else 0.0

    print("==========================================================================")
    print("  RULES-ONLY BASELINE (Evaluated on Identical 100-Transaction Subset)     ")
    print("==========================================================================")
    print(f"Confusion Matrix:          TP={tp_rules}, FP={fp_rules}, FN={fn_rules}, TN={tn_rules}")
    print(f"Precision:                 {prec_rules*100:.2f}% ({tp_rules}/{tp_rules+fp_rules})")
    print(f"Recall:                    {rec_rules*100:.2f}% ({tp_rules}/{tp_rules+fn_rules})")
    print(f"F1 Score:                  {f1_rules:.4f}")
    print(f"False Positive Rate (FPR): {fpr_rules*100:.2f}% ({fp_rules}/{fp_rules+tn_rules})")
    print("==========================================================================\n")

if __name__ == "__main__":
    run_100row_comparison()
