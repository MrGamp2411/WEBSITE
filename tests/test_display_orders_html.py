import os
import pathlib
import hashlib
import sys

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


def test_display_orders_page_shows_two_columns():
    setup_db()
    with TestClient(app) as client:
        db = SessionLocal()
        bar = Bar(name="Test Bar", slug="test-bar")
        pwd = hashlib.sha256("pass".encode("utf-8")).hexdigest()
        display = User(username="d", email="d@example.com", password_hash=pwd, role=RoleEnum.DISPLAY)
        db.add_all([bar, display])
        db.commit()
        db.add(UserBarRole(user_id=display.id, bar_id=bar.id, role=RoleEnum.DISPLAY))
        db.commit(); db.refresh(bar); db.close()
        load_bars_from_db()
        client.post('/login', data={'email': 'd@example.com', 'password': 'pass'})
        resp = client.get(f'/dashboard/bar/{bar.id}/orders')
        assert resp.status_code == 200
        assert '<div id="preparing-orders"' in resp.text
        assert '<div id="ready-orders"' in resp.text
        assert 'Incoming Orders' not in resp.text
        assert 'Completed' not in resp.text
