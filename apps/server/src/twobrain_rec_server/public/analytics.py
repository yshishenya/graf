"""Public pages: the consent-based measurement contract of feature 273.

Three levels meet here and stay separate:

* **level 1** — the anonymous aggregate is recorded by
  :func:`record_public_page_visit` on every public route, before any consent is
  known and without any provider call (FR-009, FR-058);
* **level 2** — the campaign labels of a visit live in the session cookie
  described by :data:`PUBLIC_VISIT_ATTRIBUTION_COOKIE` and are read back by
  :func:`read_public_visit_attribution`, which is the entry point used by the
  registration path (FR-014, FR-015, FR-016);
* **level 3** — a consented visitor's ordinary page events are relayed to
  PostHog through the first-party route :data:`PUBLIC_ANALYTICS_CAPTURE_ENDPOINT`
  and :func:`deliver_public_analytics_event`; a refusal, a missing decision or an
  unreadable decision produces no optional event at all (FR-004, FR-006, FR-059).
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.acquisition import (
    DEFAULT_PUBLIC_LANDING_PATH,
    KNOWN_VISIT_ATTRIBUTION_STATUSES,
    MAX_VISIT_ATTRIBUTION_REFS,
    ensure_visit_attribution_reference,
    is_within_attribution_window,
)
from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    INSTALLER_DELIVERY_SURFACE,
    MINIMUM_AGGREGATE_BUCKET_SIZE,
    AnonymousAggregateBucket,
    assert_no_anonymous_aggregate_identifiers,
    build_anonymous_aggregate_bucket_from_attribution,
    device_class_from_user_agent,
    is_disclosed_bucket,
    record_anonymous_aggregate_bucket_safely,
    registration_step_surface,
    sanitize_anonymous_aggregate_label,
    surface_for_public_path,
)
from twobrain_rec_server.product_analytics.attribution import (
    APP_HANDOFF_BRIDGE_PARAM,
    ATTRIBUTION_REF_REQUEST_PARAM,
    attribution_bridge_id_for_request,
    build_public_bridge_context,
    default_attribution_bridge_registry,
)
from twobrain_rec_server.product_analytics.forbidden_fields import (
    assert_no_forbidden_fields,
)
from twobrain_rec_server.product_analytics.page_inventory import get_page_class_policy
from twobrain_rec_server.product_analytics.posthog_client import PostHogClientWrapper
from twobrain_rec_server.product_analytics.provider_delivery_gate import (
    resolve_provider_delivery_gate,
)
from twobrain_rec_server.product_analytics.traffic_class import classify_public_traffic

logger = logging.getLogger(__name__)

COOKIECONSENT_VERSION = "3.1.0"
PUBLIC_ANALYTICS_CONSENT_VERSION = "2026-09-15.1"
PUBLIC_ANALYTICS_CONSENT_STORAGE_KEY = "graf_public_cookie_consent"
PUBLIC_ANALYTICS_PROVIDER = "yandex_metrica"
PUBLIC_ANALYTICS_PRODUCTION_ENVS = {"production", "staging"}
PUBLIC_ANALYTICS_VALIDATION_MODES = {"disabled", "render_only", "provider_smoke"}

# Consent-based measurement covers every public page (FR-027), sign-up and login
# included. The two auth pages carry forms, so they are measured through the
# first-party relay only: the external counter stays off them (see
# ``PUBLIC_ANALYTICS_EXTERNAL_COUNTER_SURFACES``) and the relay carries a closed
# field list, so no value a visitor typed can reach measurement.
PUBLIC_ANALYTICS_SURFACES = {
    "/": "public_landing",
    "/download": "public_download",
    "/sign-up": "public_signup",
    "/login": "public_login",
    "/privacy": "public_privacy",
    "/cookies": "public_cookies",
    "/terms": "public_terms",
    "/offer": "public_offer",
    "/analytics-consent": "public_analytics_consent",
}
PUBLIC_ANALYTICS_REPLAY_SURFACES = ("public_landing", "public_download")
# The published cookies policy names two pages for the external counter, and
# behaviour replay keeps exactly that narrower scope. A surface outside this list
# is measured by consent through the first-party relay, so widening the measured
# page list cannot widen what leaves GRAF for a third party, and a page with a
# credential form never loads an external script.
PUBLIC_ANALYTICS_EXTERNAL_COUNTER_SURFACES = ("public_landing", "public_download")
PUBLIC_ANALYTICS_CONSENT_PATHS = tuple(PUBLIC_ANALYTICS_SURFACES)

PUBLIC_ANALYTICS_CONSENT_CATEGORIES = (
    "necessary",
    "analytics",
    "advertising_attribution",
    "behavior_replay",
)

PUBLIC_ANALYTICS_SECTION_IDS = ("hero", "audience", "workflow", "pricing", "faq", "final_cta")
PUBLIC_ANALYTICS_CTA_LOCATIONS = (
    "header_download",
    "hero_download",
    "pricing_download",
    "final_download",
    "header_login",
    "final_login",
    "download_page_installer",
    "download_page_login",
)
PUBLIC_ANALYTICS_TARGET_KINDS = ("download_page", "installer_package", "login", "section")
PUBLIC_ANALYTICS_PRODUCT_TABS = ("recording", "transcript", "outcomes")
PUBLIC_ANALYTICS_PRICING_CYCLES = ("month", "year")
PUBLIC_ANALYTICS_FAQ_IDS = (
    "google_calendar",
    "recognition",
    "calling_apps",
    "upload",
    "results",
    "platforms",
    "offline",
    "storage",
)
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
        "event_name": "public_signup_viewed",
        "surface": "public_signup",
        "target_kind": None,
        "stable_fields": ("page_path", "surface", "campaign_attribution"),
    },
    {
        "event_name": "public_login_viewed",
        "surface": "public_login",
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
        "surface": None,
        "target_kind": "login",
        "stable_fields": ("cta_location", "target_kind"),
    },
    {
        "event_name": "public_product_tab_selected",
        "surface": "public_landing",
        "target_kind": None,
        "stable_fields": ("product_tab",),
    },
    {
        "event_name": "public_pricing_cycle_selected",
        "surface": "public_landing",
        "target_kind": None,
        "stable_fields": ("pricing_cycle",),
    },
    {
        "event_name": "public_faq_opened",
        "surface": "public_landing",
        "target_kind": None,
        "stable_fields": ("faq_item",),
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

# --- Session storage of the visit attribution (level 2) ---------------------
#
# FR-014: campaign labels must survive navigation inside one visit without
# creating a separate persistent tracking identifier. The storage is therefore a
# *session* cookie (no ``Max-Age``/``Expires``: the browser drops it when the
# visit ends).  The cookie keeps a bounded ring of exact opaque server references
# so authentication can apply the 90-day rule to the visits this session actually
# carried.  It never performs a global latest lookup and it never authorizes raw
# campaign labels supplied by the browser.
PUBLIC_VISIT_ATTRIBUTION_COOKIE = "graf_visit_attribution"
PUBLIC_VISIT_ATTRIBUTION_VERSION = 2
PUBLIC_VISIT_ATTRIBUTION_LEGACY_VERSIONS = (1, 2)
PUBLIC_VISIT_ATTRIBUTION_MAX_REFS = MAX_VISIT_ATTRIBUTION_REFS
PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_id",
    "utm_content",
    "utm_term",
)
# FR-016: the Yandex.Direct click identifier is kept with the visit attribution
# only. It is never part of the level 1 aggregate, whose allowlist has no room
# for it, and it is never sent to an advertising platform without a confirmed
# basis (FR-028).
PUBLIC_VISIT_ATTRIBUTION_YCLID_FIELD = "yclid"
PUBLIC_VISIT_ATTRIBUTION_STATUS_FIELDS = ("referrer_category", "landing_path", "first_seen_at")
# ``attribution_ref`` remains the current-reference compatibility field.  The
# ring is additive so old v1 cookies can still be read and old callers can keep
# reading the current reference without knowing about the bounded history.
PUBLIC_VISIT_ATTRIBUTION_REF_FIELD = "attribution_ref"
PUBLIC_VISIT_ATTRIBUTION_REFS_FIELD = "attribution_refs"
_PUBLIC_VISIT_ATTRIBUTION_REF_RE = re.compile(r"^graf_visit_[0-9a-f]{16,64}$")
PUBLIC_VISIT_ATTRIBUTION_FIELDS = (
    *PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS,
    PUBLIC_VISIT_ATTRIBUTION_YCLID_FIELD,
    *PUBLIC_VISIT_ATTRIBUTION_STATUS_FIELDS,
    PUBLIC_VISIT_ATTRIBUTION_REF_FIELD,
    PUBLIC_VISIT_ATTRIBUTION_REFS_FIELD,
)
PUBLIC_VISIT_ATTRIBUTION_STATUSES = ("missing", "saved", "current", "invalid")
# Statuses that carry campaign labels. The other two mean "campaign unknown",
# which is never the same as a direct entry (FR-018, FR-024, FR-059).
PUBLIC_VISIT_ATTRIBUTION_KNOWN_STATUSES = KNOWN_VISIT_ATTRIBUTION_STATUSES
PUBLIC_VISIT_ATTRIBUTION_MAX_BYTES = 1024
YCLID_QUERY_PARAM = "yclid"

# --- Consent-based delivery to PostHog (level 3) ---------------------------
#
# One first-party same-origin route relays ordinary page events. No external
# script is loaded, no project key reaches the browser and delivery happens only
# for a visitor whose decision allows the analytics category.
PUBLIC_ANALYTICS_CAPTURE_ENDPOINT = "/analytics/public-event"
PUBLIC_ANALYTICS_CONSENT_GRANTED_STATES = ("accepted_all", "customized")
PUBLIC_ANALYTICS_CONSENT_REFUSED_STATES = ("necessary_only", "revoked", "unknown")
PUBLIC_ANALYTICS_VIEW_ID_FIELD = "view_id"
PUBLIC_ANALYTICS_VIEW_ID_MAX_LENGTH = 120
PUBLIC_ANALYTICS_RELAY_STABLE_LABEL_FIELDS = (
    "section_id",
    "cta_location",
    "target_kind",
    "product_tab",
    "pricing_cycle",
    "faq_item",
)
PUBLIC_ANALYTICS_RELAY_ALLOWED_FIELDS = (
    "event_name",
    "page_path",
    "surface",
    PUBLIC_ANALYTICS_VIEW_ID_FIELD,
    "consent_state",
    "consent_categories",
    "campaign_attribution",
    *PUBLIC_ANALYTICS_RELAY_STABLE_LABEL_FIELDS,
)
PUBLIC_ANALYTICS_RELAY_MAX_BYTES = 4096

_SEARCH_REFERRERS = ("yandex.", "google.", "bing.", "duckduckgo.", "mail.ru")
_PAID_MEDIA = {"cpc", "paid_search", "paid_social", "display", "retargeting"}
_YCLID_RE = re.compile(r"^[A-Za-z0-9_-]{8,120}$")
_VIEW_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{7,119}$")


def public_analytics_consent_revision(copy_version: str) -> int:
    """Derive CookieConsent's numeric revision from the displayed copy version."""
    digits = re.sub(r"\D", "", str(copy_version))
    return int(digits) if digits else 0


PUBLIC_ANALYTICS_CONSENT_REVISION = public_analytics_consent_revision(
    PUBLIC_ANALYTICS_CONSENT_VERSION
)


def public_analytics_event_names() -> tuple[str, ...]:
    return tuple(event["event_name"] for event in PUBLIC_ANALYTICS_EVENT_CATALOG)


def public_analytics_utm_fields() -> tuple[str, ...]:
    return UTM_FIELDS


def public_analytics_stable_labels() -> dict[str, tuple[str, ...]]:
    return {
        "section_id": PUBLIC_ANALYTICS_SECTION_IDS,
        "cta_location": PUBLIC_ANALYTICS_CTA_LOCATIONS,
        "target_kind": PUBLIC_ANALYTICS_TARGET_KINDS,
        "product_tab": PUBLIC_ANALYTICS_PRODUCT_TABS,
        "pricing_cycle": PUBLIC_ANALYTICS_PRICING_CYCLES,
        "faq_item": PUBLIC_ANALYTICS_FAQ_IDS,
    }


def public_analytics_consent_states() -> tuple[str, ...]:
    return PUBLIC_ANALYTICS_CONSENT_STATES


def public_analytics_consent_transitions() -> dict[str, tuple[str, ...]]:
    return PUBLIC_ANALYTICS_CONSENT_TRANSITIONS


def normalize_public_analytics_consent(
    consent: Any | None,
    *,
    previous: Mapping[str, Any] | None = None,
    copy_version: str = PUBLIC_ANALYTICS_CONSENT_VERSION,
) -> dict[str, Any]:
    """Normalize a saved browser decision without granting unknown input."""
    unknown = {
        "state": "unknown",
        "categories": [],
        "copy_version": None,
        "analytics_allowed": False,
        "advertising_attribution_allowed": False,
        "behavior_replay_allowed": False,
    }
    if not isinstance(consent, Mapping) or consent.get("copy_version") != copy_version:
        return unknown

    raw_categories = consent.get("categories")
    if not isinstance(raw_categories, list | tuple):
        return unknown
    if any(
        not isinstance(category, str)
        or category not in PUBLIC_ANALYTICS_CONSENT_CATEGORIES
        for category in raw_categories
    ):
        return unknown
    if len(set(raw_categories)) != len(raw_categories) or "necessary" not in raw_categories:
        return unknown

    categories = [
        category
        for category in PUBLIC_ANALYTICS_CONSENT_CATEGORIES
        if category in raw_categories
    ]
    optional_categories = set(PUBLIC_ANALYTICS_CONSENT_CATEGORIES) - {"necessary"}
    granted_optional = optional_categories.intersection(categories)
    if granted_optional == optional_categories:
        state = "accepted_all"
    elif granted_optional:
        state = "customized"
    elif consent.get("state") == "revoked" or _previous_consent_had_optional(previous):
        state = "revoked"
    else:
        state = "necessary_only"
    supplied_state = consent.get("state")
    if supplied_state is not None and supplied_state != state:
        return unknown

    return {
        "state": state,
        "categories": categories,
        "copy_version": copy_version,
        "analytics_allowed": "analytics" in categories,
        "advertising_attribution_allowed": "advertising_attribution" in categories,
        "behavior_replay_allowed": "behavior_replay" in categories,
    }


def _previous_consent_had_optional(previous: Mapping[str, Any] | None) -> bool:
    if not isinstance(previous, Mapping) or previous.get("copy_version") != PUBLIC_ANALYTICS_CONSENT_VERSION:
        return False
    categories = previous.get("categories")
    return isinstance(categories, list | tuple) and any(
        category in categories
        for category in ("analytics", "advertising_attribution", "behavior_replay")
    )


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
    consent_copy_version = settings.public_analytics_consent_copy_version
    environment_allowed = settings.env.lower() in PUBLIC_ANALYTICS_PRODUCTION_ENVS or validation_mode in {
        "render_only",
        "provider_smoke",
    }
    configured = bool(settings.public_analytics_enabled and environment_allowed and counter_id)
    enabled = bool(configured and surface)
    consent_ui_enabled = bool(configured and path in PUBLIC_ANALYTICS_CONSENT_PATHS)
    # Replay stays narrower than measurement: the published cookies policy names
    # ``/`` and ``/download`` only, so a legal or auth page measured by consent
    # must not start recording behaviour.
    replay_allowed = bool(
        settings.public_analytics_replay_enabled
        and enabled
        and surface in PUBLIC_ANALYTICS_REPLAY_SURFACES
    )
    # The external counter is a third-party script. On a page outside the two
    # published counter surfaces — the pages that show a credential form in
    # particular — the visitor's decision authorises the first-party relay only,
    # so no external script is loaded there.
    external_counter_allowed = bool(enabled and surface in PUBLIC_ANALYTICS_EXTERNAL_COUNTER_SURFACES)

    campaign_attribution = normalize_public_campaign_attribution(
        query_params,
        referrer=referrer,
        landing_path=path if surface else None,
    )

    return {
        "enabled": enabled,
        "consent_ui_enabled": consent_ui_enabled,
        "provider": PUBLIC_ANALYTICS_PROVIDER,
        "validation_mode": validation_mode,
        "environment_allowed": environment_allowed,
        "yandex_metrica_id_present": bool(counter_id),
        "yandex_metrica_id": counter_id if enabled else None,
        "replay_allowed": replay_allowed,
        "webvisor_allowed": replay_allowed,
        "click_map_allowed": replay_allowed,
        "scroll_map_allowed": replay_allowed,
        "form_analytics_allowed": False,
        "replay_scope": list(PUBLIC_ANALYTICS_REPLAY_SURFACES),
        "external_counter_allowed": external_counter_allowed,
        "external_counter_scope": list(PUBLIC_ANALYTICS_EXTERNAL_COUNTER_SURFACES),
        "measurement_scope": "all_public_pages_by_consent",
        "posthog_capture_endpoint": PUBLIC_ANALYTICS_CAPTURE_ENDPOINT,
        "visit_attribution_cookie": PUBLIC_VISIT_ATTRIBUTION_COOKIE,
        "consent_copy_version": consent_copy_version,
        "consent_revision": public_analytics_consent_revision(consent_copy_version),
        "consent_storage_key": PUBLIC_ANALYTICS_CONSENT_STORAGE_KEY,
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


def build_product_yandex_provider_context(
    settings: Settings,
    page_class: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    policy = get_page_class_policy(page_class)
    counter_id = _normalized_counter_id(settings.product_analytics_yandex_counter_id)
    provider_gate_allowed = False
    if settings.product_analytics_validation_mode == "live_safe":
        provider_gate_allowed = resolve_provider_delivery_gate(
            settings,
            provider="yandex_all_pages",
            environ=environ,
        ).allowed
    elif settings.product_analytics_validation_mode in {"render_only", "provider_smoke"}:
        # These modes are explicitly non-live: they may render the contract or
        # run a metadata-only smoke, but must never cause the browser to load an
        # external counter or emit a hit.
        provider_gate_allowed = False
    enabled = bool(
        provider_gate_allowed
        and settings.product_analytics_yandex_all_pages_enabled
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
        "provider_gate_allowed": provider_gate_allowed,
        "webvisor_allowed": policy.yandex_webvisor_allowed,
        "click_map_allowed": policy.click_map_allowed,
        "scroll_map_allowed": policy.scroll_map_allowed,
        "form_analytics_allowed": policy.form_analytics_allowed,
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


def _parse_iso_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _visit_timestamp_is_live(value: Any, *, now: datetime | None = None) -> bool:
    parsed = _parse_iso_timestamp(value)
    return parsed is not None and is_within_attribution_window(
        parsed, now=now or datetime.now(UTC)
    )


def _is_safe_campaign_value(value: str) -> bool:
    """Campaign labels arrive from the page address and are untrusted input.

    Length, allowed characters and the rejection of values that look like an
    email address, a phone number, a token or a person's name are decided by
    the single shared sanitizer, so the label handed to the browser, to a
    provider and to the anonymous aggregate is exactly the same string.
    """
    return sanitize_anonymous_aggregate_label(value) is not None


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


# --- Level 2: the campaign labels of one visit ------------------------------


def read_public_visit_attribution(request: Any, *, now: datetime | None = None) -> dict[str, Any]:
    """Return the campaign attribution saved for the current public visit.

    This is the entry point the registration path uses: the labels of the visit
    are read from the request and handed to the client acquisition attribute
    (FR-015, FR-016). It never raises: a missing, unreadable or damaged record
    produces ``attribution_status`` ``"missing"``/``"invalid"`` with empty
    labels, which the caller must treat as "campaign unknown" rather than
    "direct" (FR-018, FR-024, FR-059).

    Storage contract — session cookie, not a tracking identifier (FR-014):

    * cookie name/key: ``graf_visit_attribution``;
    * value: compact JSON object ``{"v": 1, ...}`` with exactly these keys —
      ``utm_source``, ``utm_medium``, ``utm_campaign``, ``utm_id``,
      ``utm_content``, ``utm_term`` (sanitized campaign labels),
      ``yclid`` (Yandex.Direct click identifier, when present),
      ``referrer_category``, ``landing_path``, ``first_seen_at`` (ISO-8601 UTC),
      ``attribution_ref`` (opaque server lookup key for this visit only);
    * the cookie has no ``Max-Age`` and remains session-scoped. The opaque key
      does not identify a person or link separate browser visits;
    * every value is re-validated and re-sanitized on read, because the cookie
      comes back from the browser and is untrusted input.

    Returned mapping: the six ``utm_*`` keys above plus ``yclid``,
    ``referrer_category``, ``landing_path``, ``first_seen_at`` and
    ``attribution_status`` (``missing`` | ``saved`` | ``current`` | ``invalid``).
    Values are ``None`` when absent.

    How the registration path must read the result:

    * ``attribution_status == "invalid"`` or ``"missing"`` with empty labels means
      "campaign unknown" — never "direct" (FR-018, FR-024);
    * ``landing_path`` is a path from the published public page set, or ``None``
      when the campaign was seen outside the public pages. A ``None`` landing path
      must not be replaced with an invented path: the visit attribution contract
      accepts public pages only, so either pass the documented public default of
      the acquisition module or record the campaign as unknown;
    * the labels are already sanitized, and a label that looked like contact data,
      a token or a name was dropped by the sanitizer.
    """
    return _merge_visit_attribution(request, now=now)


def apply_public_visit_attribution_cookie(
    response: Any,
    request: Any,
    *,
    attribution: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> bool:
    """Remember the visit's campaign labels in a session cookie (FR-014).

    Returns whether a cookie was set. A visit without campaign material gets no
    cookie at all, and the cookie is only ever written with the labels described
    in :func:`read_public_visit_attribution`; it carries nothing that could
    identify the visitor or link two visits.
    """
    values = attribution if attribution is not None else read_public_visit_attribution(request, now=now)
    if not _visit_attribution_has_campaign(values):
        return False
    if not _visit_timestamp_is_live(values.get("first_seen_at"), now=now):
        return False
    encoded = _encode_visit_attribution(values)
    if encoded is None or len(encoded) > PUBLIC_VISIT_ATTRIBUTION_MAX_BYTES:
        return False
    response.set_cookie(
        PUBLIC_VISIT_ATTRIBUTION_COOKIE,
        encoded,
        path="/",
        httponly=True,
        samesite="lax",
        secure=_request_is_secure(request),
    )
    return True


# --- Level 1: counting one public page visit -------------------------------


def _request_internal_hosts(request: Any) -> tuple[str, ...]:
    settings = getattr(getattr(request, "app", None), "state", None)
    settings = getattr(settings, "settings", None)
    hosts = getattr(settings, "product_analytics_internal_hosts", ())
    return tuple(hosts) if hosts else ()


def build_public_page_aggregate_bucket(
    request: Any,
    *,
    attribution: Mapping[str, str | None] | None = None,
    now: datetime | None = None,
) -> AnonymousAggregateBucket | None:
    """Build the anonymous bucket of one public page visit, or ``None``.

    Only the dimensions of ``data-model.md`` level 1 are produced: the surface
    and path of the page being viewed, the campaign labels carried by the visit,
    the coarse device class and the traffic class. The landing page is the page
    the visit started from, so a campaign keeps describing the visit while the
    visitor moves between public pages. Nothing here reads the analytics stack,
    the consent decision or a provider setting.
    """
    path = _request_path(request)
    if surface_for_public_path(path) is None:
        return None
    visit = attribution if attribution is not None else read_public_visit_attribution(request, now=now)
    bucket = build_anonymous_aggregate_bucket_from_attribution(
        {
            "utm_source": visit.get("utm_source"),
            "utm_medium": visit.get("utm_medium"),
            "utm_campaign": visit.get("utm_campaign"),
            "utm_content": visit.get("utm_content"),
            "utm_term": visit.get("utm_term"),
            "referrer_category": visit.get("referrer_category"),
        },
        path=path,
        occurred_at=now,
        device_class=device_class_from_user_agent(_request_header(request, "user-agent")),
        traffic_class=classify_public_traffic(
            headers=getattr(request, "headers", None),
            query_params=getattr(request, "query_params", None),
            user_agent=_request_header(request, "user-agent"),
            client_host=_request_client_host(request),
            internal_hosts=_request_internal_hosts(request),
        ),
    )
    landing_path = visit.get("landing_path")
    if landing_path and landing_path != bucket.landing_path and surface_for_public_path(landing_path):
        bucket = replace(bucket, landing_path=landing_path)
        assert_no_anonymous_aggregate_identifiers(bucket.as_dict())
    return bucket


async def record_public_page_visit(
    session: Any,
    request: Any,
    *,
    attribution: Mapping[str, str | None] | None = None,
    now: datetime | None = None,
) -> AnonymousAggregateBucket | None:
    """Count one public page visit without any chance of breaking the page.

    The write is one synchronous ``INSERT ... ON CONFLICT DO UPDATE`` by bucket
    key in the product database: no network call, no queue, no provider, and no
    dependency on whether analytics is configured or reachable (FR-009, FR-058).
    A failed write returns ``None`` and is logged; the visitor still gets the
    page and the loss stays a measurement gap.
    """
    bucket = build_public_page_aggregate_bucket(request, attribution=attribution, now=now)
    if bucket is None:
        return None
    settings = getattr(getattr(request, "app", None), "state", None)
    settings = getattr(settings, "settings", None)
    recorded = await record_anonymous_aggregate_bucket_safely(
        session,
        bucket,
        settings=settings,
    )
    return bucket if recorded is not None else None


# --- Level 1: the steps of web registration (FR-020) ------------------------


def _visit_campaign_dimensions(
    request: Any,
    attribution: Mapping[str, str | None] | None,
    now: datetime | None,
) -> tuple[dict[str, str | None], str]:
    """Return the campaign dimensions of a counted action and its landing page.

    A visit is what creates the campaign record (FR-015); every later action of
    the same visitor — a registration step (FR-020), the delivery of the
    installer (FR-019) — is counted with the same dimensions, so one reading
    answers both "how many" and "from which campaign".

    A record whose status is unknown grants no campaign at all and no referrer
    category: what is not known is never reported as a direct entry (FR-018,
    FR-024). When the record has no public landing page — the action happened
    without a counted public visit — the documented public default of the
    acquisition module is used, because the column cannot be left empty and no
    path may be invented here.
    """
    visit = attribution if attribution is not None else read_public_visit_attribution(request, now=now)
    campaign_seen = (
        visit.get("attribution_status") in PUBLIC_VISIT_ATTRIBUTION_KNOWN_STATUSES
        and _visit_timestamp_is_live(visit.get("first_seen_at"), now=now)
    )
    labels = {
        field: (visit.get(field) if campaign_seen else None)
        for field in PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS
    }
    landing_path = visit.get("landing_path")
    if not isinstance(landing_path, str) or surface_for_public_path(landing_path) is None:
        landing_path = DEFAULT_PUBLIC_LANDING_PATH
    return (
        {
            "utm_source": labels["utm_source"],
            "utm_medium": labels["utm_medium"],
            "utm_campaign": labels["utm_campaign"],
            "utm_content": labels["utm_content"],
            "utm_term": labels["utm_term"],
            "referrer_category": visit.get("referrer_category") if campaign_seen else None,
        },
        landing_path,
    )


def _request_traffic_dimensions(request: Any) -> tuple[str, str]:
    """Return the device class and the traffic class of one request."""
    user_agent = _request_header(request, "user-agent")
    settings = getattr(getattr(request, "app", None), "state", None)
    settings = getattr(settings, "settings", None)
    internal_hosts = getattr(settings, "product_analytics_internal_hosts", ())
    return (
        device_class_from_user_agent(user_agent),
        classify_public_traffic(
            headers=getattr(request, "headers", None),
            query_params=getattr(request, "query_params", None),
            user_agent=user_agent,
            client_host=_request_client_host(request),
            internal_hosts=internal_hosts,
        ),
    )


def build_public_registration_step_bucket(
    request: Any,
    step: str,
    *,
    attribution: Mapping[str, str | None] | None = None,
    now: datetime | None = None,
) -> AnonymousAggregateBucket:
    """Build the anonymous counter of one step of web registration (FR-020).

    A step is counted like a visit — same dimensions, same counter, no
    identifier — and keeps the campaign of the visit, so the funnel reads
    "click → registration → first value" per campaign (SC-005, SC-006). The step
    carries its own surface, so a step can never be read as a page view.
    """
    surface = registration_step_surface(step)
    dimensions, landing_path = _visit_campaign_dimensions(request, attribution, now)
    device_class, traffic_class = _request_traffic_dimensions(request)
    bucket = build_anonymous_aggregate_bucket_from_attribution(
        dimensions,
        path=landing_path,
        occurred_at=now,
        device_class=device_class,
        traffic_class=traffic_class,
    )
    bucket = replace(bucket, surface=surface)
    assert_no_anonymous_aggregate_identifiers(bucket.as_dict())
    return bucket


async def record_public_registration_step(
    session: Any,
    request: Any,
    step: str,
    *,
    attribution: Mapping[str, str | None] | None = None,
    now: datetime | None = None,
) -> AnonymousAggregateBucket | None:
    """Count one step of web registration without any chance of breaking it.

    The step is written by the same synchronous bucket write as a visit, so a
    registration never waits for analytics and a refused write leaves a
    measurement gap instead of a failed registration (FR-058). ``None`` means
    "not counted", and the caller must not retry.
    """
    try:
        bucket = build_public_registration_step_bucket(
            request, step, attribution=attribution, now=now
        )
        settings = getattr(getattr(request, "app", None), "state", None)
        settings = getattr(settings, "settings", None)
        recorded = await record_anonymous_aggregate_bucket_safely(
            session,
            bucket,
            settings=settings,
        )
    except Exception as exc:  # noqa: BLE001 - a registration must succeed
        logger.warning(
            "web registration step was not counted: step=%s error=%s",
            step,
            exc.__class__.__name__,
        )
        return None
    return bucket if recorded is not None else None


# --- Level 1: the delivery of the installer file (FR-019) -------------------


def build_public_installer_delivery_bucket(
    request: Any,
    *,
    attribution: Mapping[str, str | None] | None = None,
    now: datetime | None = None,
) -> AnonymousAggregateBucket:
    """Build the anonymous counter of one delivered installer file (FR-019).

    The button on the download page carries the click; this counter is written
    only when the file itself was handed to the browser, so the two numbers can
    be compared and a broken link shows up as clicks without deliveries. The
    delivery keeps the campaign of the visit, exactly like the page view it
    follows.
    """
    dimensions, landing_path = _visit_campaign_dimensions(request, attribution, now)
    device_class, traffic_class = _request_traffic_dimensions(request)
    bucket = build_anonymous_aggregate_bucket_from_attribution(
        dimensions,
        path=landing_path,
        occurred_at=now,
        device_class=device_class,
        traffic_class=traffic_class,
    )
    bucket = replace(bucket, surface=INSTALLER_DELIVERY_SURFACE)
    assert_no_anonymous_aggregate_identifiers(bucket.as_dict())
    return bucket


async def record_public_installer_delivery(
    session: Any,
    request: Any,
    *,
    attribution: Mapping[str, str | None] | None = None,
    now: datetime | None = None,
) -> AnonymousAggregateBucket | None:
    """Count the installer file that really reached the browser (FR-019, FR-058).

    Called after the file was served successfully, so the counter measures
    delivery and not intent. It never raises: the download is already on its way
    to the visitor, and a refused write stays a measurement gap.
    """
    try:
        bucket = build_public_installer_delivery_bucket(
            request, attribution=attribution, now=now
        )
        settings = getattr(getattr(request, "app", None), "state", None)
        settings = getattr(settings, "settings", None)
        recorded = await record_anonymous_aggregate_bucket_safely(
            session,
            bucket,
            settings=settings,
        )
    except Exception as exc:  # noqa: BLE001 - a delivery must reach the visitor
        logger.warning(
            "installer delivery was not counted: error=%s", exc.__class__.__name__
        )
        return None
    return bucket if recorded is not None else None


# --- Level 3: the share of visitors who granted optional consent -----------

PUBLIC_CONSENT_SHARE_CAVEAT = (
    "Доля посетителей, давших необязательное согласие, приводится рядом с каждым "
    "выводом по каналам: остальные визиты учтены только обезличенным счётом и "
    "меток кампании не несут, поэтому выводы описывают меньшую часть трафика."
)


def build_public_consent_share_report(
    *,
    aggregate_visits: Any,
    consent_visits: Any,
    minimum_bucket_size: int = MINIMUM_AGGREGATE_BUCKET_SIZE,
) -> dict[str, Any]:
    """Return the share of visitors who granted optional consent (FR-012).

    The denominator is the level 1 anonymous aggregate, which counts every
    public visit including the visitors who refused; the numerator is the number
    of consented visits reported by the level 3 measurement. Combining them is
    the only way to state the share: the aggregate itself never reads or writes
    a consent decision, and no identifier is needed to divide two counters.

    The share is published only when it cannot point at a single person: a
    denominator below the minimum bucket size is not disclosed (FR-057), and
    inconsistent counters (more consenting visits than visits) are refused
    instead of being clamped into a comforting number.
    """
    total = _non_negative_int(aggregate_visits)
    consenting = _non_negative_int(consent_visits)
    report: dict[str, Any] = {
        "aggregate_visits": total,
        "consent_visits": consenting,
        "minimum_bucket_size": int(minimum_bucket_size),
        "consent_share": None,
        "consent_share_percent": None,
        "consent_share_label": None,
        "published": False,
        "blocked_reason": None,
        "caveat": PUBLIC_CONSENT_SHARE_CAVEAT,
    }
    if total is None or consenting is None:
        report["blocked_reason"] = "invalid_counts"
        return report
    if not is_disclosed_bucket(total, minimum_bucket_size=int(minimum_bucket_size)):
        report["blocked_reason"] = "below_minimum_bucket_size"
        return report
    if consenting > total:
        report["blocked_reason"] = "counts_inconsistent"
        return report
    share = consenting / total
    report.update(
        {
            "consent_share": share,
            "consent_share_percent": round(share * 100),
            "consent_share_label": f"{round(share * 100)} %",
            "published": True,
        }
    )
    return report


# --- Level 3: the first-party relay of consented public events -------------


class PublicAnalyticsEventRejected(ValueError):
    """The relay refused a browser payload; nothing was sent to a provider."""


class PublicAnalyticsConsentRequired(PublicAnalyticsEventRejected):
    """The visitor's decision does not allow the analytics category (FR-059)."""


def normalize_public_analytics_event(payload: Any) -> dict[str, Any]:
    """Validate one browser event and return the only shape that may be sent.

    The browser gate already refuses to send an optional event after a refusal;
    this function is the server-side half of the same rule, because a gate that
    exists only in the browser can be bypassed. Unknown fields, an event outside
    the public catalog, an event reported from the wrong surface, a label outside
    the stable catalog, a malformed view reference and any value that looks like
    contact data, a token or a local path are refused with
    :class:`PublicAnalyticsEventRejected`; a missing, refused or unreadable
    consent decision is refused with :class:`PublicAnalyticsConsentRequired`.
    """
    if not isinstance(payload, Mapping):
        raise PublicAnalyticsEventRejected("payload_must_be_object")
    unknown_fields = sorted(set(payload) - set(PUBLIC_ANALYTICS_RELAY_ALLOWED_FIELDS))
    if unknown_fields:
        raise PublicAnalyticsEventRejected("unknown_field")

    event_name = payload.get("event_name")
    catalog_entry = next(
        (entry for entry in PUBLIC_ANALYTICS_EVENT_CATALOG if entry["event_name"] == event_name),
        None,
    )
    if catalog_entry is None:
        raise PublicAnalyticsEventRejected("unknown_event")

    consent_state = payload.get("consent_state")
    if consent_state not in PUBLIC_ANALYTICS_CONSENT_GRANTED_STATES:
        raise PublicAnalyticsConsentRequired("consent_not_granted")
    categories = payload.get("consent_categories")
    if not isinstance(categories, list | tuple) or "analytics" not in categories:
        raise PublicAnalyticsConsentRequired("analytics_category_not_granted")
    if any(category not in PUBLIC_ANALYTICS_CONSENT_CATEGORIES for category in categories):
        raise PublicAnalyticsEventRejected("unknown_consent_category")

    page_path = payload.get("page_path")
    surface = PUBLIC_ANALYTICS_SURFACES.get(page_path) if isinstance(page_path, str) else None
    if surface is None:
        raise PublicAnalyticsEventRejected("page_path_rejected")
    declared_surface = payload.get("surface")
    if declared_surface is not None and declared_surface != surface:
        raise PublicAnalyticsEventRejected("surface_mismatch")
    if catalog_entry["surface"] is not None and catalog_entry["surface"] != surface:
        raise PublicAnalyticsEventRejected("event_not_allowed_on_surface")

    view_id = payload.get(PUBLIC_ANALYTICS_VIEW_ID_FIELD)
    if not isinstance(view_id, str) or not _VIEW_ID_RE.fullmatch(view_id):
        raise PublicAnalyticsEventRejected("view_id_rejected")

    labels: dict[str, str] = {}
    stable_labels = public_analytics_stable_labels()
    for field in PUBLIC_ANALYTICS_RELAY_STABLE_LABEL_FIELDS:
        value = payload.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or value not in stable_labels[field]:
            raise PublicAnalyticsEventRejected(f"{field}_rejected")
        labels[field] = value

    properties: dict[str, Any] = {
        "page_path": page_path,
        "surface": surface,
        "consent_state": consent_state,
        **labels,
    }
    campaign = _relay_campaign_attribution(
        payload.get("campaign_attribution"),
        categories=categories,
    )
    if campaign:
        properties["campaign_attribution"] = campaign
    try:
        assert_no_forbidden_fields(properties)
    except ValueError as exc:
        raise PublicAnalyticsEventRejected("forbidden_material") from exc
    properties["consent_categories"] = list(categories)
    return {
        "event_name": str(event_name),
        "page_path": page_path,
        "surface": surface,
        PUBLIC_ANALYTICS_VIEW_ID_FIELD: view_id,
        "consent_state": consent_state,
        "properties": properties,
    }


def deliver_public_analytics_event(settings: Settings, event: Mapping[str, Any]) -> dict[str, Any]:
    """Relay one consented public event to PostHog and never raise.

    Delivery goes through the same first-party ``PostHogClientWrapper`` the
    product uses, so no project key and no provider script ever reach the
    browser. A disabled provider, a dry-run validation mode, a missing key file,
    an unreachable host or a rejected payload is reported in the returned
    metadata and produces no exception: the public page and the anonymous count
    must not depend on the analytics stack (FR-058).
    """
    properties = {
        **dict(event.get("properties") or {}),
        "source_feature": "273-paid-traffic-analytics",
        "delivery_route": "first_party_browser_proxy",
        "measurement_level": "consent",
    }
    try:
        client = PostHogClientWrapper.from_settings(settings)
        result = client.capture_event(
            event_name=str(event["event_name"]),
            distinct_id=str(event[PUBLIC_ANALYTICS_VIEW_ID_FIELD]),
            properties=properties,
        )
    except Exception as exc:  # noqa: BLE001 - provider trouble must not reach the page
        logger.warning(
            "public analytics event was not delivered: event_name=%s error=%s",
            event.get("event_name"),
            exc.__class__.__name__,
        )
        return {
            "provider": "posthog",
            "status": "unavailable",
            "delivered": False,
            "retryable": True,
        }
    return {
        "provider": result.provider,
        "status": result.status,
        "delivered": result.status == "live_safe_sent",
        "retryable": result.retryable,
    }


# --- visit attribution helpers ---------------------------------------------


def _merge_visit_attribution(request: Any, *, now: datetime | None = None) -> dict[str, Any]:
    """Merge current labels while retaining a bounded ring of exact visit refs.

    The campaign of the visit is a unit, not a bag of fields: a new click
    replaces the whole label set of the visit (the last non-direct source wins,
    FR-017), so a campaign can never become a mixture of two different ads. The
    landing page, the visit start and a click identifier that the new request does
    not carry stay with the visit.

    The reference ring is additive to the legacy ``attribution_ref`` field. It is
    ordered newest-first, de-duplicated and truncated before it is returned to the
    cookie. Authentication receives only these exact opaque references and loads
    matching server rows; it never trusts campaign labels from the cookie or does
    a global latest-row lookup.

    A request may also carry only the identifier of the handoff link of the
    download page — the embedded cabinet of the desktop application forwards
    exactly that (FR-022). The bridge is then resolved to the campaign labels
    recorded while the public page was rendered, so a sign-in inside the
    application attaches the same campaign as a sign-in in the browser.
    """
    saved, saved_status = _decoded_visit_attribution(request, now=now)
    saved_refs = _bounded_visit_attribution_refs(saved)
    query_params = getattr(request, "query_params", None)
    current = normalize_public_campaign_attribution(
        query_params,
        referrer=_request_header(request, "referer"),
        landing_path=_request_path(request),
    )
    current_yclid = _safe_yclid(_query_value(query_params, YCLID_QUERY_PARAM))
    current_has_campaign = bool(current_yclid) or any(
        current.get(field) for field in PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS
    )
    if not current_has_campaign:
        # The bridge is the last resort and never overrides a label the request
        # itself carries, exactly as in ``resolve_attribution_handoff``.
        bridge = _bridge_from_request(request, now=now)
        bridge_labels = bridge.campaign_context() if bridge is not None else {}
        if any(bridge_labels.values()):
            current = {**current, **bridge_labels}
            current_has_campaign = True

    labels = {
        field: (
            current.get(field) if current_has_campaign else (saved or {}).get(field)
        )
        for field in PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS
    }
    # A new campaign is a new server-side visit record. Never reuse the prior
    # opaque reference, or authentication could resolve the previous campaign
    # while the cookie displays the new one. ``ensure_visit_attribution_reference``
    # creates the fresh reference after the mapping is assembled.
    saved_ref = (saved or {}).get(PUBLIC_VISIT_ATTRIBUTION_REF_FIELD)
    attribution_ref = None if current_has_campaign else saved_ref
    yclid = current_yclid or (saved or {}).get(PUBLIC_VISIT_ATTRIBUTION_YCLID_FIELD)
    saved_category = (saved or {}).get("referrer_category")
    if current_has_campaign or not saved_category:
        referrer_category = current.get("referrer_category")
    else:
        referrer_category = saved_category
    landing_path = (saved or {}).get("landing_path") or current.get("landing_path")
    first_seen_at = None if current_has_campaign else (saved or {}).get("first_seen_at")
    if not first_seen_at and (current_has_campaign or any(labels.values())):
        first_seen_at = (now or datetime.now(UTC)).astimezone(UTC).isoformat()

    if current_has_campaign:
        # A stale or damaged prior cookie must not poison a fresh campaign
        # arriving on this request.  The current labels are authoritative only
        # for creating a new visit row, while the old opaque refs remain useful
        # only when the cookie itself decoded successfully.
        attribution_status = "current"
    elif saved_status == "invalid":
        attribution_status = "invalid"
    elif saved_status == "saved":
        attribution_status = "saved"
    else:
        attribution_status = "missing"

    attribution: dict[str, Any] = {
        **labels,
        PUBLIC_VISIT_ATTRIBUTION_YCLID_FIELD: yclid,
        "referrer_category": referrer_category,
        "landing_path": landing_path,
        "first_seen_at": first_seen_at,
        PUBLIC_VISIT_ATTRIBUTION_REF_FIELD: attribution_ref,
        PUBLIC_VISIT_ATTRIBUTION_REFS_FIELD: list(saved_refs),
        "attribution_status": attribution_status,
    }
    if attribution_status in PUBLIC_VISIT_ATTRIBUTION_KNOWN_STATUSES:
        attribution = ensure_visit_attribution_reference(attribution, now=now)
        attribution[PUBLIC_VISIT_ATTRIBUTION_REFS_FIELD] = _bounded_visit_attribution_refs(
            attribution,
            prepend=attribution.get(PUBLIC_VISIT_ATTRIBUTION_REF_FIELD),
        )
    return attribution


def _bridge_from_request(request: Any, *, now: datetime | None = None) -> Any:
    """Resolve the attribution bridge a request carries, when it carries one.

    The identifier is checked against the exact shape the product issues before
    it is looked up, so a value that came from the address bar cannot become a
    lookup key of anything else (FR-014, FR-022).
    """
    query_params = getattr(request, "query_params", None)
    bridge_id = attribution_bridge_id_for_request(
        {
            APP_HANDOFF_BRIDGE_PARAM: _query_value(query_params, APP_HANDOFF_BRIDGE_PARAM),
            ATTRIBUTION_REF_REQUEST_PARAM: _query_value(
                query_params, ATTRIBUTION_REF_REQUEST_PARAM
            ),
        }
    )
    if bridge_id is None:
        return None
    return default_attribution_bridge_registry().resolve(bridge_id, now=now)


def _decoded_visit_attribution(
    request: Any, *, now: datetime | None = None
) -> tuple[dict[str, Any] | None, str]:
    """Return validated labels and exact refs; a damaged record grants nothing."""
    cookies = getattr(request, "cookies", None)
    raw = cookies.get(PUBLIC_VISIT_ATTRIBUTION_COOKIE) if hasattr(cookies, "get") else None
    if not raw:
        return None, "missing"
    if len(str(raw)) > PUBLIC_VISIT_ATTRIBUTION_MAX_BYTES:
        return None, "invalid"
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return None, "invalid"
    if not isinstance(payload, Mapping) or payload.get("v") not in PUBLIC_VISIT_ATTRIBUTION_LEGACY_VERSIONS:
        return None, "invalid"
    if set(payload) - {"v", *PUBLIC_VISIT_ATTRIBUTION_FIELDS}:
        return None, "invalid"

    labels: dict[str, str | None] = {}
    for field in PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS:
        value = payload.get(field)
        if value is None:
            labels[field] = None
            continue
        sanitized = sanitize_anonymous_aggregate_label(value)
        if sanitized is None:
            return None, "invalid"
        labels[field] = sanitized.lower() if field in {"utm_source", "utm_medium"} else sanitized

    yclid = payload.get(PUBLIC_VISIT_ATTRIBUTION_YCLID_FIELD)
    safe_yclid = _safe_yclid(yclid) if yclid is not None else None
    if yclid is not None and safe_yclid is None:
        return None, "invalid"

    landing_path = payload.get("landing_path")
    if landing_path is not None and not surface_for_public_path(str(landing_path)):
        return None, "invalid"
    referrer_category = payload.get("referrer_category")
    if referrer_category is not None and referrer_category not in {
        "direct",
        "organic",
        "paid",
        "referral",
        "unknown",
    }:
        return None, "invalid"
    first_seen_at = payload.get("first_seen_at")
    if first_seen_at is not None:
        if not _is_iso_timestamp(first_seen_at):
            return None, "invalid"
        parsed_first_seen = _parse_iso_timestamp(first_seen_at)
        moment = (now or datetime.now(UTC)).astimezone(UTC)
        if parsed_first_seen is None or not is_within_attribution_window(parsed_first_seen, now=moment):
            return None, "invalid"
        first_seen_at = parsed_first_seen.isoformat()
    current_ref = payload.get(PUBLIC_VISIT_ATTRIBUTION_REF_FIELD)
    if current_ref is not None and not _PUBLIC_VISIT_ATTRIBUTION_REF_RE.fullmatch(str(current_ref)):
        return None, "invalid"
    refs_value = payload.get(PUBLIC_VISIT_ATTRIBUTION_REFS_FIELD)
    if refs_value is None:
        refs_value = [current_ref] if current_ref else []
    if not isinstance(refs_value, (list, tuple)):
        return None, "invalid"
    refs = _bounded_visit_attribution_refs(
        {PUBLIC_VISIT_ATTRIBUTION_REFS_FIELD: refs_value},
    )
    if current_ref and current_ref not in refs:
        refs = _bounded_visit_attribution_refs({}, prepend=current_ref, refs=refs)

    return (
        {
            **labels,
            PUBLIC_VISIT_ATTRIBUTION_YCLID_FIELD: safe_yclid,
            "referrer_category": referrer_category,
            "landing_path": landing_path,
            "first_seen_at": first_seen_at,
            PUBLIC_VISIT_ATTRIBUTION_REF_FIELD: str(current_ref) if current_ref else None,
            PUBLIC_VISIT_ATTRIBUTION_REFS_FIELD: refs,
        },
        "saved",
    )


def _bounded_visit_attribution_refs(
    attribution: Mapping[str, Any] | None,
    *,
    prepend: Any = None,
    refs: Any = None,
) -> tuple[str, ...]:
    """Return a newest-first, deduplicated ring of exact opaque references."""
    values: list[Any] = []
    if prepend is not None:
        values.append(prepend)
    source = refs if refs is not None else (attribution or {}).get(PUBLIC_VISIT_ATTRIBUTION_REFS_FIELD, ())
    if isinstance(source, (list, tuple)):
        values.extend(source)
    elif source is not None:
        values.append(source)
    current = (attribution or {}).get(PUBLIC_VISIT_ATTRIBUTION_REF_FIELD)
    if current is not None:
        values.append(current)
    result: list[str] = []
    for value in values:
        if not isinstance(value, str) or not _PUBLIC_VISIT_ATTRIBUTION_REF_RE.fullmatch(value):
            continue
        if value not in result:
            result.append(value)
        if len(result) >= PUBLIC_VISIT_ATTRIBUTION_MAX_REFS:
            break
    return tuple(result)


def _encode_visit_attribution(attribution: Mapping[str, Any]) -> str | None:
    payload: dict[str, Any] = {"v": PUBLIC_VISIT_ATTRIBUTION_VERSION}
    refs = _bounded_visit_attribution_refs(attribution, prepend=attribution.get(PUBLIC_VISIT_ATTRIBUTION_REF_FIELD))
    for field in PUBLIC_VISIT_ATTRIBUTION_FIELDS:
        if field == PUBLIC_VISIT_ATTRIBUTION_REFS_FIELD:
            if refs:
                payload[field] = list(refs)
            continue
        value = attribution.get(field)
        if value:
            payload[field] = str(value)
    try:
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)
    except (TypeError, ValueError):
        return None


def _visit_attribution_has_campaign(attribution: Mapping[str, str | None] | None) -> bool:
    if not attribution:
        return False
    return bool(
        attribution.get(PUBLIC_VISIT_ATTRIBUTION_YCLID_FIELD)
        or any(attribution.get(field) for field in PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS)
    )


def _relay_campaign_attribution(value: Any, *, categories: Any) -> dict[str, str]:
    """Keep campaign labels only when advertising attribution was granted."""
    if value is None:
        return {}
    if "advertising_attribution" not in list(categories):
        return {}
    if not isinstance(value, Mapping):
        raise PublicAnalyticsEventRejected("campaign_attribution_rejected")
    if set(value) - set(UTM_FIELDS):
        raise PublicAnalyticsEventRejected("campaign_attribution_rejected")
    campaign: dict[str, str] = {}
    for field in UTM_FIELDS:
        sanitized = sanitize_anonymous_aggregate_label(value.get(field))
        if sanitized is not None:
            campaign[field] = sanitized
    return campaign


def _request_path(request: Any) -> str:
    url = getattr(request, "url", None)
    path = getattr(url, "path", None)
    if not isinstance(path, str):
        path = getattr(request, "url_path", "")
    return path if isinstance(path, str) else ""


def _request_header(request: Any, name: str) -> str | None:
    headers = getattr(request, "headers", None)
    getter = getattr(headers, "get", None)
    if getter is None:
        return None
    value = getter(name)
    return str(value) if value is not None else None


def _request_client_host(request: Any) -> str | None:
    client = getattr(request, "client", None)
    host = getattr(client, "host", None)
    return str(host) if host else None


def _request_is_secure(request: Any) -> bool:
    forwarded = _request_header(request, "x-forwarded-proto")
    if forwarded:
        return forwarded.split(",")[0].strip().lower() == "https"
    url = getattr(request, "url", None)
    return str(getattr(url, "scheme", "")).lower() == "https"


def _safe_yclid(value: Any) -> str | None:
    """Keep a Yandex click identifier only when it has a sane shape (FR-016)."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped if _YCLID_RE.fullmatch(stripped) else None


def _is_iso_timestamp(value: Any) -> bool:
    return _parse_iso_timestamp(value) is not None


def _non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value >= 0 else None
