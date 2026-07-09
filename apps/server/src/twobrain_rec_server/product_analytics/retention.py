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


@dataclass(frozen=True, slots=True)
class ProviderLifecycleRecord:
    provider: str
    data_class: str
    storage_location: str
    retention_days: int
    deletion_scope: str
    backup_behavior: str
    export_policy: str
    dashboard_caveat: str
    evidence_state: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "data_class": self.data_class,
            "storage_location": self.storage_location,
            "retention_days": self.retention_days,
            "deletion_scope": self.deletion_scope,
            "backup_behavior": self.backup_behavior,
            "export_policy": self.export_policy,
            "dashboard_caveat": self.dashboard_caveat,
            "evidence_state": self.evidence_state,
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

PROVIDER_LIFECYCLE_RECORDS: tuple[ProviderLifecycleRecord, ...] = (
    ProviderLifecycleRecord(
        "posthog",
        "activation_event",
        "self_hosted_posthog_workspace",
        90,
        "provider_operator_action",
        "retained_until_backup_expiry",
        "metadata_only_or_provider_internal",
        "Deletion is handled through PostHog operator action where supported; aggregate cohorts may remain.",
        "documented",
    ),
    ProviderLifecycleRecord(
        "posthog",
        "autocapture_event",
        "self_hosted_posthog_workspace",
        90,
        "provider_operator_action",
        "retained_until_backup_expiry",
        "provider_internal_only",
        "Autocapture may contain first-party product behavior inside PostHog; committed evidence stays metadata-only.",
        "documented",
    ),
    ProviderLifecycleRecord(
        "posthog",
        "replay_recording",
        "not_collected_by_default",
        90,
        "not_collected",
        "not_applicable_until_enabled",
        "forbidden_until_page_proof",
        "Replay is disabled by default and needs separate masking/storage/legal/QA proof.",
        "documented",
    ),
    ProviderLifecycleRecord(
        "posthog",
        "backup",
        "posthog_backup_target",
        90,
        "provider_operator_action",
        "retained_until_backup_expiry",
        "forbidden_content_bearing_export",
        "Backups may retain provider data until expiry and are not committed as evidence.",
        "documented",
    ),
    ProviderLifecycleRecord(
        "yandex_metrica",
        "page_event",
        "yandex_counter",
        90,
        "not_promised",
        "provider_controlled",
        "dashboard_aggregate",
        "GRAF deletion does not promise universal erasure from Yandex aggregate reports.",
        "documented",
    ),
    ProviderLifecycleRecord(
        "yandex_metrica",
        "offline_conversion",
        "yandex_counter_offline_conversion_store",
        90,
        "not_promised",
        "provider_controlled",
        "dashboard_aggregate",
        "GRAF can stop future uploads, but already uploaded offline conversions may remain in aggregate reports.",
        "documented",
    ),
    ProviderLifecycleRecord(
        "yandex_metrica",
        "provider_aggregate",
        "yandex_reports",
        90,
        "aggregate_only",
        "provider_controlled",
        "dashboard_aggregate",
        "Campaign and attribution aggregates are provider-held and must carry deletion caveats.",
        "documented",
    ),
    ProviderLifecycleRecord(
        "graf_metadata",
        "delivery_gap_record",
        "graf_metadata_store_or_evidence",
        90,
        "deleteable_by_graf",
        "retained_until_backup_expiry",
        "metadata_only",
        "Delivery gaps contain safe buckets and caveats only.",
        "documented",
    ),
    ProviderLifecycleRecord(
        "graf_metadata",
        "dashboard_evidence",
        "committed_metadata_only_evidence",
        90,
        "deleteable_by_graf",
        "git_history_limited",
        "metadata_only",
        "Committed evidence must not contain raw provider payloads or visitor/account data.",
        "documented",
    ),
)


def retention_rules() -> tuple[AnalyticsRetentionRule, ...]:
    return RETENTION_RULES


def provider_lifecycle_records() -> tuple[ProviderLifecycleRecord, ...]:
    return PROVIDER_LIFECYCLE_RECORDS


def retention_rule(category: str) -> AnalyticsRetentionRule:
    for rule in RETENTION_RULES:
        if rule.category == category:
            return rule
    raise ValueError(f"unknown analytics retention category: {category}")
