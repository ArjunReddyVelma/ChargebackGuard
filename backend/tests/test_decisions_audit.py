import pytest
from fastapi.testclient import TestClient
from main import app
from app.database import Base, engine, SessionLocal
from app.models import AuditLog, Decision

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_analyst_decision_submission_and_audit_trail():
    # 1. Ingest batch
    csv_content = (
        "transaction_id,timestamp,amount,payment_method,device_id,is_new_device,ip_country,billing_country,shipping_country,account_age_days,velocity_10min,avg_user_amount\n"
        "TX_DECISION_1,2026-08-01T10:00:00Z,15000.0,card,DEV_AMBIG,true,SG,IN,IN,10,2,1000.0\n"
    )
    client.post("/batches", files={"file": ("test.csv", csv_content, "text/csv")})

    # 2. Submit Analyst Decision with valid reason (VR-3)
    decision_payload = {
        "decision": "confirm-block",
        "reason_text": "High amount on new device with SG IP mismatch confirmed fraudulent pattern."
    }
    res = client.post("/transactions/TX_DECISION_1/decision", json=decision_payload)
    assert res.status_code == 200
    assert res.json()["final_decision"] == "confirm-block"

    # 3. Test EC-5 Concurrent Decision Race Condition (Second attempt gets 409 ALREADY_DECIDED)
    res_second = client.post("/transactions/TX_DECISION_1/decision", json=decision_payload)
    assert res_second.status_code == 409
    assert res_second.json()["detail"]["error_code"] == "ALREADY_DECIDED"

    # 4. Verify Immutable Audit Log record (BR-1 / FR-10)
    db = SessionLocal()
    audit_entries = db.query(AuditLog).filter(AuditLog.transaction_id == "TX_DECISION_1").all()
    assert len(audit_entries) >= 1
    override_log = [log for log in audit_entries if log.event_type == "override"][0]
    assert override_log.actor_role == "Analyst"
    assert "confirm-block" in override_log.details
    db.close()

def test_decision_reason_too_short_rejection():
    # VR-3: reason text < 10 chars rejected
    csv_content = (
        "transaction_id,timestamp,amount,payment_method,device_id,is_new_device,ip_country,billing_country,shipping_country,account_age_days,velocity_10min,avg_user_amount\n"
        "TX_SHORT_1,2026-08-01T10:00:00Z,5000.0,card,DEV_1,true,IN,IN,IN,5,1,100.0\n"
    )
    client.post("/batches", files={"file": ("test.csv", csv_content, "text/csv")})

    res = client.post("/transactions/TX_SHORT_1/decision", json={"decision": "confirm-clear", "reason_text": "Short"})
    assert res.status_code == 422  # Pydantic VR-3 validation rejection
