import os
import sys
import pathlib
import hashlib
from decimal import Decimal

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import (  # noqa: E402
    Bar,
    Category,
    MenuItem,
    Order,
    OrderItem,
    Table,
    User,
    UserCart,
)
from main import (  # noqa: E402
    app,
    bars,
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


def seed_order(db):
    bar = Bar(name="Test Bar", slug="test-bar")
    db.add(bar)
    db.commit()
    db.refresh(bar)

    category = Category(bar_id=bar.id, name="Drinks")
    db.add(category)
    db.commit()
    db.refresh(category)

    first_item = MenuItem(
        bar_id=bar.id,
        category_id=category.id,
        name="Water",
        price_chf=5,
    )
    second_item = MenuItem(
        bar_id=bar.id,
        category_id=category.id,
        name="Juice",
        price_chf=6,
    )
    db.add_all([first_item, second_item])

    table = Table(bar_id=bar.id, name="T1")
    db.add(table)

    password_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    user = User(username="u", email="u@example.com", password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(first_item)
    db.refresh(second_item)
    db.refresh(table)
    db.refresh(user)

    order = Order(
        bar_id=bar.id,
        customer_id=user.id,
        table_id=table.id,
        status="COMPLETED",
        subtotal=Decimal("10"),
        vat_total=Decimal("0"),
        payment_method="card",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    order_item = OrderItem(
        order_id=order.id,
        menu_item_id=first_item.id,
        qty=2,
        unit_price=Decimal("5"),
        line_total=Decimal("10"),
    )
    db.add(order_item)
    db.commit()

    return {
        "bar_id": bar.id,
        "order_id": order.id,
        "table_id": table.id,
        "user_id": user.id,
        "user_email": user.email,
        "first_item_id": first_item.id,
        "second_item_id": second_item.id,
    }


def test_reorder_completed_order_populates_cart():
    setup_db()
    with TestClient(app) as client:
        db = SessionLocal()
        ids = seed_order(db)
        db.close()
        load_bars_from_db()

        client.post('/login', data={'email': ids['user_email'], 'password': 'pass'})

        response = client.post(
            f"/orders/{ids['order_id']}/reorder",
            headers={'accept': 'application/json'},
        )
        assert response.status_code == 200
        assert response.json() == {'redirect': '/cart'}

        cart_response = client.get('/cart', headers={'accept': 'application/json'})
        data = cart_response.json()
        assert data['count'] == 2
        assert data['items'][0]['id'] == ids['first_item_id']
        assert data['items'][0]['qty'] == 2

        with SessionLocal() as verify:
            stored = verify.get(UserCart, ids['user_id'])
            assert stored is not None
            assert stored.bar_id == ids['bar_id']
            assert stored.table_id == ids['table_id']


def test_reorder_returns_error_when_item_missing():
    setup_db()
    with TestClient(app) as client:
        db = SessionLocal()
        ids = seed_order(db)
        db.close()
        load_bars_from_db()

        bars[ids['bar_id']].products.pop(ids['first_item_id'], None)

        client.post('/login', data={'email': ids['user_email'], 'password': 'pass'})

        client.post(
            f"/bars/{ids['bar_id']}/add_to_cart",
            data={'product_id': ids['second_item_id']},
        )

        response = client.post(
            f"/orders/{ids['order_id']}/reorder",
            headers={'accept': 'application/json'},
        )
        assert response.status_code == 409
        assert response.json() == {'error': 'items_unavailable'}

        cart_response = client.get('/cart', headers={'accept': 'application/json'})
        data = cart_response.json()
        assert data['count'] == 1
        assert data['items'][0]['id'] == ids['second_item_id']
