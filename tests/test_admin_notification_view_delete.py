import os
import sys
import hashlib
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import User, RoleEnum, Notification, NotificationLog  # noqa: E402
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


def test_view_and_delete_notification():
    db = SessionLocal()
    password_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    u1 = User(
        username="u1",
        email="u1@example.com",
        password_hash=password_hash,
        role=RoleEnum.CUSTOMER,
    )
    u2 = User(
        username="u2",
        email="u2@example.com",
        password_hash=password_hash,
        role=RoleEnum.CUSTOMER,
    )
    db.add_all([u1, u2])
    db.commit()
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)
        resp = client.post(
            "/admin/notifications",
            data={"target": "all", "subject": "Hi", "body": "Test"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

        db = SessionLocal()
        note = db.query(Notification).first()
        assert note.log_id == 1
        db.close()

        resp = client.get("/admin/notifications/1")
        assert resp.status_code == 200
        assert "u1" in resp.text
        assert "u2" in resp.text

        resp = client.post("/admin/notifications/1/delete", follow_redirects=False)
        assert resp.status_code == 303

    db = SessionLocal()
    assert db.query(Notification).count() == 0
    assert db.query(NotificationLog).count() == 0
    db.close()

