from __future__ import annotations

from dataclasses import dataclass

from twobrain_rec_server.product_analytics.forbidden_fields import FORBIDDEN_FIELD_NAMES


@dataclass(frozen=True, slots=True)
class ActivationEventDefinition:
    event_name: str
    surface: str
    owner: str
    posthog_destination: str
    yandex_destination: str
    allowed_fields: tuple[str, ...]
    delivery_mode: str
    identity_rule: str
    retention_category: str
    dashboard_owner: str
    reason: str

    @property
    def forbidden_fields(self) -> tuple[str, ...]:
        return FORBIDDEN_FIELD_NAMES

    def as_dict(self) -> dict[str, object]:
        return {
            "event_name": self.event_name,
            "surface": self.surface,
            "owner": self.owner,
            "posthog_destination": self.posthog_destination,
            "yandex_destination": self.yandex_destination,
            "allowed_fields": list(self.allowed_fields),
            "forbidden_fields": list(FORBIDDEN_FIELD_NAMES),
            "delivery_mode": self.delivery_mode,
            "identity_rule": self.identity_rule,
            "retention_category": self.retention_category,
            "dashboard_owner": self.dashboard_owner,
            "reason": self.reason,
        }


PUBLIC_ACQUISITION_EVENT_NAMES = (
    "public_landing_viewed",
    "public_landing_section_seen",
    "public_landing_cta_clicked",
    "public_download_viewed",
    "public_installer_download_clicked",
    "public_login_intent_clicked",
)

PRODUCT_ACTIVATION_EVENT_NAMES = (
    "desktop_first_opened",
    "desktop_account_connected",
    "desktop_autorecord_enabled",
    "first_recording_completed",
    "first_result_viewed",
    "first_value_session_completed",
)

FULL_ACTIVATION_FUNNEL = (
    "public_installer_download_clicked",
    *PRODUCT_ACTIVATION_EVENT_NAMES,
)

YANDEX_OFFLINE_CONVERSION_EVENTS = (
    "desktop_account_connected",
    "first_value_session_completed",
)

_COMMON_FIELDS = (
    "stable_pseudonymous_user_id",
    "graf_attribution_id",
    "attribution_reliability",
    "bridge_present",
    "elapsed_bucket",
    "source_bucket",
    "yandex_user_id_present",
    "yandex_client_id_present",
    "yclid_present",
)

ACTIVATION_EVENT_CATALOG: dict[str, ActivationEventDefinition] = {
    "desktop_first_opened": ActivationEventDefinition(
        event_name="desktop_first_opened",
        surface="desktop_native",
        owner="desktop",
        posthog_destination="identified_or_unlinked_event",
        yandex_destination="none",
        allowed_fields=(
            *_COMMON_FIELDS,
            "app_version_bucket",
            "platform",
            "install_channel",
        ),
        delivery_mode="server_mediated",
        identity_rule="count unlinked; link to stable pseudonymous user when known",
        retention_category="posthog_product_events",
        dashboard_owner="desktop",
        reason="Count first desktop adoption separately from public download intent.",
    ),
    "desktop_account_connected": ActivationEventDefinition(
        event_name="desktop_account_connected",
        surface="desktop_server_auth",
        owner="auth_server",
        posthog_destination="identified_event",
        yandex_destination="offline_conversion",
        allowed_fields=(
            *_COMMON_FIELDS,
            "auth_method_category",
            "account_connection_state",
        ),
        delivery_mode="server_mediated",
        identity_rule="stable pseudonymous user; first reliable campaign-linked milestone",
        retention_category="posthog_product_events",
        dashboard_owner="auth_server_growth",
        reason="Connect public campaign context to authenticated product activation.",
    ),
    "desktop_autorecord_enabled": ActivationEventDefinition(
        event_name="desktop_autorecord_enabled",
        surface="desktop_or_cabinet",
        owner="calendar_policy",
        posthog_destination="identified_event",
        yandex_destination="none",
        allowed_fields=(
            *_COMMON_FIELDS,
            "policy_state",
            "previous_state",
            "source",
            "surface",
        ),
        delivery_mode="server_mediated",
        identity_rule="stable pseudonymous user",
        retention_category="posthog_product_events",
        dashboard_owner="calendar_policy",
        reason="Measure first activation setup without calendar content.",
    ),
    "first_recording_completed": ActivationEventDefinition(
        event_name="first_recording_completed",
        surface="desktop_server",
        owner="capture_server",
        posthog_destination="identified_event",
        yandex_destination="none",
        allowed_fields=(
            *_COMMON_FIELDS,
            "duration_bucket",
            "capture_mode",
            "completion_state",
            "result_pending_state",
        ),
        delivery_mode="server_mediated",
        identity_rule="stable pseudonymous user",
        retention_category="posthog_product_events",
        dashboard_owner="capture_server",
        reason="Measure first successful recording without audio, filenames, or meeting titles.",
    ),
    "first_result_viewed": ActivationEventDefinition(
        event_name="first_result_viewed",
        surface="cabinet_web",
        owner="cabinet",
        posthog_destination="identified_event",
        yandex_destination="none",
        allowed_fields=(
            *_COMMON_FIELDS,
            "result_state",
            "surface",
            "useful_output_present",
        ),
        delivery_mode="server_mediated",
        identity_rule="stable pseudonymous user",
        retention_category="posthog_product_events",
        dashboard_owner="cabinet",
        reason="Measure result engagement without transcript, summary, participants, or title.",
    ),
    "first_value_session_completed": ActivationEventDefinition(
        event_name="first_value_session_completed",
        surface="cabinet_or_product_analytics",
        owner="product_analytics",
        posthog_destination="identified_event",
        yandex_destination="offline_conversion",
        allowed_fields=(
            *_COMMON_FIELDS,
            "first_recording_completed",
            "first_result_viewed",
            "useful_output_present",
            "useful_result_type",
        ),
        delivery_mode="server_mediated",
        identity_rule="stable pseudonymous user; approved bridge identifiers for offline conversion only",
        retention_category="posthog_product_events",
        dashboard_owner="product_analytics_growth",
        reason="Measure first value and default ad optimization milestone.",
    ),
}


def event_names() -> tuple[str, ...]:
    return tuple(ACTIVATION_EVENT_CATALOG)


def get_event_definition(event_name: str) -> ActivationEventDefinition:
    try:
        return ACTIVATION_EVENT_CATALOG[event_name]
    except KeyError as exc:
        raise ValueError(f"unknown product activation event: {event_name}") from exc


def catalog_payload() -> list[dict[str, object]]:
    return [definition.as_dict() for definition in ACTIVATION_EVENT_CATALOG.values()]


def yandex_offline_conversion_event_names() -> tuple[str, ...]:
    return YANDEX_OFFLINE_CONVERSION_EVENTS
