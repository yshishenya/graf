from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit


def safe_billing_return_path(value: str | None) -> str | None:
    """Keep only fresh billing GET choices; never carry a purchase or authority."""
    if value is not None and re.fullmatch(
        r"/billing/(?:checkout\?cycle=(?:month|year)|storage\?package_count=(?:0|[1-9][0-9]?)|subscription)",
        value,
    ):
        return value
    return None


def safe_first_party_path(value: str | None) -> str | None:
    """Return a browser-safe local path, never a network-path reference."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        decoded = unquote(stripped, errors="strict")
        parsed = urlsplit(decoded)
    except (UnicodeDecodeError, ValueError):
        return None
    if (
        parsed.scheme
        or parsed.netloc
        or not decoded.startswith("/")
        or decoded.startswith("//")
        or "\\" in decoded
        or any(ord(char) < 32 or ord(char) == 127 for char in decoded)
    ):
        return None
    return stripped
