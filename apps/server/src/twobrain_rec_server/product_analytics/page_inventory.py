from __future__ import annotations

from dataclasses import dataclass


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
        }


DEFAULT_PAGE_CLASS_POLICIES: tuple[PageClassAnalyticsPolicy, ...] = (
    PageClassAnalyticsPolicy(
        "public_landing",
        ("/",),
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        False,
        "replay_allowed",
        "safe",
        "passed_public_093",
        "approved_public_093",
        "Live only for 093 public scope until 094 rollout.",
    ),
    PageClassAnalyticsPolicy(
        "public_download",
        ("/download",),
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        False,
        "replay_allowed",
        "safe",
        "passed_public_093",
        "approved_public_093",
        "Download intent is not product activation.",
    ),
    PageClassAnalyticsPolicy(
        "legal_pages",
        ("/terms", "/privacy", "/analytics-consent"),
        False,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        "replay_unavailable",
        "needs_sanitization",
        "replay_unavailable",
        "in_review",
        "Safe page views/events only after legal and URL/title review.",
    ),
    PageClassAnalyticsPolicy(
        "login_signup",
        ("/login", "/sign-up"),
        False,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        "replay_unavailable",
        "needs_sanitization",
        "replay_unavailable",
        "in_review",
        "No email, phone, or auth field replay.",
    ),
    PageClassAnalyticsPolicy(
        "auth_callback",
        ("/api/v1/auth/callback/*",),
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        "blocked",
        "blocked",
        "blocked",
        "blocked",
        "Provider snippets absent because callback routes can expose state/errors.",
    ),
    PageClassAnalyticsPolicy(
        "cabinet_home",
        ("/cabinet", "/meetings"),
        False,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        "replay_unavailable",
        "needs_sanitization",
        "replay_unavailable",
        "in_review",
        "Workspace/account names and meeting content stay hidden.",
    ),
    PageClassAnalyticsPolicy(
        "meeting_result_detail",
        ("/meetings/{id}", "/desktop/meetings/{id}"),
        False,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        "replay_unavailable",
        "needs_sanitization",
        "replay_unavailable",
        "in_review",
        "Transcript, summary, participants, playback, and title are never captured.",
    ),
    PageClassAnalyticsPolicy(
        "upload",
        ("/upload",),
        False,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        "replay_unavailable",
        "needs_sanitization",
        "replay_unavailable",
        "in_review",
        "Filenames, object keys, and local paths are forbidden.",
    ),
    PageClassAnalyticsPolicy(
        "deletion",
        ("/deletion", "/meetings/{id}/deletion"),
        False,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        "replay_unavailable",
        "needs_sanitization",
        "replay_unavailable",
        "in_review",
        "Deletion reports disclose provider limits without replay.",
    ),
    PageClassAnalyticsPolicy(
        "admin",
        ("/admin/*",),
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        "blocked",
        "blocked",
        "blocked",
        "blocked",
        "Admin/user/file data is too sensitive for initial 094.",
    ),
    PageClassAnalyticsPolicy(
        "embedded_desktop_webview",
        ("/desktop/*",),
        False,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        "replay_unavailable",
        "needs_sanitization",
        "replay_unavailable",
        "in_review",
        "Desktop session bridge requires separate proof.",
    ),
    PageClassAnalyticsPolicy(
        "error_pages",
        ("4xx", "5xx"),
        False,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        "blocked",
        "needs_sanitization",
        "blocked",
        "not_started",
        "No stack traces, request IDs, or private URLs in provider payloads.",
    ),
)


def page_class_policies() -> tuple[PageClassAnalyticsPolicy, ...]:
    return DEFAULT_PAGE_CLASS_POLICIES


def get_page_class_policy(page_class: str) -> PageClassAnalyticsPolicy:
    for policy in DEFAULT_PAGE_CLASS_POLICIES:
        if policy.page_class == page_class:
            return policy
    raise ValueError(f"unknown page class: {page_class}")


def approved_provider_page_classes() -> tuple[str, ...]:
    return tuple(policy.page_class for policy in DEFAULT_PAGE_CLASS_POLICIES if policy.tag_allowed)


def blocked_page_classes() -> tuple[str, ...]:
    return tuple(policy.page_class for policy in DEFAULT_PAGE_CLASS_POLICIES if policy.launch_state == "blocked")
