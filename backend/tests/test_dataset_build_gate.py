import os
import csv
import pytest
from data.generate_dataset import generate_synthetic_dataset, run_build_gate_check, TRANSACTIONS_CSV, LABELS_CSV

def test_dataset_generation_and_build_gate():
    # 1. Generate dataset
    generate_synthetic_dataset(num_records=600)
    
    assert os.path.exists(TRANSACTIONS_CSV), "Transactions CSV must be generated"
    assert os.path.exists(LABELS_CSV), "Labels CSV must be generated"
    
    # 2. Assert DR-1 (No label leakage in scoring input)
    with open(TRANSACTIONS_CSV, "r") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        assert "is_fraud" not in header, "CRITICAL DR-1 VIOLATION: 'is_fraud' column leaked into scoring input file!"

    # 3. Assert Ground Truth labels exist separately
    with open(LABELS_CSV, "r") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        assert "transaction_id" in header and "is_fraud" in header
        rows = list(reader)
        assert len(rows) == 600

    # 4. Run Build Gate Check
    res = run_build_gate_check()
    assert res["passed"] is True
    assert res["precision"] <= 0.95, f"Rules-only precision too high: {res['precision']}"
    assert res["recall"] <= 0.95, f"Rules-only recall too high: {res['recall']}"
