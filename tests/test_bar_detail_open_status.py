import os
import sys
import json
import pathlib
from datetime import datetime

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import Bar as BarModel  # noqa: E402
from main import app, bars, load_bars_from_db  # noqa: E402
import main  # noqa: E402

def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    bars.clear()

def add_bar(hours_json: str) -> int:
    db = SessionLocal()
    bar = BarModel(name="Bar", slug="bar", opening_hours=hours_json)
    db.add(bar)
    db.commit()
    db.refresh(bar)
    bar_id = bar.id
    db.close()
    return bar_id

def test_bar_detail_shows_open_status(monkeypatch):
    reset_db()
    monkeypatch.setenv("BAR_TIMEZONE", "UTC")
    hours = json.dumps({"0": {"open": "08:00", "close": "17:00"}})
    bar_id = add_bar(hours)

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2024, 1, 1, 12, 0, tzinfo=tz)

    monkeypatch.setattr(main, "datetime", FakeDatetime)

    load_bars_from_db()

    client = TestClient(app)
    resp = client.get(f"/bars/{bar_id}")
    assert resp.status_code == 200
    assert "Open now" in resp.text

def test_bar_detail_shows_closed_status(monkeypatch):
    reset_db()
    monkeypatch.setenv("BAR_TIMEZONE", "UTC")
    hours = json.dumps({"0": {"open": "08:00", "close": "17:00"}})
    bar_id = add_bar(hours)

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2024, 1, 1, 18, 0, tzinfo=tz)

    monkeypatch.setattr(main, "datetime", FakeDatetime)

    load_bars_from_db()

    client = TestClient(app)
    resp = client.get(f"/bars/{bar_id}")
    assert resp.status_code == 200
    assert "Closed now" in resp.text
