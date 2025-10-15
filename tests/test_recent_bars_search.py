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


def test_search_recent_section_shows_only_visited():
    db = SessionLocal()
    visited = Bar(name="Visited Bar", slug="visited-bar")
    other = Bar(name="Other Bar", slug="other-bar")
    db.add_all([visited, other])
    db.commit()
    db.refresh(visited)
    db.refresh(other)
    db.close()

    with TestClient(app) as client:
        client.get(f"/bars/{visited.id}")
        client.post(f"/bars/{visited.id}/recently-viewed")
        resp = client.get("/search")
        assert resp.status_code == 200
        assert 'data-section="recent"' in resp.text
        recent_section = resp.text.split("Recently visited bars", 1)[1].split("Closest to you", 1)[0]
        assert "Visited Bar" in recent_section
        assert "Other Bar" not in recent_section

