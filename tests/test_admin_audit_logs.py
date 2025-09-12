import os
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import AuditLog  # noqa: E402
from main import app  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _login_super_admin(client: TestClient) -> None:
    resp = client.post(
        "/login",
        data={"email": "admin@example.com", "password": "ChangeMe!123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_audit_log_filter_by_user():
    db = SessionLocal()
    log1 = AuditLog(
        actor_user_id=1,
        action="order",
        entity_type="order",
        entity_id=1,
        payload_json='{"bar_id": 1}'
    )
    log2 = AuditLog(
        actor_user_id=2,
        action="topup",
        entity_type="wallet",
        entity_id=2,
        payload_json='{"bar_id": 1}'
    )
    db.add_all([log1, log2])
    db.commit()
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)
        resp = client.get("/admin/audit?user_id=1")
        assert resp.status_code == 200
        assert "order" in resp.text
        assert "topup" not in resp.text
