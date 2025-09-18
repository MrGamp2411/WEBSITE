import hashlib
import os
import pathlib
import sys

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import User, RoleEnum, Notification  # noqa: E402
from main import app  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _login(client: TestClient, email: str, password: str) -> None:
    resp = client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_notification_badge():
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
    user_id = user.id
    db.close()

    with TestClient(app) as client:
        _login(client, "admin@example.com", "ChangeMe!123")
        resp = client.post(
            "/admin/notifications",
            data={
                "target": "user",
                "user_id": user_id,
                "subject_en": "Hi",
                "body_en": "Test",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

        db = SessionLocal()
        note = db.query(Notification).filter(Notification.user_id == user_id).first()
        note_id = note.id
        db.close()

        _login(client, "u1@example.com", "pass")
        resp = client.get("/notifications")
        assert resp.status_code == 200
        assert "notif-badge" in resp.text

        resp = client.get(f"/notifications/{note_id}")
        assert resp.status_code == 200

        resp = client.get("/notifications")
        assert "notif-badge" not in resp.text
