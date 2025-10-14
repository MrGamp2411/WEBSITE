import os
import sys
import pathlib

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from main import should_use_secure_session_cookie  # noqa: E402


def test_session_cookie_secure_true_when_flag_truthy(monkeypatch):
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "TrUe")
    monkeypatch.setenv("BASE_URL", "http://example.test")
    assert should_use_secure_session_cookie() is True


def test_session_cookie_secure_false_when_flag_false(monkeypatch):
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "no")
    monkeypatch.setenv("BASE_URL", "https://example.test")
    assert should_use_secure_session_cookie() is False


def test_session_cookie_secure_defaults_to_https_base(monkeypatch):
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    monkeypatch.setenv("BASE_URL", "  https://secure.example ")
    assert should_use_secure_session_cookie() is True


def test_session_cookie_secure_defaults_to_false(monkeypatch):
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    monkeypatch.delenv("BASE_URL", raising=False)
    assert should_use_secure_session_cookie() is False
