import os
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import User, Notification, WelcomeMessage  # noqa: E402
from main import app  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_welcome_notification_sent():
    with TestClient(app) as client:
        resp = client.post(
            "/register",
            data={
                "email": "new@example.com",
                "password": "Password123",
                "confirm_password": "Password123",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/register/details"

        resp = client.post(
            "/register/details",
            data={
                "username": "newuser",
                "phone": "3123456789",
                "prefix": "+39",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"

    db = SessionLocal()
    user = db.query(User).filter_by(email="new@example.com").one()
    note = db.query(Notification).filter_by(user_id=user.id).one()
    assert note.subject == "Welcome"
    assert note.body == "Welcome to SiplyGo!"
    assert note.subject_translations["en"] == "Welcome"
    assert note.body_translations["en"] == "Welcome to SiplyGo!"
    db.close()


def test_welcome_notification_respects_language():
    db = SessionLocal()
    wm = WelcomeMessage(
        id=1,
        subject="Welcome",
        body="Welcome to SiplyGo!",
        subject_translations={"en": "Welcome", "it": "Benvenuto"},
        body_translations={
            "en": "Welcome to SiplyGo!",
            "it": "Benvenuto su SiplyGo!",
        },
    )
    db.merge(wm)
    db.commit()
    db.close()

    with TestClient(app) as client:
        resp = client.post(
            "/register?lang=it",
            data={
                "email": "italian@example.com",
                "password": "Password123",
                "confirm_password": "Password123",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/register/details"

        resp = client.post(
            "/register/details?lang=it",
            data={
                "username": "italianuser",
                "phone": "3123456790",
                "prefix": "+39",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"

    db = SessionLocal()
    user = db.query(User).filter_by(email="italian@example.com").one()
    note = db.query(Notification).filter_by(user_id=user.id).one()
    assert note.subject == "Benvenuto"
    assert note.body == "Benvenuto su SiplyGo!"
    assert note.subject_translations["it"] == "Benvenuto"
    assert note.body_translations["it"] == "Benvenuto su SiplyGo!"
    db.close()


def test_notification_updates_when_switching_language():
    db = SessionLocal()
    wm = WelcomeMessage(
        id=1,
        subject="Welcome",
        body="Welcome to SiplyGo!",
        subject_translations={"en": "Welcome", "it": "Benvenuto"},
        body_translations={
            "en": "Welcome to SiplyGo!",
            "it": "Benvenuto su SiplyGo!",
        },
    )
    db.merge(wm)
    db.commit()
    db.close()

    with TestClient(app) as client:
        resp = client.post(
            "/register",
            data={
                "email": "switch@example.com",
                "password": "Password123",
                "confirm_password": "Password123",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/register/details"

        resp = client.post(
            "/register/details",
            data={
                "username": "switchuser",
                "phone": "3123456791",
                "prefix": "+39",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"

        resp = client.post(
            "/login",
            data={
                "email": "switch@example.com",
                "password": "Password123",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/dashboard"

        resp = client.get("/notifications")
        assert "Welcome to SiplyGo!" in resp.text

        resp = client.get("/notifications?lang=it")
        assert "Benvenuto su SiplyGo!" in resp.text
