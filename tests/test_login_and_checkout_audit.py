import os
import sys
import pathlib
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import AuditLog, User  # noqa: E402
from main import app  # noqa: E402
from tests.helpers import trust_testclient_proxy  # noqa: E402
from tests.test_cancel_order import setup_db, create_order  # noqa: E402


def test_login_creates_audit_log():
    setup_db()
    with TestClient(app) as client:
        resp = client.post(
            "/login",
            data={
                "email": "admin@example.com",
                "password": "ChangeMe!123",
                "latitude": "12.34",
                "longitude": "56.78",
            },
            follow_redirects=False,
            headers={"User-Agent": "test-agent"},
        )
        assert resp.status_code == 303
    db = SessionLocal()
    logs = db.query(AuditLog).all()
    assert any(log.action == "login" for log in logs)
    assert any(
        log.action == "POST /login"
        and log.user_agent == "test-agent"
        and log.phone is None
        and log.ip
        and log.actor_credit == Decimal("0")
        for log in logs
    )
    assert any(
        log.action == "login"
        and log.latitude == Decimal("12.34")
        and log.longitude == Decimal("56.78")
        for log in logs
    )
    db.close()


def test_register_creates_audit_log():
    setup_db()
    with trust_testclient_proxy():
        with TestClient(app) as client:
            resp = client.post(
                "/register",
                data={
                    "email": "newuser@example.com",
                    "password": "Str0ngPass!",
                    "confirm_password": "Str0ngPass!",
                },
                follow_redirects=False,
                headers={
                    "User-Agent": "test-agent",
                    "X-Forwarded-For": "2001:db8::1",
                },
            )
            assert resp.status_code == 303
            assert resp.headers["location"] == "/register/details"
    db = SessionLocal()
    user = db.query(User).filter(User.email == "newuser@example.com").one()
    logs = db.query(AuditLog).filter(AuditLog.action == "register").all()
    assert logs
    assert any(log.actor_user_id == user.id and log.entity_id == user.id for log in logs)
    assert any(log.ip == "2001:db8::1" for log in logs)
    assert any(log.user_agent == "test-agent" for log in logs)
    db.close()


def test_checkout_creates_audit_log():
    setup_db()
    with TestClient(app) as client:
        ids = create_order(client, "wallet")
    db = SessionLocal()
    logs = db.query(AuditLog).all()
    assert any(
        log.action == "order_create"
        and log.entity_id == ids["order_id"]
        and log.actor_credit == Decimal("4.8")
        for log in logs
    )
    db.close()
