import importlib
import types
import pytest
from fastapi import HTTPException

from app.utils import disposable_email as de


@pytest.fixture(autouse=True)
def clear_cache():
    de._cache.clear()
    yield
    de._cache.clear()


def _mock_loaders(monkeypatch, remote=None, local=None, pypi=None):
    if remote is not None:
        monkeypatch.setattr(de, "_load_remote", lambda urls: set(remote))
    if local is not None:
        monkeypatch.setattr(de, "_load_local", lambda: set(local))
    if pypi is not None:
        monkeypatch.setattr(de, "_load_from_pypi_pkg", lambda: set(pypi))


def test_block_disposable_domains(monkeypatch):
    block = {
        "mailinator.com",
        "10minutemail.com",
        "tempmail.io",
        "guerrillamail.com",
        "yopmail.com",
        "trashmail.com",
    }
    _mock_loaders(monkeypatch, remote=block)
    for domain in block | {"sub.mailinator.com"}:
        with pytest.raises(HTTPException):
            de.ensure_not_disposable(f"user@{domain}")


def test_allow_legit_domains(monkeypatch):
    _mock_loaders(monkeypatch, remote=set())
    good = [
        "libero.it",
        "tiscali.it",
        "gmx.ch",
        "gmx.net",
        "fastwebnet.it",
        "email.it",
        "interia.pl",
        "outlook.com",
        "gmail.com",
        "proton.me",
        "icloud.com",
    ]
    for domain in good:
        de.ensure_not_disposable(f"user@{domain}")


def test_unicode_domain_normalization(monkeypatch):
    # "müller.com" -> "xn--mller-kva.com"
    _mock_loaders(monkeypatch, remote={"xn--mller-kva.com"})
    with pytest.raises(HTTPException):
        de.ensure_not_disposable("user@müller.com")


def test_enforce_false(monkeypatch):
    monkeypatch.setenv("DISPOSABLE_EMAIL_ENFORCE", "false")
    importlib.reload(de)
    _mock_loaders(monkeypatch, remote={"mailinator.com"})
    de.ensure_not_disposable("user@mailinator.com")
    importlib.reload(de)


def test_fallback_priority(monkeypatch):
    _mock_loaders(monkeypatch, remote={"remote.com"}, local={"local.com"}, pypi={"pypi.com"})
    assert de.is_disposable_domain("remote.com")
    _mock_loaders(monkeypatch, remote=set(), local={"local.com"}, pypi={"pypi.com"})
    de._cache.clear()
    assert de.is_disposable_domain("local.com")
    _mock_loaders(monkeypatch, remote=set(), local=set(), pypi={"pypi.com"})
    de._cache.clear()
    assert de.is_disposable_domain("pypi.com")


def test_http_urls_upgraded_and_invalid_skipped(monkeypatch):
    urls = [
        "http://example.com/list.txt",
        "https://valid.com/list.txt",
        "ftp://ignored.com/list.txt",
        "https://valid.com/list.txt",
        "http://",
    ]
    normalized = de._normalize_remote_urls(urls)
    assert normalized == [
        "https://example.com/list.txt",
        "https://valid.com/list.txt",
    ]


def test_remote_urls_reloaded_with_https(monkeypatch):
    monkeypatch.setenv(
        "DISPOSABLE_DOMAIN_URLS",
        "http://blocked.example.com/list.txt,https://ok.example.com/list.txt",
    )
    importlib.reload(de)
    try:
        assert de.REMOTE_URLS == [
            "https://blocked.example.com/list.txt",
            "https://ok.example.com/list.txt",
        ]
    finally:
        monkeypatch.delenv("DISPOSABLE_DOMAIN_URLS", raising=False)
        importlib.reload(de)
