import os
import pytest
from fastapi.testclient import TestClient
from main import app
from app.database import Base, engine, SessionLocal
from app.auth import seed_demo_users
from data.seed_labels import seed_test_labels
from data.generate_dataset import generate_synthetic_dataset, TRANSACTIONS_CSV, LABELS_CSV

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_e2e_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_demo_users(db)
    db.close()
    
    # Ensure synthetic dataset exists & seed labels
    generate_synthetic_dataset(num_records=100)
    seed_test_labels()
    
    yield
    Base.metadata.drop_all(bind=engine)

def test_full_end_to_end_system_flow():
    # 1. Login as Analyst & Risk Manager
    res_analyst = client.post("/auth/login", json={"email": "analyst@chargebackguard.io", "password": "analyst123"})
    assert res_analyst.status_code == 200
    analyst_token = res_analyst.json()["access_token"]

    res_manager = client.post("/auth/login", json={"email": "manager@chargebackguard.io", "password": "manager123"})
    assert res_manager.status_code == 200
    manager_token = res_manager.json()["access_token"]

    # 2. Batch Upload (FR-1)
    with open(TRANSACTIONS_CSV, "rb") as f:
        upload_res = client.post("/batches", files={"file": ("batch.csv", f, "text/csv")})
    
    assert upload_res.status_code == 201
    batch_data = upload_res.json()
    assert batch_data["total_rows"] == 100
    assert batch_data["valid_rows_count"] == 100
    assert batch_data["quarantined_rows_count"] == 0

    # 3. Fetch Review Queue (FR-8)
    queue_res = client.get("/transactions?routing_outcome=review-queue")
    assert queue_res.status_code == 200
    queue_data = queue_res.json()
    assert "items" in queue_data

    if queue_data["items"]:
        target_tx_id = queue_data["items"][0]["transaction_id"]
        
        # 4. Fetch Transaction Detail (FR-4, FR-6)
        detail_res = client.get(f"/transactions/{target_tx_id}")
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        assert detail_data["transaction_id"] == target_tx_id
        assert detail_data["score"] is not None
        assert len(detail_data["reason_bullets"]) > 0
        assert detail_data["fp_cost_estimate"] > 0

        # 5. Analyst Decision Submission (FR-9, VR-3)
        decision_payload = {
            "decision": "confirm-block",
            "reason_text": "Analyst verified suspicious high velocity pattern and location anomaly."
        }
        dec_res = client.post(f"/transactions/{target_tx_id}/decision", json=decision_payload)
        assert dec_res.status_code == 200
        assert dec_res.json()["final_decision"] == "confirm-block"

    # 6. Metrics Calculation (FR-11, FR-12, FR-13)
    metrics_res = client.get("/metrics")
    assert metrics_res.status_code == 200
    metrics_data = metrics_res.json()
    assert metrics_data["total_scored"] == 100
    assert metrics_data["precision"] >= 0
    assert metrics_data["recall"] >= 0
    assert metrics_data["f1_score"] >= 0
    assert metrics_data["rule_percent"] + metrics_data["llm_percent"] == 100.0

    # 7. Risk Manager Config Update (FR-14, FR-15, AuthZ-2)
    headers_manager = {"Authorization": f"Bearer {manager_token}"}
    config_payload = {
        "low_threshold": 25,
        "high_threshold": 75,
        "fp_cost_base": 600.0,
        "fn_cost_fee": 2000.0
    }
    cfg_res = client.put("/config", headers=headers_manager, json=config_payload)
    assert cfg_res.status_code == 200
    assert cfg_res.json()["config"]["low_threshold"] == 25
