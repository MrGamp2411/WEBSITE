import os
import sys
import pathlib

# Use shared in-memory SQLite database
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import Bar, Table  # noqa: E402
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


def test_add_table():
    db = SessionLocal()
    bar = Bar(name="My Bar", slug="my-bar")
    db.add(bar)
    db.commit()
    db.refresh(bar)
    db.close()

    with TestClient(app) as client:
        _login_super_admin(client)
        form = {"name": "Table 1", "description": "Near window"}
        resp = client.post(f"/admin/bars/{bar.id}/tables/new", data=form, follow_redirects=False)
        assert resp.status_code in (200, 303)
        resp = client.get(f"/admin/bars/{bar.id}/tables")
        assert "Table 1" in resp.text
        assert "Near window" in resp.text

    db = SessionLocal()
    table = db.query(Table).filter_by(bar_id=bar.id, name="Table 1").first()
    assert table is not None and table.description == "Near window"
    db.close()
