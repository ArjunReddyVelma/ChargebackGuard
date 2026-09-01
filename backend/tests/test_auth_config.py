import pytest
from fastapi.testclient import TestClient
from main import app
from app.database import Base, engine, SessionLocal
from app.auth import seed_demo_users
from app.models import AuditLog

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_demo_users(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)

def test_authn_login_success_and_failure():
    # 1. Successful Login as Analyst
    res = client.post("/auth/login", json={"email": "analyst@chargebackguard.io", "password": "analyst123"})
    assert res.status_code == 200
    assert "access_token" in res.json()
    assert res.json()["role"] == "Analyst"

    # 2. Failed Login (AuthN-3)
    res_failed = client.post("/auth/login", json={"email": "analyst@chargebackguard.io", "password": "wrongpassword"})
    assert res_failed.status_code == 401
    assert res_failed.json()["detail"]["error_code"] == "INVALID_CREDENTIALS"

def test_authz_role_permission_matrix():
    # Get Analyst token
    res_analyst = client.post("/auth/login", json={"email": "analyst@chargebackguard.io", "password": "analyst123"})
    analyst_token = res_analyst.json()["access_token"]

    # Get Risk Manager token
    res_manager = client.post("/auth/login", json={"email": "manager@chargebackguard.io", "password": "manager123"})
    manager_token = res_manager.json()["access_token"]

    # 1. Analyst attempts PUT /config -> REJECTED 403 FORBIDDEN (AuthZ-2)
    headers_analyst = {"Authorization": f"Bearer {analyst_token}"}
    res_forbidden = client.put("/config", headers=headers_analyst, json={"low_threshold": 25, "high_threshold": 75, "fp_cost_base": 500, "fn_cost_fee": 1500})
    assert res_forbidden.status_code == 403
    assert res_forbidden.json()["detail"]["error_code"] == "FORBIDDEN"

    # 2. Risk Manager attempts PUT /config -> ALLOWED 200 OK
    headers_manager = {"Authorization": f"Bearer {manager_token}"}
    res_success = client.put("/config", headers=headers_manager, json={"low_threshold": 25, "high_threshold": 75, "fp_cost_base": 600.0, "fn_cost_fee": 1800.0})
    assert res_success.status_code == 200
    assert res_success.json()["config"]["low_threshold"] == 25

    # 3. Verify audit log entry created for config_change (FR-15)
    db = SessionLocal()
    audit_entries = db.query(AuditLog).filter(AuditLog.event_type == "config_change").all()
    assert len(audit_entries) >= 1
    assert "manager@chargebackguard.io" in audit_entries[0].actor_id
    db.close()

def test_vr5_invalid_threshold_config_rejected():
    res_manager = client.post("/auth/login", json={"email": "manager@chargebackguard.io", "password": "manager123"})
    manager_token = res_manager.json()["access_token"]
    headers_manager = {"Authorization": f"Bearer {manager_token}"}

    # Invalid low >= high config rejected with 422/400
    res_bad = client.put("/config", headers=headers_manager, json={"low_threshold": 80, "high_threshold": 20, "fp_cost_base": 500, "fn_cost_fee": 1500})
    assert res_bad.status_code in [400, 422]
