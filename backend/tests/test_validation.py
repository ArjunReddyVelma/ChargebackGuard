import pytest
from app.schemas import TransactionIngestSchema, DecisionSubmitSchema, ThresholdConfigSchema

def test_vr1_invalid_amount():
    data = {
        "transaction_id": "TX_INVALID_1",
        "timestamp": "2026-08-01T10:00:00Z",
        "amount": -50.0,
        "payment_method": "UPI",
        "device_id": "DEV_1",
        "is_new_device": False,
        "ip_country": "IN",
        "billing_country": "IN",
        "account_age_days": 10,
        "velocity_10min": 1,
        "avg_user_amount": 100.0
    }
    with pytest.raises(ValueError, match="INVALID_AMOUNT"):
        TransactionIngestSchema(**data)

def test_vr2_invalid_country_code():
    data = {
        "transaction_id": "TX_INVALID_2",
        "timestamp": "2026-08-01T10:00:00Z",
        "amount": 500.0,
        "payment_method": "card",
        "device_id": "DEV_1",
        "is_new_device": False,
        "ip_country": "INDIA",  # Invalid 5-char country code!
        "billing_country": "IN",
        "account_age_days": 10,
        "velocity_10min": 1,
        "avg_user_amount": 100.0
    }
    with pytest.raises(ValueError, match="INVALID_COUNTRY_CODE"):
        TransactionIngestSchema(**data)

def test_vr3_reason_too_short():
    with pytest.raises(ValueError, match="REASON_TOO_SHORT"):
        DecisionSubmitSchema(decision="confirm-block", reason_text="Short")

def test_vr3_valid_reason():
    schema = DecisionSubmitSchema(decision="confirm-block", reason_text="This is a valid long reason for decision.")
    assert schema.reason_text == "This is a valid long reason for decision."

def test_vr5_invalid_threshold_config():
    with pytest.raises(ValueError, match="INVALID_THRESHOLD_CONFIG"):
        ThresholdConfigSchema(low_threshold=80, high_threshold=30)  # low >= high!
