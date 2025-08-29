import os
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import Bar as BarModel  # noqa: E402
from main import app, bars, load_bars_from_db  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    bars.clear()

def test_bar_detail_has_rating_and_distance_placeholders():
    db = SessionLocal()
    bar = BarModel(
        name="Bar",
        slug="bar",
        rating=4.5,
        latitude=0.0,
        longitude=0.0,
    )
    db.add(bar)
    db.commit()
    db.refresh(bar)
    bar_id = bar.id
    db.close()

    load_bars_from_db()

    client = TestClient(app)
    resp = client.get(f"/bars/{bar_id}")
    assert resp.status_code == 200
    assert 'data-latitude="0.0"' in resp.text
    assert 'data-longitude="0.0"' in resp.text
    assert '<span class="bar-rating"><i class="bi bi-star-fill" aria-hidden="true"></i> 4.5</span>' in resp.text
    assert '<span class="bar-distance" data-has-distance="true" hidden></span>' in resp.text

