import os
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine  # noqa: E402
from main import app  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_bar_description_limit_api():
    client = TestClient(app)
    long_desc = "x" * 121
    data = {"name": "BarA", "slug": "bar-a", "description": long_desc}
    resp = client.post("/api/bars", json=data)
    assert resp.status_code == 422

    ok_desc = "x" * 120
    data["description"] = ok_desc
    resp = client.post("/api/bars", json=data)
    assert resp.status_code == 201
    assert resp.json()["description"] == ok_desc
