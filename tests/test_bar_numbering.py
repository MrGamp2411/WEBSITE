import os
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import Bar  # noqa: E402
from main import app, DemoUser, users, users_by_email, users_by_username  # noqa: E402


def reset_env():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def test_bar_listing_numbers():
    reset_env()
    db = SessionLocal()
    bars = [Bar(name=f"Bar {i}", slug=f"bar-{i}") for i in range(1, 4)]
    db.add_all(bars)
    db.commit()
    db.close()

    client = TestClient(app)
    resp = client.get("/bars")
    assert resp.status_code == 200
    idx1 = resp.text.index("001")
    idx2 = resp.text.index("002")
    idx3 = resp.text.index("003")
    assert idx1 < idx2 < idx3


def test_admin_bars_numbers():
    reset_env()
    db = SessionLocal()
    bars = [Bar(name=f"Admin Bar {i}", slug=f"admin-bar-{i}") for i in range(1, 4)]
    db.add_all(bars)
    db.commit()
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

    resp = client.get("/admin/bars")
    assert resp.status_code == 200
    idx1 = resp.text.index("001")
    idx2 = resp.text.index("002")
    idx3 = resp.text.index("003")
    assert idx1 < idx2 < idx3
