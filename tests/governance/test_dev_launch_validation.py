"""Installed startup orchestration; all lifecycle effects below are synthetic."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("launch_harness", ROOT / "scripts/dev-harness.py")
assert SPEC and SPEC.loader
h = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(h)


def test_launch_validation_requires_explicit_live():
    with pytest.raises(h.HarnessError, match="explicit --live"):
        h.operation_validate_app_launch(SimpleNamespace(live=False, restart_idle_app=False))


def test_parser_exposes_only_opt_in_installed_launch():
    args = h.parser().parse_args(["validate-app-launch", "--live", "--restart-idle-app"])
    assert args.live and args.restart_idle_app


@pytest.fixture
def environment(tmp_path, monkeypatch):
    import plistlib

    state = tmp_path / "state"
    app = tmp_path / "GRAF Dev.app"
    (app / "Contents").mkdir(parents=True)
    info = {
        "CFBundleIdentifier": h.APP_BUNDLE_ID, "GRAFSourceSHA": "a" * 40,
        "LSEnvironment": {"GRAF_APP_CHANNEL": h.APP_CHANNEL},
    }
    (app / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
    monkeypatch.setattr(h, "DEV_APP_PATH", app)
    monkeypatch.delenv("GRAF_DEV_INSTALL_PATH", raising=False)
    monkeypatch.delenv("GRAF_DEV_STATE_DIR", raising=False)
    monkeypatch.setattr(h, "global_state_dir", lambda: state)
    monkeypatch.setattr(h, "_repo_root", lambda: ROOT)
    active = h.build_manifest("a" * 40, "232", migration_head="test-head", root=state)
    active["status"] = "active"
    active["components"]["macos_app"]["digest"] = h._tree_digest(app)
    h._publish_active(state, active, "live")
    model = SimpleNamespace(running=False, token="110:1234.0", launches=[], quits=0,
                            commands=[], logs=[], dirty=False, fail_validation=False,
                            replace=False, fail_quit=0, fail_restore=False)
    monkeypatch.setattr(h.GrafLocalAdapter, "_assert_supported", lambda self: None)
    expected_signing = tuple(active["app_identity"][key] for key in (
        "signing_identity", "designated_requirement", "entitlements_digest"
    ))
    monkeypatch.setattr(h.GrafLocalAdapter, "_measure_signed_app_identity", lambda self, path: expected_signing)
    monkeypatch.setattr(h.GrafLocalAdapter, "_app_is_running", lambda self, path: model.running)

    def launch(self, path, *, log_directory=None):
        model.launches.append(log_directory)
        if log_directory is None and model.fail_restore:
            raise h.HarnessError("synthetic restoration refusal")
        model.running = True
        model.token = f"{110 + len(model.launches)}:1234.0"
        if log_directory is not None:
            assert log_directory.is_dir() and not list(log_directory.iterdir())
            model.logs.append(log_directory)

    def quit_app(self, path, *, expected_identity=None):
        assert expected_identity == model.token
        model.quits += 1
        if model.fail_quit == model.quits:
            raise h.HarnessError("synthetic graceful refusal")
        model.running = False
        return True

    def command(argv, *, cwd, env=None):
        model.commands.append(argv)
        if argv[:3] == ["git", "rev-parse", "HEAD"]:
            return "b" * 40
        if argv[:3] == ["git", "status", "--porcelain"]:
            return " M synthetic.py" if model.dirty else ""
        if argv[:2] == ["git", "hash-object"] or argv[:2] == ["git", "rev-parse"]:
            return "d" * 40
        if argv[0] == "codesign":
            return ""
        if argv[0] == "swift":
            assert argv[2:] == ["identity", str(app)]
            return model.token
        if argv[0] == "sh":
            assert argv[1] == str(ROOT / "apps/macos/Scripts/validate-packaged-app-launch.sh")
            assert argv[2:] == ["--observe-installed-dev", model.token, str(model.logs[-1])]
            if model.replace:
                model.token = "999:5678.0"
            if model.fail_validation:
                raise h.HarnessError("synthetic missing readiness")
            return "packaged_app_launch=pass minimum_seconds=5 architecture=native lifecycle=dev-harness"
        raise AssertionError(argv)

    monkeypatch.setattr(h.GrafLocalAdapter, "_launch_dev_app", launch)
    monkeypatch.setattr(h.GrafLocalAdapter, "_terminate_dev_app", quit_app)
    monkeypatch.setattr(h, "_run_command", command)
    model.state, model.app, model.active = state, app, active
    return model


def validate(restart=False):
    return h.operation_validate_app_launch(SimpleNamespace(live=True, restart_idle_app=restart))


def test_stopped_app_is_checked_and_stays_stopped(environment):
    result = validate()
    assert result["tooling_sha"] == "b" * 40 and result["source_sha"] == "a" * 40
    assert result["markers"] == ["app_launch_finished", "app_main_window_presented"]
    assert result["status"] == "pass" and not result["restored_running"]
    assert not environment.running and environment.quits == 1
    assert len(environment.launches) == 1 and not environment.logs[0].exists()
    assert h._load_active(environment.state) == environment.active


def test_running_app_refused_without_explicit_idle_confirmation(environment):
    environment.running = True
    with pytest.raises(h.HarnessError, match="confirm idle"):
        validate()
    assert environment.running and not environment.launches and environment.quits == 0


def test_running_app_restored_normally_without_temporary_environment(environment):
    environment.running = True
    result = validate(restart=True)
    assert result["restored_running"] and environment.running
    assert environment.launches[-1] is None and environment.quits == 2
    assert not environment.logs[0].exists()


def test_readiness_failure_still_restores_and_propagates(environment):
    environment.running = True
    environment.fail_validation = True
    with pytest.raises(h.HarnessError, match="synthetic missing readiness"):
        validate(restart=True)
    assert environment.running and environment.launches[-1] is None
    assert not environment.logs[0].exists()
    assert not (environment.state / "app-launch-validation-recovery.json").exists()


def test_initial_graceful_refusal_does_not_force_quit_or_launch(environment):
    environment.running = True
    environment.fail_quit = 1
    with pytest.raises(h.HarnessError, match="graceful refusal"):
        validate(restart=True)
    assert environment.running and environment.quits == 1
    # Reusing the normal launch helper is idempotent if the original app stayed live.
    assert all(path is None for path in environment.launches)


@pytest.mark.parametrize("replacement", [False, True])
def test_failed_cleanup_never_forces_or_removes_live_log(environment, replacement):
    import json
    environment.replace = replacement
    environment.fail_quit = 1 if not replacement else 0
    environment.fail_validation = True
    with pytest.raises(h.HarnessError, match="restoration failed.*validation_failed=True"):
        validate()
    assert environment.running and environment.logs[0].is_dir()
    recovery = json.loads((environment.state / "app-launch-validation-recovery.json").read_text())
    assert recovery["validation_failed"] and recovery["temporary_log_directory"] == str(environment.logs[0])
    assert environment.quits == (0 if replacement else 1)
    with pytest.raises(h.HarnessError, match="resolved recovery"):
        validate()
    # Fixture owns these synthetic directories; no installed process uses them.
    import shutil
    shutil.rmtree(environment.logs[0])


def test_normal_restore_failure_is_failure_even_after_validator_pass(environment):
    environment.running = True
    environment.fail_restore = True
    with pytest.raises(h.HarnessError, match="restoration failed.*validation_failed=False"):
        validate(restart=True)
    assert not environment.running and not environment.logs[0].exists()
    assert (environment.state / "app-launch-validation-recovery.json").exists()


@pytest.mark.parametrize("guard", ["dirty", "metadata", "rollback", "signature", "digest", "source", "path", "symlink", "transition", "tooling_bytes", "codesign"])
def test_guards_fail_before_any_app_lifecycle(environment, monkeypatch, guard):
    import json
    import plistlib
    if guard == "dirty":
        environment.dirty = True
    elif guard == "metadata":
        p = environment.state / "active-manifest.json"
        data = json.loads(p.read_text())
        data["runtime_mode"] = "metadata-only"
        p.write_text(json.dumps(data))
    elif guard == "rollback":
        (environment.state / "rollback-required.json").write_text("{}")
    elif guard == "transition":
        monkeypatch.setattr(h, "_assert_no_schema_transition", lambda root: (_ for _ in ()).throw(h.HarnessError("synthetic transition")))
    elif guard == "signature":
        monkeypatch.setattr(h.GrafLocalAdapter, "_measure_signed_app_identity", lambda self, path: ("wrong", "wrong", "wrong"))
    elif guard == "digest":
        (environment.app / "altered").write_text("synthetic change")
    elif guard == "source":
        p = environment.app / "Contents/Info.plist"
        data = plistlib.loads(p.read_bytes())
        data["GRAFSourceSHA"] = "c" * 40
        p.write_bytes(plistlib.dumps(data))
    elif guard in {"tooling_bytes", "codesign"}:
        command = h._run_command
        def reject(argv, **kwargs):
            if guard == "tooling_bytes" and argv[:2] == ["git", "hash-object"]:
                return "e" * 40  # Clean Git status cannot conceal altered tooling bytes.
            if guard == "codesign" and argv[0] == "codesign":
                raise h.HarnessError("synthetic invalid actual signature")
            return command(argv, **kwargs)
        monkeypatch.setattr(h, "_run_command", reject)
    elif guard == "path":
        monkeypatch.setattr(h, "_dev_app_destination", lambda: environment.app.parent / "Other.app")
    elif guard == "symlink":
        link = environment.app.parent / "alias.app"
        link.symlink_to(environment.app)
        monkeypatch.setattr(h, "DEV_APP_PATH", link)
        monkeypatch.setattr(h, "_dev_app_destination", lambda: link)
    with pytest.raises(h.HarnessError):
        validate()
    assert not environment.launches and environment.quits == 0


def test_existing_launch_helper_adds_only_log_environment(monkeypatch, tmp_path):
    app = tmp_path / "GRAF Dev.app"
    app.mkdir()
    states = iter([False, True])
    calls = []
    monkeypatch.setattr(h.GrafLocalAdapter, "_app_is_running", lambda self, path: next(states))
    monkeypatch.setattr(h, "_run_command", lambda command, **kwargs: calls.append(command) or "")
    h.GrafLocalAdapter(ROOT, tmp_path)._launch_dev_app(app, log_directory=tmp_path / "logs")
    assert calls == [["/usr/bin/open", "-n", "--env", f"GRAF_LOG_DIRECTORY={tmp_path / 'logs'}", str(app)]]


@pytest.mark.parametrize("mode", ["pass", "no-window", "replacement", "zombie", "dead", "prefix"])
def test_read_only_observer_checks_runtime_and_fresh_markers(tmp_path, mode):
    import os
    import subprocess

    tools = tmp_path / "bin"
    tools.mkdir()
    # Synthetic lifecycle identity, not an installed app or Mac acceptance proof.
    swift = tools / "swift"
    swift.write_text('''#!/bin/sh
n=0
[ ! -f "$GRAF_FIXTURE_COUNTER" ] || n=$(cat "$GRAF_FIXTURE_COUNTER")
printf '%s' "$((n + 1))" > "$GRAF_FIXTURE_COUNTER"
if [ "$GRAF_FIXTURE_MODE" = replacement ] && [ "$n" -gt 0 ]; then
  printf '%s:9999.0\\n' "$GRAF_FIXTURE_PID"
else
  printf '%s:1234.0\\n' "$GRAF_FIXTURE_PID"
fi
''')
    swift.chmod(0o755)
    ps = tools / "ps"
    ps.write_text('''#!/bin/sh
[ "$GRAF_FIXTURE_MODE" != zombie ] || { printf 'Z\\n'; exit 0; }
exec /bin/ps "$@"
''')
    ps.chmod(0o755)
    logs = tmp_path / "logs"
    logs.mkdir()
    markers = "timestamp event=app_launch_finished detail=fixture\n"
    if mode not in {"no-window", "prefix"}:
        markers += "timestamp event=app_main_window_presented detail=fixture\n"
    elif mode == "prefix":
        markers += "timestamp event=app_main_window_presented_fake detail=fixture\n"
    (logs / "graf.log").write_text(markers)
    process = subprocess.Popen(["/bin/sleep", "30"])
    try:
        if mode == "dead":
            process.terminate()
            process.wait(timeout=5)
        env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ["PATH"],
                   GRAF_FIXTURE_COUNTER=str(tmp_path / "counter"),
                   GRAF_FIXTURE_MODE=mode, GRAF_FIXTURE_PID=str(process.pid))
        result = subprocess.run([
            "sh", str(ROOT / "apps/macos/Scripts/validate-packaged-app-launch.sh"),
            "--observe-installed-dev", f"{process.pid}:1234.0", str(logs),
        ], env=env, capture_output=True, text=True, timeout=20)
        assert (result.returncode == 0) == (mode == "pass"), result.stderr
        if mode == "pass":
            assert "lifecycle=dev-harness" in result.stdout
        if mode != "dead":
            assert process.poll() is None, "read-only observer terminated an unrelated fixture process"
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=5)


def test_launch_helper_refuses_to_reuse_running_app_for_fresh_logs(monkeypatch, tmp_path):
    app = tmp_path / "GRAF Dev.app"
    app.mkdir()
    monkeypatch.setattr(h.GrafLocalAdapter, "_app_is_running", lambda self, path: True)
    monkeypatch.setattr(h, "_run_command", lambda *a, **kw: pytest.fail("must not launch"))
    adapter = h.GrafLocalAdapter(ROOT, tmp_path)
    adapter._launch_dev_app(app)  # Existing normal launch remains idempotent.
    with pytest.raises(h.HarnessError, match="reuse a running"):
        adapter._launch_dev_app(app, log_directory=tmp_path / "logs")


def test_ambiguous_initial_identity_refuses_before_termination(environment, monkeypatch):
    environment.running = True
    def ambiguous(self, path):
        raise h.HarnessError("ambiguous process identity")
    monkeypatch.setattr(h.GrafLocalAdapter, "_app_launch_identity", ambiguous)
    with pytest.raises(h.HarnessError, match="ambiguous"):
        validate(restart=True)
    assert environment.running and environment.quits == 0 and not environment.launches


def test_durable_receipt_precedes_lifecycle_and_records_launched_identity(environment, monkeypatch):
    environment.running = True
    terminate = h.GrafLocalAdapter._terminate_dev_app
    command = h._run_command
    def check_terminate(self, path, **kwargs):
        receipt = h._read_json(environment.state / "app-launch-validation-recovery.json")
        assert receipt["status"] == "in_progress" and receipt["was_running"]
        assert receipt["initial_identity"] == "110:1234.0"
        return terminate(self, path, **kwargs)
    def check_command(argv, **kwargs):
        if argv[0] == "sh":
            receipt = h._read_json(environment.state / "app-launch-validation-recovery.json")
            assert receipt["owned_identity"] == environment.token
        return command(argv, **kwargs)
    monkeypatch.setattr(h.GrafLocalAdapter, "_terminate_dev_app", check_terminate)
    monkeypatch.setattr(h, "_run_command", check_command)
    validate(restart=True)
    assert not (environment.state / "app-launch-validation-recovery.json").exists()


def test_unexpected_running_process_is_preserved_when_launch_is_refused(environment, monkeypatch):
    def refuse(self, path, *, log_directory=None):
        environment.running = True
        raise h.HarnessError("unexpected running process")
    monkeypatch.setattr(h.GrafLocalAdapter, "_launch_dev_app", refuse)
    with pytest.raises(h.HarnessError, match="restoration failed"):
        validate()
    assert environment.running and environment.quits == 0
    receipt = h._read_json(environment.state / "app-launch-validation-recovery.json")
    assert receipt["owned_identity"] is None
    import shutil
    shutil.rmtree(receipt["temporary_log_directory"])


def test_abrupt_controller_exit_leaves_receipt_before_launch(environment, monkeypatch):
    import os
    import shutil
    def interrupted(self, path, *, log_directory=None):
        os._exit(93)  # Synthetic controller dies; no installed app is launched.
    monkeypatch.setattr(h.GrafLocalAdapter, "_launch_dev_app", interrupted)
    child = os.fork()
    if child == 0:
        try:
            validate()
        finally:
            os._exit(94)
    _, exit_status = os.waitpid(child, 0)
    assert os.waitstatus_to_exitcode(exit_status) == 93
    receipt = h._read_json(environment.state / "app-launch-validation-recovery.json")
    assert receipt["status"] == "in_progress" and receipt["owned_identity"] is None
    with pytest.raises(h.HarnessError, match="resolved recovery"):
        validate()
    status = h.operation_status(SimpleNamespace(live=True))
    assert status["status"] == "blocked" and status["app_launch_recovery"] == receipt
    shutil.rmtree(receipt["temporary_log_directory"])


def test_identity_bound_termination_passes_token_to_native_helper(monkeypatch, tmp_path):
    calls = []
    states = iter([True, False])
    monkeypatch.setattr(h.GrafLocalAdapter, "_app_is_running", lambda self, path: next(states))
    monkeypatch.setattr(h, "_run_command", lambda command, **kwargs: calls.append(command) or "")
    h.GrafLocalAdapter(ROOT, tmp_path)._terminate_dev_app(h.DEV_APP_PATH, expected_identity="110:1234.0")
    assert calls[0][-3:] == ["terminate", str(h.DEV_APP_PATH), "110:1234.0"]


@pytest.mark.parametrize("operation", ["build", "promote", "rollback", "recover-schema", "rehydrate", "prune", "reset-data"])
def test_recovery_receipt_blocks_other_mutating_operations_before_adapter(environment, tmp_path, operation, monkeypatch):
    receipt = environment.state / "app-launch-validation-recovery.json"
    receipt.write_text('{"status":"in_progress"}')
    manifest = tmp_path / "manifest.json"
    h._write_json(manifest, environment.active)
    arguments = {
        "build": ["--sha", "a" * 40, "--live"],
        "promote": ["--manifest", str(manifest), "--live"],
        "rollback": ["--live"], "recover-schema": [],
        "rehydrate": ["--manifest", str(manifest)],
        "prune": [], "reset-data": ["--confirm-dev-reset"],
    }
    for method in ("build", "promote", "rollback", "rehydrate", "estimate_or_apply_prune"):
        monkeypatch.setattr(h.GrafLocalAdapter, method, lambda *a, **kw: pytest.fail("recovery must block adapter"))
    with pytest.raises(h.HarnessError, match="resolved recovery"):
        h.dispatch(h.parser().parse_args([operation, *arguments[operation]]))
    assert receipt.read_text() == '{"status":"in_progress"}'
    assert not environment.launches and environment.quits == 0
