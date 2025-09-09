import os
import sys
import pathlib
import hashlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import Bar, Category, MenuItem, Table, User  # noqa: E402
from main import app, user_carts, users, get_cart_for_user, save_cart_for_user  # noqa: E402


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_cart_table_defaults_to_placeholder():
    reset_db()
    db = SessionLocal()
    bar = Bar(name="Test Bar", slug="test-bar")
    db.add(bar)
    db.commit()
    db.refresh(bar)
    bar_id = bar.id
    table = Table(bar_id=bar_id, name="T1")
    db.add(table)
    db.commit()
    db.refresh(table)
    cat = Category(bar_id=bar_id, name="Drinks")
    db.add(cat)
    db.commit()
    db.refresh(cat)
    item = MenuItem(bar_id=bar_id, category_id=cat.id, name="Water", price_chf=5)
    db.add(item)
    pwd = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    user = User(username="u", email="u@example.com", password_hash=pwd)
    db.add(user)
    db.commit()
    db.refresh(item)
    db.refresh(user)
    item_id = item.id
    user_email = user.email
    user_id = user.id
    # bar_id already captured
    db.close()

    with TestClient(app) as client:
        client.post("/login", data={"email": user_email, "password": "pass"})
        client.post(
            f"/bars/{bar_id}/add_to_cart",
            data={"product_id": item_id},
            headers={"accept": "application/json"},
        )
        demo_user = users[user_id]
        cart = get_cart_for_user(demo_user)
        cart.table_id = 999
        save_cart_for_user(user_id, cart)
        resp = client.get("/cart")
        assert '<option value="" disabled selected>Select table</option>' in resp.text
        assert get_cart_for_user(demo_user).table_id is None
