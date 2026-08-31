from __future__ import annotations

import importlib.util
import json
import multiprocessing
from pathlib import Path
import os

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("dev_harness", ROOT / "scripts" / "dev-harness.py")
assert SPEC and SPEC.loader
dev_harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dev_harness)


def run(operation, root, **kwargs):
    old = os.environ.get("GRAF_DEV_STATE_DIR")
    os.environ["GRAF_DEV_STATE_DIR"] = str(root)
    try:
        return getattr(dev_harness, f"operation_{operation}")(type("Args", (), kwargs)())
    finally:
        if old is None:
            os.environ.pop("GRAF_DEV_STATE_DIR", None)
        else:
            os.environ["GRAF_DEV_STATE_DIR"] = old


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


def test_dry_run_does_not_activate_and_reset_requires_confirmation(tmp_path):
    manifest = build(tmp_path, "c" * 40)
    candidate = tmp_path / "manifests" / f"{manifest['manifest_id']}.json"
    run("promote", tmp_path, manifest=str(candidate), dry_run=True)
    assert not (tmp_path / "active-manifest.json").exists()
    with pytest.raises(dev_harness.HarnessError):
        run("reset_data", tmp_path, confirm_dev_reset=False, dry_run=False)


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
