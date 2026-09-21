"""The attribution bridge: from a public page visit to a product activation.

Level 2 needs one thing that level 1 deliberately does not have — a way to carry
the campaign of a visit into the product. The bridge is that carrier:

* :func:`build_public_bridge_context` creates a real bridge while a public page
  is rendered (it is called from the public analytics context, so every public
  page render reaches this code);
* :class:`AttributionBridgeRegistry` resolves the bridge identifier back to the
  campaign labels while the visit is still alive;
* :func:`build_app_handoff_url` produces the link the download page hands to the
  desktop app, because sign-in and sign-up inside the app happen in an embedded
  window that never sees the browser state of the visit (FR-022);
* :func:`resolve_attribution_handoff` reads that link back on the server side.

Rules kept here: the bridge lives at most 90 days and normally much less; the
reliability of a link is ``linked``, ``weak`` or ``unknown`` (FR-023); an
unknown campaign is ``unknown`` and never ``direct`` (FR-024); only presence
flags of Yandex identities travel, never their values (FR-016, FR-028).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl, urlencode
from uuid import uuid4

from twobrain_rec_server.product_analytics.acquisition import (
    ATTRIBUTION_CONFIDENCE_LEVELS,
    ATTRIBUTION_WINDOW_DAYS,
    VisitAttribution,
    resolve_attribution_confidence,
    resolve_last_non_direct_source,
    sanitize_yclid,
)
from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    sanitize_anonymous_aggregate_label,
)
from twobrain_rec_server.product_analytics.event_catalog import PRODUCT_ACTIVATION_EVENT_NAMES
from twobrain_rec_server.product_analytics.forbidden_fields import (
    assert_no_forbidden_fields,
    find_forbidden_fields,
)

ATTRIBUTION_FIELDS = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_id",
    "utm_content",
    "utm_term",
    "referrer_category",
    "landing_path",
    "normalization_status",
)

CAMPAIGN_CONTEXT_FIELDS = ("utm_source", "utm_medium", "utm_campaign", "utm_id", "utm_content", "utm_term")

# The labels a conversion event may carry (FR-018). They are the campaign
# *categories* of the visit and nothing else: ``utm_id`` is deliberately absent,
# because that value is a raw identifier of an ad on the platform, while a click
# identifier never travels in an event at all (FR-016, FR-028).
CAMPAIGN_LABEL_FIELDS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")
# The two labels the whole feature stores lowered, so a campaign keeps one
# spelling from the page address to the client record and to an event.
CAMPAIGN_LOWERCASED_LABEL_FIELDS = ("utm_source", "utm_medium")

# Whether a conversion event knows its campaign at all. ``unknown`` is a value of
# its own and never ``direct``: "прямой заход" is a property of the referrer of a
# visit, not of a conversion whose campaign nobody knows (FR-018, FR-024).
CAMPAIGN_LABEL_STATE_KNOWN = "known"
CAMPAIGN_LABEL_STATE_UNKNOWN = "unknown"
CAMPAIGN_LABEL_STATES = (CAMPAIGN_LABEL_STATE_KNOWN, CAMPAIGN_LABEL_STATE_UNKNOWN)

ATTRIBUTION_RELIABILITY_LINKED = "linked"
ATTRIBUTION_RELIABILITY_WEAK = "weak"
ATTRIBUTION_RELIABILITY_UNKNOWN = "unknown"

# The vocabulary of the earlier slice is still produced by older call sites; it
# is translated here instead of being accepted as a reliability of its own, so
# every conversion event carries exactly one of the three contract levels.
LEGACY_RELIABILITY_LEVELS = {
    "campaign_linked_reliable": ATTRIBUTION_RELIABILITY_LINKED,
    "campaign_linked_weak": ATTRIBUTION_RELIABILITY_WEAK,
    "counted_unlinked": ATTRIBUTION_RELIABILITY_UNKNOWN,
    "not_linkable": ATTRIBUTION_RELIABILITY_UNKNOWN,
}

BRIDGE_TOKEN_PREFIX = "graf_bridge_hash_"
BRIDGE_ID_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz_-"
BRIDGE_ID_PREFIX = "graf_attr_"
ATTRIBUTION_BRIDGE_TTL_HOURS = 72
ATTRIBUTION_BRIDGE_MAX_ENTRIES = 4096

# Keys of a raw page context that describe which Yandex identity was present.
# Only presence is kept: the value itself never reaches a bridge record.
BRIDGE_IDENTITY_PRESENCE_KEYS = {
    "yclid": "yclid_present",
    "yandex_user_id_present": "yandex_user_id_present",
    "yandex_client_id_present": "yandex_client_id_present",
    "posthog_anonymous_id_present": "posthog_anonymous_id_present",
}

APP_HANDOFF_SCHEME = "grafrec"
APP_HANDOFF_HOST = "attribution"
APP_HANDOFF_BRIDGE_PARAM = "bridge"
APP_HANDOFF_LANDING_PATH_PARAM = "landing_path"
APP_HANDOFF_FALLBACK_PARAM = "fallback"
APP_HANDOFF_SESSION_STORAGE_KEY = "graf_attribution_handoff"
# The embedded cabinet window is the only place where an in-app sign-up happens,
# so the app forwards the handoff through the requested route as well.
ATTRIBUTION_REF_REQUEST_PARAM = "graf_attribution_ref"
ATTRIBUTION_FALLBACK_REQUEST_PARAM = "graf_attribution_fallback"


@dataclass(frozen=True, slots=True)
class AttributionBridgeRecord:
    graf_attribution_id: str
    bridge_token_hash: str | None
    created_at: datetime
    expires_at: datetime
    source_context: dict[str, str | None]
    yandex_client_id_present: bool = False
    yandex_user_id_present: bool = False
    yclid_present: bool = False
    posthog_anonymous_id_present: bool = False
    link_state: str = "unlinked"
    reliability_level: str = ATTRIBUTION_RELIABILITY_UNKNOWN

    def as_dict(self) -> dict[str, Any]:
        return {
            "graf_attribution_id": self.graf_attribution_id,
            "bridge_token_hash": self.bridge_token_hash,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "source_context": dict(self.source_context),
            "yandex_user_id_present": self.yandex_user_id_present,
            "yandex_client_id_present": self.yandex_client_id_present,
            "yclid_present": self.yclid_present,
            "yandex_identity_sources_present": self.yandex_identity_sources_present(),
            "posthog_anonymous_id_present": self.posthog_anonymous_id_present,
            "link_state": self.link_state,
            "reliability_level": self.reliability_level,
        }

    def yandex_identity_sources_present(self) -> list[str]:
        sources: list[str] = []
        if self.yandex_user_id_present:
            sources.append("UserId")
        if self.yandex_client_id_present:
            sources.append("ClientId")
        if self.yclid_present:
            sources.append("Yclid")
        return sources

    def campaign_known(self) -> bool:
        return any(self.source_context.get(field) for field in CAMPAIGN_CONTEXT_FIELDS)

    def is_expired(self, *, now: datetime | None = None) -> bool:
        return (now or datetime.now(UTC)) >= self.expires_at

    def campaign_context(self) -> dict[str, str | None]:
        """The labels of the visit, without any identifier of the visitor."""
        return {field: self.source_context.get(field) for field in CAMPAIGN_CONTEXT_FIELDS}


@dataclass(frozen=True, slots=True)
class AttributionHandoff:
    """The attribution that travels from a public page into the product."""

    graf_attribution_id: str | None
    campaign_context: dict[str, str | None]
    fallback_recovered: bool
    landing_path: str | None = None

    def campaign_known(self) -> bool:
        return any(self.campaign_context.values())

    def reliability(self, *, account_connected: bool = False) -> str:
        """``linked``, ``weak`` or ``unknown`` for one conversion event (FR-023)."""
        return resolve_conversion_reliability(
            campaign_known=self.campaign_known(),
            account_connected=account_connected,
            fallback_recovered=self.fallback_recovered,
        )


def normalize_attribution_reliability(value: Any) -> str | None:
    """Translate any known reliability wording into the contract level.

    ``direct`` is not a reliability level, so it never translates into one: an
    event whose campaign is unknown stays ``unknown`` (FR-024).
    """
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in ATTRIBUTION_CONFIDENCE_LEVELS:
        return normalized
    return LEGACY_RELIABILITY_LEVELS.get(normalized)


def resolve_conversion_reliability(
    *,
    campaign_known: bool,
    account_connected: bool = False,
    fallback_recovered: bool = False,
) -> str:
    """The reliability of one conversion event's campaign link (FR-023)."""
    if not campaign_known:
        return ATTRIBUTION_RELIABILITY_UNKNOWN
    if account_connected and not fallback_recovered:
        return ATTRIBUTION_RELIABILITY_LINKED
    return ATTRIBUTION_RELIABILITY_WEAK


def campaign_labels_for_event(
    campaign_context: Mapping[str, Any] | None,
) -> tuple[dict[str, str | None], str]:
    """Return the campaign labels a conversion event carries and their state.

    This is the same rule as everywhere else in the feature, applied to the
    properties of an event instead of to a stored row: a label survives only
    when it cannot be private data, and a campaign that is not known is reported
    as ``unknown`` — the event never invents a source and never reads as a
    direct entry (FR-018, FR-024).

    The returned mapping always names every label of
    :data:`CAMPAIGN_LABEL_FIELDS`, so a reader can tell "no campaign" from
    "label absent from this event", and the state is the single explicit marker
    of that difference.
    """
    values = campaign_context or {}
    labels = {
        field: _safe_optional_str(
            # The public page and the visit record lower these two labels before
            # storing them, so the same normalization is applied before the
            # shared sanitizer: it reads a capitalized label as a person's name
            # and would drop a perfectly ordinary ``Yandex_Direct``.
            _lowered(values.get(field)) if field in CAMPAIGN_LOWERCASED_LABEL_FIELDS else values.get(field)
        )
        for field in CAMPAIGN_LABEL_FIELDS
    }
    known = any(value for value in labels.values())
    if not known:
        # One label of a campaign is not a campaign: a half-known set would be
        # read as a channel the visitor never came from.
        labels = dict.fromkeys(CAMPAIGN_LABEL_FIELDS)
    state = CAMPAIGN_LABEL_STATE_KNOWN if known else CAMPAIGN_LABEL_STATE_UNKNOWN
    return labels, state


def campaign_labels_from_values(values: Mapping[str, Any] | None) -> dict[str, Any]:
    """Read the campaign labels of a request, a link or a page context.

    Only the label names of the contract are read, so a caller cannot smuggle a
    click identifier or a personal value into an event through this helper.
    """
    source = values or {}
    return {field: source.get(field) for field in CAMPAIGN_LABEL_FIELDS if source.get(field)}


def attribution_bridge_id_for_request(values: Mapping[str, Any] | None) -> str | None:
    """Return the bridge identifier a request carries, in its checked shape.

    Only the identifier of the handoff link is read here; the campaign labels of
    the request win over the bridge, exactly as in
    :func:`resolve_attribution_handoff` (FR-022).
    """
    source = values or {}
    return safe_attribution_bridge_id(
        source.get(APP_HANDOFF_BRIDGE_PARAM) or source.get(ATTRIBUTION_REF_REQUEST_PARAM)
    )


def build_public_bridge_context(
    attribution: Mapping[str, Any] | None,
    *,
    bridge_token: str | None = None,
    ttl_hours: int = ATTRIBUTION_BRIDGE_TTL_HOURS,
    registry: AttributionBridgeRegistry | None = None,
) -> dict[str, Any]:
    """Build the bridge of a public page render and record it for resolution.

    The returned mapping is rendered into the public page configuration, so it
    may contain campaign labels and presence flags only. It never contains an
    identifier of the visitor and never a raw Yandex identifier value.
    """
    bridge = create_attribution_bridge(
        source_context=attribution or {},
        bridge_token=bridge_token,
        ttl_hours=ttl_hours,
    )
    # Явно переданный реестр используется как есть: пустой реестр — это
    # изоляция на вызов, а не повод молча писать в процессный.
    (registry if registry is not None else default_attribution_bridge_registry()).record(bridge)
    context = {
        "bridge_supported": True,
        "graf_attribution_id_required_for_reliable_handoff": True,
        "graf_attribution_id": bridge.graf_attribution_id,
        "attribution_link_state": bridge.link_state,
        "attribution_reliability": bridge.reliability_level,
        "bridge_expires_at": bridge.expires_at.isoformat(),
        "yclid_present": bridge.yclid_present,
        "yandex_identity_sources_present": bridge.yandex_identity_sources_present(),
        "app_handoff_url": build_app_handoff_url(bridge),
        "source_context_fields": list(ATTRIBUTION_FIELDS),
        "source_context": dict(bridge.source_context),
    }
    # Only the untrusted part is checked here: the timestamps and the handoff
    # link are produced by this module and are not analytics payload fields.
    assert_no_forbidden_fields({"source_context": dict(bridge.source_context)})
    return context


def create_attribution_bridge(
    *,
    source_context: Mapping[str, Any],
    bridge_token: str | None = None,
    ttl_hours: int = ATTRIBUTION_BRIDGE_TTL_HOURS,
    bridge_id: str | None = None,
    now: datetime | None = None,
) -> AttributionBridgeRecord:
    """Create the bridge of one visit from the campaign context of a page.

    Presence flags are derived from the context that actually arrived, so a
    click identifier that is really present is really reported (FR-016).
    """
    moment = now or datetime.now(UTC)
    if not 1 <= int(ttl_hours) <= ATTRIBUTION_WINDOW_DAYS * 24:
        raise ValueError("attribution bridge lifetime must stay inside the 90-day window")
    safe_context = {
        field: _safe_bridge_context_value(field, source_context.get(field))
        for field in ATTRIBUTION_FIELDS
    }
    presence = {
        flag: _identity_presence(source_context.get(key))
        for key, flag in BRIDGE_IDENTITY_PRESENCE_KEYS.items()
    }
    campaign_known = any(safe_context.get(field) for field in CAMPAIGN_CONTEXT_FIELDS)
    identified = safe_attribution_bridge_id(bridge_id) if bridge_id else f"{BRIDGE_ID_PREFIX}{uuid4().hex}"
    if identified is None:
        raise ValueError("attribution bridge identifier must be an opaque safe identifier")
    bridge = AttributionBridgeRecord(
        graf_attribution_id=identified,
        bridge_token_hash=_hash_bridge_token(bridge_token) if bridge_token else None,
        created_at=moment,
        expires_at=moment + timedelta(hours=int(ttl_hours)),
        source_context=safe_context,
        link_state="linked" if campaign_known else "unlinked",
        reliability_level=resolve_attribution_confidence(campaign_known=campaign_known),
        **presence,
    )
    # The labels are the only untrusted part of a bridge: every one of them has
    # already been dropped when it looked like private data.
    assert_no_forbidden_fields({"source_context": dict(bridge.source_context)})
    return bridge


def reliability_for_event(
    event_name: str,
    *,
    bridge_present: bool,
    account_connected: bool,
) -> str:
    """The reliability level a conversion milestone must carry (FR-023)."""
    if event_name not in PRODUCT_ACTIVATION_EVENT_NAMES:
        raise ValueError("attribution reliability is defined for conversion milestones only")
    if not bridge_present:
        return ATTRIBUTION_RELIABILITY_UNKNOWN
    return (
        ATTRIBUTION_RELIABILITY_LINKED
        if account_connected
        else ATTRIBUTION_RELIABILITY_WEAK
    )


def build_app_handoff_url(
    bridge: AttributionBridgeRecord,
    *,
    scheme: str = APP_HANDOFF_SCHEME,
    fallback: bool = True,
) -> str:
    """The link the download page hands to the desktop app (FR-022).

    Only campaign labels travel: the click identifier of Yandex.Direct stays in
    the visit attribution and is never put into a link (FR-016, FR-028).
    """
    query: list[tuple[str, str]] = [(APP_HANDOFF_BRIDGE_PARAM, bridge.graf_attribution_id)]
    for field, value in bridge.source_context.items():
        if field in CAMPAIGN_CONTEXT_FIELDS and value:
            query.append((field, value))
    landing_path = bridge.source_context.get("landing_path")
    if landing_path:
        query.append((APP_HANDOFF_LANDING_PATH_PARAM, landing_path))
    if fallback:
        query.append((APP_HANDOFF_FALLBACK_PARAM, "1"))
    return f"{scheme}://{APP_HANDOFF_HOST}?{urlencode(query)}"


def resolve_attribution_handoff(
    values: Mapping[str, Any],
    *,
    fallback_recovered: bool | None = None,
    registry: AttributionBridgeRegistry | None = None,
    visits: Iterable[VisitAttribution] | None = None,
    now: datetime | None = None,
) -> AttributionHandoff | None:
    """Read a handoff back from a request, a link or the visits of the browser.

    The labels of the request win when they are present, because the visitor
    really came with them. When only the bridge identifier is left, the bridge
    registry of the rendering process resolves it. When the visits of the
    browser are known, the same rule as the primary path applies to them
    (:func:`resolve_last_non_direct_source`: the last non-direct visit inside
    90 days), so both paths attach the same campaign (FR-022, T049).
    """
    normalized = {str(key): value for key, value in values.items() if value is not None}
    bridge_id = safe_attribution_bridge_id(
        normalized.get(APP_HANDOFF_BRIDGE_PARAM) or normalized.get(ATTRIBUTION_REF_REQUEST_PARAM)
    )
    campaign_context = {
        field: _safe_optional_str(normalized.get(field)) for field in CAMPAIGN_CONTEXT_FIELDS
    }
    landing_path = _safe_path_or_state(
        normalized.get(APP_HANDOFF_LANDING_PATH_PARAM) or normalized.get("landing_path")
    )
    resolved_bridge: AttributionBridgeRecord | None = None
    if bridge_id is not None and not any(campaign_context.values()):
        active_registry = registry if registry is not None else default_attribution_bridge_registry()
        resolved_bridge = active_registry.resolve(
            bridge_id, now=now
        )
        if resolved_bridge is not None:
            campaign_context = resolved_bridge.campaign_context()
            landing_path = landing_path or resolved_bridge.source_context.get("landing_path")
    if visits is not None and not any(campaign_context.values()):
        visit = resolve_last_non_direct_source(visits, now=now)
        if visit is not None:
            campaign_context = {
                "utm_source": visit.source,
                "utm_medium": visit.medium,
                "utm_campaign": visit.campaign,
                "utm_id": None,
                "utm_content": visit.content,
                "utm_term": visit.term,
            }
            landing_path = landing_path or visit.landing_path
    if bridge_id is None and resolved_bridge is None and not any(campaign_context.values()):
        return None
    recovered = fallback_recovered
    if recovered is None:
        recovered = _fallback_flag(normalized.get(APP_HANDOFF_FALLBACK_PARAM)) or (
            _fallback_flag(normalized.get(ATTRIBUTION_FALLBACK_REQUEST_PARAM))
        )
    handoff = AttributionHandoff(
        graf_attribution_id=bridge_id,
        campaign_context=campaign_context,
        fallback_recovered=bool(recovered),
        landing_path=landing_path,
    )
    # Only the labels are untrusted here: the bridge identifier has already been
    # checked to be exactly ``graf_attr_`` plus hexadecimal characters, and a
    # request that carries it must never fail (FR-011).
    assert_no_forbidden_fields({"campaign_context": dict(handoff.campaign_context)})
    return handoff


class AttributionBridgeRegistry:
    """Resolves a bridge created while rendering a public page (FR-022).

    The durable record of a visit is the ``public_visit_attributions`` row
    written when the labels reach the product. This registry covers the window
    between rendering the page and that write inside one process; it is bounded,
    it forgets an expired bridge and it never outlives the process.
    """

    def __init__(
        self,
        *,
        max_entries: int = ATTRIBUTION_BRIDGE_MAX_ENTRIES,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.max_entries = max(1, int(max_entries))
        self._clock = clock or (lambda: datetime.now(UTC))
        self._bridges: dict[str, AttributionBridgeRecord] = {}

    def record(self, bridge: AttributionBridgeRecord) -> None:
        self.prune()
        self._bridges[bridge.graf_attribution_id] = bridge
        while len(self._bridges) > self.max_entries:
            oldest = min(self._bridges, key=lambda key: self._bridges[key].created_at)
            self._bridges.pop(oldest, None)

    def resolve(
        self,
        graf_attribution_id: str,
        *,
        now: datetime | None = None,
    ) -> AttributionBridgeRecord | None:
        bridge = self._bridges.get(graf_attribution_id)
        if bridge is None:
            return None
        if bridge.is_expired(now=now or self._clock()):
            self._bridges.pop(graf_attribution_id, None)
            return None
        return bridge

    def prune(self, *, now: datetime | None = None) -> int:
        moment = now or self._clock()
        expired = [key for key, bridge in self._bridges.items() if bridge.is_expired(now=moment)]
        for key in expired:
            self._bridges.pop(key, None)
        return len(expired)

    def clear(self) -> None:
        self._bridges.clear()

    def __len__(self) -> int:
        return len(self._bridges)


_DEFAULT_BRIDGE_REGISTRY = AttributionBridgeRegistry()


def default_attribution_bridge_registry() -> AttributionBridgeRegistry:
    return _DEFAULT_BRIDGE_REGISTRY


def _identity_presence(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return sanitize_yclid(value) is not None or value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def safe_attribution_bridge_id(value: Any) -> str | None:
    """Keep an identifier that is exactly the bridge shape and nothing else.

    The shape is an allowlist (prefix plus lowercase hexadecimal), so the
    generic value predicate is deliberately not applied here: a legitimate
    hexadecimal identifier must never be dropped because it happens to contain
    a long run of digits.
    """
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized.startswith(BRIDGE_ID_PREFIX):
        return None
    suffix = normalized[len(BRIDGE_ID_PREFIX):]
    if not 8 <= len(suffix) <= 64:
        return None
    if any(character not in BRIDGE_ID_ALPHABET for character in suffix):
        return None
    return normalized


def _fallback_flag(value: Any) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes"}


def parse_app_handoff_url(url: str) -> AttributionHandoff | None:
    """Read the handoff link of the download page without a browser."""
    if not isinstance(url, str):
        return None
    prefix = f"{APP_HANDOFF_SCHEME}://{APP_HANDOFF_HOST}"
    if not url.startswith(prefix):
        return None
    query = url.partition("?")[2]
    values = dict(parse_qsl(query, keep_blank_values=False))
    return resolve_attribution_handoff(values, fallback_recovered=True)


def _hash_bridge_token(value: str) -> str:
    return BRIDGE_TOKEN_PREFIX + hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def _lowered(value: Any) -> Any:
    return value.lower() if isinstance(value, str) else value


def _safe_optional_str(value: object) -> str | None:
    """Keep a campaign label only when it cannot be private data.

    The single shared sanitizer decides it, exactly as it does for the visit
    record and for the level 1 aggregate: an address, a phone number, a token or
    a local path is dropped instead of raising, because the public page must keep
    rendering and a page render must never fail because of a campaign label
    (FR-011, FR-014).
    """
    sanitized = sanitize_anonymous_aggregate_label(value)
    if sanitized is None:
        return None
    if find_forbidden_fields({"value": sanitized}):
        return None
    return sanitized[:96]


# The fields of a bridge context that are paths or states rather than campaign
# labels: the label sanitizer reads the separating slash of a path as unsafe, so
# a path is checked by its own rule.
_BRIDGE_PATH_FIELDS = ("landing_path", "referrer_category", "normalization_status")


def _safe_bridge_context_value(field: str, value: object) -> str | None:
    if field in _BRIDGE_PATH_FIELDS:
        return _safe_path_or_state(value)
    return _safe_optional_str(value)


def _safe_path_or_state(value: object) -> str | None:
    """Keep a path or a state of the visit, checked against the public pages."""
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized or len(normalized) > 200:
        return None
    if find_forbidden_fields({"value": normalized}):
        return None
    return normalized
