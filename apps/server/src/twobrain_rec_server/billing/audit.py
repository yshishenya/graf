"""Metadata-only billing audit projection."""

from __future__ import annotations

import re
from collections.abc import Mapping

_SAFE_KEY = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
_BLOCKED = frozenset(
    {
        "card",
        "email",
        "email_body",
        "meeting",
        "payload",
        "provider_id",
        "secret",
        "token",
    }
)


def metadata_only(values: Mapping[str, object]) -> dict[str, str]:
    """Keep bounded lifecycle facts; drop provider/customer content by default."""
    result: dict[str, str] = {}
    for key, value in values.items():
        normalized = str(key).strip().lower()
        if not _SAFE_KEY.fullmatch(normalized) or any(part in normalized for part in _BLOCKED):
            continue
        if isinstance(value, (str, int, bool)):
            result[normalized] = str(value)[:160]
    return result
