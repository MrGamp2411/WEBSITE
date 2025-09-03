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


def test_bartender_orders_page_contains_completed_list():
    setup_db()
    with TestClient(app) as client:
        db = SessionLocal()
        bar = Bar(name="Test Bar", slug="test-bar")
        pwd = hashlib.sha256("pass".encode("utf-8")).hexdigest()
        bartender = User(username="b", email="b@example.com", password_hash=pwd, role=RoleEnum.BARTENDER)
        db.add_all([bar, bartender])
        db.commit()
        db.add(UserBarRole(user_id=bartender.id, bar_id=bar.id, role=RoleEnum.BARTENDER))
        db.commit(); db.refresh(bar); db.close()
        load_bars_from_db()
        client.post('/login', data={'email': 'b@example.com', 'password': 'pass'})
        resp = client.get(f'/dashboard/bar/{bar.id}/orders')
        assert resp.status_code == 200
        assert '<div id="completed-orders"' in resp.text
