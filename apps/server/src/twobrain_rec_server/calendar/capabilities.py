from __future__ import annotations

from dataclasses import dataclass

CAPABILITY_KEYS = (
    "supports_attendees",
    "supports_response_status",
    "supports_recurrence",
    "supports_recurrence_exceptions",
    "supports_private_events",
    "supports_conference_metadata",
    "supports_attachments_metadata",
    "supports_delta_sync",
    "supports_updates_deletes",
    "supports_free_busy_only",
    "supports_rich_provider_extras",
)


@dataclass(frozen=True, slots=True)
class CalendarProviderPreset:
    provider_family: str
    label: str
    adapter_family: str
    supported: bool
    capability_state: dict[str, str]


def _capabilities(**overrides: str) -> dict[str, str]:
    values = dict.fromkeys(CAPABILITY_KEYS, "unknown")
    values.update(overrides)
    return values


PROVIDER_PRESETS = (
    CalendarProviderPreset(
        "caldav_yandex",
        "Yandex Calendar",
        "caldav",
        True,
        _capabilities(supports_recurrence="partial", supports_free_busy_only="unknown"),
    ),
    CalendarProviderPreset(
        "caldav_mail_ru",
        "Mail.ru Calendar",
        "caldav",
        True,
        _capabilities(supports_recurrence="partial", supports_free_busy_only="unknown"),
    ),
    CalendarProviderPreset(
        "exchange_ews",
        "Exchange Server EWS",
        "ews",
        False,
        _capabilities(supports_attendees="supported", supports_recurrence_exceptions="supported"),
    ),
    CalendarProviderPreset(
        "bitrix24",
        "Bitrix24 Calendar",
        "rich_api",
        False,
        _capabilities(supports_attendees="supported", supports_rich_provider_extras="supported"),
    ),
    CalendarProviderPreset(
        "custom_caldav_vk_workspace",
        "VK WorkSpace Calendar",
        "caldav",
        True,
        _capabilities(supports_recurrence="partial", supports_free_busy_only="unknown"),
    ),
    CalendarProviderPreset(
        "caldav_mailion_myoffice",
        "Mailion / MyOffice Calendar",
        "caldav",
        True,
        _capabilities(supports_recurrence="partial", supports_free_busy_only="unknown"),
    ),
    CalendarProviderPreset(
        "caldav_r7_office",
        "R7-Office Calendar",
        "caldav",
        True,
        _capabilities(supports_recurrence="partial", supports_free_busy_only="unknown"),
    ),
    CalendarProviderPreset(
        "caldav_communigate_pro",
        "CommuniGate Pro Calendar",
        "caldav",
        True,
        _capabilities(supports_recurrence="partial", supports_free_busy_only="unknown"),
    ),
    CalendarProviderPreset(
        "caldav_rupost",
        "RuPost Calendar",
        "caldav",
        True,
        _capabilities(supports_recurrence="partial", supports_free_busy_only="unknown"),
    ),
    CalendarProviderPreset(
        "caldav_nextcloud_sogo",
        "Nextcloud / SOGo Calendar",
        "caldav",
        True,
        _capabilities(
            supports_recurrence="partial",
            supports_recurrence_exceptions="partial",
            supports_free_busy_only="unknown",
        ),
    ),
    CalendarProviderPreset(
        "custom_caldav",
        "Custom CalDAV",
        "caldav",
        True,
        _capabilities(supports_recurrence="unknown", supports_free_busy_only="unknown"),
    ),
    CalendarProviderPreset(
        "google_calendar",
        "Google Calendar",
        "google_api",
        False,
        _capabilities(
            supports_attendees="supported",
            supports_recurrence="supported",
            supports_recurrence_exceptions="supported",
            supports_private_events="supported",
            supports_conference_metadata="supported",
            supports_delta_sync="supported",
            supports_updates_deletes="supported",
            supports_free_busy_only="supported",
        ),
    ),
)

# Y201 rollout approval: enable only the certified provider family. Other
# providers remain fail-closed until their own certification is complete.
REAL_E2E_CERTIFIED_PROVIDER_FAMILIES: frozenset[str] = frozenset({"caldav_yandex"})


def provider_preset(provider_family: str) -> CalendarProviderPreset | None:
    return next(
        (preset for preset in PROVIDER_PRESETS if preset.provider_family == provider_family),
        None,
    )


def provider_adapter_family(provider_family: str) -> str | None:
    preset = provider_preset(provider_family)
    return preset.adapter_family if preset is not None and preset.supported else None


def provider_preset_payloads(
    *,
    google_available: bool | None = None,
    allow_uncertified_google: bool = False,
    allow_uncertified_yandex: bool = False,
) -> list[dict[str, object]]:
    payloads = []
    for preset in PROVIDER_PRESETS:
        certified = preset.provider_family in REAL_E2E_CERTIFIED_PROVIDER_FAMILIES
        configured = preset.provider_family != "google_calendar" or google_available is True
        development_google = (
            preset.provider_family == "google_calendar" and allow_uncertified_google
        )
        development_yandex = (
            preset.provider_family == "caldav_yandex" and allow_uncertified_yandex
        )
        connectable = configured and (certified or development_google or development_yandex)
        payload = {
            "provider_family": preset.provider_family,
            "label": preset.label,
            "adapter_family": preset.adapter_family,
            "supported": connectable,
            "runtime_available": connectable,
            "capability_state": preset.capability_state,
        }
        payloads.append(payload)
    return payloads
