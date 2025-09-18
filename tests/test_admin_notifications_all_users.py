import os
import sys
import hashlib
import pathlib
import re

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import User, RoleEnum  # noqa: E402
from main import app  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _login_super_admin(client: TestClient) -> None:
    resp = client.post(
        "/login",
        data={"email": "admin@example.com", "password": "ChangeMe!123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_all_user_notification_shows_single_row():
    db = SessionLocal()
    password_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    u1 = User(
        username="u1",
        email="u1@example.com",
        password_hash=password_hash,
        role=RoleEnum.CUSTOMER,
    )
    u2 = User(
        username="u2",
        email="u2@example.com",
        password_hash=password_hash,
        role=RoleEnum.CUSTOMER,
    )
    db.add_all([u1, u2])
    db.commit()
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)
        resp = client.post(
            "/admin/notifications",
            data={"target": "all", "subject_en": "Hi", "body_en": "Test"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        resp = client.get("/admin/notifications")
        assert resp.status_code == 200
        table_html = re.search(
            r"Sent Notifications</h2>.*?<tbody>(.*?)</tbody>", resp.text, re.S
        ).group(1)
        assert table_html.count("<tr>") == 1
        assert "All Users" in table_html
