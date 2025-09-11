import os
import pathlib
import sys

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import User  # noqa: E402
from main import (
    app,
    load_bars_from_db,
    user_carts,
    users,
    users_by_email,
    users_by_username,
    bars,
)  # noqa: E402


def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    user_carts.clear()
    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    bars.clear()


def test_superadmin_can_create_user_with_email_password():
    setup_db()
    with TestClient(app) as client:
        load_bars_from_db()
        client.post("/login", data={"email": "admin@example.com", "password": "ChangeMe!123"})
        resp = client.post(
            "/admin/users/new",
            data={"email": "new@example.com", "password": "pass"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        db = SessionLocal()
        new_user = db.query(User).filter(User.email == "new@example.com").first()
        db.close()
        assert new_user is not None
