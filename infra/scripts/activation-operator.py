#!/usr/bin/python3 -I
"""Prepare pinned T113 operator dependencies; full admission remains closed."""

from __future__ import annotations

import argparse
import ctypes
import fcntl
import grp
import hashlib
import io
import json
import os
import pwd
import re
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

ROOT = Path("/opt/projects/2brain-rec")
GIT = "/usr/bin/git"
INSTALLATION_UID = 1001
INSTALLATION_GID = 1002
# UID1003 is currently a group member; owner confirmation is still pending.
# Fail closed before preparing a privileged working environment meanwhile.
TRUSTED_GROUP_UIDS = frozenset({1001})
PACKAGE = Path("apps/server/src/twobrain_rec_server")
_cancelled = None


class BootstrapHold(PermissionError):
    """Finite reason only; no child output, paths or secrets."""


def _require(value, reason):
    if not value:
        raise BootstrapHold(reason)


def _environment():
    return {"PATH": "/usr/bin:/bin", "HOME": "/root", "LANG": "C.UTF-8",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0", "UV_NO_CONFIG": "1",
            "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "safe.directory",
            "GIT_CONFIG_VALUE_0": str(ROOT),
            "DOCKER_HOST": "unix:///var/run/docker.sock"}


@contextmanager
def _signals():
    """One cancellation latch for this synchronous CLI, including temp cleanup."""
    global _cancelled
    if _cancelled is not None:
        yield _cancelled
        return
    pending = set()
    previous = {number: signal.signal(number, lambda number, _frame: pending.add(number))
                for number in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)}
    _cancelled = pending
    try:
        yield pending
    finally:
        _cancelled = None
        for number, handler in previous.items():
            signal.signal(number, handler)


def _run(argv, *, deadline=None, env=None):
    with _signals() as pending:
        return _owned_run(argv, pending, deadline=deadline, env=env)


def _owned_run(argv, pending, *, deadline=None, env=None):
    """Do not release a caller's lock or staging while our process group lives."""
    deadline = deadline if deadline is not None else time.monotonic() + 30
    child, subreaper = None, None
    if sys.platform == "linux":
        libc, subreaper = ctypes.CDLL(None, use_errno=True), ctypes.c_int()
        _require(libc.prctl(37, ctypes.byref(subreaper), 0, 0, 0) == 0
                 and libc.prctl(36, 1, 0, 0, 0) == 0, "bootstrap_supervisor_unavailable")
    try:
        _require(not pending, "bootstrap_interrupted")
        _require(time.monotonic() < deadline, "bootstrap_child_timeout")
        child = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 env=env or _environment(), start_new_session=True)
        while True:
            _require(not pending, "bootstrap_interrupted")
            remaining = deadline - time.monotonic()
            _require(remaining > 0, "bootstrap_child_timeout")
            try:
                output, _ = child.communicate(timeout=min(.2, remaining))
                break
            except subprocess.TimeoutExpired:
                continue
        _require(not pending, "bootstrap_interrupted")
        _require(child.returncode == 0, "bootstrap_child_failed")
        return output
    finally:
        try:
            _reap(child, subreaper is not None)
        finally:
            if subreaper is not None:
                _require(libc.prctl(36, subreaper.value, 0, 0, 0) == 0,
                         "bootstrap_supervisor_unavailable")
        _require(not pending, "bootstrap_interrupted")


def _reap(child, adopt):
    if child is not None:
        # The group may outlive its direct parent; terminate it in both cases.
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            child.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.communicate()
        if adopt:
            # Linux reparents orphaned grandchildren here, not to an unknown PID1.
            while True:
                try:
                    os.waitpid(-child.pid, 0)
                except ChildProcessError:
                    break
            try:
                os.killpg(child.pid, 0)
            except ProcessLookupError:
                pass
            else:
                raise BootstrapHold("bootstrap_child_group_unsettled")

def _git(root, *args):
    return _run([GIT, "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null",
                 "-c", f"safe.directory={root}", "-C", str(root), *args])


def _installation():
    _require(sys.platform == "linux" and os.geteuid() == 0, "bootstrap_linux_root_required")
    members = set(grp.getgrgid(INSTALLATION_GID).gr_mem)
    actual = {entry.pw_uid for entry in pwd.getpwall()
              if entry.pw_gid == INSTALLATION_GID or entry.pw_name in members}
    _require(actual == TRUSTED_GROUP_UIDS, "bootstrap_installation_group_unconfirmed")
    _require(ROOT.is_absolute() and ROOT.resolve(strict=True) == ROOT, "bootstrap_root_untrusted")
    for path in (ROOT, *ROOT.parents, ROOT / ".git", ROOT / ".git/config", ROOT / ".git/HEAD"):
        info = path.lstat()
        _require(not stat.S_ISLNK(info.st_mode) and info.st_uid in {0, INSTALLATION_UID}
                 and not info.st_mode & stat.S_IWOTH
                 and (not info.st_mode & stat.S_IWGRP or info.st_gid == INSTALLATION_GID),
                 "bootstrap_root_untrusted")
    _require((ROOT / ".git").is_dir(), "bootstrap_linked_worktree")
    return ROOT


def _root_identity(root):
    paths = (root, *root.parents, root / ".git", root / ".git/config", root / ".git/HEAD")
    infos = [path.lstat() for path in paths]
    _require(all(not stat.S_ISLNK(info.st_mode) for info in infos), "bootstrap_root_untrusted")
    group = set(grp.getgrgid(infos[0].st_gid).gr_mem)
    members = tuple(sorted(p.pw_uid for p in pwd.getpwall()
                           if p.pw_gid == infos[0].st_gid or p.pw_name in group))
    return tuple((i.st_dev, i.st_ino, i.st_uid, i.st_gid, i.st_mode) for i in infos), members


def _tool(path):
    resolved = path.resolve(strict=True)
    for part in (resolved, *resolved.parents):
        info = part.lstat()
        _require(info.st_uid in {0, INSTALLATION_UID} and not info.st_mode & stat.S_IWOTH
                 and (not info.st_mode & stat.S_IWGRP or info.st_gid == INSTALLATION_GID),
                 "bootstrap_tool_untrusted")
    _require(resolved.is_file() and os.access(resolved, os.X_OK), "bootstrap_tool_untrusted")
    return str(resolved)


@contextmanager
def _deployment_lock(root):
    """Caller validated this installation; never create/replace the shell lock."""
    _require((root / ".git").is_dir() and not (root / ".git").is_symlink(),
             "bootstrap_linked_worktree")
    installation = _root_identity(root)
    gitdir = Path(_git(root, "rev-parse", "--absolute-git-dir").decode().strip())
    common = Path(_git(root, "rev-parse", "--git-common-dir").decode().strip())
    lock = Path(_git(root, "rev-parse", "--git-path", "twobrain-rec-deploy.lock").decode().strip())
    common = common if common.is_absolute() else root / common
    lock = lock if lock.is_absolute() else root / lock
    _require(gitdir == root / ".git" and common.resolve() == gitdir
             and lock == gitdir / "twobrain-rec-deploy.lock"
             and _git(root, "rev-parse", "--show-toplevel").decode().strip() == str(root),
             "bootstrap_lock_path_mismatch")
    descriptor = None
    try:
        descriptor = os.open(lock, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        initial = os.fstat(descriptor)

        def same():
            _require(_root_identity(root) == installation, "bootstrap_root_changed")
            info = lock.lstat()
            _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                     and info.st_uid in {0, root.stat().st_uid}
                     and not info.st_mode & stat.S_IWOTH
                     and (not info.st_mode & stat.S_IWGRP or info.st_gid == root.stat().st_gid)
                     and (info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode)
                     == (initial.st_dev, initial.st_ino, initial.st_uid, initial.st_gid,
                         initial.st_mode), "bootstrap_lock_untrusted")

        same()
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        same()
        try:
            yield descriptor
        finally:
            same()
    except BootstrapHold:
        raise
    except OSError:
        raise BootstrapHold("bootstrap_lock_unavailable") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _snapshot(root, source, destination):
    with tarfile.open(fileobj=io.BytesIO(_git(root, "archive", "--format=tar", source))) as archive:
        names = set()
        for member in archive.getmembers():
            path = PurePosixPath(member.name)
            _require(not path.is_absolute() and path.parts and ".." not in path.parts
                     and member.name.rstrip("/") == str(path)
                     and str(path) not in names and (member.isfile() or member.isdir()),
                     "bootstrap_archive_untrusted")
            names.add(str(path))
        archive.extractall(destination, filter="data")


def _package_manifest(source, installed):
    def files(root):
        found = {}
        for path in root.rglob("*"):
            info = path.lstat()
            _require(stat.S_ISDIR(info.st_mode) or (stat.S_ISREG(info.st_mode)
                     and info.st_nlink == 1), "bootstrap_package_untrusted")
            if path.is_file():
                found[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        return found

    expected, actual = files(source), files(installed)
    _require(expected and expected == actual, "bootstrap_package_mismatch")
    digest = hashlib.sha256()
    for name in sorted(expected):
        digest.update(name.encode() + b"\0" + bytes.fromhex(expected[name]))
    return dict(package_file_count=len(expected), package_manifest_sha256=digest.hexdigest())


def _prepare(root, source, temporary):
    _require(shutil.disk_usage(root).free > 10 * 1024**3, "bootstrap_space_insufficient")
    snapshot, venv = temporary / "source", temporary / "venv"
    snapshot.mkdir(mode=0o700)
    _snapshot(root, source, snapshot)
    project = snapshot / "apps/server"
    snapshot_before = _package_manifest(snapshot, snapshot)
    package_before = _package_manifest(snapshot / PACKAGE, snapshot / PACKAGE)
    lock_digest = hashlib.sha256((project / "uv.lock").read_bytes()).hexdigest()
    home = Path(pwd.getpwuid(INSTALLATION_UID).pw_dir)
    uv = home / ".local/bin/uv"
    python = home / ".local/share/uv/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13"
    env = dict(_environment(), UV_PROJECT_ENVIRONMENT=str(venv), UV_LINK_MODE="copy",
               UV_COMPILE_BYTECODE="0")
    _run([_tool(uv), "--no-cache", "sync", "--project", str(project), "--frozen", "--no-dev",
          "--no-default-groups", "--no-editable", "--no-python-downloads", "--python", _tool(python)],
         deadline=time.monotonic() + 180, env=env)
    code = ("import json,sys,twobrain_rec_server;print(json.dumps(dict("
            "version=list(sys.version_info[:2]),prefix=sys.prefix,"
            "package=twobrain_rec_server.__file__)))")
    info = json.loads(_run([str(venv / "bin/python"), "-I", "-B", "-c", code]))
    installed = Path(info["package"]).resolve(strict=True).parent
    _require(info["version"] == [3, 13] and Path(info["prefix"]).resolve() == venv.resolve()
             and installed.is_relative_to(venv.resolve()) and not installed.is_relative_to(snapshot),
             "bootstrap_runtime_mismatch")
    manifest = _package_manifest(snapshot / PACKAGE, installed)
    _require(manifest == package_before
             and _package_manifest(snapshot, snapshot) == snapshot_before,
             "bootstrap_source_changed")
    for directory in (snapshot, installed):
        for path in directory.rglob("*"):
            _require(not path.is_symlink(), "bootstrap_package_untrusted")
            path.chmod(0o500 if path.is_dir() or path.stat().st_mode & 0o111 else 0o400)
        directory.chmod(0o500)
    _require(_package_manifest(snapshot / PACKAGE, installed) == manifest
             and hashlib.sha256((project / "uv.lock").read_bytes()).hexdigest() == lock_digest,
             "bootstrap_package_changed")
    return dict(source_sha=source, lock_sha256=lock_digest, **manifest)


def _runtime(temporary, source):
    """Invoke only the installed module while its pinned environment still exists."""
    raw = _run([str(temporary / "venv/bin/python"), "-I", "-B", "-m",
                "twobrain_rec_server.product_analytics.activation_operator",
                "--runtime-preflight", "--source-sha", source], deadline=time.monotonic() + 35)

    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, "bootstrap_runtime_result_invalid")
            result[key] = value
        return result

    _require(len(raw) <= 2048, "bootstrap_runtime_result_invalid")
    result = json.loads(raw, object_pairs_hook=unique)
    _require(isinstance(result, dict)
             and set(result) == {"runtime", "source_sha", "runtime_sha256", "container_count"}
             and result["runtime"] == "verified" and result["source_sha"] == source
             and isinstance(result["runtime_sha256"], str)
             and re.fullmatch(r"[a-f0-9]{64}", result["runtime_sha256"])
             and type(result["container_count"]) is int and 1 <= result["container_count"] <= 11,
             "bootstrap_runtime_result_invalid")
    return result


def main(argv=None):
    with _signals() as pending:
        return _main(argv, pending)


def _main(argv, pending):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true", required=True)
    parser.parse_args(argv)
    result = dict(result="hold", reason="full_preflight_not_implemented", bootstrap="unverified")
    try:
        _require(sys.flags.isolated, "bootstrap_isolated_python_required")
        root = _installation()
        with _deployment_lock(root):
            _require(_installation() == root and not pending, "bootstrap_installation_changed")
            source = _git(root, "rev-parse", "HEAD").decode().strip()
            _require(re.fullmatch(r"[a-f0-9]{40}", source)
                     and not _git(root, "status", "--porcelain", "--untracked-files=no").strip()
                     and _git(root, "show", f"{source}:infra/scripts/activation-operator.py")
                     == Path(__file__).read_bytes(), "bootstrap_source_mismatch")
            temporary = Path(tempfile.mkdtemp(prefix="graf-activation-operator-"))
            try:
                temporary.chmod(0o700)
                metadata = _prepare(root, source, temporary)
                metadata.update(_runtime(temporary, source))
                _require(_git(root, "rev-parse", "HEAD").decode().strip() == source
                         and not _git(root, "status", "--porcelain", "--untracked-files=no").strip(),
                         "bootstrap_source_changed")
            finally:
                for path in temporary.rglob("*"):
                    if path.is_dir() and not path.is_symlink():
                        path.chmod(0o700)
                shutil.rmtree(temporary)
            _require(not pending, "bootstrap_interrupted")
            _require(_installation() == root, "bootstrap_installation_changed")
            result.update(metadata, bootstrap="verified")
    except BootstrapHold as error:
        result["reason"] = str(error)
    except Exception:
        result["reason"] = "bootstrap_unverified"
    print(json.dumps(result, sort_keys=True))
    return 1  # No complete preflight, readiness, T0 or product mutation in this stage.


if __name__ == "__main__":
    raise SystemExit(main())
