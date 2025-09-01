import os
import sys
import pathlib
import hashlib

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
        phone="123",
        prefix="+1",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)

        form = {
        "username": "newuser",
        "password": "",
        "email": "new@example.com",
        "prefix": "+41",
        "phone": "763661800",
        "role": "bar_admin",
        "bar_id": "",
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
    assert updated.phone == "763661800"
    assert updated.role == RoleEnum.BARADMIN
    assert float(updated.credit) == 5.0
    # password should remain unchanged
    assert updated.password_hash == password_hash
    db.close()


def test_update_user_reassign_bar():
    db = SessionLocal()
    password_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    bar1 = Bar(name="Bar1", slug="bar1")
    bar2 = Bar(name="Bar2", slug="bar2")
    db.add_all([bar1, bar2])
    db.commit()
    bar1_id = bar1.id
    bar2_id = bar2.id
    user = User(
        username="user1",
        email="user1@example.com",
        password_hash=password_hash,
        role=RoleEnum.BARADMIN,
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
            "password": "",
            "email": "user1@example.com",
            "prefix": "",
            "phone": "",
            "role": "bar_admin",
            "bar_id": str(bar2_id),
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
