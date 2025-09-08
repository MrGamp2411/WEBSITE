import os
import sys
import pathlib
import hashlib
from types import SimpleNamespace
from urllib.parse import urlparse, parse_qs
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["WALLEE_VERIFY_SIGNATURE"] = "false"

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import Bar, Category, MenuItem, Table, User, Order, Payment  # noqa: E402
from main import app, load_bars_from_db  # noqa: E402


def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_failed_card_payment_cancels_order():
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
        db.add(item)
        table = Table(bar_id=bar.id, name="T1")
        db.add(table)
        pwd = hashlib.sha256("pass".encode("utf-8")).hexdigest()
        user = User(username="u", email="u@example.com", password_hash=pwd)
        db.add(user)
        db.commit()
        db.refresh(item)
        db.refresh(table)
        item_id, bar_id, table_id, user_email = item.id, bar.id, table.id, user.email
        db.close()
        load_bars_from_db()

        client.post("/login", data={"email": user_email, "password": "pass"})
        client.post(f"/bars/{bar_id}/add_to_cart", data={"product_id": item_id})

        with patch("app.wallee_client.space_id", 1), patch(
            "app.wallee_client.cfg"
        ) as MockCfg, patch("app.wallee_client.tx_service") as MockTx, patch(
            "app.wallee_client.pp_service"
        ) as MockPage:
            MockCfg.user_id = 1
            MockCfg.api_secret = "secret"
            MockTx.create.return_value = SimpleNamespace(id=123)
            MockPage.payment_page_url.return_value = "https://pay.example/123"
            resp = client.post(
                "/cart/checkout",
                data={"table_id": table_id, "payment_method": "card"},
                follow_redirects=False,
            )
            assert resp.status_code == 303

        db = SessionLocal()
        payment = db.query(Payment).first()
        db.close()

        payload = {"entityId": int(payment.wallee_tx_id), "state": "FAILED"}
        resp2 = client.post("/webhooks/wallee", json=payload)
        assert resp2.status_code == 200

        db = SessionLocal()
        order_count = db.query(Order).count()
        payment = db.get(Payment, payment.id)
        db.close()
        assert order_count == 0
        assert payment.state == "FAILED"
        cart_state = client.get("/cart", headers={"accept": "application/json"})
        assert cart_state.json()["count"] == 1


def test_card_checkout_without_wallee_cancels_order():
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
        db.add(item)
        table = Table(bar_id=bar.id, name="T1")
        db.add(table)
        pwd = hashlib.sha256("pass".encode("utf-8")).hexdigest()
        user = User(username="u", email="u@example.com", password_hash=pwd)
        db.add(user)
        db.commit()
        db.refresh(item)
        db.refresh(table)
        item_id, bar_id, table_id, user_email = item.id, bar.id, table.id, user.email
        db.close()
        load_bars_from_db()

        client.post("/login", data={"email": user_email, "password": "pass"})
        client.post(f"/bars/{bar_id}/add_to_cart", data={"product_id": item_id})

        with patch("app.wallee_client.space_id", None), patch(
            "app.wallee_client.cfg"
        ) as MockCfg, patch("app.wallee_client.tx_service") as MockTx:
            MockCfg.user_id = None
            MockCfg.api_secret = None
            MockTx.create.side_effect = Exception("unavailable")
            resp = client.post(
                "/cart/checkout",
                data={"table_id": table_id, "payment_method": "card"},
                follow_redirects=False,
            )
            assert resp.status_code == 303
            parsed = urlparse(resp.headers["location"])
            assert parsed.path == "/cart"
            qs = parse_qs(parsed.query)
            assert qs.get("notice") == ["payment_failed"]

        db = SessionLocal()
        order_count = db.query(Order).count()
        db.close()
        assert order_count == 0

        cart_state = client.get("/cart", headers={"accept": "application/json"})
        assert cart_state.json()["count"] == 1

