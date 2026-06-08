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

    @model_validator(mode="after")
    def validate_decision_boundary(self) -> RollbackDecisionRecord:
        if self.decision in {"restore", "rollback"} and not self.prior_state_reference:
            raise ValueError("restore/rollback decisions require prior state reference")
        if self.cleanup_obligations and not (self.residue_owner and self.residue_follow_up_reason):
            raise ValueError("cleanup obligations require residue owner and follow-up reason")
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
            "# 2brain Rec Infrastructure Smoke Evidence",
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
}


def rollback_decision_for_trigger(
    trigger: str,
    *,
    prior_state_reference: str | None = None,
    residue_owner: str | None = None,
    residue_follow_up_reason: str | None = None,
) -> RollbackDecisionRecord:
    if trigger not in ROLLBACK_TRIGGER_DECISIONS:
        raise ValueError(f"unsupported rollback trigger: {trigger}")
    decision = ROLLBACK_TRIGGER_DECISIONS[trigger]
    cleanup_obligations = []
    if trigger in {"smoke_upload", "cleanup", "forbidden_content"}:
        cleanup_obligations.append("record smoke residue and remove Rec-owned database/object artifacts before retry")
    return RollbackDecisionRecord(
        trigger=trigger,
        decision=decision,
        prior_state_reference=prior_state_reference,
        cleanup_obligations=cleanup_obligations,
        residue_owner=residue_owner,
        residue_follow_up_reason=residue_follow_up_reason,
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
