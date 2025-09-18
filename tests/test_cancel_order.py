import os
import sys
import pathlib
import hashlib
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['WALLEE_VERIFY_SIGNATURE'] = 'false'
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import (  # noqa: E402
    Bar,
    Category,
    MenuItem,
    Table,
    User,
    UserBarRole,
    RoleEnum,
    Order,
    Payment,
)
from main import (  # noqa: E402
    app,
    load_bars_from_db,
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


def create_order(client, payment_method):
    db = SessionLocal()
    bar = Bar(name="Test Bar", slug="test-bar")
    db.add(bar); db.commit(); db.refresh(bar)
    cat = Category(bar_id=bar.id, name="Drinks")
    db.add(cat); db.commit(); db.refresh(cat)
    item = MenuItem(bar_id=bar.id, category_id=cat.id, name="Water", price_chf=5)
    db.add(item)
    table = Table(bar_id=bar.id, name="T1")
    db.add(table)
    pwd = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    customer = User(username="u", email="u@example.com", password_hash=pwd, credit=10)
    bartender = User(username="b", email="b@example.com", password_hash=pwd, role=RoleEnum.BARTENDER)
    db.add_all([customer, bartender]); db.commit()
    db.add(UserBarRole(user_id=bartender.id, bar_id=bar.id, role=RoleEnum.BARTENDER))
    db.commit(); db.refresh(item); db.refresh(table)
    ids = {
        'item_id': item.id,
        'bar_id': bar.id,
        'table_id': table.id,
        'customer_email': customer.email,
        'bartender_email': bartender.email,
        'customer_id': customer.id,
        'order_total': 5.2,
    }
    db.close(); load_bars_from_db()

    client.post('/login', data={'email': ids['customer_email'], 'password': 'pass'})
    client.post(f"/bars/{ids['bar_id']}/add_to_cart", data={'product_id': ids['item_id']})
    if payment_method == 'card':
        with patch("app.wallee_client.space_id", 1), patch(
            "app.wallee_client.cfg"
        ) as MockCfg, patch("app.wallee_client.tx_service") as MockTx, patch(
            "app.wallee_client.pp_service"
        ) as MockPage:
            MockCfg.user_id = 1
            MockCfg.api_secret = "secret"
            MockTx.create.return_value = SimpleNamespace(id=123)
            MockPage.payment_page_url.return_value = "https://pay.example/123"
            client.post(
                '/cart/checkout',
                data={'table_id': ids['table_id'], 'payment_method': payment_method},
                follow_redirects=False,
            )
            db = SessionLocal()
            payment = db.query(Payment).first()
            db.close()
            client.post(
                '/webhooks/wallee',
                json={'entityId': int(payment.wallee_tx_id), 'state': 'COMPLETED'},
            )
    else:
        client.post(
            '/cart/checkout',
            data={'table_id': ids['table_id'], 'payment_method': payment_method},
        )
    client.get('/logout')
    db = SessionLocal()
    order = db.query(Order).first()
    db.close()
    ids['order_id'] = order.id
    ids['customer_initial_credit'] = 10
    return ids


def cancel_order(client, ids):
    client.post('/login', data={'email': ids['bartender_email'], 'password': 'pass'})
    resp = client.post(f"/api/orders/{ids['order_id']}/status", json={'status': 'CANCELED'})
    client.get('/logout')
    return resp


def test_cancel_order_refunds_wallet_and_card():
    for method, expected in [('wallet', 10), ('card', 15.2)]:
        setup_db()
        with TestClient(app) as client:
            ids = create_order(client, method)
            resp = cancel_order(client, ids)
            assert resp.status_code == 200
            db = SessionLocal()
            user = db.get(User, ids['customer_id'])
            order = db.get(Order, ids['order_id'])
            db.close()
            assert order.status == 'CANCELED'
            assert order.cancellation_reason == 'bartender'
            assert float(user.credit) == expected
            assert Decimal(order.refund_amount) == Decimal(str(ids['order_total']))
            assert order.cancelled_at is not None
    user_carts.clear()
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def test_cancel_bar_order_no_refund():
    setup_db()
    with TestClient(app) as client:
        ids = create_order(client, 'bar')
        resp = cancel_order(client, ids)
        assert resp.status_code == 200
        db = SessionLocal()
        user = db.get(User, ids['customer_id'])
        order = db.get(Order, ids['order_id'])
        db.close()
        assert order.status == 'CANCELED'
        assert order.cancellation_reason == 'bartender'
        assert float(user.credit) == ids['customer_initial_credit']
        assert Decimal(order.refund_amount) == Decimal('0')
        assert order.cancelled_at is not None
    user_carts.clear()
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def test_cancel_order_updates_user_cache():
    setup_db()
    with TestClient(app) as client:
        ids = create_order(client, 'card')
        cached = users_by_email[ids['customer_email']]
        assert cached.credit == ids['customer_initial_credit']
        resp = cancel_order(client, ids)
        assert resp.status_code == 200
        cached_after = users_by_email[ids['customer_email']]
        assert cached_after.credit == ids['customer_initial_credit'] + ids['order_total']
        db = SessionLocal()
        order = db.get(Order, ids['order_id'])
        db.close()
        assert order.cancellation_reason == 'bartender'
    user_carts.clear()
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def test_cancel_order_reflected_in_html():
    setup_db()
    with TestClient(app) as client:
        ids = create_order(client, 'card')
        cancel_order(client, ids)
        db = SessionLocal()
        order = db.get(Order, ids['order_id'])
        db.close()
        assert order.cancellation_reason == 'bartender'
        client.post('/login', data={'email': ids['customer_email'], 'password': 'pass'})
        wallet = client.get('/wallet')
        assert f"CHF {ids['customer_initial_credit'] + ids['order_total']:.2f}" in wallet.text
        orders_page = client.get('/orders')
        assert f"<dt>Refunded</dt><dd class=\"num nowrap\">CHF {ids['order_total']:.2f}</dd>" in orders_page.text
    user_carts.clear()
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def test_customer_can_cancel_pending_order():
    setup_db()
    with TestClient(app) as client:
        ids = create_order(client, 'card')
        client.post('/login', data={'email': ids['customer_email'], 'password': 'pass'})
        resp = client.post(f"/api/orders/{ids['order_id']}/status", json={'status': 'CANCELED'})
        assert resp.status_code == 200
        db = SessionLocal()
        order = db.get(Order, ids['order_id'])
        user = db.get(User, ids['customer_id'])
        db.close()
        assert order.status == 'CANCELED'
        assert order.cancellation_reason == 'customer'
        assert float(user.credit) == ids['customer_initial_credit'] + ids['order_total']
    user_carts.clear()
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def test_customer_cannot_cancel_after_acceptance():
    setup_db()
    with TestClient(app) as client:
        ids = create_order(client, 'card')
        client.post('/login', data={'email': ids['bartender_email'], 'password': 'pass'})
        client.post(f"/api/orders/{ids['order_id']}/status", json={'status': 'ACCEPTED'})
        client.get('/logout')
        client.post('/login', data={'email': ids['customer_email'], 'password': 'pass'})
        resp = client.post(f"/api/orders/{ids['order_id']}/status", json={'status': 'CANCELED'})
        assert resp.status_code == 403
    user_carts.clear()
    users.clear()
    users_by_email.clear()
    users_by_username.clear()
