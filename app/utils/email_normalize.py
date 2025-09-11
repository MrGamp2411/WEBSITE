from typing import Tuple
import idna


def normalize_email(email: str) -> tuple[str, str, str]:
    """Return normalized email, local part, and ASCII domain.

    Strips whitespace, lowercases, and converts internationalized domains
    to ASCII via IDNA. Raises ValueError if the email is invalid.
    """
    e = (email or "").strip().lower()
    if "@" not in e:
        raise ValueError("invalid email")
    local, domain = e.rsplit("@", 1)
    domain_ascii = idna.encode(domain).decode("ascii")
    return f"{local}@{domain_ascii}", local, domain_ascii
