from __future__ import annotations

from twobrain_rec_server.calendar.google import (
    GOOGLE_READONLY_SCOPES,
    GoogleOAuthConfig,
    build_google_authorization_url,
)


def test_google_contract_has_only_approved_read_only_scopes_and_exact_redirect() -> None:
    config = GoogleOAuthConfig(
        client_id="synthetic-client-id",
        client_secret="synthetic-client-secret",
        redirect_uri="https://graf.example.test/settings/integrations/calendar/google/callback",
    )
    url = build_google_authorization_url(config, state="synthetic-state")

    assert config.scopes == GOOGLE_READONLY_SCOPES
    assert "calendar.events.readonly" in url
    assert "calendar.calendarlist.readonly" in url
    assert "calendar.readonly" not in url
    assert "redirect_uri=https%3A%2F%2Fgraf.example.test%2Fsettings%2Fintegrations%2Fcalendar%2Fgoogle%2Fcallback" in url
    assert "access_type=offline" in url
    assert "prompt=consent" in url


def test_google_authorization_contract_never_allows_calendar_write_parameters() -> None:
    config = GoogleOAuthConfig(
        client_id="synthetic-client-id",
        client_secret="synthetic-client-secret",
        redirect_uri="https://graf.example.test/settings/integrations/calendar/google/callback",
    )

    url = build_google_authorization_url(config, state="synthetic-state")

    assert "calendar.events.insert" not in url
    assert "calendar.events" not in url.replace("calendar.events.readonly", "")
    assert "calendar.acl" not in url
