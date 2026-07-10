from twobrain_rec_server.product_analytics.event_catalog import (
    FULL_ACTIVATION_FUNNEL,
    YANDEX_OFFLINE_CONVERSION_EVENTS,
    event_names,
    get_event_definition,
)
from twobrain_rec_server.product_analytics.page_inventory import (
    approved_provider_page_classes,
    blocked_page_classes,
    get_page_class_policy,
    page_class_policies,
)
from twobrain_rec_server.product_analytics.replay_masking import replay_decision_for_policy
from twobrain_rec_server.product_analytics.retention import retention_rule, retention_rules
from twobrain_rec_server.product_analytics.yandex_offline import is_yandex_offline_event_allowed


def test_activation_event_catalog_has_stable_order_and_owners() -> None:
    assert FULL_ACTIVATION_FUNNEL == (
        "public_installer_download_clicked",
        "desktop_first_opened",
        "desktop_account_connected",
        "desktop_autorecord_enabled",
        "first_recording_completed",
        "first_result_viewed",
        "first_value_session_completed",
    )
    assert event_names() == (
        "desktop_first_opened",
        "desktop_account_connected",
        "desktop_autorecord_enabled",
        "first_recording_completed",
        "first_result_viewed",
        "first_value_session_completed",
    )
    assert get_event_definition("desktop_first_opened").owner == "desktop"
    assert get_event_definition("desktop_account_connected").owner == "auth_server"
    assert get_event_definition("first_result_viewed").owner == "cabinet"
    assert get_event_definition("first_value_session_completed").owner == "product_analytics"


def test_activation_event_catalog_forbids_private_and_content_fields() -> None:
    for event_name in event_names():
        definition = get_event_definition(event_name)
        assert "email" in definition.forbidden_fields
        assert "meeting_title" in definition.forbidden_fields
        assert "transcript" in definition.forbidden_fields
        assert "raw_audio" in definition.forbidden_fields
        assert "local_file_path" in definition.forbidden_fields
        assert "signed_url" in definition.forbidden_fields


def test_yandex_offline_conversion_subset_is_default_limited() -> None:
    assert YANDEX_OFFLINE_CONVERSION_EVENTS == (
        "desktop_account_connected",
        "first_value_session_completed",
    )
    assert is_yandex_offline_event_allowed("desktop_account_connected") is True
    assert is_yandex_offline_event_allowed("first_value_session_completed") is True
    assert is_yandex_offline_event_allowed("desktop_first_opened") is False
    assert is_yandex_offline_event_allowed("first_recording_completed") is False


def test_yandex_all_pages_inventory_has_approved_blocked_and_replay_unavailable_classes() -> None:
    policy_names = {policy.page_class for policy in page_class_policies()}

    assert {"public_landing", "public_download", "cabinet_home", "admin", "auth_callback"} <= policy_names
    assert approved_provider_page_classes() == ("public_landing", "public_download")
    assert "admin" in blocked_page_classes()
    assert get_page_class_policy("auth_callback").launch_state == "blocked"
    assert get_page_class_policy("cabinet_home").launch_state == "replay_unavailable"
    assert get_page_class_policy("cabinet_home").posthog_replay_allowed is False
    assert get_page_class_policy("cabinet_home").yandex_webvisor_allowed is False


def test_replay_disabled_states_have_private_masking_attributes() -> None:
    decision = replay_decision_for_policy(get_page_class_policy("meeting_result_detail"))

    assert decision.launch_state == "replay_unavailable"
    assert decision.replay_allowed is False
    assert decision.attributes["data-ph-no-capture"] == "true"
    assert decision.attributes["data-ym-hide-content"] == "true"
    assert decision.attributes["data-ym-disable-keys"] == "true"


def test_retention_contract_uses_minimum_ninety_days_and_deletion_truth() -> None:
    categories = {rule.category for rule in retention_rules()}

    assert "attribution_bridge" in categories
    assert "posthog_product_events" in categories
    assert "yandex_offline_conversions" in categories
    assert "delivery_gap" in categories
    assert all(rule.minimum_retention_days >= 90 for rule in retention_rules())
    assert retention_rule("attribution_bridge").maximum_retention_days == 90
    assert retention_rule("yandex_page_events").delete_on_user_request == "manual_process"
