from __future__ import annotations

from dataclasses import dataclass

from twobrain_rec_server.product_analytics.forbidden_fields import (
    ANONYMOUS_AGGREGATE_ALLOWED_FIELDS,
    FORBIDDEN_FIELD_NAMES,
)


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
    # Every conversion event carries the campaign it came from (FR-018). The
    # labels are the categories of the visit — never a click identifier and
    # never a value that could point at a person — and ``campaign_label_state``
    # says explicitly whether the campaign is known at all, so "unknown" can
    # never be read as "прямой заход" (FR-024).
    "campaign_label_state",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
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
            # The way in: ``oauth_provider`` for an external provider and
            # ``email_code`` for the embedded cabinet signing in by an emailed
            # code. Keeping them apart is the point of the field, so a new way in
            # must add its own value rather than reuse the provider one.
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
            # Named for what it is: the event is sent by the desktop app too, and
            # a bare ``source`` would sit next to the campaign labels of FR-018
            # and be read as the channel the person came from.
            "autorecord_source",
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


# Level 1 signals of feature 273. They describe the anonymous page aggregate:
# dimensions plus a visit counter, no identifier and no provider delivery. They
# deliberately live outside ACTIVATION_EVENT_CATALOG, because that catalog is
# the provider contract and every entry there may be sent to a provider.
ANONYMOUS_AGGREGATE_SIGNAL_NAMES = (
    "public_page_view_aggregate",
    "public_source_aggregate",
    "public_installer_download_aggregate",
    "public_consent_share_aggregate",
)

ANONYMOUS_AGGREGATE_DELIVERY_MODE = "anonymous_aggregate"

_ANONYMOUS_AGGREGATE_IDENTITY_RULE = (
    "no identifiers: only coarse dimensions and a visit counter are stored"
)

# ``allowed_fields`` is the allowlist of the aggregate itself (data-model.md,
# level 1), reused instead of copied: device address, session or visit
# identifier, user-agent string, device fingerprint and any pseudonym are absent
# from it, and the forbidden list below stays the single source of truth.
ANONYMOUS_AGGREGATE_SIGNAL_CATALOG: dict[str, ActivationEventDefinition] = {
    "public_page_view_aggregate": ActivationEventDefinition(
        event_name="public_page_view_aggregate",
        surface="public_web",
        owner="public_web",
        posthog_destination="none",
        yandex_destination="none",
        allowed_fields=ANONYMOUS_AGGREGATE_ALLOWED_FIELDS,
        delivery_mode=ANONYMOUS_AGGREGATE_DELIVERY_MODE,
        identity_rule=_ANONYMOUS_AGGREGATE_IDENTITY_RULE,
        retention_category="anonymous_page_aggregate",
        dashboard_owner="product_analytics_growth",
        reason="Count public page visits without any identifier of the visitor.",
    ),
    "public_source_aggregate": ActivationEventDefinition(
        event_name="public_source_aggregate",
        surface="public_web",
        owner="public_web",
        posthog_destination="none",
        yandex_destination="none",
        allowed_fields=ANONYMOUS_AGGREGATE_ALLOWED_FIELDS,
        delivery_mode=ANONYMOUS_AGGREGATE_DELIVERY_MODE,
        identity_rule=_ANONYMOUS_AGGREGATE_IDENTITY_RULE,
        retention_category="anonymous_page_aggregate",
        dashboard_owner="product_analytics_growth",
        reason="Split public visits by campaign label and referrer category only.",
    ),
    "public_installer_download_aggregate": ActivationEventDefinition(
        event_name="public_installer_download_aggregate",
        surface="public_web",
        owner="public_web",
        posthog_destination="none",
        yandex_destination="none",
        allowed_fields=ANONYMOUS_AGGREGATE_ALLOWED_FIELDS,
        delivery_mode=ANONYMOUS_AGGREGATE_DELIVERY_MODE,
        identity_rule=_ANONYMOUS_AGGREGATE_IDENTITY_RULE,
        retention_category="anonymous_page_aggregate",
        dashboard_owner="product_analytics_growth",
        reason="Count installer downloads on the public download page as a counter only.",
    ),
    "public_consent_share_aggregate": ActivationEventDefinition(
        event_name="public_consent_share_aggregate",
        surface="public_web",
        owner="public_web",
        posthog_destination="none",
        yandex_destination="none",
        allowed_fields=ANONYMOUS_AGGREGATE_ALLOWED_FIELDS,
        delivery_mode=ANONYMOUS_AGGREGATE_DELIVERY_MODE,
        identity_rule=_ANONYMOUS_AGGREGATE_IDENTITY_RULE,
        retention_category="anonymous_page_aggregate",
        dashboard_owner="product_analytics_growth",
        reason="Report the share of visitors who gave consent without identifying them.",
    ),
}


def anonymous_aggregate_signal_names() -> tuple[str, ...]:
    return ANONYMOUS_AGGREGATE_SIGNAL_NAMES


def get_anonymous_aggregate_signal(event_name: str) -> ActivationEventDefinition:
    try:
        return ANONYMOUS_AGGREGATE_SIGNAL_CATALOG[event_name]
    except KeyError as exc:
        raise ValueError(f"unknown anonymous aggregate signal: {event_name}") from exc


def anonymous_aggregate_signals_payload() -> list[dict[str, object]]:
    return [definition.as_dict() for definition in ANONYMOUS_AGGREGATE_SIGNAL_CATALOG.values()]


def aggregate_signal_delivers_to_provider(event_name: str) -> bool:
    """Level 1 never sends anything to a provider; fail closed for unknown names."""
    definition = ANONYMOUS_AGGREGATE_SIGNAL_CATALOG.get(event_name)
    if definition is None:
        return False
    return (
        definition.posthog_destination != "none"
        or definition.yandex_destination != "none"
        or definition.delivery_mode != ANONYMOUS_AGGREGATE_DELIVERY_MODE
    )
