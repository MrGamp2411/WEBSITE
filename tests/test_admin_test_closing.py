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


def test_super_admin_can_create_and_delete_test_closing():
    setup_db()
    with TestClient(app) as client:
        db = SessionLocal()
        bar = Bar(name="Test Bar", slug="test-bar")
        pwd = hashlib.sha256("pass".encode("utf-8")).hexdigest()
        admin = User(username="s", email="s@example.com", password_hash=pwd, role=RoleEnum.SUPERADMIN)
        db.add_all([bar, admin])
        db.commit(); db.refresh(bar); db.close()
        load_bars_from_db()
        client.post('/login', data={'email': 's@example.com', 'password': 'pass'})
        resp = client.post(f'/admin/payments/{bar.id}/test_closing', follow_redirects=False)
        assert resp.status_code == 303
        resp = client.get(f'/dashboard/bar/{bar.id}/orders/history')
        now = datetime.now()
        if now.month == 1:
            year = now.year - 1
            month = 12
        else:
            year = now.year
            month = now.month - 1
        label = datetime(year, month, 1).strftime("%B %Y")
        assert label in resp.text
        resp = client.post(f'/admin/payments/{bar.id}/test_closing/delete', follow_redirects=False)
        assert resp.status_code == 303
        resp = client.get(f'/dashboard/bar/{bar.id}/orders/history')
        assert label not in resp.text
        with SessionLocal() as db2:
            closing = db2.query(BarClosing).first()
            assert closing is None
