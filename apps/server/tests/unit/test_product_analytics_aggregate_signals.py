"""Unit contracts of the level 1 aggregate signals in the event catalog (T004)."""

import pytest

from twobrain_rec_server.product_analytics.event_catalog import (
    ACTIVATION_EVENT_CATALOG,
    ANONYMOUS_AGGREGATE_DELIVERY_MODE,
    ANONYMOUS_AGGREGATE_SIGNAL_CATALOG,
    ANONYMOUS_AGGREGATE_SIGNAL_NAMES,
    aggregate_signal_delivers_to_provider,
    anonymous_aggregate_signal_names,
    anonymous_aggregate_signals_payload,
    event_names,
    get_anonymous_aggregate_signal,
)
from twobrain_rec_server.product_analytics.forbidden_fields import (
    ANONYMOUS_AGGREGATE_ALLOWED_FIELDS,
)
from twobrain_rec_server.product_analytics.retention import retention_rule


def test_aggregate_signal_names_are_stable() -> None:
    assert ANONYMOUS_AGGREGATE_SIGNAL_NAMES == (
        "public_page_view_aggregate",
        "public_source_aggregate",
        "public_installer_download_aggregate",
        "public_consent_share_aggregate",
    )
    assert anonymous_aggregate_signal_names() == ANONYMOUS_AGGREGATE_SIGNAL_NAMES


def test_aggregate_signals_do_not_touch_the_provider_catalog() -> None:
    assert event_names() == (
        "desktop_first_opened",
        "desktop_account_connected",
        "desktop_autorecord_enabled",
        "first_recording_completed",
        "first_result_viewed",
        "first_value_session_completed",
    )
    for signal in ANONYMOUS_AGGREGATE_SIGNAL_NAMES:
        assert signal not in ACTIVATION_EVENT_CATALOG
        assert signal not in event_names()


def test_every_aggregate_signal_is_local_and_counter_only() -> None:
    for signal in ANONYMOUS_AGGREGATE_SIGNAL_NAMES:
        definition = get_anonymous_aggregate_signal(signal)

        assert definition.event_name == signal
        assert definition.posthog_destination == "none"
        assert definition.yandex_destination == "none"
        assert definition.delivery_mode == ANONYMOUS_AGGREGATE_DELIVERY_MODE
        assert definition.retention_category == "anonymous_page_aggregate"
        assert definition.owner == "public_web"
        assert definition.dashboard_owner == "product_analytics_growth"
        assert aggregate_signal_delivers_to_provider(signal) is False


def test_aggregate_signal_fields_are_the_aggregate_dimensions() -> None:
    for signal in ANONYMOUS_AGGREGATE_SIGNAL_NAMES:
        definition = get_anonymous_aggregate_signal(signal)

        assert set(definition.allowed_fields) == set(ANONYMOUS_AGGREGATE_ALLOWED_FIELDS)


def test_aggregate_signal_forbidden_fields_include_every_identifier() -> None:
    for signal in ANONYMOUS_AGGREGATE_SIGNAL_NAMES:
        forbidden = get_anonymous_aggregate_signal(signal).forbidden_fields

        for identifier in (
            "ip_address",
            "device_address",
            "session_id",
            "user_agent",
            "device_fingerprint",
            "anonymous_id",
            "email",
            "transcript",
            "raw_audio",
            "signed_url",
        ):
            assert identifier in forbidden


def test_aggregate_signal_retention_category_is_registered() -> None:
    rule = retention_rule("anonymous_page_aggregate")

    assert rule.minimum_retention_days == 1095
    assert rule.maximum_retention_days == 1095


def test_unknown_aggregate_signal_is_refused_and_never_delivers() -> None:
    with pytest.raises(ValueError):
        get_anonymous_aggregate_signal("public_secret_aggregate")

    assert aggregate_signal_delivers_to_provider("public_secret_aggregate") is False


def test_payload_is_serializable_and_free_of_identifiers() -> None:
    payload = anonymous_aggregate_signals_payload()

    assert [entry["event_name"] for entry in payload] == list(ANONYMOUS_AGGREGATE_SIGNAL_NAMES)
    for entry in payload:
        assert entry["posthog_destination"] == "none"
        assert entry["yandex_destination"] == "none"
        assert entry["identity_rule"].startswith("no identifiers")
        assert "ip_address" in entry["forbidden_fields"]


def test_signal_catalog_keys_match_the_declared_order() -> None:
    assert tuple(ANONYMOUS_AGGREGATE_SIGNAL_CATALOG) == ANONYMOUS_AGGREGATE_SIGNAL_NAMES
