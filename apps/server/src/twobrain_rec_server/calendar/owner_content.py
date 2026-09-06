"""Lossless calendar content for reads already scoped to the calendar owner.

Decrypted data lives only on an unmapped attribute; reading must never write it
back into ORM text columns. This module does not grant access: callers first
apply tenant, owner, selected-calendar and connected-source constraints.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from twobrain_rec_server.calendar.credentials import seal_credential, unseal_credential

OWNER_CONTENT_ENVELOPE_KEY = "sealed_owner_content"
OWNER_CONTENT_VERSION = 1
_OWNER_ATTRIBUTE = "_owner_calendar_content"
# Protect entire text, preserving its original form inside the envelope.
_PROTECTED_TEXT = re.compile(
    r"(?:[a-z][a-z0-9+.-]*://|\bwww\.|\b(?:pass(?:word|[\s_-]?code)?|pwd|pin|access[\s_-]+code|пароль|код)\b)",
    re.IGNORECASE,
)


def plaintext_owner_text(value: str | None) -> str | None:
    return None if value is not None and _PROTECTED_TEXT.search(value) else value


def seal_owner_event_content(event: Any, key: bytes) -> str:
    content = {
        "title": event.title,
        "description": event.description,
        "location": event.location,
        "participants": event.participants,
        "attachments": event.attachments_metadata,
        "provider_extras": event.provider_extras,
        "conference_links": event.conference_links,
    }
    return seal_credential(json.dumps(content, ensure_ascii=False), key).decode("ascii")


def owner_content_key_from_settings(settings: object | None) -> bytes | None:
    path = getattr(settings, "credential_encryption_key_file", None)
    if path is None:
        return None
    try:
        key = path.read_text(encoding="utf-8").strip().encode("ascii")
        Fernet(key)
        return key
    except (OSError, ValueError, UnicodeError):
        return None


def owner_event_content(event: Any, key: bytes | None = None) -> dict[str, Any]:
    if key is None:
        attached = getattr(event, _OWNER_ATTRIBUTE, None)
        if isinstance(attached, dict):
            return attached
    extras = event.provider_extras_json or {}
    sealed = extras.get(OWNER_CONTENT_ENVELOPE_KEY)
    if isinstance(sealed, str) and key is not None:
        try:
            content = json.loads(unseal_credential(sealed.encode("ascii"), key))
            if isinstance(content, dict):
                return content
        except (InvalidToken, ValueError, UnicodeError):
            pass
    return {
        "title": getattr(event, "title", None),
        "description": getattr(event, "description", None),
        "location": getattr(event, "location", None),
        "participants": [],
        "attachments": getattr(event, "attachments_metadata_json", None) or [],
        "provider_extras": {},
        "conference_links": [],
    }


def owner_event_title(event: Any, key: bytes | None = None) -> str | None:
    title = owner_event_content(event, key).get("title")
    return title if isinstance(title, str) and title else None


def attach_owner_content[T: Iterable](events: T, key: bytes | None) -> T:
    for event in events:
        setattr(event, _OWNER_ATTRIBUTE, owner_event_content(event, key))
    return events
