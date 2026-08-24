from __future__ import annotations

import json
import socket
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from twobrain_rec_server.calendar.caldav import CalDAVAdapter, UrlLibCalDAVHttpClient
from twobrain_rec_server.calendar.providers import CalendarProviderError

CATALOG_XML = b"""
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:response>
    <d:href>/calendars/synthetic/</d:href>
    <d:propstat><d:prop><d:resourcetype><c:calendar/></d:resourcetype>
    <d:displayname>Synthetic Calendar</d:displayname></d:prop></d:propstat>
  </d:response>
</d:multistatus>
"""
PRINCIPAL_XML = b"""
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:response>
    <d:href>/principals/users/synthetic-owner@example.test/</d:href>
    <d:propstat><d:prop>
      <d:resourcetype><d:collection/></d:resourcetype>
      <c:calendar-home-set><d:href>/calendars/users/synthetic-owner@example.test/</d:href></c:calendar-home-set>
    </d:prop></d:propstat>
  </d:response>
</d:multistatus>
"""
EVENTS_XML = b"""
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:response>
    <d:href>/calendars/synthetic/</d:href>
    <d:propstat><d:prop><c:calendar-data>BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:synthetic-event@example.test
DTSTART:20260819T090000Z
DTEND:20260819T100000Z
SUMMARY:Synthetic Event
END:VEVENT
END:VCALENDAR</c:calendar-data></d:prop></d:propstat>
  </d:response>
</d:multistatus>
"""


class FakeCalDAVHttp:
    def __init__(self, responses: list[tuple[int, bytes, dict[str, str]]]) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, object]] = []

    async def request(self, method, url, *, username, password, headers, body=None):
        self.requests.append(
            {
                "method": method,
                "url": url,
                "username": username,
                "password": password,
                "headers": headers,
                "body": body,
            }
        )
        return self.responses.pop(0)


def _credential() -> str:
    return json.dumps(
        {
            "caldav_url": "https://calendar.example.test/dav/",
            "username": "synthetic-owner@example.test",
            "credential_input": "synthetic-app-password",
        },
        separators=(",", ":"),
    )


@pytest.mark.asyncio
async def test_caldav_catalog_and_events_are_read_only_and_normalized() -> None:
    http = FakeCalDAVHttp([(207, CATALOG_XML, {}), (207, EVENTS_XML, {})])
    adapter = CalDAVAdapter("custom_caldav", http=http)

    validation = await adapter.validate(_credential())
    page = await adapter.list_events(
        _credential(), calendar_id="https://calendar.example.test/calendars/synthetic/"
    )

    assert validation.calendars[0].display_label == "Synthetic Calendar"
    assert page.events[0].title == "Synthetic Event"
    assert http.requests[0]["method"] == "PROPFIND"
    assert http.requests[1]["method"] == "REPORT"
    assert "synthetic-app-password" not in str(http.requests[0]["body"])
    assert "<d:displayname/><d:resourcetype>" in str(http.requests[0]["body"])
    assert "calendar-data" in str(http.requests[1]["body"])


@pytest.mark.asyncio
async def test_caldav_catalog_rejects_cross_origin_calendar_href() -> None:
    payload = CATALOG_XML.replace(
        b"/calendars/synthetic/",
        b"https://attacker.example.test/calendars/synthetic/",
    )
    adapter = CalDAVAdapter("custom_caldav", http=FakeCalDAVHttp([(207, payload, {})]))

    with pytest.raises(CalendarProviderError) as error:
        await adapter.validate(_credential())

    assert error.value.safe_code == "provider_policy_denied"


@pytest.mark.asyncio
async def test_caldav_account_identity_includes_provider_origin() -> None:
    first = await CalDAVAdapter(
        "custom_caldav", http=FakeCalDAVHttp([(207, CATALOG_XML, {})])
    ).validate(_credential())
    second_credential = json.loads(_credential())
    second_credential["caldav_url"] = "https://other-calendar.example.test/dav/"
    second = await CalDAVAdapter(
        "custom_caldav", http=FakeCalDAVHttp([(207, CATALOG_XML, {})])
    ).validate(json.dumps(second_credential))

    assert first.account_subject != second.account_subject


@pytest.mark.asyncio
async def test_caldav_auth_failure_is_safe() -> None:
    http = FakeCalDAVHttp([(401, b"private provider response", {})])
    adapter = CalDAVAdapter("custom_caldav", http=http)

    with pytest.raises(CalendarProviderError) as error:
        await adapter.validate(_credential())

    assert error.value.safe_code == "invalid_credentials"
    assert "private provider response" not in str(error.value)


def test_caldav_http_client_preserves_provider_http_error_status() -> None:
    error = HTTPError(
        "https://calendar.example.test/dav/",
        401,
        "synthetic unauthorized",
        {},
        BytesIO(b"synthetic provider body"),
    )
    with (
        patch("twobrain_rec_server.calendar.caldav._open_request", side_effect=error),
        patch(
            "twobrain_rec_server.calendar.caldav.socket.getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
        ),
    ):
        status, payload, _headers = UrlLibCalDAVHttpClient._request_sync(
            "PROPFIND",
            "https://calendar.example.test/dav/",
            username="synthetic-owner@example.test",
            password="synthetic-app-password",
            headers={},
            body=None,
        )

    assert status == 401
    assert payload == b"synthetic provider body"


def test_caldav_http_client_rejects_private_resolution_before_sending_credentials() -> None:
    with (
        patch(
            "twobrain_rec_server.calendar.caldav.socket.getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
        ),
        patch("twobrain_rec_server.calendar.caldav._open_request") as opened,
        pytest.raises(CalendarProviderError) as error,
    ):
        UrlLibCalDAVHttpClient._request_sync(
            "PROPFIND",
            "https://calendar.example.test/dav/",
            username="synthetic-owner@example.test",
            password="synthetic-app-password",
            headers={},
            body=None,
        )

    assert error.value.safe_code == "provider_policy_denied"
    opened.assert_not_called()


def test_caldav_http_client_rejects_cross_origin_redirect_without_reusing_credentials() -> None:
    redirect = HTTPError(
        "https://calendar.example.test/dav/",
        302,
        "synthetic redirect",
        {"Location": "https://attacker.example.test/dav/"},
        BytesIO(b""),
    )
    with (
        patch(
            "twobrain_rec_server.calendar.caldav.socket.getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
        ),
        patch("twobrain_rec_server.calendar.caldav._open_request", side_effect=redirect) as opened,
        pytest.raises(CalendarProviderError) as error,
    ):
        UrlLibCalDAVHttpClient._request_sync(
            "PROPFIND",
            "https://calendar.example.test/dav/",
            username="synthetic-owner@example.test",
            password="synthetic-app-password",
            headers={},
            body=None,
        )

    assert error.value.safe_code == "provider_policy_denied"
    assert opened.call_count == 1


@pytest.mark.asyncio
async def test_yandex_preset_connection_uses_its_documented_principal_endpoint() -> None:
    http = FakeCalDAVHttp([(207, CATALOG_XML, {})])
    adapter = CalDAVAdapter("caldav_yandex", http=http)

    await adapter.validate(
        json.dumps(
            {
                "username": "synthetic-owner@example.test",
                "credential_input": "synthetic-app-password",
            }
        )
    )

    assert (
        http.requests[0]["url"]
        == "https://caldav.yandex.ru/principals/users/synthetic-owner@example.test/"
    )


@pytest.mark.asyncio
async def test_caldav_discovery_follows_calendar_home_set() -> None:
    http = FakeCalDAVHttp([(207, PRINCIPAL_XML, {}), (207, CATALOG_XML, {})])
    adapter = CalDAVAdapter("caldav_yandex", http=http)

    validation = await adapter.validate(
        json.dumps(
            {
                "username": "synthetic-owner@example.test",
                "credential_input": "synthetic-app-password",
            }
        )
    )

    assert validation.calendars[0].display_label == "Synthetic Calendar"
    assert [request["url"] for request in http.requests] == [
        "https://caldav.yandex.ru/principals/users/synthetic-owner@example.test/",
        "https://caldav.yandex.ru/calendars/users/synthetic-owner@example.test/",
    ]
