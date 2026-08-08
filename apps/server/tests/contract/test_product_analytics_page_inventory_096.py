from twobrain_rec_server.product_analytics.page_inventory import (
    blocked_yandex_page_classes,
    page_class_policies,
    posthog_autocapture_page_classes,
    yandex_approved_page_classes,
)


def test_096_inventory_covers_all_current_and_future_browser_page_classes() -> None:
    policy_names = {policy.page_class for policy in page_class_policies()}

    assert {
        "public_landing",
        "public_download",
        "legal",
        "login_signup",
        "auth_callback",
        "cabinet_home",
        "onboarding",
        "settings",
        "recording_list",
        "meeting_result_detail",
        "upload",
        "playback",
        "deletion",
        "admin",
        "embedded_desktop_webview",
        "error_pages",
        "future_browser_page",
    } <= policy_names


def test_posthog_autocapture_is_enabled_for_all_browser_page_classes() -> None:
    policies = page_class_policies()

    assert posthog_autocapture_page_classes() == tuple(policy.page_class for policy in policies)
    assert all(policy.posthog_autocapture_state == "enabled" for policy in policies)
    assert all(policy.credential_suppression for policy in policies)
    assert all("oauth_codes" in policy.credential_suppression for policy in policies)
    assert all(policy.posthog_replay_allowed is False for policy in policies)


def test_yandex_preserves_093_public_scope_and_blocks_high_risk_pages() -> None:
    assert yandex_approved_page_classes() == ("public_landing", "public_download")

    blocked = set(blocked_yandex_page_classes())
    assert "auth_callback" in blocked
    assert "admin" in blocked
    assert "deletion" in blocked
    assert "future_browser_page" in blocked

    policy_by_name = {policy.page_class: policy for policy in page_class_policies()}
    assert policy_by_name["meeting_result_detail"].yandex_state == "replay_unavailable"
    assert policy_by_name["embedded_desktop_webview"].yandex_state == "replay_unavailable"
    assert policy_by_name["future_browser_page"].dashboard_purpose == "blocked_until_inventory_approval"
    assert policy_by_name["future_browser_page"].rollback_behavior == "yandex_blocked_by_default"
