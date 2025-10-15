import os
import sys
import pathlib
import ipaddress

from fastapi.testclient import TestClient
from starlette.requests import Request

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from database import Base, engine  # noqa: E402
from main import app, TRUSTED_HOSTS, get_request_ip  # noqa: E402


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _build_request(headers=None, client=("203.0.113.50", 12345)):
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": headers or [],
        "client": client,
        "server": ("testserver", 80),
    }
    return Request(scope)


def test_invalid_host_header_is_rejected(monkeypatch):
    reset_db()
    # Ensure we start from the default allow-list.
    monkeypatch.setattr("main.TRUSTED_HOSTS", set(TRUSTED_HOSTS))

    with TestClient(app) as client:
        ok = client.get("/login")
        assert ok.status_code == 200

        response = client.get("/login", headers={"host": "attacker.example"})
        assert response.status_code == 400
        assert response.text == "Invalid Host header"


def test_x_forwarded_for_ignored_without_trusted_proxy(monkeypatch):
    monkeypatch.setattr("main.TRUSTED_PROXY_NETWORKS", tuple())
    request = _build_request(headers=[(b"x-forwarded-for", b"198.51.100.10")])
    ip = get_request_ip(request)
    assert ip == "203.0.113.50"


def test_x_forwarded_for_accepted_from_trusted_proxy(monkeypatch):
    network = ipaddress.ip_network("10.0.0.0/24")
    monkeypatch.setattr("main.TRUSTED_PROXY_NETWORKS", (network,))
    request = _build_request(
        headers=[(b"x-forwarded-for", b"198.51.100.10")],
        client=("10.0.0.5", 43210),
    )
    ip = get_request_ip(request)
    assert ip == "198.51.100.10"
