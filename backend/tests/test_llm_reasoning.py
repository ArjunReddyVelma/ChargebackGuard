import os
import pytest
from app.llm_reasoning import generate_llm_reasoning, fallback_rule_reasoning

def test_er2_fallback_when_key_missing_or_placeholder(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "your_anthropic_api_key_here")
    tx = {
        "transaction_id": "TX_AMBIG_1",
        "amount": 15000.0,
        "payment_method": "card",
        "device_id": "DEV_AMBIG",
        "is_new_device": True,
        "ip_country": "SG",
        "billing_country": "IN",
        "account_age_days": 10,
        "velocity_10min": 2,
        "avg_user_amount": 1000.0
    }
    score, reasons, decided_by = generate_llm_reasoning(tx, ["Pre-rule signal"])
    
    assert decided_by == "degraded_reasoning"
    assert 0 <= score <= 100
    assert any("ER-2" in r for r in reasons)

def test_sec6_prompt_safety_scoped_fields(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "your_anthropic_api_key_here")
    tx_with_label = {
        "transaction_id": "TX_AMBIG_2",
        "amount": 5000.0,
        "is_new_device": True,
        "ip_country": "IN",
        "billing_country": "IN",
        "account_age_days": 5,
        "velocity_10min": 1,
        "avg_user_amount": 500.0,
        "is_fraud": True  # Ground truth label!
    }
    # generate_llm_reasoning strips 'is_fraud' before sending prompt
    score, reasons, decided_by = generate_llm_reasoning(tx_with_label, [])
    assert decided_by == "degraded_reasoning"
