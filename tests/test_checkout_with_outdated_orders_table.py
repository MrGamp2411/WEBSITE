import os
import sys
import pathlib
import hashlib
from sqlalchemy import text, inspect

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import Bar, Category, MenuItem, Table, User, Order  # noqa: E402
from main import app, load_bars_from_db  # noqa: E402


def reset_db_with_legacy_orders():
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY,
                    bar_id INTEGER NOT NULL,
                    customer_id INTEGER,
                    subtotal NUMERIC(10,2) DEFAULT 0
                )
                """
            )
        )


def test_checkout_succeeds_when_order_columns_missing():
    reset_db_with_legacy_orders()
    with TestClient(app) as client:
        # Ensure startup hook added new columns
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("orders")}
        assert "status" in cols  # added by ensure_order_columns()
        assert "table_id" in cols  # added by ensure_order_columns()

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
        item_id = item.id
        bar_id = bar.id
        table_id = table.id
        user_email = user.email
        db.close()
        load_bars_from_db()

        client.post("/login", data={"email": user_email, "password": "pass"})
        client.post(f"/bars/{bar_id}/add_to_cart", data={"product_id": item_id})
        resp = client.post(
            "/cart/checkout",
            data={"table_id": table_id, "payment_method": "card"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        db = SessionLocal()
        assert db.query(Order).count() == 1
        db.close()
