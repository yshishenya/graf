from __future__ import annotations

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


def manifest(tmp_path: Path, sha: str = "a" * 40):
    return dev_harness.build_manifest(sha, "216", root=tmp_path)


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


def test_live_build_runs_compose_backend_and_signed_app_adapter(monkeypatch, tmp_path):
    sha = "b" * 40
    fake_root = tmp_path / "root"
    adapter = dev_harness.GrafLocalAdapter(fake_root, tmp_path / "state")
    for path in (adapter.compose_file, adapter.start_script, adapter.build_app_script, adapter.install_app_script):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    monkeypatch.setattr(dev_harness.sys, "platform", "darwin")
    calls = []

    def fake_run(command, *, cwd, env=None):
        calls.append(command)
        if command[:2] == ["git", "rev-parse"]:
            return sha
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
        return outputs["-d"]

    monkeypatch.setattr(dev_harness, "_run_command_combined", fake_combined)
    monkeypatch.setattr(dev_harness, "_run_command", fake_run)
    signer, requirement, entitlements_digest = adapter._measure_signed_app_identity(tmp_path / "GRAF Dev.app")

    assert signer == "GRAF Local Code Signing"
    assert requirement == 'identifier "pro.2brain.graf.dev"'
    assert entitlements_digest.startswith("sha256:")


def test_live_smoke_checks_server_rendered_frontend_auth_and_one_app(monkeypatch, tmp_path):
    sha = "c" * 40
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    active = manifest(tmp_path, sha)
    app = tmp_path / "GRAF Dev.app"
    (app / "Contents").mkdir(parents=True)
    (app / "Contents" / "Info.plist").touch()
    monkeypatch.setenv("GRAF_DEV_INSTALL_PATH", str(app))
    monkeypatch.setattr(dev_harness.sys, "platform", "darwin")
    monkeypatch.setattr(adapter, "_assert_supported", lambda: None)
    monkeypatch.setattr(adapter, "_wait_http", lambda *args, **kwargs: 200)

    def fake_plutil(command, *, cwd, env=None):
        if command[:2] == ["docker", "compose"] and "ps" in command:
            service = command[-1]
            return json.dumps({"Service": service, "State": "running", "Health": "healthy"})
        if command[2] == "GRAFSourceSHA":
            return sha
        if command[2] == "CFBundleIdentifier":
            return dev_harness.APP_BUNDLE_ID
        return active["dev_boundary"]["backend_origin"]

    monkeypatch.setattr(dev_harness, "_run_command", fake_plutil)
    checks = adapter.smoke(active)

    assert checks == {
        "backend_health": "pass",
        "temporal_health": "pass",
        "worker_dependencies": "pass",
        "frontend_reachability": "pass",
        "auth_session_bootstrap": "pass",
        "representative_api": "pass",
        "app_origin": "pass",
    }


def test_live_smoke_rejects_empty_or_unrelated_worker_status(monkeypatch, tmp_path):
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    active = manifest(tmp_path, "c" * 40)
    monkeypatch.setattr(dev_harness.sys, "platform", "darwin")
    monkeypatch.setattr(adapter, "_assert_supported", lambda: None)
    monkeypatch.setattr(adapter, "_wait_http", lambda *args, **kwargs: 200)
    monkeypatch.setattr(
        dev_harness,
        "_run_command",
        lambda command, *, cwd, env=None: "{}" if command[:2] == ["docker", "compose"] else (
            active["source_sha"] if command[2] == "GRAFSourceSHA" else dev_harness.APP_BUNDLE_ID
        ),
    )
    app = tmp_path / "GRAF Dev.app" / "Contents"
    app.mkdir(parents=True)
    monkeypatch.setenv("GRAF_DEV_INSTALL_PATH", str(app.parent))
    checks = adapter.smoke(active)
    assert checks["worker_dependencies"] == "fail"


def test_http_probe_preserves_auth_challenge_status(monkeypatch, tmp_path):
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)

    def raise_auth_challenge(*_args, **_kwargs):
        raise HTTPError("http://127.0.0.1:8081/api/v1/cabinet/meetings", 401, "Unauthorized", {}, None)

    monkeypatch.setattr(dev_harness, "urlopen", raise_auth_challenge)

    assert adapter._wait_http("http://127.0.0.1:8081", "/api/v1/cabinet/meetings") == 401


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


def test_live_promote_restores_app_and_restarts_previous_backend_on_smoke_failure(monkeypatch, tmp_path):
    old_sha = "a" * 40
    candidate_sha = "b" * 40
    old = manifest(tmp_path, old_sha)
    candidate = manifest(tmp_path, candidate_sha)
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    app = tmp_path / "GRAF Dev.app"
    (app / "Contents").mkdir(parents=True)
    marker = app / "Contents" / "marker"
    marker.write_text("old", encoding="utf-8")
    monkeypatch.setenv("GRAF_DEV_INSTALL_PATH", str(app))

    (tmp_path / "manifests").mkdir()
    dev_harness._write_json(tmp_path / "manifests" / f"{old['manifest_id']}.json", old)
    dev_harness._write_json(
        tmp_path / "active-manifest.json",
        {
            "schema_version": dev_harness.POINTER_VERSION,
            "manifest_id": old["manifest_id"],
            "runtime_mode": "live",
            "updated_at": dev_harness.now(),
        },
    )
    previous_runtime = {
        "pid": 101,
        "source_sha": old_sha,
        "command": str(adapter.start_script),
    }
    dev_harness._write_json(tmp_path / "runtime.json", previous_runtime)

    calls = []
    monkeypatch.setattr(adapter, "_assert_supported", lambda: None)
    monkeypatch.setattr(adapter, "_assert_source_matches_checkout", lambda _: None)
    monkeypatch.setattr(adapter, "_compose_config", lambda _: None)
    monkeypatch.setattr(adapter, "_runtime_is_live", lambda _: True)
    monkeypatch.setattr(adapter, "_pid_alive", lambda _: True)
    monkeypatch.setattr(adapter, "_pid_owned", lambda _: True)
    monkeypatch.setattr(adapter, "_stop_previous", lambda: calls.append("stop"))

    def fake_install(manifest_value, _env):
        calls.append(("install", manifest_value["source_sha"]))
        marker.write_text("new", encoding="utf-8")

    def fake_start(manifest_value, _env):
        calls.append(("start", manifest_value["source_sha"]))
        dev_harness._write_json(
            tmp_path / "runtime.json",
            {
                "pid": 303 if manifest_value["source_sha"] == candidate_sha else 101,
                "source_sha": manifest_value["source_sha"],
                "command": str(adapter.start_script),
            },
        )

    monkeypatch.setattr(adapter, "_install_app", fake_install)
    monkeypatch.setattr(adapter, "_start_backend", fake_start)
    monkeypatch.setattr(adapter, "smoke", lambda _: {"backend_health": "fail", "mode": "live"})

    with pytest.raises(dev_harness.HarnessError, match="live promotion smoke failed"):
        adapter.promote(candidate)

    assert marker.read_text(encoding="utf-8") == "old"
    assert json.loads((tmp_path / "runtime.json").read_text(encoding="utf-8")) == previous_runtime
    assert calls == ["stop", ("install", candidate_sha), ("start", candidate_sha), "stop", ("start", old_sha)]


def test_live_rollback_reinstalls_target_and_verifies_before_return(monkeypatch, tmp_path):
    active_sha = "c" * 40
    target_sha = "d" * 40
    active = manifest(tmp_path, active_sha)
    target = manifest(tmp_path, target_sha)
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    app = tmp_path / "GRAF Dev.app"
    (app / "Contents").mkdir(parents=True)
    marker = app / "Contents" / "marker"
    marker.write_text("active", encoding="utf-8")
    monkeypatch.setenv("GRAF_DEV_INSTALL_PATH", str(app))

    previous_runtime = {
        "pid": 202,
        "source_sha": active_sha,
        "command": str(adapter.start_script),
    }
    dev_harness._write_json(tmp_path / "runtime.json", previous_runtime)
    calls = []
    monkeypatch.setattr(adapter, "_assert_supported", lambda: None)
    monkeypatch.setattr(adapter, "_assert_source_matches_checkout", lambda _: None)
    monkeypatch.setattr(adapter, "_compose_config", lambda _: None)
    monkeypatch.setattr(adapter, "_runtime_is_live", lambda _: True)
    monkeypatch.setattr(adapter, "_stop_previous", lambda: calls.append("stop"))

    def fake_install(manifest_value, _env):
        calls.append(("install", manifest_value["source_sha"]))
        marker.write_text("target", encoding="utf-8")

    def fake_start(manifest_value, _env):
        calls.append(("start", manifest_value["source_sha"]))

    monkeypatch.setattr(adapter, "_install_app", fake_install)
    monkeypatch.setattr(adapter, "_start_backend", fake_start)
    monkeypatch.setattr(
        adapter,
        "smoke",
        lambda _: {"backend_health": "pass", "frontend_reachability": "pass", "mode": "live"},
    )

    result = adapter.rollback(active, target)

    assert result["mode"] == "live"
    assert result["checks"]["backend_health"] == "pass"
    assert marker.read_text(encoding="utf-8") == "target"
    assert calls == ["stop", ("install", target_sha), ("start", target_sha)]


def test_live_rollback_validates_target_checkout_before_starting(monkeypatch, tmp_path):
    active = manifest(tmp_path, "c" * 40)
    target = manifest(tmp_path, "d" * 40)
    adapter = dev_harness.GrafLocalAdapter(tmp_path, tmp_path)
    calls = []

    monkeypatch.setattr(adapter, "_assert_supported", lambda: None)
    monkeypatch.setattr(
        adapter,
        "_assert_source_matches_checkout",
        lambda value: calls.append(value["source_sha"]),
    )
    monkeypatch.setattr(adapter, "_env", lambda _: {})
    monkeypatch.setattr(adapter, "_compose_config", lambda _: None)
    monkeypatch.setattr(adapter, "_runtime_record", lambda: tmp_path / "runtime.json")
    monkeypatch.setattr(adapter, "_runtime_is_live", lambda _: True)
    dev_harness._write_json(
        tmp_path / "runtime.json",
        {"pid": 202, "source_sha": active["source_sha"], "command": "start-local"},
    )
    monkeypatch.setattr(adapter, "_snapshot_app", lambda: None)
    monkeypatch.setattr(adapter, "_stop_previous", lambda: None)
    monkeypatch.setattr(adapter, "_install_app", lambda *_: None)
    monkeypatch.setattr(adapter, "_start_backend", lambda *_: None)
    monkeypatch.setattr(
        adapter,
        "smoke",
        lambda _: {"backend_health": "pass", "mode": "live"},
    )

    adapter.rollback(active, target)

    assert calls == [target["source_sha"]]
