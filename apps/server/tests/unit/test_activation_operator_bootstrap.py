"""Real Git/flock/archive boundaries; installation is replaced only in unit tests."""

import fcntl
import importlib.util
import io
import json
import os
import signal
import subprocess
import sys
import tarfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[4] / "infra/scripts/activation-operator.py"


@pytest.fixture
def bootstrap():
    spec = importlib.util.spec_from_file_location("activation_bootstrap", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def repository(tmp_path, bootstrap):
    root = tmp_path / "repository"
    root.mkdir(mode=0o700)
    for argv in (["init", "-q"], ["config", "user.name", "Synthetic"],
                 ["config", "user.email", "synthetic@example.invalid"]):
        subprocess.run(["git", "-C", str(root), *argv], check=True, capture_output=True)
    (root / "example").write_text("committed bytes")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "synthetic"], check=True)
    lock = root / ".git/twobrain-rec-deploy.lock"
    lock.write_bytes(b"existing shell lock")
    lock.chmod(0o600)
    return root, lock


def test_existing_flock_shared_with_shell_and_inode_preserved(bootstrap, repository):
    root, lock = repository
    before = lock.stat()
    with bootstrap._deployment_lock(root) as descriptor:
        assert os.fstat(descriptor).st_ino == before.st_ino
        code = "import fcntl,sys; f=open(sys.argv[1],'r'); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)"
        child = subprocess.run([sys.executable, "-c", code, str(lock)], capture_output=True)
        assert child.returncode != 0 and b"BlockingIOError" in child.stderr
    assert lock.read_bytes() == b"existing shell lock"
    assert lock.stat().st_ino == before.st_ino
    with lock.open() as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)


@pytest.mark.parametrize("case", ["missing", "symlink", "hardlink", "world_write", "busy", "replaced", "root_symlink"])
def test_lock_refusals(bootstrap, repository, case):
    root, lock = repository
    with lock.open() as competing:
        if case == "missing":
            lock.unlink()
        elif case == "symlink":
            lock.rename(lock.with_suffix(".original"))
            lock.symlink_to(lock.with_suffix(".original"))
        elif case == "hardlink":
            os.link(lock, lock.with_suffix(".other"))
        elif case == "world_write":
            lock.chmod(0o666)
        elif case == "busy":
            fcntl.flock(competing, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(bootstrap.BootstrapHold), bootstrap._deployment_lock(root):
            if case == "replaced":
                lock.rename(lock.with_suffix(".old"))
                lock.write_bytes(b"replacement")
            elif case == "root_symlink":
                retired = root.with_name("retired")
                root.rename(retired)
                root.symlink_to(retired)
        if case == "missing":
            assert not lock.exists()


def test_linked_worktree_cannot_use_its_different_lock(bootstrap, repository, tmp_path):
    root, _ = repository
    linked = tmp_path / "linked"
    subprocess.run(["git", "-C", str(root), "worktree", "add", "--detach", str(linked)],
                   check=True, capture_output=True)
    with pytest.raises(bootstrap.BootstrapHold), bootstrap._deployment_lock(linked):
        pytest.fail("linked worktree entered")


def test_archive_uses_commit_despite_checkout_change(bootstrap, repository, tmp_path):
    root, _ = repository
    source = bootstrap._git(root, "rev-parse", "HEAD").decode().strip()
    (root / "example").write_text("moving checkout")
    destination = tmp_path / "snapshot"
    destination.mkdir(mode=0o700)
    bootstrap._snapshot(root, source, destination)
    assert (destination / "example").read_text() == "committed bytes"


@pytest.mark.parametrize("kind", ["traversal", "symlink", "duplicate"])
def test_archive_rejects_unsafe_members(bootstrap, tmp_path, monkeypatch, kind):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as archive:
        member = tarfile.TarInfo("../escape" if kind == "traversal" else "name")
        if kind == "symlink":
            member.type, member.linkname = tarfile.SYMTYPE, "/outside"
        archive.addfile(member)
        if kind == "duplicate":
            archive.addfile(member)
    monkeypatch.setattr(bootstrap, "_git", lambda *a: raw.getvalue())
    with pytest.raises(bootstrap.BootstrapHold):
        bootstrap._snapshot(tmp_path, "a" * 40, tmp_path)
    assert not (tmp_path.parent / "escape").exists()


def test_environment_does_not_choose_source_or_interpreter(bootstrap, monkeypatch):
    for name in ("PYTHONPATH", "GIT_DIR", "GIT_CONFIG_COUNT", "UV_PROJECT_ENVIRONMENT",
                 "VIRTUAL_ENV", "CONDA_PREFIX", "PATH", "HOME"):
        monkeypatch.setenv(name, "/synthetic-poison")
    env = bootstrap._environment()
    assert not any(name in env for name in ("PYTHONPATH", "GIT_DIR", "VIRTUAL_ENV", "CONDA_PREFIX"))
    assert "/synthetic-poison" not in env.values()
    assert env["PATH"] == "/usr/bin:/bin"


def test_unisolated_entry_refuses_before_installation(bootstrap, monkeypatch, capsys):
    monkeypatch.setattr(bootstrap.sys, "flags", type("Flags", (), {"isolated": 0})())
    monkeypatch.setattr(bootstrap, "_installation", lambda: pytest.fail("installation accessed"))
    assert bootstrap.main(["--preflight"]) == 1
    assert json.loads(capsys.readouterr().out)["reason"] == "bootstrap_isolated_python_required"


def test_child_timeout_reaps_group_before_lock_release(bootstrap, repository, tmp_path):
    root, _ = repository
    pidfile = tmp_path / "pid"
    code = "import os,sys,time; open(sys.argv[1],'w').write(str(os.getpid())); time.sleep(10)"
    with bootstrap._deployment_lock(root):
        with pytest.raises(bootstrap.BootstrapHold, match="bootstrap_child_timeout"):
            bootstrap._run([sys.executable, "-c", code, str(pidfile)],
                           deadline=time.monotonic() + .3)
        with pytest.raises(ProcessLookupError):
            os.kill(int(pidfile.read_text()), 0)


def test_package_manifest_rejects_missing_extra_and_same_size_change(bootstrap, tmp_path):
    source, installed = tmp_path / "source", tmp_path / "installed"
    source.mkdir()
    installed.mkdir()
    (source / "__init__.py").write_bytes(b"abcd")
    (installed / "__init__.py").write_bytes(b"abcd")
    assert bootstrap._package_manifest(source, installed)["package_file_count"] == 1
    (installed / "__init__.py").write_bytes(b"abce")
    with pytest.raises(bootstrap.BootstrapHold):
        bootstrap._package_manifest(source, installed)
    (installed / "__init__.py").unlink()
    with pytest.raises(bootstrap.BootstrapHold):
        bootstrap._package_manifest(source, installed)
    (installed / "__init__.py").write_bytes(b"abcd")
    (installed / "extra.py").write_text("untracked")
    with pytest.raises(bootstrap.BootstrapHold):
        bootstrap._package_manifest(source, installed)


@pytest.mark.parametrize("case", ["good", "python312", "editable", "package_changed", "snapshot_changed", "install_failed"])
def test_pinned_installation_boundary(bootstrap, tmp_path, monkeypatch, case):
    temporary = tmp_path / "temporary"
    temporary.mkdir(mode=0o700)
    installed = temporary / "venv/lib/site-packages/twobrain_rec_server"

    def snapshot(_root, _source, directory):
        package = directory / bootstrap.PACKAGE
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("# pinned package\n")
        (directory / "apps/server/uv.lock").write_text("# pinned lock\n")

    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        if "sync" in argv:
            assert {"--frozen", "--no-editable", "--no-default-groups", "--no-python-downloads"} <= set(argv)
            assert kwargs["env"]["UV_PROJECT_ENVIRONMENT"] == str(temporary / "venv")
            if case == "install_failed":
                raise bootstrap.BootstrapHold("bootstrap_child_failed")
            installed.mkdir(parents=True)
            (installed / "__init__.py").write_text("# pinned package\n")
            if case == "package_changed":
                (installed / "__init__.py").write_text("# changed bytes\n")
            if case == "snapshot_changed":
                (temporary / "source/apps/server/uv.lock").write_text("# changed lock\n")
            return b""
        assert argv[1:4] == ["-I", "-B", "-c"]
        return json.dumps(dict(version=[3, 12] if case == "python312" else [3, 13],
                               prefix=str(temporary / "venv"),
                               package=str((temporary / "source" / bootstrap.PACKAGE if case == "editable"
                                            else installed) / "__init__.py"))).encode()

    monkeypatch.setattr(bootstrap, "_snapshot", snapshot)
    monkeypatch.setattr(bootstrap, "_run", run)
    monkeypatch.setattr(bootstrap, "_tool", str)
    monkeypatch.setattr(bootstrap.pwd, "getpwuid", lambda _uid: SimpleNamespace(pw_dir="/synthetic"))
    if case == "good":
        result = bootstrap._prepare(tmp_path, "a" * 40, temporary)
        assert result["source_sha"] == "a" * 40 and result["package_file_count"] == 1
        assert installed.stat().st_mode & 0o777 == 0o500
        assert (installed / "__init__.py").stat().st_mode & 0o777 == 0o400
    else:
        with pytest.raises(bootstrap.BootstrapHold):
            bootstrap._prepare(tmp_path, "a" * 40, temporary)
    for path in temporary.rglob("*"):
        if path.is_dir():
            path.chmod(0o700)
    assert calls


def test_group_trust_is_explicit_and_closed(bootstrap, tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap.sys, "platform", "linux")
    monkeypatch.setattr(bootstrap.os, "geteuid", lambda: 0)
    monkeypatch.setattr(bootstrap.grp, "getgrgid", lambda _gid: SimpleNamespace(gr_mem=["operator", "other"]))
    monkeypatch.setattr(bootstrap.pwd, "getpwall", lambda: [
        SimpleNamespace(pw_uid=1001, pw_gid=1002, pw_name="operator"),
        SimpleNamespace(pw_uid=1003, pw_gid=1002, pw_name="other"),
    ])
    with pytest.raises(bootstrap.BootstrapHold, match="bootstrap_installation_group_unconfirmed"):
        bootstrap._installation()


def test_signal_in_successful_reap_is_retained_between_children(bootstrap, monkeypatch):
    reap = bootstrap._reap

    def cancelled_reap(child, adopt):
        reap(child, adopt)
        os.kill(os.getpid(), signal.SIGTERM)

    monkeypatch.setattr(bootstrap, "_reap", cancelled_reap)
    with bootstrap._signals(), pytest.raises(bootstrap.BootstrapHold, match="bootstrap_interrupted"):
        try:
            bootstrap._run([sys.executable, "-c", "pass"])
        except bootstrap.BootstrapHold:
            monkeypatch.setattr(bootstrap, "_reap", reap)
            monkeypatch.setattr(bootstrap.subprocess, "Popen", lambda *a, **kw: pytest.fail("new child after cancellation"))
            bootstrap._run([sys.executable, "-c", "pass"])


@pytest.mark.parametrize("failure", ["unsettled", "restore_prctl"])
def test_cleanup_errors_restore_handlers_and_subreaper(bootstrap, monkeypatch, failure):
    original = {n: signal.getsignal(n) for n in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)}
    calls = []

    def prctl(operation, value, *_):
        if operation == 37:
            value._obj.value = 0
        calls.append((operation, value if operation == 36 else None))
        return -1 if operation == 36 and value == 0 and failure == "restore_prctl" else 0

    monkeypatch.setattr(bootstrap.sys, "platform", "linux")
    monkeypatch.setattr(bootstrap.ctypes, "CDLL", lambda *a, **kw: SimpleNamespace(prctl=prctl))
    reap = bootstrap._reap

    def fail_after_reap(child, adopt):
        reap(child, adopt)
        if failure == "unsettled":
            raise bootstrap.BootstrapHold("bootstrap_child_group_unsettled")

    monkeypatch.setattr(bootstrap, "_reap", fail_after_reap)
    with pytest.raises(bootstrap.BootstrapHold):
        bootstrap._run([sys.executable, "-c", "pass"])
    assert calls[-1] == (36, 0)
    assert all(signal.getsignal(n) == value for n, value in original.items())
    assert bootstrap._cancelled is None


def test_signal_during_temp_cleanup_holds_lock_and_cannot_verify(bootstrap, repository, monkeypatch, capsys):
    root, lock = repository
    script = root / "infra/scripts/activation-operator.py"
    script.parent.mkdir(parents=True)
    script.write_bytes(SCRIPT.read_bytes())
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "bootstrap"], check=True)
    monkeypatch.setattr(bootstrap.sys, "flags", SimpleNamespace(isolated=1))
    monkeypatch.setattr(bootstrap, "_installation", lambda: root)
    directories = []

    def prepare(_root, _source, temporary):
        directories.append(temporary)
        (temporary / "own").write_text("synthetic")
        return {"source_sha": _source}

    remove = bootstrap.shutil.rmtree

    def interrupted_cleanup(directory):
        os.kill(os.getpid(), signal.SIGTERM)
        with lock.open() as contender, pytest.raises(BlockingIOError):
            fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
        remove(directory)

    monkeypatch.setattr(bootstrap, "_prepare", prepare)
    monkeypatch.setattr(bootstrap.shutil, "rmtree", interrupted_cleanup)
    assert bootstrap.main(["--preflight"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["bootstrap"] == "unverified" and result["reason"] == "bootstrap_interrupted"
    assert directories and all(not p.exists() for p in directories)


@pytest.mark.skipif(sys.platform != "linux", reason="Linux subreaper boundary")
def test_linux_supervisor_reaps_descendants_and_repeated_signals(bootstrap, tmp_path):
    import ctypes

    libc, before = ctypes.CDLL(None), ctypes.c_int()
    assert libc.prctl(37, ctypes.byref(before), 0, 0, 0) == 0
    grandfile, pidfile, lock = tmp_path / "grand", tmp_path / "pid", tmp_path / "lock"
    lock.write_bytes(b"existing")
    with lock.open() as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        grand = ("import os,signal,time; from pathlib import Path; "
                 "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
                 f"Path({str(grandfile)!r}).write_text(str(os.getpid())); time.sleep(30)")
        leader = ("import subprocess,sys,time; from pathlib import Path; "
                  f"subprocess.Popen([sys.executable,'-c',{grand!r}],"
                  "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); deadline=time.monotonic()+3;\n"
                  f"while not Path({str(grandfile)!r}).exists() and time.monotonic()<deadline: time.sleep(.01)")
        bootstrap._run([sys.executable, "-c", leader])
        try:
            os.kill(int(grandfile.read_text()), 0)
        except ProcessLookupError:
            pass
        else:
            raise AssertionError("orphan survived")
        child = ("import os,signal,time; from pathlib import Path; "
                 "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
                 f"Path({str(pidfile)!r}).write_text(str(os.getpid())); time.sleep(30)")
        original = {n: signal.getsignal(n) for n in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)}

        def interrupt():
            deadline = time.monotonic() + 5
            while not pidfile.exists() and time.monotonic() < deadline:
                time.sleep(.01)
            if pidfile.exists():
                os.kill(os.getpid(), signal.SIGTERM)
                time.sleep(.05)
                os.kill(os.getpid(), signal.SIGTERM)

        sender = threading.Thread(target=interrupt)
        sender.start()
        try:
            try:
                bootstrap._run([sys.executable, "-c", child], deadline=time.monotonic() + 6)
            except bootstrap.BootstrapHold as error:
                assert str(error) == "bootstrap_interrupted"
            else:
                raise AssertionError("interruption passed")
        finally:
            sender.join()
        try:
            os.kill(int(pidfile.read_text()), 0)
        except ProcessLookupError:
            pass
        else:
            raise AssertionError("cancelled child survived")
        assert all(signal.getsignal(n) == value for n, value in original.items())
        contender = subprocess.run([sys.executable, "-c",
            "import fcntl,sys; f=open(sys.argv[1]); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)",
            str(lock)], capture_output=True)
        assert contender.returncode != 0 and b"BlockingIOError" in contender.stderr
    with lock.open() as released:
        fcntl.flock(released, fcntl.LOCK_EX | fcntl.LOCK_NB)
    after = ctypes.c_int()
    assert libc.prctl(37, ctypes.byref(after), 0, 0, 0) == 0 and before.value == after.value
