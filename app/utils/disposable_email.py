import os
import logging
from datetime import datetime, timezone
from typing import Iterable, List, Set
from urllib.parse import urlparse, urlunparse
from cachetools import TTLCache
import httpx
from importlib import resources
from fastapi import HTTPException

from .email_normalize import normalize_email

_LOG = logging.getLogger(__name__)

ENFORCE = os.getenv("DISPOSABLE_EMAIL_ENFORCE", "true").lower() == "true"
RAW_URLS = [u.strip() for u in os.getenv("DISPOSABLE_DOMAIN_URLS", "").split(",") if u.strip()]
TTL_MIN = int(os.getenv("DISPOSABLE_CACHE_TTL_MIN", "360"))
LOCAL_PATH = os.getenv("DISPOSABLE_LOCAL_PATH", "app/data/disposable_domains.txt")

_cache = TTLCache(maxsize=1, ttl=TTL_MIN * 60)
_meta = {"last_refreshed": None}


def _is_domain_or_subdomain_of(target: str, base: str) -> bool:
    return target == base or target.endswith("." + base)


def _normalize_remote_urls(urls: Iterable[str]) -> List[str]:
    normalized: List[str] = []
    seen = set()
    for raw in urls:
        if not raw:
            continue
        parsed = urlparse(raw)
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"}:
            _LOG.warning("Skipping disposable list URL with unsupported scheme: %s", raw)
            continue
        if not parsed.netloc:
            _LOG.warning("Skipping disposable list URL without host: %s", raw)
            continue
        if scheme == "http":
            parsed = parsed._replace(scheme="https")
            upgraded = urlunparse(parsed)
            _LOG.warning("Upgrading disposable list URL to HTTPS: %s -> %s", raw, upgraded)
        else:
            upgraded = urlunparse(parsed)
        if upgraded in seen:
            continue
        seen.add(upgraded)
        normalized.append(upgraded)
    return normalized


REMOTE_URLS = _normalize_remote_urls(RAW_URLS)


def _load_local() -> Set[str]:
    s: Set[str] = set()
    try:
        with open(LOCAL_PATH, "r", encoding="utf-8") as f:
            for line in f:
                d = line.strip().lower()
                if d and not d.startswith("#"):
                    s.add(d)
    except FileNotFoundError:
        pass
    return s


def _load_remote(urls: Iterable[str]) -> Set[str]:
    s: Set[str] = set()
    for u in urls or []:
        try:
            r = httpx.get(u, timeout=15.0)
            r.raise_for_status()
            for line in r.text.splitlines():
                d = line.strip().lower()
                if d and not d.startswith("#"):
                    s.add(d)
        except Exception as exc:  # pragma: no cover - log but continue
            _LOG.warning("Disposable list fetch failed: %s (%s)", u, exc)
    return s


def _load_from_pypi_pkg() -> Set[str]:
    s: Set[str] = set()
    try:
        with resources.files("disposable_email_domains").joinpath("disposable_email_blocklist.conf").open(
            "r", encoding="utf-8"
        ) as f:
            for line in f:
                d = line.strip().lower()
                if d and not d.startswith("#"):
                    s.add(d)
        return s
    except Exception:  # pragma: no cover
        pass
    try:
        from disposable_email_domains import blocklist

        data = blocklist() if callable(blocklist) else blocklist
        for d in data:
            d = str(d).strip().lower()
            if d:
                s.add(d)
    except Exception:  # pragma: no cover - best effort fallback
        _LOG.warning("PyPI dataset fallback not available")
    return s


def _merge_sets(*sets: Iterable[str]) -> Set[str]:
    merged = set()
    for s in sets:
        merged.update({d for d in s if d})
    return merged


def _build_domains_set(force: bool = False) -> Set[str]:
    if "domains_set" in _cache and not force:
        return _cache["domains_set"]
    remote = _load_remote(REMOTE_URLS)
    local = _load_local()
    pypi = _load_from_pypi_pkg()
    domains = _merge_sets(remote, local, pypi)
    _cache["domains_set"] = domains
    _meta["last_refreshed"] = datetime.now(timezone.utc).isoformat()
    _LOG.info(
        "Disposable domains loaded: %d (remote=%d local=%d pypi=%d)",
        len(domains),
        len(remote),
        len(local),
        len(pypi),
    )
    return domains


def refresh_disposable_cache(force: bool = False) -> int:
    ds = _build_domains_set(force=force)
    try:
        os.makedirs(os.path.dirname("app/data/"), exist_ok=True)
        with open("app/data/disposable_domains.snapshot", "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(ds)))
    except Exception:  # pragma: no cover - snapshot best effort
        pass
    return len(ds)


def get_disposable_stats() -> dict:
    ds = _build_domains_set()
    return {"count": len(ds), "ttl_min": TTL_MIN, "last_refreshed": _meta["last_refreshed"]}


def is_disposable_domain(domain: str) -> bool:
    ds = _build_domains_set()
    return any(_is_domain_or_subdomain_of(domain, b) for b in ds)


def ensure_not_disposable(email: str) -> None:
    email_norm, _local, dom = normalize_email(email)
    if not ENFORCE:
        if is_disposable_domain(dom):
            _LOG.warning("Disposable email detected but not enforced: %s", email_norm)
        return
    if is_disposable_domain(dom):
        _LOG.info("Registration blocked (disposable): domain=%s", dom)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "EMAIL_DISPOSABLE",
                "message": "Disposable email addresses are not allowed. Please use a permanent email.",
            },
        )
