"""Small provider boundary for read-only calendar adapters.

Adapters return bounded, provider-neutral data.  They never write calendar
resources and never expose provider response bodies to the cabinet or audit
stream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

SAFE_FAILURE_CODES = frozenset(
    {
        "invalid_credentials",
        "revoked_access",
        "provider_timeout",
        "provider_unavailable",
        "rate_limited",
        "invalid_payload",
        "provider_policy_denied",
        "calendar_catalog_empty",
        "cursor_invalid",
        "credential_encryption_unavailable",
    }
)
MAX_PROVIDER_PAGES = 20


class CalendarProviderError(RuntimeError):
    """Provider failure with a public-safe reason only."""

    def __init__(self, safe_code: str, *, retryable: bool = False) -> None:
        if safe_code not in SAFE_FAILURE_CODES:
            raise ValueError(f"unsupported calendar failure code: {safe_code}")
        super().__init__(safe_code)
        self.safe_code = safe_code
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class CalendarCatalogEntry:
    provider_calendar_id: str
    display_label: str
    access_role: str = "reader"
    primary: bool = False
    selected: bool = False
    visibility: str = "available"
    color: str | None = None
    owner_email_hash: str | None = None


@dataclass(frozen=True, slots=True)
class CalendarEventPage:
    events: tuple[Any, ...] = ()
    next_page_token: str | None = None
    next_sync_token: str | None = None
    full_resync_required: bool = False


@dataclass(frozen=True, slots=True)
class CalendarValidation:
    account_subject: str
    account_label: str
    calendars: tuple[CalendarCatalogEntry, ...] = ()
    granted_scopes: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)


class CalendarProvider(Protocol):
    provider_family: str

    async def validate(self, credential: str) -> CalendarValidation: ...

    async def list_calendars(
        self, credential: str, *, page_token: str | None = None
    ) -> tuple[tuple[CalendarCatalogEntry, ...], str | None]: ...

    async def list_events(
        self,
        credential: str,
        *,
        calendar_id: str,
        time_min: Any | None = None,
        time_max: Any | None = None,
        page_token: str | None = None,
        sync_token: str | None = None,
    ) -> CalendarEventPage: ...


def require_safe_failure_code(code: str) -> str:
    if code not in SAFE_FAILURE_CODES:
        raise ValueError(f"unsafe provider failure code: {code}")
    return code
