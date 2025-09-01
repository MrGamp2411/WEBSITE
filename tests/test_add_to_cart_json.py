import os
import sys
import pathlib
import hashlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import Bar, Category, MenuItem, User  # noqa: E402
from main import app  # noqa: E402


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_add_to_cart_returns_json_count():
    reset_db()
    db = SessionLocal()
    bar = Bar(name="Test Bar", slug="test-bar")
    db.add(bar)
    db.commit()
    db.refresh(bar)
    bar_id = bar.id
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
    item_id = item.id
    user_email = user.email
    db.close()
    with TestClient(app) as client:
        client.post("/login", data={"email": user_email, "password": "pass"})
        resp = client.post(
            f"/bars/{bar_id}/add_to_cart",
            data={"product_id": item_id},
            headers={"accept": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["cart_count"] == 1
