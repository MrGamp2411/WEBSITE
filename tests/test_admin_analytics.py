import os
import sys
import pathlib

# Use shared in-memory SQLite database
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine  # noqa: E402
from main import app  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _login_super_admin(client: TestClient) -> None:
    resp = client.post(
        "/login",
        data={"email": "admin@example.com", "password": "ChangeMe!123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_analytics_page():
    with TestClient(app) as client:
        _login_super_admin(client)
        resp = client.get("/admin/analytics")
        assert resp.status_code == 200
        assert "Orders" in resp.text
        assert "Gross GMV" in resp.text
        assert "Net GMV" in resp.text
        assert "Revenue & Fees" in resp.text
        assert "Products / Menu" in resp.text
        assert "Total refunds" in resp.text
