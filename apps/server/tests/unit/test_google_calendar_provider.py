from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from twobrain_rec_server.calendar.google import (
    GoogleCalendarAdapter,
    GoogleCalendarRuntime,
    GoogleOAuthConfig,
    UrlLibGoogleHttpClient,
    build_google_authorization_url,
    google_oauth_config_from_settings,
)
from twobrain_rec_server.calendar.providers import CalendarProviderError


class FakeGoogleHttp:
    def __init__(self, responses: list[tuple[int, dict, dict]]) -> None:
        self.responses = list(responses)
        self.requests: list[tuple[str, str, dict | None, dict | None, dict | None]] = []

    async def request(self, method, url, *, params=None, form=None, headers=None):
        self.requests.append((method, url, params, form, headers))
        return self.responses.pop(0)


def _config() -> GoogleOAuthConfig:
    return GoogleOAuthConfig(
        client_id="synthetic-client-id",
        client_secret="synthetic-client-secret",
        redirect_uri="https://graf.example.test/settings/integrations/calendar/google/callback",
    )


class _Settings:
    google_calendar_enabled = True
    google_calendar_client_id = "synthetic-client-id"
    google_calendar_client_secret_file = None
    google_calendar_redirect_uri = None
    env = "production"


def test_google_settings_reject_insecure_or_non_exact_production_redirect() -> None:
    class SecretPath:
        def read_text(self, *, encoding: str) -> str:
            assert encoding == "utf-8"
            return "synthetic-client-secret"

    settings = _Settings()
    settings.google_calendar_client_secret_file = SecretPath()
    for redirect_uri in (
        "http://graf.example.test/settings/integrations/calendar/google/callback",
        "https://graf.example.test/settings/integrations/calendar/google/callback?next=/meetings",
        "https://graf.example.test/oauth/callback",
    ):
        settings.google_calendar_redirect_uri = redirect_uri
        assert google_oauth_config_from_settings(settings) is None

    settings.google_calendar_redirect_uri = (
        "https://graf.example.test/settings/integrations/calendar/google/callback"
    )
    assert google_oauth_config_from_settings(settings) is not None


def test_google_http_client_preserves_provider_http_error_status() -> None:
    error = HTTPError(
        "https://www.googleapis.com/calendar/v3/users/me/calendarList",
        429,
        "synthetic rate limit",
        {"Retry-After": "5"},
        BytesIO(b"{}"),
    )
    with patch("twobrain_rec_server.calendar.google.urlopen", side_effect=error):
        status, payload, headers = UrlLibGoogleHttpClient._request_sync(
            "GET",
            "https://www.googleapis.com/calendar/v3/users/me/calendarList",
            params=None,
            form=None,
            headers=None,
        )

    assert status == 429
    assert payload == {}
    assert headers["retry-after"] == "5"


def test_google_authorization_url_is_read_only_and_redirect_bound() -> None:
    url = build_google_authorization_url(_config(), state="synthetic-state")

    assert "calendar.events.readonly" in url
    assert "calendar.calendarlist.readonly" in url
    assert "scope=openid" in url
    assert (
        "redirect_uri=https%3A%2F%2Fgraf.example.test%2Fsettings%2Fintegrations%2Fcalendar%2Fgoogle%2Fcallback"
        in url
    )
    assert "access_type=offline" in url
    assert "prompt=consent" in url


@pytest.mark.asyncio
async def test_google_catalog_paginates_and_keeps_safe_calendar_metadata() -> None:
    http = FakeGoogleHttp(
        [
            (
                200,
                {
                    "items": [{"id": "primary", "summary": "Synthetic Calendar", "primary": True}],
                    "nextPageToken": "page-2",
                },
                {},
            ),
            (
                200,
                {"items": [{"id": "team", "summary": "Synthetic Team", "accessRole": "reader"}]},
                {},
            ),
            (200, {"sub": "synthetic-google-subject"}, {}),
        ]
    )
    adapter = GoogleCalendarAdapter(_config(), http=http)

    result = await adapter.validate("fixture-access")

    assert [calendar.provider_calendar_id for calendar in result.calendars] == ["primary", "team"]
    assert result.calendars[0].primary is True
    assert (
        result.account_subject == f"sha256:{sha256(b'google:synthetic-google-subject').hexdigest()}"
    )
    assert http.requests[1][2] == {"pageToken": "page-2", "maxResults": "250"}


@pytest.mark.asyncio
async def test_google_catalog_rejects_repeated_page_token() -> None:
    adapter = GoogleCalendarAdapter(
        _config(),
        http=FakeGoogleHttp(
            [
                (200, {"items": [], "nextPageToken": "repeated"}, {}),
                (200, {"items": [], "nextPageToken": "repeated"}, {}),
            ]
        ),
    )

    with pytest.raises(CalendarProviderError) as error:
        await adapter.validate("fixture-access")

    assert error.value.safe_code == "invalid_payload"


def test_google_adapter_exposes_no_provider_side_revoke_operation() -> None:
    adapter = GoogleCalendarAdapter(_config(), http=FakeGoogleHttp([]))

    assert not hasattr(adapter, "revoke")


@pytest.mark.asyncio
async def test_google_events_paginates_incrementally_and_normalizes_meet_without_raw_url() -> None:
    http = FakeGoogleHttp(
        [
            (
                200,
                {
                    "items": [
                        {
                            "id": "event-1",
                            "iCalUID": "event-1@example.test",
                            "etag": "etag-1",
                            "status": "confirmed",
                            "start": {"dateTime": "2026-08-19T09:00:00Z", "timeZone": "UTC"},
                            "end": {"dateTime": "2026-08-19T10:00:00Z", "timeZone": "UTC"},
                            "summary": "Synthetic Event",
                            "visibility": "public",
                            "hangoutLink": "https://meet.google.com/synthetic-room",
                        }
                    ],
                    "nextSyncToken": "cursor-2",
                },
                {},
            )
        ]
    )
    adapter = GoogleCalendarAdapter(_config(), http=http)

    page = await adapter.list_events(
        "fixture-access",
        calendar_id="primary",
        time_min=datetime(2026, 8, 19, tzinfo=UTC),
        time_max=datetime(2026, 8, 20, tzinfo=UTC),
    )

    assert page.next_sync_token == "cursor-2"
    event = page.events[0]
    assert event.starts_at.isoformat() == "2026-08-19T09:00:00+00:00"
    assert event.meeting_link_present is True
    assert event.conference_links[0]["url_hash"].startswith("sha256:")
    assert event.conference_links[0]["open_url"].startswith("https://meet.google.com/")


@pytest.mark.asyncio
async def test_google_event_uses_iana_timezone_when_datetime_has_no_offset() -> None:
    http = FakeGoogleHttp(
        [
            (
                200,
                {
                    "items": [
                        {
                            "id": "timezone-event",
                            "start": {
                                "dateTime": "2026-08-19T12:00:00",
                                "timeZone": "Europe/Moscow",
                            },
                            "end": {
                                "dateTime": "2026-08-19T13:00:00",
                                "timeZone": "Europe/Moscow",
                            },
                        }
                    ]
                },
                {},
            )
        ]
    )

    page = await GoogleCalendarAdapter(_config(), http=http).list_events(
        "fixture-access", calendar_id="primary"
    )

    assert page.events[0].starts_at.isoformat() == "2026-08-19T12:00:00+03:00"
    assert page.events[0].timezone == "Europe/Moscow"


@pytest.mark.asyncio
async def test_google_cancelled_recurring_instance_can_omit_start_and_end() -> None:
    http = FakeGoogleHttp(
        [
            (
                200,
                {
                    "items": [
                        {
                            "id": "cancelled-instance",
                            "iCalUID": "series@example.test",
                            "status": "cancelled",
                            "recurringEventId": "series",
                            "originalStartTime": {
                                "dateTime": "2026-08-19T09:00:00Z",
                                "timeZone": "UTC",
                            },
                        }
                    ]
                },
                {},
            )
        ]
    )

    page = await GoogleCalendarAdapter(_config(), http=http).list_events(
        "fixture-access", calendar_id="primary"
    )

    event = page.events[0]
    assert event.source_status == "cancelled"
    assert event.original_start.isoformat() == "2026-08-19T09:00:00+00:00"
    assert event.recurrence_instance_id == "cancelled-instance"


@pytest.mark.asyncio
async def test_google_cursor_invalidation_is_safe_and_requires_full_resync() -> None:
    http = FakeGoogleHttp([(410, {"error": {"status": "INVALID_ARGUMENT"}}, {})])
    adapter = GoogleCalendarAdapter(_config(), http=http)

    with pytest.raises(CalendarProviderError) as error:
        await adapter.list_events(
            "fixture-access", calendar_id="primary", sync_token="stale-cursor"
        )

    assert error.value.safe_code == "cursor_invalid"


@pytest.mark.asyncio
async def test_google_invalid_grant_requires_reconnect_without_echoing_provider_body() -> None:
    http = FakeGoogleHttp(
        [(400, {"error": "invalid_grant", "error_description": "private detail"}, {})]
    )
    adapter = GoogleCalendarAdapter(_config(), http=http)

    with pytest.raises(CalendarProviderError) as error:
        await adapter.refresh_access_token("fixture-refresh")

    assert error.value.safe_code == "revoked_access"
    assert "private detail" not in str(error.value)


@pytest.mark.asyncio
async def test_google_token_rate_limit_is_retryable_and_safe() -> None:
    adapter = GoogleCalendarAdapter(
        _config(), http=FakeGoogleHttp([(429, {"error": "slow_down"}, {})])
    )

    with pytest.raises(CalendarProviderError) as error:
        await adapter.refresh_access_token("fixture-refresh")

    assert error.value.safe_code == "rate_limited"
    assert error.value.retryable is True


@pytest.mark.asyncio
async def test_google_403_rate_limit_is_retryable_but_policy_403_is_not() -> None:
    rate_limited = GoogleCalendarAdapter(
        _config(),
        http=FakeGoogleHttp(
            [
                (
                    403,
                    {"error": {"errors": [{"reason": "userRateLimitExceeded"}]}},
                    {},
                )
            ]
        ),
    )
    with pytest.raises(CalendarProviderError) as rate_error:
        await rate_limited.list_calendars("fixture-access")
    assert rate_error.value.safe_code == "rate_limited"
    assert rate_error.value.retryable is True

    policy_denied = GoogleCalendarAdapter(
        _config(), http=FakeGoogleHttp([(403, {"error": {"status": "PERMISSION_DENIED"}}, {})])
    )
    with pytest.raises(CalendarProviderError) as policy_error:
        await policy_denied.list_calendars("fixture-access")
    assert policy_error.value.safe_code == "provider_policy_denied"
    assert policy_error.value.retryable is False


@pytest.mark.asyncio
async def test_google_runtime_refreshes_server_owned_token_before_event_read() -> None:
    http = FakeGoogleHttp(
        [
            (200, {"access_token": "fixture-access", "expires_in": 3600}, {}),
            (
                200,
                {
                    "items": [
                        {
                            "id": "runtime-event",
                            "start": {"dateTime": "2026-08-19T09:00:00Z"},
                            "end": {"dateTime": "2026-08-19T10:00:00Z"},
                            "visibility": "public",
                        }
                    ],
                    "nextSyncToken": "fixture-cursor",
                },
                {},
            ),
            (200, {"items": [], "nextSyncToken": "fixture-cursor-2"}, {}),
        ]
    )
    runtime = GoogleCalendarRuntime(GoogleCalendarAdapter(_config(), http=http))

    page = await runtime.list_events("fixture-refresh", calendar_id="primary")
    second_page = await runtime.list_events("fixture-refresh", calendar_id="secondary")

    assert page.next_sync_token == "fixture-cursor"
    assert second_page.next_sync_token == "fixture-cursor-2"
    assert len([request for request in http.requests if request[1].endswith("/token")]) == 1
    assert http.requests[0][1].endswith("/token")
    assert http.requests[1][3] is None
    assert http.requests[1][4] == {"Authorization": "Bearer fixture-access"}
