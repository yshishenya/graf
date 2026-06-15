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


def test_rls_validation_report_passes_only_when_all_required_probes_pass() -> None:
    report = RLSValidationReport(environment="postgres_test", probes=_passing_probes())

    assert report.validation_result == "pass"
    assert report.ready_for_production_truth is True


def test_rls_validation_report_blocks_missing_or_failed_probes() -> None:
    probes = _passing_probes()[:-1]
    probes[0] = RLSProbeEvidence(name=probes[0].name, result="blocked", environment="postgres_test")

    report = RLSValidationReport(environment="postgres_test", probes=probes)

    assert report.validation_result == "blocked"
    assert probes[0].name in report.blocking_reasons
    assert REQUIRED_RLS_PROBES[-1] in report.blocking_reasons


def test_live_production_enforcement_requires_read_only_state() -> None:
    report = RLSValidationReport(
        environment="live_production",
        probes=_passing_probes(),
        live_production_decision="not_requested",
    )

    assert report.validation_result == "blocked"
    assert "production_read_only_state_required" in report.blocking_reasons
    assert report.live_production_enforcement == "not_inspected"
