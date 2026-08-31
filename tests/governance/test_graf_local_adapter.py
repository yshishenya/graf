from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("dev_harness_adapter", ROOT / "scripts" / "dev-harness.py")
assert SPEC and SPEC.loader
dev_harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dev_harness)


def manifest(tmp_path: Path, sha: str = "a" * 40):
    return dev_harness.build_manifest(sha, "216", root=tmp_path)


def test_live_adapter_build_is_explicit_and_uses_only_dev_environment(monkeypatch, tmp_path):
    sha = "a" * 40
    adapter = dev_harness.GrafLocalAdapter(ROOT, tmp_path)
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", "postgresql://production.example/secret")
    monkeypatch.setenv("TWOBRAIN_API_KEY", "should-not-cross-boundary")

    env = adapter._env(manifest(tmp_path, sha))

    assert env["TWOBRAIN_ENV"] == "development"
    assert env["TWOBRAIN_DATABASE_URL"].startswith("postgresql+asyncpg://twobrain_rec")
    assert "TWOBRAIN_API_KEY" not in env
    assert env["GRAF_DEV_ORIGIN"] == "http://127.0.0.1:8081"


def test_live_build_runs_compose_backend_and_signed_app_adapter(monkeypatch, tmp_path):
    sha = "b" * 40
    adapter = dev_harness.GrafLocalAdapter(ROOT, tmp_path)
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


def test_live_smoke_checks_server_rendered_frontend_auth_and_one_app(monkeypatch, tmp_path):
    sha = "c" * 40
    adapter = dev_harness.GrafLocalAdapter(ROOT, tmp_path)
    active = manifest(tmp_path, sha)
    app = tmp_path / "GRAF Dev.app"
    (app / "Contents").mkdir(parents=True)
    (app / "Contents" / "Info.plist").touch()
    monkeypatch.setenv("GRAF_DEV_INSTALL_PATH", str(app))
    monkeypatch.setattr(dev_harness.sys, "platform", "darwin")
    monkeypatch.setattr(adapter, "_assert_supported", lambda: None)
    monkeypatch.setattr(adapter, "_wait_http", lambda *args, **kwargs: 200)

    def fake_plutil(command, *, cwd, env=None):
        if command[2] == "GRAFSourceSHA":
            return sha
        if command[2] == "CFBundleIdentifier":
            return dev_harness.APP_BUNDLE_ID
        return active["dev_boundary"]["backend_origin"]

    monkeypatch.setattr(dev_harness, "_run_command", fake_plutil)
    checks = adapter.smoke(active)

    assert checks == {
        "backend_health": "pass",
        "worker_dependencies": "pass",
        "frontend_reachability": "pass",
        "auth_session_bootstrap": "pass",
        "representative_api": "pass",
        "app_origin": "pass",
    }
