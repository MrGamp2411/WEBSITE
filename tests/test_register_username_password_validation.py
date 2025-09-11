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


def _start(client: TestClient, email: str) -> None:
    resp = client.post(
        "/register",
        data={"email": email, "password": "password1", "confirm_password": "password1"},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_register_username_validation():
    with TestClient(app) as client:
        invalid_usernames = [
            "ab",
            "a" * 25,
            "User",
            "user name",
            "user@name",
            "-user",
            "user_",
            "user..name",
            "1234567",
            "user@example.com",
            "admin",
        ]
        for i, uname in enumerate(invalid_usernames):
            _start(client, f"user{i}@example.com")
            resp = client.post(
                "/register/details",
                data={"username": uname, "prefix": "+41", "phone": f"07655512{i:02d}"},
            )
            assert resp.status_code == 200
            assert "3–24 characters" in resp.text
            client.get("/logout")

        _start(client, "user_valid@example.com")
        resp_ok = client.post(
            "/register/details",
            data={"username": "valid.user", "prefix": "+41", "phone": "0765551299"},
            follow_redirects=False,
        )
        assert resp_ok.status_code == 303
        assert resp_ok.headers["location"] == "/login"
        client.get("/logout")
        _start(client, "user_dup@example.com")
        resp_dup = client.post(
            "/register/details",
            data={"username": "valid.user", "prefix": "+41", "phone": "0765551288"},
        )
        assert resp_dup.status_code == 200
        assert "Username already taken" in resp_dup.text


def test_register_password_length_validation():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    with TestClient(app) as client:
        resp = client.post(
            "/register",
            data={"email": "user3@example.com", "password": "short", "confirm_password": "short"},
        )
        assert resp.status_code == 200
        assert "Password must be between 8 and 128 characters" in resp.text

        resp_long = client.post(
            "/register",
            data={"email": "userlong@example.com", "password": "p" * 129, "confirm_password": "p" * 129},
        )
        assert resp_long.status_code == 200
        assert "Password must be between 8 and 128 characters" in resp_long.text

        resp_weak = client.post(
            "/register",
            data={"email": "userweak@example.com", "password": "12345678", "confirm_password": "12345678"},
        )
        assert resp_weak.status_code == 200
        assert "Password is too common" in resp_weak.text

        resp_ok = client.post(
            "/register",
            data={"email": "user4@example.com", "password": "longpass1", "confirm_password": "longpass1"},
            follow_redirects=False,
        )
        assert resp_ok.status_code == 303
        assert resp_ok.headers["location"] == "/register/details"


def test_register_password_mismatch_validation():
    with TestClient(app) as client:
        resp = client.post(
            "/register",
            data={"email": "confirm@example.com", "password": "password1", "confirm_password": "different"},
        )
        assert resp.status_code == 200
        assert "Passwords do not match" in resp.text
