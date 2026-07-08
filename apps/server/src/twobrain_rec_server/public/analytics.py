from __future__ import annotations

from typing import Any

from twobrain_rec_server.config import Settings

COOKIECONSENT_VERSION = "3.1.0"
PUBLIC_ANALYTICS_PROVIDER = "yandex_metrica"
PUBLIC_ANALYTICS_PRODUCTION_ENVS = {"production", "staging"}
PUBLIC_ANALYTICS_VALIDATION_MODES = {"disabled", "render_only", "provider_smoke"}

PUBLIC_ANALYTICS_SURFACES = {
    "/": "public_landing",
    "/download": "public_download",
}

PUBLIC_ANALYTICS_CONSENT_CATEGORIES = (
    "necessary",
    "analytics",
    "advertising_attribution",
    "behavior_replay",
)

PUBLIC_ANALYTICS_EVENT_CATALOG = (
    {
        "event_name": "public_landing_viewed",
        "surface": "public_landing",
        "target_kind": None,
        "stable_fields": ("page_path", "surface", "campaign_attribution"),
    },
    {
        "event_name": "public_landing_section_seen",
        "surface": "public_landing",
        "target_kind": "section",
        "stable_fields": ("section_id", "page_path", "surface"),
    },
    {
        "event_name": "public_landing_cta_clicked",
        "surface": "public_landing",
        "target_kind": "download_page",
        "stable_fields": ("cta_location", "target_kind", "page_path"),
    },
    {
        "event_name": "public_download_viewed",
        "surface": "public_download",
        "target_kind": None,
        "stable_fields": ("page_path", "surface", "campaign_attribution"),
    },
    {
        "event_name": "public_installer_download_clicked",
        "surface": "public_download",
        "target_kind": "installer_package",
        "stable_fields": ("cta_location", "target_kind"),
    },
    {
        "event_name": "public_login_intent_clicked",
        "surface": "public_landing",
        "target_kind": "login",
        "stable_fields": ("cta_location", "target_kind"),
    },
)


def public_analytics_event_names() -> tuple[str, ...]:
    return tuple(event["event_name"] for event in PUBLIC_ANALYTICS_EVENT_CATALOG)


def build_public_analytics_context(settings: Settings, path: str) -> dict[str, Any]:
    surface = PUBLIC_ANALYTICS_SURFACES.get(path)
    validation_mode = settings.public_analytics_validation_mode
    counter_id = _normalized_counter_id(settings.public_analytics_yandex_metrica_id)
    environment_allowed = settings.env.lower() in PUBLIC_ANALYTICS_PRODUCTION_ENVS or validation_mode in {
        "render_only",
        "provider_smoke",
    }
    enabled = bool(settings.public_analytics_enabled and environment_allowed and counter_id and surface)

    return {
        "enabled": enabled,
        "provider": PUBLIC_ANALYTICS_PROVIDER,
        "validation_mode": validation_mode,
        "environment_allowed": environment_allowed,
        "yandex_metrica_id_present": bool(counter_id),
        "yandex_metrica_id": counter_id if enabled else None,
        "replay_allowed": bool(enabled and settings.public_analytics_replay_enabled),
        "consent_copy_version": settings.public_analytics_consent_copy_version,
        "cookieconsent_version": COOKIECONSENT_VERSION,
        "page_path": path if surface else None,
        "surface": surface,
        "consent_categories": list(PUBLIC_ANALYTICS_CONSENT_CATEGORIES),
        "event_catalog": [dict(event) for event in PUBLIC_ANALYTICS_EVENT_CATALOG],
    }


def _normalized_counter_id(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
