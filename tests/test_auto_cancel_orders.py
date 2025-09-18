import os
import sys
import pathlib
from datetime import datetime, timedelta
from decimal import Decimal

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from database import Base, engine, SessionLocal  # noqa: E402
from models import Bar, Order, User, WalletTransaction  # noqa: E402
from main import (  # noqa: E402
    auto_cancel_unprepared_orders_once,
    user_carts,
    users,
    users_by_email,
    users_by_username,
)


def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    user_carts.clear()
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def test_auto_cancel_unprepared_orders_once():
    setup_db()
    db = SessionLocal()
    now = datetime.utcnow()

    bar = Bar(name="Test Bar", slug="test-bar")
    customer = User(
        username="alice",
        email="alice@example.com",
        password_hash="hash",
        credit=Decimal('0'),
    )
    db.add_all([bar, customer])
    db.commit()
    db.refresh(bar)
    db.refresh(customer)

    stale_order = Order(
        bar_id=bar.id,
        customer_id=customer.id,
        status="ACCEPTED",
        subtotal=Decimal('8.00'),
        vat_total=Decimal('2.00'),
        payment_method="wallet",
        accepted_at=now - timedelta(minutes=61),
    )
    fresh_order = Order(
        bar_id=bar.id,
        customer_id=customer.id,
        status="ACCEPTED",
        subtotal=Decimal('5.00'),
        vat_total=Decimal('1.00'),
        payment_method="wallet",
        accepted_at=now - timedelta(minutes=30),
    )
    db.add_all([stale_order, fresh_order])
    db.commit()
    db.refresh(stale_order)
    db.refresh(fresh_order)

    tx = WalletTransaction(
        user_id=customer.id,
        order_id=stale_order.id,
        total=Decimal('10.00'),
        payment_method="wallet",
        status="PROCESSING",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    canceled = auto_cancel_unprepared_orders_once(db, now)
    assert len(canceled) == 1
    assert canceled[0].id == stale_order.id

    db.refresh(stale_order)
    db.refresh(fresh_order)
    db.refresh(customer)
    db.refresh(tx)

    assert stale_order.status == "CANCELED"
    assert stale_order.cancelled_at is not None
    assert Decimal(stale_order.refund_amount) == Decimal('10.00')
    assert float(customer.credit) == 10.0
    assert tx.status == "CANCELED"
    assert float(tx.total) == 0.0
    assert fresh_order.status == "ACCEPTED"

    db.close()
