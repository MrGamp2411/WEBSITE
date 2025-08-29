import os
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import Bar as BarModel, Category as CategoryModel, MenuItem  # noqa: E402
from main import app, DemoUser, users, users_by_email, users_by_username, bars  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    bars.clear()


def test_product_description_trimmed_to_190_chars():
    db = SessionLocal()
    bar = BarModel(name="Bar", slug="bar")
    db.add(bar)
    db.commit()
    db.refresh(bar)
    category = CategoryModel(bar_id=bar.id, name="Drinks")
    db.add(category)
    db.commit()
    db.refresh(category)
    bar_id, category_id = bar.id, category.id
    db.close()

    admin = DemoUser(
        id=1,
        username="admin",
        password="secret",
        email="admin@example.com",
        role="super_admin",
    )
    users[admin.id] = admin
    users_by_email[admin.email] = admin
    users_by_username[admin.username] = admin

    client = TestClient(app)
    client.post("/login", data={"email": admin.email, "password": admin.password})

    long_desc = "x" * 195
    client.post(
        f"/bar/{bar_id}/categories/{category_id}/products/new",
        data={"name": "Beer", "price": "5.00", "description": long_desc, "display_order": "0"},
    )

    db = SessionLocal()
    item = db.query(MenuItem).filter_by(bar_id=bar_id, category_id=category_id).first()
    assert item is not None
    assert len(item.description) == 190
    assert item.description == long_desc[:190]
    db.close()

    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    bars.clear()
