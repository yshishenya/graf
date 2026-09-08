"""User notification preferences and safe in-product action paths."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from twobrain_rec_server.billing.notifications import (
    MANDATORY_NOTIFICATION_KINDS,
    BillingNotification,
)


@dataclass(frozen=True, slots=True)
class NotificationPreferences:
    optional_email_enabled: bool = True
    optional_in_app_enabled: bool = True
    version: int = 0


def channel_enabled(
    kind: BillingNotification,
    *,
    channel: str,
    preferences: NotificationPreferences,
) -> bool:
    """Mandatory legal/financial events cannot be disabled by a user."""
    if channel not in {"email", "in_app"}:
        raise ValueError("notification channel is invalid")
    if kind in MANDATORY_NOTIFICATION_KINDS:
        return True
    return (
        preferences.optional_email_enabled
        if channel == "email"
        else preferences.optional_in_app_enabled
    )


def safe_action_path(value: str | None) -> str | None:
    """Allow only same-origin cabinet paths; reject URLs, fragments and queries."""
    if not isinstance(value, str) or not value.startswith("/") or value.startswith("//"):
        return None
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or "\\" in value:
        return None
    if not re.fullmatch(
        r"/(?:account|settings|billing|meetings)(?:/[A-Za-z0-9_-]+){0,8}",
        parsed.path,
    ):
        return None
    return parsed.path


def merge_preferences(current: NotificationPreferences, form) -> NotificationPreferences:
    """Missing legacy fields preserve consent; new forms submit explicit false values."""
    if form.get('version') is not None and str(current.version) != str(form.get('version')):
        raise ValueError('notification_preferences_conflict')
    values = {}
    for name in ('optional_email_enabled', 'optional_in_app_enabled'):
        value = form.get(name)
        if value is None:
            values[name] = getattr(current, name)
        elif value in ('on', 'true', '1', True):
            values[name] = True
        elif value in ('false', '0', False):
            values[name] = False
        else:
            raise ValueError('notification_preferences_invalid')
    return NotificationPreferences(**values, version=current.version + 1)
