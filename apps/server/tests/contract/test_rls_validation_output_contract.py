from __future__ import annotations

from twobrain_rec_server.db.rls_validation import (
    REQUIRED_RLS_PROBES,
    RLSProbeEvidence,
    RLSValidationReport,
)


def _passing_probes() -> list[RLSProbeEvidence]:
    return [
        RLSProbeEvidence(name=name, result="pass", environment="postgres_test")
        for name in REQUIRED_RLS_PROBES
    ]


def test_test_probe_output_is_explicitly_not_live_production() -> None:
    report = RLSValidationReport(environment="postgres_test")
    output = "\n".join(report.evidence_lines())

    assert "rls_validation_result=blocked" in output
    assert "live_production_probe=not_attempted" in output
    assert "destructive_probe_database=not_provided" in output
    assert "live_production_enforcement=not_inspected" in output
    assert "ready_for_production_truth=false" in output
    assert "not_changed" not in output


def test_disposable_probe_pass_output_can_support_production_truth() -> None:
    report = RLSValidationReport(
        environment="postgres_test",
        probes=_passing_probes(),
        destructive_probe_database="disposable",
    )
    output = "\n".join(report.evidence_lines())

    assert report.validation_result == "pass"
    assert report.ready_for_production_truth is True
    assert "destructive_probe_database=disposable" in output
    assert "ready_for_production_truth=true" in output
    assert "live_production_enforcement=not_inspected" in output
    assert "not_changed" not in output


def test_failed_probe_names_are_blocking_reasons() -> None:
    probes = _passing_probes()
    probes[0] = RLSProbeEvidence(name=probes[0].name, result="failed", environment="postgres_test")
    report = RLSValidationReport(
        environment="postgres_test",
        probes=probes,
        destructive_probe_database="explicit_test",
    )

    assert report.validation_result == "blocked"
    assert probes[0].name in report.blocking_reasons
