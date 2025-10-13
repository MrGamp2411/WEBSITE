import hashlib
import os
import pathlib
import sys

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['WALLEE_VERIFY_SIGNATURE'] = 'false'
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import (  # noqa: E402
    Bar,
    Category,
    MenuItem,
    Order,
    RoleEnum,
    User,
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


def seed_menu():
    db = SessionLocal()
    bar = Bar(name="Test Bar", slug="test-bar")
    db.add(bar)
    db.commit()
    db.refresh(bar)

    category = Category(bar_id=bar.id, name="Drinks")
    db.add(category)
    db.commit()
    db.refresh(category)

    item = MenuItem(
        bar_id=bar.id,
        category_id=category.id,
        name="Water",
        price_chf=5,
        vat_rate=0,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    bar_id = bar.id
    item_id = item.id
    db.close()
    load_bars_from_db()
    return bar_id, item_id


def create_user(email: str, role: RoleEnum = RoleEnum.CUSTOMER) -> User:
    db = SessionLocal()
    password_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    user = User(
        username=email.split("@")[0],
        email=email,
        password_hash=password_hash,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def test_create_order_requires_authentication():
    setup_db()
    bar_id, item_id = seed_menu()

    with TestClient(app) as client:
        payload = {
            'bar_id': bar_id,
            'items': [{'menu_item_id': item_id, 'qty': 1}],
        }
        resp = client.post('/api/orders', json=payload)
        assert resp.status_code == 401


def test_create_order_binds_to_customer():
    setup_db()
    bar_id, item_id = seed_menu()
    customer = create_user('customer@example.com')

    with TestClient(app) as client:
        client.post('/login', data={'email': customer.email, 'password': 'pass'})
        payload = {
            'bar_id': bar_id,
            'items': [{'menu_item_id': item_id, 'qty': 2}],
        }
        resp = client.post('/api/orders', json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body['status'] == 'PLACED'
        db = SessionLocal()
        order = db.query(Order).first()
        db.close()
        assert order.customer_id == customer.id
        assert order.source_channel == 'api'


def test_non_customer_cannot_create_order():
    setup_db()
    bar_id, item_id = seed_menu()
    bartender = create_user('bartender@example.com', RoleEnum.BARTENDER)

    with TestClient(app) as client:
        client.post('/login', data={'email': bartender.email, 'password': 'pass'})
        payload = {
            'bar_id': bar_id,
            'items': [{'menu_item_id': item_id, 'qty': 1}],
        }
        resp = client.post('/api/orders', json=payload)
        assert resp.status_code == 403
