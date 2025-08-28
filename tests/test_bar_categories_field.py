import os
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import Bar as BarModel  # noqa: E402
from main import app, DemoUser, users, users_by_email, users_by_username, BAR_CATEGORIES  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def test_bar_categories_persist():
    db = SessionLocal()
    bar = BarModel(
        name="Test",
        slug="test",
        address="a",
        city="c",
        state="s",
        latitude=0,
        longitude=0,
        description="d",
        bar_categories="Gin bar,Pub/Irish pub",
    )
    db.add(bar)
    db.commit()
    fetched = db.query(BarModel).filter_by(slug="test").first()
    assert fetched.bar_categories == "Gin bar,Pub/Irish pub"


def test_admin_bar_categories_limit():
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

    data = {
        "name": "Bar1",
        "address": "a",
        "city": "c",
        "state": "s",
        "latitude": "0",
        "longitude": "0",
        "description": "d",
        "categories": BAR_CATEGORIES[:6],
    }

    resp = client.post("/admin/bars/new", data=data)
    assert resp.status_code == 200
    assert "Select up to 5 categories" in resp.text
    db = SessionLocal()
    assert db.query(BarModel).filter_by(slug="bar1").first() is None
    db.close()


def test_admin_bar_categories_max_five_allowed():
    admin = DemoUser(
        id=2,
        username="admin2",
        password="secret",
        email="admin2@example.com",
        role="super_admin",
    )
    users[admin.id] = admin
    users_by_email[admin.email] = admin
    users_by_username[admin.username] = admin

    client = TestClient(app)
    client.post("/login", data={"email": admin.email, "password": admin.password})

    data = {
        "name": "Bar2",
        "address": "a",
        "city": "c",
        "state": "s",
        "latitude": "0",
        "longitude": "0",
        "description": "d",
        "categories": BAR_CATEGORIES[:5],
    }

    resp = client.post("/admin/bars/new", data=data, follow_redirects=False)
    assert resp.status_code == 303
    db = SessionLocal()
    bar = db.query(BarModel).filter_by(slug="bar2").first()
    assert bar is not None
    assert bar.bar_categories == ",".join(BAR_CATEGORIES[:5])
    db.close()
