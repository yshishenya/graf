from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AnalyticsRetentionRule:
    category: str
    minimum_retention_days: int
    maximum_retention_days: int | None
    delete_on_user_request: str
    provider_delete_method: str
    deletion_truth: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "minimum_retention_days": self.minimum_retention_days,
            "maximum_retention_days": self.maximum_retention_days,
            "delete_on_user_request": self.delete_on_user_request,
            "provider_delete_method": self.provider_delete_method,
            "deletion_truth": self.deletion_truth,
        }


RETENTION_RULES: tuple[AnalyticsRetentionRule, ...] = (
    AnalyticsRetentionRule(
        "attribution_bridge",
        90,
        90,
        "graf_controlled",
        "purge bridge row/token hash in GRAF storage",
        "Campaign link can be removed; aggregate reports may remain.",
    ),
    AnalyticsRetentionRule(
        "posthog_product_events",
        90,
        90,
        "provider_supported",
        "PostHog person/event deletion for stable pseudonymous identity where supported",
        "Raw GRAF identity is not present; aggregate cohorts may remain.",
    ),
    AnalyticsRetentionRule(
        "posthog_session_replay",
        90,
        90,
        "provider_supported",
        "PostHog recording deletion for stable pseudonymous identity/session where supported",
        "Replay must be masked; aggregate replay metrics may remain.",
    ),
    AnalyticsRetentionRule(
        "yandex_page_events",
        90,
        None,
        "manual_process",
        "Yandex counter/user-data deletion process where available",
        "GRAF must not promise universal erasure from Yandex aggregate reports.",
    ),
    AnalyticsRetentionRule(
        "yandex_webvisor",
        90,
        90,
        "manual_process",
        "Yandex Webvisor/session deletion process where available",
        "Unapproved page classes keep Webvisor off.",
    ),
    AnalyticsRetentionRule(
        "yandex_offline_conversions",
        90,
        90,
        "manual_process",
        "remove queued uploads in GRAF; request/provider process for uploaded conversions",
        "Uploaded ad conversions may remain in aggregate ad reports.",
    ),
    AnalyticsRetentionRule(
        "delivery_gap",
        90,
        90,
        "graf_controlled",
        "purge safe gap row in GRAF storage",
        "Gaps contain only safe buckets and caveats.",
    ),
    AnalyticsRetentionRule(
        "exported_report",
        90,
        90,
        "manual_process",
        "delete/redact exported report files controlled by GRAF",
        "Reports outside GRAF control are outside direct erasure control.",
    ),
)


def retention_rules() -> tuple[AnalyticsRetentionRule, ...]:
    return RETENTION_RULES


def retention_rule(category: str) -> AnalyticsRetentionRule:
    for rule in RETENTION_RULES:
        if rule.category == category:
            return rule
    raise ValueError(f"unknown analytics retention category: {category}")
