import os
from decimal import Decimal
from datetime import datetime, timedelta
import pathlib
import sys

# Use shared in-memory SQLite database
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import Bar, Order, AuditLog, User  # noqa: E402
from main import app  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_run_payout_creates_audit_log():
    db = SessionLocal()
    bar = Bar(name="Audit Bar", slug="audit-bar")
    db.add(bar)
    db.commit()
    db.refresh(bar)
    bar_id = bar.id

    now = datetime.utcnow()
    order = Order(
        bar_id=bar.id,
        subtotal=Decimal("100.00"),
        vat_total=Decimal("7.70"),
        fee_platform_5pct=Decimal("5.00"),
        payout_due_to_bar=Decimal("102.70"),
        status="COMPLETED",
        created_at=now,
    )
    db.add(order)
    db.commit()
    db.close()

    with TestClient(app) as client:
        resp = client.post(
            "/login",
            data={"email": "admin@example.com", "password": "ChangeMe!123"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

        payload = {
            "bar_id": bar_id,
            "period_start": (now - timedelta(days=1)).isoformat(),
            "period_end": (now + timedelta(days=1)).isoformat(),
        }
        resp = client.post("/api/payouts/run", json=payload)
        assert resp.status_code == 201
        payout_id = resp.json()["id"]

    db = SessionLocal()
    admin = db.query(User).filter(User.email == "admin@example.com").one()
    logs = db.query(AuditLog).all()
    assert any(
        log.actor_user_id == admin.id
        and log.action == "payout_run"
        and log.entity_type == "payout"
        and log.entity_id == payout_id
        for log in logs
    )
    db.close()


def test_run_payout_rejects_spoofed_actor_id():
    db = SessionLocal()
    bar = Bar(name="Spoofed Actor Bar", slug="spoofed-actor-bar")
    db.add(bar)
    db.commit()
    db.refresh(bar)
    bar_id = bar.id

    now = datetime.utcnow()
    db.add(
        Order(
            bar_id=bar.id,
            subtotal=Decimal("100.00"),
            vat_total=Decimal("7.70"),
            fee_platform_5pct=Decimal("5.00"),
            payout_due_to_bar=Decimal("102.70"),
            status="COMPLETED",
            created_at=now,
        )
    )
    db.commit()
    db.close()

    with TestClient(app) as client:
        resp = client.post(
            "/login",
            data={"email": "admin@example.com", "password": "ChangeMe!123"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

        db = SessionLocal()
        admin = db.query(User).filter(User.email == "admin@example.com").one()
        payload = {
            "bar_id": bar_id,
            "period_start": (now - timedelta(days=1)).isoformat(),
            "period_end": (now + timedelta(days=1)).isoformat(),
            "actor_user_id": admin.id + 100,
        }
        db.close()

        resp = client.post("/api/payouts/run", json=payload)
        assert resp.status_code == 400

    db = SessionLocal()
    logs = db.query(AuditLog).filter(AuditLog.action == "payout_run_actor_mismatch_attempt").all()
    db.close()
    assert logs, "Expected mismatch attempt to be logged"
