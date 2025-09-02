import os
import sys
import pathlib
import hashlib

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import Bar, Category, MenuItem, Table, User, RoleEnum, UserBarRole  # noqa: E402
from main import (
    app,
    load_bars_from_db,
    user_carts,
    users,
    users_by_email,
    users_by_username,
)  # noqa: E402


def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    user_carts.clear()
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def test_rejected_order_moves_to_completed_history():
    setup_db()
    with TestClient(app) as client:
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
        user = User(username="u", email="u@example.com", password_hash=pwd)
        bartender = User(username="b", email="b@example.com", password_hash=pwd, role=RoleEnum.BARTENDER)
        db.add_all([user, bartender]); db.commit(); db.refresh(item); db.refresh(table); db.refresh(bartender)
        db.add(UserBarRole(user_id=bartender.id, bar_id=bar.id, role=RoleEnum.BARTENDER))
        db.commit()
        item_id, bar_id, table_id, user_email, bartender_email = (
            item.id,
            bar.id,
            table.id,
            user.email,
            bartender.email,
        )
        db.close(); load_bars_from_db()

        client.post('/login', data={'email': user_email, 'password': 'pass'})
        client.post(f'/bars/{bar_id}/add_to_cart', data={'product_id': item_id})
        client.post('/cart/checkout', data={'table_id': table_id, 'payment_method': 'card'})
        client.post('/login', data={'email': bartender_email, 'password': 'pass'})
        client.post('/api/orders/1/status', json={'status': 'REJECTED'})
        client.post('/login', data={'email': user_email, 'password': 'pass'})
        resp = client.get('/orders')
        pending = resp.text.split('<h2>Pending Orders</h2>')[1].split('<h2>Completed Orders</h2>')[0]
        completed = resp.text.split('<h2>Completed Orders</h2>')[1]
        assert 'Order #1' not in pending
        assert 'Order #1' in completed
        assert 'Rejected' in completed
    user_carts.clear()
    users.clear()
    users_by_email.clear()
    users_by_username.clear()

