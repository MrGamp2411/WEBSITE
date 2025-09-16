"""Utilities for handling runtime translations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

from starlette.requests import Request

DEFAULT_LANGUAGE = "en"
LANGUAGES: Dict[str, str] = {
    "en": "English",
    "it": "Italiano",
    "fr": "Français",
    "de": "Deutsch",
}
LANGUAGE_SESSION_KEY = "language_code"
TRANSLATIONS_DIR = Path(__file__).resolve().parent / "translations"

_translation_cache: Dict[str, Mapping[str, Any]] = {}


def normalize_language(language: Optional[str]) -> Optional[str]:
    """Normalise a language string to a supported code."""
    if not language:
        return None
    candidate = language.lower().replace("_", "-")
    base_code = candidate.split("-")[0]
    if base_code in LANGUAGES:
        return base_code
    return None


def _parse_accept_language(header_value: str) -> Iterable[str]:
    """Yield language codes from an ``Accept-Language`` header in priority order."""
    for part in header_value.split(","):
        token = part.strip()
        if not token:
            continue
        lang = token.split(";")[0].strip()
        normalized = normalize_language(lang)
        if normalized:
            yield normalized


def load_translations() -> None:
    """Load translation JSON files into memory."""
    TRANSLATIONS_DIR.mkdir(parents=True, exist_ok=True)
    loaded: Dict[str, Mapping[str, Any]] = {}
    for code in LANGUAGES:
        file_path = TRANSLATIONS_DIR / f"{code}.json"
        if not file_path.exists():
            loaded[code] = {}
            continue
        with file_path.open("r", encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:  # pragma: no cover - configuration error
                raise RuntimeError(f"Invalid JSON in translation file: {file_path}") from exc
        if not isinstance(data, Mapping):  # pragma: no cover - configuration error
            raise RuntimeError(
                f"Translation file {file_path} must contain a JSON object as the root node."
            )
        loaded[code] = data
    _translation_cache.clear()
    _translation_cache.update(loaded)


def _resolve_translation(language: str, key: str) -> Optional[str]:
    translations = _translation_cache.get(language)
    if not translations:
        return None
    node: Any = translations
    for part in key.split("."):
        if not isinstance(node, Mapping) or part not in node:
            return None
        node = node[part]
    if isinstance(node, str):
        return node
    return None


def translate(key: str, *, language: Optional[str] = None, default: Optional[str] = None) -> str:
    """Return a translated string for ``key``.

    ``default`` is used when no translation is found; otherwise the key itself is
    returned to make missing strings easy to spot during development.
    """
    if not key:
        return default or ""
    lang = normalize_language(language) or DEFAULT_LANGUAGE
    value = _resolve_translation(lang, key)
    if value is None and lang != DEFAULT_LANGUAGE:
        value = _resolve_translation(DEFAULT_LANGUAGE, key)
    if value is None:
        return default if default is not None else key
    return value


def create_translator(language: Optional[str] = None) -> Callable[[str, Optional[str]], str]:
    """Return a helper that translates keys using ``language``.

    The returned callable accepts ``key`` and an optional ``default`` positional
    argument; keyword arguments are used for ``str.format`` interpolation.
    """
    lang = normalize_language(language) or DEFAULT_LANGUAGE

    def _translator(key: str, default: Optional[str] = None, **fmt: Any) -> str:
        text = translate(key, language=lang, default=default)
        if fmt:
            try:
                text = text.format(**fmt)
            except (IndexError, KeyError, ValueError):  # pragma: no cover - defensive
                pass
        return text

    return _translator


def available_languages() -> List[Dict[str, str]]:
    """Return supported language codes with display names."""
    return [{"code": code, "name": name} for code, name in LANGUAGES.items()]


def get_language_from_request(
    request: Optional[Request], *, persist: bool = True, default: str = DEFAULT_LANGUAGE
) -> str:
    """Determine the best-fit language for ``request``.

    Order of preference: explicit ``lang`` query parameter, stored session value,
    ``Accept-Language`` header, then ``default``. When ``persist`` is ``True`` the
    resolved language is saved to the session for subsequent requests.
    """
    if request is None:
        return default

    chosen: Optional[str] = None

    query_lang = request.query_params.get("lang") if hasattr(request, "query_params") else None
    normalized = normalize_language(query_lang)
    if normalized:
        chosen = normalized
    else:
        session_lang = request.session.get(LANGUAGE_SESSION_KEY) if hasattr(request, "session") else None
        normalized = normalize_language(session_lang)
        if normalized:
            chosen = normalized
        else:
            header_value = request.headers.get("Accept-Language") if hasattr(request, "headers") else None
            if header_value:
                for candidate in _parse_accept_language(header_value):
                    chosen = candidate
                    break

    if not chosen:
        chosen = default

    if persist and hasattr(request, "session"):
        if request.session.get(LANGUAGE_SESSION_KEY) != chosen:
            request.session[LANGUAGE_SESSION_KEY] = chosen

    request.state.language_code = chosen
    return chosen


def translator_for_request(request: Optional[Request], *, persist: bool = True):
    """Return a translator bound to the active language for ``request``."""
    language = get_language_from_request(request, persist=persist)
    translator = create_translator(language)
    if request is not None:
        request.state.translator = translator
    return translator


__all__ = [
    "DEFAULT_LANGUAGE",
    "LANGUAGES",
    "LANGUAGE_SESSION_KEY",
    "available_languages",
    "create_translator",
    "get_language_from_request",
    "load_translations",
    "translate",
    "translator_for_request",
]

# Load translations when the module is imported so tests and scripts that call
# translation helpers outside the FastAPI startup lifecycle have data available.
load_translations()
