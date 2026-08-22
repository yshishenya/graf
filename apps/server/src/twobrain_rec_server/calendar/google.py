"""Read-only Google Calendar adapter.

The adapter is deliberately independent of SQLAlchemy.  The service layer
owns sealed credentials and persistence; this module only translates the
documented Google API into the existing normalized calendar contract.
"""

from __future__ import annotations

import asyncio
import json
import time as monotonic_time
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from hashlib import sha256
from typing import Any, Protocol
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from twobrain_rec_server.calendar.conference_links import safe_open_meeting_url
from twobrain_rec_server.calendar.normalize import normalize_calendar_event
from twobrain_rec_server.calendar.providers import (
    MAX_PROVIDER_PAGES,
    CalendarCatalogEntry,
    CalendarEventPage,
    CalendarProviderError,
    CalendarValidation,
)

GOOGLE_PROVIDER_FAMILY = "google_calendar"
GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_CALENDAR_LIST_URL = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
GOOGLE_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars"
GOOGLE_READONLY_SCOPES = (
    "openid",
    "https://www.googleapis.com/auth/calendar.events.readonly",
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
)


@dataclass(frozen=True, slots=True)
class GoogleOAuthConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: tuple[str, ...] = GOOGLE_READONLY_SCOPES


def google_oauth_config_from_settings(settings: Any) -> GoogleOAuthConfig | None:
    """Read the server-owned Google OAuth configuration without exposing secrets."""

    if not getattr(settings, "google_calendar_enabled", False):
        return None
    client_id = _optional_string(getattr(settings, "google_calendar_client_id", None))
    secret_path = getattr(settings, "google_calendar_client_secret_file", None)
    redirect_uri = _optional_string(getattr(settings, "google_calendar_redirect_uri", None))
    if (
        not client_id
        or secret_path is None
        or not redirect_uri
        or not _is_exact_google_redirect_uri(
            redirect_uri,
            production=getattr(settings, "env", "production").lower() == "production",
        )
    ):
        return None
    try:
        client_secret = secret_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not client_secret:
        return None
    return GoogleOAuthConfig(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )


def _is_exact_google_redirect_uri(value: str, *, production: bool) -> bool:
    parsed = urlsplit(value)
    return bool(
        parsed.scheme in ({"https"} if production else {"http", "https"})
        and parsed.netloc
        and not parsed.username
        and not parsed.password
        and not parsed.query
        and not parsed.fragment
        and parsed.path
        in {
            "/settings/integrations/calendar/google/callback",
            "/desktop/settings/integrations/calendar/google/callback",
        }
    )


def google_adapter_from_settings(settings: Any) -> GoogleCalendarAdapter | None:
    config = google_oauth_config_from_settings(settings)
    return GoogleCalendarAdapter(config) if config is not None else None


@dataclass(frozen=True, slots=True)
class GoogleTokenSet:
    access_token: str
    refresh_token: str | None
    expires_in: int | None
    scope: tuple[str, ...]
    token_type: str = "Bearer"


class GoogleHttpClient(Protocol):
    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        form: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, Any], dict[str, str]]: ...


class UrlLibGoogleHttpClient:
    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        form: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, Any], dict[str, str]]:
        return await asyncio.to_thread(
            self._request_sync,
            method,
            url,
            params=params,
            form=form,
            headers=headers,
        )

    @staticmethod
    def _request_sync(
        method: str,
        url: str,
        *,
        params: dict[str, str] | None,
        form: dict[str, str] | None,
        headers: dict[str, str] | None,
    ) -> tuple[int, dict[str, Any], dict[str, str]]:
        target = f"{url}?{urlencode(params)}" if params else url
        body = urlencode(form).encode() if form else None
        request = Request(
            target,
            data=body,
            method=method,
            headers={"Accept": "application/json", **(headers or {})},
        )
        try:
            with urlopen(request, timeout=15) as response:
                raw = response.read()
                status = int(response.status)
                response_headers = {key.lower(): value for key, value in response.headers.items()}
        except HTTPError as error:
            # HTTP errors are provider responses, not transport failures; keep the
            # status so revoked, rate-limited and cursor-invalid mappings survive.
            raw = error.read()
            status = int(error.code)
            response_headers = {key.lower(): value for key, value in error.headers.items()}
        except Exception as exc:  # pragma: no cover - network boundary
            raise CalendarProviderError("provider_timeout", retryable=True) from exc
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CalendarProviderError("invalid_payload") from exc
        if not isinstance(payload, dict):
            raise CalendarProviderError("invalid_payload")
        return status, payload, response_headers


def build_google_authorization_url(config: GoogleOAuthConfig, *, state: str) -> str:
    """Build an exact redirect-bound authorization-code request."""

    if not config.client_id or not config.client_secret or not config.redirect_uri or not state:
        raise CalendarProviderError("provider_policy_denied")
    return f"{GOOGLE_AUTHORIZATION_URL}?{
        urlencode(
            {
                'client_id': config.client_id,
                'redirect_uri': config.redirect_uri,
                'response_type': 'code',
                'access_type': 'offline',
                'prompt': 'consent',
                'scope': ' '.join(config.scopes),
                'state': state,
            }
        )
    }"


class GoogleCalendarAdapter:
    provider_family = GOOGLE_PROVIDER_FAMILY

    def __init__(self, config: GoogleOAuthConfig, *, http: GoogleHttpClient | None = None) -> None:
        self.config = config
        self.http = http or UrlLibGoogleHttpClient()

    async def exchange_code(self, code: str) -> GoogleTokenSet:
        if not code:
            raise CalendarProviderError("provider_policy_denied")
        status, payload, _ = await self.http.request(
            "POST",
            GOOGLE_TOKEN_URL,
            form={
                "code": code,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "redirect_uri": self.config.redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        return self._token_response(status, payload)

    async def refresh_access_token(self, refresh_token: str) -> GoogleTokenSet:
        if not refresh_token:
            raise CalendarProviderError("revoked_access")
        status, payload, _ = await self.http.request(
            "POST",
            GOOGLE_TOKEN_URL,
            form={
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        return self._token_response(status, payload, refresh_token=refresh_token)

    async def account_subject(self, access_token: str) -> str:
        """Return a non-reversible account identity from Google's OIDC subject."""

        status, payload, headers = await self.http.request(
            "GET",
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        self._raise_for_status(status, payload, headers)
        subject = _optional_string(payload.get("sub"))
        if not subject:
            raise CalendarProviderError("invalid_payload")
        return f"sha256:{sha256(f'google:{subject}'.encode()).hexdigest()}"

    async def list_calendars(
        self, access_token: str, *, page_token: str | None = None
    ) -> tuple[tuple[CalendarCatalogEntry, ...], str | None]:
        status, payload, headers = await self.http.request(
            "GET",
            GOOGLE_CALENDAR_LIST_URL,
            params={**({"pageToken": page_token} if page_token else {}), "maxResults": "250"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        self._raise_for_status(status, payload, headers)
        items = payload.get("items")
        if not isinstance(items, list):
            raise CalendarProviderError("invalid_payload")
        calendars = tuple(self._catalog_entry(item) for item in items if isinstance(item, dict))
        return calendars, _optional_string(payload.get("nextPageToken"))

    async def list_events(
        self,
        access_token: str,
        *,
        calendar_id: str,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        page_token: str | None = None,
        sync_token: str | None = None,
    ) -> CalendarEventPage:
        params = {
            "singleEvents": "true",
            "showDeleted": "true",
            "maxResults": "2500",
        }
        if sync_token:
            params["syncToken"] = sync_token
        else:
            if time_min:
                params["timeMin"] = _google_datetime(time_min)
            if time_max:
                params["timeMax"] = _google_datetime(time_max)
        if page_token:
            params["pageToken"] = page_token
        url = f"{GOOGLE_EVENTS_URL}/{_quote_calendar_id(calendar_id)}/events"
        status, payload, headers = await self.http.request(
            "GET", url, params=params, headers={"Authorization": f"Bearer {access_token}"}
        )
        if status == 410:
            raise CalendarProviderError("cursor_invalid")
        self._raise_for_status(status, payload, headers)
        items = payload.get("items")
        if not isinstance(items, list):
            raise CalendarProviderError("invalid_payload")
        events = tuple(
            normalize_calendar_event(_normalize_google_event(item, calendar_id=calendar_id))
            for item in items
            if isinstance(item, dict) and item.get("id")
        )
        return CalendarEventPage(
            events=events,
            next_page_token=_optional_string(payload.get("nextPageToken")),
            next_sync_token=_optional_string(payload.get("nextSyncToken")),
        )

    async def validate(self, access_token: str) -> CalendarValidation:
        calendars, next_page = await self.list_calendars(access_token)
        all_calendars = list(calendars)
        seen_page_tokens: set[str] = set()
        for _ in range(MAX_PROVIDER_PAGES - 1):
            if not next_page:
                break
            if next_page in seen_page_tokens:
                raise CalendarProviderError("invalid_payload")
            seen_page_tokens.add(next_page)
            page, next_page = await self.list_calendars(access_token, page_token=next_page)
            all_calendars.extend(page)
        if next_page:
            raise CalendarProviderError("invalid_payload")
        if not all_calendars:
            raise CalendarProviderError("calendar_catalog_empty")
        return CalendarValidation(
            account_subject=await self.account_subject(access_token),
            account_label="Google Calendar",
            calendars=tuple(all_calendars),
            granted_scopes=self.config.scopes,
        )

    @staticmethod
    def _catalog_entry(item: dict[str, Any]) -> CalendarCatalogEntry:
        calendar_id = _optional_string(item.get("id"))
        label = _optional_string(item.get("summary"))
        if not calendar_id or not label:
            raise CalendarProviderError("invalid_payload")
        access_role = _optional_string(item.get("accessRole")) or "reader"
        return CalendarCatalogEntry(
            provider_calendar_id=calendar_id,
            display_label=label[:240],
            access_role=access_role,
            primary=bool(item.get("primary")),
            visibility="available"
            if access_role in {"reader", "writer", "owner"}
            else "unavailable",
            color=_optional_string(item.get("backgroundColor")),
        )

    @staticmethod
    def _token_response(
        status: int,
        payload: dict[str, Any],
        *,
        refresh_token: str | None = None,
    ) -> GoogleTokenSet:
        if status in {400, 401} and payload.get("error") == "invalid_grant":
            raise CalendarProviderError("revoked_access")
        if status == 429:
            raise CalendarProviderError("rate_limited", retryable=True)
        if status >= 400:
            raise CalendarProviderError("provider_unavailable", retryable=status >= 500)
        access_token = _optional_string(payload.get("access_token"))
        if not access_token:
            raise CalendarProviderError("invalid_payload")
        scope = tuple(
            value for value in (_optional_string(payload.get("scope")) or "").split() if value
        )
        return GoogleTokenSet(
            access_token=access_token,
            refresh_token=_optional_string(payload.get("refresh_token")) or refresh_token,
            expires_in=_optional_int(payload.get("expires_in")),
            scope=scope,
            token_type=_optional_string(payload.get("token_type")) or "Bearer",
        )

    @staticmethod
    def _raise_for_status(status: int, payload: dict[str, Any], headers: dict[str, str]) -> None:
        if status == 401:
            raise CalendarProviderError("revoked_access")
        if status == 429 or (status == 403 and _is_rate_limited_payload(payload)):
            raise CalendarProviderError("rate_limited", retryable=True)
        if status == 403:
            raise CalendarProviderError("provider_policy_denied")
        if status >= 500:
            raise CalendarProviderError("provider_unavailable", retryable=True)
        if status >= 400:
            raise CalendarProviderError("provider_unavailable")


class GoogleCalendarRuntime:
    """Provider facade used by sync; refresh tokens never leave this module."""

    provider_family = GOOGLE_PROVIDER_FAMILY

    def __init__(self, adapter: GoogleCalendarAdapter) -> None:
        self.adapter = adapter
        self._access_token: str | None = None
        self._access_token_expires_at = 0.0
        self._refresh_lock = asyncio.Lock()

    async def _access_token_for(self, refresh_token: str) -> str:
        now = monotonic_time.monotonic()
        if self._access_token and now < self._access_token_expires_at:
            return self._access_token
        async with self._refresh_lock:
            now = monotonic_time.monotonic()
            if self._access_token and now < self._access_token_expires_at:
                return self._access_token
            token = await self.adapter.refresh_access_token(refresh_token)
            self._access_token = token.access_token
            self._access_token_expires_at = now + max((token.expires_in or 0) - 60, 0)
            return token.access_token

    async def validate(self, refresh_token: str) -> CalendarValidation:
        return await self.adapter.validate(await self._access_token_for(refresh_token))

    async def list_calendars(
        self, refresh_token: str, *, page_token: str | None = None
    ) -> tuple[tuple[CalendarCatalogEntry, ...], str | None]:
        return await self.adapter.list_calendars(
            await self._access_token_for(refresh_token), page_token=page_token
        )

    async def list_events(
        self,
        refresh_token: str,
        *,
        calendar_id: str,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        page_token: str | None = None,
        sync_token: str | None = None,
    ) -> CalendarEventPage:
        return await self.adapter.list_events(
            await self._access_token_for(refresh_token),
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
            page_token=page_token,
            sync_token=sync_token,
        )


def _normalize_google_event(item: dict[str, Any], *, calendar_id: str) -> dict[str, Any]:
    status = _optional_string(item.get("status")) or "confirmed"
    original_start, _ = (
        _event_time(item.get("originalStartTime"))
        if item.get("originalStartTime")
        else (None, False)
    )
    start_value = item.get("start") or (
        item.get("originalStartTime") if status == "cancelled" else None
    )
    start, all_day = _event_time(start_value)
    end, _ = _event_time(item.get("end"), default=start)
    privacy = _optional_string(item.get("visibility")) or "public"
    privacy_class = "private" if privacy in {"private", "confidential"} else "public"
    conference_links = (
        _conference_links(item) if privacy_class == "public" and status != "cancelled" else []
    )
    participants = []
    if privacy_class == "public" and status != "cancelled":
        for attendee in item.get("attendees") or []:
            if not isinstance(attendee, dict) or not attendee.get("email"):
                continue
            participants.append(
                {
                    "participant_kind": "organizer"
                    if attendee.get("organizer")
                    else "required_attendee",
                    "response_status": attendee.get("responseStatus", "unknown"),
                    "email": attendee["email"],
                    "display_name": attendee.get("displayName"),
                }
            )
    recurring_id = _optional_string(item.get("recurringEventId"))
    return {
        "provider_family": GOOGLE_PROVIDER_FAMILY,
        "provider_calendar_id": calendar_id,
        "provider_event_id": item.get("id"),
        "ical_uid": _optional_string(item.get("iCalUID")),
        "source_version": _optional_string(item.get("etag"))
        or _optional_string(item.get("updated")),
        "source_status": status,
        "starts_at": start,
        "ends_at": end,
        "timezone": _event_timezone(item.get("start")),
        "all_day": all_day,
        "title": item.get("summary") if privacy_class == "public" else None,
        "description": item.get("description") if privacy_class == "public" else None,
        "location": item.get("location") if privacy_class == "public" else None,
        "privacy_class": privacy_class,
        "participants": participants,
        "conference_links": conference_links,
        "transparency": item.get("transparency"),
        "recurring_series_id": recurring_id,
        "recurrence_instance_id": item.get("id") if recurring_id else None,
        "original_start": original_start,
        "recurrence_rule": {"rules": item.get("recurrence", [])}
        if item.get("recurrence")
        else None,
        "provider_extras": {"google_event_type": item.get("eventType", "default")},
        "source_updated_at": item.get("updated"),
    }


def _conference_links(item: dict[str, Any]) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    raw_links = []
    if item.get("hangoutLink"):
        raw_links.append(("hangoutLink", item["hangoutLink"]))
    for entry in (item.get("conferenceData") or {}).get("entryPoints") or []:
        if isinstance(entry, dict) and entry.get("uri"):
            raw_links.append(("conferenceData", entry["uri"]))
    for source_field, raw_url in raw_links[:10]:
        open_url = safe_open_meeting_url(str(raw_url))
        if open_url is None:
            continue
        links.append(
            {
                "provider_family": "google_meet"
                if "meet.google.com" in str(raw_url)
                else "generic",
                "source_field": source_field,
                "url_hash": f"sha256:{sha256(str(raw_url).encode()).hexdigest()}",
                "contains_passcode": False,
                "sensitivity_class": "meeting_link",
                "open_url": open_url,
            }
        )
    return links


def _event_time(value: Any, *, default: datetime | None = None) -> tuple[datetime, bool]:
    if not isinstance(value, dict):
        if default is not None:
            return default, False
        raise CalendarProviderError("invalid_payload")
    if value.get("date"):
        try:
            return datetime.combine(date.fromisoformat(value["date"]), time.min, tzinfo=UTC), True
        except (TypeError, ValueError) as exc:
            raise CalendarProviderError("invalid_payload") from exc
    raw = value.get("dateTime")
    if not isinstance(raw, str):
        if default is not None:
            return default, False
        raise CalendarProviderError("invalid_payload")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            timezone_name = _optional_string(value.get("timeZone"))
            try:
                parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name or "UTC"))
            except ZoneInfoNotFoundError as exc:
                raise CalendarProviderError("invalid_payload") from exc
        return parsed, False
    except ValueError as exc:
        raise CalendarProviderError("invalid_payload") from exc


def _event_timezone(value: Any) -> str | None:
    return _optional_string(value.get("timeZone")) if isinstance(value, dict) else None


def _google_datetime(value: datetime) -> str:
    value = value.astimezone(UTC)
    return value.isoformat().replace("+00:00", "Z")


def _quote_calendar_id(value: str) -> str:
    from urllib.parse import quote

    return quote(value, safe="")


def _optional_string(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _is_rate_limited_payload(payload: dict[str, Any]) -> bool:
    error = payload.get("error")
    if not isinstance(error, dict):
        return False
    reasons = {
        entry.get("reason")
        for entry in error.get("errors", [])
        if isinstance(entry, dict) and isinstance(entry.get("reason"), str)
    }
    reasons.update(
        value for value in (error.get("status"), error.get("reason")) if isinstance(value, str)
    )
    return bool(
        reasons
        & {
            "rateLimitExceeded",
            "userRateLimitExceeded",
            "quotaExceeded",
            "dailyLimitExceeded",
        }
    )
