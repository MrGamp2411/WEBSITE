import os
import sys
import pathlib
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import Bar as BarModel, Category as CategoryModel, MenuItem  # noqa: E402
from main import app, bars, load_bars_from_db  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    bars.clear()


def test_bar_detail_handles_invalid_opening_hours():
    db = SessionLocal()
    bar = BarModel(name="Bar", slug="bar", opening_hours="[]")
    db.add(bar)
    db.commit()
    db.refresh(bar)
    category = CategoryModel(bar_id=bar.id, name="Drinks")
    db.add(category)
    db.commit()
    db.refresh(category)
    item = MenuItem(
        bar_id=bar.id,
        category_id=category.id,
        name="Beer",
        description="desc",
        price_chf=Decimal("5.00"),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    bar_id = bar.id
    db.close()

    load_bars_from_db()

    client = TestClient(app)
    resp = client.get(f"/bars/{bar_id}")
    assert resp.status_code == 200
    assert "Beer" in resp.text
