import os
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from decimal import Decimal
from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import (
    Bar as BarModel,
    Category as CategoryModel,
    MenuItem,
    ProductImage,
)  # noqa: E402
from main import app, DemoUser, users, users_by_email, users_by_username, bars  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    bars.clear()


def test_edit_product_shows_uploaded_photo():
    db = SessionLocal()
    bar = BarModel(name="Bar", slug="bar")
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
        description="Nice",
        price_chf=Decimal("5.00"),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    db.add(ProductImage(product_id=item.id, mime="image/jpeg", data=b"img"))
    db.commit()
    bar_id, category_id, item_id = bar.id, category.id, item.id
    db.close()

    admin = DemoUser(
        id=999,
        username="prodadmin",
        password="secret",
        email="prodadmin@example.com",
        role="super_admin",
    )
    users[admin.id] = admin
    users_by_email[admin.email] = admin
    users_by_username[admin.username] = admin

    client = TestClient(app)
    client.post("/login", data={"email": admin.email, "password": admin.password})

    resp = client.get(f"/bar/{bar_id}/categories/{category_id}/products/{item_id}/edit")
    assert resp.status_code == 200
    assert f"/api/products/{item_id}/image" in resp.text

    detail = client.get(f"/bars/{bar_id}")
    assert detail.status_code == 200
    assert f"/api/products/{item_id}/image" in detail.text

    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    bars.clear()
