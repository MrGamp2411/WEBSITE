import os
import sys
import pathlib
import hashlib

# Use shared in-memory SQLite database
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import User, RoleEnum  # noqa: E402
from main import app  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_user():
    db = SessionLocal()
    password_hash = hashlib.sha256("testpass".encode("utf-8")).hexdigest()
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=password_hash,
        role=RoleEnum.CUSTOMER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def _login_user(client: TestClient, email: str, password: str) -> None:
    resp = client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_topup_adds_credit():
    user = _register_user()
    with TestClient(app) as client:
        _login_user(client, user.email, "testpass")
        resp = client.get(
            "/topup",
            params={"amount": "10", "card": "4111111111111111", "expiry": "12/24", "cvc": "123"},
        )
        assert resp.status_code == 200
    db = SessionLocal()
    updated = db.query(User).filter(User.id == user.id).first()
    assert float(updated.credit) == 10.0
    db.close()
