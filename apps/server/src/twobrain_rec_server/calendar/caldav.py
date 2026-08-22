"""Small read-only CalDAV adapter for the existing manual URL contract."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
from datetime import UTC
from hashlib import sha256
from typing import Any, Protocol
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree

from twobrain_rec_server.calendar.credentials import _safe_caldav_url
from twobrain_rec_server.calendar.normalize import normalize_icalendar_event
from twobrain_rec_server.calendar.providers import (
    CalendarCatalogEntry,
    CalendarEventPage,
    CalendarProviderError,
    CalendarValidation,
)

PRESET_CALDAV_URLS = {
    "caldav_yandex": "https://caldav.yandex.ru/",
    "caldav_mail_ru": "https://calendar.mail.ru/",
}
MAX_REDIRECTS = 3


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_request(request: Request, *, timeout: int):
    return build_opener(_NoRedirect).open(request, timeout=timeout)


class CalDAVHttpClient(Protocol):
    async def request(
        self,
        method: str,
        url: str,
        *,
        username: str,
        password: str,
        headers: dict[str, str],
        body: str | None = None,
    ) -> tuple[int, bytes, dict[str, str]]: ...


class UrlLibCalDAVHttpClient:
    async def request(
        self,
        method: str,
        url: str,
        *,
        username: str,
        password: str,
        headers: dict[str, str],
        body: str | None = None,
    ) -> tuple[int, bytes, dict[str, str]]:
        return await asyncio.to_thread(
            self._request_sync,
            method,
            url,
            username=username,
            password=password,
            headers=headers,
            body=body,
        )

    @staticmethod
    def _request_sync(
        method: str,
        url: str,
        *,
        username: str,
        password: str,
        headers: dict[str, str],
        body: str | None,
    ) -> tuple[int, bytes, dict[str, str]]:
        from base64 import b64encode

        origin = _origin(url)
        auth = b64encode(f"{username}:{password}".encode()).decode()
        current_url = url
        for redirect_count in range(MAX_REDIRECTS + 1):
            _require_public_destination(current_url)
            request = Request(
                current_url,
                method=method,
                data=body.encode() if body else None,
                headers={"Authorization": f"Basic {auth}", **headers},
            )
            try:
                with _open_request(request, timeout=15) as response:
                    return (
                        int(response.status),
                        response.read(),
                        {key.lower(): value for key, value in response.headers.items()},
                    )
            except HTTPError as error:
                if error.code in {301, 302, 303, 307, 308}:
                    location = error.headers.get("Location")
                    next_url = urljoin(current_url, location or "")
                    if redirect_count == MAX_REDIRECTS or _origin(next_url) != origin:
                        raise CalendarProviderError("provider_policy_denied") from error
                    current_url = next_url
                    continue
                return (
                    int(error.code),
                    error.read(),
                    {key.lower(): value for key, value in error.headers.items()},
                )
            except TimeoutError as exc:  # pragma: no cover - network boundary
                raise CalendarProviderError("provider_timeout", retryable=True) from exc
            except OSError as exc:  # pragma: no cover - network boundary
                raise CalendarProviderError("provider_unavailable", retryable=True) from exc
        raise CalendarProviderError("provider_policy_denied")  # pragma: no cover


class CalDAVAdapter:
    provider_family: str

    def __init__(
        self,
        provider_family: str,
        *,
        http: CalDAVHttpClient | None = None,
    ) -> None:
        self.provider_family = provider_family
        self.http = http or UrlLibCalDAVHttpClient()

    async def validate(self, credential: str) -> CalendarValidation:
        account, calendars = await self._catalog(credential)
        if not calendars:
            raise CalendarProviderError("calendar_catalog_empty")
        return CalendarValidation(
            account_subject=f"sha256:{sha256(account.encode()).hexdigest()}",
            account_label="CalDAV account",
            calendars=tuple(calendars),
        )

    async def list_calendars(
        self, credential: str, *, page_token: str | None = None
    ) -> tuple[tuple[CalendarCatalogEntry, ...], str | None]:
        _account, calendars = await self._catalog(credential)
        return tuple(calendars), None

    async def list_events(
        self,
        credential: str,
        *,
        calendar_id: str,
        time_min=None,
        time_max=None,
        page_token: str | None = None,
        sync_token: str | None = None,
    ) -> CalendarEventPage:
        config = _credential_config(credential, provider_family=self.provider_family)
        _require_same_origin(config["caldav_url"], calendar_id)
        body = _calendar_query_body(time_min, time_max)
        status, payload, _headers = await self.http.request(
            "REPORT",
            calendar_id,
            username=config["username"],
            password=config["credential_input"],
            headers={
                "Content-Type": "application/xml; charset=utf-8",
                "Depth": "1",
            },
            body=body,
        )
        _require_success(status)
        try:
            responses = _xml_responses(payload)
        except ElementTree.ParseError as exc:
            raise CalendarProviderError("invalid_payload") from exc
        events = []
        for response in responses:
            icalendar_text = response.get("calendar_data")
            if not icalendar_text:
                continue
            events.append(
                normalize_icalendar_event(
                    icalendar_text,
                    provider_family=self.provider_family,
                    provider_calendar_id=calendar_id,
                )
            )
        return CalendarEventPage(events=tuple(events))

    async def _catalog(self, credential: str) -> tuple[str, list[CalendarCatalogEntry]]:
        config = _credential_config(credential, provider_family=self.provider_family)
        status, payload, _headers = await self.http.request(
            "PROPFIND",
            config["caldav_url"],
            username=config["username"],
            password=config["credential_input"],
            headers={
                "Content-Type": "application/xml; charset=utf-8",
                "Depth": "1",
            },
            body=_calendar_propfind_body(),
        )
        _require_success(status)
        try:
            responses = _xml_responses(payload)
        except ElementTree.ParseError as exc:
            raise CalendarProviderError("invalid_payload") from exc
        calendars = []
        for response in responses:
            if not response.get("is_calendar") or not response.get("href"):
                continue
            calendars.append(
                CalendarCatalogEntry(
                    provider_calendar_id=_require_same_origin(
                        config["caldav_url"], str(response["href"])
                    ),
                    display_label=(response.get("display_name") or "CalDAV calendar")[:240],
                    access_role="reader",
                    primary=not calendars,
                )
            )
        account = "|".join(
            (
                self.provider_family,
                _origin(config["caldav_url"]),
                config["username"].casefold(),
            )
        )
        return account, calendars


def _credential_config(value: str, *, provider_family: str | None = None) -> dict[str, str]:
    try:
        config = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise CalendarProviderError("invalid_credentials") from exc
    if not isinstance(config, dict):
        raise CalendarProviderError("invalid_credentials")
    result = {
        key: config.get(key, "")
        for key in ("caldav_url", "username", "credential_input")
    }
    if not result["caldav_url"] and provider_family in PRESET_CALDAV_URLS:
        result["caldav_url"] = PRESET_CALDAV_URLS[provider_family]
    if not all(isinstance(value, str) and value.strip() for value in result.values()):
        raise CalendarProviderError("invalid_credentials")
    if _safe_caldav_url(result["caldav_url"]) is None:
        raise CalendarProviderError("provider_policy_denied")
    return result


def _origin(url: str) -> str:
    safe_url = _safe_caldav_url(url)
    if safe_url is None:
        raise CalendarProviderError("provider_policy_denied")
    parsed = urlparse(safe_url)
    port = parsed.port or 443
    return f"https://{parsed.hostname.rstrip('.').lower()}:{port}"


def _require_same_origin(base_url: str, candidate_url: str) -> str:
    resolved = urljoin(base_url, candidate_url)
    if _origin(resolved) != _origin(base_url):
        raise CalendarProviderError("provider_policy_denied")
    return resolved


def _require_public_destination(url: str) -> None:
    parsed = urlparse(url)
    if _safe_caldav_url(url) is None or not parsed.hostname:
        raise CalendarProviderError("provider_policy_denied")
    try:
        addresses = socket.getaddrinfo(
            parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM
        )
    except OSError as exc:
        raise CalendarProviderError("provider_unavailable", retryable=True) from exc
    if not addresses or any(
        not ipaddress.ip_address(item[4][0]).is_global for item in addresses
    ):
        raise CalendarProviderError("provider_policy_denied")


def _calendar_propfind_body() -> str:
    return (
        '<?xml version="1.0" encoding="utf-8" ?>'
        '<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
        "<d:prop><d:displayname><d:resourcetype><c:calendar/></d:resourcetype>"
        "</d:displayname></d:prop></d:propfind>"
    )


def _calendar_query_body(time_min: Any, time_max: Any) -> str:
    time_range = ""
    if time_min is not None and time_max is not None:
        time_range = (
            f'<c:time-range start="{_ical_datetime(time_min)}" '
            f'end="{_ical_datetime(time_max)}"/>'
        )
    return (
        '<?xml version="1.0" encoding="utf-8" ?>'
        '<c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
        "<d:prop><d:getetag/><c:calendar-data/></d:prop>"
        f"<c:filter><c:comp-filter name=\"VCALENDAR\"><c:comp-filter name=\"VEVENT\">"
        f"{time_range}</c:comp-filter></c:comp-filter></c:filter></c:calendar-query>"
    )


def _ical_datetime(value: Any) -> str:
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _require_success(status: int) -> None:
    if status in {401, 403}:
        raise CalendarProviderError("invalid_credentials" if status == 401 else "provider_policy_denied")
    if status == 429:
        raise CalendarProviderError("rate_limited", retryable=True)
    if status >= 500:
        raise CalendarProviderError("provider_unavailable", retryable=True)
    if status >= 400:
        raise CalendarProviderError("provider_unavailable")
    if status not in {200, 207}:
        raise CalendarProviderError("invalid_payload")


def _xml_responses(payload: bytes) -> list[dict[str, str | bool]]:
    root = ElementTree.fromstring(payload)
    responses: list[dict[str, str | bool]] = []
    for element in root.iter():
        if _local(element.tag) != "response":
            continue
        row: dict[str, str | bool] = {}
        for child in element.iter():
            local = _local(child.tag)
            text = (child.text or "").strip()
            if local == "href" and text and "href" not in row:
                row["href"] = text
            elif local == "displayname" and text:
                row["display_name"] = text
            elif local == "calendar-data" and text:
                row["calendar_data"] = text
            elif local == "calendar":
                row["is_calendar"] = True
        responses.append(row)
    return responses


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
