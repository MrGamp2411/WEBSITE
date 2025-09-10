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


def test_register_phone_length_validation():
    with TestClient(app) as client:
        resp = client.post(
            "/register",
            data={
                "username": "validuser",
                "password": "pass1234",
                "confirm_password": "pass1234",
                "email": "short@example.com",
                "prefix": "+41",
                "phone": "12345678",
            },
        )
        assert resp.status_code == 200
        assert "Phone number must be 9-10 digits" in resp.text

        resp_ok = client.post(
            "/register",
            data={
                "username": "validuser2",
                "password": "pass1234",
                "confirm_password": "pass1234",
                "email": "valid@example.com",
                "prefix": "+41",
                "phone": "123456789",
            },
            follow_redirects=False,
        )
        assert resp_ok.status_code == 303
        assert resp_ok.headers["location"] == "/login"


def test_register_phone_duplicate():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    users.clear()
    users_by_email.clear()
    users_by_username.clear()

    with TestClient(app) as client:
        resp_first = client.post(
            "/register",
            data={
                "username": "firstuser",
                "password": "pass1234",
                "confirm_password": "pass1234",
                "email": "first@example.com",
                "prefix": "+41",
                "phone": "123456789",
            },
            follow_redirects=False,
        )
        assert resp_first.status_code == 303

        resp_dup = client.post(
            "/register",
            data={
                "username": "seconduser",
                "password": "pass1234",
                "confirm_password": "pass1234",
                "email": "second@example.com",
                "prefix": "+41",
                "phone": "123456789",
            },
        )
        assert resp_dup.status_code == 200
        assert "Phone number already taken" in resp_dup.text
