import os
import sys
import pathlib
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import Bar as BarModel, Category as CategoryModel, MenuItem  # noqa: E402
from main import (  # noqa: E402
    app,
    DemoUser,
    users,
    users_by_email,
    users_by_username,
    bars,
    LANGUAGES,
)


def reset_state():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    bars.clear()


def seed_product():
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
        name="Spritz",
        description="Classic aperitif",
        price_chf=Decimal("12.00"),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    bar_id, category_id, product_id = bar.id, category.id, item.id
    db.close()
    return bar_id, category_id, product_id


def create_admin():
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
    return admin


def test_edit_product_name_updates_translations():
    reset_state()
    bar_id, category_id, product_id = seed_product()
    admin = create_admin()

    client = TestClient(app, follow_redirects=False)
    client.post("/login", data={"email": admin.email, "password": admin.password})

    payload = {
        f"name_{code}": f"Name {code.upper()}"
        for code in LANGUAGES.keys()
    }
    response = client.post(
        f"/bar/{bar_id}/categories/{category_id}/products/{product_id}/edit/name",
        data=payload,
    )
    assert response.status_code == 303

    db = SessionLocal()
    item = db.get(MenuItem, product_id)
    assert item is not None
    assert set(item.name_translations.keys()) == set(LANGUAGES.keys())
    for code in LANGUAGES.keys():
        expected = payload[f"name_{code}"][:80]
        assert item.name_translations[code] == expected
    assert item.name == payload.get("name_en")
    db.close()


def test_edit_product_description_updates_translations():
    reset_state()
    bar_id, category_id, product_id = seed_product()
    admin = create_admin()

    client = TestClient(app, follow_redirects=False)
    client.post("/login", data={"email": admin.email, "password": admin.password})

    payload = {}
    for code in LANGUAGES.keys():
        text = f"Description {code.upper()}"
        if code == "en":
            text = "X" * 195
        payload[f"description_{code}"] = text
    response = client.post(
        f"/bar/{bar_id}/categories/{category_id}/products/{product_id}/edit/description",
        data=payload,
    )
    assert response.status_code == 303

    db = SessionLocal()
    item = db.get(MenuItem, product_id)
    assert item is not None
    assert set(item.description_translations.keys()) == set(LANGUAGES.keys())
    for code in LANGUAGES.keys():
        expected = payload[f"description_{code}"][:190]
        assert item.description_translations[code] == expected
    assert item.description == payload["description_en"][:190]
    db.close()
