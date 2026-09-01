import pytest
from fastapi.testclient import TestClient
from main import app
from app.database import Base, engine

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_batch_upload_with_quarantine_and_rules():
    csv_content = (
        "transaction_id,timestamp,amount,payment_method,device_id,is_new_device,ip_country,billing_country,shipping_country,account_age_days,velocity_10min,avg_user_amount\n"
        "TX_101,2026-08-01T10:00:00Z,500.0,UPI,DEV_1,false,IN,IN,IN,100,1,500.0\n"
        "TX_102,2026-08-01T10:05:00Z,-50.0,card,DEV_2,true,IN,IN,IN,10,1,100.0\n"  # Invalid amount (VR-1)!
        "TX_101,2026-08-01T10:10:00Z,200.0,card,DEV_3,false,IN,IN,IN,50,0,200.0\n" # Duplicate ID (VR-6)!
    )

    response = client.post(
        "/batches",
        files={"file": ("test_batch.csv", csv_content, "text/csv")}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["total_rows"] == 3
    assert data["valid_rows_count"] == 1
    assert data["quarantined_rows_count"] == 2
    assert len(data["quarantined_errors"]) == 2
    
    err_codes = [err["error_code"] for err in data["quarantined_errors"]]
    assert "INVALID_AMOUNT" in err_codes
    assert "DUPLICATE_TRANSACTION_ID" in err_codes
