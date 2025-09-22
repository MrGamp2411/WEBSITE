import os
import sys
import pathlib
import json

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import User, RoleEnum, AuditLog  # noqa: E402
from main import app, hash_password, verify_password  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _create_user(username: str, email: str, phone: str, phone_e164: str) -> int:
    db = SessionLocal()
    user = User(
        username=username,
        email=email,
        password_hash=hash_password("Oldpass123"),
        role=RoleEnum.CUSTOMER,
        phone=phone,
        prefix="+41",
        phone_e164=phone_e164,
        phone_region="CH",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user.id


def _login(client: TestClient, email: str) -> None:
    resp = client.post(
        "/login",
        data={"email": email, "password": "Oldpass123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_profile_update_details():
    user_id = _create_user("olduser", "old@example.com", "0790000000", "+41790000000")
    with TestClient(app) as client:
        _login(client, "old@example.com")
        resp = client.post(
            "/profile",
            data={
                "username": "newuser",
                "email": "new@example.com",
                "prefix": "+41",
                "phone": "0765551234",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/profile?success=1"
    db = SessionLocal()
    updated = db.query(User).filter(User.id == user_id).first()
    assert updated.username == "newuser"
    assert updated.email == "new@example.com"
    assert updated.phone == "0765551234"
    log = (
        db.query(AuditLog)
        .filter(
            AuditLog.actor_user_id == user_id,
            AuditLog.action == "profile_update",
        )
        .first()
    )
    assert log is not None
    payload = json.loads(log.payload_json)
    changes = {change["field"]: change for change in payload.get("changes", [])}
    assert changes["username"]["from"] == "olduser"
    assert changes["username"]["to"] == "newuser"
    assert changes["email"]["from"] == "old@example.com"
    assert changes["email"]["to"] == "new@example.com"
    assert changes["phone"]["from"] == "+41 0790000000"
    assert changes["phone"]["to"] == "+41 0765551234"
    db.close()


def test_profile_update_password_change():
    user_id = _create_user("olduser2", "old2@example.com", "0790000001", "+41790000001")
    with TestClient(app) as client:
        _login(client, "old2@example.com")
        resp = client.post(
            "/profile/password",
            data={
                "current_password": "Oldpass123",
                "password": "Newpass123",
                "confirm_password": "Newpass123",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"
    db = SessionLocal()
    updated = db.query(User).filter(User.id == user_id).first()
    assert verify_password(updated.password_hash, "Newpass123")
    db.close()


def test_profile_update_wrong_current_password():
    user_id = _create_user("olduser3", "old3@example.com", "0790000002", "+41790000002")
    with TestClient(app) as client:
        _login(client, "old3@example.com")
        resp = client.post(
            "/profile/password",
            data={
                "current_password": "Wrongpass123",
                "password": "Newpass123",
                "confirm_password": "Newpass123",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert b"Current password is incorrect" in resp.content
    db = SessionLocal()
    updated = db.query(User).filter(User.id == user_id).first()
    assert verify_password(updated.password_hash, "Oldpass123")
    db.close()

