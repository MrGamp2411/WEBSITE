import os
import sys
import pathlib
import hashlib
import json
from datetime import datetime

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import Bar, User, UserBarRole, RoleEnum, Order, BarClosing  # noqa: E402
from main import (
    app,
    load_bars_from_db,
    user_carts,
    users,
    users_by_email,
    users_by_username,
    auto_close_bars_once,
)  # noqa: E402


def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    user_carts.clear()
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def test_bar_admin_orders_page_has_history_link():
    setup_db()
    with TestClient(app) as client:
        db = SessionLocal()
        bar = Bar(name="Test Bar", slug="test-bar")
        pwd = hashlib.sha256("pass".encode("utf-8")).hexdigest()
        admin = User(username="a", email="a@example.com", password_hash=pwd, role=RoleEnum.BARADMIN)
        db.add_all([bar, admin])
        db.commit()
        db.add(UserBarRole(user_id=admin.id, bar_id=bar.id, role=RoleEnum.BARADMIN))
        db.commit(); db.refresh(bar); db.close()
        load_bars_from_db()
        client.post('/login', data={'email': 'a@example.com', 'password': 'pass'})
        resp = client.get(f'/dashboard/bar/{bar.id}/orders')
        assert resp.status_code == 200
        assert 'Order History &amp; Revenue' in resp.text
        assert f'href="/dashboard/bar/{bar.id}/orders/history"' in resp.text
        assert 'Close Day' not in resp.text


def test_bar_admin_orders_history_page():
    setup_db()
    with TestClient(app) as client:
        db = SessionLocal()
        bar = Bar(name="Test Bar", slug="test-bar")
        pwd = hashlib.sha256("pass".encode("utf-8")).hexdigest()
        admin = User(username="a", email="a@example.com", password_hash=pwd, role=RoleEnum.BARADMIN)
        db.add_all([bar, admin])
        db.commit()
        db.add(UserBarRole(user_id=admin.id, bar_id=bar.id, role=RoleEnum.BARADMIN))
        db.commit(); db.refresh(bar); db.close()
        load_bars_from_db()
        client.post('/login', data={'email': 'a@example.com', 'password': 'pass'})
        resp = client.get(f'/dashboard/bar/{bar.id}/orders/history')
        assert resp.status_code == 200
        assert 'No order history yet.' in resp.text


def test_auto_close_moves_orders_to_history():
    setup_db()
    with TestClient(app) as client:
        db = SessionLocal()
        hours = {"0": {"open": "10:00", "close": "20:00"}}
        bar = Bar(name="Test Bar", slug="test-bar", opening_hours=json.dumps(hours))
        pwd = hashlib.sha256("pass".encode("utf-8")).hexdigest()
        admin = User(username="a", email="a@example.com", password_hash=pwd, role=RoleEnum.BARADMIN)
        cc = Order(
            bar=bar,
            status="COMPLETED",
            subtotal=6,
            vat_total=0,
            payment_method="credit_card",
        )
        wallet = Order(
            bar=bar,
            status="COMPLETED",
            subtotal=4,
            vat_total=2,
            payment_method="wallet",
        )
        pay_at_bar = Order(
            bar=bar,
            status="COMPLETED",
            subtotal=5,
            vat_total=1,
            payment_method="bar",
        )
        canceled = Order(bar=bar, status="CANCELED", subtotal=5, vat_total=1, payment_method="credit_card")
        db.add_all([bar, admin, cc, wallet, pay_at_bar, canceled])
        db.commit()
        db.add(UserBarRole(user_id=admin.id, bar_id=bar.id, role=RoleEnum.BARADMIN))
        db.commit(); db.refresh(bar); db.close()
        load_bars_from_db()
        # simulate time after closing
        now = datetime(2024, 1, 1, 21, 0, 0)
        with SessionLocal() as db2:
            auto_close_bars_once(db2, now)
            closings = db2.query(BarClosing).filter_by(bar_id=bar.id).all()
            assert len(closings) == 1
            assert float(closings[0].total_revenue) == 18.0
            orders = db2.query(Order).order_by(Order.id).all()
            assert [o.closing_id for o in orders] == [closings[0].id] * 4
            closing_id = closings[0].id
        client.post('/login', data={'email': 'a@example.com', 'password': 'pass'})
        resp = client.get(f'/dashboard/bar/{bar.id}/orders/history')
        assert 'January 2024' in resp.text
        assert 'Total collected' in resp.text and 'CHF 18.00' in resp.text
        assert 'Total earned' in resp.text and 'CHF 17.10' in resp.text
        assert 'Siplygo commission (5%)' in resp.text and 'CHF 0.90' in resp.text
        assert 'Amount to pay to bar' in resp.text and 'CHF 11.10' in resp.text
        resp = client.get(f'/dashboard/bar/{bar.id}/orders/history/2024/1')
        assert 'Total collected' in resp.text and 'CHF 18.00' in resp.text
        assert 'Total earned' in resp.text and 'CHF 17.10' in resp.text
        assert 'Siplygo commission (5%)' in resp.text and 'CHF 0.90' in resp.text
        assert 'Amount to pay to bar' in resp.text and 'CHF 11.10' in resp.text
        resp = client.get(f'/dashboard/bar/{bar.id}/orders/history/{closing_id}')
        assert 'Total collected' in resp.text and 'CHF 18.00' in resp.text
        assert 'Total earned' in resp.text and 'CHF 17.10' in resp.text
        assert 'Siplygo commission (5%)' in resp.text and 'CHF 0.90' in resp.text
        assert 'Amount to pay to bar' in resp.text and 'CHF 11.10' in resp.text
        assert 'Credit Card</span><span class="amount">CHF 6.00' in resp.text
        assert 'Wallet</span><span class="amount">CHF 6.00' in resp.text
        assert 'Bar</span><span class="amount">CHF 6.00' in resp.text
        with SessionLocal() as db_codes:
            codes = [
                (o.public_order_code or f"#{o.id}")
                for o in db_codes.query(Order).order_by(Order.id).limit(3)
            ]
        assert f'Order {codes[0]}' in resp.text
        assert f'Order {codes[1]}' in resp.text
        assert f'Order {codes[2]}' in resp.text
