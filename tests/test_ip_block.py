import os
import sys
import hashlib
import pathlib

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import User, RoleEnum, BlockedIP  # noqa: E402
from main import (  # noqa: E402
    app,
    load_bars_from_db,
    load_blocked_ips_from_db,
    users,
    users_by_email,
    users_by_username,
    blocked_ips,
    blocked_ip_lookup,
)


def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    blocked_ips.clear()
    blocked_ip_lookup.clear()


def _login_super_admin(client: TestClient) -> None:
    client.post('/login', data={'email': 'admin@example.com', 'password': 'pass'})


def test_admin_can_add_and_remove_blocked_ip():
    setup_db()
    db = SessionLocal()
    pwd = hashlib.sha256('pass'.encode('utf-8')).hexdigest()
    admin = User(
        username='admin',
        email='admin@example.com',
        password_hash=pwd,
        role=RoleEnum.SUPERADMIN,
    )
    db.add(admin)
    db.commit()
    db.close()

    load_bars_from_db()
    load_blocked_ips_from_db()

    with TestClient(app) as client:
        _login_super_admin(client)
        resp = client.post(
            '/admin/ip-block',
            data={'ip_address': '203.0.113.5', 'note': 'suspicious'},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers['location'] == '/admin/ip-block?message=IP+added'
        assert '203.0.113.5' in blocked_ip_lookup
        entry_id = next(iter(blocked_ips.keys()))

        delete_resp = client.post(
            f'/admin/ip-block/{entry_id}/delete',
            follow_redirects=False,
        )
        assert delete_resp.status_code == 303
        assert delete_resp.headers['location'] == '/admin/ip-block?message=IP+removed'
        assert entry_id not in blocked_ips
        assert '203.0.113.5' not in blocked_ip_lookup


def test_login_from_blocked_ip_redirects_user():
    setup_db()
    db = SessionLocal()
    pwd = hashlib.sha256('pass'.encode('utf-8')).hexdigest()
    user = User(
        username='customer',
        email='customer@example.com',
        password_hash=pwd,
        role=RoleEnum.CUSTOMER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    blocked = BlockedIP(address='203.0.113.5')
    db.add(blocked)
    db.commit()
    db.close()

    load_bars_from_db()
    load_blocked_ips_from_db()

    with TestClient(app) as client:
        resp = client.post(
            '/login',
            data={'email': 'customer@example.com', 'password': 'pass'},
            headers={'x-forwarded-for': '203.0.113.5'},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers['location'] == '/ip-blocked'

        page = client.get('/ip-blocked')
        assert page.status_code == 200

        redirect_home = client.get('/', follow_redirects=False)
        assert redirect_home.status_code == 303
        assert redirect_home.headers['location'] == '/ip-blocked'

        notes = client.get('/notifications')
        assert notes.status_code == 200

    demo_user = users[user_id]
    assert demo_user.role == 'ip_block'
    assert demo_user.base_role == 'customer'

    db = SessionLocal()
    stored_user = db.get(User, user_id)
    assert stored_user.role == RoleEnum.CUSTOMER
    db.close()
