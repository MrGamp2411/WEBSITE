import os
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import Bar  # noqa: E402
from main import app  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_top_rated_section_sorts_and_fills():
    db = SessionLocal()
    bars = [
        Bar(name="Bar D", slug="bar-d", rating=5.0, latitude=0.03, longitude=0.0),
        Bar(name="Bar A", slug="bar-a", rating=4.9, latitude=0.0, longitude=0.0),
        Bar(name="Bar C", slug="bar-c", rating=4.8, latitude=0.02, longitude=0.0),
        Bar(name="Bar B", slug="bar-b", rating=4.5, latitude=0.01, longitude=0.0),
        Bar(name="Bar F", slug="bar-f", rating=4.2, latitude=0.06, longitude=0.0),
        Bar(name="Bar E", slug="bar-e", rating=3.5, latitude=0.5, longitude=0.0),
    ]
    db.add_all(bars)
    db.commit()
    for b in bars:
        db.refresh(b)
    db.close()

    with TestClient(app) as client:
        resp = client.get("/search?lat=0&lng=0")
        assert resp.status_code == 200
        section = resp.text.split("I più votati", 1)[1].split("Consigliati", 1)[0]
        expected = ["Bar D", "Bar A", "Bar C", "Bar B", "Bar F"]
        for name in expected:
            assert name in section
        positions = [section.index(name) for name in expected]
        assert positions == sorted(positions)
        assert "Bar E" not in section
