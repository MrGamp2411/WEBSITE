import os
import re
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import User, RoleEnum  # noqa: E402
from main import app, hash_password  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _create_user(username: str, email: str) -> int:
    db = SessionLocal()
    user = User(
        username=username,
        email=email,
        password_hash=hash_password("Password123"),
        role=RoleEnum.CUSTOMER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user.id


def _login(client: TestClient, email: str) -> None:
    resp = client.post(
        "/login",
        data={"email": email, "password": "Password123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_cross_origin_post_is_blocked():
    _create_user("csrf_user", "csrf-user@example.com")
    with TestClient(app) as client:
        _login(client, "csrf-user@example.com")
        resp = client.post(
            "/profile",
            data={
                "username": "csrf_user",
                "email": "csrf-user@example.com",
                "prefix": "+41",
                "phone": "0790000000",
            },
            headers={"origin": "http://evil.test"},
            follow_redirects=False,
        )
        assert resp.status_code == 403
        assert b"CSRF token" in resp.content


def test_post_with_csrf_token_succeeds():
    _create_user("csrf_user2", "csrf-user2@example.com")
    with TestClient(app) as client:
        _login(client, "csrf-user2@example.com")
        page = client.get("/profile")
        assert page.status_code == 200
        match = re.search(r'<meta name="csrf-token" content="([^"]+)"', page.text)
        assert match is not None
        token = match.group(1)
        resp = client.post(
            "/profile",
            data={
                "username": "csrf_user2",
                "email": "csrf-user2@example.com",
                "prefix": "+41",
                "phone": "0790000001",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"].startswith("/profile")
