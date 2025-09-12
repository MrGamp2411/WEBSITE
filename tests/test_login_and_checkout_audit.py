import os
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import AuditLog  # noqa: E402
from main import app  # noqa: E402
from tests.test_cancel_order import setup_db, create_order  # noqa: E402


def test_login_creates_audit_log():
    setup_db()
    with TestClient(app) as client:
        resp = client.post(
            "/login",
            data={"email": "admin@example.com", "password": "ChangeMe!123"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
    db = SessionLocal()
    logs = db.query(AuditLog).all()
    assert any(log.action == "login" for log in logs)
    db.close()


def test_checkout_creates_audit_log():
    setup_db()
    with TestClient(app) as client:
        ids = create_order(client, "wallet")
    db = SessionLocal()
    logs = db.query(AuditLog).all()
    assert any(
        log.action == "order_create" and log.entity_id == ids["order_id"]
        for log in logs
    )
    db.close()
