"""Authenticated, consent-bound explicit milestones. No provider configuration mutation."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.event_catalog import PRODUCT_ACTIVATION_EVENT_NAMES
from twobrain_rec_server.product_analytics.events import build_activation_event
from twobrain_rec_server.product_analytics.identity import build_safe_identity
from twobrain_rec_server.product_analytics.posthog_client import PostHogClientWrapper

EXPLICIT_EVENTS = frozenset(PRODUCT_ACTIVATION_EVENT_NAMES) - {"desktop_autorecord_enabled"}


def configuration_allowed(settings: Settings) -> bool:
    return bool(
        settings.product_analytics_explicit_funnel_enabled
        and settings.product_analytics_legal_approved
        and settings.product_analytics_privacy_approved
        and settings.public_analytics_consent_copy_version
        and not settings.public_analytics_consent_copy_version.startswith("pending")
        and not settings.product_analytics_posthog_autocapture_enabled
        and not settings.product_analytics_posthog_web_direct_enabled
        and not settings.product_analytics_replay_enabled
        and not settings.product_analytics_posthog_desktop_direct_enabled
        and not settings.product_analytics_direct_desktop_egress_enabled
        and not settings.product_analytics_yandex_offline_enabled
    )


def context_for(settings: Settings, *, user_id: str, state: dict | None) -> dict[str, Any]:
    state = state or {}
    consent = state.get("consent") or {}
    allowed = configuration_allowed(settings)
    gate = "not_seen"
    if allowed and consent.get("state") == "accepted":
        gate = (
            "accepted"
            if consent.get("copy_version") == settings.public_analytics_consent_copy_version
            else "terms_update_required"
        )
    elif consent.get("state") == "withdrawn":
        gate = "withdrawn"
    return {
        "enabled": allowed,
        "telemetry_gate_state": gate,
        "copy_version": settings.public_analytics_consent_copy_version,
        "stable_pseudonymous_user_id": build_safe_identity(
            user_source_id=user_id
        ).posthog_distinct_id,
        "event_route": "/api/v1/product-analytics/explicit-events",
        "delivery_mode": "server_mediated",
    }


def change_consent(
    settings: Settings, state: dict | None, *, accepted: bool, copy_version: str
) -> dict:
    if accepted and not configuration_allowed(settings):
        raise ValueError("explicit analytics consent configuration is not ready")
    if accepted and copy_version != settings.public_analytics_consent_copy_version:
        raise ValueError("analytics disclosure version is not current")
    updated = dict(state or {})
    updated["consent"] = {
        "state": "accepted" if accepted else "withdrawn",
        "copy_version": copy_version,
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    return updated


# Closed categories only: free text, nested values and client identity fields
# cannot cross this boundary. Campaign names/bridge IDs require a separately
# verified server registry; they are deliberately absent from this slice.
_CATEGORY_VALUES = {
    "platform": {"macos"},
    "install_channel": {"developer_id", "local_build", "direct", "unknown"},
    "auth_method_category": {"unknown", "oauth_provider", "email_code"},
    "account_connection_state": {"connected"},
    "duration_bucket": {"under_1m", "1m_to_10m", "10m_to_30m", "30m_to_60m", "over_60m"},
    "capture_mode": {"system_audio_and_microphone"},
    "completion_state": {"saved", "degraded"},
    "result_pending_state": {"upload_pending", "degraded"},
    "result_state": {"ready", "processing"},
    "surface": {"embedded_cabinet_meeting_detail", "cabinet_web"},
    "useful_result_type": {
        "transcript",
        "summary",
        "outcome",
        "action_items",
        "approved_equivalent",
    },
    "attribution_reliability": {"unknown", "weak"},
    "campaign_label_state": {"unknown", "known"},
    "utm_source": {
        "google",
        "yandex",
        "bing",
        "telegram",
        "productradar",
        "chatgpt",
        "perplexity",
        "unknown",
    },
    "utm_medium": {"organic", "referral", "social", "email", "cpc", "unknown"},
}
_BOOLEAN_FIELDS = {
    "bridge_present",
    "useful_output_present",
    "first_recording_completed",
    "first_result_viewed",
}


def closed_properties(properties: dict) -> dict:
    if not isinstance(properties, dict):
        raise ValueError("explicit properties must be a flat category object")
    for key, value in properties.items():
        if key in _BOOLEAN_FIELDS:
            valid = type(value) is bool or (isinstance(value, str) and value in {"true", "false"})
        elif key == "app_version_bucket":
            valid = isinstance(value, str) and (
                value == "unknown" or re.fullmatch(r"[0-9]{1,4}\.[0-9]{1,2}", value) is not None
            )
        else:
            valid = (
                key in _CATEGORY_VALUES
                and isinstance(value, str)
                and value in _CATEGORY_VALUES[key]
            )
        if not valid:
            raise ValueError("explicit property is outside its closed category contract")
    return dict(properties)


def validate_milestone(settings: Settings, *, user_id: str, state: dict | None, payload: dict):
    context = context_for(settings, user_id=user_id, state=state)
    if context["telemetry_gate_state"] != "accepted":
        raise ValueError("current personal analytics consent is required")
    name = payload.get("event_name")
    if name not in EXPLICIT_EVENTS:
        raise ValueError("event is outside the minimal explicit funnel")
    identity = context["stable_pseudonymous_user_id"]
    claimed = payload.get("stable_pseudonymous_user_id")
    if claimed is not None and claimed != identity:
        raise ValueError("analytics identity does not match the authenticated user")
    event = build_activation_event(
        name,
        stable_pseudonymous_user_id=identity,
        occurred_at=payload.get("occurred_at"),
        properties=closed_properties(payload.get("properties") or {}),
    )
    return event


def deliver_milestone(
    settings: Settings,
    *,
    user_id: str,
    state: dict | None,
    payload: dict,
    provider: PostHogClientWrapper | None = None,
) -> tuple[dict, dict]:
    """Caller holds the authenticated user row lock until it commits metadata.

    Provider acceptance is not an ingestion proof. Unknown network completion
    can retry the same UUID; readback verifies actual ingestion independently.
    """
    updated = dict(state or {})
    event = validate_milestone(settings, user_id=user_id, state=updated, payload=payload)
    name = event.event_name
    identity = event.stable_pseudonymous_user_id
    receipts = dict(updated.get("milestones") or {})
    event_id = str(uuid5(NAMESPACE_URL, f"graf-explicit-funnel-v1:{identity}:{name}"))
    if name in receipts:
        return updated, {
            "accepted": True,
            "status": "duplicate",
            "provider_accepted": True,
            "ingestion_verified": False,
        }
    result = (provider or PostHogClientWrapper.from_settings(settings)).capture_event(
        event_name=name,
        distinct_id=identity,
        properties=event.properties,
        timestamp=event.occurred_at,
        explicit_event_id=event_id,
    )
    if result.status != "live_safe_sent":
        return updated, {
            "accepted": False,
            "status": "delivery_pending",
            "provider_accepted": False,
            "ingestion_verified": False,
        }
    receipts[name] = {"event_id": event_id, "provider_accepted_at": datetime.now(UTC).isoformat()}
    updated["milestones"] = receipts
    return updated, {
        "accepted": True,
        "status": "provider_accepted",
        "provider_accepted": True,
        "ingestion_verified": False,
    }
