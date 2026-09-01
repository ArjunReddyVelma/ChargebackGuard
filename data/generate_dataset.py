import os
import csv
import random
from datetime import datetime, timedelta, timezone

# Seed for reproducibility
SEED = 42
random.seed(SEED)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
TRANSACTIONS_CSV = os.path.join(OUTPUT_DIR, "synthetic_transactions.csv")
LABELS_CSV = os.path.join(OUTPUT_DIR, "synthetic_labels.csv")

COUNTRIES = ["IN", "IN", "IN", "IN", "US", "SG", "GB", "AE", "CA"]
PAYMENT_METHODS = ["UPI", "card", "netbanking", "wallet"]

def generate_synthetic_dataset(num_records=600):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    transactions = []
    labels = []

    base_time = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)

    for i in range(1, num_records + 1):
        tx_id = f"TXN_{i:05d}"
        timestamp = (base_time + timedelta(minutes=i * 2)).isoformat()
        
        # Decide scenario
        # ~10% target fraud rate (60 fraud, 540 legit)
        rand_val = random.random()
        
        if rand_val < 0.04:
            # Pattern 1: High fraud probability (Geo mismatch + velocity + new device)
            is_fraud = True
            amount = round(random.uniform(5000, 45000), 2)
            payment_method = random.choice(["card", "netbanking"])
            device_id = f"DEV_FRAUD_{random.randint(1, 10)}"
            is_new_device = True
            ip_country = "SG"
            billing_country = "IN"
            shipping_country = "US"
            account_age_days = random.randint(0, 5)
            velocity_10min = random.randint(4, 12)
            avg_user_amount = round(random.uniform(200, 1500), 2)

        elif rand_val < 0.07:
            # Pattern 2: Ambiguous Fraud (New device + high amount, but low velocity)
            is_fraud = True
            amount = round(random.uniform(15000, 60000), 2)
            payment_method = random.choice(["UPI", "card"])
            device_id = f"DEV_AMBIG_{random.randint(1, 20)}"
            is_new_device = True
            ip_country = "IN"
            billing_country = "IN"
            shipping_country = "IN"
            account_age_days = random.randint(10, 90)
            velocity_10min = random.randint(1, 2)  # Low velocity! Rules might miss this
            avg_user_amount = round(random.uniform(1000, 3000), 2)

        elif rand_val < 0.10:
            # Pattern 3: Ambiguous Fraud (Geo mismatch alone, moderate velocity)
            is_fraud = True
            amount = round(random.uniform(2000, 12000), 2)
            payment_method = random.choice(PAYMENT_METHODS)
            device_id = f"DEV_GEO_{random.randint(1, 20)}"
            is_new_device = False
            ip_country = random.choice(["US", "GB", "AE"])
            billing_country = "IN"
            shipping_country = None  # Digital goods
            account_age_days = random.randint(30, 365)
            velocity_10min = random.randint(1, 3)
            avg_user_amount = round(random.uniform(1500, 5000), 2)

        elif rand_val < 0.15:
            # Pattern 4: Ambiguous Legitimate (Looks like fraud to rules, but actually LEGIT)
            # e.g., Traveler / Flash Sale buyer (New device or IP mismatch, high amount, but legitimate)
            is_fraud = False
            amount = round(random.uniform(10000, 50000), 2)
            payment_method = "card"
            device_id = f"DEV_LEGIT_TRAVEL_{random.randint(1, 30)}"
            is_new_device = True
            ip_country = random.choice(["SG", "AE", "US"])  # Traveler IP
            billing_country = "IN"
            shipping_country = "IN"
            account_age_days = random.randint(180, 1000)
            velocity_10min = random.randint(3, 6)  # High velocity due to sale!
            avg_user_amount = round(random.uniform(8000, 25000), 2)

        else:
            # Pattern 5: Clear Legitimate
            is_fraud = False
            amount = round(random.uniform(100, 8000), 2)
            payment_method = random.choice(PAYMENT_METHODS)
            device_id = f"DEV_USER_{random.randint(1, 200)}"
            is_new_device = random.random() < 0.1
            ip_country = "IN"
            billing_country = "IN"
            shipping_country = "IN" if random.random() > 0.2 else None
            account_age_days = random.randint(15, 1200)
            velocity_10min = random.randint(0, 2)
            avg_user_amount = round(amount * random.uniform(0.6, 1.4), 2)

        tx_record = {
            "transaction_id": tx_id,
            "timestamp": timestamp,
            "amount": amount,
            "payment_method": payment_method,
            "device_id": device_id,
            "is_new_device": is_new_device,
            "ip_country": ip_country,
            "billing_country": billing_country,
            "shipping_country": shipping_country or "",
            "account_age_days": account_age_days,
            "velocity_10min": velocity_10min,
            "avg_user_amount": avg_user_amount,
        }
        
        label_record = {
            "transaction_id": tx_id,
            "is_fraud": is_fraud
        }
        
        transactions.append(tx_record)
        labels.append(label_record)

    # Write synthetic_transactions.csv (DR-1: NO is_fraud field!)
    with open(TRANSACTIONS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(transactions[0].keys()))
        writer.writeheader()
        writer.writerows(transactions)

    # Write synthetic_labels.csv (DR-1: Ground truth stored separately!)
    with open(LABELS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["transaction_id", "is_fraud"])
        writer.writeheader()
        writer.writerows(labels)

    print(f"Generated {len(transactions)} synthetic transactions -> {TRANSACTIONS_CSV}")
    print(f"Generated {len(labels)} ground truth labels -> {LABELS_CSV}")


def run_build_gate_check():
    """
    Build Gate Check per Phase 1 & Requirement 5:
    Evaluates a naive rules-only baseline against the dataset.
    Verifies that rules-only precision and recall do NOT exceed ~95%.
    If rules achieve >95%, the dataset is too simple/separable.
    """
    with open(TRANSACTIONS_CSV, "r") as f:
        tx_rows = list(csv.DictReader(f))

    with open(LABELS_CSV, "r") as f:
        label_map = {row["transaction_id"]: (row["is_fraud"].lower() == "true") for row in csv.DictReader(f)}

    tp = fp = fn = tn = 0

    for row in tx_rows:
        tx_id = row["transaction_id"]
        actual_fraud = label_map[tx_id]
        
        # Naive rules baseline:
        # Rule 1: velocity >= 4
        # Rule 2: ip_country != billing_country AND is_new_device
        # Rule 3: amount > 5 * avg_user_amount (if avg_user_amount > 0)
        
        velocity = int(row["velocity_10min"])
        is_new_dev = (row["is_new_device"].lower() == "true")
        ip_c = row["ip_country"]
        bill_c = row["billing_country"]
        amount = float(row["amount"])
        avg_amount = float(row["avg_user_amount"])

        rule_flagged = False
        if velocity >= 4:
            rule_flagged = True
        elif is_new_dev and ip_c != bill_c:
            rule_flagged = True
        elif avg_amount > 0 and amount > (4.0 * avg_amount):
            rule_flagged = True

        if rule_flagged and actual_fraud:
            tp += 1
        elif rule_flagged and not actual_fraud:
            fp += 1
        elif not rule_flagged and actual_fraud:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    print("\n--- Build Gate Check (Rules-Only Baseline) ---")
    print(f"Total Transactions: {len(tx_rows)}")
    print(f"Actual Fraud Count: {sum(1 for v in label_map.values() if v)}")
    print(f"Rules Flagged Count: {tp + fp}")
    print(f"True Positives: {tp}, False Positives: {fp}")
    print(f"False Negatives: {fn}, True Negatives: {tn}")
    print(f"Precision: {precision:.4f} ({precision*100:.2f}%)")
    print(f"Recall:    {recall:.4f} ({recall*100:.2f}%)")
    print(f"F1 Score:  {f1:.4f}")

    # Build Gate Assertions (Requirement 5):
    # Must NOT exceed 95% precision or 95% recall.
    max_threshold = 0.95
    if precision > max_threshold or recall > max_threshold:
        raise ValueError(
            f"BUILD GATE FAILED: Rules-only baseline achieved precision={precision*100:.2f}%, recall={recall*100:.2f}%. "
            f"Dataset is too separable (>95%). Need more ambiguity for LLM layer to add value."
        )

    print("✅ BUILD GATE PASSED: Rules-only baseline exhibits realistic ambiguity (<95% precision/recall). Proceeding!")
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "passed": True
    }


if __name__ == "__main__":
    generate_synthetic_dataset(num_records=600)
    run_build_gate_check()
