import sys
import pathlib
import hashlib

import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import User  # noqa: E402
from main import app, users, users_by_email, users_by_username  # noqa: E402


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_session_survives_restart():
    reset_db()
    db = SessionLocal()
    pwd = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    user = User(username="u", email="u@example.com", password_hash=pwd)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()

    with TestClient(app) as client:
        client.post("/login", data={"email": "u@example.com", "password": "pass"})
        # simulate server restart by clearing in-memory caches
        users.clear()
        users_by_email.clear()
        users_by_username.clear()
        resp = client.get("/profile")
        assert resp.status_code == 200
        assert "Profile" in resp.text
