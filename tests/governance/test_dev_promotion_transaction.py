import argparse
import fcntl
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
import tempfile

import pytest

from pathlib import Path


OLD = "a" * 40
NEW = "b" * 40
ROOT = Path(__file__).resolve().parents[2]


def test_promotion_is_lock_protected_and_pointer_written_after_smoke():
    source = (ROOT / "scripts/dev-harness.py").read_text()
    assert "with state_lock(root)" in source
    assert "self._assert_transition_smoke(checks)" in source
    assert "active-manifest.json" in source


def test_runtime_compensation_refuses_unowned_processes():
    source = (ROOT / "scripts/dev-harness.py").read_text()
    assert "refusing to terminate unverified Dev backend pid" in source
    assert "refusing to restore over unverified Dev backend pid" in source
    assert "deadline = time.monotonic() + RUNTIME_CLEANUP_TIMEOUT_SECONDS" in source


def test_app_swap_rechecks_lifecycle_and_allows_cleanup_grace():
    installer = (ROOT / "apps/macos/Scripts/install-dev-app.sh").read_text()
    lifecycle = (ROOT / "apps/macos/Scripts/dev-app-lifecycle.swift").read_text()
    harness = (ROOT / "scripts/dev-harness.py").read_text()
    assert installer.count('assert_app_stopped') >= 2
    ditto_offset = installer.index('ditto --norsrc --noextattr --noqtn "$CANDIDATE" "$STAGED_DESTINATION"')
    assert installer.index('assert_app_stopped', ditto_offset) > ditto_offset
    assert 'LaunchServices registration failed' in installer
    assert 'swift "$APP_LIFECYCLE" swap "$STAGED_DESTINATION" "$DESTINATION"' in installer
    assert 'DESTINATION_WAS_PRESENT=false' in installer
    assert 'mv "$DESTINATION" "$STAGED_DESTINATION"' in installer
    assert 'renameatx_np' in lifecycle
    assert 'RENAME_SWAP' in lifecycle
    assert 'expectedDevDestination' in lifecycle
    assert 'app swap destination must be /Applications/GRAF Dev.app' in lifecycle
    assert 'assertDevBundle(staged' in lifecycle
    assert 'assertDevBundle(installed' in lifecycle
    registration_offset = installer.index('if ! "$LSREGISTER" -f "$DESTINATION"')
    assert 'rm -rf "$DESTINATION"' not in installer
    assert 'BACKUP_DESTINATION' not in installer
    assert installer.index('rm -rf "$STAGED_DESTINATION"', registration_offset) > registration_offset
    assert 'expectedBundleIdentifier = "pro.2brain.graf.dev"' in lifecycle
    assert 'destination must not be a symlink' in lifecycle
    assert 'application.bundleIdentifier == expectedBundleIdentifier' in lifecycle
    assert "APP_STOP_TIMEOUT_SECONDS = 30" in harness
    assert "deadline = time.monotonic() + APP_STOP_TIMEOUT_SECONDS" in harness
    assert "if not self._app_is_running(destination):" in harness
    assert harness.count("if self._app_is_running(destination):") >= 2
    assert "check=True" in harness
    assert "def _atomic_swap_dev_app" in harness
    restore = harness[harness.index("    def _restore_app("):harness.index("    def _restore_runtime(")]
    assert "shutil.rmtree(destination)" not in restore
    assert "self._atomic_swap_dev_app(restored, destination)" in restore

    transaction = harness[harness.index("    def _ordinary_transition("):harness.index("    def _write_ordinary_receipt(")]
    assert transaction.index("previous_app_was_running = self._app_is_running") < transaction.index(
        "app_backup = self._snapshot_app()"
    )


# These subprocesses execute real control flow with file markers in place of
# all app/runtime effects. No app bundle, Docker, Swift or network is used.
def _crash_harness(root):
    spec = importlib.util.spec_from_file_location('crash_probe_harness', ROOT / 'scripts/dev-harness.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._state_ownership = lambda root: False
    module.state_dir = lambda **kwargs: root
    module._repo_root = lambda: root
    module._assert_dev_environment = lambda: None
    module._assert_empty_dev_machine = lambda: None
    module._dev_app_destination = lambda: root / 'installed-marker'
    module._installed_app_state = lambda: {'installed': (root / 'installed-marker').exists()}
    module._status_app_fields = lambda **kwargs: {'app': {'installed': (root / 'installed-marker').exists(), 'synthetic': True}}
    def forbidden(*args, **kwargs):
        raise AssertionError('Unexpected external command; diagnostic stopped')
    module._test_command = module._run_command
    module._run_command = forbidden
    module._run_command_combined = forbidden
    return module


def _crash_handshake(root, boundary, selected):
    if selected == boundary:
        (root / 'ready').write_text(boundary)
        while True:
            time.sleep(0.05)


def _runtime_marker(sha):
    return {"source_sha": sha, "mode": "compose", "pid": 99999999,
            "command": "synthetic runtime marker", "start_token": "synthetic-start",
            "runtime_definition_digest": "sha256:" + "d" * 64}


def _crash_worker(root, selected, command):
    module = _crash_harness(root)
    cls = module.GrafLocalAdapter
    faults = json.loads((root / 'faults.json').read_text()) if (root / 'faults.json').exists() else []
    def fault(boundary):
        _crash_handshake(root, boundary, selected)
        if boundary in faults:
            faults.remove(boundary)
            raise OSError('injected ' + boundary)
    write = module._write_json
    def write_with_fault(path, value):
        if path.name == 'rollback-required.json':
            fault('receipt-write')
        if (root / 'rollback-required.json').exists():
            if path.parent.name == 'manifests':
                fault('manifest-write')
            elif path.name == 'active-manifest.json':
                fault('pointer-write')
        write(path, value)
    module._write_json = write_with_fault
    unlink = Path.unlink
    def unlink_with_fault(path, *args, **kwargs):
        if path == root / 'rollback-required.json':
            fault('receipt-unlink')
        result = unlink(path, *args, **kwargs)
        if path.parent.name == 'manifests':
            fault('after-target-record-unlink')
        return result
    Path.unlink = unlink_with_fault
    sync = module._fsync_directory
    def sync_with_fault(path):
        if path == root and (root / 'completed-publication').exists() and not (root / 'rollback-required.json').exists():
            fault('receipt-sync')
        return sync(path)
    module._fsync_directory = sync_with_fault
    cls._assert_supported = lambda self: None
    cls._assert_source_matches_checkout = lambda self, manifest: None
    cls._checkout_adapter = lambda self, checkout, manifest: cls(checkout, self.state)
    cls._runtime_definition_digest = lambda self: 'sha256:' + 'd' * 64
    cls._checked_app_bundle = lambda self, manifest: root
    def validate(self, manifest, path):
        assert path.read_text() == manifest['source_sha']
    cls._validate_launch_bundle = validate
    cls._env = lambda self, manifest: {}
    cls._compose_config = lambda self, env: None
    cls._runtime_is_live = lambda self, record: record is not None
    cls._previous_adapter = lambda self, *args: self
    cls._assert_manifest_images = lambda self, *args: None
    cls._app_is_running = lambda self, path: (root / 'running-without-bundle').exists()
    def snapshot(self):
        if not (root / 'installed-marker').exists():
            return None
        backup = root / 'transactions' / 'previous-marker.app'
        backup.mkdir(parents=True)
        (backup / 'version').write_bytes((root / 'installed-marker').read_bytes())
        return backup
    cls._snapshot_app = snapshot
    def stop(self):
        _crash_handshake(root, 'before-stop', selected)
        (root / 'runtime-observed').write_text('stopped')
        _crash_handshake(root, 'after-stop', selected)
    cls._stop_previous = stop
    cls._terminate_dev_app = lambda self, path: None
    def install(self, manifest, env):
        _crash_handshake(root, 'before-install', selected)
        (root / 'installed-marker').write_text(manifest['source_sha'])
        _crash_handshake(root, 'after-install', selected)
        fault('install-failure')
    cls._install_app = install
    def start(self, manifest, env):
        _crash_handshake(root, 'before-start', selected)
        (root / 'runtime-observed').write_text(manifest['source_sha'])
        module._write_json(root / 'runtime.json', _runtime_marker(manifest['source_sha']))
        _crash_handshake(root, 'after-start', selected)
    cls._start_backend = start
    cls._launch_dev_app = lambda self, path: None
    def restore(self, backup):
        fault('before-restore')
        if backup is None:
            (root / 'installed-marker').unlink(missing_ok=True)
        else:
            (root / 'installed-marker').write_bytes((backup / 'version').read_bytes())
        fault('after-restore')
    cls._restore_app = restore
    restore_runtime = cls._restore_runtime
    def restore_backend(self, *args):
        fault('before-restore-runtime')
        restore_runtime(self, *args)
        if args[0] is None:
            (root / 'runtime-observed').write_text('stopped')
        fault('after-restore-runtime')
    cls._restore_runtime = restore_backend
    def smoke(self, manifest):
        _crash_handshake(root, 'before-smoke', selected)
        _crash_handshake(root, 'after-smoke', selected)
        return {key: 'pass' for key in ('backend_health', 'frontend_reachability',
            'auth_session_bootstrap', 'representative_api', 'processing_worker_readiness',
            'media_worker_readiness', 'database_readiness', 'storage_readiness',
            'temporal_readiness', 'migration_readiness', 'exact_source_sha',
            'app_identity', 'app_presentation')}
    cls.smoke = smoke
    cls._ensure_rollback_archive = lambda self, previous: None
    cls._apply_retention = lambda self, *args, **kwargs: None
    remove = module.shutil.rmtree
    def cleanup(path, *args, **kwargs):
        if Path(path).name == 'previous-marker.app':
            _crash_handshake(root, 'before-cleanup', selected)
            fault('cleanup-failure')
        result = remove(path, *args, **kwargs)
        if Path(path).name == 'previous-marker.app':
            _crash_handshake(root, 'after-cleanup', selected)
        return result
    module.shutil.rmtree = cleanup
    publish = module._publish_active
    def publish_at_boundary(state, manifest, mode):
        _crash_handshake(root, 'before-pointer', selected)
        publish(state, manifest, mode)
        (root / 'completed-publication').touch()
        _crash_handshake(root, 'after-pointer', selected)
    module._publish_active = publish_at_boundary
    if command == 'rollback':
        result = module.operation_rollback(argparse.Namespace(manifest_id=None, live=True, dry_run=False, previous_checkout=None, target_checkout=None))
    else:
        result = module.operation_promote(argparse.Namespace(manifest=root / 'candidate.json', live=True, dry_run=False, previous_checkout=None))
    (root / 'completed').write_text(result['status'])



@pytest.mark.parametrize(("command", "boundary"), [
    (command, boundary)
    for command in ("promote", "rollback", "first-install")
    for boundary in (
        "none", "before-stop", "after-stop", "before-install", "after-install",
        "before-start", "after-start", "before-smoke", "after-smoke",
        "before-pointer", "after-pointer", "before-cleanup", "after-cleanup",
    )
    if command != "first-install" or not boundary.endswith("cleanup")
])
def test_ordinary_promotion_crash_requires_verified_recovery(command, boundary):
    with tempfile.TemporaryDirectory(prefix="graf-f224-crash-test-") as temporary:
        _exercise_crash(Path(temporary).resolve(), command, boundary)


def _exercise_crash(root, command, boundary, tamper=None):
    harness, previous, target, protected, lock, inode = _prepare_crash(root, command)
    process = _start_crash_worker(root, boundary, command)
    try:
        if boundary != "none":
            deadline = time.monotonic() + 10
            while not (root / "ready").exists():
                if process.poll() is not None:
                    out, err = process.communicate()
                    pytest.fail(f"worker exited before {boundary}: {process.returncode}: {out} {err}")
                if time.monotonic() > deadline:
                    pytest.fail(f"handshake timeout at {boundary}")
                time.sleep(0.01)
            process.kill()
        out, err = process.communicate(timeout=10)
        assert process.returncode == (0 if boundary == "none" else -signal.SIGKILL), (out, err)
        assert protected.read_bytes() == b"synthetic protected bytes"
        assert lock.stat().st_ino == inode
        status = harness.operation_status(argparse.Namespace())
        if boundary == "none" or boundary.endswith("cleanup"):
            assert status["status"] == "active"
            assert status["manifest"]["source_sha"] == target["source_sha"]
            assert (root / "installed-marker").read_text() == target["source_sha"]
            assert (root / "runtime-observed").read_text() == target["source_sha"]
            assert not (root / "rollback-required.json").exists()
        else:
            assert status["status"] == "rollback_required", {
                "boundary": boundary, "command": command, "reported": status["status"],
                "active": status.get("manifest", {}).get("source_sha"),
                "installed": (root / "installed-marker").read_text() if (root / "installed-marker").exists() else None,
                "runtime": (root / "runtime-observed").read_text() if (root / "runtime-observed").exists() else None,
            }
            assert (root / "rollback-required.json").is_file()
            if command != "first-install":
                assert (root / "transactions" / "previous-marker.app").is_dir()
        if boundary != "none" and not boundary.endswith("cleanup"):
            (root / "faults.json").unlink(missing_ok=True)
            if tamper is not None:
                _tamper_recovery(root, tamper)
            guarded = {name: (root / name).read_bytes() if (root / name).exists() else None for name in
                       ("rollback-required.json", "installed-marker", "runtime.json", "runtime-observed")}
            retry = _start_crash_worker(root, "none", "rollback" if tamper == "different-command" else command)
            retry_out, retry_err = retry.communicate(timeout=10)
            if tamper is not None and tamper != "controller-token":
                assert retry.returncode != 0 and "HarnessError" in retry_err, retry_err
                assert guarded == {name: (root / name).read_bytes() if (root / name).exists() else None for name in guarded}
                assert protected.read_bytes() == b"synthetic protected bytes"
                assert lock.stat().st_ino == inode
                return
            assert retry.returncode == 0, (retry_out, retry_err)
            restored = harness.operation_status(argparse.Namespace())
            assert restored["status"] == "active"
            assert restored["manifest"]["source_sha"] == target["source_sha"]
            assert (root / "installed-marker").read_text() == target["source_sha"]
            assert (root / "runtime-observed").read_text() == target["source_sha"]
            assert not (root / "rollback-required.json").exists()
            assert not (root / "transactions" / "previous-marker.app").exists()
            assert protected.read_bytes() == b"synthetic protected bytes"
            assert lock.stat().st_ino == inode
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def _prepare_crash(root, command):
    harness = _crash_harness(root)
    previous = harness.build_manifest(OLD, "224", "synthetic-test", "same-revision", root)
    previous.update(status="active", health={"result": "pass", "checks": {}, "checked_at": harness.now()})
    if command != "first-install":
        harness._publish_active(root, previous, "live")
    target = harness.build_manifest(NEW, "224", "synthetic-test", "same-revision", root)
    for component in ("database", "storage", "temporal"):
        target["components"][component]["digest"] = previous["components"][component]["digest"]
    if command == "rollback":
        target.update(status="active", health={"result": "pass", "checks": {}, "checked_at": harness.now()})
        harness._publish_active(root, target, "live")
        previous, target = target, previous
    harness._write_json(root / "candidate.json", target)
    if command != "first-install":
        harness._write_json(root / "runtime.json", _runtime_marker(previous["source_sha"]))
        (root / "installed-marker").write_text(previous["source_sha"])
        (root / "runtime-observed").write_text(previous["source_sha"])
    protected = root / "protected-data-marker"
    protected.write_bytes(b"synthetic protected bytes")
    lock = root / "promote.lock"
    lock.touch()
    inode = lock.stat().st_ino
    return harness, previous, target, protected, lock, inode


def _start_crash_worker(root, boundary, command):
    return subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--crash-worker", str(root), boundary, command],
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


def test_missing_bundle_with_live_app_refuses_before_recovery_writes():
    with tempfile.TemporaryDirectory(prefix="graf-f224-missing-live-app-") as temporary:
        root = Path(temporary).resolve()
        harness, previous, _, protected, lock, inode = _prepare_crash(root, "promote")
        harness._write_json(root / "candidate.json", previous)
        (root / "installed-marker").unlink()
        (root / "running-without-bundle").touch()
        before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        process = _start_crash_worker(root, "none", "promote")
        out, err = process.communicate(timeout=10)
        assert process.returncode != 0 and "running Dev app has no installed bundle" in err, (out, err)
        assert before == {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        assert not (root / "rollback-required.json").exists()
        assert not (root / "transactions").exists()
        assert protected.read_bytes() == b"synthetic protected bytes"
        assert lock.stat().st_ino == inode


@pytest.mark.parametrize("partial_publication", [False, True])
@pytest.mark.parametrize("stored_candidate", [False, True])
def test_compensated_promotion_keeps_ready_candidate_for_prune(partial_publication, stored_candidate):
    with tempfile.TemporaryDirectory(prefix="graf-f224-ready-candidate-") as temporary:
        root = Path(temporary).resolve()
        harness, previous, target, _, _, _ = _prepare_crash(root, "promote")
        candidate_path = harness._manifest_path(root, target["manifest_id"])
        if stored_candidate:
            harness._write_json(candidate_path, target)
        before = candidate_path.read_bytes() if stored_candidate else None
        if partial_publication:
            (root / "faults.json").write_text(json.dumps(["pointer-write"]))
            process = _start_crash_worker(root, "none", "promote")
            out, err = process.communicate(timeout=10)
            assert process.returncode != 0 and "pointer-write" in err, (out, err)
            assert (root / "rollback-required.json").exists()
        (root / "faults.json").write_text(json.dumps(["install-failure"]))
        process = _start_crash_worker(root, "none", "promote")
        out, err = process.communicate(timeout=10)
        assert process.returncode != 0 and "live promote failed" in err, (out, err)
        assert harness._load_active(root)["manifest_id"] == previous["manifest_id"]
        assert not (root / "rollback-required.json").exists()
        if not stored_candidate:
            assert not candidate_path.exists()
            return
        assert candidate_path.read_bytes() == before
        adapter = harness.GrafLocalAdapter(root, root)
        assert target["manifest_id"] in adapter._pending_candidate_ids(harness._load_active(root))
        artifact = root / "artifacts" / target["manifest_id"] / "GRAF Dev.app"
        artifact.mkdir(parents=True)
        (artifact / "marker").write_text("candidate")
        harness._run_command = lambda *args, **kwargs: ""
        harness.operation_prune(argparse.Namespace(dry_run=False, live=False, json=True))
        assert (artifact / "marker").read_text() == "candidate"


def test_recovery_refuses_unknown_live_controller_token(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    harness, _, target, _, _, _ = _pending_operation(root)
    adapter = harness.GrafLocalAdapter(root, root)
    monkeypatch.setattr(adapter, "_assert_supported", lambda: None)
    monkeypatch.setattr(adapter, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(adapter, "_process_start_token", lambda pid: "")
    before = (root / "rollback-required.json").read_bytes()
    with pytest.raises(harness.HarnessError, match="another live controller"):
        adapter._ordinary_transition("promote", target)
    assert (root / "rollback-required.json").read_bytes() == before


def test_same_active_compensation_keeps_active_manifest(tmp_path):
    root = tmp_path.resolve()
    harness, previous, _, _, _, _ = _prepare_crash(root, "promote")
    harness._write_json(root / "candidate.json", previous)
    (root / "installed-marker").unlink()
    (root / "faults.json").write_text(json.dumps(["install-failure"]))
    process = _start_crash_worker(root, "none", "promote")
    out, err = process.communicate(timeout=10)
    assert process.returncode != 0 and "live promote failed" in err, (out, err)
    restored = harness._load_active(root)
    assert restored["status"] == "active" and harness._same_pinned_manifest(restored, previous)
    assert not (root / "rollback-required.json").exists()
    assert not (root / "installed-marker").exists()


@pytest.mark.parametrize("command", ["promote", "first-install"])
def test_compensation_crash_after_target_record_removal_can_retry(tmp_path, command):
    root = tmp_path.resolve()
    harness, previous, target, protected, lock, inode = _prepare_crash(root, command)
    (root / "faults.json").write_text(json.dumps(["receipt-unlink"]))
    first = _start_crash_worker(root, "none", command)
    out, err = first.communicate(timeout=10)
    assert first.returncode != 0 and "receipt removal failed" in err, (out, err)
    assert harness._load_active(root)["manifest_id"] == target["manifest_id"]
    (root / "faults.json").write_text(json.dumps(["install-failure"]))
    second = _start_crash_worker(root, "after-target-record-unlink", command)
    try:
        _wait_marker(root / "ready")
    finally:
        second.kill()
        second.communicate(timeout=5)
    assert second.returncode == -signal.SIGKILL
    active = harness._load_active(root)
    assert active is None if command == "first-install" else active["manifest_id"] == previous["manifest_id"]
    assert (root / "rollback-required.json").exists()
    (root / "faults.json").unlink()
    retry = _start_crash_worker(root, "none", command)
    out, err = retry.communicate(timeout=10)
    assert retry.returncode == 0, (out, err)
    assert harness._load_active(root)["manifest_id"] == target["manifest_id"]
    assert not (root / "rollback-required.json").exists()
    assert protected.read_bytes() == b"synthetic protected bytes" and lock.stat().st_ino == inode


@pytest.mark.parametrize("failure", ["write", "unlink", "sync", "readback"])
def test_target_record_restore_failure_keeps_receipt(tmp_path, monkeypatch, failure):
    root = tmp_path.resolve()
    harness, previous, target, _, _, _ = _pending_operation(root)
    adapter = harness.GrafLocalAdapter(root, root)
    path = harness._manifest_path(root, target["manifest_id"])
    with harness.state_lock(root):
        operation = harness._read_ordinary_operation(root)
        operation.update(controller_pid=os.getpid(), controller_start=adapter._process_start_token(os.getpid()),
                         target_record=target if failure in {"write", "readback"} else None)
        adapter._write_ordinary_receipt(operation)
        harness._write_json(path, dict(target, status="active"))
        before = (root / "rollback-required.json").read_bytes()
        write, read, unlink, sync = harness._write_json, harness._read_json, Path.unlink, harness._fsync_directory
        def fail():
            raise OSError("injected target record " + failure)
        if failure == "write":
            monkeypatch.setattr(harness, "_write_json", lambda p, v: fail() if p == path else write(p, v))
        elif failure == "unlink":
            monkeypatch.setattr(Path, "unlink", lambda p, *a, **kw: fail() if p == path else unlink(p, *a, **kw))
        elif failure == "sync":
            monkeypatch.setattr(harness, "_fsync_directory", lambda p: fail() if p == path.parent else sync(p))
        else:
            monkeypatch.setattr(harness, "_read_json", lambda p: dict(target, status="active") if p == path else read(p))
        with pytest.raises((OSError, harness.HarnessError)):
            adapter._complete_ordinary(operation, previous)
        assert (root / "rollback-required.json").read_bytes() == before
        assert harness._load_active(root)["manifest_id"] == previous["manifest_id"]


@pytest.mark.parametrize(("command", "failure"), [
    (command, failure)
    for command in ("promote", "rollback", "first-install")
    for failure in ("receipt-write", "manifest-write", "pointer-write", "receipt-unlink", "receipt-sync",
                    "install-failure", "compensation-failure", "cleanup-failure")
    if (command, failure) != ("first-install", "cleanup-failure")
])
def test_ordinary_write_and_compensation_failures(command, failure):
    with tempfile.TemporaryDirectory(prefix="graf-f224-write-fault-") as temporary:
        root = Path(temporary).resolve()
        harness, previous, target, protected, lock, inode = _prepare_crash(root, command)
        failures = ["install-failure", "after-restore"] if failure == "compensation-failure" else [failure]
        (root / "faults.json").write_text(json.dumps(failures))
        process = _start_crash_worker(root, "none", command)
        out, err = process.communicate(timeout=10)
        warning_only = failure in {"receipt-sync", "cleanup-failure"}
        assert (process.returncode == 0) == warning_only, (out, err)
        assert protected.read_bytes() == b"synthetic protected bytes"
        assert lock.stat().st_ino == inode
        marker = root / "rollback-required.json"
        backup = root / "transactions/previous-marker.app"
        active = harness._load_active(root)
        if warning_only:
            assert '"status": "warning"' in err
            assert active["source_sha"] == target["source_sha"]
            assert (root / "installed-marker").read_text() == target["source_sha"]
            assert (root / "runtime-observed").read_text() == target["source_sha"]
            assert not marker.exists()
            assert backup.exists() == (command != "first-install")
        elif failure in {"receipt-write", "install-failure"}:
            assert not marker.exists()
            if command == "first-install":
                assert active is None
                assert not (root / "installed-marker").exists()
                assert not (root / "runtime.json").exists()
            else:
                assert active["source_sha"] == previous["source_sha"]
                assert (root / "installed-marker").read_text() == previous["source_sha"]
                assert (root / "runtime-observed").read_text() == previous["source_sha"]
        else:
            assert marker.is_file()
            assert harness.operation_status(argparse.Namespace())["status"] == "rollback_required"
            assert backup.exists() == (command != "first-install")
            (root / "faults.json").unlink()
            retry = _start_crash_worker(root, "none", command)
            retry_out, retry_err = retry.communicate(timeout=10)
            assert retry.returncode == 0, (retry_out, retry_err)
            assert harness._load_active(root)["source_sha"] == target["source_sha"]
            assert (root / "installed-marker").read_text() == target["source_sha"]
            assert (root / "runtime-observed").read_text() == target["source_sha"]
            assert not marker.exists()
        assert protected.read_bytes() == b"synthetic protected bytes"
        assert lock.stat().st_ino == inode


@pytest.mark.parametrize("command", ["promote", "rollback", "first-install"])
@pytest.mark.parametrize("boundary", ["before-restore", "after-restore", "before-restore-runtime", "after-restore-runtime"])
def test_sigkill_during_compensation_keeps_exact_retry(command, boundary):
    with tempfile.TemporaryDirectory(prefix="graf-f224-compensation-crash-") as temporary:
        root = Path(temporary).resolve()
        (root / "faults.json").write_text(json.dumps(["install-failure"]))
        # The same full coordinator is killed during compensation; the retry
        # has no injected failure and must still complete the original target.
        try:
            _exercise_crash(root, command, boundary)
        finally:
            (root / "faults.json").unlink(missing_ok=True)


def _tamper_recovery(root, case):
    path = root / "rollback-required.json"
    receipt = json.loads(path.read_text())
    operation = receipt["operation"]
    candidate_path = root / "candidate.json"
    candidate = json.loads(candidate_path.read_text())
    if case == "target-digest":
        candidate["components"]["macos_app"]["digest"] = "sha256:" + "e" * 64
    elif case == "identity":
        candidate["app_identity"]["signing_identity"] = "another signer"
    elif case == "boundary":
        candidate["dev_boundary"]["backend_origin"] = "http://127.0.0.1:19999"
    elif case == "parent":
        candidate["parent_manifest_id"] = "another-parent"
    elif case == "operator":
        candidate["operator"] = "changed operator"
    elif case == "feature":
        candidate["feature_id"] = "225"
    elif case in {"controller-pid", "controller-token"}:
        operation["controller_pid"] = os.getpid()
        operation["controller_start"] = (_crash_harness(root).GrafLocalAdapter(root, root)._process_start_token(os.getpid())
                                         if case == "controller-pid" else "wrong start token")
    elif case == "backup-digest":
        operation["backup_digest"] = "sha256:" + "e" * 64
    elif case == "backup-path":
        operation["backup"] = "../previous-escape.app"
    elif case == "backup-link":
        backup = root / operation["backup"]
        kept = root / "kept-backup"
        backup.rename(kept)
        backup.symlink_to(kept, target_is_directory=True)
    elif case == "checkout-digest":
        operation["checkouts"]["target"]["digest"] = "sha256:" + "e" * 64
    elif case == "checkout-missing":
        operation["checkouts"]["target"]["root"] = str(root / "missing-checkout")
    elif case in {"runtime-pid", "runtime-digest"}:
        runtime_path = root / "runtime.json"
        runtime = json.loads(runtime_path.read_text())
        if case == "runtime-pid":
            runtime["pid"] = os.getpid()
        else:
            runtime["runtime_definition_digest"] = "sha256:" + "e" * 64
        runtime_path.write_text(json.dumps(runtime))
    elif case == "old-receipt":
        receipt.pop("operation")
    elif case != "different-command":
        raise AssertionError(case)
    path.write_text(json.dumps(receipt))
    candidate_path.write_text(json.dumps(candidate))


@pytest.mark.parametrize("tamper", [
    "target-digest", "identity", "boundary", "parent", "operator", "feature",
    "controller-pid", "controller-token", "backup-digest", "backup-path", "backup-link",
    "checkout-digest", "checkout-missing", "runtime-pid", "runtime-digest",
    "old-receipt", "different-command",
])
def test_recovery_rejects_changed_identity_before_effects(tamper):
    with tempfile.TemporaryDirectory(prefix="graf-f224-invalid-retry-") as temporary:
        _exercise_crash(Path(temporary).resolve(), "promote", "after-install", tamper)


def test_operation_lock_context_closes_fd_and_rejects_nested_or_foreign_locks():
    with tempfile.TemporaryDirectory(prefix="graf-f224-lock-context-") as temporary:
        root = Path(temporary).resolve()
        harness = _crash_harness(root)
        with pytest.raises(RuntimeError, match="injected"):
            with harness.state_lock(root):
                fd, = harness._command_lock_fds()
                assert os.fstat(fd).st_ino == (root / "promote.lock").stat().st_ino
                with pytest.raises(harness.HarnessError, match="nested"):
                    with harness.state_lock(root / "other"):
                        pytest.fail("nested lock was accepted")
                token = harness._HELD_OPERATION_LOCK.set((99999999, root, fd))
                try:
                    with pytest.raises(harness.HarnessError, match="another controller"):
                        harness._command_lock_fds()
                finally:
                    harness._HELD_OPERATION_LOCK.reset(token)
                raise RuntimeError("injected")
        assert harness._command_lock_fds() == ()
        with pytest.raises(OSError):
            os.fstat(fd)


def _lock_busy(path):
    with path.open("r+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
    return False


def _wait_marker(path):
    deadline = time.monotonic() + 10
    while not path.exists():
        assert time.monotonic() < deadline, f"process did not publish {path.name}"
        time.sleep(0.01)


def _lock_worker(root, route):
    harness = _crash_harness(root)
    child = """import pathlib,sys,time
root=pathlib.Path(sys.argv[1])
(root/'child-ready').touch()
deadline=time.monotonic()+10
while not (root/'release').exists() and time.monotonic()<deadline: time.sleep(.01)
(root/'child-done').touch()
"""
    adapter = harness.GrafLocalAdapter(ROOT, root)
    harness._run_command = harness._test_command
    harness._dev_app_destination = lambda: harness.DEV_APP_PATH
    env = dict(os.environ, GRAF_TEST_ROOT=str(root))
    if route != "command":
        binaries = root / "bin"
        binaries.mkdir()
        stub = (f'#!{sys.executable}\n' + child.replace(
            'root=pathlib.Path(sys.argv[1])',
            'import os\nroot=pathlib.Path(os.environ["GRAF_TEST_ROOT"])')
            + '\nprint("running")\n')
        for name in ("swift", "docker"):
            path = binaries / name
            path.write_text(stub)
            path.chmod(0o700)
        env["PATH"] = str(binaries) + os.pathsep + os.environ["PATH"]
        env["TMPDIR"] = str(root)
        os.environ.update(env)
        adapter._env = lambda manifest: env
    with harness.state_lock(root):
        if route == "installer":
            # The real installer stops at its first lifecycle check. Returning
            # running prevents any build, copy or write to /Applications.
            adapter._checked_app_bundle = lambda manifest: root
            adapter._install_app({}, env)
        elif route == "compose":
            adapter._schema_compose({}, "stop")
        elif route == "lifecycle":
            adapter._atomic_swap_dev_app(root / "unused", harness.DEV_APP_PATH)
        else:
            harness._test_command([sys.executable, "-c", child, str(root)], cwd=root)


@pytest.mark.parametrize("route", ["command", "installer", "compose", "lifecycle"])
def test_mutating_child_keeps_original_lock_after_controller_sigkill(route):
    with tempfile.TemporaryDirectory(prefix="graf-f224-child-lock-") as temporary:
        root = Path(temporary).resolve()
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--lock-worker", str(root), route])
        try:
            _wait_marker(root / "child-ready")
            lock = root / "promote.lock"
            inode = lock.stat().st_ino
            assert _lock_busy(lock)
            process.kill()
            assert process.wait(timeout=5) == -signal.SIGKILL
            assert _lock_busy(lock), "mutating child survived, but promote.lock was released"
            assert lock.stat().st_ino == inode
        finally:
            (root / "release").touch()
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            if (root / "child-ready").exists():
                _wait_marker(root / "child-done")
                deadline = time.monotonic() + 5
                while _lock_busy(lock):
                    assert time.monotonic() < deadline, "finished child did not release lock"
                    time.sleep(0.01)
                assert lock.stat().st_ino == inode


def _pending_operation(root):
    prepared = _prepare_crash(root, "promote")
    process = _start_crash_worker(root, "after-install", "promote")
    try:
        _wait_marker(root / "ready")
    finally:
        process.kill()
        process.communicate(timeout=5)
    assert process.returncode == -signal.SIGKILL
    (root / "ready").unlink()
    return prepared


def _startup_worker(root, boundary):
    harness = _crash_harness(root)
    adapter = harness.GrafLocalAdapter(root, root)
    adapter.start_script = root / "startup.sh"
    adapter._runtime_definition_digest = lambda: "sha256:" + "d" * 64
    adapter._wait_runtime_ready = lambda *args: _crash_handshake(root, "after-permit", boundary)
    spawn = subprocess.Popen
    def capture(*args, **kwargs):
        child = spawn(*args, **kwargs)
        if harness.SCHEMA_STARTUP_GATE in args[0]:
            (root / "startup-pid").write_text(str(child.pid))
        return child
    harness.subprocess.Popen = capture
    write = harness._write_json
    def runtime_write(path, value):
        if path.name == "runtime.json":
            if boundary == "record-failure":
                raise OSError("injected runtime record failure")
            _crash_handshake(root, "before-record", boundary)
        write(path, value)
        if path.name == "runtime.json":
            _crash_handshake(root, "after-record", boundary)
    harness._write_json = runtime_write
    with harness.state_lock(root):
        operation = harness._read_ordinary_operation(root)
        operation.update(controller_pid=os.getpid(), controller_start=adapter._process_start_token(os.getpid()))
        adapter._write_ordinary_receipt(operation)
        adapter._start_backend(operation["target"], os.environ.copy())


@pytest.mark.parametrize("route", [
    "manifest", "cli-build", "cli-rehydrate", "cli-prune", "cli-smoke", "cli-reset",
    "promote-dry", "rollback-dry", "build", "rehydrate", "retention", "prune",
    "schema-cleanup", "startup", "smoke", "startup-guard",
])
def test_pending_operation_blocks_competing_routes_before_effects(tmp_path, route):
    root = tmp_path.resolve()
    harness, previous, target, protected, lock, inode = _pending_operation(root)
    adapter = harness.GrafLocalAdapter(root, root)
    adapter._assert_supported = lambda: None
    adapter._wait_http = lambda *args, **kwargs: pytest.fail("probe started before recovery guard")
    args = argparse.Namespace(manifest=root / "candidate.json", live=True, dry_run=True,
                              fixture=False, confirm_dev_reset=True)
    actions = {
        "manifest": lambda: harness.build_manifest(NEW, "224", root=root),
        "cli-build": lambda: harness.operation_build(args),
        "cli-rehydrate": lambda: harness.operation_rehydrate(args),
        "cli-prune": lambda: harness.operation_prune(args),
        "cli-smoke": lambda: harness.operation_smoke(args),
        "cli-reset": lambda: harness.operation_reset_data(args),
        "promote-dry": lambda: harness.operation_promote(args),
        "rollback-dry": lambda: harness.operation_rollback(args),
        "build": lambda: adapter.build(target),
        "rehydrate": lambda: adapter.rehydrate(target),
        "retention": lambda: adapter._apply_retention(previous, target),
        "prune": lambda: adapter.estimate_or_apply_prune(dry_run=False),
        "schema-cleanup": lambda: adapter._cleanup_schema_snapshots(),
        "startup": lambda: adapter._start_backend(target, {}),
        "smoke": lambda: adapter.smoke(target),
        "startup-guard": lambda: harness._schema_start_guard(root, NEW),
    }
    before = {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    with pytest.raises(harness.HarnessError, match="operation|rollback|controller"):
        actions[route]()
    assert before == {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    assert lock.stat().st_ino == inode


def test_same_active_target_still_enters_pending_recovery(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    harness, previous, target, protected, lock, inode = _pending_operation(root)
    harness._publish_active(root, target, "live")
    called = []
    def retry(self, manifest, **kwargs):
        called.append(manifest["source_sha"])
        raise harness.HarnessError("verified retry reached")
    monkeypatch.setattr(harness.GrafLocalAdapter, "promote", retry)
    with pytest.raises(harness.HarnessError, match="verified retry reached"):
        harness.operation_promote(argparse.Namespace(manifest=root / "candidate.json", live=True,
                                                    dry_run=False, previous_checkout=None))
    assert called == [NEW]
    assert (root / "rollback-required.json").exists()
    assert (root / "transactions/previous-marker.app").exists()


def test_smoke_rejects_operation_appearing_during_probes(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    harness, previous, target, protected, lock, inode = _pending_operation(root)
    marker = root / "rollback-required.json"
    receipt = marker.read_bytes()
    marker.unlink()
    adapter = harness.GrafLocalAdapter(root, root)
    adapter._assert_supported = lambda: None
    def probe(*args, **kwargs):
        marker.write_bytes(receipt)
        return 200
    adapter._wait_http = probe
    adapter._env = lambda *args: {}
    adapter._compose_service_ready = lambda *args: "pass"
    adapter._tcp_ready = lambda *args: "pass"
    monkeypatch.setattr(harness, "_run_command", lambda *args, **kwargs: "")
    with pytest.raises(harness.HarnessError, match="unfinished Dev operation"):
        adapter.smoke(previous)
    assert marker.read_bytes() == receipt
    assert protected.read_bytes() == b"synthetic protected bytes"
    assert lock.stat().st_ino == inode


@pytest.mark.parametrize("boundary", ["before-record", "after-record", "after-permit", "record-failure"])
def test_ordinary_startup_gate_registers_before_execution(tmp_path, boundary):
    root = tmp_path.resolve()
    harness, previous, target, protected, lock, inode = _pending_operation(root)
    script = root / "startup.sh"
    script.write_text('cd "$(dirname "$0")"\ntouch startup-executed\n'
                      'while [ ! -f startup-release ]; do sleep .02; done\n')
    process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--startup-worker", str(root), boundary],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    adapter = harness.GrafLocalAdapter(root, root)
    try:
        if boundary != "record-failure":
            _wait_marker(root / "ready")
            if boundary == "after-permit":
                _wait_marker(root / "startup-executed")
                assert adapter._pid_owned(harness._read_json(root / "runtime.json"))
            else:
                assert not (root / "startup-executed").exists()
                record = harness._read_json(root / "runtime.json")
                assert (record["source_sha"] == target["source_sha"]) == (boundary == "after-record")
            process.kill()
        out, err = process.communicate(timeout=5)
        assert process.returncode != 0, (out, err)
        pid = int((root / "startup-pid").read_text())
        if boundary == "after-permit":
            assert adapter._pid_alive(pid)
            assert not _lock_busy(lock), "long-lived backend inherited operation lock"
            adapter._stop_previous()  # Actual ownership check and SIGTERM, no Docker.
        deadline = time.monotonic() + 5
        while adapter._pid_alive(pid):
            assert time.monotonic() < deadline, "startup pipe did not close on controller death"
            time.sleep(0.01)
        assert (root / "startup-executed").exists() == (boundary == "after-permit")
        assert harness.operation_status(argparse.Namespace())["status"] == "rollback_required"
        assert protected.read_bytes() == b"synthetic protected bytes"
        assert lock.stat().st_ino == inode
        retry = _start_crash_worker(root, "none", "promote")
        out, err = retry.communicate(timeout=10)
        assert retry.returncode == 0, (out, err)
        assert harness._load_active(root)["source_sha"] == target["source_sha"]
    finally:
        (root / "startup-release").touch()
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
        if (root / "startup-pid").exists():
            pid = int((root / "startup-pid").read_text())
            if adapter._pid_alive(pid):
                os.kill(pid, signal.SIGTERM)


# Reachable master history with the exact inspected frozen harness/startup bytes.
FROZEN_RUNTIME = "66bc074c5b39fc2ef7955a28a920785e0775f24f"


def _stopped_git(checkout, *args):
    result = subprocess.run(["git", *args], cwd=checkout, text=True,
                            capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _load_stopped_module(checkout):
    spec = importlib.util.spec_from_file_location("stopped_candidate", checkout / "scripts/dev-harness.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def stopped_case(tmp_path, monkeypatch):
    import urllib.request  # Import platform helpers before modelling macOS on Linux.

    scratch = tmp_path.resolve()
    # GNU ps otherwise truncates command identity under pytest's captured output.
    monkeypatch.setenv("COLUMNS", "4096")
    # Model macOS consistently in the controller and its unchanged Python guards.
    python_site = scratch / "test-python"
    python_site.mkdir()
    (python_site / "sitecustomize.py").write_text('import urllib.request, sys\nsys.platform = "darwin"\n')
    monkeypatch.setenv("PYTHONPATH", str(python_site))
    monkeypatch.setattr(sys, "platform", "darwin")
    checkouts = {}
    inputs = ("scripts/dev-harness.py", "infra/docker-compose.dev.yml",
              "infra/scripts/start-dev-runtime.sh", "apps/macos/Scripts/install-dev-app.sh",
              "apps/macos/Scripts/dev-app-lifecycle.swift", "apps/macos/Scripts/build-dev-app.sh",
              "infra/scripts/dev-migration-preflight.py")
    for role, sha in (("controller", "609633cd0e43b26adc0def3dfa6c478939f41c09"),
                      ("runtime", FROZEN_RUNTIME)):
        _stopped_git(ROOT, "merge-base", "--is-ancestor", sha, "HEAD")
        checkout = scratch / role / "crisp"
        checkout.parent.mkdir()
        _stopped_git(ROOT, "clone", "--shared", "--no-checkout", "--quiet", str(ROOT), str(checkout))
        _stopped_git(checkout, "remote", "set-url", "origin", "git@github.com:yshishenya/graf.git")
        _stopped_git(checkout, "sparse-checkout", "set", "--no-cone", *("/" + p for p in inputs))
        _stopped_git(checkout, "checkout", "--quiet", "--detach", sha)
        if role == "controller":
            (checkout / "scripts/dev-harness.py").write_bytes((ROOT / "scripts/dev-harness.py").read_bytes())
            _stopped_git(checkout, "add", "scripts/dev-harness.py")
            # A disposable fixture commit lets the real guards verify this candidate.
            _stopped_git(checkout, "-c", "user.name=GRAF fixture", "-c", "user.email=fixture@graf.test",
                         "commit", "--allow-empty", "--quiet", "-m", "isolated controller candidate")
        checkouts[role] = checkout
    monkeypatch.setenv("HOME", str(scratch / "home"))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.delenv("GRAF_DEV_STATE_DIR", raising=False)
    module = _load_stopped_module(checkouts["controller"])
    module._stopped_test_workers = []
    state = module._machine_state_base() / "crisp/harness"
    state.mkdir(parents=True, mode=0o700)
    module._write_json(module._machine_state_base() / "repository-state.json", {
        "schema_version": "graf-dev-repository-state.v1", "repository": "github.com/yshishenya/graf",
        "state_root": str(state), "adopted_active_sha": FROZEN_RUNTIME, "adopted_at": "2026-10-29T00:00:00Z"})
    manifest = module.build_manifest(FROZEN_RUNTIME, "224", "synthetic", "synthetic-head", state)
    manifest["status"] = "active"
    module._publish_active(state, manifest, "live")
    adapter = module.GrafLocalAdapter(checkouts["controller"], state)
    frozen = adapter._checkout_adapter(checkouts["runtime"], manifest)
    module._write_json(state / "runtime.json", dict(_runtime_marker(FROZEN_RUNTIME),
                       runtime_definition_digest=frozen._runtime_definition_digest()))
    (state / "promote.lock").touch()
    (state / "protected-data").write_bytes(b"synthetic protected bytes")
    try:
        yield module, checkouts, state, manifest
    finally:
        for worker in module._stopped_test_workers:
            if worker.poll() is None:
                worker.kill()
            worker.communicate(timeout=5)
        record = module._read_json(state / "runtime.json") if (state / "runtime.json").exists() else None
        adapter = module.GrafLocalAdapter(checkouts["runtime"], state)
        if record and adapter._pid_alive(record.get("pid", -1)) and adapter._pid_owned(record):
            adapter._stop_previous()
        # No dependencies/history copied; discard owned sparse clones and state.
        module.shutil.rmtree(scratch)


def _stopped_worker(controller, runtime, state, boundary):
    module = _load_stopped_module(controller)
    cls = module.GrafLocalAdapter
    destination = state / "installed-marker"
    module._dev_app_destination = lambda: destination
    module._installed_app_state = lambda: {"installed": destination.exists()}
    cls._app_is_running = lambda self, path: boundary == "live-app"
    cls._checked_app_bundle = lambda self, manifest: state
    cls._validate_launch_bundle = lambda self, manifest, path: None
    cls._compose_config = lambda self, env: None
    cls._assert_manifest_images = lambda self, manifest, env: None
    cls._ensure_rollback_archive = lambda self, manifest: None
    cls._apply_retention = lambda self, *args, **kwargs: None
    cls._terminate_dev_app = lambda self, path: None
    cls._launch_dev_app = lambda self, path: None

    def snapshot(self):
        _crash_handshake(state, "before-receipt", boundary)
        if not destination.exists():
            return None
        backup = state / "transactions/previous-stopped.app"
        backup.mkdir(parents=True)
        (backup / "version").write_bytes(destination.read_bytes())
        return backup
    cls._snapshot_app = snapshot

    def install(self, manifest, env):
        destination.write_text(manifest["source_sha"])
        _crash_handshake(state, "after-install", boundary)
    cls._install_app = install

    def restore(self, backup):
        _crash_handshake(state, "before-restore", boundary)
        if backup is None:
            destination.unlink(missing_ok=True)
        else:
            destination.write_bytes((backup / "version").read_bytes())
        _crash_handshake(state, "after-restore", boundary)
    cls._restore_app = restore
    restore_runtime = cls._restore_runtime

    def restoring_runtime(self, *args):
        _crash_handshake(state, "before-restore-runtime", boundary)
        restore_runtime(self, *args)
        _crash_handshake(state, "after-restore-runtime", boundary)
    cls._restore_runtime = restoring_runtime
    cleanup = cls._cleanup_ordinary

    def cleaning(self, *args):
        _crash_handshake(state, "before-cleanup", boundary)
        cleanup(self, *args)
        _crash_handshake(state, "after-cleanup", boundary)
    cls._cleanup_ordinary = cleaning

    def smoke(self, manifest):
        _crash_handshake(state, "after-start", boundary)
        if boundary == "smoke-failure" or boundary in {"before-restore", "after-restore", "before-restore-runtime", "after-restore-runtime"}:
            raise module.HarnessError("injected smoke failure")
        return {key: "pass" for key in ("backend_health", "frontend_reachability",
            "auth_session_bootstrap", "representative_api", "processing_worker_readiness",
            "media_worker_readiness", "database_readiness", "storage_readiness", "temporal_readiness",
            "migration_readiness", "exact_source_sha", "app_identity", "app_presentation")}
    cls.smoke = smoke
    # Pinned shell, frozen guard and preflight run unchanged. External Docker
    # and Alembic are markers; this is not database or installed-app acceptance.
    os.environ["GRAF_DEV_STATE_ROOT"] = str(state)
    binaries = state.parent / "test-bin"
    binaries.mkdir(exist_ok=True)
    docker = binaries / "docker"
    docker.write_text(f"#!{sys.executable}\n" + r'''
import os,pathlib,subprocess,sys
state=pathlib.Path(os.environ['GRAF_DEV_STATE_ROOT'])
args=sys.argv[1:]
with (pathlib.Path(sys.argv[0]).parent/'docker-calls').open('a') as out: out.write(' '.join(args)+'\n')
if args[0]=='ps':
    if os.environ.get('GRAF_TEST_ORPHAN'): print('orphan')
    sys.exit(0)
if '/app/scripts/dev-migration-preflight.py' in args:
    sys.exit(subprocess.call([sys.executable, str(pathlib.Path.cwd()/'infra/scripts/dev-migration-preflight.py'), '--server-root', str(state), '--json']))
if 'api' in args and 'up' in args: (state/'writers-started').touch()
if '--services' in args: print('api')
''')
    docker.chmod(0o700)
    alembic = binaries / "alembic"
    revision = "unknown-revision" if boundary == "unknown-revision" else "synthetic-head"
    alembic.write_text("#!/bin/sh\nprintf '%s\\n' " + revision + "\n")
    alembic.chmod(0o700)
    os.environ["PATH"] = str(binaries) + os.pathsep + os.path.dirname(sys.executable) + os.pathsep + os.defpath
    if boundary == "orphan":
        os.environ["GRAF_TEST_ORPHAN"] = "1"

    def wait_ready(self, *args):
        _crash_handshake(state, "after-permit", boundary)
        _wait_marker(state / "writers-started")
    cls._wait_runtime_ready = wait_ready
    write = module._write_json

    def writing(path, value):
        write(path, value)
        if path.name == "rollback-required.json":
            with (binaries / "receipt-history.jsonl").open("a") as history:
                history.write(json.dumps(value["operation"]) + "\n")
            _crash_handshake(state, "after-receipt", boundary)
        if path.name == "runtime.json":
            if boundary == "runtime-tamper":
                write(path, dict(value, start_token="foreign"))
            elif boundary == "receipt-tamper":
                receipt = module._read_json(state / "rollback-required.json")
                receipt["operation"]["checkouts"]["controller"]["digest"] = "sha256:" + "0" * 64
                write(state / "rollback-required.json", receipt)
            elif boundary in {"controller-drift", "runtime-drift"}:
                checkout = controller if boundary == "controller-drift" else runtime
                with (checkout / "infra/docker-compose.dev.yml").open("a") as file:
                    file.write("\n# drift before startup admission\n")
            _crash_handshake(state, "after-runtime", boundary)
    module._write_json = writing
    publish = module._publish_active

    def publishing(*args):
        publish(*args)
        _crash_handshake(state, "after-pointer", boundary)
    module._publish_active = publishing
    unlink = Path.unlink

    def unlinking(path, *args, **kwargs):
        if path == state / "rollback-required.json":
            _crash_handshake(state, "before-unlink", boundary)
        result = unlink(path, *args, **kwargs)
        if path == state / "rollback-required.json":
            _crash_handshake(state, "after-unlink", boundary)
        return result
    Path.unlink = unlinking
    sys.exit(module.main(["promote", "--live", "--manifest", str(state / "manifests" / ("dev-" + FROZEN_RUNTIME[:12] + ".json")),
                          "--previous-checkout", str(runtime)]))


def _start_stopped_worker(case, boundary="none"):
    module, checkouts, state, _manifest = case
    worker = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--stopped-worker",
                             str(checkouts["controller"]), str(checkouts["runtime"]), str(state), boundary],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    module._stopped_test_workers.append(worker)
    return worker


@pytest.mark.parametrize("fault", [
    "controller-origin", "runtime-origin", "controller-dirty", "runtime-dirty",
    "controller-hidden", "runtime-hidden", "runtime-sha", "runtime-resolver",
    "runtime-digest", "runtime-source", "runtime-missing", "runtime-token",
    "runtime-command", "runtime-pid-zero", "runtime-pid-negative",
    "active-missing", "active-mode", "unsupported-startup",
    "schema-malformed", "schema-unfinished",
])
def test_stopped_source_and_state_guards_refuse_before_effects(stopped_case, fault):
    module, checkouts, state, manifest = stopped_case
    if fault.endswith("-origin"):
        _stopped_git(checkouts[fault.split("-")[0]], "remote", "set-url", "origin", "git@github.com:other/repo.git")
    elif fault.endswith(("-dirty", "-hidden")):
        checkout = checkouts[fault.split("-")[0]]
        if fault.endswith("-hidden"):
            _stopped_git(checkout, "update-index", "--assume-unchanged", "infra/docker-compose.dev.yml")
        with (checkout / "infra/docker-compose.dev.yml").open("a") as file:
            file.write("\n# changed tracked bytes\n")
    elif fault == "runtime-sha":
        _stopped_git(checkouts["runtime"], "checkout", "--quiet", "--detach", "609633cd0e43b26adc0def3dfa6c478939f41c09")
    elif fault == "runtime-resolver":
        destination = checkouts["runtime"].with_name("renamed")
        checkouts["runtime"].rename(destination)
        checkouts["runtime"] = destination
    elif fault == "runtime-missing":
        (state / "runtime.json").unlink()
    elif fault.startswith("runtime-"):
        record = module._read_json(state / "runtime.json")
        key = {"runtime-digest": "runtime_definition_digest", "runtime-source": "source_sha",
               "runtime-token": "start_token", "runtime-command": "command",
               "runtime-pid-zero": "pid", "runtime-pid-negative": "pid"}[fault]
        record[key] = {"runtime-digest": "sha256:" + "0" * 64,
                       "runtime-pid-zero": 0, "runtime-pid-negative": -1}.get(fault, "")
        module._write_json(state / "runtime.json", record)
    elif fault == "active-missing":
        (state / "active-manifest.json").unlink()
    elif fault == "active-mode":
        pointer = module._read_json(state / "active-manifest.json")
        module._write_json(state / "active-manifest.json", dict(pointer, runtime_mode="metadata-only"))
    elif fault == "unsupported-startup":
        sha = "609633cd0e43b26adc0def3dfa6c478939f41c09"
        _stopped_git(checkouts["runtime"], "checkout", "--quiet", "--detach", sha)
        candidate = dict(module.build_manifest(sha, "224", "synthetic", "synthetic-head", state), status="active")
        module._publish_active(state, candidate, "live")
        module._write_json(state / "manifests" / (manifest["manifest_id"] + ".json"), candidate)
        adapter = module.GrafLocalAdapter(checkouts["runtime"], state)
        module._write_json(state / "runtime.json", dict(_runtime_marker(sha),
                           runtime_definition_digest=adapter._runtime_definition_digest()))
    else:
        journal = {} if fault == "schema-malformed" else {
            "schema_version": "dev-schema-transition.v1", "phase": "prepared", "operation_id": "upgrade-1",
            "previous": manifest, "target": manifest,
            "volumes": {"graf-dev-postgres-data": {}, "graf-dev-minio-data": {}},
        }
        module._write_json(state / "schema-transition.json", journal)
        if fault == "schema-unfinished":
            assert module._read_schema_transition(state)["phase"] == "prepared"
    before = {str(path.relative_to(state)): path.read_bytes() for path in state.rglob("*") if path.is_file()}
    inode = (state / "promote.lock").stat().st_ino
    worker = _start_stopped_worker(stopped_case)
    out, err = worker.communicate(timeout=60)
    assert worker.returncode != 0, (fault, out, err)
    expected = {
        "controller-origin": "Dev state belongs to another repository",
        "runtime-origin": "transition checkout must belong to this Git repository",
        "controller-dirty": "live adapter requires a clean checkout",
        "runtime-dirty": "live adapter requires a clean checkout",
        "controller-hidden": "transition input differs from committed bytes",
        "runtime-hidden": "transition input differs from committed bytes",
        "runtime-sha": "candidate source_sha to equal the checked-out HEAD",
        "runtime-resolver": "pinned checkout resolver does not match the adopted Dev state",
        "runtime-digest": "active Dev runtime definition differs from checkout",
        "runtime-source": "ordinary transition runtime identity is unknown",
        "runtime-missing": "same-active recovery requires stopped runtime, app and Dev containers",
        "runtime-token": "ordinary transition runtime identity is unknown",
        "runtime-command": "ordinary transition runtime identity is unknown",
        "runtime-pid-zero": "ordinary transition runtime identity is unknown",
        "runtime-pid-negative": "ordinary transition runtime identity is unknown",
        "active-missing": "candidate source_sha to equal the checked-out HEAD",
        "active-mode": "different controller source requires a stopped same-active promotion",
        "unsupported-startup": "unsupported stopped-runtime startup",
        "schema-malformed": "invalid schema transition journal",
        "schema-unfinished": "unfinished schema transition",
    }[fault]
    assert expected in err, (fault, err)
    assert before == {str(path.relative_to(state)): path.read_bytes() for path in state.rglob("*") if path.is_file()}
    assert (state / "promote.lock").stat().st_ino == inode
    assert not (state / "transactions").exists()
    assert not (state / "writers-started").exists()


@pytest.mark.parametrize("fault", [
    "missing-field", "null", "boolean", "short-sha", "same-sha", "rollback",
    "no-previous", "live-runtime", "live-app", "no-runtime", "invalid-pid",
    "controller-pin", "different-runtime-pin", "runtime-record-digest", "extra-field",
])
def test_stopped_optional_receipt_rejects_invalid_forms(tmp_path, fault):
    root = tmp_path.resolve()
    module, _previous, target, protected, lock, inode = _pending_operation(root)
    adapter = module.GrafLocalAdapter(root, root)
    operation = module._read_ordinary_operation(root)
    operation.update(previous=target, controller_manifest=target, previous_runtime=_runtime_marker(NEW),
                     previous_was_live=False, app_was_running=False, backup=None, backup_digest=None,
                     controller_source_sha=OLD)
    operation["checkouts"]["controller"]["source_sha"] = OLD
    operation["checkouts"]["previous"] = dict(operation["checkouts"]["target"])
    adapter._write_ordinary_receipt(operation)
    assert module._read_ordinary_operation(root) == operation
    if fault == "missing-field":
        operation.pop("controller_source_sha")
    elif fault in {"null", "boolean", "short-sha", "same-sha"}:
        operation["controller_source_sha"] = {"null": None, "boolean": True, "short-sha": OLD[:8], "same-sha": NEW}[fault]
    elif fault == "rollback":
        operation["kind"] = "rollback"
    elif fault == "no-previous":
        operation["previous"] = None
    elif fault in {"live-runtime", "live-app"}:
        operation["previous_was_live" if fault == "live-runtime" else "app_was_running"] = True
    elif fault == "no-runtime":
        operation["previous_runtime"] = None
    elif fault == "invalid-pid":
        operation["previous_runtime"]["pid"] = 0
    elif fault == "controller-pin":
        operation["checkouts"]["controller"]["source_sha"] = NEW
    elif fault == "different-runtime-pin":
        operation["checkouts"]["previous"]["digest"] = "sha256:" + "0" * 64
    elif fault == "runtime-record-digest":
        operation["previous_runtime"]["runtime_definition_digest"] = "sha256:" + "0" * 64
    else:
        operation["unexpected"] = True
    adapter._write_ordinary_receipt(operation)
    receipt = (root / "rollback-required.json").read_bytes()
    with pytest.raises(module.HarnessError):
        module._read_ordinary_operation(root)
    assert (root / "rollback-required.json").read_bytes() == receipt
    assert protected.read_bytes() == b"synthetic protected bytes"
    assert lock.stat().st_ino == inode


@pytest.mark.parametrize(("installed", "schema_phase"), [(False, None), (True, None), (False, "complete"), (False, "recovered")])
def test_stopped_same_active_cli_uses_current_controller_and_pinned_startup(stopped_case, installed, schema_phase):
    module, checkouts, state, manifest = stopped_case
    if installed:
        (state / "installed-marker").write_text(FROZEN_RUNTIME)
    if schema_phase:
        module._write_json(state / "schema-transition.json", {
            "schema_version": "dev-schema-transition.v1", "phase": schema_phase, "operation_id": "upgrade-1",
            "previous": manifest, "target": manifest,
            "volumes": {"graf-dev-postgres-data": {}, "graf-dev-minio-data": {}},
        })
        assert module._read_schema_transition(state)["phase"] == schema_phase
    worker = _start_stopped_worker(stopped_case)
    try:
        out, err = worker.communicate(timeout=60)
        assert worker.returncode == 0, (out, err)
        assert module._same_pinned_manifest(module._load_active(state), manifest)
        record = module._read_json(state / "runtime.json")
        assert record["source_sha"] == FROZEN_RUNTIME
        assert record["runtime_definition_digest"] == module.GrafLocalAdapter(checkouts["runtime"], state)._runtime_definition_digest()
        assert (state / "writers-started").exists()
        assert not (state / "rollback-required.json").exists()
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.communicate(timeout=5)
        module.GrafLocalAdapter(checkouts["runtime"], state)._stop_previous()


@pytest.mark.parametrize("boundary", ["before-receipt", "after-receipt", "after-install",
                                     "after-runtime", "after-permit", "after-start",
                                     "after-pointer", "before-unlink", "after-unlink",
                                     "before-cleanup", "after-cleanup", "before-restore", "after-restore",
                                     "before-restore-runtime", "after-restore-runtime"])
def test_stopped_same_active_sigkill_and_exact_retry(stopped_case, boundary):
    module, checkouts, state, manifest = stopped_case
    if boundary.endswith("cleanup"):
        (state / "installed-marker").write_text(FROZEN_RUNTIME)
    lock_inode = (state / "promote.lock").stat().st_ino
    worker = _start_stopped_worker(stopped_case, boundary)
    try:
        deadline = time.monotonic() + 60
        while not (state / "ready").exists():
            if worker.poll() is not None:
                pytest.fail(str(worker.communicate()))
            assert time.monotonic() < deadline, boundary
            time.sleep(0.02)
        worker.kill()
        worker.communicate(timeout=5)
        assert worker.returncode == -signal.SIGKILL
        before = module._read_ordinary_operation(state)
        status = module.operation_status(argparse.Namespace())
        assert status["status"] == ("active" if boundary in {"before-receipt", "after-unlink", "before-cleanup", "after-cleanup"} else "rollback_required")
        if boundary.endswith("cleanup"):
            assert (state / "transactions/previous-stopped.app").exists() == (boundary == "before-cleanup")
        (state / "ready").unlink()
        retry = _start_stopped_worker(stopped_case)
        out, err = retry.communicate(timeout=60)
        assert retry.returncode == 0, (out, err)
        assert not (state / "rollback-required.json").exists()
        assert module._same_pinned_manifest(module._load_active(state), manifest)
        assert (state / "protected-data").read_bytes() == b"synthetic protected bytes"
        assert (state / "promote.lock").stat().st_ino == lock_inode
        if before is not None:
            assert before["checkouts"]["target"] == before["checkouts"]["previous"]
            assert before["controller_source_sha"] == _stopped_git(checkouts["controller"], "rev-parse", "HEAD")
            history = [json.loads(line) for line in (state.parent / "test-bin/receipt-history.jsonl").read_text().splitlines()]
            mutable = {"controller_pid", "controller_start"}
            assert {key: value for key, value in before.items() if key not in mutable} == {
                key: value for key, value in history[-1].items() if key not in mutable}
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.communicate(timeout=5)


@pytest.mark.parametrize("failure", ["orphan", "live-app", "runtime-tamper", "receipt-tamper", "smoke-failure", "unknown-revision", "controller-drift", "runtime-drift"])
def test_stopped_same_active_failure_preserves_data(stopped_case, failure):
    module, _checkouts, state, manifest = stopped_case
    original_runtime = (state / "runtime.json").read_bytes()
    inode = (state / "promote.lock").stat().st_ino
    source_inputs = {role: (checkout / "infra/docker-compose.dev.yml").read_bytes() for role, checkout in _checkouts.items()}
    worker = _start_stopped_worker(stopped_case, failure)
    out, err = worker.communicate(timeout=60)
    assert worker.returncode != 0, (out, err)
    assert (state / "protected-data").read_bytes() == b"synthetic protected bytes"
    assert (state / "promote.lock").stat().st_ino == inode
    if failure in {"orphan", "live-app"}:
        assert not (state / "transactions").exists()
    if failure in {"runtime-tamper", "receipt-tamper", "unknown-revision", "controller-drift", "runtime-drift"}:
        assert not (state / "writers-started").exists()
    if failure in {"controller-drift", "runtime-drift"}:
        assert (state / "rollback-required.json").exists(), err
        for role, source in source_inputs.items():
            (_checkouts[role] / "infra/docker-compose.dev.yml").write_bytes(source)
    if failure in {"runtime-tamper", "controller-drift", "runtime-drift"} and (state / "rollback-required.json").exists():
        record = module._read_json(state / "runtime.json")
        adapter = module.GrafLocalAdapter(_checkouts["runtime"], state)
        deadline = time.monotonic() + 5
        while adapter._pid_alive(record["pid"]):
            assert time.monotonic() < deadline, "denied startup child did not exit on pipe EOF"
            time.sleep(0.01)
        retry = _start_stopped_worker(stopped_case)
        out, err = retry.communicate(timeout=60)
        assert retry.returncode == 0, (out, err)
        assert not (state / "rollback-required.json").exists()
        assert module._same_pinned_manifest(module._load_active(state), manifest)
    elif failure != "receipt-tamper":
        assert not (state / "rollback-required.json").exists(), err
        assert (state / "runtime.json").read_bytes() == original_runtime
        assert not (state / "installed-marker").exists()
        if failure not in {"orphan", "live-app"}:
            assert module._load_active(state)["health"]["result"] == "unknown"


if __name__ == "__main__":
    if len(sys.argv) == 6 and sys.argv[1] == "--stopped-worker":
        _stopped_worker(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5])
    elif len(sys.argv) == 4 and sys.argv[1] == "--lock-worker":
        _lock_worker(Path(sys.argv[2]), sys.argv[3])
    elif len(sys.argv) == 4 and sys.argv[1] == "--startup-worker":
        _startup_worker(Path(sys.argv[2]), sys.argv[3])
    else:
        assert len(sys.argv) == 5 and sys.argv[1] == "--crash-worker"
        _crash_worker(Path(sys.argv[2]), sys.argv[3], sys.argv[4])
