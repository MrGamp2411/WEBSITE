import sys
import pathlib
import hashlib
import os

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import (  # noqa: E402
    Bar,
    Category,
    MenuItem,
    Table,
    User,
    RoleEnum,
    Order,
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


def test_super_admin_can_view_and_update_orders():
    setup_db()
    with TestClient(app) as client:
        db = SessionLocal()
        bar = Bar(name="Test Bar", slug="test-bar")
        db.add(bar)
        db.commit()
        db.refresh(bar)
        cat = Category(bar_id=bar.id, name="Drinks")
        db.add(cat)
        db.commit()
        db.refresh(cat)
        item = MenuItem(bar_id=bar.id, category_id=cat.id, name="Water", price_chf=5)
        table = Table(bar_id=bar.id, name="T1")
        pwd = hashlib.sha256("pass".encode("utf-8")).hexdigest()
        customer = User(username="u", email="u@example.com", password_hash=pwd)
        super_admin = User(
            username="s",
            email="s@example.com",
            password_hash=pwd,
            role=RoleEnum.SUPERADMIN,
        )
        db.add_all([item, table, customer, super_admin])
        db.commit()
        db.refresh(item)
        db.refresh(table)
        db.refresh(bar)
        bar_id, item_id, table_id = bar.id, item.id, table.id
        db.close()
        load_bars_from_db()

        client.post('/login', data={'email': 'u@example.com', 'password': 'pass'})
        client.post(f'/bars/{bar_id}/add_to_cart', data={'product_id': item_id})
        client.post('/cart/checkout', data={'table_id': table_id, 'payment_method': 'card'})
        client.get('/logout')

        db = SessionLocal()
        order_id = db.query(Order).first().id
        db.close()

        client.post('/login', data={'email': 's@example.com', 'password': 'pass'})

        resp = client.get(f'/api/bars/{bar_id}/orders')
        assert resp.status_code == 200
        data = resp.json()
        assert any(o['id'] == order_id for o in data)

        resp = client.post(
            f'/api/orders/{order_id}/status', json={'status': 'ACCEPTED'}
        )
        assert resp.status_code == 200

        resp = client.get(f'/api/bars/{bar_id}/orders')
        statuses = {o['id']: o['status'] for o in resp.json()}
        assert statuses[order_id] == 'ACCEPTED'

    setup_db()

