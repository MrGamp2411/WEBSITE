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


def test_register_username_validation():
    with TestClient(app) as client:
        invalid_usernames = [
            "ab",  # too short
            "a" * 25,  # too long
            "User",  # uppercase
            "user name",  # space
            "user@name",  # invalid char
            "-user",  # starts with hyphen
            "user_",  # ends with underscore
            "user..name",  # consecutive punctuation
            "1234567",  # digits only
            "user@example.com",  # email format
            "admin",  # reserved
        ]
        for i, uname in enumerate(invalid_usernames):
            resp = client.post(
                "/register",
                data={
                    "username": uname,
                    "password": "password1",
                    "email": f"user{i}@example.com",
                    "prefix": "+41",
                    "phone": f"1234567{i:02d}",
                },
            )
            assert resp.status_code == 200
            assert "3–24 characters" in resp.text

        resp_ok = client.post(
            "/register",
            data={
                "username": "valid.user",
                "password": "password1",
                "email": "user_valid@example.com",
                "prefix": "+41",
                "phone": "123456799",
            },
            follow_redirects=False,
        )
        assert resp_ok.status_code == 303
        assert resp_ok.headers["location"] == "/login"

        resp_dup = client.post(
            "/register",
            data={
                "username": "valid.user",
                "password": "password1",
                "email": "user_dup@example.com",
                "prefix": "+41",
                "phone": "123456788",
            },
        )
        assert resp_dup.status_code == 200
        assert "Username already taken" in resp_dup.text


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
        assert "Password must be between 8 and 128 characters" in resp.text

        resp_long = client.post(
            "/register",
            data={
                "username": "validuserlong",
                "password": "p" * 129,
                "email": "userlong@example.com",
                "prefix": "+41",
                "phone": "123456783",
            },
        )
        assert resp_long.status_code == 200
        assert "Password must be between 8 and 128 characters" in resp_long.text

        resp_weak = client.post(
            "/register",
            data={
                "username": "validuser4",
                "password": "12345678",
                "email": "userweak@example.com",
                "prefix": "+41",
                "phone": "123456784",
            },
        )
        assert resp_weak.status_code == 200
        assert "Password is too common" in resp_weak.text

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
