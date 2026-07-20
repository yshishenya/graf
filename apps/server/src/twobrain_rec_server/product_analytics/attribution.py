from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from twobrain_rec_server.product_analytics.forbidden_fields import assert_no_forbidden_fields

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
    reliability_level: str = "counted_unlinked"

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


def build_public_bridge_context(attribution: Mapping[str, Any] | None) -> dict[str, Any]:
    source_context = {field: _safe_optional_str(attribution.get(field)) if attribution else None for field in ATTRIBUTION_FIELDS}
    context = {
        "bridge_supported": True,
        "graf_attribution_id_required_for_reliable_handoff": True,
        "source_context_fields": list(ATTRIBUTION_FIELDS),
        "source_context": source_context,
    }
    assert_no_forbidden_fields(context)
    return context


def create_attribution_bridge(
    *,
    source_context: Mapping[str, str | None],
    bridge_token: str | None = None,
    ttl_hours: int = 72,
) -> AttributionBridgeRecord:
    now = datetime.now(UTC)
    safe_context = {field: _safe_optional_str(source_context.get(field)) for field in ATTRIBUTION_FIELDS}
    bridge = AttributionBridgeRecord(
        graf_attribution_id=f"graf_attr_{uuid4().hex}",
        bridge_token_hash=_hash_bridge_token(bridge_token) if bridge_token else None,
        created_at=now,
        expires_at=now + timedelta(hours=ttl_hours),
        source_context=safe_context,
    )
    assert_no_forbidden_fields(bridge.as_dict())
    return bridge


def reliability_for_event(event_name: str, *, bridge_present: bool, account_connected: bool) -> str:
    if event_name == "desktop_first_opened" and not bridge_present:
        return "counted_unlinked"
    if account_connected:
        return "campaign_linked_reliable"
    if bridge_present:
        return "campaign_linked_weak"
    return "not_linkable"


def _hash_bridge_token(value: str) -> str:
    return "graf_bridge_hash_" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def _safe_optional_str(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    assert_no_forbidden_fields({"value": normalized})
    return normalized[:96]
