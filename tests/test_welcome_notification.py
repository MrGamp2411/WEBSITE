import os
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import User, Notification  # noqa: E402
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
        assert resp.headers["location"] == "/login"

    db = SessionLocal()
    user = db.query(User).filter_by(email="new@example.com").one()
    note = db.query(Notification).filter_by(user_id=user.id).one()
    assert note.subject == "Welcome"
    assert note.body == "Welcome to SiplyGo!"
    db.close()
