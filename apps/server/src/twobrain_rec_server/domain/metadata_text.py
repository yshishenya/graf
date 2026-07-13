from __future__ import annotations

import re

UNSAFE_METADATA_TEXT_RE = re.compile(
    r"https?://|www\.|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|"
    r"token=|password|bearer\s|(?:^|[^A-Z0-9])sk-[A-Z0-9_-]{8,}|"
    r"\b(?:[A-Z0-9-]+\.)+[A-Z]{2,}/[^\s<>'\"]+",
    re.IGNORECASE,
)


def contains_forbidden_metadata_text(value: object) -> bool:
    """Return whether untrusted text is unsafe for a metadata-only projection."""

    text = str(value)
    return bool(
        UNSAFE_METADATA_TEXT_RE.search(text)
        or any(ord(character) < 32 or ord(character) == 127 for character in text)
    )


def safe_metadata_text(value: object | None, *, max_length: int) -> str | None:
    """Return bounded metadata-safe text, or fail closed without echoing it."""

    if value is None:
        return None
    text = str(value).strip()
    if not text or contains_forbidden_metadata_text(text):
        return None
    return text[:max_length]
