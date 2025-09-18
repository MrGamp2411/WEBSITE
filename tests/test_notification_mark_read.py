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


def test_notification_marked_read_after_view():
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
                "body_en": "Test body",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

        db = SessionLocal()
        note = db.query(Notification).filter(Notification.user_id == user_id).first()
        note_id = note.id
        log_id = note.log_id
        db.close()

        _login(client, "u1@example.com", "pass")
        resp = client.get("/notifications")
        assert resp.status_code == 200
        assert "card--unread" in resp.text

        resp = client.get(f"/notifications/{note_id}")
        assert resp.status_code == 200

        resp = client.get("/notifications")
        assert "card--unread" not in resp.text

        db = SessionLocal()
        note = db.query(Notification).filter(Notification.id == note_id).first()
        assert note.read is True
        db.close()

        _login(client, "admin@example.com", "ChangeMe!123")
        resp = client.get(f"/admin/notifications/{log_id}")
        assert ">Yes<" in resp.text


def test_notification_translations_render_for_user():
    db = SessionLocal()
    password_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    user = User(
        username="languser",
        email="lang@example.com",
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
                "subject_en": "Hello",
                "body_en": "English body",
                "subject_it": "Ciao",
                "body_it": "Messaggio italiano",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

        db = SessionLocal()
        note = (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .first()
        )
        assert note is not None
        assert note.subject_translations["en"] == "Hello"
        assert note.subject_translations["it"] == "Ciao"
        assert note.body_translations["en"] == "English body"
        assert note.body_translations["it"] == "Messaggio italiano"
        note_id = note.id
        db.close()

        _login(client, "lang@example.com", "pass")
        resp = client.get("/notifications")
        assert resp.status_code == 200
        assert "English body" in resp.text
        resp = client.get(f"/notifications/{note_id}")
        assert resp.status_code == 200
        assert "Hello" in resp.text

        resp = client.get("/notifications?lang=it")
        assert resp.status_code == 200
        assert "Messaggio italiano" in resp.text
        resp = client.get(f"/notifications/{note_id}?lang=it")
        assert resp.status_code == 200
        assert "Ciao" in resp.text
