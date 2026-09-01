import pytest
from app.rule_engine import evaluate_transaction_rules

def test_ec1_null_shipping_country():
    tx = {
        "transaction_id": "TX_EC1",
        "amount": 100.0,
        "velocity_10min": 1,
        "is_new_device": False,
        "ip_country": "IN",
        "billing_country": "IN",
        "shipping_country": None,  # EC-1: Null for digital goods
        "account_age_days": 100,
        "avg_user_amount": 100.0
    }
    status_tag, score, outcome, rule_name, reasons = evaluate_transaction_rules(tx)
    assert status_tag == "rule_decided"
    assert outcome == "auto-clear"
    # Verify shipping mismatch rule was NOT triggered erroneously
    assert not any("shipping" in r.lower() for r in reasons)

def test_ec2_zero_account_age_and_no_history():
    tx = {
        "transaction_id": "TX_EC2",
        "amount": 5000.0,
        "velocity_10min": 1,
        "is_new_device": True,
        "ip_country": "IN",
        "billing_country": "IN",
        "shipping_country": "IN",
        "account_age_days": 0,  # EC-2: Brand new account
        "avg_user_amount": 0.0   # No baseline amount
    }
    status_tag, score, outcome, rule_name, reasons = evaluate_transaction_rules(tx)
    # Should NOT crash with divide-by-zero, routes to LLM review cleanly
    assert status_tag == "needs_llm_review"
    assert any("0 days old" in r for r in reasons)

def test_ec6_extreme_velocity_anomaly():
    tx = {
        "transaction_id": "TX_EC6",
        "amount": 100.0,
        "velocity_10min": 999,  # EC-6: Extreme velocity anomaly
        "is_new_device": False,
        "ip_country": "IN",
        "billing_country": "IN",
        "account_age_days": 50,
        "avg_user_amount": 100.0
    }
    status_tag, score, outcome, rule_name, reasons = evaluate_transaction_rules(tx)
    assert status_tag == "rule_decided"
    assert outcome == "review-queue"
    assert rule_name == "ANOMALY_HIGH_VELOCITY"
    assert any("Data quality anomaly" in r for r in reasons)

def test_high_velocity_block_rule():
    tx = {
        "transaction_id": "TX_BLOCK",
        "amount": 20000.0,
        "velocity_10min": 8,
        "is_new_device": True,
        "ip_country": "SG",
        "billing_country": "IN",
        "account_age_days": 2,
        "avg_user_amount": 500.0
    }
    status_tag, score, outcome, rule_name, reasons = evaluate_transaction_rules(tx)
    assert status_tag == "rule_decided"
    assert outcome == "auto-block"
    assert score == 92
