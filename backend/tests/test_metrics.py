import pytest
from fastapi.testclient import TestClient
from main import app
from app.database import Base, engine, SessionLocal
from app.models import TestLabel

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Seed Ground Truth Test Labels (DR-1 compliant!)
    db.add(TestLabel(transaction_id="TX_METRIC_1", is_fraud=True))
    db.add(TestLabel(transaction_id="TX_METRIC_2", is_fraud=False))
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)

def test_metrics_endpoint():
    csv_content = (
        "transaction_id,timestamp,amount,payment_method,device_id,is_new_device,ip_country,billing_country,shipping_country,account_age_days,velocity_10min,avg_user_amount\n"
        "TX_METRIC_1,2026-08-01T10:00:00Z,20000.0,card,DEV_1,true,SG,IN,IN,2,8,500.0\n" # Flagged fraud (TP)
        "TX_METRIC_2,2026-08-01T10:05:00Z,100.0,UPI,DEV_2,false,IN,IN,IN,100,1,100.0\n"  # Auto-clear legit (TN)
    )
    client.post("/batches", files={"file": ("test.csv", csv_content, "text/csv")})

    res = client.get("/metrics")
    assert res.status_code == 200
    data = res.json()

    assert data["total_scored"] == 2
    assert data["precision"] == 1.0
    assert data["recall"] == 1.0
    assert data["f1_score"] == 1.0
    assert data["confusion_matrix"]["tp"] == 1
    assert data["confusion_matrix"]["tn"] == 1
    assert data["rule_percent"] == 100.0
