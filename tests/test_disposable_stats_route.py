import os
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from database import Base, engine, SessionLocal  # noqa: E402
from models import User, RoleEnum  # noqa: E402
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


def test_disposable_stats_returns_404_when_feature_disabled(monkeypatch):
    reset_db()
    monkeypatch.delenv("DISPOSABLE_STATS_ENABLED", raising=False)
    with TestClient(app) as client:
        _login(client, "admin@example.com", "ChangeMe!123")
        response = client.get("/internal/disposable-domains/stats")
        assert response.status_code == 404


def test_disposable_stats_requires_authentication(monkeypatch):
    reset_db()
    monkeypatch.setenv("DISPOSABLE_STATS_ENABLED", "true")
    with TestClient(app) as client:
        response = client.get("/internal/disposable-domains/stats")
        assert response.status_code == 401


def test_disposable_stats_requires_super_admin(monkeypatch):
    reset_db()
    monkeypatch.setenv("DISPOSABLE_STATS_ENABLED", "true")
    db = SessionLocal()
    try:
        password = hash_password("UserPass123!")
        user = User(
            username="user",
            email="user@example.com",
            password_hash=password,
            role=RoleEnum.FINANCE,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        _login(client, "user@example.com", "UserPass123!")
        response = client.get("/internal/disposable-domains/stats")
        assert response.status_code == 403


def test_disposable_stats_super_admin_success(monkeypatch):
    reset_db()
    monkeypatch.setenv("DISPOSABLE_STATS_ENABLED", "true")
    with TestClient(app) as client:
        _login(client, "admin@example.com", "ChangeMe!123")
        response = client.get("/internal/disposable-domains/stats")
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == {"count", "ttl_min", "last_refreshed"}
