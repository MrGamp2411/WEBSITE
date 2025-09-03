import os
import sys
import pathlib
import hashlib

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import Bar, User, UserBarRole, RoleEnum  # noqa: E402
from main import app, load_bars_from_db, user_carts, users, users_by_email, users_by_username  # noqa: E402


def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    user_carts.clear()
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def test_bar_admin_dashboard_shows_bar_sections():
    setup_db()
    with TestClient(app) as client:
        db = SessionLocal()
        bar = Bar(name="Test Bar", slug="test-bar")
        pwd = hashlib.sha256("pass".encode("utf-8")).hexdigest()
        admin = User(username="a", email="a@example.com", password_hash=pwd, role=RoleEnum.BARADMIN)
        db.add_all([bar, admin])
        db.commit()
        db.add(UserBarRole(user_id=admin.id, bar_id=bar.id, role=RoleEnum.BARADMIN))
        db.commit(); db.refresh(bar); db.close()
        load_bars_from_db()
        client.post('/login', data={'email': 'a@example.com', 'password': 'pass'})
        resp = client.get('/dashboard')
        assert resp.status_code == 200
        assert 'class="bar-toggle"' in resp.text
        assert 'class="bar-sections"' in resp.text
