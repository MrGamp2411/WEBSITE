import os
import sys
import pathlib
import hashlib

# Use shared in-memory SQLite database
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import Bar, User, RoleEnum, UserBarRole  # noqa: E402
from main import app  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _login_super_admin(client: TestClient) -> None:
    resp = client.post(
        "/login",
        data={"email": "admin@example.com", "password": "ChangeMe!123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_add_existing_user_to_bar():
    db = SessionLocal()
    bar = Bar(name="My Bar", slug="my-bar")
    db.add(bar)
    existing = User(
        username="existing",
        email="existing@example.com",
        password_hash=hashlib.sha256("pass".encode("utf-8")).hexdigest(),
        role=RoleEnum.CUSTOMER,
    )
    db.add(existing)
    db.commit()
    db.refresh(bar)
    db.refresh(existing)
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)
        form = {
            "action": "existing",
            "email": "existing@example.com",
            "role": "bar_admin",
        }
        resp = client.post(f"/admin/bars/{bar.id}/users", data=form)
        assert resp.status_code == 200
        assert "existing" in resp.text

        form = {
            "action": "new",
            "username": "brandnew",
            "email": "fresh@example.com",
            "password": "secret",
            "prefix": "+41",
            "phone": "763661800",
            "role": "bartender",
        }
        resp = client.post(f"/admin/bars/{bar.id}/users", data=form)
        assert resp.status_code == 200
        assert "Invalid action" in resp.text

    db = SessionLocal()
    rel_existing = (
        db.query(UserBarRole)
        .filter_by(user_id=existing.id, bar_id=bar.id)
        .first()
    )
    assert rel_existing is not None and rel_existing.role == RoleEnum.BARADMIN
    new_db_user = db.query(User).filter(User.email == "fresh@example.com").first()
    assert new_db_user is None
    db.close()
