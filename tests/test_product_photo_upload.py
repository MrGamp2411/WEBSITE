import os
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from decimal import Decimal
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


def test_upload_product_photo_updates_db_and_renders():
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
        description="desc",
        price_chf=Decimal("5.00"),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    bar_id, category_id, item_id = bar.id, category.id, item.id
    db.close()

    admin = DemoUser(
        id=123,
        username="uploader",
        password="secret",
        email="uploader@example.com",
        role="super_admin",
    )
    users[admin.id] = admin
    users_by_email[admin.email] = admin
    users_by_username[admin.username] = admin

    client = TestClient(app)
    client.post("/login", data={"email": admin.email, "password": admin.password})

    file_content = b"img"
    client.post(
        f"/bar/{bar_id}/categories/{category_id}/products/{item_id}/edit",
        data={
            "name": "Beer",
            "price": "5.00",
            "description": "desc",
            "display_order": "0",
        },
        files={"photo": ("beer.jpg", file_content, "image/jpeg")},
    )

    edit = client.get(
        f"/bar/{bar_id}/categories/{category_id}/products/{item_id}/edit"
    )
    assert edit.status_code == 200
    assert "http://testserver/static/uploads/" in edit.text

    detail = client.get(f"/bars/{bar_id}")
    assert detail.status_code == 200
    assert "http://testserver/static/uploads/" in detail.text

    db = SessionLocal()
    db_item = db.get(MenuItem, item_id)
    assert db_item.photo and db_item.photo.startswith("/static/uploads/")
    db.close()

    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    bars.clear()
