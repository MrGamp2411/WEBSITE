import os
from decimal import Decimal
from datetime import datetime, timedelta
import pathlib
import sys

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from database import Base, SessionLocal, engine  # noqa: E402
from models import Bar, Order  # noqa: E402
from payouts import schedule_payout  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_schedule_payout_creates_record():
    db = SessionLocal()
    bar = Bar(name="Test Bar", slug="test-bar")
    db.add(bar)
    db.commit()
    db.refresh(bar)

    now = datetime.utcnow()
    orders = [
        Order(
            bar_id=bar.id,
            subtotal=Decimal("100.00"),
            vat_total=Decimal("7.70"),
            fee_platform_5pct=Decimal("5.00"),
            payout_due_to_bar=Decimal("102.70"),
            status="COMPLETED",
            created_at=now,
        ),
        Order(
            bar_id=bar.id,
            subtotal=Decimal("50.00"),
            vat_total=Decimal("3.85"),
            fee_platform_5pct=Decimal("2.50"),
            payout_due_to_bar=Decimal("51.35"),
            status="COMPLETED",
            created_at=now,
        ),
    ]
    db.add_all(orders)
    db.commit()

    payout = schedule_payout(db, bar.id, now - timedelta(days=1), now + timedelta(days=1))

    assert payout.amount_chf == Decimal("154.05")
    assert payout.status == "scheduled"
    assert payout.bar_id == bar.id
