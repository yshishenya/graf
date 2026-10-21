from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

RETENTION_STORAGES = (
    "clickhouse_posthog",
    "graf_postgres",
    "graf_files",
    "yandex_provider",
)
RETENTION_ENFORCEMENTS = (
    "provider_controlled",
    "decision_required",
)
# until_decision prohibits age-based deletion in GRAF-controlled storage.
GRAF_CONTROLLED_STORAGES = frozenset({"clickhouse_posthog", "graf_postgres", "graf_files"})


class AnalyticsRetentionConfigurationError(ValueError):
    """A missing or conflicting explicit retention policy is a configuration error."""


@dataclass(frozen=True, slots=True)
class AnalyticsRetentionRule:
    category: str
    minimum_retention_days: int | None
    maximum_retention_days: int | None
    delete_on_user_request: str
    provider_delete_method: str
    deletion_truth: str
    storage: str = "graf_postgres"
    enforcement: str = ""
    retention_mode: str = ""

    def __post_init__(self) -> None:
        if self.retention_mode not in ("provider_controlled", "until_decision"):
            raise AnalyticsRetentionConfigurationError("unknown analytics retention mode")
        if self.retention_mode == "until_decision":
            if (
                self.minimum_retention_days is not None
                or self.maximum_retention_days is not None
                or self.enforcement != "decision_required"
                or self.storage not in GRAF_CONTROLLED_STORAGES
            ):
                raise AnalyticsRetentionConfigurationError(
                    "until_decision conflicts with age enforcement"
                )
        else:
            if self.enforcement != "provider_controlled" or self.storage != "yandex_provider":
                raise AnalyticsRetentionConfigurationError(
                    "provider retention requires provider storage"
                )
            if self.minimum_retention_days is None or self.minimum_retention_days < 1:
                raise AnalyticsRetentionConfigurationError(
                    "bounded retention requires a positive term"
                )
            if self.maximum_retention_days is not None and (
                self.maximum_retention_days < self.minimum_retention_days
            ):
                raise AnalyticsRetentionConfigurationError("maximum retention is below its minimum")
        if self.storage not in RETENTION_STORAGES:
            raise AnalyticsRetentionConfigurationError(
                f"analytics retention category {self.category!r} has an unknown storage"
            )
        if self.enforcement not in RETENTION_ENFORCEMENTS:
            raise AnalyticsRetentionConfigurationError(
                f"analytics retention category {self.category!r} has an unknown enforcement"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "retention_mode": self.retention_mode,
            "minimum_retention_days": self.minimum_retention_days,
            "maximum_retention_days": self.maximum_retention_days,
            "delete_on_user_request": self.delete_on_user_request,
            "provider_delete_method": self.provider_delete_method,
            "deletion_truth": self.deletion_truth,
            "storage": self.storage,
            "enforcement": self.enforcement,
        }

    def enforced_retention_days(self) -> int | None:
        """Return the term that is actually applied to stored rows."""
        return self.maximum_retention_days or self.minimum_retention_days


@dataclass(frozen=True, slots=True)
class ProviderLifecycleRecord:
    provider: str
    data_class: str
    storage_location: str
    retention_days: int | None
    deletion_scope: str
    backup_behavior: str
    export_policy: str
    dashboard_caveat: str
    evidence_state: str
    retention_mode: str

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
            "retention_mode": self.retention_mode,
        }


RETENTION_RULES: tuple[AnalyticsRetentionRule, ...] = (
    AnalyticsRetentionRule(
        "attribution_bridge",
        None,
        None,
        "graf_controlled",
        "purge bridge row/token hash in GRAF storage",
        "Campaign link can be removed; aggregate reports may remain.",
        "graf_postgres",
        "decision_required",
        retention_mode="until_decision",
    ),
    # GRAF-controlled history is retained until a separate deletion decision.
    AnalyticsRetentionRule(
        "posthog_product_events",
        None,
        None,
        "provider_supported",
        "PostHog person/event deletion for stable pseudonymous identity where supported",
        "Raw GRAF identity is not present in the aggregate; level 1 counters stay outside PostHog.",
        "clickhouse_posthog",
        "decision_required",
        retention_mode="until_decision",
    ),
    AnalyticsRetentionRule(
        "posthog_session_replay",
        None,
        None,
        "provider_supported",
        "PostHog recording deletion for stable pseudonymous identity/session where supported",
        "Replay must be masked; aggregate replay metrics may remain.",
        "clickhouse_posthog",
        "decision_required",
        retention_mode="until_decision",
    ),
    AnalyticsRetentionRule(
        "yandex_page_events",
        90,
        None,
        "manual_process",
        "Yandex counter/user-data deletion process where available",
        "GRAF must not promise universal erasure from Yandex aggregate reports.",
        "yandex_provider",
        "provider_controlled",
        retention_mode="provider_controlled",
    ),
    AnalyticsRetentionRule(
        "yandex_webvisor",
        90,
        90,
        "manual_process",
        "Yandex Webvisor/session deletion process where available",
        "Unapproved page classes keep Webvisor off.",
        "yandex_provider",
        "provider_controlled",
        retention_mode="provider_controlled",
    ),
    AnalyticsRetentionRule(
        "yandex_offline_conversions",
        90,
        90,
        "manual_process",
        "remove queued uploads in GRAF; request/provider process for uploaded conversions",
        "Uploaded ad conversions may remain in aggregate ad reports.",
        "yandex_provider",
        "provider_controlled",
        retention_mode="provider_controlled",
    ),
    AnalyticsRetentionRule(
        "delivery_gap",
        None,
        None,
        "graf_controlled",
        "purge safe gap row in GRAF storage",
        "Gaps contain only safe buckets and caveats.",
        "graf_postgres",
        "decision_required",
        retention_mode="until_decision",
    ),
    AnalyticsRetentionRule(
        "exported_report",
        None,
        None,
        "manual_process",
        "delete/redact exported report files controlled by GRAF",
        "Reports outside GRAF control are outside direct erasure control.",
        "graf_files",
        "decision_required",
        retention_mode="until_decision",
    ),
    # Anonymous history follows the same explicit retention mode.
    AnalyticsRetentionRule(
        "anonymous_page_aggregate",
        None,
        None,
        "graf_controlled",
        "delete selected aggregate buckets on a separate deletion decision",
        "Buckets contain only coarse dimensions and visit counters; nothing to erase per person.",
        "graf_postgres",
        "decision_required",
        retention_mode="until_decision",
    ),
    # Level 2: campaign attribute copied onto the client record at registration.
    AnalyticsRetentionRule(
        "client_acquisition_attribute",
        None,
        None,
        "graf_controlled",
        "delete or anonymise the acquisition attribute with its account record",
        "The attribute is part of the client record; deletion follows account deletion.",
        "graf_postgres",
        "decision_required",
        retention_mode="until_decision",
    ),
    # The 90-day attribution window limits use, not storage lifetime.
    AnalyticsRetentionRule(
        "visit_attribution",
        None,
        None,
        "graf_controlled",
        "delete selected visit attribution rows on a separate deletion decision",
        "Attribution stops after 90 days; retained history does not extend the linking window.",
        "graf_postgres",
        "decision_required",
        retention_mode="until_decision",
    ),
)

PROVIDER_LIFECYCLE_RECORDS: tuple[ProviderLifecycleRecord, ...] = (
    ProviderLifecycleRecord(
        "posthog",
        "activation_event",
        "self_hosted_posthog_workspace",
        None,
        "provider_operator_action",
        "retained_until_backup_expiry",
        "metadata_only_or_provider_internal",
        "Deletion is handled through PostHog operator action where supported; aggregate cohorts may remain.",
        "documented",
        "until_decision",
    ),
    ProviderLifecycleRecord(
        "posthog",
        "autocapture_event",
        "self_hosted_posthog_workspace",
        None,
        "provider_operator_action",
        "retained_until_backup_expiry",
        "provider_internal_only",
        "Autocapture may contain first-party product behavior inside PostHog; committed evidence stays metadata-only.",
        "documented",
        "until_decision",
    ),
    ProviderLifecycleRecord(
        "posthog",
        "replay_recording",
        "not_collected_by_default",
        None,
        "not_collected",
        "not_applicable_until_enabled",
        "forbidden_until_page_proof",
        "Replay is disabled by default and needs separate masking/storage/legal/QA proof.",
        "documented",
        "until_decision",
    ),
    ProviderLifecycleRecord(
        "posthog",
        "backup",
        "posthog_backup_target",
        None,
        "provider_operator_action",
        "latest_7_successful_full_sets_minimum_2",
        "forbidden_content_bearing_export",
        "Backups may retain provider data until expiry and are not committed as evidence.",
        "documented",
        "backup_rotation",
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
        "provider_controlled",
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
        "provider_controlled",
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
        "provider_controlled",
    ),
    ProviderLifecycleRecord(
        "graf_metadata",
        "delivery_gap_record",
        "graf_metadata_store_or_evidence",
        None,
        "deleteable_by_graf",
        "retained_until_backup_expiry",
        "metadata_only",
        "Delivery gaps contain safe buckets and caveats only.",
        "documented",
        "until_decision",
    ),
    ProviderLifecycleRecord(
        "graf_metadata",
        "dashboard_evidence",
        "committed_metadata_only_evidence",
        None,
        "deleteable_by_graf",
        "git_history_limited",
        "metadata_only",
        "Committed evidence must not contain raw provider payloads or visitor/account data.",
        "documented",
        "until_decision",
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
    raise AnalyticsRetentionConfigurationError(f"unknown analytics retention category: {category}")


def retention_days_for_category(category: str) -> int | None:
    """Return the enforced term, or fail closed for an unknown category.

    A missing category fails; None is valid only under an explicit policy.
    """
    rules = [rule for rule in RETENTION_RULES if rule.category == category]
    if not rules:
        raise AnalyticsRetentionConfigurationError(
            f"analytics retention category has no configured term: {category}"
        )
    return rules[0].enforced_retention_days()


def retention_deadline(
    rule: AnalyticsRetentionRule,
    *,
    since: datetime,
    due_at: datetime | None = None,
) -> datetime | None:
    """A separate deletion deadline must never be inferred from storage lifetime."""
    if due_at is not None:
        if due_at.tzinfo is None or since.tzinfo is None or due_at < since:
            raise AnalyticsRetentionConfigurationError("invalid separate deletion deadline")
        return due_at
    return None


def validate_retention_rules(
    rules: tuple[AnalyticsRetentionRule, ...] = RETENTION_RULES,
) -> tuple[str, ...]:
    """Return the configured categories; every rule validates on construction."""
    if not rules:
        raise AnalyticsRetentionConfigurationError("analytics retention rules are empty")
    categories = tuple(rule.category for rule in rules)
    if len(set(categories)) != len(categories):
        raise AnalyticsRetentionConfigurationError("analytics retention categories must be unique")
    return categories


# Missing policy fails at construction; until_decision must be explicit.
validate_retention_rules()
