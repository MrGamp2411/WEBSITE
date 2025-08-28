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


def extract_nearby_section(html: str) -> str:
    return html.split("Closest to you", 1)[1].split("Top rated", 1)[0]


def test_nearby_bars_sorted_by_distance():
    reset_db()
    db = SessionLocal()
    bars = [
        Bar(name="Far", slug="far", latitude=0.1, longitude=0.0),
        Bar(name="Near", slug="near", latitude=0.01, longitude=0.0),
        Bar(name="NoLoc", slug="noloc"),
    ]
    db.add_all(bars)
    db.commit()
    for b in bars:
        db.refresh(b)
    db.close()

    with TestClient(app) as client:
        resp = client.get("/search?lat=0&lng=0")
        assert resp.status_code == 200
        section = extract_nearby_section(resp.text)
        assert "Near" in section and "Far" in section and "NoLoc" in section
        assert section.index("Near") < section.index("Far") < section.index("NoLoc")
