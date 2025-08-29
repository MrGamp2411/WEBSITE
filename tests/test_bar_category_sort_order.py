import os
import sys
import pathlib
from decimal import Decimal

# Use shared in-memory SQLite database
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import Bar as BarModel, Category as CategoryModel, MenuItem  # noqa: E402
from main import (
    app,
    bars,
    load_bars_from_db,
    users,
    users_by_email,
    users_by_username,
)  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    bars.clear()
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def _login(client: TestClient) -> None:
    resp = client.post(
        "/login",
        data={"email": "admin@example.com", "password": "ChangeMe!123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_menu_handles_missing_category_sort_order():
    db = SessionLocal()
    bar = BarModel(name="Bar", slug="bar")
    db.add(bar)
    db.commit()
    db.refresh(bar)
    bar_id = bar.id

    c1 = CategoryModel(bar_id=bar_id, name="NoOrder", sort_order=None)
    c2 = CategoryModel(bar_id=bar_id, name="WithOrder", sort_order=1)
    db.add_all([c1, c2])
    db.commit()
    db.refresh(c1)
    db.refresh(c2)
    c1_id, c2_id = c1.id, c2.id

    item1 = MenuItem(
        bar_id=bar_id,
        category_id=c1_id,
        name="Item1",
        description="d",
        price_chf=Decimal("3.00"),
    )
    item2 = MenuItem(
        bar_id=bar_id,
        category_id=c2_id,
        name="Item2",
        description="d",
        price_chf=Decimal("4.00"),
    )
    db.add_all([item1, item2])
    db.commit()
    db.close()

    load_bars_from_db()

    with TestClient(app) as client:
        _login(client)
        resp = client.get(f"/bars/{bar_id}")
        assert resp.status_code == 200
        assert "Item1" in resp.text
        assert "Item2" in resp.text

        resp = client.get(f"/bar/{bar_id}/categories")
        assert resp.status_code == 200
        assert "NoOrder" in resp.text
        assert "WithOrder" in resp.text

