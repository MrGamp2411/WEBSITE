import os
import sys
import json
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import Bar  # noqa: E402
from main import app  # noqa: E402


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def extract_recommended_section(html: str) -> str:
    return html.split("Consigliati", 1)[1]


def test_recommended_only_open_within_20km():
    reset_db()
    db = SessionLocal()
    hours = json.dumps({str(i): {"open": "00:00", "close": "23:59"} for i in range(7)})
    bars = [
        Bar(name="NearOpenA", slug="near-open-a", latitude=0.05, longitude=0.0, opening_hours=hours),
        Bar(name="NearOpenB", slug="near-open-b", latitude=0.02, longitude=0.0, opening_hours=hours),
        Bar(name="FarOpen", slug="far-open", latitude=0.25, longitude=0.0, opening_hours=hours),
        Bar(
            name="NearClosed",
            slug="near-closed",
            latitude=0.01,
            longitude=0.0,
            opening_hours=hours,
            manual_closed=True,
        ),
    ]
    db.add_all(bars)
    db.commit()
    for b in bars:
        db.refresh(b)
    db.close()

    with TestClient(app) as client:
        resp = client.get("/search?lat=0&lng=0")
        assert resp.status_code == 200
        section = extract_recommended_section(resp.text)
        assert "NearOpenA" in section
        assert "NearOpenB" in section
        assert "FarOpen" not in section
        assert "NearClosed" not in section

