from __future__ import annotations

from dataclasses import dataclass

DEFAULT_CREDENTIAL_SUPPRESSION = (
    "passwords",
    "passcodes",
    "oauth_codes",
    "access_refresh_id_tokens",
    "api_keys",
    "signed_urls",
    "cookies",
    "provider_client_secrets",
    "private_keys",
    "local_paths",
    "raw_payload_dumps",
)


@dataclass(frozen=True, slots=True)
class PageClassAnalyticsPolicy:
    page_class: str
    examples: tuple[str, ...]
    tag_allowed: bool
    page_view_allowed: bool
    safe_event_allowed: bool
    posthog_replay_allowed: bool
    yandex_webvisor_allowed: bool
    click_map_allowed: bool
    scroll_map_allowed: bool
    form_analytics_allowed: bool
    launch_state: str
    url_title_referrer_status: str
    masking_contract_status: str
    legal_status: str
    dashboard_caveat: str
    posthog_autocapture_state: str
    posthog_replay_state: str
    yandex_state: str
    credential_suppression: tuple[str, ...]
    sensitivity: str
    expected_product_visible_data: str
    qa_status: str
    dashboard_purpose: str
    rollback_behavior: str

    def as_dict(self) -> dict[str, object]:
        return {
            "page_class": self.page_class,
            "examples": list(self.examples),
            "tag_allowed": self.tag_allowed,
            "page_view_allowed": self.page_view_allowed,
            "safe_event_allowed": self.safe_event_allowed,
            "posthog_replay_allowed": self.posthog_replay_allowed,
            "yandex_webvisor_allowed": self.yandex_webvisor_allowed,
            "click_map_allowed": self.click_map_allowed,
            "scroll_map_allowed": self.scroll_map_allowed,
            "form_analytics_allowed": self.form_analytics_allowed,
            "launch_state": self.launch_state,
            "url_title_referrer_status": self.url_title_referrer_status,
            "masking_contract_status": self.masking_contract_status,
            "legal_status": self.legal_status,
            "dashboard_caveat": self.dashboard_caveat,
            "posthog_autocapture_state": self.posthog_autocapture_state,
            "posthog_replay_state": self.posthog_replay_state,
            "yandex_state": self.yandex_state,
            "credential_suppression": list(self.credential_suppression),
            "sensitivity": self.sensitivity,
            "expected_product_visible_data": self.expected_product_visible_data,
            "qa_status": self.qa_status,
            "dashboard_purpose": self.dashboard_purpose,
            "rollback_behavior": self.rollback_behavior,
        }


def _policy(
    page_class: str,
    examples: tuple[str, ...],
    *,
    yandex_state: str,
    sensitivity: str,
    dashboard_purpose: str,
    launch_state: str | None = None,
    url_title_referrer_status: str = "needs_sanitization",
    legal_status: str = "in_review",
    qa_status: str = "pending",
    expected_product_visible_data: str = "product-visible interaction metadata",
    rollback_behavior: str = "disable_posthog_or_yandex_runtime_flags",
    dashboard_caveat: str = "PostHog autocapture is first-party; Yandex/replay remain separately gated.",
    posthog_autocapture_state: str = "enabled",
    page_view_allowed: bool = True,
    safe_event_allowed: bool = True,
) -> PageClassAnalyticsPolicy:
    yandex_approved = yandex_state == "approved_page_view_event"
    resolved_launch_state = launch_state or ("replay_allowed" if yandex_approved else yandex_state)
    return PageClassAnalyticsPolicy(
        page_class=page_class,
        examples=examples,
        tag_allowed=yandex_approved,
        page_view_allowed=page_view_allowed,
        safe_event_allowed=safe_event_allowed,
        posthog_replay_allowed=False,
        yandex_webvisor_allowed=False,
        click_map_allowed=False,
        scroll_map_allowed=False,
        form_analytics_allowed=False,
        launch_state=resolved_launch_state,
        url_title_referrer_status=url_title_referrer_status,
        masking_contract_status="replay_unavailable" if yandex_state == "replay_unavailable" else "blocked",
        legal_status=legal_status,
        dashboard_caveat=dashboard_caveat,
        posthog_autocapture_state=posthog_autocapture_state,
        posthog_replay_state="disabled" if yandex_state != "replay_unavailable" else "unavailable",
        yandex_state=yandex_state,
        credential_suppression=DEFAULT_CREDENTIAL_SUPPRESSION,
        sensitivity=sensitivity,
        expected_product_visible_data=expected_product_visible_data,
        qa_status=qa_status,
        dashboard_purpose=dashboard_purpose,
        rollback_behavior=rollback_behavior,
    )


DEFAULT_PAGE_CLASS_POLICIES: tuple[PageClassAnalyticsPolicy, ...] = (
    _policy(
        "public_landing",
        ("/",),
        yandex_state="approved_page_view_event",
        sensitivity="public",
        dashboard_purpose="acquisition",
        url_title_referrer_status="safe",
        legal_status="approved_public_093",
        qa_status="passed_public_093",
        expected_product_visible_data="public acquisition page behavior",
        rollback_behavior="preserve_093_or_disable_public_runtime_flag",
        dashboard_caveat="Existing 093 public landing scope remains approved.",
    ),
    _policy(
        "public_download",
        ("/download",),
        yandex_state="approved_page_view_event",
        sensitivity="public",
        dashboard_purpose="acquisition",
        url_title_referrer_status="safe",
        legal_status="approved_public_093",
        qa_status="passed_public_093",
        expected_product_visible_data="public installer/download intent",
        rollback_behavior="preserve_093_or_disable_public_runtime_flag",
        dashboard_caveat="Existing 093 download goal remains approved.",
    ),
    _policy(
        "legal",
        ("/privacy", "/cookies", "/terms", "/analytics-consent"),
        yandex_state="blocked",
        sensitivity="public",
        dashboard_purpose="legal_review",
        expected_product_visible_data="legal page navigation only",
    ),
    _policy(
        "login_signup",
        ("/login", "/sign-up"),
        yandex_state="blocked",
        sensitivity="auth",
        dashboard_purpose="product_onboarding",
        expected_product_visible_data="auth flow interaction metadata without credentials",
        dashboard_caveat="Credential fields must be suppressed before PostHog autocapture evidence can pass.",
    ),
    _policy(
        "auth_callback",
        ("/api/v1/auth/callback/*",),
        yandex_state="blocked",
        sensitivity="auth",
        dashboard_purpose="blocked_until_callback_sanitization",
        launch_state="blocked",
        url_title_referrer_status="blocked",
        legal_status="blocked",
        qa_status="blocked",
        expected_product_visible_data="callback success/failure metadata only",
        rollback_behavior="yandex_blocked_by_default",
        dashboard_caveat="OAuth codes, state, cookies, and errors must be suppressed.",
    ),
    _policy(
        "cabinet_home",
        ("/cabinet", "/meetings"),
        yandex_state="replay_unavailable",
        sensitivity="product",
        dashboard_purpose="product_activation",
        expected_product_visible_data="cabinet navigation and empty/non-empty product state",
        dashboard_caveat="Workspace/account names and meeting content stay out of Yandex/evidence.",
    ),
    _policy(
        "onboarding",
        ("/cabinet/onboarding", "/telemetry-gate"),
        yandex_state="blocked",
        sensitivity="product",
        dashboard_purpose="product_onboarding",
        expected_product_visible_data="telemetry gate and setup state interactions",
    ),
    _policy(
        "settings",
        ("/settings", "/cabinet/settings"),
        yandex_state="replay_unavailable",
        sensitivity="product",
        dashboard_purpose="product_settings",
        expected_product_visible_data="settings navigation and toggle interaction metadata",
    ),
    _policy(
        "billing_overview",
        ("/billing",),
        yandex_state="blocked",
        sensitivity="financial",
        dashboard_purpose="billing_safe_events_only",
        launch_state="analytics_disabled",
        url_title_referrer_status="blocked",
        legal_status="financial_pages_blocked",
        qa_status="fail_closed",
        expected_product_visible_data="none until a billing-safe event allowlist is approved",
        rollback_behavior="financial_analytics_disabled",
        dashboard_caveat="Amounts, payment state, promo codes, referral tokens, invoices, and provider data are forbidden.",
        posthog_autocapture_state="disabled",
        page_view_allowed=False,
    ),
    _policy(
        "billing_usage",
        ("/billing/usage",),
        yandex_state="blocked",
        sensitivity="financial",
        dashboard_purpose="billing_safe_events_only",
        launch_state="analytics_disabled",
        url_title_referrer_status="blocked",
        legal_status="financial_pages_blocked",
        qa_status="fail_closed",
        expected_product_visible_data="none until a billing-safe event allowlist is approved",
        rollback_behavior="financial_analytics_disabled",
        dashboard_caveat="Usage quantities and quota state are forbidden until separately approved.",
        posthog_autocapture_state="disabled",
        page_view_allowed=False,
    ),
    _policy(
        "billing_subscription",
        ("/billing/subscription",),
        yandex_state="blocked",
        sensitivity="financial",
        dashboard_purpose="billing_safe_events_only",
        launch_state="analytics_disabled",
        url_title_referrer_status="blocked",
        legal_status="financial_pages_blocked",
        qa_status="fail_closed",
        expected_product_visible_data="none until a billing-safe event allowlist is approved",
        rollback_behavior="financial_analytics_disabled",
        dashboard_caveat="Subscription state and renewal dates are forbidden until separately approved.",
        posthog_autocapture_state="disabled",
        page_view_allowed=False,
    ),
    _policy(
        "billing_payment_method",
        ("/billing/payment-method",),
        yandex_state="blocked",
        sensitivity="financial",
        dashboard_purpose="billing_safe_events_only",
        launch_state="analytics_disabled",
        url_title_referrer_status="blocked",
        legal_status="financial_pages_blocked",
        qa_status="fail_closed",
        expected_product_visible_data="none until a billing-safe event allowlist is approved",
        rollback_behavior="financial_analytics_disabled",
        dashboard_caveat="Payment method metadata and provider redirects are forbidden.",
        posthog_autocapture_state="disabled",
        page_view_allowed=False,
    ),
    _policy(
        "billing_storage_addons",
        ("/billing/storage",),
        yandex_state="blocked",
        sensitivity="financial",
        dashboard_purpose="billing_safe_events_only",
        launch_state="analytics_disabled",
        url_title_referrer_status="blocked",
        legal_status="financial_pages_blocked",
        qa_status="fail_closed",
        expected_product_visible_data="none until a billing-safe event allowlist is approved",
        rollback_behavior="financial_analytics_disabled",
        dashboard_caveat="Purchased storage quantities and prices are forbidden.",
        posthog_autocapture_state="disabled",
        page_view_allowed=False,
    ),
    _policy(
        "billing_checkout",
        ("/billing/checkout",),
        yandex_state="blocked",
        sensitivity="financial",
        dashboard_purpose="billing_safe_events_only",
        launch_state="analytics_disabled",
        url_title_referrer_status="blocked",
        legal_status="financial_pages_blocked",
        qa_status="fail_closed",
        expected_product_visible_data="none until a billing-safe event allowlist is approved",
        rollback_behavior="financial_analytics_disabled",
        dashboard_caveat="Amounts, consent state, promo codes, idempotency keys, and provider redirects are forbidden.",
        posthog_autocapture_state="disabled",
        page_view_allowed=False,
    ),
    _policy(
        "billing_history",
        ("/billing/history",),
        yandex_state="blocked",
        sensitivity="financial",
        dashboard_purpose="billing_safe_events_only",
        launch_state="analytics_disabled",
        url_title_referrer_status="blocked",
        legal_status="financial_pages_blocked",
        qa_status="fail_closed",
        expected_product_visible_data="none until a billing-safe event allowlist is approved",
        rollback_behavior="financial_analytics_disabled",
        dashboard_caveat="Invoice numbers, payment status, amounts, and receipt links are forbidden.",
        posthog_autocapture_state="disabled",
        page_view_allowed=False,
    ),
    _policy(
        "billing_invoice",
        ("/billing/invoices/{safe_number}",),
        yandex_state="blocked",
        sensitivity="financial",
        dashboard_purpose="billing_safe_events_only",
        launch_state="analytics_disabled",
        url_title_referrer_status="blocked",
        legal_status="financial_pages_blocked",
        qa_status="fail_closed",
        expected_product_visible_data="none until a billing-safe event allowlist is approved",
        rollback_behavior="financial_analytics_disabled",
        dashboard_caveat="Invoice numbers, payment status, amounts, receipt links and support email drafts are forbidden.",
        posthog_autocapture_state="disabled",
        page_view_allowed=False,
    ),
    _policy(
        "billing_referrals",
        ("/billing/referrals",),
        yandex_state="blocked",
        sensitivity="financial",
        dashboard_purpose="billing_safe_events_only",
        launch_state="analytics_disabled",
        url_title_referrer_status="blocked",
        legal_status="financial_pages_blocked",
        qa_status="fail_closed",
        expected_product_visible_data="none until a billing-safe event allowlist is approved",
        rollback_behavior="financial_analytics_disabled",
        dashboard_caveat="Referral tokens, attribution, reward state, and balances are forbidden.",
        posthog_autocapture_state="disabled",
        page_view_allowed=False,
    ),
    _policy(
        "recording_list",
        ("/meetings", "/recordings"),
        yandex_state="replay_unavailable",
        sensitivity="meeting",
        dashboard_purpose="product_activation",
        expected_product_visible_data="list interaction metadata without meeting titles",
    ),
    _policy(
        "meeting_result_detail",
        ("/meetings/{id}", "/desktop/meetings/{id}"),
        yandex_state="replay_unavailable",
        sensitivity="meeting",
        dashboard_purpose="product_activation",
        expected_product_visible_data="review interaction metadata without transcript/audio/title",
        dashboard_caveat="Meeting content may be first-party PostHog behavior only; Yandex/replay remain unavailable.",
    ),
    _policy(
        "upload",
        ("/upload",),
        yandex_state="replay_unavailable",
        sensitivity="product",
        dashboard_purpose="product_activation",
        expected_product_visible_data="upload flow progress and outcome metadata",
        dashboard_caveat="Filenames, local paths, signed URLs, and object keys are forbidden.",
    ),
    _policy(
        "playback",
        ("/meetings/{id}/playback",),
        yandex_state="replay_unavailable",
        sensitivity="meeting",
        dashboard_purpose="product_activation",
        expected_product_visible_data="playback control interaction metadata without raw audio",
    ),
    _policy(
        "deletion",
        ("/deletion", "/meetings/{id}/deletion"),
        yandex_state="blocked",
        sensitivity="product",
        dashboard_purpose="deletion_truth",
        expected_product_visible_data="deletion report interaction metadata",
        rollback_behavior="yandex_blocked_by_default",
        dashboard_caveat="Deletion truth is sensitive; Yandex is blocked by default.",
    ),
    _policy(
        "admin",
        ("/admin/*",),
        yandex_state="blocked",
        sensitivity="admin",
        dashboard_purpose="blocked_internal_admin",
        launch_state="blocked",
        url_title_referrer_status="blocked",
        legal_status="blocked",
        qa_status="blocked",
        expected_product_visible_data="admin navigation metadata only after global suppression",
        rollback_behavior="yandex_blocked_by_default",
        dashboard_caveat="Admin pages are PostHog first-party only after credential suppression; Yandex remains blocked.",
    ),
    _policy(
        "embedded_desktop_webview",
        ("/desktop/*",),
        yandex_state="replay_unavailable",
        sensitivity="embedded",
        dashboard_purpose="desktop_product_activation",
        expected_product_visible_data="embedded cabinet interaction metadata",
    ),
    _policy(
        "error_pages",
        ("4xx", "5xx"),
        yandex_state="blocked",
        sensitivity="error",
        dashboard_purpose="diagnostic",
        expected_product_visible_data="error page class and non-secret status metadata",
        dashboard_caveat="No stack traces, request IDs, private URLs, or secrets in provider payloads.",
    ),
    _policy(
        "future_browser_page",
        ("future browser-rendered routes",),
        yandex_state="blocked",
        sensitivity="future",
        dashboard_purpose="blocked_until_inventory_approval",
        expected_product_visible_data="future page interaction metadata after global suppression",
        rollback_behavior="yandex_blocked_by_default",
        dashboard_caveat="Future pages inherit PostHog autocapture but Yandex remains blocked until inventory approval.",
    ),
)


def page_class_policies() -> tuple[PageClassAnalyticsPolicy, ...]:
    return DEFAULT_PAGE_CLASS_POLICIES


def get_page_class_policy(page_class: str) -> PageClassAnalyticsPolicy:
    aliases = {"legal_pages": "legal"}
    normalized = aliases.get(page_class, page_class)
    for policy in DEFAULT_PAGE_CLASS_POLICIES:
        if policy.page_class == normalized:
            return policy
    raise ValueError(f"unknown page class: {page_class}")


def approved_provider_page_classes() -> tuple[str, ...]:
    return yandex_approved_page_classes()


def yandex_approved_page_classes() -> tuple[str, ...]:
    return tuple(policy.page_class for policy in DEFAULT_PAGE_CLASS_POLICIES if policy.yandex_state == "approved_page_view_event")


def blocked_page_classes() -> tuple[str, ...]:
    return tuple(policy.page_class for policy in DEFAULT_PAGE_CLASS_POLICIES if policy.launch_state == "blocked")


def blocked_yandex_page_classes() -> tuple[str, ...]:
    return tuple(policy.page_class for policy in DEFAULT_PAGE_CLASS_POLICIES if policy.yandex_state == "blocked")


def posthog_autocapture_page_classes() -> tuple[str, ...]:
    return tuple(policy.page_class for policy in DEFAULT_PAGE_CLASS_POLICIES if policy.posthog_autocapture_state == "enabled")
