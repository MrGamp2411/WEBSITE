import os
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine  # noqa: E402
from main import app, users, users_by_email, users_by_username  # noqa: E402
from models import User  # noqa: E402
from sqlalchemy import text  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def _start(client: TestClient, email: str) -> None:
    resp = client.post(
        "/register",
        data={"email": email, "password": "pass1234", "confirm_password": "pass1234"},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_register_phone_valid_numbers():
    cases = [
        ("+41", "076 555 12 34", "+41765551234"),
        ("+39", "345 123 4567", "+393451234567"),
        ("+49", "0151 23456789", "+4915123456789"),
        ("+33", "06 12 34 56 78", "+33612345678"),
    ]
    with TestClient(app) as client:
        for i, (dial, number, e164) in enumerate(cases):
            _start(client, f"u{i}@example.com")
            resp = client.post(
                "/register/details",
                data={"username": f"user{i}", "prefix": dial, "phone": number},
                follow_redirects=False,
            )
            assert resp.status_code == 303
            with engine.connect() as conn:
                db_user = conn.execute(
                    text("SELECT phone_e164 FROM users WHERE email=:email"),
                    {"email": f"u{i}@example.com"},
                ).fetchone()
            assert db_user[0] == e164
            client.get("/logout")


def test_register_phone_prefix_mismatch():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    with TestClient(app) as client:
        _start(client, "mm1@example.com")
        resp = client.post(
            "/register/details",
            data={"username": "mismatch1", "prefix": "+41", "phone": "0039 345 123 4567"},
        )
        assert resp.status_code == 422
        assert "Il numero non corrisponde al prefisso selezionato (+41)." in resp.text
        client.get("/logout")
        _start(client, "mm2@example.com")
        resp2 = client.post(
            "/register/details",
            data={"username": "mismatch2", "prefix": "+39", "phone": "0041 76 555 12 34"},
        )
        assert resp2.status_code == 422
        assert "Il numero non corrisponde al prefisso selezionato (+39)." in resp2.text


def test_register_phone_format_errors():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    with TestClient(app) as client:
        _start(client, "short@example.com")
        resp_short = client.post(
            "/register/details",
            data={"username": "shortnum", "prefix": "+41", "phone": "123"},
        )
        assert resp_short.status_code == 422
        assert "Lunghezza numero non valida." in resp_short.text
        client.get("/logout")
        _start(client, "ext@example.com")
        resp_ext = client.post(
            "/register/details",
            data={"username": "extnum", "prefix": "+39", "phone": "345-123-4567 ext. 2"},
        )
        assert resp_ext.status_code == 422
        assert "Le estensioni non sono supportate." in resp_ext.text


def test_register_phone_duplicate():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    users.clear()
    users_by_email.clear()
    users_by_username.clear()

    with TestClient(app) as client:
        _start(client, "first@example.com")
        resp_first = client.post(
            "/register/details",
            data={"username": "firstuser", "prefix": "+41", "phone": "076 555 12 34"},
            follow_redirects=False,
        )
        assert resp_first.status_code == 303
        client.get("/logout")
        _start(client, "second@example.com")
        resp_dup = client.post(
            "/register/details",
            data={"username": "seconduser", "prefix": "+41", "phone": "076 555 12 34"},
        )
        assert resp_dup.status_code == 409
        assert "Phone already in use" in resp_dup.text
