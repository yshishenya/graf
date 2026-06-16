from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

StageStatus = Literal["ready", "degraded", "blocked", "not_accepted", "out_of_scope"]
EvidenceStrength = Literal[
    "live",
    "production_smoke",
    "local_runtime",
    "synthetic",
    "docs_only",
    "missing",
    "blocked",
]
EvidenceType = Literal[
    "command",
    "screenshot",
    "document",
    "endpoint",
    "github",
    "runtime",
    "production_smoke",
    "reference_review",
]
EvidenceScanStatus = Literal["pass", "blocked", "not_applicable", "pending"]
ClaimOutcome = Literal[
    "mvp_loop_ready",
    "internal_pilot_candidate",
    "partial_readiness",
    "pilot_blocked",
    "evidence_blocked",
]
ClaimStatus = Literal["proven", "partial", "blocked"]
ReferenceResult = Literal["pass", "needs_polish", "blocked"]
Severity = Literal["P0", "P1", "P2", "P3"]


class ReadinessEvidence(BaseModel):
    id: str
    type: EvidenceType
    source: str
    captured_at: str
    scope: str
    strength: EvidenceStrength
    safe_to_commit: bool = True
    forbidden_content_scan: EvidenceScanStatus = "pending"
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_commit_boundary(self) -> ReadinessEvidence:
        if self.type == "screenshot" and not self.safe_to_commit:
            raise ValueError("unsafe screenshot evidence cannot be committed")
        if not self.safe_to_commit and self.forbidden_content_scan == "pass":
            raise ValueError("unsafe evidence cannot have a passing scan")
        return self


class LaunchGap(BaseModel):
    id: str
    severity: Severity
    affected_journey: str
    current_evidence: str
    missing_evidence: str
    recommended_next_action: str
    owner_area: Literal["desktop", "web", "server", "infra", "security", "ux", "product", "ops"]
    deferred: bool = False
    deferral_guardrail: str | None = None

    @model_validator(mode="after")
    def validate_gap_action(self) -> LaunchGap:
        if self.severity in {"P0", "P1"} and not self.recommended_next_action.strip():
            raise ValueError("P0/P1 launch gaps require a recommended next action")
        if self.deferred and not self.deferral_guardrail:
            raise ValueError("deferred launch gaps require a deferral guardrail")
        return self


class MvpLoopStage(BaseModel):
    id: str
    label: str
    owner_surface: Literal[
        "macos_native",
        "desktop_embedded_web",
        "web_cabinet",
        "server_backend",
        "production_infra",
        "docs_status",
    ]
    status: StageStatus
    evidence_strength: EvidenceStrength
    evidence_ids: list[str] = Field(default_factory=list)
    launch_gap_ids: list[str] = Field(default_factory=list)
    claim_impact: list[str] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="after")
    def validate_stage_truth(self) -> MvpLoopStage:
        if self.status == "ready" and not self.evidence_ids:
            raise ValueError("ready stage requires at least one evidence record")
        if self.status in {"blocked", "not_accepted"} and not self.launch_gap_ids:
            raise ValueError("blocked stage requires at least one launch gap")
        if self.status == "ready" and self.evidence_strength in {"missing", "blocked"}:
            raise ValueError("ready stage cannot use missing or blocked evidence strength")
        return self


class ReferenceComparison(BaseModel):
    id: str
    surface: Literal[
        "desktop_home",
        "desktop_detail",
        "web_list",
        "web_detail",
        "settings",
        "governance",
        "other",
    ]
    allowed_lessons: list[str]
    implementation_alignment: str
    intentional_differences: list[str] = Field(default_factory=list)
    forbidden_similarity_checks: list[str]
    result: ReferenceResult
    evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_reference_boundary(self) -> ReferenceComparison:
        if self.result == "pass" and not self.forbidden_similarity_checks:
            raise ValueError("passing reference comparisons require forbidden-similarity checks")
        return self


class ReadinessClaim(BaseModel):
    claim: Literal[
        "infra_smoke_ready",
        "desktop_loop_verified",
        "web_review_verified",
        "policy_lifecycle_verified",
        "internal_pilot_candidate",
        "pilot_blocked",
        "mvp_loop_ready",
    ]
    status: ClaimStatus
    required_stage_ids: list[str]
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    blocking_gap_ids: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)


class ClaimSummary(BaseModel):
    outcome: ClaimOutcome = "partial_readiness"
    bounded_claims: list[str] = Field(default_factory=list)
    excluded_claims: list[str] = Field(default_factory=list)
    p0_p1_blockers: int = 0


class ForbiddenContentScan(BaseModel):
    status: Literal["pass", "blocked", "pending"] = "pending"
    commands: list[str] = Field(default_factory=list)
    matches: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_scan_status(self) -> ForbiddenContentScan:
        if self.status == "pass" and self.matches:
            raise ValueError("passing forbidden-content scan cannot include matches")
        return self


class ReadinessReport(BaseModel):
    feature: str = "034-mvp-loop-readiness"
    generated_at: str = "2026-06-16T00:00:00Z"
    deployed_commit: str = "unknown"
    claim_summary: ClaimSummary = Field(default_factory=ClaimSummary)
    stages: list[MvpLoopStage] = Field(default_factory=list)
    evidence: list[ReadinessEvidence] = Field(default_factory=list)
    launch_gaps: list[LaunchGap] = Field(default_factory=list)
    reference_comparisons: list[ReferenceComparison] = Field(default_factory=list)
    forbidden_content_scan: ForbiddenContentScan = Field(default_factory=ForbiddenContentScan)

    @model_validator(mode="after")
    def validate_report_references_and_claims(self) -> ReadinessReport:
        evidence_ids = {item.id for item in self.evidence}
        gap_ids = {gap.id for gap in self.launch_gaps}

        for stage in self.stages:
            missing_evidence = set(stage.evidence_ids) - evidence_ids
            if missing_evidence:
                raise ValueError(f"stage {stage.id} references unknown evidence: {missing_evidence}")
            missing_gaps = set(stage.launch_gap_ids) - gap_ids
            if missing_gaps:
                raise ValueError(f"stage {stage.id} references unknown launch gaps: {missing_gaps}")
        for comparison in self.reference_comparisons:
            missing_evidence = set(comparison.evidence_ids) - evidence_ids
            if missing_evidence:
                raise ValueError(
                    f"reference comparison {comparison.id} references unknown evidence: {missing_evidence}"
                )

        p0_p1_count = sum(1 for gap in self.launch_gaps if gap.severity in {"P0", "P1"})
        if self.claim_summary.outcome == "mvp_loop_ready" and p0_p1_count:
            raise ValueError("mvp_loop_ready cannot be claimed while P0/P1 launch gaps remain")
        if self.claim_summary.outcome == "internal_pilot_candidate" and p0_p1_count:
            raise ValueError("internal_pilot_candidate cannot be claimed while P0/P1 gaps remain")
        if (
            self.forbidden_content_scan.status == "blocked"
            and self.claim_summary.outcome in {"mvp_loop_ready", "internal_pilot_candidate"}
        ):
            raise ValueError("passing launch claims require a non-blocked forbidden-content scan")
        return self
