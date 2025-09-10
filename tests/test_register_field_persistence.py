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


def test_register_preserves_fields_on_error():
    with TestClient(app) as client:
        resp = client.post(
            "/register",
            data={
                "username": "myuser",
                "password": "pass1234",
                "confirm_password": "pass1234",
                "email": "invalid",
                "prefix": "+44",
                "phone": "07123 456789",
            },
        )
        assert resp.status_code == 200
        assert 'value="myuser"' in resp.text
        assert 'value="invalid"' in resp.text
        assert 'value="07123 456789"' in resp.text
        assert '<option value="+44" selected>' in resp.text

