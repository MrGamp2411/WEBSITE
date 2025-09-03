import os
import sys
import pathlib
import hashlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import Bar, Category, MenuItem, User  # noqa: E402
from main import app, bars  # noqa: E402


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_cart_shows_pause_popup_when_bar_paused():
    reset_db()
    db = SessionLocal()
    bar = Bar(name="Test Bar", slug="test-bar", ordering_paused=False)
    db.add(bar)
    db.commit()
    db.refresh(bar)
    cat = Category(bar_id=bar.id, name="Drinks")
    db.add(cat)
    db.commit()
    db.refresh(cat)
    item = MenuItem(bar_id=bar.id, category_id=cat.id, name="Water", price_chf=5)
    db.add(item)
    pwd = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    user = User(username="u", email="u@example.com", password_hash=pwd)
    db.add(user)
    db.commit()
    db.refresh(item)
    user_email = user.email
    item_id = item.id
    bar_id = bar.id
    db.close()
    with TestClient(app) as client:
        client.post("/login", data={"email": user_email, "password": "pass"})
        client.post(
            f"/bars/{bar_id}/add_to_cart",
            data={"product_id": item_id},
            headers={"accept": "application/json"},
        )
        db2 = SessionLocal()
        bar_obj = db2.get(Bar, bar_id)
        bar_obj.ordering_paused = True
        db2.commit()
        db2.close()
        bars[bar_id].ordering_paused = True
        resp = client.get("/cart")
        assert resp.status_code == 200
        assert "window.orderingPaused = true" in resp.text
