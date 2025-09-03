import os
import sys
import pathlib
import hashlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import Bar, Category, MenuItem, Table, User  # noqa: E402
from main import app, load_bars_from_db  # noqa: E402


def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_checkout_saves_notes():
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
        db.add(user); db.commit(); db.refresh(item); db.refresh(table)
        item_id, bar_id, table_id, user_email = item.id, bar.id, table.id, user.email
        db.close(); load_bars_from_db()

        client.post("/login", data={"email": user_email, "password": "pass"})
        client.post(f"/bars/{bar_id}/add_to_cart", data={"product_id": item_id})
        resp = client.post(
            "/cart/checkout",
            data={"table_id": table_id, "payment_method": "card", "notes": "No sugar"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "<dt>Notes</dt><dd>No sugar</dd>" in resp.text

