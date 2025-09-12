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


def test_subject_too_long_is_rejected():
    db = SessionLocal()
    password_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    user = User(
        username="u1",
        email="u1@example.com",
        password_hash=password_hash,
        role=RoleEnum.CUSTOMER,
    )
    db.add(user)
    db.commit()
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)
        resp = client.post(
            "/admin/notifications",
            data={"target": "all", "subject": "x" * 31, "body": "Test"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "Subject+too+long" in resp.headers["location"]

    db = SessionLocal()
    assert db.query(Notification).count() == 0
    assert db.query(NotificationLog).count() == 0
    db.close()
