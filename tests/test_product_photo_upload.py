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
from main import (
    app,
    DemoUser,
    users,
    users_by_email,
    users_by_username,
    bars,
    load_bars_from_db,
)  # noqa: E402


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
    resp = client.post(
        f"/api/products/{item_id}/image",
        files={"image": ("beer.jpg", file_content, "image/jpeg")},
    )
    assert resp.status_code == 204

    edit = client.get(
        f"/bar/{bar_id}/categories/{category_id}/products/{item_id}/edit"
    )
    assert edit.status_code == 200
    assert f"/api/products/{item_id}/image" in edit.text

    detail = client.get(f"/bars/{bar_id}")
    assert detail.status_code == 200

    db = SessionLocal()
    db_img = db.query(ProductImage).filter_by(product_id=item_id).first()
    assert db_img and db_img.mime == "image/jpeg" and db_img.data == file_content
    assert f"/api/products/{item_id}/image" in detail.text
    db.close()

    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    bars.clear()


def test_product_photo_persists_after_restart():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
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
        id=456,
        username="restarter",
        password="secret",
        email="restart@example.com",
        role="super_admin",
    )
    users[admin.id] = admin
    users_by_email[admin.email] = admin
    users_by_username[admin.username] = admin

    client = TestClient(app)
    client.post("/login", data={"email": admin.email, "password": admin.password})

    file_content = b"img"
    resp = client.post(
        f"/api/products/{item_id}/image",
        files={"image": ("beer.jpg", file_content, "image/jpeg")},
    )
    assert resp.status_code == 204

    load_bars_from_db()
    photo_path = bars[bar_id].products[item_id].photo_url
    assert photo_path == f"/api/products/{item_id}/image"
    detail = client.get(f"/bars/{bar_id}")
    assert f"/api/products/{item_id}/image" in detail.text

    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    bars.clear()


def test_upload_product_photo_requires_staff_access():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

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
    item_id = item.id
    db.close()

    customer = DemoUser(
        id=9999,
        username="customer",
        password="secret",
        email="customer@example.com",
    )
    users[customer.id] = customer
    users_by_email[customer.email] = customer
    users_by_username[customer.username] = customer

    client = TestClient(app)
    client.post(
        "/login", data={"email": customer.email, "password": customer.password}
    )

    resp = client.post(
        f"/api/products/{item_id}/image",
        files={"image": ("beer.jpg", b"img", "image/jpeg")},
    )
    assert resp.status_code == 403

    db = SessionLocal()
    assert db.query(ProductImage).filter_by(product_id=item_id).first() is None
    db.close()

    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    bars.clear()
