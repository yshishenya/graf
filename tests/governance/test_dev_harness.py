from __future__ import annotations

import importlib.util
import json
import multiprocessing
from pathlib import Path
import os
import subprocess
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("dev_harness", ROOT / "scripts" / "dev-harness.py")
assert SPEC and SPEC.loader
dev_harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dev_harness)
CONTRACTS_SPEC = importlib.util.spec_from_file_location(
    "dev_harness_ci_contracts", ROOT / "harness/src/dev_harness/ci_contracts.py"
)
assert CONTRACTS_SPEC and CONTRACTS_SPEC.loader
ci_contracts = importlib.util.module_from_spec(CONTRACTS_SPEC)
CONTRACTS_SPEC.loader.exec_module(ci_contracts)


def run(operation, root, **kwargs):
    old = dev_harness.state_dir
    dev_harness.state_dir = lambda **_kwargs: Path(root)
    try:
        return getattr(dev_harness, f"operation_{operation}")(type("Args", (), kwargs)())
    finally:
        dev_harness.state_dir = old


def build(root, sha, feature="216"):
    return run("build", root, sha=sha, feature_id=feature, operator="test", migration_head="dev-head", dry_run=False)["manifest"]


def test_build_promote_status_smoke_and_rollback(tmp_path):
    sha_a = "a" * 40
    sha_b = "b" * 40
    first = build(tmp_path, sha_a)
    run("promote", tmp_path, manifest=str(tmp_path / "manifests" / f"{first['manifest_id']}.json"), dry_run=False)
    assert run("status", tmp_path)["manifest"]["source_sha"] == sha_a
    assert run("smoke", tmp_path, fixture=True)["status"] == "pass"
    second = build(tmp_path, sha_b)
    run("promote", tmp_path, manifest=str(tmp_path / "manifests" / f"{second['manifest_id']}.json"), dry_run=False)
    assert run("rollback", tmp_path, manifest_id=None, dry_run=False)["manifest"]["source_sha"] == sha_a


def test_portable_event_identity_resolves_nested_merge_group() -> None:
    result = ci_contracts.resolve_event_identity(
        {"merge_group": {"head_sha": "a" * 40, "base_sha": "b" * 40,
                          "id": "mg-1", "pull_requests": [{"number": 7}]}},
        "merge_group",
    )
    assert result["target_sha"] == "a" * 40
    assert result["pull_request_numbers"] == [7]


def test_portable_receipt_validator_rejects_stale_success() -> None:
    sha = "a" * 40
    receipt = {
        "schema_version": 1, "status": "passed", "event_name": "pull_request",
        "workflow": "governance", "run_id": "run-1", "run_attempt": 1,
        "workflow_url": "https://github.com/example/project/actions/runs/1",
        "target_sha": sha, "base_sha": "b" * 40, "pull_request_numbers": [1],
        "merge_group_id": None, "requested_sha": sha, "observed_sha_start": sha,
        "observed_sha_end": "c" * 40, "final_cleanliness": "pass",
        "local_evidence_digest": "sha256:" + "d" * 64,
        "started_at": "2026-01-01T00:00:00Z", "finished_at": "2026-01-01T00:01:00Z",
    }
    assert ci_contracts.ci_receipt(receipt)


def test_portable_receipt_matches_canonical_fail_closed_contract() -> None:
    sha = "a" * 40
    good = {
        "schema_version": 1, "status": "passed", "event_name": "pull_request",
        "workflow": "governance", "run_id": "run-1", "run_attempt": 1,
        "workflow_url": "https://github.com/example/project/actions/runs/1",
        "target_sha": sha, "base_sha": "b" * 40, "pull_request_numbers": [1],
        "merge_group_id": None, "requested_sha": sha, "observed_sha_start": sha,
        "observed_sha_end": sha, "final_cleanliness": "pass",
        "local_evidence_digest": "sha256:" + "c" * 64,
        "started_at": "2026-01-01T00:00:00Z", "finished_at": "2026-01-01T00:01:00Z",
    }
    assert ci_contracts.ci_receipt(good) == []
    assert ci_contracts.ci_receipt({**good, "raw_transcript": "private"})
    assert ci_contracts.ci_receipt({**good, "workflow_url": "http://example.test"})
    assert ci_contracts.ci_receipt({**good, "local_evidence_digest": "bad"})
    assert ci_contracts.ci_receipt({**good, "merge_group_id": "mg/1"})
    assert ci_contracts.ci_receipt({**good, "conclusion": "failed"})
    assert ci_contracts.ci_receipt({**good, "observed_sha_end": "d" * 40})


def test_live_rollback_publishes_pointer_only_after_verified_adapter(monkeypatch, tmp_path):
    first = build(tmp_path, "a" * 40)
    run("promote", tmp_path, manifest=str(tmp_path / "manifests" / f"{first['manifest_id']}.json"), dry_run=False)
    second = build(tmp_path, "b" * 40)
    run("promote", tmp_path, manifest=str(tmp_path / "manifests" / f"{second['manifest_id']}.json"), dry_run=False)
    before = json.loads((tmp_path / "active-manifest.json").read_text(encoding="utf-8"))
    calls = []

    class FakeAdapter:
        def __init__(self, _root, _state):
            pass

        def rollback(self, active, target):
            calls.append((active["source_sha"], target["source_sha"]))
            return {"mode": "live", "checks": {"backend_health": "pass"}}

    monkeypatch.setattr(dev_harness, "GrafLocalAdapter", FakeAdapter)
    result = run("rollback", tmp_path, manifest_id=None, dry_run=False, live=True)

    after = json.loads((tmp_path / "active-manifest.json").read_text(encoding="utf-8"))
    assert calls == [("b" * 40, "a" * 40)]
    assert before["manifest_id"] != after["manifest_id"]
    assert after["manifest_id"] == first["manifest_id"]
    assert result["adapter"]["checks"]["backend_health"] == "pass"
    restored = json.loads((tmp_path / "manifests" / f"{first['manifest_id']}.json").read_text(encoding="utf-8"))
    assert restored["health"]["result"] == "pass"


def test_build_same_active_sha_is_idempotent_and_preserves_active_record(tmp_path):
    sha = "a" * 40
    first = build(tmp_path, sha)
    run("promote", tmp_path, manifest=str(tmp_path / "manifests" / f"{first['manifest_id']}.json"), dry_run=False)
    active_before = json.loads((tmp_path / "manifests" / f"{first['manifest_id']}.json").read_text())
    rebuilt = run("build", tmp_path, sha=sha, feature_id="216", operator="test", migration_head="dev-head", dry_run=False)
    assert rebuilt["idempotent"] is True
    assert rebuilt["manifest"]["status"] == "active"
    assert run("status", tmp_path)["manifest"]["status"] == "active"


def test_manifest_rejects_unknown_and_sensitive_fields(tmp_path):
    manifest = build(tmp_path, "1" * 40)
    manifest["raw_transcript"] = "must never enter Dev metadata"
    path = tmp_path / "unsafe.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(dev_harness.HarnessError, match="unsupported fields|forbidden"):
        run("promote", tmp_path, manifest=str(path), dry_run=False)


def test_manifest_runtime_validator_requires_schema_fields_and_status(tmp_path):
    manifest = build(tmp_path, "1" * 40)
    manifest.pop("status")
    path = tmp_path / "missing-status.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(dev_harness.HarnessError, match="manifest missing required fields: status"):
        run("promote", tmp_path, manifest=str(path), dry_run=False)

    manifest = build(tmp_path, "2" * 40)
    manifest["status"] = "not-a-status"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(dev_harness.HarnessError, match="manifest status is invalid"):
        run("promote", tmp_path, manifest=str(path), dry_run=False)


def test_live_build_does_not_claim_existing_metadata_is_a_live_artifact(monkeypatch, tmp_path):
    sha = "2" * 40
    first = build(tmp_path, sha)
    run("promote", tmp_path, manifest=str(tmp_path / "manifests" / f"{first['manifest_id']}.json"), dry_run=False)
    active_before = json.loads((tmp_path / "manifests" / f"{first['manifest_id']}.json").read_text())
    calls = []

    class FakeAdapter:
        def __init__(self, _root, _state):
            pass

        def build(self, manifest):
            calls.append(manifest["source_sha"])
            return {"mode": "live", "app_bundle_digest": "sha256:" + "3" * 64}

    monkeypatch.setattr(dev_harness, "GrafLocalAdapter", FakeAdapter)
    run(
        "build", tmp_path, sha=sha, feature_id="216", operator="test",
        migration_head="dev-head", dry_run=False, live=True,
    )
    assert calls == [sha]
    assert json.loads((tmp_path / "manifests" / f"{first['manifest_id']}.json").read_text()) == active_before


def test_live_build_rebuilds_when_existing_app_digest_drifted(monkeypatch, tmp_path):
    sha = "3" * 40
    first = build(tmp_path, sha)
    run("promote", tmp_path, manifest=str(tmp_path / "manifests" / f"{first['manifest_id']}.json"), dry_run=False)
    bundle = tmp_path / "artifacts" / first["manifest_id"] / "GRAF Dev.app" / "Contents"
    bundle.mkdir(parents=True)
    marker = bundle / "marker"
    marker.write_text("before", encoding="utf-8")
    active_path = tmp_path / "manifests" / f"{first['manifest_id']}.json"
    active = json.loads(active_path.read_text(encoding="utf-8"))
    active["components"]["macos_app"]["digest"] = dev_harness._tree_digest(bundle.parent)
    active_path.write_text(json.dumps(active), encoding="utf-8")
    marker.write_text("after", encoding="utf-8")
    calls = []

    class FakeAdapter:
        def __init__(self, _root, state):
            self.state = state

        def build(self, manifest):
            calls.append(manifest["source_sha"])
            rebuilt = self.state / "artifacts" / manifest["manifest_id"] / "GRAF Dev.app"
            (rebuilt / "Contents").mkdir(parents=True, exist_ok=True)
            (rebuilt / "Contents" / "marker").write_text("rebuilt", encoding="utf-8")
            manifest["components"]["macos_app"]["digest"] = dev_harness._tree_digest(rebuilt)
            return {"mode": "live", "app_bundle_digest": manifest["components"]["macos_app"]["digest"]}

    monkeypatch.setattr(dev_harness, "GrafLocalAdapter", FakeAdapter)
    run(
        "build", tmp_path, sha=sha, feature_id="216", operator="test",
        migration_head="dev-head", dry_run=False, live=True,
    )
    assert calls == [sha]


def test_metadata_only_promote_refuses_live_active_target(tmp_path):
    first = build(tmp_path, "4" * 40)
    run("promote", tmp_path, manifest=str(tmp_path / "manifests" / f"{first['manifest_id']}.json"), dry_run=False)
    (tmp_path / "active-manifest.json").write_text(
        json.dumps({"schema_version": dev_harness.POINTER_VERSION, "runtime_mode": "live", "manifest_id": first["manifest_id"]}),
        encoding="utf-8",
    )
    second = build(tmp_path, "5" * 40)
    with pytest.raises(dev_harness.HarnessError, match="metadata-only promotion is blocked"):
        run("promote", tmp_path, manifest=str(tmp_path / "manifests" / f"{second['manifest_id']}.json"), dry_run=False)


def test_reset_refuses_owned_live_runtime(monkeypatch, tmp_path):
    build(tmp_path, "4" * 40)
    dev_harness._write_json(tmp_path / "runtime.json", {"pid": 42, "source_sha": "4" * 40})

    class FakeAdapter:
        def __init__(self, _root, _state):
            pass

        def _runtime_is_live(self, record):
            return record.get("pid") == 42

    monkeypatch.setattr(dev_harness, "GrafLocalAdapter", FakeAdapter)
    with pytest.raises(dev_harness.HarnessError, match="cannot reset Dev metadata"):
        run("reset_data", tmp_path, confirm_dev_reset=True, dry_run=False)


def test_reset_refuses_runtime_with_unproven_ownership(monkeypatch, tmp_path):
    build(tmp_path, "5" * 40)
    dev_harness._write_json(tmp_path / "runtime.json", {"pid": 42, "source_sha": "5" * 40})

    class FakeAdapter:
        def __init__(self, _root, _state):
            pass

        def _runtime_is_live(self, _record):
            return False

    monkeypatch.setattr(dev_harness, "GrafLocalAdapter", FakeAdapter)
    with pytest.raises(dev_harness.HarnessError, match="runtime ownership cannot be proven"):
        run("reset_data", tmp_path, confirm_dev_reset=True, dry_run=False)


def test_build_requires_or_resolves_feature_identity(tmp_path, monkeypatch):
    monkeypatch.delenv("GRAF_FEATURE_ID", raising=False)
    monkeypatch.setattr(dev_harness, "_repo_root", lambda: tmp_path / "repo")
    with pytest.raises(dev_harness.HarnessError, match="feature id is required"):
        run("build", tmp_path, sha="a" * 40, feature_id=None, operator="test", migration_head="dev-head", dry_run=True)
    pointer = tmp_path / "repo" / ".specify"
    pointer.mkdir(parents=True)
    (pointer / "feature.json").write_text(json.dumps({"feature_id": "216"}), encoding="utf-8")
    result = run("build", tmp_path, sha="a" * 40, feature_id=None, operator="test", migration_head="dev-head", dry_run=True)
    assert result["manifest"]["feature_id"] == "216"


def test_build_resolves_migration_head_for_real_checkout(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / "apps" / "server").mkdir(parents=True)
    (repo / "apps" / "server" / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")
    monkeypatch.setattr(dev_harness, "_repo_root", lambda: repo)
    calls = []

    def fake_run(command, *, cwd, env=None):
        calls.append((command, cwd))
        return "0085_merge_summary_mediascribe (head)"

    monkeypatch.setattr(dev_harness, "_run_command", fake_run)
    result = run(
        "build",
        tmp_path / "state",
        sha="a" * 40,
        feature_id="216",
        operator="test",
        migration_head="unknown",
        dry_run=True,
    )

    assert result["manifest"]["migration_head"] == "0085_merge_summary_mediascribe"
    assert calls == [(["uv", "run", "alembic", "heads"], repo / "apps" / "server")]


def test_dry_run_does_not_activate_and_reset_requires_confirmation(tmp_path):
    manifest = build(tmp_path, "c" * 40)
    candidate = tmp_path / "manifests" / f"{manifest['manifest_id']}.json"
    run("promote", tmp_path, manifest=str(candidate), dry_run=True)
    assert not (tmp_path / "active-manifest.json").exists()
    with pytest.raises(dev_harness.HarnessError):
        run("reset_data", tmp_path, confirm_dev_reset=False, dry_run=False)


def test_promote_rejects_candidate_with_different_migration_head(tmp_path):
    active = build(tmp_path, "a" * 40)
    run("promote", tmp_path, manifest=str(tmp_path / "manifests" / f"{active['manifest_id']}.json"), dry_run=False)
    candidate = build(tmp_path, "b" * 40)
    candidate["migration_head"] = "other-head"
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(candidate), encoding="utf-8")
    with pytest.raises(dev_harness.HarnessError, match="migration_head"):
        run("promote", tmp_path, manifest=str(path), dry_run=False)


def test_mismatched_component_and_production_boundary_are_rejected(tmp_path):
    manifest = build(tmp_path, "d" * 40)
    manifest["components"]["frontend"]["source_sha"] = "e" * 40
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(dev_harness.HarnessError, match="frontend"):
        run("promote", tmp_path, manifest=str(bad), dry_run=False)
    os.environ["GRAF_DEV_STATE_DIR"] = str(tmp_path / "production-data")
    try:
        with pytest.raises(dev_harness.HarnessError, match="production"):
            dev_harness.state_dir()
    finally:
        os.environ.pop("GRAF_DEV_STATE_DIR", None)


def test_live_state_cannot_be_split_by_worktree_override(monkeypatch, tmp_path):
    monkeypatch.setenv("GRAF_DEV_STATE_DIR", str(tmp_path / "other-worktree-state"))
    with pytest.raises(dev_harness.HarnessError, match="cannot override the repository-global state"):
        dev_harness.state_dir(live=True)


def test_repository_identity_failure_is_fail_closed(monkeypatch, tmp_path):
    monkeypatch.delenv("GRAF_DEV_STATE_DIR", raising=False)
    monkeypatch.setattr(dev_harness, "_repo_root", lambda: tmp_path)

    def fail_git(*_args, **_kwargs):
        raise subprocess.CalledProcessError(128, "git")

    monkeypatch.setattr(dev_harness.subprocess, "run", fail_git)
    with pytest.raises(dev_harness.HarnessError, match="repository-global Git metadata"):
        dev_harness.state_dir()


def test_repository_identity_is_shared_by_linked_worktrees(monkeypatch, tmp_path):
    common = tmp_path / "repo" / ".git"
    common.mkdir(parents=True)
    roots = [tmp_path / "worktree-a", tmp_path / "worktree-b"]

    def fake_run(_command, *, cwd, **_kwargs):
        assert cwd in roots
        return SimpleNamespace(stdout=str(common) + "\n")

    monkeypatch.setattr(dev_harness.subprocess, "run", fake_run)
    monkeypatch.setattr(dev_harness, "_repo_root", lambda: roots[0])
    first = dev_harness._repository_identity()
    monkeypatch.setattr(dev_harness, "_repo_root", lambda: roots[1])
    second = dev_harness._repository_identity()
    assert first == second


def _promote_worker(root: str, manifest: str, queue) -> None:
    try:
        result = run("promote", Path(root), manifest=manifest, dry_run=False)
        queue.put(("pass", result["manifest"]["manifest_id"]))
    except Exception as exc:  # pragma: no cover - exercised by process race.
        queue.put(("fail", str(exc)))


def test_concurrent_promote_is_serialized(tmp_path):
    first = build(tmp_path, "f" * 40)
    candidate = str(tmp_path / "manifests" / f"{first['manifest_id']}.json")
    queue = multiprocessing.Queue()
    processes = [multiprocessing.Process(target=_promote_worker, args=(str(tmp_path), candidate, queue)) for _ in range(2)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(10)
    outcomes = [queue.get(timeout=2) for _ in processes]
    assert all(process.exitcode == 0 for process in processes)
    # The lock serializes the operation and the stale-parent check refuses the
    # second writer; it must never silently replace the first active manifest.
    assert sum(outcome[0] == "pass" for outcome in outcomes) == 1
    assert sum(outcome[0] == "fail" for outcome in outcomes) == 1
    assert run("status", tmp_path)["manifest"]["source_sha"] == "f" * 40
