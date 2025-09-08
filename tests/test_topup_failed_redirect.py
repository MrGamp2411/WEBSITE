import sys
import pathlib
from urllib.parse import urlparse, parse_qs
import os

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402


def test_topup_failed_redirect():
    client = TestClient(app)
    resp = client.get("/wallet/topup/failed?topup=123", follow_redirects=False)
    assert resp.status_code == 303
    loc = resp.headers["location"]
    assert loc.startswith("/wallet?")
    qs = parse_qs(urlparse(loc).query)
    assert qs.get("notice") == ["topup_failed"]
    assert qs.get("noticeTitle") == ["Payment failed"]
