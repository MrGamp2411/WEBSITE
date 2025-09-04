import os
import sys
import pathlib
import hashlib
from datetime import datetime

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import Bar, User, RoleEnum, BarClosing  # noqa: E402
from main import (
    app,
    load_bars_from_db,
    user_carts,
    users,
    users_by_email,
    users_by_username,
)  # noqa: E402


def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    user_carts.clear()
    users.clear()
    users_by_email.clear()
    users_by_username.clear()


def test_super_admin_can_confirm_monthly_payments():
    setup_db()
    with TestClient(app) as client:
        db = SessionLocal()
        bar = Bar(name="Test Bar", slug="test-bar")
        pwd = hashlib.sha256("pass".encode("utf-8")).hexdigest()
        admin = User(username="s", email="s@example.com", password_hash=pwd, role=RoleEnum.SUPERADMIN)
        closing = BarClosing(bar=bar, closed_at=datetime(2020, 1, 15), total_revenue=10)
        db.add_all([bar, admin, closing])
        db.commit(); db.refresh(bar); db.close()
        load_bars_from_db()
        client.post('/login', data={'email': 's@example.com', 'password': 'pass'})
        resp = client.get(f'/dashboard/bar/{bar.id}/orders/history')
        assert 'Confirm Payment' in resp.text
        assert 'card--accepted' in resp.text
        resp = client.post(
            f'/dashboard/bar/{bar.id}/orders/history/2020/1/confirm',
            follow_redirects=False,
        )
        assert resp.status_code == 303
        resp = client.get(f'/dashboard/bar/{bar.id}/orders/history')
        assert 'Confirm Payment' not in resp.text
        assert 'card--ready' in resp.text
        with SessionLocal() as db2:
            closing = db2.query(BarClosing).first()
            assert closing.payment_confirmed
