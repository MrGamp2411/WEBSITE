import os
import sys
import hashlib
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import (
    User,
    RoleEnum,
    Bar,
    Order,
    Category,
    MenuItem,
    OrderItem,
    AuditLog,
)  # noqa: E402
from main import app, refresh_bar_from_db  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _login_super_admin(client: TestClient) -> None:
    resp = client.post(
        "/login",
        data={"email": "admin@example.com", "password": "ChangeMe!123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_view_user_lists_orders():
    db = SessionLocal()
    password_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    user = User(
        username="cust",
        email="cust@example.com",
        password_hash=password_hash,
        role=RoleEnum.CUSTOMER,
    )
    bar = Bar(name="BarX", slug="barx")
    db.add_all([user, bar])
    db.commit()
    refresh_bar_from_db(bar.id, db)
    order = Order(bar_id=bar.id, customer_id=user.id, subtotal=5, vat_total=0)
    db.add(order)
    db.commit()
    order_id = order.id
    code = order.public_order_code or f"#{order_id}"
    user_id = user.id
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)
        resp = client.get(f"/admin/users/view/{user_id}")
        assert resp.status_code == 200
        assert f"/admin/orders/{order_id}" in resp.text
        assert code in resp.text


def test_view_user_lists_login_activity():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    password_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    user = User(
        username="cust",
        email="cust@example.com",
        password_hash=password_hash,
        role=RoleEnum.CUSTOMER,
    )
    db.add(user)
    db.commit()
    log = AuditLog(
        actor_user_id=user.id,
        action="login",
        entity_type="User",
        entity_id=user.id,
        ip="1.2.3.4",
        user_agent="test-agent",
        latitude=12.34,
        longitude=56.78,
    )
    db.add(log)
    db.commit()
    user_id = user.id
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)
        resp = client.get(f"/admin/users/view/{user_id}")
        assert resp.status_code == 200
        assert "1.2.3.4" in resp.text
        assert "test-agent" in resp.text
        assert "12.34" in resp.text
        assert "56.78" in resp.text


def test_order_detail_view():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    password_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    user = User(
        username="cust",
        email="cust@example.com",
        password_hash=password_hash,
        role=RoleEnum.CUSTOMER,
    )
    bar = Bar(name="BarX", slug="barx")
    db.add_all([user, bar])
    db.commit()
    refresh_bar_from_db(bar.id, db)
    cat = Category(bar_id=bar.id, name="Drinks")
    db.add(cat)
    db.commit()
    item = MenuItem(bar_id=bar.id, category_id=cat.id, name="Water", price_chf=5)
    db.add(item)
    db.commit()
    order = Order(bar_id=bar.id, customer_id=user.id, subtotal=5, vat_total=0)
    db.add(order)
    db.commit()
    code = order.public_order_code
    order_item = OrderItem(
        order_id=order.id,
        menu_item_id=item.id,
        qty=1,
        unit_price=5,
        line_total=5,
    )
    db.add(order_item)
    db.commit()
    order_id = order.id
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)
        resp = client.get(f"/admin/orders/{order_id}")
        assert resp.status_code == 200
        expected = f"Order {code}" if code else f"Order #{order_id}"
        assert expected in resp.text
        assert "Water" in resp.text

