from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

RLSProbeResult = Literal["pass", "blocked", "failed"]
RLSEnvironment = Literal["local", "postgres_test", "production_like", "live_production"]
RLSValidationResult = Literal["pass", "blocked"]
RLSLiveProductionDecision = Literal["not_requested", "approved"]
RLSLiveProductionProbe = Literal["not_attempted", "read_only_metadata"]
RLSDestructiveProbeDatabase = Literal["not_provided", "disposable", "explicit_test"]
RLSLiveProductionEnforcement = Literal["not_inspected", "enabled", "verification_blocked"]
RLSProductionStateResult = Literal["pass", "blocked"]

PRODUCTION_RLS_MINIMUM_REVISION = "0008_recording_sync_loop"

RLS_DIRECT_WORKSPACE_TABLES = frozenset(
    {
        "workspaces",
        "workspace_memberships",
        "registered_devices",
        "workspace_auth_policies",
        "auth_sessions",
        "workspace_provider_link_states",
        "auth_callback_states",
        "auth_audit_events",
        "workspace_consent_copy",
        "meetings",
        "media_revisions",
        "upload_sessions",
        "temporary_upload_objects",
        "track_artifacts",
        "manifest_snapshots",
        "ingest_audit_events",
        "processing_placeholders",
        "processing_workflows",
        "mediascribe_jobs",
        "processing_results",
        "transcript_segments",
        "diarization_segments",
        "processing_audit_events",
        "processing_dependency_states",
        "meeting_share_grants",
        "meeting_artifact_policies",
        "meeting_egress_audit_events",
        "export_packages",
        "meeting_deletion_requests",
        "meeting_deletion_artifact_states",
        "meeting_deletion_reports",
        "retention_policy_snapshots",
        "local_purge_tasks",
        "meeting_lifecycle_audit_events",
        "meeting_outcome_sets",
        "meeting_outcome_items",
        "meeting_outcome_generation_attempts",
        "calendar_sources",
        "calendar_credential_envelopes",
        "external_calendars",
        "calendar_event_snapshots",
        "calendar_participants",
        "conference_link_candidates",
        "recording_calendar_context_links",
        "calendar_reminder_states",
        "calendar_settings_preferences",
        "calendar_audit_events",
        "support_incidents",
        "support_incident_rate_limit_buckets",
        "workspace_invitations",
        "workspace_quota_policies",
        "workspace_usage_daily",
        "user_usage_daily",
        "admin_audit_events",
    }
)

RLS_INHERITED_WORKSPACE_TABLES = frozenset(
    {
        "upload_parts",
        "auth_session_device_bindings",
        "external_identities",
    }
)

RLS_ORGANIZATION_TABLES = frozenset(
    {
        "organizations",
        "user_identities",
    }
)

RLS_COVERED_TABLES = tuple(
    sorted(RLS_DIRECT_WORKSPACE_TABLES | RLS_INHERITED_WORKSPACE_TABLES | RLS_ORGANIZATION_TABLES)
)

REQUIRED_RLS_PROBES = (
    "same_tenant_read",
    "cross_tenant_read_not_found_or_empty",
    "cross_tenant_mutation_forbidden",
    "missing_context_auth_or_context_error",
    "worker_context",
    "maintenance_context",
)


@dataclass(frozen=True, slots=True)
class RLSProbeEvidence:
    name: str
    result: RLSProbeResult
    environment: RLSEnvironment


@dataclass(frozen=True, slots=True)
class RLSValidationReport:
    environment: RLSEnvironment
    probes: list[RLSProbeEvidence] = field(default_factory=list)
    live_production_decision: RLSLiveProductionDecision = "not_requested"
    live_production_probe: RLSLiveProductionProbe = "not_attempted"
    destructive_probe_database: RLSDestructiveProbeDatabase = "not_provided"
    live_production_enforcement: RLSLiveProductionEnforcement = "not_inspected"

    @property
    def probe_results(self) -> dict[str, RLSProbeResult]:
        return {probe.name: probe.result for probe in self.probes}

    @property
    def blocking_reasons(self) -> list[str]:
        reasons: list[str] = []
        results = self.probe_results
        for required_probe in REQUIRED_RLS_PROBES:
            if results.get(required_probe) != "pass":
                reasons.append(required_probe)
        if self.environment == "live_production" and self.live_production_enforcement != "enabled":
            reasons.append("production_read_only_state_required")
        return reasons

    @property
    def validation_result(self) -> RLSValidationResult:
        return "pass" if not self.blocking_reasons else "blocked"

    @property
    def ready_for_production_truth(self) -> bool:
        return self.environment in {"postgres_test", "production_like"} and self.validation_result == "pass"

    def evidence_lines(self) -> list[str]:
        lines = [
            f"rls_validation_result={self.validation_result}",
            f"environment={self.environment}",
            f"live_production_probe={self.live_production_probe}",
            f"destructive_probe_database={self.destructive_probe_database}",
            f"live_production_enforcement={self.live_production_enforcement}",
        ]
        if self.blocking_reasons:
            lines.append(f"blocking_reasons={','.join(self.blocking_reasons)}")
        lines.append(f"ready_for_production_truth={str(self.ready_for_production_truth).lower()}")
        return lines


@dataclass(frozen=True, slots=True)
class RLSTableStateEvidence:
    table_name: str
    rls_enabled: bool
    rls_forced: bool
    table_exists: bool = True
    source: Literal["pg_catalog"] = "pg_catalog"

    @property
    def enabled_and_forced(self) -> bool:
        return self.table_exists and self.rls_enabled and self.rls_forced


def alembic_revision_includes_rls_hardening(revision: str) -> bool:
    if PRODUCTION_RLS_MINIMUM_REVISION in revision:
        return True
    current = re.match(r"0*(\d+)", revision.strip())
    minimum = re.match(r"0*(\d+)", PRODUCTION_RLS_MINIMUM_REVISION)
    if current is None or minimum is None:
        return False
    return int(current.group(1)) >= int(minimum.group(1))


@dataclass(frozen=True, slots=True)
class RLSProductionStateReport:
    table_states: list[RLSTableStateEvidence]
    deployed_commit: str
    alembic_revision: str
    environment: Literal["live_production"] = "live_production"

    @property
    def covered_table_count(self) -> int:
        return len(RLS_COVERED_TABLES)

    @property
    def normalized_table_states(self) -> list[RLSTableStateEvidence]:
        by_table = {state.table_name: state for state in self.table_states}
        return [
            by_table.get(
                table_name,
                RLSTableStateEvidence(
                    table_name=table_name,
                    rls_enabled=False,
                    rls_forced=False,
                    table_exists=False,
                ),
            )
            for table_name in RLS_COVERED_TABLES
        ]

    @property
    def rls_enabled_and_forced_count(self) -> int:
        return sum(1 for state in self.normalized_table_states if state.enabled_and_forced)

    @property
    def failed_table_names(self) -> list[str]:
        return [
            state.table_name
            for state in self.normalized_table_states
            if not state.enabled_and_forced
        ]

    @property
    def blocking_reasons(self) -> list[str]:
        reasons: list[str] = []
        if not alembic_revision_includes_rls_hardening(self.alembic_revision):
            reasons.append("alembic_revision_before_rls_hardening")
        if self.failed_table_names:
            reasons.append("covered_tables_not_enabled_and_forced")
        return reasons

    @property
    def production_rls_state_result(self) -> RLSProductionStateResult:
        return "pass" if not self.blocking_reasons else "blocked"

    @property
    def live_production_enforcement(self) -> RLSLiveProductionEnforcement:
        return "enabled" if self.production_rls_state_result == "pass" else "verification_blocked"

    def evidence_lines(self) -> list[str]:
        failed_table_names = ",".join(self.failed_table_names) if self.failed_table_names else "none"
        lines = [
            f"production_rls_state_result={self.production_rls_state_result}",
            f"environment={self.environment}",
            "live_production_probe=read_only_metadata",
            f"live_production_enforcement={self.live_production_enforcement}",
            f"deployed_commit={self.deployed_commit}",
            f"alembic_revision={self.alembic_revision}",
            f"covered_table_count={self.covered_table_count}",
            f"rls_enabled_and_forced_count={self.rls_enabled_and_forced_count}",
            f"failed_table_names={failed_table_names}",
        ]
        if self.blocking_reasons:
            lines.append(f"blocking_reasons={','.join(self.blocking_reasons)}")
        return lines


def evaluate_production_rls_state(
    table_states: list[RLSTableStateEvidence],
    *,
    deployed_commit: str,
    alembic_revision: str,
) -> RLSProductionStateReport:
    return RLSProductionStateReport(
        table_states=table_states,
        deployed_commit=deployed_commit,
        alembic_revision=alembic_revision,
    )
