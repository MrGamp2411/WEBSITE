import os
import sys
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


def extract_top_section(html: str) -> str:
    return html.split("I più votati", 1)[1].split("Consigliati", 1)[0]


def test_top_rated_within_5km():
    reset_db()
    db = SessionLocal()
    bars = [
        Bar(name="Near A", slug="near-a", rating=5.0, latitude=0.03, longitude=0.0),
        Bar(name="Near B", slug="near-b", rating=4.5, latitude=0.04, longitude=0.0),
        Bar(name="Mid", slug="mid", rating=4.9, latitude=0.08, longitude=0.0),
    ]
    db.add_all(bars)
    db.commit()
    for b in bars:
        db.refresh(b)
    db.close()

    with TestClient(app) as client:
        resp = client.get("/search?lat=0&lng=0")
        assert resp.status_code == 200
        section = extract_top_section(resp.text)
        assert "Near A" in section
        assert "Near B" in section
        assert "Mid" not in section
        assert section.index("Near A") < section.index("Near B")


def test_top_rated_no_nearby_message():
    reset_db()
    db = SessionLocal()
    bars = [
        Bar(name="Far A", slug="far-a", rating=5.0, latitude=0.15, longitude=0.0),
        Bar(name="Far B", slug="far-b", rating=4.5, latitude=-0.16, longitude=0.0),
    ]
    db.add_all(bars)
    db.commit()
    for b in bars:
        db.refresh(b)
    db.close()

    with TestClient(app) as client:
        resp = client.get("/search?lat=0&lng=0")
        assert resp.status_code == 200
        section = extract_top_section(resp.text)
        assert "Far A" not in section
        assert "Far B" not in section
        assert "Non ci sono bar nelle tue vicinanze." in section


def test_top_rated_section_without_location():
    reset_db()
    db = SessionLocal()
    bars = [
        Bar(name="Rated A", slug="rated-a", rating=5.0),
        Bar(name="Rated B", slug="rated-b", rating=4.5),
        Bar(name="Unrated", slug="unrated"),
    ]
    db.add_all(bars)
    db.commit()
    for b in bars:
        db.refresh(b)
    db.close()

    with TestClient(app) as client:
        resp = client.get("/search")
        assert resp.status_code == 200
        section = extract_top_section(resp.text)
        expected = ["Rated A", "Rated B", "Unrated"]
        for name in expected:
            assert name in section
        positions = [section.index(name) for name in expected]
        assert positions == sorted(positions)

