from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

RETENTION_STORAGES = (
    "clickhouse_posthog",
    "graf_postgres",
    "graf_files",
    "yandex_provider",
)
RETENTION_ENFORCEMENTS = (
    "clickhouse_row_ttl",
    "scheduled_purge",
    "manual_process",
    "provider_controlled",
)
# Storages GRAF owns must carry an automatic enforcement. A GRAF-controlled
# category without one would silently become "keep forever", which FR-050
# forbids. ``graf_files`` is deliberately outside this set: exported report
# files may already have left GRAF storage, so only a manual process is honest.
GRAF_CONTROLLED_STORAGES = frozenset({"clickhouse_posthog", "graf_postgres"})
AUTOMATIC_ENFORCEMENTS = frozenset({"clickhouse_row_ttl", "scheduled_purge"})


class AnalyticsRetentionConfigurationError(ValueError):
    """Raised when a retention category has no explicit, enforceable term.

    FR-050: a missing term is a configuration error, never an implicit
    "retain indefinitely".
    """


@dataclass(frozen=True, slots=True)
class AnalyticsRetentionRule:
    category: str
    minimum_retention_days: int
    maximum_retention_days: int | None
    delete_on_user_request: str
    provider_delete_method: str
    deletion_truth: str
    storage: str = "graf_postgres"
    enforcement: str = "scheduled_purge"

    def __post_init__(self) -> None:
        if self.minimum_retention_days is None or self.minimum_retention_days < 1:
            raise AnalyticsRetentionConfigurationError(
                f"analytics retention category {self.category!r} has no retention term"
            )
        if self.maximum_retention_days is not None and (
            self.maximum_retention_days < self.minimum_retention_days
        ):
            raise AnalyticsRetentionConfigurationError(
                f"analytics retention category {self.category!r} has a maximum below its minimum"
            )
        if self.storage not in RETENTION_STORAGES:
            raise AnalyticsRetentionConfigurationError(
                f"analytics retention category {self.category!r} has an unknown storage"
            )
        if self.enforcement not in RETENTION_ENFORCEMENTS:
            raise AnalyticsRetentionConfigurationError(
                f"analytics retention category {self.category!r} has an unknown enforcement"
            )
        if (
            self.storage in GRAF_CONTROLLED_STORAGES
            and self.enforcement not in AUTOMATIC_ENFORCEMENTS
        ):
            raise AnalyticsRetentionConfigurationError(
                f"analytics retention category {self.category!r} is GRAF-controlled "
                "but has no automatic enforcement"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "minimum_retention_days": self.minimum_retention_days,
            "maximum_retention_days": self.maximum_retention_days,
            "delete_on_user_request": self.delete_on_user_request,
            "provider_delete_method": self.provider_delete_method,
            "deletion_truth": self.deletion_truth,
            "storage": self.storage,
            "enforcement": self.enforcement,
        }

    def enforced_retention_days(self) -> int:
        """Return the term that is actually applied to stored rows."""
        return self.maximum_retention_days or self.minimum_retention_days


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
        "graf_postgres",
        "scheduled_purge",
    ),
    # Level 2 and level 3 measurement events live in ClickHouse inside PostHog.
    # FR-036 and contracts/operations.md set one term for all of them: 365 days,
    # applied as a ClickHouse row TTL (T017).
    AnalyticsRetentionRule(
        "posthog_product_events",
        365,
        365,
        "provider_supported",
        "PostHog person/event deletion for stable pseudonymous identity where supported",
        "Raw GRAF identity is not present in the aggregate; level 1 counters stay outside PostHog.",
        "clickhouse_posthog",
        "clickhouse_row_ttl",
    ),
    AnalyticsRetentionRule(
        "posthog_session_replay",
        90,
        90,
        "provider_supported",
        "PostHog recording deletion for stable pseudonymous identity/session where supported",
        "Replay must be masked; aggregate replay metrics may remain.",
        "clickhouse_posthog",
        "clickhouse_row_ttl",
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
    ),
    AnalyticsRetentionRule(
        "delivery_gap",
        90,
        90,
        "graf_controlled",
        "purge safe gap row in GRAF storage",
        "Gaps contain only safe buckets and caveats.",
        "graf_postgres",
        "scheduled_purge",
    ),
    AnalyticsRetentionRule(
        "exported_report",
        90,
        90,
        "manual_process",
        "delete/redact exported report files controlled by GRAF",
        "Reports outside GRAF control are outside direct erasure control.",
        "graf_files",
        "manual_process",
    ),
    # Level 1: the anonymous page aggregate carries no identifier, so it is kept
    # long enough to compare campaigns across years (36 months, FR-036).
    AnalyticsRetentionRule(
        "anonymous_page_aggregate",
        1095,
        1095,
        "graf_controlled",
        "delete aggregate buckets older than the retention term in GRAF storage",
        "Buckets contain only coarse dimensions and visit counters; nothing to erase per person.",
        "graf_postgres",
        "scheduled_purge",
    ),
    # Level 2: campaign attribute copied onto the client record at registration.
    AnalyticsRetentionRule(
        "client_acquisition_attribute",
        1095,
        1095,
        "graf_controlled",
        "delete or anonymise the acquisition attribute with its account record",
        "The attribute is part of the client record; deletion follows account deletion.",
        "graf_postgres",
        "scheduled_purge",
    ),
    # Level 2: the visit attribution row is useless after its 90-day window.
    AnalyticsRetentionRule(
        "visit_attribution",
        90,
        90,
        "graf_controlled",
        "delete expired visit attribution rows in GRAF storage",
        "The row is not a tracking identifier and carries no reporting value after its window.",
        "graf_postgres",
        "scheduled_purge",
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
    raise AnalyticsRetentionConfigurationError(
        f"unknown analytics retention category: {category}"
    )


def retention_days_for_category(category: str) -> int:
    """Return the enforced term, or fail closed for an unknown category.

    FR-050: a category without a term must never fall back to "retain
    indefinitely"; readiness must be blocked instead.
    """
    rules = [rule for rule in RETENTION_RULES if rule.category == category]
    if not rules:
        raise AnalyticsRetentionConfigurationError(
            f"analytics retention category has no configured term: {category}"
        )
    return rules[0].enforced_retention_days()


def retention_deadline(rule: AnalyticsRetentionRule, *, since: datetime) -> datetime:
    """The moment by which the rule's term has certainly passed.

    FR-048 asks for data that lost its legal basis to be deleted or anonymised
    "within the term the retention rules set". The term lives in exactly one
    place — :func:`enforced_retention_days` — so this helper only adds it to the
    moment the basis was lost instead of introducing a second number.
    """

    return since + timedelta(days=rule.enforced_retention_days())


def validate_retention_rules(
    rules: tuple[AnalyticsRetentionRule, ...] = RETENTION_RULES,
) -> tuple[str, ...]:
    """Return the configured categories; every rule validates on construction."""
    if not rules:
        raise AnalyticsRetentionConfigurationError("analytics retention rules are empty")
    categories = tuple(rule.category for rule in rules)
    if len(set(categories)) != len(categories):
        raise AnalyticsRetentionConfigurationError(
            "analytics retention categories must be unique"
        )
    return categories


# Import-time gate: a category that lost its term (or its enforcement) must fail
# fast instead of silently keeping data forever.
validate_retention_rules()
