import os
import sys
import hashlib
import pathlib
from datetime import datetime

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import User, RoleEnum, BlockedIP  # noqa: E402
from main import (  # noqa: E402
    BlockedIPEntry,
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
    assert demo_user.base_role == 'ip_block'

    db = SessionLocal()
    stored_user = db.get(User, user_id)
    assert stored_user.role == RoleEnum.IPBLOCK
    db.close()


def test_super_admin_login_ignores_ip_block():
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
    db.refresh(admin)
    admin_id = admin.id
    blocked = BlockedIP(address='203.0.113.5')
    db.add(blocked)
    db.commit()
    db.close()

    load_bars_from_db()
    load_blocked_ips_from_db()

    with TestClient(app) as client:
        resp = client.post(
            '/login',
            data={'email': 'admin@example.com', 'password': 'pass'},
            headers={'x-forwarded-for': '203.0.113.5'},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers['location'] == '/dashboard'

        dashboard = client.get(
            '/admin/dashboard',
            headers={'x-forwarded-for': '203.0.113.5'},
        )
        assert dashboard.status_code == 200

    demo_user = users[admin_id]
    assert demo_user.role == 'super_admin'
    assert demo_user.base_role == 'super_admin'

    db = SessionLocal()
    stored_admin = db.get(User, admin_id)
    assert stored_admin.role == RoleEnum.SUPERADMIN
    db.close()


def test_register_from_blocked_ip_sets_role():
    setup_db()
    db = SessionLocal()
    blocked = BlockedIP(address='203.0.113.5')
    db.add(blocked)
    db.commit()
    db.close()

    load_bars_from_db()
    load_blocked_ips_from_db()

    with TestClient(app) as client:
        resp = client.post(
            '/register',
            data={
                'email': 'blocked@example.com',
                'password': 'pass12345',
                'confirm_password': 'pass12345',
            },
            headers={'x-forwarded-for': '203.0.113.5'},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers['location'] == '/ip-blocked'

        page = client.get('/ip-blocked')
        assert page.status_code == 200

        details_redirect = client.get('/register/details', follow_redirects=False)
        assert details_redirect.status_code == 303
        assert details_redirect.headers['location'] == '/ip-blocked'

    db = SessionLocal()
    stored_user = db.query(User).filter(User.email == 'blocked@example.com').first()
    assert stored_user is not None
    user_id = stored_user.id
    assert stored_user.role == RoleEnum.IPBLOCK
    db.close()

    demo_user = users[user_id]
    assert demo_user.role == 'ip_block'
    assert demo_user.base_role == 'ip_block'


def test_existing_session_is_ip_blocked_after_block_added():
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
    db.close()

    load_bars_from_db()
    load_blocked_ips_from_db()

    with TestClient(app) as client:
        resp = client.post(
            '/login',
            data={'email': 'customer@example.com', 'password': 'pass'},
            headers={'x-forwarded-for': '198.51.100.10'},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers['location'] == '/dashboard'

        profile = client.get(
            '/profile',
            headers={'x-forwarded-for': '198.51.100.10'},
        )
        assert profile.status_code == 200

        db = SessionLocal()
        entry = BlockedIP(address='198.51.100.10')
        db.add(entry)
        db.commit()
        db.refresh(entry)
        record = BlockedIPEntry(
            entry.id,
            entry.address,
            entry.note or '',
            entry.created_at or datetime.utcnow(),
        )
        blocked_ips[record.id] = record
        blocked_ip_lookup[record.address] = record
        db.close()

        redirected = client.get(
            '/profile',
            headers={'x-forwarded-for': '198.51.100.10'},
            follow_redirects=False,
        )
        assert redirected.status_code == 303
        assert redirected.headers['location'] == '/ip-blocked'

        blocked_page = client.get(
            '/ip-blocked',
            headers={'x-forwarded-for': '198.51.100.10'},
        )
        assert blocked_page.status_code == 200

    demo_user = users[user_id]
    assert demo_user.role == 'ip_block'
    assert demo_user.base_role == 'ip_block'

    db = SessionLocal()
    stored_user = db.get(User, user_id)
    assert stored_user.role == RoleEnum.IPBLOCK
    db.close()
