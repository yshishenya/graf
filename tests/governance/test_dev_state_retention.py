from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest


SOURCE_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("dev_harness_retention", SOURCE_ROOT / "scripts" / "dev-harness.py")
assert SPEC and SPEC.loader
dev_harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dev_harness)

IMAGE_ID = "sha256:" + "1" * 64


def manifest(tmp_path: Path, sha: str, feature: str = "269"):
    return dev_harness.build_manifest(sha, feature, root=tmp_path)


def publish_active(state: Path, active: dict, parent: str | None = None) -> None:
    record = dict(active)
    record["parent_manifest_id"] = parent
    state.mkdir(parents=True, exist_ok=True)
    (state / "manifests").mkdir(exist_ok=True)
    dev_harness._write_json(state / "manifests" / f"{record['manifest_id']}.json", record)
    dev_harness._write_json(
        state / "active-manifest.json",
        {
            "schema_version": dev_harness.POINTER_VERSION,
            "manifest_id": record["manifest_id"],
            "runtime_mode": "live",
            "updated_at": dev_harness.now(),
        },
    )


def make_set(state: Path, manifest_id: str, *, archive: bool = False, app: bool = True, build: bool = False) -> Path:
    root = state / "artifacts" / manifest_id
    if archive:
        root.mkdir(parents=True, exist_ok=True)
        (root / "runtime-images.tar").write_bytes(b"archive")
    if app:
        (root / "GRAF Dev.app" / "Contents").mkdir(parents=True, exist_ok=True)
        (root / "GRAF Dev.app" / "Contents" / "Info.plist").write_text("metadata", encoding="utf-8")
    if build:
        (root / "build").mkdir(parents=True, exist_ok=True)
        (root / "build" / "object.o").write_bytes(b"object")
    root.mkdir(parents=True, exist_ok=True)
    return root


def docker_fake(calls: list, *, fail_rm: bool = False):
    def fake_run(command, *, cwd, env=None):
        calls.append(command)
        if command[:3] == ["docker", "image", "inspect"]:
            target = command[-1]
            return target if target.startswith("sha256:") else IMAGE_ID
        if command[:3] == ["docker", "image", "save"]:
            Path(command[command.index("--output") + 1]).write_bytes(b"archive")
            return ""
        if command[:3] == ["docker", "image", "rm"] and fail_rm:
            raise dev_harness.HarnessError("docker unavailable")
        return ""

    return fake_run


def test_build_skips_archive_and_removes_build_directory(monkeypatch, tmp_path):
    sha = "b" * 40
    adapter = dev_harness.GrafLocalAdapter(tmp_path / "root", tmp_path / "state")
    calls: list = []
    monkeypatch.setattr(dev_harness.sys, "platform", "darwin")
    monkeypatch.setattr(dev_harness, "_run_command", docker_fake(calls))
    monkeypatch.setattr(adapter, "_assert_supported", lambda: None)
    monkeypatch.setattr(adapter, "_assert_source_matches_checkout", lambda _: None)
    monkeypatch.setattr(adapter, "_compose_config", lambda _: None)

    def fake_builder(command, *, cwd, env=None):
        calls.append(command)
        bundle = Path(env["GRAF_DEV_APP_BUNDLE"])
        (bundle / "Contents").mkdir(parents=True)
        (bundle / "Contents" / "Info.plist").write_text("metadata", encoding="utf-8")
        build_dir = Path(env["GRAF_DEV_BUILD_DIR"])
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / "object.o").write_bytes(b"object")
        return ""

    monkeypatch.setattr(dev_harness, "_run_command_combined", lambda *args, **kwargs: "")
    monkeypatch.setattr(
        adapter,
        "_measure_signed_app_identity",
        lambda _: ("GRAF Local Code Signing", "identifier pro.2brain.graf.dev", "sha256:" + "e" * 64),
    )

    original_run = dev_harness._run_command

    def dispatch(command, *, cwd, env=None):
        if command[0] == "sh" and command[-1] == str(adapter.build_app_script):
            return fake_builder(command, cwd=cwd, env=env)
        return original_run(command, cwd=cwd, env=env)

    monkeypatch.setattr(dev_harness, "_run_command", dispatch)
    candidate = manifest(tmp_path, sha)

    adapter.build(candidate)

    assert not any(command[:3] == ["docker", "image", "save"] for command in calls)
    artifact_root = tmp_path / "state" / "artifacts" / candidate["manifest_id"]
    assert (artifact_root / "GRAF Dev.app").is_dir()
    assert not (artifact_root / "build").exists()
    assert not (artifact_root / "runtime-images.tar").exists()


def test_promote_archives_previous_manifest_and_removes_stale_sets(monkeypatch, tmp_path):
    state = tmp_path / "state"
    previous = manifest(tmp_path, "a" * 40)
    candidate = manifest(tmp_path, "b" * 40)
    stale = manifest(tmp_path, "c" * 40)
    publish_active(state, previous)
    previous_set = make_set(state, previous["manifest_id"], app=True)
    make_set(state, stale["manifest_id"], archive=True, app=True)
    candidate_set = make_set(state, candidate["manifest_id"], app=True)
    (state / "transactions").mkdir()
    leftover = state / "transactions" / "previous-999-1.app"
    leftover.mkdir()
    (leftover / "Contents").mkdir()

    adapter = dev_harness.GrafLocalAdapter(tmp_path, state)
    calls: list = []
    monkeypatch.setattr(dev_harness, "_run_command", docker_fake(calls))
    monkeypatch.setattr(adapter, "_assert_supported", lambda: None)
    monkeypatch.setattr(adapter, "_assert_source_matches_checkout", lambda _: None)
    monkeypatch.setattr(adapter, "_compose_config", lambda _: None)
    monkeypatch.setattr(adapter, "_assert_manifest_images", lambda *_: None)
    monkeypatch.setattr(adapter, "_runtime_is_live", lambda _: True)
    monkeypatch.setattr(adapter, "_runtime_definition_digest", lambda: "sha256:" + "d" * 64)
    monkeypatch.setattr(adapter, "_app_is_running", lambda _: False)
    monkeypatch.setattr(adapter, "_snapshot_app", lambda: None)
    monkeypatch.setattr(adapter, "_stop_previous", lambda: None)
    monkeypatch.setattr(adapter, "_terminate_dev_app", lambda _: False)
    monkeypatch.setattr(adapter, "_install_app", lambda *_: None)
    monkeypatch.setattr(adapter, "_start_backend", lambda *_: None)
    monkeypatch.setattr(adapter, "_launch_dev_app", lambda _: None)
    monkeypatch.setattr(adapter, "smoke", lambda _: {"app_presentation": "pass", "mode": "live"})
    dev_harness._write_json(
        state / "runtime.json",
        {
            "pid": 101,
            "source_sha": previous["source_sha"],
            "command": str(adapter.start_script),
            "runtime_definition_digest": "sha256:" + "d" * 64,
        },
    )

    adapter.promote(candidate)

    archive = previous_set / "runtime-images.tar"
    assert archive.is_file()
    assert (candidate_set / "GRAF Dev.app").is_dir()
    assert not (state / "artifacts" / stale["manifest_id"]).exists()
    assert not leftover.exists()
    removed_tags = [command[-1] for command in calls if command[:3] == ["docker", "image", "rm"]]
    assert any(tag.startswith(f"graf-dev-immutable:{stale['manifest_id']}-") for tag in removed_tags)
    assert not any(tag.startswith(f"graf-dev-immutable:{previous['manifest_id']}-") for tag in removed_tags)


def test_promote_refuses_when_rollback_target_images_are_unavailable(monkeypatch, tmp_path):
    state = tmp_path / "state"
    previous = manifest(tmp_path, "a" * 40)
    candidate = manifest(tmp_path, "b" * 40)
    publish_active(state, previous)

    adapter = dev_harness.GrafLocalAdapter(tmp_path, state)
    monkeypatch.setattr(adapter, "_assert_supported", lambda: None)
    monkeypatch.setattr(adapter, "_assert_source_matches_checkout", lambda _: None)
    monkeypatch.setattr(adapter, "_compose_config", lambda _: None)
    monkeypatch.setattr(adapter, "_assert_manifest_images", lambda *_: None)
    monkeypatch.setattr(adapter, "_runtime_is_live", lambda _: True)
    monkeypatch.setattr(adapter, "_runtime_definition_digest", lambda: "sha256:" + "d" * 64)
    monkeypatch.setattr(adapter, "_app_is_running", lambda _: False)
    monkeypatch.setattr(adapter, "_snapshot_app", lambda: None)
    monkeypatch.setattr(adapter, "_stop_previous", lambda: None)
    monkeypatch.setattr(adapter, "_terminate_dev_app", lambda _: False)
    monkeypatch.setattr(adapter, "_install_app", lambda *_: None)
    monkeypatch.setattr(adapter, "_start_backend", lambda *_: None)
    monkeypatch.setattr(adapter, "_launch_dev_app", lambda _: None)
    monkeypatch.setattr(adapter, "smoke", lambda _: {"app_presentation": "pass", "mode": "live"})
    dev_harness._write_json(
        state / "runtime.json",
        {
            "pid": 101,
            "source_sha": previous["source_sha"],
            "command": str(adapter.start_script),
            "runtime_definition_digest": "sha256:" + "d" * 64,
        },
    )

    def no_images(command, *, cwd, env=None):
        if command[:3] == ["docker", "image", "inspect"]:
            raise dev_harness.HarnessError("missing image")
        return ""

    monkeypatch.setattr(dev_harness, "_run_command", no_images)

    with pytest.raises(dev_harness.HarnessError, match="rollback target images are unavailable"):
        adapter.promote(candidate)


def test_schema_snapshots_are_removed_only_when_finished(tmp_path):
    state = tmp_path / "state"
    adapter = dev_harness.GrafLocalAdapter(tmp_path, state)
    operation = "upgrade-1"
    snapshot = state / "schema-transactions" / operation
    snapshot.mkdir(parents=True)
    (snapshot / "graf-dev-postgres-data.tar").write_bytes(b"snapshot")
    journal = {"operation_id": operation, "phase": "prepared", "schema_version": "dev-schema-transition.v1"}

    adapter._schema_phase(journal, "migrating")
    assert snapshot.is_dir()

    adapter._schema_phase(journal, "complete")
    assert not snapshot.exists()


def _make_prune_state(tmp_path: Path, *, unfinished: bool = False, rollback_required: bool = False):
    state = tmp_path / "state"
    parent = manifest(tmp_path, "a" * 40)
    active = manifest(tmp_path, "b" * 40)
    stale = manifest(tmp_path, "c" * 40)
    publish_active(state, active, parent=parent["manifest_id"])
    (state / "manifests").mkdir(exist_ok=True)
    dev_harness._write_json(state / "manifests" / f"{parent['manifest_id']}.json", parent)
    make_set(state, parent["manifest_id"], archive=False, app=True)
    make_set(state, active["manifest_id"], app=True)
    stale_set = make_set(state, stale["manifest_id"], archive=True, app=True)
    snapshot = state / "schema-transactions" / "upgrade-99"
    snapshot.mkdir(parents=True)
    (snapshot / "graf-dev-minio-data.tar").write_bytes(b"snapshot")
    if unfinished:
        journal = {
            "schema_version": "dev-schema-transition.v1",
            "operation_id": "upgrade-99",
            "phase": "migrating",
            "previous": parent,
            "target": active,
            "volumes": {"graf-dev-postgres-data": {}, "graf-dev-minio-data": {}},
        }
        dev_harness._write_json(state / "schema-transition.json", journal)
    if rollback_required:
        dev_harness._write_json(
            state / "rollback-required.json",
            {
                "schema_version": "dev-rollback-required.v1",
                "status": "rollback_required",
                "manifest_id": active["manifest_id"],
                "source_sha": active["source_sha"],
                "checked_at": dev_harness.now(),
            },
        )
    return state, active, parent, stale_set, snapshot


def test_prune_dry_run_reports_without_mutation_then_applies(monkeypatch, tmp_path):
    state, active, parent, stale_set, snapshot = _make_prune_state(tmp_path)
    monkeypatch.setenv("GRAF_DEV_STATE_DIR", str(state))
    monkeypatch.setenv("TWOBRAIN_ENV", "development")
    calls: list = []
    monkeypatch.setattr(dev_harness, "_run_command", docker_fake(calls))

    preview = dev_harness.operation_prune(argparse.Namespace(dry_run=True, json=True, live=False))

    assert preview["schema_version"] == dev_harness.PRUNE_RECEIPT_SCHEMA_VERSION
    assert preview["status"] == "ok"
    assert preview["dry_run"] is True
    assert stale_set.exists() and snapshot.exists()
    assert not (state / dev_harness.PRUNE_HISTORY_FILE).exists()
    assert {item["kind"] for item in preview["removed"]} >= {"artifact_set", "schema_snapshot"}

    result = dev_harness.operation_prune(argparse.Namespace(dry_run=False, json=True, live=False))

    assert result["status"] == "ok"
    assert result["bytes_freed"] > 0
    assert not stale_set.exists()
    assert not snapshot.exists()
    assert (state / "artifacts" / active["manifest_id"] / "GRAF Dev.app").is_dir()
    assert (state / "artifacts" / parent["manifest_id"] / "GRAF Dev.app").is_dir()
    history = (state / dev_harness.PRUNE_HISTORY_FILE).read_text(encoding="utf-8").splitlines()
    assert len(history) == 1
    assert json.loads(history[0])["schema_version"] == dev_harness.PRUNE_RECEIPT_SCHEMA_VERSION


@pytest.mark.parametrize("condition", ["unfinished", "rollback_required"])
def test_prune_is_blocked_by_unfinished_transition_or_rollback_required(tmp_path, monkeypatch, condition):
    state, _active, _parent, stale_set, snapshot = _make_prune_state(
        tmp_path,
        unfinished=condition == "unfinished",
        rollback_required=condition == "rollback_required",
    )
    monkeypatch.setenv("GRAF_DEV_STATE_DIR", str(state))
    monkeypatch.setenv("TWOBRAIN_ENV", "development")

    with pytest.raises(dev_harness.HarnessError):
        dev_harness.operation_prune(argparse.Namespace(dry_run=False, json=True, live=False))

    assert stale_set.exists() and snapshot.exists()


def test_prune_reports_partial_when_docker_is_unavailable(tmp_path, monkeypatch):
    state, _active, _parent, stale_set, snapshot = _make_prune_state(tmp_path)
    monkeypatch.setenv("GRAF_DEV_STATE_DIR", str(state))
    monkeypatch.setenv("TWOBRAIN_ENV", "development")
    monkeypatch.setattr(dev_harness, "_run_command", docker_fake([], fail_rm=True))

    result = dev_harness.operation_prune(argparse.Namespace(dry_run=False, json=True, live=False))

    assert result["status"] == "partial"
    assert result["partial_reasons"]
    assert not stale_set.exists() and not snapshot.exists()


def test_prune_receipt_matches_contract_schema_fields(tmp_path, monkeypatch):
    schema_path = SOURCE_ROOT / "specs/269-dev-storage-hygiene/contracts/prune-receipt.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    state, _active, _parent, _stale, _snapshot = _make_prune_state(tmp_path)
    monkeypatch.setenv("GRAF_DEV_STATE_DIR", str(state))
    monkeypatch.setenv("TWOBRAIN_ENV", "development")
    monkeypatch.setattr(dev_harness, "_run_command", docker_fake([]))

    receipt = dev_harness.operation_prune(argparse.Namespace(dry_run=False, json=True, live=False))
    receipt.pop("operation")

    assert set(schema["required"]).issubset(receipt)
    assert receipt["schema_version"] == schema["properties"]["schema_version"]["const"]
    allowed_kinds = set(schema["properties"]["removed"]["items"]["properties"]["kind"]["enum"])
    assert {item["kind"] for item in receipt["removed"]} <= allowed_kinds
    assert receipt["status"] in schema["properties"]["status"]["enum"]
