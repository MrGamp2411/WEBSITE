import os
import sys
import pathlib
import hashlib
import re

# Use shared in-memory SQLite database
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import User, RoleEnum, Bar, UserBarRole  # noqa: E402
from main import app, refresh_bar_from_db  # noqa: E402


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


def test_update_user_details_without_password():
    db = SessionLocal()
    password_hash = hashlib.sha256("oldpass".encode("utf-8")).hexdigest()
    user = User(
        username="olduser",
        email="old@example.com",
        password_hash=password_hash,
        role=RoleEnum.CUSTOMER,
        phone="0790000000",
        prefix="+41",
        phone_e164="+41790000000",
        phone_region="CH",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)

        form = {
            "username": "newuser",
            "email": "new@example.com",
            "prefix": "+41",
            "phone": "076 555 12 34",
            "role": "bar_admin",
            "bar_ids": "",
            "credit": "5.0",
        }
        resp = client.post(
            f"/admin/users/edit/{user.id}", data=form, follow_redirects=False
        )
        assert resp.status_code == 303

    db = SessionLocal()
    updated = db.query(User).filter(User.id == user.id).first()
    assert updated.username == "newuser"
    assert updated.email == "new@example.com"
    assert updated.prefix == "+41"
    assert updated.phone == "076 555 12 34"
    assert updated.role == RoleEnum.BARADMIN
    assert float(updated.credit) == 5.0
    # password should remain unchanged
    assert updated.password_hash == password_hash
    db.close()


def test_update_user_reassign_bar():
    db = SessionLocal()
    password_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    bar1 = Bar(name="Bar3", slug="bar3")
    bar2 = Bar(name="Bar4", slug="bar4")
    db.add_all([bar1, bar2])
    db.commit()
    bar1_id = bar1.id
    bar2_id = bar2.id
    user = User(
        username="user1",
        email="user1@example.com",
        password_hash=password_hash,
        role=RoleEnum.BARADMIN,
        phone="0790000001",
        prefix="+41",
        phone_e164="+41790000001",
        phone_region="CH",
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.add(UserBarRole(user_id=user_id, bar_id=bar1_id, role=RoleEnum.BARADMIN))
    db.commit()
    db.close()

    db = SessionLocal()
    refresh_bar_from_db(bar1_id, db)
    refresh_bar_from_db(bar2_id, db)
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)
        form = {
            "username": "user1",
            "email": "user1@example.com",
            "prefix": "",
            "phone": "",
            "role": "bar_admin",
            "bar_ids": str(bar2_id),
            "credit": "0",
        }
        resp = client.post(
            f"/admin/users/edit/{user_id}", data=form, follow_redirects=False
        )
        assert resp.status_code == 303

    db = SessionLocal()
    roles = db.query(UserBarRole).filter(UserBarRole.user_id == user_id).all()
    assert len(roles) == 1
    assert roles[0].bar_id == bar2_id
    db.close()


def test_update_user_credit_and_bar_assignment():
    db = SessionLocal()
    password_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    bar1 = Bar(name="Bar1", slug="bar1")
    bar2 = Bar(name="Bar2", slug="bar2")
    db.add_all([bar1, bar2])
    db.commit()
    bar1_id = bar1.id
    bar2_id = bar2.id
    user = User(
        username="user2",
        email="user2@example.com",
        password_hash=password_hash,
        role=RoleEnum.BARADMIN,
        credit=0,
        phone="0790000002",
        prefix="+41",
        phone_e164="+41790000002",
        phone_region="CH",
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.add(UserBarRole(user_id=user_id, bar_id=bar1_id, role=RoleEnum.BARADMIN))
    db.commit()
    db.close()

    db = SessionLocal()
    refresh_bar_from_db(bar1_id, db)
    refresh_bar_from_db(bar2_id, db)
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)
        form = {
            "username": "user2",
            "email": "user2@example.com",
            "prefix": "",
            "phone": "",
            "role": "bar_admin",
            "bar_ids": str(bar2_id),
            "credit": "15.5",
        }
        resp = client.post(
            f"/admin/users/edit/{user_id}", data=form, follow_redirects=False
        )
        assert resp.status_code == 303

    db = SessionLocal()
    updated = db.query(User).filter(User.id == user_id).first()
    assert float(updated.credit) == 15.5
    roles = db.query(UserBarRole).filter(UserBarRole.user_id == user_id).all()
    assert len(roles) == 1
    assert roles[0].bar_id == bar2_id
    db.close()


def test_update_user_multiple_bar_assignment():
    db = SessionLocal()
    password_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    bar1 = Bar(name="Multi1", slug="multi1")
    bar2 = Bar(name="Multi2", slug="multi2")
    db.add_all([bar1, bar2])
    db.commit()
    bar1_id, bar2_id = bar1.id, bar2.id
    user = User(
        username="multibar",
        email="multibar@example.com",
        password_hash=password_hash,
        role=RoleEnum.BARTENDER,
        phone="0790000003",
        prefix="+41",
        phone_e164="+41790000003",
        phone_region="CH",
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    db = SessionLocal()
    refresh_bar_from_db(bar1_id, db)
    refresh_bar_from_db(bar2_id, db)
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)
        form = {
            "username": "multibar",
            "email": "multibar@example.com",
            "prefix": "",
            "phone": "",
            "role": "bartender",
            "bar_ids": [str(bar1_id), str(bar2_id)],
            "credit": "0",
        }
        resp = client.post(
            f"/admin/users/edit/{user_id}", data=form, follow_redirects=False
        )
        assert resp.status_code == 303

    db = SessionLocal()
    roles = (
        db.query(UserBarRole)
        .filter(UserBarRole.user_id == user_id)
        .order_by(UserBarRole.bar_id)
        .all()
    )
    assert [r.bar_id for r in roles] == [bar1_id, bar2_id]
    db.close()


def test_update_user_password_change():
    db = SessionLocal()
    old_hash = hashlib.sha256("old".encode("utf-8")).hexdigest()
    user = User(
        username="userpw",
        email="userpw@example.com",
        password_hash=old_hash,
        role=RoleEnum.CUSTOMER,
        phone="0790000004",
        prefix="+41",
        phone_e164="+41790000004",
        phone_region="CH",
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)
        form = {"password": "newpass123", "confirm_password": "newpass123"}
        resp = client.post(
            f"/admin/users/{user_id}/password", data=form, follow_redirects=False
        )
        assert resp.status_code == 303

    db = SessionLocal()
    updated = db.query(User).filter(User.id == user_id).first()
    from main import verify_password
    assert verify_password(updated.password_hash, "newpass123")
    db.close()


def test_admin_users_shows_reassigned_bar_after_restart():
    db = SessionLocal()
    password_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    bar1 = Bar(name="ReloadBar1", slug="reloadbar1")
    bar2 = Bar(name="ReloadBar2", slug="reloadbar2")
    db.add_all([bar1, bar2])
    db.commit()
    bar1_id, bar1_name = bar1.id, bar1.name
    bar2_id, bar2_name = bar2.id, bar2.name
    user = User(
        username="reloaduser",
        email="reload@example.com",
        password_hash=password_hash,
        role=RoleEnum.BARADMIN,
        phone="0790000005",
        prefix="+41",
        phone_e164="+41790000005",
        phone_region="CH",
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.add(UserBarRole(user_id=user_id, bar_id=bar1_id, role=RoleEnum.BARADMIN))
    db.commit()
    db.close()

    db = SessionLocal()
    refresh_bar_from_db(bar1_id, db)
    refresh_bar_from_db(bar2_id, db)
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)
        form = {
            "username": "reloaduser",
            "email": "reload@example.com",
            "prefix": "",
            "phone": "",
            "role": "bar_admin",
            "bar_ids": str(bar2_id),
            "credit": "0",
        }
        resp = client.post(
            f"/admin/users/edit/{user_id}", data=form, follow_redirects=False
        )
        assert resp.status_code == 303

    # Simulate application restart by clearing in-memory caches
    from main import users, users_by_username, users_by_email, bars

    users.clear()
    users_by_username.clear()
    users_by_email.clear()
    bars.clear()

    db = SessionLocal()
    refresh_bar_from_db(bar1_id, db)
    refresh_bar_from_db(bar2_id, db)
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)
        resp = client.get("/admin/users")
        assert resp.status_code == 200
        pattern = re.compile(
            rf"<tr>\s*<td>reloaduser</td>.*?<td>\s*{bar2_name}\s*</td>", re.DOTALL
        )
        assert pattern.search(resp.text)
