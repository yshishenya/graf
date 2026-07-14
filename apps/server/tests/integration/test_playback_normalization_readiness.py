from __future__ import annotations

import pytest

from twobrain_rec_server.normalization.statuses import (
    CANONICAL_PROFILE_VERSION,
    VALIDATION_VERSION,
)
from twobrain_rec_server.readiness.default_evidence import build_default_evidence
from twobrain_rec_server.readiness.feature_ids import FEATURE_099_ID
from twobrain_rec_server.readiness.matrix import (
    PLAYBACK_NORMALIZATION_CAPABILITY_GATES,
    evaluate_playback_normalization_capability,
)


def _passing_gates() -> dict[str, str]:
    return {gate: "pass" for gate in PLAYBACK_NORMALIZATION_CAPABILITY_GATES}


def test_media_worker_capability_is_ready_only_when_every_gate_passes() -> None:
    capability = evaluate_playback_normalization_capability(_passing_gates())

    assert capability.state == "ready"
    assert capability.scope == "worker_capability_only"
    assert capability.profile_version == CANONICAL_PROFILE_VERSION
    assert capability.validation_version == VALIDATION_VERSION
    assert capability.blocked_gates == []
    assert capability.recording_readiness_implied is False


def test_retrying_jobs_degrade_intact_worker_without_blocking_capability() -> None:
    capability = evaluate_playback_normalization_capability(
        _passing_gates(),
        retrying_job_count=3,
    )

    assert capability.state == "degraded"
    assert capability.blocked_gates == []
    assert capability.retrying_job_count == 3


@pytest.mark.parametrize(
    "blocked_gate",
    PLAYBACK_NORMALIZATION_CAPABILITY_GATES,
)
def test_any_missing_core_capability_blocks_global_worker_readiness(blocked_gate: str) -> None:
    gates = _passing_gates()
    gates[blocked_gate] = "blocked"

    capability = evaluate_playback_normalization_capability(gates)

    assert capability.state == "blocked"
    assert capability.blocked_gates == [blocked_gate]


def test_capability_rejects_incomplete_or_unknown_gate_sets() -> None:
    missing = _passing_gates()
    missing.pop("schema_0022")
    with pytest.raises(ValueError, match="exact gate set"):
        evaluate_playback_normalization_capability(missing)

    unknown = _passing_gates()
    unknown["meeting_title"] = "pass"
    with pytest.raises(ValueError, match="exact gate set"):
        evaluate_playback_normalization_capability(unknown)


def test_feature_099_default_evidence_caps_claim_at_worker_capability() -> None:
    evidence = build_default_evidence(
        "2026-07-14T00:00:00Z",
        "candidate-sha",
        feature=FEATURE_099_ID,
    )
    item = next(row for row in evidence if row.id == "feature-099-media-worker-capability")

    assert item.scope.startswith("Capability-only")
    assert any("does not prove" in limitation for limitation in item.limitations)
    serialized = item.model_dump_json()
    for forbidden in ("meeting_title", "filename", "object_key", "transcript"):
        assert forbidden not in serialized
