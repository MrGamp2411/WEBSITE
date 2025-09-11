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


def test_register_email_format_validation():
    with TestClient(app) as client:
        resp = client.post(
            "/register",
            data={
                "email": "invalid",
                "password": "pass1234",
                "confirm_password": "pass1234",
            },
        )
        assert resp.status_code == 200
        assert "Invalid email format" in resp.text

        resp_ok = client.post(
            "/register",
            data={
                "email": "valid@example.com",
                "password": "pass1234",
                "confirm_password": "pass1234",
            },
            follow_redirects=False,
        )
        assert resp_ok.status_code == 303
        assert resp_ok.headers["location"] == "/register/details"
