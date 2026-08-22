from __future__ import annotations

from twobrain_rec_server.calendar.caldav import CalDAVAdapter
from twobrain_rec_server.calendar.capabilities import provider_preset_payloads
from twobrain_rec_server.calendar.worker import provider_for_source
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import CalendarSource


def _source(provider_family: str) -> CalendarSource:
    return CalendarSource(
        provider_family=provider_family,
        auth_mode="app_password",
        workspace_id=None,
        owner_user_id=None,
    )


def test_calendar_worker_reuses_caldav_provider_boundary() -> None:
    provider = provider_for_source(_source("caldav_yandex"), Settings())

    assert isinstance(provider, CalDAVAdapter)


def test_calendar_worker_reuses_caldav_provider_boundary_for_vk_workspace_alias() -> None:
    provider = provider_for_source(_source("custom_caldav_vk_workspace"), Settings())

    assert isinstance(provider, CalDAVAdapter)


def test_calendar_worker_fails_closed_for_unavailable_provider() -> None:
    provider = provider_for_source(_source("unsupported"), Settings())

    assert provider is None


def test_calendar_worker_fails_closed_for_listed_but_unimplemented_providers() -> None:
    assert provider_for_source(_source("exchange_ews"), Settings()) is None
    assert provider_for_source(_source("bitrix24"), Settings()) is None


def test_caldav_capabilities_do_not_overclaim_simplified_parser_coverage() -> None:
    for provider in provider_preset_payloads():
        if provider["adapter_family"] != "caldav":
            continue
        capabilities = provider["capability_state"]
        assert capabilities["supports_recurrence"] != "supported"
        assert capabilities["supports_free_busy_only"] != "supported"
