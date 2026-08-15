from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

DESKTOP_BILLING_HANDOFF_PROVIDER = "desktop_billing_handoff"
DESKTOP_BILLING_HANDOFF_TTL_SECONDS = 120
_SEALED_SESSION_PREFIX = "desktop-billing:v1:"


def seal_desktop_billing_session(session_token: str, *, key: bytes) -> str:
    """Keep the bearer out of the URL while allowing a one-time browser exchange."""
    return _SEALED_SESSION_PREFIX + Fernet(key).encrypt(session_token.encode("utf-8")).decode("ascii")


def open_desktop_billing_session(value: str, *, key: bytes) -> str | None:
    if not value.startswith(_SEALED_SESSION_PREFIX):
        return None
    try:
        raw = Fernet(key).decrypt(value[len(_SEALED_SESSION_PREFIX) :].encode("ascii"))
    except (InvalidToken, ValueError, UnicodeError):
        return None
    token = raw.decode("utf-8").strip()
    return token or None
