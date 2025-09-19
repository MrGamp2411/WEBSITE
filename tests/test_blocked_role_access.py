import os
import pathlib
import hashlib
import sys

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import User, RoleEnum, Notification, NotificationLog  # noqa: E402
from main import app, load_bars_from_db, user_carts, users, users_by_email, users_by_username  # noqa: E402


def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    user_carts.clear()
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def test_blocked_user_redirects_and_can_view_notifications():
    setup_db()
    with TestClient(app) as client:
        db = SessionLocal()
        pwd = hashlib.sha256('pass'.encode('utf-8')).hexdigest()
        blocked = User(username='blocked', email='blocked@example.com', password_hash=pwd, role=RoleEnum.BLOCKED)
        db.add(blocked)
        db.commit()
        db.refresh(blocked)
        log = NotificationLog(sender_id=blocked.id, target='user', user_id=blocked.id, subject='Update', body='Please review')
        db.add(log)
        db.commit()
        db.refresh(log)
        note = Notification(user_id=blocked.id, sender_id=blocked.id, log_id=log.id, subject='Update', body='Blocked message')
        db.add(note)
        db.commit()
        db.close()
        load_bars_from_db()

        client.post('/login', data={'email': 'blocked@example.com', 'password': 'pass'})

        resp = client.get('/', follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers['location'] == '/blocked'

        blocked_page = client.get('/blocked')
        assert blocked_page.status_code == 200
        assert 'Account access limited' in blocked_page.text
        assert 'support@siplygo.example.com' in blocked_page.text

        notifications_page = client.get('/notifications')
        assert notifications_page.status_code == 200
        assert 'Update' in notifications_page.text
