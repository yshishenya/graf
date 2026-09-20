from __future__ import annotations

import os
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.access_governance import (
    access_governance_blockers,
    read_access_governance_state,
)
from twobrain_rec_server.product_analytics.provider_secrets import secret_file_status

# Metadata-only evidence files written by the scheduled operations tasks:
# `infra/scripts/backup-posthog.sh`, `infra/scripts/verify-posthog-restore.sh`
# and `infra/scripts/enforce-product-analytics-retention.sh`. Paths follow the
# same environment contract as those scripts, so a single out-of-git
# environment file configures both sides.
BACKUP_STATE_FILE_ENV = "GRAF_POSTHOG_BACKUP_STATE_FILE"
RESTORE_STATE_FILE_ENV = "GRAF_POSTHOG_RESTORE_STATE_FILE"
RETENTION_STATE_FILE_ENV = "GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_FILE"
BACKUP_STATE_DIR_ENV = "GRAF_POSTHOG_BACKUP_STATE_DIR"
RETENTION_STATE_DIR_ENV = "GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_DIR"
DEFAULT_BACKUP_STATE_DIR = "/var/lib/graf-posthog-backup"
DEFAULT_RETENTION_STATE_DIR = "/var/lib/graf-posthog-retention"

# Readiness thresholds (FR-034, FR-035, FR-052, SC-010).
BACKUP_MAX_AGE_HOURS_ENV = "GRAF_POSTHOG_BACKUP_MAX_AGE_HOURS"
RESTORE_MAX_AGE_DAYS_ENV = "GRAF_POSTHOG_RESTORE_MAX_AGE_DAYS"
MINIMUM_COPIES_ENV = "GRAF_POSTHOG_BACKUP_MIN_COPIES"
MINIMUM_OFFSITE_COPIES_ENV = "GRAF_POSTHOG_BACKUP_MIN_OFFSITE_COPIES"
DEFAULT_BACKUP_MAX_AGE_HOURS = 26
DEFAULT_RESTORE_MAX_AGE_DAYS = 30
DEFAULT_MINIMUM_COPIES = 2
DEFAULT_MINIMUM_OFFSITE_COPIES = 1

# Approved retention terms (FR-036, FR-050, contract `operations.md`). A
# category without a term is a configuration error, never "keep forever", and a
# term below the approved minimum blocks the analytics readiness claim.
REQUIRED_RETENTION_TERMS: tuple[tuple[str, int], ...] = (
    ("measurement_events", 365),
    ("anonymous_aggregate", 1095),
    ("visit_attribution", 90),
    ("acquisition_attribute", 1095),
)

BLOCKER_BACKUP_STATE_UNAVAILABLE = "backup_state_unavailable"
BLOCKER_BACKUP_MISSING = "backup_missing"
BLOCKER_BACKUP_STALE = "backup_stale"
BLOCKER_BACKUP_COPY_COUNT = "backup_copy_count_below_minimum"
BLOCKER_BACKUP_OFFSITE_COPY = "backup_offsite_copy_missing"
BLOCKER_RESTORE_MISSING = "restore_verification_missing"
BLOCKER_RESTORE_FAILED = "restore_verification_failed"
BLOCKER_RESTORE_STALE = "restore_verification_stale"
BLOCKER_RETENTION_STATE_UNAVAILABLE = "retention_state_unavailable"
BLOCKER_RETENTION_CATEGORY_MISSING = "retention_category_missing"
BLOCKER_RETENTION_TERM_MISSING = "retention_term_missing"
BLOCKER_RETENTION_TERM_BELOW_REQUIRED = "retention_term_below_required"
BLOCKER_RETENTION_ENFORCEMENT_UNVERIFIED = "retention_enforcement_unverified"


@dataclass(frozen=True, slots=True)
class ProviderReadiness:
    provider: str
    enabled: bool
    configured: bool
    blockers: tuple[str, ...]
    metadata: dict[str, str] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "enabled": self.enabled,
            "configured": self.configured,
            "blockers": list(self.blockers),
            "metadata": dict(self.metadata or {}),
        }


@dataclass(frozen=True, slots=True)
class RetentionCategoryEvidence:
    """One retention category as enforced by the scheduled task."""

    category: str
    retention_days: int | None
    storage: str
    enforcement: str
    enforcement_verified: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "retention_days": self.retention_days,
            "storage": self.storage,
            "enforcement": self.enforcement,
            "enforcement_verified": self.enforcement_verified,
        }


@dataclass(frozen=True, slots=True)
class AnalyticsOperationsEvidence:
    """Metadata-only evidence collected from the scheduled operations tasks."""

    backup_state_available: bool = False
    backup_age_hours: float | None = None
    backup_copies_local: int | None = None
    backup_copies_offsite: int | None = None
    backup_result: str = "unknown"
    restore_state_available: bool = False
    restore_age_days: float | None = None
    restore_result: str = "unknown"
    retention_state_available: bool = False
    retention_result: str = "unknown"
    retention_categories: tuple[RetentionCategoryEvidence, ...] = ()
    missing_retention_categories: tuple[str, ...] = field(default=())


@dataclass(frozen=True, slots=True)
class ProductAnalyticsProviderReadiness:
    provider_mode: str
    posthog: ProviderReadiness
    yandex_all_pages: ProviderReadiness
    yandex_offline: ProviderReadiness
    analytics_operations: ProviderReadiness = field(
        default_factory=lambda: ProviderReadiness("analytics_operations", False, False, ())
    )
    access_governance: ProviderReadiness = field(
        default_factory=lambda: ProviderReadiness("access_governance", False, False, ())
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider_mode": self.provider_mode,
            "posthog": self.posthog.as_dict(),
            "yandex_all_pages": self.yandex_all_pages.as_dict(),
            "yandex_offline": self.yandex_offline.as_dict(),
            "analytics_operations": self.analytics_operations.as_dict(),
            "access_governance": self.access_governance.as_dict(),
        }


def _first_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values.setdefault(key.strip(), value.strip())
    return values


def _record_lines(text: str) -> tuple[dict[str, str], ...]:
    records: list[dict[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        record: dict[str, str] = {}
        for token in stripped.split():
            key, separator, value = token.partition("=")
            if separator:
                record.setdefault(key, value)
        if record:
            records.append(record)
    return tuple(records)


def _read_state_text(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as state_file:
            return state_file.read()
    except (OSError, UnicodeError):
        return None


def _optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _optional_epoch(value: str | None) -> int | None:
    parsed = _optional_int(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def _bounded_number(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _state_file_path(environ: Mapping[str, str], explicit_env: str, directory_env: str, default_dir: str, name: str) -> str:
    explicit = environ.get(explicit_env)
    if explicit:
        return explicit
    directory = environ.get(directory_env) or default_dir
    return os.path.join(directory, name)


def backup_state_file_path(environ: Mapping[str, str]) -> str:
    return _state_file_path(
        environ, BACKUP_STATE_FILE_ENV, BACKUP_STATE_DIR_ENV, DEFAULT_BACKUP_STATE_DIR, "backup-state"
    )


def restore_state_file_path(environ: Mapping[str, str]) -> str:
    return _state_file_path(
        environ, RESTORE_STATE_FILE_ENV, BACKUP_STATE_DIR_ENV, DEFAULT_BACKUP_STATE_DIR, "restore-state"
    )


def retention_state_file_path(environ: Mapping[str, str]) -> str:
    return _state_file_path(
        environ,
        RETENTION_STATE_FILE_ENV,
        RETENTION_STATE_DIR_ENV,
        DEFAULT_RETENTION_STATE_DIR,
        "retention-state",
    )


def collect_analytics_operations_evidence(
    environ: Mapping[str, str] | None = None,
    *,
    now: float | None = None,
) -> AnalyticsOperationsEvidence:
    """Read the metadata-only operations state files.

    Missing files are reported as unavailable instead of raising: a missing
    evidence file means the scheduled task never ran, which is exactly the state
    readiness must block (FR-034, FR-035, FR-050).
    """

    environment = os.environ if environ is None else environ
    current_time = time.time() if now is None else now

    backup_text = _read_state_text(backup_state_file_path(environment))
    backup_values = _first_values(backup_text) if backup_text is not None else {}
    backup_epoch = _optional_epoch(backup_values.get("last_success_epoch"))
    backup_age_hours = (current_time - backup_epoch) / 3600 if backup_epoch is not None else None

    restore_text = _read_state_text(restore_state_file_path(environment))
    restore_values = _first_values(restore_text) if restore_text is not None else {}
    restore_epoch = _optional_epoch(restore_values.get("last_verify_epoch"))
    restore_age_days = (current_time - restore_epoch) / 86400 if restore_epoch is not None else None

    retention_text = _read_state_text(retention_state_file_path(environment))
    retention_values = _first_values(retention_text) if retention_text is not None else {}
    categories: list[RetentionCategoryEvidence] = []
    missing_categories: list[str] = []
    if retention_text is not None:
        for record in _record_lines(retention_text):
            if record.get("category"):
                categories.append(
                    RetentionCategoryEvidence(
                        category=record["category"],
                        retention_days=_optional_int(record.get("retention_days")),
                        storage=record.get("storage", "unknown"),
                        enforcement=record.get("enforcement", "unknown"),
                        enforcement_verified=record.get("enforcement_verified") == "true",
                    )
                )
            elif record.get("missing_category"):
                missing_categories.append(record["missing_category"])

    return AnalyticsOperationsEvidence(
        backup_state_available=backup_text is not None,
        backup_age_hours=backup_age_hours,
        backup_copies_local=_optional_int(backup_values.get("copies_local")),
        backup_copies_offsite=_optional_int(backup_values.get("copies_offsite")),
        backup_result=backup_values.get("last_attempt_result", "unknown"),
        restore_state_available=restore_text is not None,
        restore_age_days=restore_age_days,
        restore_result=restore_values.get("last_verify_result", "unknown"),
        retention_state_available=retention_text is not None,
        retention_result=retention_values.get("result", "unknown"),
        retention_categories=tuple(categories),
        missing_retention_categories=tuple(missing_categories),
    )


def analytics_operations_blockers(
    evidence: AnalyticsOperationsEvidence,
    environ: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Return the blocker codes that stop the analytics readiness claim."""

    environment = os.environ if environ is None else environ
    backup_max_age_hours = _bounded_number(
        environment.get(BACKUP_MAX_AGE_HOURS_ENV), float(DEFAULT_BACKUP_MAX_AGE_HOURS)
    )
    restore_max_age_days = _bounded_number(
        environment.get(RESTORE_MAX_AGE_DAYS_ENV), float(DEFAULT_RESTORE_MAX_AGE_DAYS)
    )
    minimum_copies = int(_bounded_number(environment.get(MINIMUM_COPIES_ENV), float(DEFAULT_MINIMUM_COPIES)))
    minimum_offsite_copies = int(
        _bounded_number(environment.get(MINIMUM_OFFSITE_COPIES_ENV), float(DEFAULT_MINIMUM_OFFSITE_COPIES))
    )

    blockers: list[str] = []

    if not evidence.backup_state_available:
        blockers.append(BLOCKER_BACKUP_STATE_UNAVAILABLE)
    else:
        if evidence.backup_age_hours is None:
            blockers.append(BLOCKER_BACKUP_MISSING)
        elif evidence.backup_age_hours > backup_max_age_hours:
            blockers.append(BLOCKER_BACKUP_STALE)
        if evidence.backup_copies_local is None or evidence.backup_copies_local < minimum_copies:
            blockers.append(BLOCKER_BACKUP_COPY_COUNT)
        if evidence.backup_copies_offsite is None or evidence.backup_copies_offsite < minimum_offsite_copies:
            blockers.append(BLOCKER_BACKUP_OFFSITE_COPY)

    if not evidence.restore_state_available:
        blockers.append(BLOCKER_RESTORE_MISSING)
    elif evidence.restore_result != "pass":
        blockers.append(BLOCKER_RESTORE_FAILED)
    elif evidence.restore_age_days is None:
        blockers.append(BLOCKER_RESTORE_MISSING)
    elif evidence.restore_age_days > restore_max_age_days:
        blockers.append(BLOCKER_RESTORE_STALE)

    declared = {record.category: record for record in evidence.retention_categories}
    missing_declared = set(evidence.missing_retention_categories)
    if not evidence.retention_state_available:
        blockers.append(BLOCKER_RETENTION_STATE_UNAVAILABLE)
    else:
        for category, required_days in REQUIRED_RETENTION_TERMS:
            if category in missing_declared:
                blockers.append(f"{BLOCKER_RETENTION_CATEGORY_MISSING}:{category}")
                continue
            record = declared.get(category)
            if record is None:
                blockers.append(f"{BLOCKER_RETENTION_CATEGORY_MISSING}:{category}")
                continue
            if record.retention_days is None or record.retention_days <= 0:
                blockers.append(f"{BLOCKER_RETENTION_TERM_MISSING}:{category}")
                continue
            if record.retention_days < required_days:
                blockers.append(f"{BLOCKER_RETENTION_TERM_BELOW_REQUIRED}:{category}")
                continue
            if not record.enforcement_verified:
                blockers.append(f"{BLOCKER_RETENTION_ENFORCEMENT_UNVERIFIED}:{category}")

    return tuple(dict.fromkeys(blockers))


def build_analytics_operations_readiness(
    settings: Settings,
    environ: Mapping[str, str] | None = None,
    *,
    now: float | None = None,
    evidence: AnalyticsOperationsEvidence | None = None,
) -> ProviderReadiness:
    """Readiness of the analytics operations that keep measurement trustworthy."""

    environment = os.environ if environ is None else environ
    collected = evidence if evidence is not None else collect_analytics_operations_evidence(environment, now=now)
    blockers = analytics_operations_blockers(collected, environment)

    retention_terms = ",".join(f"{category}={days}" for category, days in REQUIRED_RETENTION_TERMS)
    declared_terms = ",".join(
        f"{record.category}={record.retention_days if record.retention_days is not None else 'missing'}"
        for record in collected.retention_categories
    )
    metadata = {
        "backup_policy": "scheduled_daily_with_required_offsite_copy",
        "backup_max_age_hours": str(int(_bounded_number(environment.get(BACKUP_MAX_AGE_HOURS_ENV), float(DEFAULT_BACKUP_MAX_AGE_HOURS)))),
        "backup_last_result": collected.backup_result,
        "backup_last_success_age_hours": (
            f"{collected.backup_age_hours:.1f}" if collected.backup_age_hours is not None else "unknown"
        ),
        "backup_copies_local": (
            str(collected.backup_copies_local) if collected.backup_copies_local is not None else "unknown"
        ),
        "backup_copies_offsite": (
            str(collected.backup_copies_offsite) if collected.backup_copies_offsite is not None else "unknown"
        ),
        "backup_minimum_copies": str(int(_bounded_number(environment.get(MINIMUM_COPIES_ENV), float(DEFAULT_MINIMUM_COPIES)))),
        "backup_minimum_offsite_copies": str(
            int(_bounded_number(environment.get(MINIMUM_OFFSITE_COPIES_ENV), float(DEFAULT_MINIMUM_OFFSITE_COPIES)))
        ),
        "restore_verification_result": collected.restore_result,
        "restore_verification_age_days": (
            f"{collected.restore_age_days:.1f}" if collected.restore_age_days is not None else "unknown"
        ),
        "restore_verification_max_age_days": str(
            int(_bounded_number(environment.get(RESTORE_MAX_AGE_DAYS_ENV), float(DEFAULT_RESTORE_MAX_AGE_DAYS)))
        ),
        "retention_result": collected.retention_result,
        "retention_required_terms": retention_terms,
        "retention_declared_terms": declared_terms or "none",
        "retention_enforcement": "row_ttl_and_scheduled_task",
        "evidence": "metadata_only",
        "product_impact": "measurement_gap_only",
    }

    return ProviderReadiness(
        "analytics_operations",
        settings.product_analytics_enabled,
        not blockers,
        blockers,
        metadata,
    )


def operations_block_claim(settings: Settings) -> bool:
    """Whether the operations blockers stop the readiness claim itself.

    A dry-run or smoke configuration explicitly does not claim live analytics:
    the readiness report already labels it `infra_smoke_ready is not user
    rollout readiness`. Once the configuration claims live provider delivery
    (FR-034, FR-051), the operations evidence becomes part of that claim and the
    same blockers stop it.
    """

    return bool(
        settings.product_analytics_enabled and settings.product_analytics_live_provider_delivery_allowed()
    )


def build_provider_readiness(
    settings: Settings,
    *,
    environ: Mapping[str, str] | None = None,
    now: float | None = None,
) -> ProductAnalyticsProviderReadiness:
    posthog_blockers: list[str] = []
    if settings.product_analytics_posthog_enabled:
        if settings.product_analytics_posthog_host is None:
            posthog_blockers.append("missing_posthog_host")
        if not secret_file_status(
            settings.product_analytics_posthog_project_key_file,
            logical_name="POSTHOG_PROJECT_KEY",
        ).present:
            posthog_blockers.append("missing_posthog_project_key_file")
    else:
        posthog_blockers.append("posthog_disabled")

    yandex_all_pages_blockers: list[str] = []
    if settings.product_analytics_yandex_all_pages_enabled:
        if settings.product_analytics_yandex_counter_id is None:
            yandex_all_pages_blockers.append("missing_yandex_counter_id")
        if not settings.product_analytics_legal_approved:
            yandex_all_pages_blockers.append("legal_not_approved")
    else:
        yandex_all_pages_blockers.append("yandex_all_pages_disabled")

    yandex_offline_blockers: list[str] = []
    if settings.product_analytics_yandex_offline_enabled:
        if settings.product_analytics_yandex_counter_id is None:
            yandex_offline_blockers.append("missing_yandex_counter_id")
        if not secret_file_status(
            settings.product_analytics_yandex_oauth_token_file,
            logical_name="YANDEX_OAUTH_TOKEN",
        ).present:
            yandex_offline_blockers.append("missing_yandex_oauth_token_file")
    else:
        yandex_offline_blockers.append("yandex_offline_disabled")

    operations = build_analytics_operations_readiness(settings, environ, now=now)
    access_evidence = read_access_governance_state(environ)
    access_blockers = access_governance_blockers(access_evidence, environ=environ, now=int(now) if now is not None else None)
    claim_gated = operations_block_claim(settings)
    if claim_gated:
        posthog_blockers.extend(operations.blockers)

    access_metadata = access_evidence.as_dict()
    access_metadata["blockers"] = list(access_blockers)

    return ProductAnalyticsProviderReadiness(
        provider_mode=settings.product_analytics_provider_mode,
        posthog=ProviderReadiness(
            "posthog",
            settings.product_analytics_posthog_enabled,
            settings.product_analytics_posthog_enabled and not posthog_blockers,
            tuple(posthog_blockers),
            {
                "rbac_access_model": "role_based_metadata_only",
                "access_governance": access_metadata,
                "audit_expectation": "provider_config_access_export_replay_retention_changes",
                "retention_deletion_lifecycle": "documented",
                "dashboard_caveat": "required",
                "deploy_handoff": "dry_run_documented",
                "resource_thresholds": "configured",
                "backup_restore": "documented",
                "operations_claim_gate": "enforced" if claim_gated else "not_claimed",
            },
        ),
        yandex_all_pages=ProviderReadiness(
            "yandex_all_pages",
            settings.product_analytics_yandex_all_pages_enabled,
            settings.product_analytics_yandex_all_pages_enabled and not yandex_all_pages_blockers,
            tuple(yandex_all_pages_blockers),
            {
                "counter_strategy": "reuse_093_runtime_only",
                "future_page_default": "blocked",
                "webvisor_maps_forms": "separate_page_class_proof_required",
            },
        ),
        yandex_offline=ProviderReadiness(
            "yandex_offline",
            settings.product_analytics_yandex_offline_enabled,
            settings.product_analytics_yandex_offline_enabled and not yandex_offline_blockers,
            tuple(yandex_offline_blockers),
            {
                "approved_conversions": "desktop_account_connected,first_value_session_completed",
                "identity_values": "redacted_metadata_only",
                "duplicate_protection": "required",
            },
        ),
        analytics_operations=operations,
        access_governance=ProviderReadiness(
            "access_governance",
            bool(access_evidence.state_available),
            not access_blockers,
            tuple(access_blockers),
            access_metadata,
        ),
    )
