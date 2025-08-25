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
from models import Bar, Order, AuditLog  # noqa: E402
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

    now = datetime.utcnow()
    order = Order(
        bar_id=bar.id,
        subtotal=Decimal("100.00"),
        vat_total=Decimal("7.70"),
        fee_platform_5pct=Decimal("5.00"),
        payout_due_to_bar=Decimal("102.70"),
        status="completed",
        created_at=now,
    )
    db.add(order)
    db.commit()

    client = TestClient(app)
    payload = {
        "bar_id": bar.id,
        "period_start": (now - timedelta(days=1)).isoformat(),
        "period_end": (now + timedelta(days=1)).isoformat(),
        "actor_user_id": 42,
    }
    resp = client.post("/api/payouts/run", json=payload)
    assert resp.status_code == 201
    payout_id = resp.json()["id"]

    logs = db.query(AuditLog).all()
    assert len(logs) == 1
    log = logs[0]
    assert log.actor_user_id == 42
    assert log.action == "payout_run"
    assert log.entity_type == "payout"
    assert log.entity_id == payout_id
