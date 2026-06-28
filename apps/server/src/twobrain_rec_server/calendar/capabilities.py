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
        _capabilities(supports_recurrence="supported", supports_free_busy_only="supported"),
    ),
    CalendarProviderPreset(
        "caldav_mail_ru",
        "Mail.ru Calendar",
        "caldav",
        True,
        _capabilities(supports_recurrence="supported", supports_free_busy_only="supported"),
    ),
    CalendarProviderPreset(
        "exchange_ews",
        "Exchange Server EWS",
        "ews",
        True,
        _capabilities(supports_attendees="supported", supports_recurrence_exceptions="supported"),
    ),
    CalendarProviderPreset(
        "bitrix24",
        "Bitrix24 Calendar",
        "rich_api",
        True,
        _capabilities(supports_attendees="supported", supports_rich_provider_extras="supported"),
    ),
    CalendarProviderPreset(
        "custom_caldav_vk_workspace",
        "VK WorkSpace Calendar",
        "caldav",
        True,
        _capabilities(supports_recurrence="admin_policy_dependent", supports_free_busy_only="supported"),
    ),
    CalendarProviderPreset(
        "caldav_mailion_myoffice",
        "Mailion / MyOffice Calendar",
        "caldav",
        True,
        _capabilities(supports_recurrence="admin_policy_dependent", supports_free_busy_only="supported"),
    ),
    CalendarProviderPreset(
        "caldav_r7_office",
        "R7-Office Calendar",
        "caldav",
        True,
        _capabilities(supports_recurrence="admin_policy_dependent", supports_free_busy_only="supported"),
    ),
    CalendarProviderPreset(
        "caldav_communigate_pro",
        "CommuniGate Pro Calendar",
        "caldav",
        True,
        _capabilities(supports_recurrence="supported", supports_free_busy_only="supported"),
    ),
    CalendarProviderPreset(
        "caldav_rupost",
        "RuPost Calendar",
        "caldav",
        True,
        _capabilities(supports_recurrence="admin_policy_dependent", supports_free_busy_only="supported"),
    ),
    CalendarProviderPreset(
        "caldav_nextcloud_sogo",
        "Nextcloud / SOGo Calendar",
        "caldav",
        True,
        _capabilities(supports_recurrence="supported", supports_recurrence_exceptions="supported"),
    ),
    CalendarProviderPreset(
        "custom_caldav",
        "Custom CalDAV",
        "caldav",
        True,
        _capabilities(supports_recurrence="unknown", supports_free_busy_only="unknown"),
    ),
)


def provider_preset_payloads() -> list[dict[str, object]]:
    return [
        {
            "provider_family": preset.provider_family,
            "label": preset.label,
            "adapter_family": preset.adapter_family,
            "supported": preset.supported,
            "capability_state": preset.capability_state,
        }
        for preset in PROVIDER_PRESETS
    ]
