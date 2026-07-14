from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, Field, model_validator

from twobrain_rec_server.config import (
    ALLOWED_READINESS_VERDICTS,
    FORBIDDEN_READINESS_VERDICTS,
    LOCAL_DEV_SMOKE_IDS,
    SMOKE_IDENTITY_CLASS,
)
from twobrain_rec_server.normalization.statuses import (
    CANONICAL_PROFILE_VERSION,
    VALIDATION_VERSION,
)
from twobrain_rec_server.observability.redaction import contains_forbidden_evidence_content

ReadinessVerdict = Literal["not_ready", "blocked", "infra_smoke_ready"]
GateResult = Literal["pass", "blocked", "failed"]
CleanupResult = Literal["pass", "residue_recorded", "blocked", "failed"]
DegradedHealth = Literal["healthy", "degraded", "unavailable", "not_checked", "not_configured"]

REQUIRED_SMOKE_EVIDENCE_FIELDS = (
    "run_id",
    "date",
    "branch_or_commit",
    "public_endpoint",
    "endpoint_reachability",
    "readiness_verdict",
    "compose_config_result",
    "secret_validation_result",
    "backup_reference",
    "restore_or_rollback_rehearsal_result",
    "migration_version_before",
    "migration_version_after",
    "health_live_result",
    "health_ready_result",
    "smoke_identity_class",
    "smoke_device_class",
    "upload_result",
    "postgres_persistence_result",
    "minio_persistence_result",
    "no_forbidden_side_effects_result",
    "mediascribe_degraded_awareness",
    "langfuse_degraded_awareness",
    "log_redaction_result",
    "cleanup_result",
    "open_risks",
)

ZERO_SIDE_EFFECT_ASSERTIONS = {
    "mediascribe_jobs_created": 0,
    "temporal_workflows_started": 0,
    "notes_jobs_created": 0,
    "retention_jobs_created": 0,
    "deletion_jobs_created": 0,
    "content_bearing_langfuse_traces_created": 0,
}

SMOKE_IDENTITY_NAMESPACE = uuid5(NAMESPACE_URL, "https://rec.2brain.pro/internal-smoke")


class SmokeIdentitySeed(BaseModel):
    organization_id: UUID
    workspace_id: UUID
    user_id: UUID
    device_id: UUID
    identity_class: Literal["internal_smoke"] = SMOKE_IDENTITY_CLASS
    device_class: Literal["internal_smoke"] = "internal_smoke"

    @model_validator(mode="after")
    def validate_seed_boundary(self) -> SmokeIdentitySeed:
        identifiers = {self.organization_id, self.workspace_id, self.user_id, self.device_id}
        if identifiers & LOCAL_DEV_SMOKE_IDS:
            raise ValueError("production smoke identity/device must not reuse local development seed identifiers")
        if len(identifiers) != 4:
            raise ValueError("production smoke identity/device identifiers must be distinct")
        return self

    def headers(self) -> dict[str, str]:
        return {
            "X-Organization-Id": str(self.organization_id),
            "X-Workspace-Id": str(self.workspace_id),
            "X-User-Id": str(self.user_id),
            "X-Device-Id": str(self.device_id),
        }


def build_smoke_identity_seed(run_id: str) -> SmokeIdentitySeed:
    base = f"{run_id}:021-production-deployment-plan"
    return SmokeIdentitySeed(
        organization_id=uuid5(SMOKE_IDENTITY_NAMESPACE, f"{base}:organization"),
        workspace_id=uuid5(SMOKE_IDENTITY_NAMESPACE, f"{base}:workspace"),
        user_id=uuid5(SMOKE_IDENTITY_NAMESPACE, f"{base}:user"),
        device_id=uuid5(SMOKE_IDENTITY_NAMESPACE, f"{base}:device"),
    )


class SmokeCleanupRecord(BaseModel):
    run_id: str
    cleanup_result: CleanupResult
    database_records_removed: int = 0
    object_keys_removed: int = 0
    residue_records: list[str] = Field(default_factory=list)
    residue_owner: str | None = None
    residue_follow_up_reason: str | None = None

    @model_validator(mode="after")
    def validate_cleanup_boundary(self) -> SmokeCleanupRecord:
        if self.cleanup_result == "pass" and self.residue_records:
            raise ValueError("pass cleanup cannot include residue records")
        if self.cleanup_result != "pass" and not (self.residue_owner and self.residue_follow_up_reason):
            raise ValueError("non-pass cleanup evidence must include residue owner and follow-up reason")
        return self


class DegradedAwarenessStatus(BaseModel):
    dependency: Literal["mediascribe", "langfuse"]
    configured: bool = False
    health_status: DegradedHealth = "not_checked"
    blocks_ingest_smoke: bool = False
    egress_created: bool = False

    @model_validator(mode="after")
    def validate_awareness_boundary(self) -> DegradedAwarenessStatus:
        if self.blocks_ingest_smoke:
            raise ValueError("degraded-awareness dependencies must not block 021 ingest smoke")
        if self.egress_created:
            raise ValueError("degraded-awareness checks must not create content egress")
        return self


class RollbackDecisionRecord(BaseModel):
    trigger: str
    decision: Literal["continue", "halt", "restore", "rollback", "blocked"]
    prior_state_reference: str | None = None
    operator: str | None = None
    evidence_reference: str | None = None
    cleanup_obligations: list[str] = Field(default_factory=list)
    residue_owner: str | None = None
    residue_follow_up_reason: str | None = None
    rollback_target: Literal["raw_pre_099", "compatibility_099", "forward_fix"] | None = None
    dispatch_stopped: bool | None = None
    legacy_playback_guard_retained: bool | None = None

    @model_validator(mode="after")
    def validate_decision_boundary(self) -> RollbackDecisionRecord:
        if self.decision in {"restore", "rollback"} and not self.prior_state_reference:
            raise ValueError("restore/rollback decisions require prior state reference")
        if self.cleanup_obligations and not (self.residue_owner and self.residue_follow_up_reason):
            raise ValueError("cleanup obligations require residue owner and follow-up reason")
        if self.trigger == "playback_normalization_compatibility":
            if self.rollback_target not in {"compatibility_099", "forward_fix"}:
                raise ValueError("playback normalization rollback cannot target a raw pre-099 binary")
            if self.dispatch_stopped is not True:
                raise ValueError("playback normalization dispatch must stop before rollback")
            if self.legacy_playback_guard_retained is not True:
                raise ValueError("playback normalization rollback must retain the legacy playback guard")
        return self


class PlaybackNormalizationDeploymentEvidence(BaseModel):
    """Metadata-only release gates for the 099 worker capability and recovery path."""

    scope: Literal["playback_normalization_capability"] = "playback_normalization_capability"
    readiness_state: Literal["ready", "degraded", "blocked"]
    runtime_sha: str
    profile_version: Literal[CANONICAL_PROFILE_VERSION]
    validation_version: Literal[VALIDATION_VERSION]
    migration_0022_result: GateResult
    image_capability_result: GateResult
    profile_contract_result: GateResult
    media_worker_result: GateResult
    automatic_retry_result: GateResult
    backfill_inventory_result: GateResult
    range_playback_result: GateResult
    cleanup_result: GateResult
    forbidden_metadata_result: GateResult

    @model_validator(mode="after")
    def validate_ready_boundary(self) -> PlaybackNormalizationDeploymentEvidence:
        if self.readiness_state != "ready":
            return self
        gate_results = {
            "migration_0022_result": self.migration_0022_result,
            "image_capability_result": self.image_capability_result,
            "profile_contract_result": self.profile_contract_result,
            "media_worker_result": self.media_worker_result,
            "automatic_retry_result": self.automatic_retry_result,
            "backfill_inventory_result": self.backfill_inventory_result,
            "range_playback_result": self.range_playback_result,
            "cleanup_result": self.cleanup_result,
            "forbidden_metadata_result": self.forbidden_metadata_result,
        }
        non_pass = [name for name, result in gate_results.items() if result != "pass"]
        if non_pass:
            raise ValueError(
                "playback normalization ready requires pass gates: " + ", ".join(non_pass)
            )
        return self


class PlaybackNormalizationRollingVersionState(BaseModel):
    """Allowed additive rollout state: migration, API, capable worker, dispatch."""

    migration_0022_present: bool
    api_contract: Literal["pre_099", "099"]
    media_worker_contract: Literal["absent", "099"]
    automatic_dispatch_enabled: bool
    api_runtime_sha: str | None = None
    media_worker_runtime_sha: str | None = None
    profile_version: Literal[CANONICAL_PROFILE_VERSION] = CANONICAL_PROFILE_VERSION
    validation_version: Literal[VALIDATION_VERSION] = VALIDATION_VERSION

    @model_validator(mode="after")
    def validate_additive_order(self) -> PlaybackNormalizationRollingVersionState:
        if self.api_contract == "099" and not self.migration_0022_present:
            raise ValueError("099 API requires migration 0022 before rollout")
        if self.media_worker_contract == "099" and self.api_contract != "099":
            raise ValueError("099 media worker requires the compatible 099 API contract")
        if self.automatic_dispatch_enabled and self.media_worker_contract != "099":
            raise ValueError("automatic dispatch requires a compatible media worker")
        if self.media_worker_contract == "099":
            if not self.api_runtime_sha or not self.media_worker_runtime_sha:
                raise ValueError("099 API and media worker require recorded runtime SHAs")
            if self.api_runtime_sha != self.media_worker_runtime_sha:
                raise ValueError("099 API and media worker runtime SHA must match")
        return self


class SmokeEvidenceRecord(BaseModel):
    run_id: str
    date: str = Field(default_factory=lambda: datetime.now(UTC).date().isoformat())
    branch_or_commit: str
    public_endpoint: str
    endpoint_reachability: str
    readiness_verdict: ReadinessVerdict
    compose_config_result: GateResult
    secret_validation_result: GateResult
    backup_reference: str
    restore_or_rollback_rehearsal_result: GateResult
    migration_version_before: str
    migration_version_after: str
    health_live_result: GateResult
    health_ready_result: GateResult
    smoke_identity_class: str = SMOKE_IDENTITY_CLASS
    smoke_device_class: str = "internal_smoke"
    upload_result: GateResult
    postgres_persistence_result: GateResult
    minio_persistence_result: GateResult
    no_forbidden_side_effects_result: GateResult
    mediascribe_degraded_awareness: DegradedAwarenessStatus
    langfuse_degraded_awareness: DegradedAwarenessStatus
    log_redaction_result: GateResult
    cleanup_result: CleanupResult
    open_risks: list[str] = Field(default_factory=list)
    side_effect_assertions: dict[str, int] = Field(default_factory=lambda: ZERO_SIDE_EFFECT_ASSERTIONS.copy())
    residue_owner: str | None = None
    residue_follow_up_reason: str | None = None

    @model_validator(mode="after")
    def validate_evidence_boundary(self) -> SmokeEvidenceRecord:
        if self.readiness_verdict not in ALLOWED_READINESS_VERDICTS:
            raise ValueError("unsupported readiness verdict")
        if self.readiness_verdict in FORBIDDEN_READINESS_VERDICTS:
            raise ValueError("forbidden readiness verdict")
        if self.smoke_identity_class != SMOKE_IDENTITY_CLASS:
            raise ValueError("smoke identity class must be internal_smoke")
        if self.side_effect_assertions != ZERO_SIDE_EFFECT_ASSERTIONS:
            raise ValueError("021 smoke must not create processing or observability side effects")
        if self.readiness_verdict == "infra_smoke_ready":
            required_pass_gates = {
                "compose_config_result": self.compose_config_result,
                "secret_validation_result": self.secret_validation_result,
                "restore_or_rollback_rehearsal_result": self.restore_or_rollback_rehearsal_result,
                "health_live_result": self.health_live_result,
                "health_ready_result": self.health_ready_result,
                "upload_result": self.upload_result,
                "postgres_persistence_result": self.postgres_persistence_result,
                "minio_persistence_result": self.minio_persistence_result,
                "no_forbidden_side_effects_result": self.no_forbidden_side_effects_result,
                "log_redaction_result": self.log_redaction_result,
            }
            blocked_gates = [name for name, result in required_pass_gates.items() if result != "pass"]
            if blocked_gates:
                raise ValueError(f"infra_smoke_ready requires pass gates: {', '.join(blocked_gates)}")
        if self.cleanup_result != "pass" and not (self.residue_owner and self.residue_follow_up_reason):
            raise ValueError("non-pass cleanup evidence must include residue owner and follow-up reason")
        if self.readiness_verdict == "infra_smoke_ready" and self.cleanup_result != "pass":
            raise ValueError("infra_smoke_ready requires cleanup_result pass")
        return self

    def safe_markdown(self) -> str:
        lines = [
            "# GRAF Infrastructure Smoke Evidence",
            "",
            f"- run_id: `{self.run_id}`",
            f"- date: `{self.date}`",
            f"- branch_or_commit: `{self.branch_or_commit}`",
            f"- public_endpoint: `{self.public_endpoint}`",
            f"- readiness_verdict: `{self.readiness_verdict}`",
            f"- cleanup_result: `{self.cleanup_result}`",
            "",
            "## Side Effects",
        ]
        for key, value in self.side_effect_assertions.items():
            lines.append(f"- {key}={value}")
        lines.extend(["", "## Open Risks"])
        lines.extend(f"- {risk}" for risk in self.open_risks) if self.open_risks else lines.append("- None recorded")
        markdown = "\n".join(lines) + "\n"
        if contains_forbidden_evidence_content(markdown):
            raise ValueError("evidence markdown contains forbidden content")
        return markdown

    def write_safe_markdown(self, path: Path) -> Path:
        markdown = self.safe_markdown()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
        return path


def validate_readiness_verdict(verdict: str) -> ReadinessVerdict:
    if verdict in FORBIDDEN_READINESS_VERDICTS:
        raise ValueError(f"forbidden 021 readiness verdict: {verdict}")
    if verdict not in ALLOWED_READINESS_VERDICTS:
        raise ValueError(f"unsupported 021 readiness verdict: {verdict}")
    return verdict  # type: ignore[return-value]


ROLLBACK_TRIGGER_DECISIONS: dict[str, Literal["halt", "restore", "rollback", "blocked"]] = {
    "dns_tls": "halt",
    "secrets": "halt",
    "health": "halt",
    "migration": "restore",
    "backup": "blocked",
    "restore_rehearsal": "blocked",
    "storage": "halt",
    "disk_full": "halt",
    "unsafe_exposure": "halt",
    "smoke_upload": "rollback",
    "forbidden_content": "halt",
    "cleanup": "blocked",
    "playback_normalization_compatibility": "rollback",
}


def rollback_decision_for_trigger(
    trigger: str,
    *,
    prior_state_reference: str | None = None,
    residue_owner: str | None = None,
    residue_follow_up_reason: str | None = None,
    rollback_target: Literal["raw_pre_099", "compatibility_099", "forward_fix"] | None = None,
    dispatch_stopped: bool | None = None,
    legacy_playback_guard_retained: bool | None = None,
) -> RollbackDecisionRecord:
    if trigger not in ROLLBACK_TRIGGER_DECISIONS:
        raise ValueError(f"unsupported rollback trigger: {trigger}")
    decision = ROLLBACK_TRIGGER_DECISIONS[trigger]
    if trigger == "playback_normalization_compatibility":
        if rollback_target == "raw_pre_099":
            raise ValueError("playback normalization rollback cannot use a raw pre-099 binary")
        if rollback_target not in {"compatibility_099", "forward_fix"}:
            raise ValueError("playback normalization rollback requires a guarded target")
        if dispatch_stopped is not True:
            raise ValueError("playback normalization dispatch must stop before rollback")
        if legacy_playback_guard_retained is not True:
            raise ValueError("playback normalization rollback must retain the legacy playback guard")
    cleanup_obligations = []
    if trigger in {
        "smoke_upload",
        "cleanup",
        "forbidden_content",
        "playback_normalization_compatibility",
    }:
        cleanup_obligations.append("record smoke residue and remove Rec-owned database/object artifacts before retry")
    return RollbackDecisionRecord(
        trigger=trigger,
        decision=decision,
        prior_state_reference=prior_state_reference,
        cleanup_obligations=cleanup_obligations,
        residue_owner=residue_owner,
        residue_follow_up_reason=residue_follow_up_reason,
        rollback_target=rollback_target,
        dispatch_stopped=dispatch_stopped,
        legacy_playback_guard_retained=legacy_playback_guard_retained,
    )


def scan_deployment_evidence_text(text: str) -> None:
    scannable_lines: list[str] = []
    skipping_prohibition = False
    for line in text.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if lowered.startswith(("do not include", "do not commit")):
            skipping_prohibition = True
            continue
        if skipping_prohibition and not stripped:
            skipping_prohibition = False
            continue
        if skipping_prohibition:
            continue
        scannable_lines.append(line)
    scannable_text = "\n".join(scannable_lines)
    if contains_forbidden_evidence_content(scannable_text):
        raise ValueError("deployment evidence contains forbidden content")
    for verdict in FORBIDDEN_READINESS_VERDICTS:
        if verdict in scannable_text:
            raise ValueError(f"deployment evidence contains forbidden verdict: {verdict}")
    if "live_production_enforcement=not_changed" in scannable_text:
        raise ValueError("deployment evidence contains stale RLS production enforcement wording")
    if (
        "production_rls_state_result=pass" in scannable_text
        and "live_production_enforcement=enabled" not in scannable_text
    ):
        raise ValueError("passing production RLS evidence must record enabled enforcement")
