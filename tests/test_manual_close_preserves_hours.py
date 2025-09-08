import os
import pathlib
import sys
import json

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import Bar  # noqa: E402
import main  # noqa: E402
from main import app, DemoUser, users, users_by_email, users_by_username, bars  # noqa: E402
from datetime import datetime  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    bars.clear()


def teardown_module(module):
    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    bars.clear()


def test_manual_close_preserves_hours(monkeypatch):
    hours = {"0": {"open": "09:00", "close": "17:00"}}

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2024, 1, 1, 12, 0, tzinfo=tz)

    monkeypatch.setattr(main, "datetime", FixedDatetime)
    monkeypatch.setenv("BAR_TIMEZONE", "UTC")

    db = SessionLocal()
    bar = Bar(
        name="Test Bar",
        slug="test-bar",
        address="Addr",
        city="City",
        state="State",
        latitude=0.0,
        longitude=0.0,
        description="Desc",
        opening_hours=json.dumps(hours),
        is_open_now=True,
    )
    db.add(bar)
    db.commit()
    db.refresh(bar)
    bars[bar.id] = bar
    db.close()

    admin = DemoUser(
        id=1,
        username="baradmin",
        password="pass",
        email="admin@example.com",
        role="bar_admin",
        bar_ids=[bar.id],
    )
    users[admin.id] = admin
    users_by_email[admin.email] = admin
    users_by_username[admin.username] = admin

    client = TestClient(app)
    client.post("/login", data={"email": admin.email, "password": admin.password})

    resp = client.post(
        f"/admin/bars/edit/{bar.id}/info",
        data={
            "name": "Test Bar",
            "address": "Addr",
            "city": "City",
            "state": "State",
            "latitude": "0",
            "longitude": "0",
            "description": "Desc",
            "manual_closed": "on",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303

    check = SessionLocal()
    updated = check.get(Bar, bar.id)
    assert json.loads(updated.opening_hours) == hours
    assert updated.manual_closed is True
    assert updated.is_open_now is False
    check.close()
    assert bars[bar.id].manual_closed is True
    assert bars[bar.id].opening_hours == hours

    resp = client.post(
        f"/admin/bars/edit/{bar.id}/info",
        data={
            "name": "Test Bar",
            "address": "Addr",
            "city": "City",
            "state": "State",
            "latitude": "0",
            "longitude": "0",
            "description": "Desc",
            "open_0": "09:00",
            "close_0": "17:00",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303

    check = SessionLocal()
    reopened = check.get(Bar, bar.id)
    assert json.loads(reopened.opening_hours) == hours
    assert reopened.manual_closed is False
    assert reopened.is_open_now is True
    check.close()
    assert bars[bar.id].manual_closed is False
    assert bars[bar.id].opening_hours == hours
