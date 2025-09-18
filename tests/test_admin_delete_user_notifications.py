import hashlib
import os
import pathlib
import sys

from sqlalchemy import or_

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import (  # noqa: E402
    User,
    RoleEnum,
    Notification,
    NotificationLog,
)
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


def test_delete_user_removes_notifications_and_logs():
    db = SessionLocal()
    password_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    victim = User(
        username="victim",
        email="victim@example.com",
        password_hash=password_hash,
        role=RoleEnum.CUSTOMER,
    )
    other = User(
        username="other",
        email="other@example.com",
        password_hash=password_hash,
        role=RoleEnum.CUSTOMER,
    )
    db.add_all([victim, other])
    db.commit()
    db.refresh(victim)
    db.refresh(other)
    victim_id = victim.id
    other_id = other.id

    manual_log = NotificationLog(
        sender_id=victim_id,
        target="user",
        user_id=other_id,
        subject="Ping",
        body="Body",
        subject_translations={"en": "Ping"},
        body_translations={"en": "Body"},
    )
    db.add(manual_log)
    db.flush()
    db.add(
        Notification(
            user_id=other_id,
            sender_id=victim_id,
            log_id=manual_log.id,
            subject="Ping",
            body="Body",
            subject_translations={"en": "Ping"},
            body_translations={"en": "Body"},
        )
    )
    db.commit()
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)
        resp = client.post(
            "/admin/notifications",
            data={
                "target": "user",
                "user_id": victim_id,
                "subject_en": "Hello",
                "body_en": "Message",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

        resp = client.post(
            f"/admin/users/{victim_id}/delete", follow_redirects=False
        )
        assert resp.status_code == 303

    db = SessionLocal()
    assert db.get(User, victim_id) is None
    assert (
        db.query(Notification)
        .filter(
            or_(
                Notification.user_id == victim_id,
                Notification.sender_id == victim_id,
            )
        )
        .count()
        == 0
    )
    assert (
        db.query(NotificationLog)
        .filter(
            or_(
                NotificationLog.user_id == victim_id,
                NotificationLog.sender_id == victim_id,
            )
        )
        .count()
        == 0
    )
    db.close()

