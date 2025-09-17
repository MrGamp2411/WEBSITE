"""Translation completeness and quality checks."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Tuple

TRANSLATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "i18n" / "translations"
EXPECTED_LANG_CODES = {"en", "it", "fr", "de"}


def load_translations() -> Dict[str, dict]:
    translations: Dict[str, dict] = {}
    for path in TRANSLATIONS_DIR.glob("*.json"):
        with path.open(encoding="utf-8") as fh:
            translations[path.stem] = json.load(fh)
    return translations


def iter_leaf_items(data: dict, prefix: str = "") -> Iterable[Tuple[str, str]]:
    """Yield dotted paths and values for all non-dict translation leaves."""
    for key, value in data.items():
        if not prefix and key == "_meta":
            continue

        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            yield from iter_leaf_items(value, path)
        else:
            yield path, value


def test_expected_languages_present() -> None:
    translations = load_translations()
    assert translations, "No translation files found."

    actual_codes = set(translations)
    missing = EXPECTED_LANG_CODES - actual_codes
    unexpected = actual_codes - EXPECTED_LANG_CODES

    assert not missing, f"Missing translation files for: {sorted(missing)}"
    assert not unexpected, f"Unexpected translation files present: {sorted(unexpected)}"


def test_translation_keys_match() -> None:
    translations = load_translations()
    baseline = translations.get("en")
    assert baseline is not None, "English translations must be present as the baseline."

    baseline_keys = {path for path, _ in iter_leaf_items(baseline)}
    assert baseline_keys, "English translation file is empty."

    for code, data in translations.items():
        keys = {path for path, _ in iter_leaf_items(data)}
        missing = baseline_keys - keys
        extra = keys - baseline_keys
        assert not missing, f"{code} is missing keys: {sorted(missing)[:5]}"
        assert not extra, f"{code} has unexpected keys: {sorted(extra)[:5]}"


def test_translation_values_are_non_empty_strings() -> None:
    translations = load_translations()
    for code, data in translations.items():
        for path, value in iter_leaf_items(data):
            assert isinstance(value, str), f"{code}:{path} is not a string (got {type(value).__name__})."
            assert value.strip(), f"{code}:{path} is an empty string."
