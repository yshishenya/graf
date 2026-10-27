from __future__ import annotations

from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest


SOURCE_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("dev_harness_adapter", SOURCE_ROOT / "scripts" / "dev-harness.py")
assert SPEC and SPEC.loader
dev_harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dev_harness)


def manifest(tmp_path: Path, sha: str = "a" * 40, feature: str = "216"):
    return dev_harness.build_manifest(sha, feature, root=tmp_path)


def test_live_adapter_build_is_explicit_and_uses_only_dev_environment(monkeypatch, tmp_path):
    sha = "a" * 40
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", "postgresql://production.example/secret")
    monkeypatch.setenv("TWOBRAIN_API_KEY", "should-not-cross-boundary")

    env = adapter._env(manifest(tmp_path, sha))

    assert env["TWOBRAIN_ENV"] == "development"
    assert env["TWOBRAIN_DATABASE_URL"].startswith("postgresql+asyncpg://twobrain_rec")
    assert "TWOBRAIN_API_KEY" not in env
    assert env["GRAF_DEV_ORIGIN"] == "http://127.0.0.1:8081"


def test_build_env_replaces_inherited_image_overrides(tmp_path, monkeypatch):
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    monkeypatch.setenv("GRAF_DEV_API_IMAGE", "production.example/api:latest")

    env = adapter._env(manifest(tmp_path), pin_images=False)

    assert env["GRAF_DEV_API_IMAGE"] == "graf-dev-api:latest"


def test_live_build_runs_compose_backend_and_signed_app_adapter(monkeypatch, tmp_path):
    sha = "b" * 40
    fake_root = tmp_path / "root"
    adapter = dev_harness.GrafLocalAdapter(fake_root, tmp_path / "state")
    # This suite substitutes the runtime; real binding is covered by ownership tests.
    monkeypatch.setattr(dev_harness, "_state_ownership", lambda root, **kw: root == adapter.state)
    for path in (
        adapter.compose_file,
        adapter.start_script,
        adapter.build_app_script,
        adapter.install_app_script,
        adapter.app_lifecycle_script,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    monkeypatch.setattr(dev_harness.sys, "platform", "darwin")
    calls = []

    def fake_run(command, *, cwd, env=None):
        calls.append(command)
        if command[:2] == ["git", "rev-parse"]:
            return sha
        if command[:3] == ["docker", "image", "inspect"]:
            return "sha256:" + "1" * 64
        if command[:3] == ["docker", "image", "save"]:
            Path(command[command.index("--output") + 1]).write_bytes(b"archive")
        if command[0] == "sh" and command[-1] == str(adapter.build_app_script):
            bundle = Path(env["GRAF_DEV_APP_BUNDLE"])
            (bundle / "Contents").mkdir(parents=True)
            (bundle / "Contents" / "Info.plist").write_text("metadata", encoding="utf-8")
        return ""

    monkeypatch.setattr(dev_harness, "_run_command", fake_run)
    monkeypatch.setattr(
        adapter,
        "_measure_signed_app_identity",
        lambda _: ("GRAF Local Code Signing", "identifier pro.2brain.graf.dev", "sha256:" + "e" * 64),
    )
    result = adapter.build(manifest(tmp_path, sha))

    assert result["mode"] == "live"
    assert [command[:2] for command in calls[:4]] == [
        ["git", "rev-parse"],
        ["git", "status"],
        ["docker", "compose"],
        ["uv", "run"],
    ]
    assert calls[-1][0:2] == ["sh", str(adapter.build_app_script)]
    assert result["app_bundle_digest"].startswith("sha256:")
    pulls = [command[command.index("pull"):] for command in calls if "pull" in command]
    assert pulls == [
        ["pull", "--quiet", "rec-temporal", "rec-postgres"],
        ["pull", "--quiet", "--policy", "missing", "rec-minio", "rec-minio-init"],
    ]

@pytest.mark.parametrize("missing_service", ["rec-minio", "rec-minio-init"])
def test_live_build_stops_before_archive_and_app_when_missing_image_cannot_pull(monkeypatch, tmp_path, missing_service):
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path / "state")
    monkeypatch.setattr(adapter, "_assert_supported", lambda: None)
    monkeypatch.setattr(adapter, "_assert_source_matches_checkout", lambda _: None)
    monkeypatch.setattr(adapter, "_compose_config", lambda _: None)
    calls = []

    def run(command, *, cwd, env=None):
        calls.append(command)
        if "pull" in command and missing_service in command:
            assert command[command.index("--policy") + 1] == "missing"
            raise dev_harness.HarnessError("image unavailable")
        return ""

    monkeypatch.setattr(dev_harness, "_run_command", run)
    with pytest.raises(dev_harness.HarnessError, match="image unavailable"):
        adapter.build(manifest(tmp_path))
    assert not any(command[:3] == ["docker", "image", "save"] for command in calls)
    assert not any(command[0] == "sh" for command in calls)
    assert not (adapter.state / "artifacts").exists()


def test_live_build_records_and_preserves_every_compose_image_for_future_features(monkeypatch, tmp_path):
    sha = "b" * 40
    fake_root = tmp_path / "root"
    adapter = dev_harness.GrafLocalAdapter(fake_root, tmp_path / "state")
    monkeypatch.setattr(dev_harness, "_state_ownership", lambda root, **kw: root == adapter.state)
    for path in (
        adapter.compose_file,
        adapter.start_script,
        adapter.build_app_script,
        adapter.install_app_script,
        adapter.app_lifecycle_script,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    monkeypatch.setattr(dev_harness.sys, "platform", "darwin")
    calls = []
    image_id = "sha256:" + "1" * 64

    def fake_run(command, *, cwd, env=None):
        calls.append(command)
        if command[:2] == ["git", "rev-parse"]:
            return sha
        if command[:3] == ["docker", "image", "inspect"]:
            return image_id
        if command[:3] == ["docker", "image", "save"]:
            Path(command[command.index("--output") + 1]).write_bytes(b"archive")
        if command[0] == "sh" and command[-1] == str(adapter.build_app_script):
            bundle = Path(env["GRAF_DEV_APP_BUNDLE"])
            (bundle / "Contents").mkdir(parents=True)
            (bundle / "Contents" / "Info.plist").write_text("metadata", encoding="utf-8")
        return ""

    monkeypatch.setattr(dev_harness, "_run_command", fake_run)
    monkeypatch.setattr(
        adapter,
        "_measure_signed_app_identity",
        lambda _: ("GRAF Local Code Signing", "identifier pro.2brain.graf.dev", "sha256:" + "e" * 64),
    )
    candidate = manifest(tmp_path, sha, feature="230")

    adapter.build(candidate)

    assert candidate["components"]["storage_init"]["digest"] == image_id
    tag_calls = [command for command in calls if command[:3] == ["docker", "image", "tag"]]
    assert len(tag_calls) == len(dev_harness.COMPOSE_IMAGE_COMPONENTS)


def test_rehydrate_loads_archived_images_and_verifies_manifest(monkeypatch, tmp_path):
    candidate = manifest(tmp_path, "a" * 40, feature="230")
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    archive = tmp_path / "artifacts" / candidate["manifest_id"] / "runtime-images.tar"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"archive")
    calls = []
    monkeypatch.setattr(adapter, "_assert_supported", lambda: None)
    monkeypatch.setattr(adapter, "_assert_source_matches_checkout", lambda _: None)
    monkeypatch.setattr(adapter, "_assert_manifest_images", lambda *_: calls.append("verified"))
    monkeypatch.setattr(
        dev_harness,
        "_run_command",
        lambda command, *, cwd, env=None: calls.append(command) or "",
    )

    assert adapter.rehydrate(candidate)["images"] == "rehydrated"
    assert calls[0] == ["docker", "image", "load", "--input", str(archive)]
    assert calls[1] == "verified"


def test_live_promote_rehydrates_missing_installed_app_even_when_process_is_alive(
    monkeypatch, tmp_path
):
    sha = "a" * 40
    state = tmp_path / "state"
    candidate = manifest(state, sha, feature="272")
    candidate["migration_head"] = "test-head"
    candidate_path = tmp_path / "candidate.json"
    dev_harness._write_json(candidate_path, candidate)
    dev_harness._write_json(state / "manifests" / f"{candidate['manifest_id']}.json", candidate)
    dev_harness._write_json(
        state / "active-manifest.json",
        {"schema_version": dev_harness.POINTER_VERSION, "manifest_id": candidate["manifest_id"], "runtime_mode": "live"},
    )
    install_path = tmp_path / "Applications" / "GRAF Dev.app"
    monkeypatch.setenv("GRAF_DEV_INSTALL_PATH", str(install_path))
    monkeypatch.setattr(dev_harness, "state_dir", lambda live=False: state)
    monkeypatch.setattr(dev_harness, "_assert_dev_environment", lambda: None)
    monkeypatch.setattr(dev_harness.GrafLocalAdapter, "_runtime_is_live", lambda self, _: True)
    calls = []

    def fake_promote(self, promoted, *, previous_checkout=None):
        calls.append(promoted["manifest_id"])
        return {"mode": "live", "checks": {"app_identity": "pass"}}

    monkeypatch.setattr(dev_harness.GrafLocalAdapter, "promote", fake_promote)

    result = dev_harness.operation_promote(
        dev_harness.argparse.Namespace(
            manifest=str(candidate_path), live=True, dry_run=False, previous_checkout=None
        )
    )

    assert result["adapter"]["mode"] == "live"
    assert calls == [candidate["manifest_id"]]


def test_rebuild_identity_ignores_resolved_artifact_digests(tmp_path):
    existing = manifest(tmp_path, "a" * 40, feature="272")
    candidate = manifest(tmp_path, "a" * 40, feature="272")
    for component in existing["components"].values():
        component["digest"] = "sha256:" + "1" * 64

    assert dev_harness._same_manifest_identity(existing, candidate)


def test_feature_229_env_pins_every_compose_service_to_manifest_image_id(tmp_path):
    candidate = manifest(tmp_path, "a" * 40, feature="229")
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)

    env = adapter._env(candidate)

    for _service, (component, variable, _fallback, _source_bound) in dev_harness.COMPOSE_IMAGE_COMPONENTS.items():
        assert env[variable] == candidate["components"][component]["digest"]


def test_pre_hardening_manifest_is_readable_but_cannot_start_without_init_image(tmp_path):
    previous = manifest(tmp_path, "a" * 40, feature="229")
    previous["components"].pop("storage_init")
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)

    dev_harness._validate_manifest(previous)
    with pytest.raises(dev_harness.HarnessError, match="rec-minio-init; rebuild the candidate"):
        adapter._env(previous)


def test_manifest_validates_storage_init_when_present(tmp_path):
    candidate = manifest(tmp_path, "a" * 40, feature="229")
    candidate["components"]["storage_init"]["digest"] = "mutable:latest"

    with pytest.raises(dev_harness.HarnessError, match="storage_init has invalid digest"):
        dev_harness._validate_manifest(candidate)


def test_runtime_definition_drift_blocks_before_mutation(monkeypatch, tmp_path):
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    monkeypatch.setattr(adapter, "_runtime_definition_digest", lambda: "sha256:" + "b" * 64)

    with pytest.raises(dev_harness.HarnessError, match="definition differs"):
        adapter._assert_runtime_definition_compatible(
            {"runtime_definition_digest": "sha256:" + "a" * 64}
        )


def test_runtime_definition_paths_cover_host_mutation_helpers_not_image_bound_server_source():
    assert {
        "scripts/dev-harness.py",
        "apps/macos/Scripts/install-dev-app.sh",
        "apps/macos/Scripts/dev-app-lifecycle.swift",
    } <= set(dev_harness.RUNTIME_DEFINITION_PATHS)
    assert "apps/server/src" not in dev_harness.RUNTIME_DEFINITION_PATHS


def test_manifest_image_preflight_rejects_server_source_sha_mismatch(monkeypatch, tmp_path):
    candidate = manifest(tmp_path, "a" * 40, feature="229")
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    env = adapter._env(candidate)

    def fake_run(command, *, cwd, env=None):
        if command[3:5] == ["--format", "{{.Id}}"]:
            return command[-1]
        return "b" * 40

    monkeypatch.setattr(dev_harness, "_run_command", fake_run)

    with pytest.raises(dev_harness.HarnessError, match="source SHA mismatch for api"):
        adapter._assert_manifest_images(candidate, env)


def test_promote_checks_required_images_before_stopping_active_runtime(monkeypatch, tmp_path):
    probe = ordinary_probe(monkeypatch, tmp_path)
    def missing(*_):
        raise dev_harness.HarnessError("required image missing")
    monkeypatch.setattr(dev_harness.GrafLocalAdapter, "_assert_manifest_images", missing)
    with pytest.raises(dev_harness.HarnessError, match="required image missing"):
        probe.adapter.promote(probe.target, **probe.options)
    assert probe.calls == []
    assert not (tmp_path / "rollback-required.json").exists()


def test_service_readiness_rejects_container_from_different_image(monkeypatch, tmp_path):
    candidate = manifest(tmp_path, "a" * 40, feature="229")
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    env = adapter._env(candidate)

    def fake_run(command, *, cwd, env=None):
        if command[:2] == ["docker", "compose"] and "-q" in command:
            return "container-id"
        if command[:2] == ["docker", "inspect"]:
            if ".Image" in command[-2]:
                return "sha256:" + "f" * 64
            return candidate["source_sha"]
        if command[:2] == ["docker", "compose"] and "--format" in command:
            return json.dumps({"State": "running", "Health": "healthy"})
        raise AssertionError(command)

    monkeypatch.setattr(dev_harness, "_run_command", fake_run)

    assert adapter._compose_service_ready("api", env) == "fail"


def test_signed_app_identity_is_measured_from_codesign_output(monkeypatch, tmp_path):
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    outputs = {
        "-dv": "Authority=GRAF Local Code Signing\nTeamIdentifier=LOCAL",
        "-dr": "designated => identifier \"pro.2brain.graf.dev\"",
        "-d": "Executable=GRAF\n<?xml version=\"1.0\"?><plist><dict/></plist>",
    }

    def fake_combined(command, *, cwd, env=None):
        return outputs[command[1]]

    def fake_run(command, *, cwd, env=None):
        return outputs["-d"].split("\n", 1)[1]

    monkeypatch.setattr(dev_harness, "_run_command_combined", fake_combined)
    monkeypatch.setattr(dev_harness, "_run_command", fake_run)
    signer, requirement, entitlements_digest = adapter._measure_signed_app_identity(tmp_path / "GRAF Dev.app")

    assert signer == "GRAF Local Code Signing"
    assert requirement == 'identifier "pro.2brain.graf.dev"'
    assert entitlements_digest.startswith("sha256:")


def test_future_feature_smoke_rejects_stale_local_presentation(monkeypatch, tmp_path):
    sha = "d" * 40
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    active = manifest(tmp_path, sha, feature="230")
    app = tmp_path / "GRAF Dev.app"
    info_plist = app / "Contents" / "Info.plist"
    dev_icon = app / "Contents" / "Resources" / "AppIcon.icns"
    production_icon = tmp_path / "apps" / "macos" / "RecApp" / "Resources" / "AppIcon.icns"
    info_plist.parent.mkdir(parents=True)
    info_plist.touch()
    dev_icon.parent.mkdir(parents=True)
    dev_icon.write_bytes(b"dev-icon")
    production_icon.parent.mkdir(parents=True)
    production_icon.write_bytes(b"production-icon")
    dev_harness._write_json(tmp_path / "migration-preflight.json", {"status": "matching"})
    monkeypatch.setenv("GRAF_DEV_INSTALL_PATH", str(app))
    monkeypatch.setattr(dev_harness.sys, "platform", "darwin")
    monkeypatch.setattr(adapter, "_assert_supported", lambda: None)
    monkeypatch.setattr(adapter, "_wait_http", lambda *args, **kwargs: 200)
    monkeypatch.setattr(adapter, "_compose_service_ready", lambda *_: "pass")
    monkeypatch.setattr(adapter, "_tcp_ready", lambda *_: "pass")
    monkeypatch.setattr(adapter, "_app_is_running", lambda _: True)
    presentation = {
        "GRAFSourceSHA": sha,
        "CFBundleIdentifier": dev_harness.APP_BUNDLE_ID,
        "CFBundleDisplayName": "GRAF Dev",
        "CFBundleName": "GRAF Dev",
        "CFBundleIconFile": "AppIcon",
        "LSEnvironment.GRAF_APP_CHANNEL": "dev",
        "LSEnvironment.GRAF_CABINET_BASE_URL": active["dev_boundary"]["backend_origin"],
    }
    monkeypatch.setattr(
        dev_harness,
        "_run_command",
        lambda command, *, cwd, env=None: presentation[command[2]],
    )

    assert adapter.smoke(active)["app_presentation"] == "pass"

    presentation["CFBundleDisplayName"] = "GRAF Local"
    assert adapter.smoke(active)["app_presentation"] == "fail"


def test_http_probe_preserves_auth_challenge_status(monkeypatch, tmp_path):
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)

    def raise_auth_challenge(*_args, **_kwargs):
        raise HTTPError("http://127.0.0.1:8081/api/v1/cabinet/meetings", 401, "Unauthorized", {}, None)

    monkeypatch.setattr(dev_harness, "urlopen", raise_auth_challenge)

    assert adapter._wait_http("http://127.0.0.1:8081", "/api/v1/cabinet/meetings") == 401


def test_startup_wait_does_not_accept_stale_http_listener(monkeypatch, tmp_path):
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    candidate = manifest(tmp_path, "a" * 40)
    attempts = {"api": 0}
    observed_services = []

    monkeypatch.setattr(
        adapter,
        "_wait_http",
        lambda *_args, **_kwargs: 200,
    )

    def service_ready(service, _env):
        observed_services.append(service)
        if service == "api":
            attempts["api"] += 1
        return "pass" if attempts["api"] >= 2 else "fail"

    monkeypatch.setattr(adapter, "_compose_service_ready", service_ready)
    monkeypatch.setattr(dev_harness.time, "sleep", lambda _seconds: None)

    adapter._wait_runtime_ready(candidate, {"GRAF_DEV_SOURCE_SHA": candidate["source_sha"]}, timeout=1)

    assert attempts["api"] == 2
    assert observed_services[:2] == ["api", "api"]


def test_failed_start_waits_for_runtime_cleanup_before_compensation(monkeypatch, tmp_path):
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    candidate = manifest(tmp_path, "a" * 40)
    events = []
    monkeypatch.setattr(adapter, "_runtime_definition_digest", lambda: "sha256:" + "d" * 64)

    class FakeProcess:
        pid = 77

        def terminate(self):
            events.append("terminate")

        def wait(self, timeout=None):
            events.append(("wait", timeout))

    monkeypatch.setattr(dev_harness.subprocess, "Popen", lambda *_args, **_kwargs: FakeProcess())
    monkeypatch.setattr(adapter, "_process_command", lambda _pid: "start-dev-runtime.sh")
    monkeypatch.setattr(adapter, "_process_start_token", lambda _pid: "start-token")
    monkeypatch.setattr(
        adapter,
        "_wait_runtime_ready",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(dev_harness.HarnessError("injected failure")),
    )

    with pytest.raises(dev_harness.HarnessError, match="injected failure"):
        adapter._start_backend(candidate, {})

    assert events == ["terminate", ("wait", dev_harness.RUNTIME_CLEANUP_TIMEOUT_SECONDS)]


def test_pid_ownership_requires_matching_process_start_token(monkeypatch, tmp_path):
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    record = {"pid": 77, "command": "/tmp/start-dev.sh", "start_token": "Mon Aug 31 01:02:03 2026"}

    def fake_ps(command, **_kwargs):
        assert command[:3] == ["ps", "-p", "77"]
        return record["command"] if command[-1] == "command=" else record["start_token"]

    monkeypatch.setattr(dev_harness.subprocess, "check_output", fake_ps)
    assert adapter._pid_owned(record) is True
    assert adapter._pid_owned(dict(record, start_token="Tue Aug 31 01:02:03 2026")) is False
    assert adapter._pid_owned({"pid": 77, "command": record["command"]}) is False


def test_pid_alive_treats_zombie_as_stopped(monkeypatch, tmp_path):
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    monkeypatch.setattr(dev_harness.os, "kill", lambda *_args: None)
    monkeypatch.setattr(
        dev_harness.subprocess,
        "check_output",
        lambda *_args, **_kwargs: "Z+" if "stat=" in _args[0] else "",
    )
    assert adapter._pid_alive(77) is False


def test_process_command_captures_post_exec_command(monkeypatch, tmp_path):
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)

    def fake_ps(command, **_kwargs):
        assert command == ["ps", "-p", "303", "-o", "command="]
        return "uv run uvicorn twobrain_rec_server.main:create_app --factory\n"

    monkeypatch.setattr(dev_harness.subprocess, "check_output", fake_ps)

    assert adapter._process_command(303) == "uv run uvicorn twobrain_rec_server.main:create_app --factory"


def test_app_snapshot_rejects_production_destination_before_copy(monkeypatch, tmp_path):
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    production = tmp_path / "GRAF.app"
    production.mkdir()
    (production / "Contents").mkdir()
    monkeypatch.setattr(dev_harness, "PRODUCTION_APP_PATH", production)
    monkeypatch.setenv("GRAF_DEV_INSTALL_PATH", str(production))

    with pytest.raises(dev_harness.HarnessError, match="Dev destination"):
        adapter._snapshot_app()


def test_app_snapshot_rejects_symlink_into_production(monkeypatch, tmp_path):
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    production = tmp_path / "GRAF.app"
    production.mkdir()
    monkeypatch.setattr(dev_harness, "PRODUCTION_APP_PATH", production)
    destination = tmp_path / "GRAF Dev.app"
    destination.symlink_to(production, target_is_directory=True)
    monkeypatch.setenv("GRAF_DEV_INSTALL_PATH", str(destination))

    with pytest.raises(dev_harness.HarnessError, match="production"):
        adapter._snapshot_app()


def test_app_lifecycle_uses_native_helper_and_waits_for_termination(monkeypatch, tmp_path):
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    destination = tmp_path / "GRAF Dev.app"
    states = iter(["running", "running", "stopped"])
    calls = []

    def fake_run(command, *, cwd, env=None):
        calls.append(command)
        if command[0] == "swift" and command[2] == "status":
            return next(states)
        if command[0] == "swift" and command[2] == "terminate":
            return "terminating"
        raise AssertionError(command)

    monkeypatch.setattr(dev_harness, "_run_command", fake_run)
    monkeypatch.setattr(dev_harness.time, "sleep", lambda _seconds: None)

    assert adapter._terminate_dev_app(destination) is True
    assert [call[2] for call in calls] == ["status", "terminate", "status", "status"]


def test_live_promote_relaunches_new_app_and_restores_previous_launch_state(monkeypatch, tmp_path):
    probe = ordinary_probe(monkeypatch, tmp_path)
    probe.adapter.promote(probe.target, **probe.options)
    assert [name for name, _sha, _root in probe.calls if name in {"install", "start", "launch"}] == ["install", "start", "launch"]
    assert probe.running["value"] is True
    assert (probe.app / "Contents/marker").read_text() == probe.target["source_sha"]
    assert not (tmp_path / "rollback-required.json").exists()
    assert not list((tmp_path / "transactions").glob("previous-*.app"))


@pytest.mark.parametrize("cross_definition", [False, True])
def test_live_promote_restores_app_and_restarts_previous_backend_on_smoke_failure(monkeypatch, tmp_path, cross_definition):
    probe = ordinary_probe(monkeypatch, tmp_path, cross_definition=cross_definition)
    monkeypatch.setattr(dev_harness.GrafLocalAdapter, "smoke",
                        lambda self, value: full_smoke() if value["source_sha"] == probe.active["source_sha"]
                        else {"backend_health": "fail"})
    with pytest.raises(dev_harness.HarnessError, match="smoke.*(failed|incomplete)"):
        probe.adapter.promote(probe.target, **probe.options)
    assert (probe.app / "Contents/marker").read_text() == probe.active["source_sha"]
    runtime = dev_harness._read_json(tmp_path / "runtime.json")
    assert runtime["source_sha"] == probe.active["source_sha"]
    assert runtime["runtime_definition_digest"] == probe.previous_digest
    assert ("start", probe.active["source_sha"], str(probe.previous_root)) in probe.calls
    assert probe.running["value"] is True
    assert not (tmp_path / "rollback-required.json").exists()
    assert dev_harness._load_active(tmp_path)["source_sha"] == probe.active["source_sha"]


def test_live_promote_marks_active_manifest_when_compensation_fails(monkeypatch, tmp_path):
    probe = ordinary_probe(monkeypatch, tmp_path)
    monkeypatch.setattr(dev_harness.GrafLocalAdapter, "smoke", lambda *_: {"backend_health": "fail"})
    def failed_restore(*_):
        raise dev_harness.HarnessError("injected restore failure")
    monkeypatch.setattr(dev_harness.GrafLocalAdapter, "_restore_runtime", failed_restore)
    with pytest.raises(dev_harness.HarnessError, match="compensation incomplete"):
        probe.adapter.promote(probe.target, **probe.options)
    status = dev_harness.operation_status(type("Args", (), {"live": False})())
    assert status["status"] == "rollback_required"
    operation = status["recovery"]["operation"]
    assert operation["target"]["source_sha"] == probe.target["source_sha"]
    assert operation["previous"]["source_sha"] == probe.active["source_sha"]
    assert (tmp_path / operation["backup"]).is_dir()
    assert dev_harness._load_active(tmp_path)["source_sha"] == probe.active["source_sha"]


def test_first_promotion_failure_is_visible_without_active_pointer(monkeypatch, tmp_path):
    candidate = manifest(tmp_path, "b" * 40, feature="229")
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    dev_harness._write_json(
        tmp_path / "manifests" / f"{candidate['manifest_id']}.json", candidate
    )
    adapter._mark_rollback_required(candidate)
    monkeypatch.setattr(dev_harness, "state_dir", lambda **_: tmp_path)

    status = dev_harness.operation_status(type("Args", (), {"live": False})())

    assert status["status"] == "rollback_required"
    assert status["manifest"]["manifest_id"] == candidate["manifest_id"]


def test_live_build_holds_repository_global_state_lock(monkeypatch, tmp_path):
    events = []

    @contextmanager
    def fake_lock(root):
        events.append(("enter", root))
        yield
        events.append(("exit", root))

    monkeypatch.setattr(dev_harness, "state_dir", lambda **_: tmp_path)
    monkeypatch.setattr(dev_harness, "state_lock", fake_lock)
    monkeypatch.setattr(
        dev_harness.GrafLocalAdapter,
        "build",
        lambda *_: events.append(("build", tmp_path)) or {"mode": "live"},
    )
    args = type(
        "Args",
        (),
        {
            "sha": "c" * 40,
            "feature_id": "229",
            "operator": "test",
            "migration_head": "head",
            "live": True,
            "dry_run": False,
        },
    )()

    dev_harness.operation_build(args)

    assert events == [("enter", tmp_path), ("build", tmp_path), ("exit", tmp_path)]


@pytest.mark.parametrize("cross_definition", [False, True])
def test_live_rollback_reinstalls_target_and_verifies_before_return(monkeypatch, tmp_path, cross_definition):
    probe = ordinary_probe(monkeypatch, tmp_path, kind="rollback", cross_definition=cross_definition)
    result = probe.adapter.rollback(probe.active, probe.target, **probe.options)
    assert result["mode"] == "live" and result["checks"]["backend_health"] == "pass"
    assert (probe.app / "Contents/marker").read_text() == probe.target["source_sha"]
    assert ("install", probe.target["source_sha"], str(probe.target_root)) in probe.calls
    assert ("start", probe.target["source_sha"], str(probe.target_root)) in probe.calls
    assert not (tmp_path / "rollback-required.json").exists()


def test_live_rollback_validates_target_checkout_before_starting(monkeypatch, tmp_path):
    probe = ordinary_probe(monkeypatch, tmp_path, kind="rollback")
    original = dev_harness.GrafLocalAdapter._assert_source_matches_checkout
    checked = []
    def reject_target(self, value):
        checked.append(value["source_sha"])
        if value["source_sha"] == probe.target["source_sha"]:
            raise dev_harness.HarnessError("target checkout source mismatch")
        original(self, value)
    monkeypatch.setattr(dev_harness.GrafLocalAdapter, "_assert_source_matches_checkout", reject_target)
    with pytest.raises(dev_harness.HarnessError, match="target checkout source mismatch"):
        probe.adapter.rollback(probe.active, probe.target, **probe.options)
    assert probe.target["source_sha"] in checked
    assert probe.calls == []
    assert not (tmp_path / "rollback-required.json").exists()


def full_smoke():
    return dict.fromkeys(("backend_health", "frontend_reachability", "auth_session_bootstrap",
        "representative_api", "processing_worker_readiness", "media_worker_readiness",
        "database_readiness", "storage_readiness", "temporal_readiness", "migration_readiness",
        "exact_source_sha", "app_identity", "app_presentation"), "pass")


@pytest.mark.parametrize("checks", [{}, {"backend_health": "pass"}, {**full_smoke(), "exact_source_sha": "fail"}])
def test_transition_rejects_incomplete_or_failed_smoke(checks):
    with pytest.raises(dev_harness.HarnessError, match="smoke"):
        dev_harness.GrafLocalAdapter._assert_transition_smoke(checks)


def test_transition_checks_exact_tracked_source_before_loading(monkeypatch, tmp_path):
    import argparse
    import subprocess
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path).decode().strip()
    git("init", "-q")
    git("config", "user.name", "Test")
    git("config", "user.email", "test@example.test")
    git("config", "remote.origin.url", "https://github.com/example/graf.git")
    monkeypatch.setenv("HOME", str(tmp_path.parent / (tmp_path.name + "-home")))
    monkeypatch.setattr(dev_harness, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(dev_harness, "_assert_empty_dev_machine", lambda: None)
    state = dev_harness._machine_state_base() / "existing" / "harness"
    dev_harness.operation_adopt_state(argparse.Namespace(
        state_root=state, expected_repository="github.com/example/graf",
        expected_active_sha=None, expect_empty=True, confirm_repository_ownership=True,
    ))
    source = (SOURCE_ROOT / "scripts/dev-harness.py").read_text()
    # No native execution needed to prove the source trust boundary.
    source = source.replace('if sys.platform != "darwin":', 'if False:')
    for relative in (*dev_harness.RUNTIME_DEFINITION_PATHS, "apps/macos/Scripts/build-dev-app.sh"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source if relative == "scripts/dev-harness.py" else "# fixture\n")
    git("add", ".")
    git("commit", "-qm", "fixture")
    sha = git("rev-parse", "HEAD")
    adapter = dev_harness.GrafLocalAdapter(tmp_path, state)
    item = manifest(tmp_path, sha)
    record = {"runtime_definition_digest": adapter._runtime_definition_digest()}
    loaded = adapter._checkout_adapter(tmp_path, item, record)
    assert loaded.root == tmp_path
    assert loaded._runtime_definition_digest() == record["runtime_definition_digest"]
    with pytest.raises(dev_harness.HarnessError, match="source_sha"):
        adapter._checkout_adapter(tmp_path, {**item, "source_sha": "f" * 40}, record)
    with pytest.raises(dev_harness.HarnessError, match="definition differs"):
        adapter._checkout_adapter(tmp_path, item, {"runtime_definition_digest": "sha256:" + "f" * 64})
    path = tmp_path / "scripts/dev-harness.py"
    path.write_text(source + "\nraise RuntimeError('must not execute')\n")
    with pytest.raises(dev_harness.HarnessError, match="clean checkout"):
        adapter._checkout_adapter(tmp_path, item)
    git("update-index", "--assume-unchanged", "scripts/dev-harness.py")
    with pytest.raises(dev_harness.HarnessError, match="committed bytes"):
        adapter._checkout_adapter(tmp_path, item)


@pytest.mark.parametrize("field", ["database", "storage", "temporal", "migration_head"])
def test_transition_cannot_change_persistent_formats(tmp_path, field):
    old = manifest(tmp_path)
    target = json.loads(json.dumps(old))
    if field == "migration_head":
        target[field] = "different"
    else:
        target["components"][field]["digest"] = "sha256:" + "f" * 64
    with pytest.raises(dev_harness.HarnessError, match="matching database schema"):
        dev_harness.GrafLocalAdapter._assert_transition_compatible(old, target)


def test_cold_start_can_finish_after_ninety_seconds_without_skipping_service_checks(monkeypatch, tmp_path):
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    candidate = manifest(tmp_path, "a" * 40)
    clock = [0.0]
    checked = []
    monkeypatch.setattr(dev_harness.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(dev_harness.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))

    def live_probe(*_args, **_kwargs):
        clock[0] += 30
        return 200

    def ready(service, _env):
        checked.append(service)
        return "pass" if clock[0] >= 120 else "fail"

    monkeypatch.setattr(adapter, "_wait_http", live_probe)
    monkeypatch.setattr(adapter, "_compose_service_ready", ready)
    adapter._wait_runtime_ready(candidate, {"GRAF_DEV_SOURCE_SHA": candidate["source_sha"]})
    assert 90 < clock[0] < 180
    assert checked[-len(dev_harness.RUNTIME_READY_SERVICES):] == list(dev_harness.RUNTIME_READY_SERVICES)


def test_cold_start_still_fails_when_one_service_never_reaches_exact_readiness(monkeypatch, tmp_path):
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    candidate = manifest(tmp_path, "a" * 40)
    clock = [0.0]
    monkeypatch.setattr(dev_harness.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(dev_harness.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))

    def live_probe(*_args, **_kwargs):
        clock[0] += 30
        return 200

    monkeypatch.setattr(adapter, "_wait_http", live_probe)
    monkeypatch.setattr(adapter, "_compose_service_ready", lambda service, _env: "fail" if service == "rec-media-worker" else "pass")
    with pytest.raises(dev_harness.HarnessError, match="exact-SHA service readiness"):
        adapter._wait_runtime_ready(candidate, {"GRAF_DEV_SOURCE_SHA": candidate["source_sha"]})
    assert 180 <= clock[0] < 185


def ordinary_probe(monkeypatch, state, *, kind="promote", cross_definition=False):
    """Real receipt/snapshot/restore flow; only external app/runtime effects are substituted."""
    from types import SimpleNamespace
    import shutil

    cls = dev_harness.GrafLocalAdapter
    controller_root = state / "controller-source"
    previous_root = state / "previous-source" if kind == "promote" else controller_root
    target_root = controller_root if kind == "promote" else state / "target-source"
    for root in {controller_root, previous_root, target_root}:
        root.mkdir()
    monkeypatch.setattr(dev_harness, "_state_ownership", lambda *args, **kwargs: False)
    monkeypatch.setattr(dev_harness, "_repo_root", lambda: controller_root)
    monkeypatch.setattr(dev_harness, "state_dir", lambda **kwargs: state)
    active = manifest(state, "a" * 40)
    target = manifest(state, "b" * 40)
    active.update(status="active", health={"result": "pass", "checks": {}, "checked_at": dev_harness.now()})
    if kind == "promote":
        target["parent_manifest_id"] = active["manifest_id"]
    else:
        active["parent_manifest_id"] = target["manifest_id"]
    for key in ("database", "storage", "temporal"):
        target["components"][key]["digest"] = active["components"][key]["digest"]
    for value in (active, target):
        bundle = state / "artifacts" / value["manifest_id"] / "GRAF Dev.app"
        (bundle / "Contents").mkdir(parents=True)
        (bundle / "Contents/marker").write_text(value["source_sha"])
        value["components"]["macos_app"]["digest"] = dev_harness._tree_digest(bundle)
    dev_harness._write_json(dev_harness._manifest_path(state, target["manifest_id"]), target)
    dev_harness._publish_active(state, active, "live")
    app = state / "GRAF Dev.app"
    shutil.copytree(state / "artifacts" / active["manifest_id"] / "GRAF Dev.app", app)
    monkeypatch.setattr(dev_harness, "_dev_app_destination", lambda: app)
    monkeypatch.setattr(cls, "_assert_dev_app_destination", staticmethod(lambda path: None))
    calls = []
    running = {"value": True}
    digests = {previous_root: "sha256:" + "d" * 64,
               target_root: "sha256:" + ("e" if cross_definition else "d") * 64}
    sources = {previous_root: active["source_sha"], target_root: target["source_sha"]}
    def source(self, value):
        assert sources[self.root] == value["source_sha"]
    class Frozen:
        def __init__(self, root):
            self.root = root
        def __getattr__(self, name):
            pytest.fail("frozen adapter method executed: " + name)
    def checkout(self, root, value):
        cls(root, state)._assert_source_matches_checkout(value)
        return Frozen(root)
    monkeypatch.setattr(cls, "_assert_supported", lambda self: None)
    monkeypatch.setattr(cls, "_assert_source_matches_checkout", source)
    monkeypatch.setattr(cls, "_checkout_adapter", checkout)
    monkeypatch.setattr(cls, "_runtime_definition_digest", lambda self: digests[self.root])
    monkeypatch.setattr(cls, "_compose_config", lambda *_: None)
    monkeypatch.setattr(cls, "_assert_manifest_images", lambda *_: None)
    monkeypatch.setattr(cls, "_runtime_is_live", lambda self, value: value is not None)
    monkeypatch.setattr(cls, "_app_is_running", lambda self, path: running["value"])
    def stop_app(self, path):
        running["value"] = False
        calls.append(("stop-app", None, str(self.root)))
    def launch(self, path):
        running["value"] = True
        calls.append(("launch", None, str(self.root)))
    def install(self, value, env):
        calls.append(("install", value["source_sha"], str(self.root)))
        shutil.rmtree(app)
        shutil.copytree(self._checked_app_bundle(value), app)
    def runtime(value, root):
        return {"pid": 99999999, "source_sha": value["source_sha"], "command": "synthetic runtime",
                "start_token": "synthetic start", "runtime_definition_digest": digests[root]}
    def start(self, value, env):
        calls.append(("start", value["source_sha"], str(self.root)))
        dev_harness._write_json(state / "runtime.json", runtime(value, self.root))
    def swap(self, staged, destination):
        saved = state / "swap-marker"
        destination.rename(saved)
        staged.rename(destination)
        saved.rename(staged)
    def validate(self, value, path):
        assert (path / "Contents/marker").read_text() == value["source_sha"]
        assert dev_harness._tree_digest(path) == value["components"]["macos_app"]["digest"]
    monkeypatch.setattr(cls, "_terminate_dev_app", stop_app)
    monkeypatch.setattr(cls, "_launch_dev_app", launch)
    monkeypatch.setattr(cls, "_stop_previous", lambda self: calls.append(("stop", None, str(self.root))))
    monkeypatch.setattr(cls, "_install_app", install)
    monkeypatch.setattr(cls, "_start_backend", start)
    monkeypatch.setattr(cls, "_atomic_swap_dev_app", swap)
    monkeypatch.setattr(cls, "_validate_launch_bundle", validate)
    monkeypatch.setattr(cls, "_refresh_dev_app_registration", staticmethod(lambda path: None))
    monkeypatch.setattr(cls, "_ensure_rollback_archive", lambda *_: None)
    monkeypatch.setattr(cls, "_apply_retention", lambda *args, **kwargs: None)
    monkeypatch.setattr(cls, "smoke", lambda self, value: full_smoke())
    dev_harness._write_json(state / "runtime.json", runtime(active, previous_root))
    options = {"previous_checkout": str(previous_root)}
    if kind == "rollback":
        options["target_checkout"] = str(target_root)
    return SimpleNamespace(adapter=cls(controller_root, state), active=active, target=target,
                           options=options, calls=calls, app=app, running=running,
                           previous_root=previous_root, target_root=target_root,
                           previous_digest=digests[previous_root])
