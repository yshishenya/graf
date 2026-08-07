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
        "billing_overview",
        "billing_plans",
        "billing_discounts",
        "billing_checkout_status",
        "billing_usage",
        "billing_subscription",
        "billing_payment_method",
        "billing_storage_addons",
        "billing_checkout",
        "billing_history",
        "billing_invoice",
        "billing_referrals",
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


def test_posthog_autocapture_excludes_financial_page_classes() -> None:
    policies = page_class_policies()
    financial_policies = tuple(policy for policy in policies if policy.sensitivity == "financial")
    non_financial_policies = tuple(policy for policy in policies if policy.sensitivity != "financial")

    assert posthog_autocapture_page_classes() == tuple(policy.page_class for policy in non_financial_policies)
    assert all(policy.posthog_autocapture_state == "enabled" for policy in non_financial_policies)
    assert all(policy.posthog_autocapture_state == "disabled" for policy in financial_policies)
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


def test_financial_pages_are_fail_closed_for_browser_analytics() -> None:
    expected = {
        "billing_overview",
        "billing_plans",
        "billing_discounts",
        "billing_checkout_status",
        "billing_usage",
        "billing_subscription",
        "billing_payment_method",
        "billing_storage_addons",
        "billing_checkout",
        "billing_history",
        "billing_invoice",
        "billing_referrals",
    }
    policies = {
        policy.page_class: policy
        for policy in page_class_policies()
        if policy.sensitivity == "financial"
    }

    assert set(policies) == expected
    assert expected <= set(blocked_yandex_page_classes())
    for policy in policies.values():
        assert policy.launch_state == "analytics_disabled"
        assert policy.posthog_autocapture_state == "disabled"
        assert policy.page_view_allowed is False
        assert policy.safe_event_allowed is True
        assert policy.posthog_replay_allowed is False
        assert policy.yandex_webvisor_allowed is False
        assert policy.click_map_allowed is False
        assert policy.scroll_map_allowed is False
        assert policy.form_analytics_allowed is False
        assert policy.url_title_referrer_status == "blocked"
        assert policy.rollback_behavior == "financial_analytics_disabled"
