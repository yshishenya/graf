from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

RLSProbeResult = Literal["pass", "blocked", "failed"]
RLSEnvironment = Literal["local", "postgres_test", "production_like", "live_production"]
RLSValidationResult = Literal["pass", "blocked"]
RLSLiveProductionDecision = Literal["not_requested", "approved"]
RLSLiveProductionEnforcement = Literal["not_changed"]

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
    live_production_enforcement: RLSLiveProductionEnforcement = "not_changed"

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
        if self.environment == "live_production" and self.live_production_decision != "approved":
            reasons.append("live_production_decision_required")
        return reasons

    @property
    def validation_result(self) -> RLSValidationResult:
        return "pass" if not self.blocking_reasons else "blocked"

    @property
    def ready_for_operator_decision(self) -> bool:
        return self.environment in {"postgres_test", "production_like"} and self.validation_result == "pass"

    def evidence_lines(self) -> list[str]:
        lines = [
            f"rls_validation_result={self.validation_result}",
            f"environment={self.environment}",
            f"live_production_enforcement={self.live_production_enforcement}",
        ]
        if self.blocking_reasons:
            lines.append(f"blocking_reasons={','.join(self.blocking_reasons)}")
        lines.append(f"ready_for_operator_decision={str(self.ready_for_operator_decision).lower()}")
        return lines
