import os
import sys
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine  # noqa: E402
from main import app, seed_super_admin  # noqa: E402


def _login_super_admin(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "admin@example.com", "password": "ChangeMe!123"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_super_admin()


def test_bar_description_limit_api():
    with TestClient(app) as client:
        _login_super_admin(client)

        long_desc = "x" * 121
        data = {"name": "BarA", "slug": "bar-a", "description": long_desc}
        resp = client.post("/api/bars", json=data)
        assert resp.status_code == 422

        ok_desc = "x" * 120
        data["description"] = ok_desc
        resp = client.post("/api/bars", json=data)
        assert resp.status_code == 201
        assert resp.json()["description"] == ok_desc
