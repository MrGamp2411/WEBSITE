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


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_topup_hides_cart_popup_when_cart_exists():
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
    db.add(item)
    password_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    user = User(username="u", email="u@example.com", password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(item)
    db.refresh(user)
    item_id = item.id
    bar_id = bar.id
    user_email = user.email
    db.close()

    with TestClient(app) as client:
        client.post("/login", data={"email": user_email, "password": "pass"})
        client.post(
            f"/bars/{bar_id}/add_to_cart",
            data={"product_id": item_id},
            headers={"accept": "application/json"},
        )
        resp = client.get("/topup")
        assert resp.status_code == 200
        assert '<div id="cartBlocker" class="cart-blocker" hidden>' in resp.text
