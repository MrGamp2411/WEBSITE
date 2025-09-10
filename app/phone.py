from __future__ import annotations

import re
from typing import Optional, Set, Tuple

import phonenumbers
from phonenumbers import PhoneNumberType, PhoneNumberFormat
from fastapi import HTTPException


class PhoneValidationError(ValueError):
    """Raised when a phone number fails validation."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def region_from_dial_code(dial_code: str) -> Optional[str]:
    """Return ISO region code for a given dial code like "+41"."""
    try:
        return phonenumbers.region_code_for_country_code(int(dial_code.lstrip("+")))
    except Exception:
        return None


def validate_and_format_phone(
    number_raw: str,
    dial_code: str,
    *,
    allowed_types: Optional[Set[PhoneNumberType]] = None,
) -> Tuple[str, str]:
    """Validate a phone number and return (E.164, region)."""
    if re.search(r"(ext\.?|x)\s*\d+", number_raw, re.IGNORECASE):
        raise PhoneValidationError("Le estensioni non sono supportate.")
    region = region_from_dial_code(dial_code)
    try:
        num = phonenumbers.parse(number_raw, region)
    except phonenumbers.NumberParseException:
        raise PhoneValidationError(
            "Numero di telefono non valido per la nazione selezionata."
        )
    if getattr(num, "extension", None):
        raise PhoneValidationError("Le estensioni non sono supportate.")
    if not phonenumbers.is_possible_number(num):
        raise PhoneValidationError("Lunghezza numero non valida.")
    if not phonenumbers.is_valid_number(num):
        raise PhoneValidationError("Numero di telefono non valido per la nazione selezionata.")
    if num.country_code != int(dial_code.lstrip("+")):
        raise PhoneValidationError(
            f"Il numero non corrisponde al prefisso selezionato ({dial_code})."
        )
    if allowed_types is not None and phonenumbers.number_type(num) not in allowed_types:
        raise PhoneValidationError("Numero di telefono non valido per la nazione selezionata.")
    e164 = phonenumbers.format_number(num, PhoneNumberFormat.E164)
    region_code = phonenumbers.region_code_for_number(num) or ""
    return e164, region_code


ALLOWED_TYPES = {
    PhoneNumberType.MOBILE,
    PhoneNumberType.FIXED_LINE,
    PhoneNumberType.FIXED_LINE_OR_MOBILE,
}


def normalize_phone_or_raise(dial_code: str, phone: str) -> Tuple[str, str]:
    """Normalize a phone number or raise HTTPException 422 with a clean message."""
    try:
        return validate_and_format_phone(phone, dial_code, allowed_types=ALLOWED_TYPES)
    except PhoneValidationError as e:
        raise HTTPException(status_code=422, detail=e.detail)
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Numero di telefono non valido o non coerente con il prefisso selezionato.",
        )
