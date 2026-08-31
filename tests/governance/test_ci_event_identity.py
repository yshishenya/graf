from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


identity = _load("ci_event_identity", "ci-event-identity.py")
receipt = _load("ci_receipt", "validate-ci-receipt.py")
train = _load("release_train", "validate-release-train.py")
emit_receipt = _load("emit_ci_receipt", "emit-ci-receipt.py")


def test_pr_identity_uses_head_and_base_sha() -> None:
    result = identity.resolve(
        {
            "number": 42,
            "pull_request": {
                "head": {"sha": "A" * 40},
                "base": {"sha": "B" * 40},
            },
        },
        event_name="pull_request",
    )
    assert result["target_sha"] == "a" * 40
    assert result["base_sha"] == "b" * 40
    assert result["concurrency_key"] == "pr-42"


def test_merge_group_requires_complete_pr_mapping() -> None:
    with pytest.raises(identity.IdentityError):
        identity.resolve(
            {"head_sha": "A" * 40, "base_sha": "B" * 40, "id": "mg-1", "pull_requests": []},
            event_name="merge_group",
        )


def test_merge_group_accepts_github_nested_payload_and_rejects_conflicts() -> None:
    result = identity.resolve(
        {
            "merge_group": {
                "id": "mg-nested",
                "head_sha": "A" * 40,
                "base_sha": "B" * 40,
                "pull_requests": [{"number": 42}, {"number": 43}],
            }
        },
        event_name="merge_group",
    )
    assert result["target_sha"] == "a" * 40
    assert result["base_sha"] == "b" * 40
    assert result["pull_request_numbers"] == [42, 43]
    with pytest.raises(identity.IdentityError, match="conflicting values"):
        identity.resolve(
            {
                "head_sha": "A" * 40,
                "merge_group": {"head_sha": "B" * 40, "base_sha": "C" * 40, "id": "mg-1", "pull_requests": [{"number": 42}]},
            },
            event_name="merge_group",
        )


def test_manual_requires_explicit_exact_sha() -> None:
    with pytest.raises(identity.IdentityError):
        identity.resolve({"inputs": {"target_sha": "not-a-sha"}}, event_name="workflow_dispatch")


def test_manual_accepts_actions_requested_sha_input() -> None:
    sha = "a" * 40
    assert identity.resolve({"inputs": {"requested_sha": sha}}, event_name="workflow_dispatch")["target_sha"] == sha


def test_manual_rejects_conflicting_sha_aliases() -> None:
    with pytest.raises(identity.IdentityError):
        identity.resolve({"inputs": {"target_sha": "a" * 40, "requested_sha": "b" * 40}}, event_name="workflow_dispatch")


def test_identity_rejects_event_name_conflict_and_unsafe_merge_group_id() -> None:
    with pytest.raises(identity.IdentityError, match="conflicts"):
        identity.resolve({"event_name": "merge_group", "inputs": {"target_sha": "a" * 40}}, event_name="workflow_dispatch")
    with pytest.raises(identity.IdentityError, match="unsafe"):
        identity.resolve(
            {"head_sha": "a" * 40, "base_sha": "b" * 40, "id": "mg\n227", "pull_requests": [{"number": 1}]},
            event_name="merge_group",
        )


def test_receipt_adapter_binds_identity_and_evidence(tmp_path: Path) -> None:
    sha = "a" * 40
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps({
        "status": "passed",
        "requested_sha": sha,
        "observed_sha_start": sha,
        "observed_sha_end": sha,
        "started_at": "2026-08-31T00:00:00Z",
        "finished_at": "2026-08-31T00:01:00Z",
    }), encoding="utf-8")
    args = type("Args", (), {
        "workflow": "governance-fast", "run_id": "1", "run_attempt": 1,
        "workflow_url": "https://github.com/o/r/actions/runs/1", "evidence": evidence_path,
    })()
    value = emit_receipt.build(
        {"event_name": "merge_group", "target_sha": sha, "base_sha": "b" * 40,
         "pull_request_numbers": [1], "merge_group_id": "mg-1", "concurrency_key": "merge-group-mg-1"},
        json.loads(evidence_path.read_text(encoding="utf-8")), args,
    )
    assert receipt.validate(value) == []


def test_receipt_adapter_maps_cancelled_run_to_ambiguous_cleanliness(tmp_path: Path) -> None:
    sha = "a" * 40
    evidence_path = tmp_path / "evidence.json"
    evidence = {"status": "cancelled", "requested_sha": sha, "observed_sha_start": sha,
                "observed_sha_end": sha, "started_at": "2026-08-31T00:00:00Z",
                "finished_at": "2026-08-31T00:01:00Z", "reason": "cancelled"}
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    args = type("Args", (), {"workflow": "governance-fast", "run_id": "1", "run_attempt": 1,
                              "workflow_url": "https://github.com/o/r/actions/runs/1",
                              "evidence": evidence_path})()
    value = emit_receipt.build(
        {"event_name": "pull_request", "target_sha": sha, "base_sha": "b" * 40,
         "pull_request_numbers": [1], "merge_group_id": None, "concurrency_key": "pr-1"},
        evidence, args,
    )
    assert value["final_cleanliness"] == "ambiguous"
    assert receipt.validate(value) == []


def test_cancelled_receipt_is_valid_terminal_metadata_but_not_success() -> None:
    sha = "a" * 40
    value = {
        "schema_version": 1,
        "status": "cancelled",
        "event_name": "pull_request",
        "workflow": "governance",
        "run_id": "run-1",
        "run_attempt": 1,
        "workflow_url": "https://github.com/o/r/actions/runs/1",
        "target_sha": sha,
        "base_sha": "b" * 40,
        "pull_request_numbers": [1],
        "merge_group_id": None,
        "requested_sha": sha,
        "observed_sha_start": sha,
        "observed_sha_end": sha,
        "final_cleanliness": "ambiguous",
        "local_evidence_digest": "sha256:" + "c" * 64,
        "started_at": "2026-08-31T00:00:00Z",
        "finished_at": "2026-08-31T00:01:00Z",
        "reason": "runner cancelled",
        "conclusion": "cancelled",
        "cancellation_state": "cancelled",
        "supersession_state": "none",
    }
    assert receipt.validate(value) == []
    assert value["status"] != "passed"


def test_release_train_rejects_synthetic_sha_as_release_source() -> None:
    value = {
        "schema_version": 1,
        "train_id": "train-1",
        "source_sha": "a" * 40,
        "base_sha": "b" * 40,
        "synthetic_merge_sha": "a" * 40,
        "included_prs": [1, 2, 3],
        "feature_ids": ["216"],
        "merge_group_ids": ["mg-1"],
        "pr_receipts": ["pr-1"],
        "merge_group_receipts": ["mg-1"],
        "changelog_digest": "sha256:" + "c" * 64,
        "authoritative_full_ci_receipt": "full-1",
        "decision": "go",
        "rollback_target": "d" * 40,
    }
    assert any("distinct" in error for error in train.validate(value))
