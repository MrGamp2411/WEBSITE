import json
import os
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from database import Base, engine, SessionLocal  # noqa: E402
from models import AuditLog, Bar, User, RoleEnum  # noqa: E402
from main import app, hash_password, seed_super_admin  # noqa: E402


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_super_admin()


def _login(client: TestClient, email: str, password: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_create_bar_requires_authentication():
    reset_db()
    with TestClient(app) as client:
        response = client.post(
            "/api/bars", json={"name": "Test Bar", "slug": "test-bar"}
        )
        assert response.status_code == 401

    db = SessionLocal()
    try:
        log = (
            db.query(AuditLog)
            .filter(AuditLog.action == "unauthenticated_api_bar_create")
            .one()
        )
        payload = json.loads(log.payload_json)
        assert payload["slug"] == "test-bar"
    finally:
        db.close()


def test_create_bar_requires_super_admin_role():
    reset_db()
    db = SessionLocal()
    try:
        password = hash_password("UserPass123!")
        user = User(
            username="user",
            email="user@example.com",
            password_hash=password,
            role=RoleEnum.CUSTOMER,
        )
        db.add(user)
        db.commit()
        user_id = user.id
    finally:
        db.close()

    with TestClient(app) as client:
        _login(client, "user@example.com", "UserPass123!")
        response = client.post(
            "/api/bars", json={"name": "Another Bar", "slug": "another-bar"}
        )
        assert response.status_code == 403

    db = SessionLocal()
    try:
        log = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "forbidden_api_bar_create",
                AuditLog.actor_user_id == user_id,
            )
            .one()
        )
        payload = json.loads(log.payload_json)
        assert payload["slug"] == "another-bar"
    finally:
        db.close()


def test_super_admin_can_create_bar():
    reset_db()
    with TestClient(app) as client:
        _login(client, "admin@example.com", "ChangeMe!123")
        response = client.post(
            "/api/bars", json={"name": "Admin Bar", "slug": "admin-bar"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "admin-bar"

    db = SessionLocal()
    try:
        bar = db.query(Bar).filter(Bar.slug == "admin-bar").one()
        log = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "api_create_bar",
                AuditLog.entity_id == bar.id,
            )
            .one()
        )
        payload = json.loads(log.payload_json)
        assert payload["slug"] == "admin-bar"
    finally:
        db.close()
