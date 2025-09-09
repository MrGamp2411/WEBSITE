import os
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine  # noqa: E402
from main import app, users, users_by_email, users_by_username  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def test_register_username_length_validation():
    with TestClient(app) as client:
        resp = client.post(
            "/register",
            data={
                "username": "short",
                "password": "password1",
                "email": "user1@example.com",
                "prefix": "+41",
                "phone": "123456789",
            },
        )
        assert resp.status_code == 200
        assert "Username must be at least 8 characters" in resp.text

        resp_ok = client.post(
            "/register",
            data={
                "username": "validuser1",
                "password": "password1",
                "email": "user2@example.com",
                "prefix": "+41",
                "phone": "123456780",
            },
            follow_redirects=False,
        )
        assert resp_ok.status_code == 303
        assert resp_ok.headers["location"] == "/login"


def test_register_password_length_validation():
    with TestClient(app) as client:
        resp = client.post(
            "/register",
            data={
                "username": "validuser2",
                "password": "short",
                "email": "user3@example.com",
                "prefix": "+41",
                "phone": "123456781",
            },
        )
        assert resp.status_code == 200
        assert "Password must be at least 8 characters" in resp.text

        resp_ok = client.post(
            "/register",
            data={
                "username": "validuser3",
                "password": "longpass1",
                "email": "user4@example.com",
                "prefix": "+41",
                "phone": "123456782",
            },
            follow_redirects=False,
        )
        assert resp_ok.status_code == 303
        assert resp_ok.headers["location"] == "/login"
