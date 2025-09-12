import os
import pathlib
import sys
from datetime import datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from database import Base, engine, SessionLocal  # noqa: E402
from models import User, RoleEnum, Notification, NotificationLog  # noqa: E402
from main import purge_old_notifications_once  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_old_notifications_are_removed():
    db = SessionLocal()
    user = User(
        username="u",
        email="u@example.com",
        password_hash="h",
        role=RoleEnum.CUSTOMER,
    )
    db.add(user)
    db.commit()

    old_time = datetime.utcnow() - timedelta(days=31)
    recent_time = datetime.utcnow() - timedelta(days=10)

    old_log = NotificationLog(
        sender_id=user.id,
        target="user",
        user_id=user.id,
        subject="Old",
        body="",
        created_at=old_time,
    )
    recent_log = NotificationLog(
        sender_id=user.id,
        target="user",
        user_id=user.id,
        subject="New",
        body="",
        created_at=recent_time,
    )
    db.add_all([old_log, recent_log])
    db.commit()

    old_note = Notification(
        user_id=user.id,
        sender_id=user.id,
        log_id=old_log.id,
        subject="Old",
        body="",
        created_at=old_time,
    )
    new_note = Notification(
        user_id=user.id,
        sender_id=user.id,
        log_id=recent_log.id,
        subject="New",
        body="",
        created_at=recent_time,
    )
    db.add_all([old_note, new_note])
    db.commit()

    purge_old_notifications_once(db, datetime.utcnow())

    subjects = [n.subject for n in db.query(Notification).all()]
    assert subjects == ["New"]
    assert db.query(NotificationLog).count() == 1
    db.close()
