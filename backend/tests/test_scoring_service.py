import pytest
from app.scoring_service import assign_routing_outcome, assert_no_label_leakage, score_and_route_transaction

def test_ec4_deterministic_boundary_threshold_routing():
    # low_threshold=30, high_threshold=70
    assert assign_routing_outcome(29, 30, 70) == "auto-clear"
    assert assign_routing_outcome(30, 30, 70) == "review-queue"  # Boundary low == review-queue!
    assert assign_routing_outcome(50, 30, 70) == "review-queue"
    assert assign_routing_outcome(70, 30, 70) == "review-queue"  # Boundary high == review-queue (EC-4)!
    assert assign_routing_outcome(71, 30, 70) == "auto-block"

def test_dr1_label_leakage_assertion():
    tx = {
        "transaction_id": "TX_LEAK",
        "amount": 100.0,
        "is_fraud": True  # Ground truth label!
    }
    with pytest.raises(ValueError, match="CRITICAL DR-1 VIOLATION"):
        assert_no_label_leakage(tx)

def test_full_scoring_pipeline_rule_decided():
    tx = {
        "transaction_id": "TX_TRUSTED",
        "timestamp": "2026-08-01T10:00:00Z",
        "amount": 100.0,
        "payment_method": "UPI",
        "device_id": "DEV_TRUSTED",
        "is_new_device": False,
        "ip_country": "IN",
        "billing_country": "IN",
        "shipping_country": "IN",
        "account_age_days": 100,
        "velocity_10min": 1,
        "avg_user_amount": 100.0
    }
    score, routing_outcome, decided_by, rule_name, reasons = score_and_route_transaction(tx)
    assert decided_by == "rule"
    assert routing_outcome == "auto-clear"
    assert score == 5
