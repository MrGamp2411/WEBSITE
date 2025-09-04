import os
import pathlib
import sys

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import Bar  # noqa: E402
from main import app, DemoUser, users, users_by_email, users_by_username  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def teardown_module(module):
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def test_admin_bars_delete_form_and_delete():
    db = SessionLocal()
    bar = Bar(name="Test Bar", slug="test-bar")
    db.add(bar)
    db.commit()
    db.refresh(bar)
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
    assert f'id="delete-bar-{bar.id}"' in resp.text
    assert 'id="deleteBlocker"' in resp.text

    resp = client.post(f"/admin/bars/{bar.id}/delete", follow_redirects=False)
    assert resp.status_code == 303
    check_db = SessionLocal()
    assert check_db.get(Bar, bar.id) is None
    check_db.close()
