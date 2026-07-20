from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.attribution import build_public_bridge_context
from twobrain_rec_server.product_analytics.page_inventory import get_page_class_policy

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

PUBLIC_ANALYTICS_SECTION_IDS = ("hero", "platforms", "outcomes", "trust", "final_cta")
PUBLIC_ANALYTICS_CTA_LOCATIONS = (
    "header_download",
    "hero_download",
    "final_download",
    "hero_login",
    "final_login",
    "download_page_installer",
    "download_page_login",
)
PUBLIC_ANALYTICS_TARGET_KINDS = ("download_page", "installer_package", "login", "section")
PUBLIC_ANALYTICS_CONSENT_STATES = (
    "unknown",
    "accepted_all",
    "necessary_only",
    "customized",
    "revoked",
)
PUBLIC_ANALYTICS_CONSENT_TRANSITIONS = {
    "unknown": ("accepted_all", "necessary_only", "customized"),
    "accepted_all": ("revoked", "necessary_only", "customized"),
    "necessary_only": ("accepted_all", "customized"),
    "customized": ("accepted_all", "necessary_only", "revoked"),
    "revoked": ("accepted_all", "necessary_only", "customized"),
}

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

UTM_FIELDS = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_id",
    "utm_content",
    "utm_term",
)

_SAFE_CAMPAIGN_VALUE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,95}$")
_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{8,}\d)")
_TOKEN_WORDS_RE = re.compile(
    r"(access[_-]?token|refresh[_-]?token|id[_-]?token|api[_-]?key|secret|password|passcode|signed[_-]?url|signature)",
    re.IGNORECASE,
)
_SEARCH_REFERRERS = ("yandex.", "google.", "bing.", "duckduckgo.", "mail.ru")
_PAID_MEDIA = {"cpc", "paid_search", "paid_social", "display", "retargeting"}


def public_analytics_event_names() -> tuple[str, ...]:
    return tuple(event["event_name"] for event in PUBLIC_ANALYTICS_EVENT_CATALOG)


def public_analytics_utm_fields() -> tuple[str, ...]:
    return UTM_FIELDS


def public_analytics_stable_labels() -> dict[str, tuple[str, ...]]:
    return {
        "section_id": PUBLIC_ANALYTICS_SECTION_IDS,
        "cta_location": PUBLIC_ANALYTICS_CTA_LOCATIONS,
        "target_kind": PUBLIC_ANALYTICS_TARGET_KINDS,
    }


def public_analytics_consent_states() -> tuple[str, ...]:
    return PUBLIC_ANALYTICS_CONSENT_STATES


def public_analytics_consent_transitions() -> dict[str, tuple[str, ...]]:
    return PUBLIC_ANALYTICS_CONSENT_TRANSITIONS


def normalize_public_campaign_attribution(
    query_params: Any | None = None,
    *,
    referrer: str | None = None,
    landing_path: str | None = None,
) -> dict[str, str | None]:
    normalized: dict[str, str | None] = {field: None for field in UTM_FIELDS}
    saw_utm = False
    dropped_unsafe = False
    changed = False

    for field in UTM_FIELDS:
        raw = _query_value(query_params, field)
        if raw is None:
            continue
        saw_utm = True
        value = raw.strip()
        if field in {"utm_source", "utm_medium"}:
            lowered = value.lower()
            changed = changed or lowered != value
            value = lowered
        if not _is_safe_campaign_value(value):
            dropped_unsafe = True
            changed = True
            continue
        normalized[field] = value

    if dropped_unsafe:
        status = "unsafe_dropped"
    elif not saw_utm:
        status = "missing"
    elif changed:
        status = "normalized"
    else:
        status = "clean"

    normalized.update(
        {
            "referrer_category": _referrer_category(normalized, referrer),
            "landing_path": landing_path if landing_path in PUBLIC_ANALYTICS_SURFACES else None,
            "normalization_status": status,
        }
    )
    return normalized


def build_public_analytics_context(
    settings: Settings,
    path: str,
    query_params: Any | None = None,
    *,
    referrer: str | None = None,
) -> dict[str, Any]:
    surface = PUBLIC_ANALYTICS_SURFACES.get(path)
    validation_mode = settings.public_analytics_validation_mode
    counter_id = _normalized_counter_id(settings.public_analytics_yandex_metrica_id)
    environment_allowed = settings.env.lower() in PUBLIC_ANALYTICS_PRODUCTION_ENVS or validation_mode in {
        "render_only",
        "provider_smoke",
    }
    enabled = bool(settings.public_analytics_enabled and environment_allowed and counter_id and surface)

    campaign_attribution = normalize_public_campaign_attribution(
        query_params,
        referrer=referrer,
        landing_path=path if surface else None,
    )

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
        "campaign_attribution": campaign_attribution,
        "product_activation_bridge": build_public_bridge_context(campaign_attribution),
        "consent_states": list(public_analytics_consent_states()),
        "consent_transitions": {
            key: list(values) for key, values in public_analytics_consent_transitions().items()
        },
        "stable_labels": {key: list(values) for key, values in public_analytics_stable_labels().items()},
        "consent_categories": list(PUBLIC_ANALYTICS_CONSENT_CATEGORIES),
        "event_catalog": [dict(event) for event in PUBLIC_ANALYTICS_EVENT_CATALOG],
    }


def build_product_yandex_provider_context(settings: Settings, page_class: str) -> dict[str, Any]:
    policy = get_page_class_policy(page_class)
    counter_id = _normalized_counter_id(settings.product_analytics_yandex_counter_id)
    enabled = bool(
        settings.product_analytics_yandex_all_pages_enabled
        and counter_id
        and settings.product_analytics_legal_approved
        and policy.yandex_state == "approved_page_view_event"
    )
    if policy.yandex_state == "approved_page_view_event":
        blocked_reason = None if enabled else "runtime_disabled"
    elif policy.yandex_state == "replay_unavailable":
        blocked_reason = "replay_unavailable"
    else:
        blocked_reason = "inventory_blocked"
    return {
        "enabled": enabled,
        "provider": PUBLIC_ANALYTICS_PROVIDER,
        "page_class": policy.page_class,
        "yandex_state": policy.yandex_state,
        "counter_id_present": bool(counter_id),
        "counter_id": counter_id if enabled else None,
        "inventory_version": settings.product_analytics_yandex_inventory_version,
        "blocked_reason": blocked_reason,
        "webvisor_allowed": False,
        "click_map_allowed": False,
        "scroll_map_allowed": False,
        "form_analytics_allowed": False,
    }


def _normalized_counter_id(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _query_value(query_params: Any | None, field: str) -> str | None:
    if query_params is None:
        return None
    value = None
    getter = getattr(query_params, "get", None)
    if getter is not None:
        value = getter(field)
    elif isinstance(query_params, dict):
        value = query_params.get(field)
    if isinstance(value, list | tuple):
        value = value[0] if value else None
    if value is None:
        return None
    return str(value)


def _is_safe_campaign_value(value: str) -> bool:
    if value == "":
        return False
    if _EMAIL_RE.search(value) or _PHONE_RE.search(value) or _TOKEN_WORDS_RE.search(value):
        return False
    if "://" in value or "/" in value or "\\" in value or "?" in value or "#" in value:
        return False
    return bool(_SAFE_CAMPAIGN_VALUE_RE.fullmatch(value))


def _referrer_category(attribution: dict[str, str | None], referrer: str | None) -> str:
    medium = attribution.get("utm_medium")
    source = attribution.get("utm_source")
    if medium in _PAID_MEDIA:
        return "paid"
    if source:
        return "referral"
    if not referrer:
        return "direct"
    parsed = urlparse(referrer)
    host = parsed.netloc.lower()
    if not host:
        return "unknown"
    if any(marker in host for marker in _SEARCH_REFERRERS):
        return "organic"
    return "referral"
