"""F224: real local Git repositories and disposable machine state; no live app."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest


ROOT = Path(__file__).resolve().parents[2]


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True, stderr=subprocess.DEVNULL).strip()


def repository(path, url="git@github.com:Example/Graf.git"):
    path.mkdir(parents=True)
    git(path, "init", "-q")
    git(path, "config", "remote.origin.url", url)
    return path


@pytest.fixture
def harness(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("ownership_harness", ROOT / "scripts/dev-harness.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    repo = repository(tmp_path / "checkout")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("GRAF_DEV_STATE_DIR", raising=False)
    monkeypatch.delenv("GRAF_DEV_INSTALL_PATH", raising=False)
    monkeypatch.setattr(module, "_repo_root", lambda: repo)
    monkeypatch.setattr(module, "_assert_empty_dev_machine", lambda: None, raising=False)
    return module


@pytest.mark.parametrize("url", [
    "https://github.com/Example/Graf.git", "ssh://git@GitHub.com/example/graf.git/",
    "git@github.com:EXAMPLE/GRAF", "https://github.com/example/graf/",
])
def test_strict_repository_forms_share_identity(harness, url):
    git(harness._repo_root(), "config", "remote.origin.url", url)
    assert harness._repo_identity() == "github.com/example/graf"


@pytest.mark.parametrize("url", [
    "https://secret@github.com/example/graf", "https://u:secret@github.com/example/graf",
    "https://github.com/example/graf?token=secret", "https://github.com/example/graf#secret",
    "https://github.com/example/%67raf", "https://github.com/example/../graf",
    "http://github.com/example/graf", "ssh://git@github.com:22/example/graf",
    "git@other.example:example/graf", "file:///example/graf", "https://github.com/example/graf//",
    "https://github.com/example/graf\n", "https://github.com/example//graf",
    "https://github.com/example/graf?", "https://github.com/example/graf#",
])
def test_unsafe_origins_fail_without_disclosing_value(harness, url):
    git(harness._repo_root(), "config", "remote.origin.url", url)
    with pytest.raises(harness.HarnessError) as error:
        harness._repo_identity()
    assert "secret" not in str(error.value) and url not in str(error.value)


def test_git_failure_multiple_origin_and_instead_of_fail_closed(harness, monkeypatch, tmp_path):
    repo = harness._repo_root()
    git(repo, "config", "--add", "remote.origin.url", "git@github.com:other/graf")
    with pytest.raises(harness.HarnessError):
        harness._repo_identity()
    git(repo, "config", "--unset-all", "remote.origin.url")
    with pytest.raises(harness.HarnessError):
        harness._repo_identity()
    git(repo, "config", "remote.origin.url", "https://github.com/example/graf")
    git(repo, "config", "url.https://github.com/other/.insteadOf", "https://github.com/example/")
    with pytest.raises(harness.HarnessError):
        harness._repo_identity()
    monkeypatch.setattr(harness, "_repo_root", lambda: tmp_path / "missing")
    with pytest.raises(harness.HarnessError):
        harness._repo_identity()


def adopt(harness, root, **kwargs):
    return harness.operation_adopt_state(argparse.Namespace(
        state_root=root, expected_repository="github.com/example/graf",
        expected_active_sha=kwargs.pop("expected_active_sha", None),
        expect_empty=kwargs.pop("expect_empty", True), confirm_repository_ownership=True,
        **kwargs,
    ))


def test_binding_preserves_root_lock_and_independent_clone(harness, tmp_path, monkeypatch):
    state = harness._machine_state_base() / "old-name" / "harness"
    state.mkdir(parents=True)
    lock = state / "promote.lock"
    lock.touch()
    inode = lock.stat().st_ino
    adopt(harness, state)
    before = (harness._machine_state_base() / "repository-state.json").read_bytes()
    clone = repository(tmp_path / "different-name", "https://github.com/EXAMPLE/graf.git")
    monkeypatch.setattr(harness, "_repo_root", lambda: clone)
    monkeypatch.chdir(tmp_path)
    assert harness.global_state_dir() == state
    assert harness.state_dir(live=True) == state
    adopt(harness, state)
    assert (harness._machine_state_base() / "repository-state.json").read_bytes() == before
    assert lock.stat().st_ino == inode
    git(clone, "config", "remote.origin.url", "git@github.com:other/graf")
    with pytest.raises(harness.HarnessError):
        harness.state_dir()


def test_unbound_shared_state_does_not_create_files(harness):
    with pytest.raises(harness.HarnessError):
        harness.state_dir()
    assert not harness._machine_state_base().exists()


def test_fixture_is_file_only_even_when_unbound(harness, monkeypatch, tmp_path):
    fixture = tmp_path / "fixture"
    monkeypatch.setenv("GRAF_DEV_STATE_DIR", str(fixture))
    assert harness.state_dir() == fixture
    with pytest.raises(harness.HarnessError):
        harness.state_dir(live=True)
    assert not fixture.exists()


def test_corrupt_binding_cannot_be_bypassed_with_fixture(harness, monkeypatch, tmp_path):
    base = harness._machine_state_base()
    base.mkdir(parents=True)
    (base / "repository-state.json").write_text("{}")
    monkeypatch.setenv("GRAF_DEV_STATE_DIR", str(tmp_path / "fixture"))
    with pytest.raises(harness.HarnessError):
        harness.state_dir()


def test_ambiguous_roots_and_symlink_are_rejected(harness, tmp_path):
    root = harness._machine_state_base() / "old" / "harness"
    other = harness._machine_state_base() / "other" / "harness"
    root.mkdir(parents=True)
    other.mkdir(parents=True)
    (other / "unclassified").touch()
    with pytest.raises(harness.HarnessError):
        adopt(harness, root)
    assert not (harness._machine_state_base() / "repository-state.json").exists()
    (other / "unclassified").unlink()
    other.rmdir()
    (root / "promote.lock").symlink_to(tmp_path / "outside-lock")
    with pytest.raises(harness.HarnessError):
        adopt(harness, root)
    assert not (tmp_path / "outside-lock").exists()


def test_fixture_overlap_and_live_override_fail_before_creation(harness, monkeypatch, tmp_path):
    state = harness._machine_state_base() / "old" / "harness"
    state.mkdir(parents=True)
    adopt(harness, state)
    for path in (state.parent, state / "fixture", tmp_path / "external"):
        monkeypatch.setenv("GRAF_DEV_STATE_DIR", str(path))
        with pytest.raises(harness.HarnessError):
            harness.state_dir(live=True)
    monkeypatch.setenv("GRAF_DEV_STATE_DIR", str(state / "fixture"))
    with pytest.raises(harness.HarnessError):
        harness.state_dir()
    assert not (state / "fixture").exists()


def test_failed_binding_publication_keeps_old_files_and_lock(harness, monkeypatch):
    state = harness._machine_state_base() / "old" / "harness"
    state.mkdir(parents=True)
    lock = state / "promote.lock"
    lock.touch()
    inode = lock.stat().st_ino
    def fail(*args):
        raise OSError("synthetic disk full")
    monkeypatch.setattr(harness, "_write_json", fail)
    with pytest.raises((harness.HarnessError, OSError)):
        adopt(harness, state)
    assert lock.stat().st_ino == inode
    assert not (harness._machine_state_base() / "repository-state.json").exists()


def legacy_state(harness, tmp_path):
    root = harness._machine_state_base() / "old" / "harness"
    root.mkdir(parents=True)
    item = harness.build_manifest("a" * 40, "224", migration_head="same", root=tmp_path / "fixture")
    item["status"] = "active"
    item["dev_boundary"]["data_root"] = str(root / "data")
    harness._write_json(root / "manifests" / (item["manifest_id"] + ".json"), item)
    harness._write_json(root / "active-manifest.json", {
        "schema_version": harness.POINTER_VERSION, "manifest_id": item["manifest_id"], "runtime_mode": "live",
    })
    harness._write_json(root / "runtime.json", {"source_sha": item["source_sha"], "images": {}})
    (root / "promote.lock").touch()
    return root, item


@pytest.mark.parametrize("marker", ["rollback-required.json", "app-launch-validation-recovery.json"])
def test_adoption_refuses_unfinished_recovery_without_changing_state(harness, tmp_path, marker):
    root, item = legacy_state(harness, tmp_path)
    (root / marker).write_text('{"status":"recovery_required"}')
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    inode = (root / "promote.lock").stat().st_ino
    with pytest.raises(harness.HarnessError, match="recover Dev state before adoption"):
        adopt(harness, root, expect_empty=False, expected_active_sha=item["source_sha"])
    assert before == {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert (root / "promote.lock").stat().st_ino == inode
    assert not (harness._machine_state_base() / "repository-state.json").exists()


def test_existing_runtime_without_manifest_id_is_preserved(harness, tmp_path):
    root, item = legacy_state(harness, tmp_path)
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    inode = (root / "promote.lock").stat().st_ino
    adopt(harness, root, expect_empty=False, expected_active_sha=item["source_sha"])
    assert before == {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert (root / "promote.lock").stat().st_ino == inode


# Execute the actual harness in children with disposable HOME and a real origin.
# Only the fresh-machine presence check is replaced: no native/Docker calls occur.
CHILD = '''
import importlib.util,json,sys
from pathlib import Path
p=json.loads(sys.argv[1]); s=importlib.util.spec_from_file_location('child_harness',p['source'])
h=importlib.util.module_from_spec(s); s.loader.exec_module(h)
h._repo_root=lambda:Path(p['repo']); h._assert_empty_dev_machine=lambda:None
'''


def child(harness, script, **values):
    payload = {"source": str(ROOT / "scripts/dev-harness.py"), "repo": str(harness._repo_root()), **values}
    return subprocess.Popen([sys.executable, "-c", CHILD + script, json.dumps(payload)],
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def wait_file(path, process):
    deadline = time.monotonic() + 10
    while not path.exists():
        assert process.poll() is None, process.communicate()
        assert time.monotonic() < deadline, "child did not reach synchronization point"
        time.sleep(0.01)


def test_adoption_waits_for_old_lock_and_rechecks_sha(harness, tmp_path):
    root, item = legacy_state(harness, tmp_path)
    ready, release = tmp_path / "ready", tmp_path / "release"
    # This holder uses the same kernel lock as the pre-binding controller.
    holder = subprocess.Popen([sys.executable, "-c", '''
import fcntl,sys,time
from pathlib import Path
with Path(sys.argv[1]).open('a+') as f:
 fcntl.flock(f,fcntl.LOCK_EX); Path(sys.argv[2]).touch()
 while not Path(sys.argv[3]).exists(): time.sleep(.01)
''', str(root / "promote.lock"), str(ready), str(release)])
    contender = None
    try:
        wait_file(ready, holder)
        contender = child(harness, '''
from argparse import Namespace
Path(p['entered']).touch()
h.operation_adopt_state(Namespace(state_root=Path(p['state']), expected_repository='github.com/example/graf',
 expected_active_sha='a'*40, expect_empty=False, confirm_repository_ownership=True))
''', state=str(root), entered=str(tmp_path / "entered"))
        wait_file(tmp_path / "entered", contender)
        time.sleep(0.1)
        assert contender.poll() is None
        assert not (harness._machine_state_base() / "repository-state.json").exists()
        # The old owner advances while the new controller waits.
        path = root / "manifests" / (item["manifest_id"] + ".json")
        changed = json.loads(path.read_text())
        changed["source_sha"] = "b" * 40
        for component in changed["components"].values():
            component["source_sha"] = "b" * 40
        harness._write_json(path, changed)
        release.touch()
        stdout, stderr = contender.communicate(timeout=10)
        assert contender.returncode != 0 and "active Dev SHA changed" in stderr
        assert not (harness._machine_state_base() / "repository-state.json").exists()
    finally:
        release.touch()
        holder.wait(timeout=10)
        if contender is not None and contender.poll() is None:
            contender.kill()
            contender.communicate()


def test_two_registrations_publish_only_one_root(harness):
    roots = [harness._machine_state_base() / side / "harness" for side in ("one", "two")]
    for root in roots:
        root.mkdir(parents=True)
    script = '''
from argparse import Namespace
h.operation_adopt_state(Namespace(state_root=Path(p['state']), expected_repository='github.com/example/graf',
 expected_active_sha=None, expect_empty=True, confirm_repository_ownership=True))
'''
    processes = [child(harness, script, state=str(root)) for root in roots]
    try:
        for process in processes:
            process.communicate(timeout=10)
        assert sorted(p.returncode for p in processes) == [0, 1]
        assert harness.global_state_dir() in roots
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()


@pytest.mark.parametrize("after_publication", [False, True])
def test_adoption_process_exit_keeps_one_definable_binding(harness, after_publication):
    root = harness._machine_state_base() / "old" / "harness"
    root.mkdir(parents=True)
    lock = root / "promote.lock"
    lock.touch()
    inode = lock.stat().st_ino
    process = child(harness, '''
from argparse import Namespace
import os
original=h._write_json
def interrupted(path,value):
 if p['after']: original(path,value)
 os._exit(9)
h._write_json=interrupted
h.operation_adopt_state(Namespace(state_root=Path(p['state']), expected_repository='github.com/example/graf',
 expected_active_sha=None, expect_empty=True, confirm_repository_ownership=True))
''', state=str(root), after=after_publication)
    process.communicate(timeout=10)
    assert process.returncode == 9
    assert (harness._read_repository_binding() is not None) == after_publication
    assert lock.stat().st_ino == inode
    if after_publication:
        assert harness.global_state_dir() == root


def test_direct_live_adapter_and_shared_metadata_publish_are_blocked(harness, tmp_path):
    adapter = harness.GrafLocalAdapter(harness._repo_root(), tmp_path / "fixture")
    with pytest.raises(harness.HarnessError):
        adapter._assert_supported()
    root, item = legacy_state(harness, tmp_path)
    adopt(harness, root, expect_empty=False, expected_active_sha=item["source_sha"])
    before = (root / "active-manifest.json").read_bytes()
    with pytest.raises(harness.HarnessError):
        harness._publish_active(root, item, "metadata-only")
    assert (root / "active-manifest.json").read_bytes() == before


@pytest.mark.parametrize("shared", [False, True])
def test_only_adopted_state_prune_can_remove_global_tags(harness, monkeypatch, tmp_path, shared):
    root = harness._machine_state_base() / "old" / "harness" if shared else tmp_path / "fixture"
    if shared:
        adopt(harness, root)
    old = harness.build_manifest("a" * 40, "224", root=root)
    active = harness.build_manifest("b" * 40, "224", root=root)
    (root / "artifacts" / old["manifest_id"]).mkdir(parents=True)
    calls = []
    monkeypatch.setattr(harness, "_run_command", lambda *a, **kw: calls.append(a) or "")
    adapter = harness.GrafLocalAdapter(harness._repo_root(), root)
    adapter._apply_retention(active, None)
    assert bool(calls) == shared
    assert all(call[0][:3] == ["docker", "image", "rm"] for call in calls)
    assert not (root / "artifacts" / old["manifest_id"]).exists()


def test_worktree_and_local_clone_use_the_same_adopted_state(harness, monkeypatch, tmp_path):
    repo = harness._repo_root()
    git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.test", "commit", "--allow-empty", "-qm", "fixture")
    worktree = tmp_path / "other-worktree"
    git(repo, "worktree", "add", "-q", "--detach", str(worktree))
    clone = tmp_path / "independent-clone"
    subprocess.check_call(["git", "clone", "-q", "--local", str(repo), str(clone)], stderr=subprocess.DEVNULL)
    git(clone, "config", "remote.origin.url", "https://github.com/example/graf.git")
    root = harness._machine_state_base() / "old" / "harness"
    adopt(harness, root)
    for checkout in (worktree, clone):
        monkeypatch.setattr(harness, "_repo_root", lambda: checkout)
        monkeypatch.chdir(tmp_path)
        assert harness.state_dir(live=True) == root


def test_lock_inode_replacement_is_rejected_after_waiting(harness, tmp_path):
    root, item = legacy_state(harness, tmp_path)
    lock = root / "promote.lock"
    ready, release, opened = (tmp_path / name for name in ("ready", "release", "opened"))
    holder = subprocess.Popen([sys.executable, "-c", '''
import fcntl,sys,time
from pathlib import Path
with Path(sys.argv[1]).open('a+') as f:
 fcntl.flock(f,fcntl.LOCK_EX); Path(sys.argv[2]).touch()
 while not Path(sys.argv[3]).exists(): time.sleep(.01)
''', str(lock), str(ready), str(release)])
    contender = None
    try:
        wait_file(ready, holder)
        contender = child(harness, '''
from argparse import Namespace
import os
original=h.fcntl.flock
def observed(fd,mode):
 if os.fstat(fd).st_ino==p['inode']: Path(p['opened']).touch()
 return original(fd,mode)
h.fcntl.flock=observed
h.operation_adopt_state(Namespace(state_root=Path(p['state']), expected_repository='github.com/example/graf',
 expected_active_sha='a'*40, expect_empty=False, confirm_repository_ownership=True))
''', state=str(root), inode=lock.stat().st_ino, opened=str(opened))
        wait_file(opened, contender)
        lock.rename(root / "old-promote.lock")
        lock.touch()
        release.touch()
        stdout, stderr = contender.communicate(timeout=10)
        assert contender.returncode != 0 and "lock was replaced" in stderr
        assert not (harness._machine_state_base() / "repository-state.json").exists()
    finally:
        release.touch()
        holder.wait(timeout=10)
        if contender is not None and contender.poll() is None:
            contender.kill()
            contender.communicate()


def test_bound_writers_recheck_parent_after_one_operational_lock(harness, tmp_path):
    root, active = legacy_state(harness, tmp_path)
    adopt(harness, root, expect_empty=False, expected_active_sha=active["source_sha"])
    candidates = []
    for sha in ("b" * 40, "c" * 40):
        item = harness.build_manifest(sha, "224", migration_head="same", root=tmp_path / "fixture")
        item["parent_manifest_id"] = active["manifest_id"]
        path = tmp_path / (sha[0] + ".json")
        harness._write_json(path, item)
        candidates.append(path)
    script = '''
import time
from argparse import Namespace
class Adapter:
 def __init__(self,*args): pass
 def promote(self,item,**kwargs):
  with Path(p['log']).open('a') as f: f.write('start '+item['source_sha']+'\\n')
  time.sleep(.1)
  with Path(p['log']).open('a') as f: f.write('finish '+item['source_sha']+'\\n')
  return {'mode':'live','checks':{'fixture':'pass'}}
h.GrafLocalAdapter=Adapter
h.operation_promote(Namespace(manifest=p['manifest'],live=True,dry_run=False))
'''
    log = tmp_path / "writers.log"
    processes = [child(harness, script, manifest=str(path), log=str(log)) for path in candidates]
    outputs = [process.communicate(timeout=10) for process in processes]
    assert sorted(p.returncode for p in processes) == [0, 1], outputs
    assert len(log.read_text().splitlines()) == 2
    assert any("parent manifest is stale" in stderr for stdout, stderr in outputs)
    assert harness._load_active(root)["source_sha"] in {"b" * 40, "c" * 40}


def test_frozen_resolver_mismatch_fails_before_adapter_execution(harness, tmp_path):
    repo = harness._repo_root()
    source = (ROOT / "scripts/dev-harness.py").read_text()
    source += "\ndef global_state_dir():\n    return Path('/wrong-frozen-root')\n"
    for relative in harness.RUNTIME_DEFINITION_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source if relative == "scripts/dev-harness.py" else "# fixture\n")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.test", "commit", "-qm", "fixture")
    item = harness.build_manifest(git(repo, "rev-parse", "HEAD"), "224", root=tmp_path / "fixture")
    adapter = harness.GrafLocalAdapter(repo, tmp_path / "fixture")
    with pytest.raises(harness.HarnessError, match="pinned checkout resolver"):
        adapter._checkout_adapter(repo, item)


@pytest.mark.parametrize("volume", ["graf-dev-postgres-data", "graf-dev-minio-data", "graf-dev-media-work", "unknown", ""])
def test_empty_machine_requires_absent_dev_volumes(monkeypatch, tmp_path, volume):
    spec = importlib.util.spec_from_file_location("empty_harness", ROOT / "scripts/dev-harness.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "sys", argparse.Namespace(platform="darwin"))
    monkeypatch.setattr(module, "DEV_APP_PATH", tmp_path / "absent.app")
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **kw: argparse.Namespace(returncode=1))
    calls = []
    def output(command, **kwargs):
        calls.append(command)
        if command[1] == "ps":
            return ""
        assert command[:3] == ["docker", "volume", "ls"]
        if volume == "unknown":
            raise subprocess.CalledProcessError(1, command)
        return volume + "\n" if volume else "unrelated-volume\n"
    monkeypatch.setattr(module.subprocess, "check_output", output)
    if volume:
        with pytest.raises(module.HarnessError):
            module._assert_empty_dev_machine()
    else:
        module._assert_empty_dev_machine()
    assert len(calls) == 2


def test_startup_guard_rejects_original_symlink(harness, tmp_path):
    root, item = legacy_state(harness, tmp_path)
    adopt(harness, root, expect_empty=False, expected_active_sha=item["source_sha"])
    harness._schema_start_guard(root, item["source_sha"])
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(harness.HarnessError, match="symlink"):
        harness._schema_start_guard(alias, item["source_sha"])


def test_state_marker_waits_for_operational_lock(harness, tmp_path):
    root, item = legacy_state(harness, tmp_path)
    adopt(harness, root, expect_empty=False, expected_active_sha=item["source_sha"])
    ready, release, waiting = (tmp_path / name for name in ("ready", "release", "waiting"))
    holder = subprocess.Popen([sys.executable, "-c", '''
import fcntl,sys,time
from pathlib import Path
with Path(sys.argv[1]).open('a+') as f:
 fcntl.flock(f,fcntl.LOCK_EX); Path(sys.argv[2]).touch()
 while not Path(sys.argv[3]).exists(): time.sleep(.01)
''', str(root / "promote.lock"), str(ready), str(release)])
    contender = None
    try:
        wait_file(ready, holder)
        contender = child(harness, '''
import os
original=h.fcntl.flock
def observed(fd,mode):
 Path(p['waiting']).touch()
 return original(fd,mode)
h.fcntl.flock=observed
with h.state_lock(Path(p['state'])): pass
''', state=str(root), waiting=str(waiting))
        wait_file(waiting, contender)
        assert contender.poll() is None
        assert not (root / ".dev-boundary").exists()
        release.touch()
        stdout, stderr = contender.communicate(timeout=10)
        assert contender.returncode == 0, (stdout, stderr)
        assert (root / ".dev-boundary").is_file()
    finally:
        release.touch()
        holder.wait(timeout=10)
        if contender is not None and contender.poll() is None:
            contender.kill()
            contender.communicate()


@pytest.mark.parametrize("bound", [False, True])
def test_adoption_rejects_nonstandard_install_before_registration(harness, tmp_path, monkeypatch, bound):
    root = harness._machine_state_base() / "empty" / "harness"
    if bound:
        adopt(harness, root)
    alternate = tmp_path / "stopped GRAF Dev.app"
    alternate.mkdir()
    monkeypatch.setenv("GRAF_DEV_INSTALL_PATH", str(alternate))
    base = harness._machine_state_base()
    before = {p: (p.read_bytes(), p.stat().st_ino) for p in base.rglob("*") if p.is_file()}
    with pytest.raises(harness.HarnessError, match="standard Dev app path"):
        adopt(harness, root)
    assert before == {p: (p.read_bytes(), p.stat().st_ino) for p in base.rglob("*") if p.is_file()}
    assert bound or not base.exists()


@pytest.mark.parametrize("mode", [None, "lve", "compose", "live-dry-run", {}, [], 7])
@pytest.mark.parametrize("operation", ["read", "adopt"])
def test_active_pointer_unknown_runtime_mode_fails_closed(harness, tmp_path, mode, operation):
    root, item = legacy_state(harness, tmp_path)
    pointer = root / "active-manifest.json"
    data = json.loads(pointer.read_text())
    if mode is None:
        data.pop("runtime_mode")
    else:
        data["runtime_mode"] = mode
    pointer.write_text(json.dumps(data))
    (root / "runtime.json").unlink()
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    inode = (root / "promote.lock").stat().st_ino
    with pytest.raises(harness.HarnessError, match="unsupported runtime mode"):
        if operation == "read":
            harness._load_active(root)
        else:
            adopt(harness, root, expect_empty=False, expected_active_sha=item["source_sha"])
    assert before == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert (root / "promote.lock").stat().st_ino == inode
    assert not (harness._machine_state_base() / "repository-state.json").exists()


@pytest.mark.parametrize("mode", ["live", "metadata-only"])
def test_active_pointer_supported_runtime_modes(harness, tmp_path, mode):
    root, item = legacy_state(harness, tmp_path)
    pointer = root / "active-manifest.json"
    data = json.loads(pointer.read_text())
    data["runtime_mode"] = mode
    pointer.write_text(json.dumps(data))
    if mode == "metadata-only":
        (root / "runtime.json").unlink()
    assert harness._load_active(root)["source_sha"] == item["source_sha"]
    adopt(harness, root, expect_empty=False, expected_active_sha=item["source_sha"])


# T009 classification fixtures use an independently encoded, disposable tree.
def classification_digest(root):
    import hashlib
    import os
    import stat
    rows = []
    for path in sorted([root, *root.rglob('*')], key=lambda p: p.relative_to(root).as_posix()):
        info = path.lstat()
        kind = ('directory' if stat.S_ISDIR(info.st_mode) else 'symlink' if stat.S_ISLNK(info.st_mode)
                else 'file' if stat.S_ISREG(info.st_mode) else 'special')
        row = {'path': path.relative_to(root).as_posix(), 'type': kind}
        row.update(device=info.st_dev, inode=info.st_ino, uid=info.st_uid, gid=info.st_gid,
                   mode=info.st_mode, size=info.st_size, mtime_ns=info.st_mtime_ns, ctime_ns=info.st_ctime_ns)
        if kind == 'file':
            row['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        elif kind == 'symlink':
            row['target'] = os.readlink(path)
        rows.append(row)
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def classification_plan(harness, tmp_path, root, *others):
    entries = []
    for candidate in (root, *others):
        info = candidate.stat()
        entries.append(dict(path=str(candidate), device=info.st_dev, inode=info.st_ino,
                            kind='selected' if candidate == root else 'preserved-state',
                            tree_sha256=classification_digest(candidate), artifacts=[], build_archives=[],
                            evidence=('Selected repository ownership verified; old jobs excluded.' if candidate == root else
                                      'Historical owner unknown; preserve without ownership or use; old jobs excluded.')))
    path = tmp_path / 'classification.json'
    path.write_text(json.dumps(dict(schema_version='graf-dev-state-classification.v1',
                                   repository='github.com/example/graf', selected_root=str(root), roots=entries)))
    return path


def classified_fixture(harness, tmp_path):
    root, item = legacy_state(harness, tmp_path)
    other = harness._machine_state_base() / 'preserved' / 'harness'
    other.mkdir(parents=True)
    (other / 'promote.lock').touch()
    (other / '.dev-boundary').write_text('historical fixture')
    plan = classification_plan(harness, tmp_path, root, other)
    return root, item, other, plan


def historical_metadata_fixture(harness, tmp_path):
    root, item, other, _ = classified_fixture(harness, tmp_path)
    # Encode the historical record independently of the current manifest builder.
    manifest = {
        'schema_version': 'dev-manifest.v1', 'manifest_id': 'historical-archive',
        'feature_id': '216', 'source_sha': 'b' * 40,
        'components': {name: {'source_sha': 'b' * 40, 'version': 'historical',
                              'digest': 'sha256:' + 'c' * 64}
                       for name in ('backend', 'frontend', 'worker', 'macos_app')},
        'migration_head': 'historical', 'operator': 'fixture',
        'created_at': '2026-01-01T00:00:00Z', 'parent_manifest_id': None,
        'health': {'result': 'unknown'},
        'app_identity': {'bundle_id': 'pro.2brain.graf.dev', 'channel': 'dev',
                         'signing_identity': 'fixture', 'designated_requirement': 'fixture'},
        'dev_boundary': {'environment': 'development', 'backend_origin': 'http://127.0.0.1:8765',
                         'frontend_origin': 'http://127.0.0.1:8765', 'data_root': str(other / 'data')},
    }
    pointer = {'schema_version': 'dev-active-pointer.v1', 'manifest_id': manifest['manifest_id'],
               'runtime_mode': 'metadata-only'}
    manifest_path = other / 'manifests' / 'historical-archive.json'
    harness._write_json(manifest_path, manifest)
    harness._write_json(other / 'active-manifest.json', pointer)
    return root, item, other, manifest, pointer, manifest_path


def test_classification_preserves_historical_metadata_without_using_it(harness, tmp_path, monkeypatch):
    root, item, other, manifest, pointer, path = historical_metadata_fixture(harness, tmp_path)
    plan = classification_plan(harness, tmp_path, root, other)
    before = [classification_digest(p) for p in (root, other)]
    monkeypatch.setattr(harness, '_run_command', lambda *a, **k: pytest.fail('external command'))
    result = adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert result['state_root'] == str(root) and result['adopted_active_sha'] == item['source_sha']
    assert before == [classification_digest(p) for p in (root, other)]
    assert json.loads(path.read_text()) == manifest
    assert json.loads((other / 'active-manifest.json').read_text()) == pointer
    assert adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'],
                 classification=plan)['idempotent']
    with pytest.raises(harness.HarnessError, match='processing_worker'):
        harness._load_active(other)


@pytest.mark.parametrize('record,field,value', [
    ('pointer', 'schema_version', None), ('pointer', 'schema_version', 'other'),
    ('pointer', 'runtime_mode', None), ('pointer', 'runtime_mode', 'other'),
    ('pointer', 'runtime_mode', []), ('pointer', 'runtime_mode', True),
    ('pointer', 'manifest_id', '../PRIVATE_SENTINEL'), ('pointer', 'manifest_id', 12),
    ('pointer', 'manifest_id', 'missing'), ('pointer', 'manifest_id', None),
    ('pointer', 'source_sha', 'c' * 40), ('pointer', 'source_sha', None),
    ('pointer', 'status', 'ready'), ('pointer', 'status', None),
    ('manifest', 'schema_version', 'other'), ('manifest', 'manifest_id', 'mismatch'),
    ('manifest', 'manifest_id', 12), ('manifest', 'feature_id', 216),
    ('manifest', 'feature_id', '../PRIVATE_SENTINEL'),
    ('manifest', 'source_sha', 12), ('manifest', 'source_sha', 'a' * 39),
    ('manifest', 'source_sha', 'g' * 40), ('manifest', 'status', 'recovery_required'),
    ('manifest', 'status', None), ('manifest', 'status', []),
    ('manifest', 'health.result', 'other'), ('manifest', 'health.result', []),
    ('manifest', 'app_identity.bundle_id', 'pro.2brain.graf'),
    ('manifest', 'app_identity.channel', 'production'),
    ('manifest', 'app_identity.signing_identity', ''),
    ('manifest', 'app_identity.designated_requirement', ''),
    ('manifest', 'dev_boundary.environment', 'production'),
    ('manifest', 'dev_boundary.backend_origin', 'https://example.com'),
    ('manifest', 'dev_boundary.frontend_origin', 'https://example.com'),
    ('manifest', 'dev_boundary.data_root', '/production/data'),
    ('manifest', 'components', []),
] + [(record, key, value) for record in ('pointer', 'manifest')
     for key in ('recovery_required', 'rollback_required') for value in (False, None, True)])
def test_historical_metadata_rejects_invalid_fields(harness, tmp_path, monkeypatch, record, field, value):
    root, item, other, manifest, pointer, path = historical_metadata_fixture(harness, tmp_path)
    target = pointer if record == 'pointer' else manifest
    keys = field.split('.')
    for key in keys[:-1]:
        target = target[key]
    target[keys[-1]] = value
    harness._write_json(path, manifest)
    harness._write_json(other / 'active-manifest.json', pointer)
    plan = classification_plan(harness, tmp_path, root, other)
    before = [classification_digest(p) for p in (root, other)]
    monkeypatch.setattr(harness, '_run_command', lambda *a, **k: pytest.fail('external command'))
    with pytest.raises(harness.HarnessError) as error:
        adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert 'PRIVATE_SENTINEL' not in str(error.value)
    assert before == [classification_digest(p) for p in (root, other)]
    assert not (harness._machine_state_base() / 'repository-state.json').exists()


@pytest.mark.parametrize('name', ['backend', 'frontend', 'worker', 'macos_app', 'extra'])
@pytest.mark.parametrize('damage', ['missing', 'scalar', 'sha', 'version-type', 'version-empty', 'digest'])
def test_historical_metadata_checks_every_component(harness, tmp_path, monkeypatch, name, damage):
    root, item, other, manifest, _, path = historical_metadata_fixture(harness, tmp_path)
    components = manifest['components']
    components['extra'] = dict(components['worker'])
    if damage == 'missing':
        if name == 'extra':
            # An additional recorded component may not omit its digest either.
            del components[name]['digest']
        else:
            del components[name]
    elif damage == 'scalar':
        components[name] = None
    else:
        key, value = {'sha': ('source_sha', 'c' * 40), 'version-type': ('version', 1),
                      'version-empty': ('version', '  '), 'digest': ('digest', 'invalid')}[damage]
        components[name][key] = value
    harness._write_json(path, manifest)
    plan = classification_plan(harness, tmp_path, root, other)
    before = [classification_digest(p) for p in (root, other)]
    monkeypatch.setattr(harness, '_run_command', lambda *a, **k: pytest.fail('external command'))
    with pytest.raises(harness.HarnessError, match='invalid preserved Dev description'):
        adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert before == [classification_digest(p) for p in (root, other)]
    assert not (harness._machine_state_base() / 'repository-state.json').exists()


@pytest.mark.parametrize('record', ['pointer', 'manifest'])
@pytest.mark.parametrize('raw', [
    'null', '[]', '123', '"PRIVATE_SENTINEL"', '{', '{"PRIVATE_SENTINEL":',
    '{"PRIVATE_SENTINEL":1,"PRIVATE_SENTINEL":2}',
    '{"nested":{"PRIVATE_SENTINEL":1,"PRIVATE_SENTINEL":2}}',
    '{"PRIVATE_SENTINEL":NaN}', '{"PRIVATE_SENTINEL":Infinity}', '{"PRIVATE_SENTINEL":-Infinity}',
])
def test_historical_metadata_rejects_ambiguous_json(harness, tmp_path, monkeypatch, record, raw):
    root, item, other, _, _, path = historical_metadata_fixture(harness, tmp_path)
    (path if record == 'manifest' else other / 'active-manifest.json').write_text(raw)
    plan = classification_plan(harness, tmp_path, root, other)
    before = [classification_digest(p) for p in (root, other)]
    monkeypatch.setattr(harness, '_run_command', lambda *a, **k: pytest.fail('external command'))
    with pytest.raises(harness.HarnessError, match='^invalid preserved Dev description$') as error:
        adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert 'PRIVATE_SENTINEL' not in str(error.value)
    assert before == [classification_digest(p) for p in (root, other)]
    assert not (harness._machine_state_base() / 'repository-state.json').exists()


@pytest.mark.parametrize('case', ['selected', 'live', 'runtime-empty', 'runtime-dead', 'runtime-unknown',
                                  'journal-complete', 'journal-empty', 'rollback', 'launch-recovery'])
def test_historical_metadata_never_becomes_a_runtime_profile(harness, tmp_path, monkeypatch, case):
    root, item, other, _, pointer, _ = historical_metadata_fixture(harness, tmp_path)
    if case == 'selected':
        root, other = other, root
        expected = 'b' * 40
    else:
        expected = item['source_sha']
        if case == 'live':
            pointer['runtime_mode'] = 'live'
            harness._write_json(other / 'active-manifest.json', pointer)
        else:
            name, value = {
                'runtime-empty': ('runtime.json', {}),
                'runtime-dead': ('runtime.json', {'pid': 999999999, 'source_sha': 'b' * 40}),
                'runtime-unknown': ('runtime.json', {'PRIVATE_SENTINEL': True}),
                'journal-complete': ('schema-transition.json', {
                    'schema_version': 'dev-schema-transition.v1', 'phase': 'complete', 'operation_id': 'upgrade-1',
                    'previous': item, 'target': item,
                    'volumes': {'graf-dev-postgres-data': {}, 'graf-dev-minio-data': {}},
                }),
                'journal-empty': ('schema-transition.json', {}),
                'rollback': ('rollback-required.json', {}),
                'launch-recovery': ('app-launch-validation-recovery.json', {}),
            }[case]
            harness._write_json(other / name, value)
            if case == 'journal-complete':
                assert harness._read_schema_transition(other)['phase'] == 'complete'
    plan = classification_plan(harness, tmp_path, root, other)
    before = [classification_digest(p) for p in (root, other)]
    monkeypatch.setattr(harness, '_run_command', lambda *a, **k: pytest.fail('external command'))
    with pytest.raises(harness.HarnessError, match='processing_worker' if case == 'journal-complete' else None):
        adopt(harness, root, expect_empty=False, expected_active_sha=expected, classification=plan)
    assert before == [classification_digest(p) for p in (root, other)]
    assert not (harness._machine_state_base() / 'repository-state.json').exists()


@pytest.mark.parametrize('record', ['pointer', 'manifest'])
@pytest.mark.parametrize('extra', ['"aux":' + raw for raw in (
    '1e999', '-1e999', '{"nested":1e999}', '{"nested":-1e999}',
    'NaN', 'Infinity', '-Infinity', '{"nested":NaN}', '{"nested":Infinity}', '{"nested":-Infinity}',
)] + ['"aux":1,"aux":1', '"aux":{"nested":1,"nested":1}'])
def test_historical_metadata_rejects_ambiguous_values_in_valid_description(harness, tmp_path, monkeypatch, record, extra):
    root, item, other, manifest, pointer, path = historical_metadata_fixture(harness, tmp_path)
    target = path if record == 'manifest' else other / 'active-manifest.json'
    valid = manifest if record == 'manifest' else pointer
    target.write_text(json.dumps(valid)[:-1] + ',' + extra + '}')
    plan = classification_plan(harness, tmp_path, root, other)
    before = [classification_digest(p) for p in (root, other)]
    monkeypatch.setattr(harness, '_run_command', lambda *a, **k: pytest.fail('external command'))
    with pytest.raises(harness.HarnessError, match='^invalid preserved Dev description$'):
        adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert before == [classification_digest(p) for p in (root, other)]
    assert not (harness._machine_state_base() / 'repository-state.json').exists()


@pytest.mark.parametrize('status', [None, 'ready', 'active'])
def test_historical_metadata_allows_recorded_valid_components(harness, tmp_path, monkeypatch, status):
    root, item, other, manifest, pointer, path = historical_metadata_fixture(harness, tmp_path)
    if status is not None:
        manifest['status'] = status
    manifest['components']['extra'] = dict(manifest['components']['worker'])
    # These are inert strings, never resolved or executed during preservation.
    manifest['components']['extra']['command'] = 'PRIVATE_SENTINEL'
    manifest['aux'] = {'finite': 1.25}
    pointer['aux'] = {'finite': -1.25}
    pointer['source_sha'] = manifest['source_sha']
    harness._write_json(path, manifest)
    harness._write_json(other / 'active-manifest.json', pointer)
    plan = classification_plan(harness, tmp_path, root, other)
    before = [classification_digest(p) for p in (root, other)]
    monkeypatch.setattr(harness, '_run_command', lambda *a, **k: pytest.fail('external command'))
    adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert before == [classification_digest(p) for p in (root, other)]


@pytest.mark.parametrize('record,key', [('pointer', key) for key in ('schema_version', 'runtime_mode', 'manifest_id')]
                         + [('manifest', key) for key in ('schema_version', 'manifest_id', 'feature_id', 'source_sha',
                            'components', 'migration_head', 'app_identity', 'operator', 'created_at',
                            'parent_manifest_id', 'health', 'dev_boundary')])
def test_historical_metadata_requires_base_fields(harness, tmp_path, monkeypatch, record, key):
    root, item, other, manifest, pointer, path = historical_metadata_fixture(harness, tmp_path)
    del (pointer if record == 'pointer' else manifest)[key]
    harness._write_json(path, manifest)
    harness._write_json(other / 'active-manifest.json', pointer)
    plan = classification_plan(harness, tmp_path, root, other)
    before = [classification_digest(p) for p in (root, other)]
    monkeypatch.setattr(harness, '_run_command', lambda *a, **k: pytest.fail('external command'))
    with pytest.raises(harness.HarnessError):
        adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert before == [classification_digest(p) for p in (root, other)]
    assert not (harness._machine_state_base() / 'repository-state.json').exists()


@pytest.mark.parametrize('record', ['pointer', 'manifest'])
@pytest.mark.parametrize('case', ['symlink', 'mode', 'unreadable', 'invalid-utf8'])
def test_historical_metadata_rejects_unsafe_files(harness, tmp_path, monkeypatch, record, case):
    root, item, other, _, _, path = historical_metadata_fixture(harness, tmp_path)
    target = path if record == 'manifest' else other / 'active-manifest.json'
    if case == 'symlink':
        saved = tmp_path / 'PRIVATE_SENTINEL'
        saved.write_bytes(target.read_bytes())
        target.unlink()
        target.symlink_to(saved)
    elif case == 'mode':
        target.chmod(0o666)
    elif case == 'invalid-utf8':
        target.write_bytes(b'\xffPRIVATE_SENTINEL')
    else:
        original = Path.read_text
        def unreadable(self, *args, **kwargs):
            if self == target:
                raise PermissionError('PRIVATE_SENTINEL')
            return original(self, *args, **kwargs)
        monkeypatch.setattr(Path, 'read_text', unreadable)
    plan = classification_plan(harness, tmp_path, root, other)
    before = [classification_digest(p) for p in (root, other)]
    monkeypatch.setattr(harness, '_run_command', lambda *a, **k: pytest.fail('external command'))
    with pytest.raises(harness.HarnessError) as error:
        adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert 'PRIVATE_SENTINEL' not in str(error.value)
    assert before == [classification_digest(p) for p in (root, other)]
    assert not (harness._machine_state_base() / 'repository-state.json').exists()


def test_classification_preserves_multiple_states_and_binding(harness, tmp_path, monkeypatch):
    root, item, other, plan = classified_fixture(harness, tmp_path)
    before = [classification_digest(p) for p in (root, other)]
    monkeypatch.setattr(harness, '_run_command', lambda *a, **k: pytest.fail('external command'))
    result = adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert result['state_root'] == str(root)
    assert before == [classification_digest(p) for p in (root, other)]
    binding = (harness._machine_state_base() / 'repository-state.json').read_bytes()
    assert adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)['idempotent']
    assert (harness._machine_state_base() / 'repository-state.json').read_bytes() == binding


@pytest.mark.parametrize('removed_before_open', [False, True])
def test_classification_missing_selected_lock_has_no_state_effects(harness, tmp_path, monkeypatch, removed_before_open):
    root, item, other, plan = classified_fixture(harness, tmp_path)
    lock = root / 'promote.lock'
    if not removed_before_open:
        lock.unlink()
        plan = classification_plan(harness, tmp_path, root, other)
    before = [classification_digest(p) for p in (root, other)]
    original = harness._state_file_lock
    def open_lock(path, **kwargs):
        nonlocal before
        if path == lock and removed_before_open:
            lock.unlink()
            before = [classification_digest(p) for p in (root, other)]
        return original(path, **kwargs)
    monkeypatch.setattr(harness, '_state_file_lock', open_lock)
    monkeypatch.setattr(harness, '_run_command', lambda *a, **k: pytest.fail('external command'))
    with pytest.raises(harness.HarnessError) as error:
        adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert not lock.exists()
    assert before == [classification_digest(p) for p in (root, other)]
    assert not (harness._machine_state_base() / 'repository-state.json').exists()
    assert str(error.value) == 'Dev state requires its existing safe lock'


def test_unclassified_initialization_creates_selected_lock(harness):
    root = harness._machine_state_base() / 'new' / 'harness'
    assert not root.exists()
    adopt(harness, root)
    assert (root / 'promote.lock').is_file()
    assert harness.global_state_dir() == root


def rewrite_classification(path, change):
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data))


@pytest.mark.parametrize('case', ['missing', 'extra', 'duplicate', 'unknown-field', 'unknown-kind',
                                  'foreign', 'selected', 'evidence', 'inode', 'bool-device',
                                  'hash', 'artifacts', 'empty', 'duplicate-json-key', 'inside-state', 'symlink-plan'])
def test_classification_invalid_plan_has_no_state_effects(harness, tmp_path, case):
    root, item, other, plan = classified_fixture(harness, tmp_path)
    before = [classification_digest(p) for p in (root, other)]
    if case == 'duplicate-json-key':
        plan.write_text(plan.read_text()[:-1] + ',"roots":[]}')
    elif case == 'inside-state':
        inside = root / 'plan.json'
        inside.write_bytes(plan.read_bytes())
        plan = inside
        before = [classification_digest(p) for p in (root, other)]
    elif case == 'symlink-plan':
        alias = tmp_path / 'alias.json'
        alias.symlink_to(plan)
        plan = alias
    else:
        def mutate(p):
            e = p['roots'][1]
            if case == 'missing':
                p['roots'].pop()
            elif case == 'extra':
                p['roots'].append(dict(e, path=str(harness._machine_state_base() / 'absent' / 'harness')))
            elif case == 'duplicate':
                p['roots'].append(e)
            elif case == 'unknown-field':
                e['force'] = True
            elif case == 'unknown-kind':
                e['kind'] = 'unknown'
            elif case == 'foreign':
                p['repository'] = 'github.com/other/graf'
            elif case == 'selected':
                p['selected_root'] = str(other)
            elif case == 'evidence':
                e['evidence'] = ' '
            elif case == 'inode':
                e['inode'] += 1
            elif case == 'bool-device':
                e['device'] = True
            elif case == 'hash':
                e['tree_sha256'] = 'z' * 64
            elif case == 'artifacts':
                e['artifacts'] = [{}]
            elif case == 'empty':
                p['roots'] = []
        rewrite_classification(plan, mutate)
    with pytest.raises(harness.HarnessError):
        adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert before == [classification_digest(p) for p in (root, other)]
    assert not (harness._machine_state_base() / 'repository-state.json').exists()


@pytest.mark.parametrize('case', ['no-plan', 'missing-lock', 'symlink-lock', 'selected-symlink-lock', 'selected-unsafe-lock', 'bad-mode', 'recovery',
                                  'schema', 'runtime', 'missing-live-runtime', 'active'])
def test_classification_preserved_state_failures(harness, tmp_path, monkeypatch, case):
    import shutil
    root, item, other, plan = classified_fixture(harness, tmp_path)
    if case == 'missing-lock':
        (other / 'promote.lock').unlink()
    elif case == 'symlink-lock':
        (other / 'promote.lock').unlink()
        (other / 'promote.lock').symlink_to(tmp_path / 'outside')
    elif case == 'selected-symlink-lock':
        (root / 'promote.lock').unlink()
        (root / 'promote.lock').symlink_to(tmp_path / 'outside')
    elif case == 'selected-unsafe-lock':
        (root / 'promote.lock').chmod(0o666)
    elif case == 'bad-mode':
        (other / '.dev-boundary').chmod(0o666)
    elif case == 'recovery':
        (other / 'rollback-required.json').write_text('{}')
    elif case == 'schema':
        harness._write_json(other / 'schema-transition.json', {'phase': 'prepared'})
    elif case in ('runtime', 'missing-live-runtime', 'active'):
        shutil.copytree(root / 'manifests', other / 'manifests')
        shutil.copyfile(root / 'active-manifest.json', other / 'active-manifest.json')
        if case != 'missing-live-runtime':
            harness._write_json(other / 'runtime.json', {'source_sha': 'b' * 40 if case == 'runtime' else item['source_sha']})
        if case == 'active':
            monkeypatch.setattr(harness.GrafLocalAdapter, '_pid_owned', lambda *a: True)
    if case not in ('symlink-lock', 'selected-symlink-lock'):
        plan = classification_plan(harness, tmp_path, root, other)
    # Snapshot helper does not follow the intentionally unsafe lock symlink.
    before = [classification_digest(p) for p in (root, other)]
    with pytest.raises(harness.HarnessError):
        kwargs = {} if case == 'no-plan' else {'classification': plan}
        adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], **kwargs)
    assert before == [classification_digest(p) for p in (root, other)]
    assert not (harness._machine_state_base() / 'repository-state.json').exists()
    assert not (tmp_path / 'outside').exists()


@pytest.mark.parametrize('journal_root', ['selected', 'preserved'])
def test_classification_canonical_snapshot_and_completed_journal(harness, tmp_path, journal_root):
    root, item, other, plan = classified_fixture(harness, tmp_path)
    target = root if journal_root == 'selected' else other
    if journal_root == 'preserved':
        harness._write_json(other / 'manifests' / (item['manifest_id'] + '.json'), item)
        harness._write_json(other / 'active-manifest.json', {
            'schema_version': harness.POINTER_VERSION, 'manifest_id': item['manifest_id'], 'runtime_mode': 'metadata-only',
        })
    harness._write_json(target / 'schema-transition.json', {
        'schema_version': 'dev-schema-transition.v1', 'phase': 'complete', 'operation_id': 'upgrade-1',
        'previous': item, 'target': item, 'volumes': {'graf-dev-postgres-data': {}, 'graf-dev-minio-data': {}},
    })
    plan = classification_plan(harness, tmp_path, root, other)
    assert harness._classification_tree_digest(root) == classification_digest(root)
    before = [classification_digest(p) for p in (root, other)]
    adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert [classification_digest(p) for p in (root, other)] == before


def archived_fixture(harness, tmp_path, monkeypatch):
    import plistlib
    root, item, other, plan = classified_fixture(harness, tmp_path)
    git(harness._repo_root(), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        'commit', '--allow-empty', '-qm', 'Historical archive fixture')
    source_sha = git(harness._repo_root(), 'rev-parse', 'HEAD')
    archive = harness._machine_state_base() / 'archive' / 'harness'
    app = archive / 'artifacts' / 'dev-fixture' / 'GRAF Dev.app'
    (app / 'Contents').mkdir(parents=True)
    (app / 'Contents' / 'Info.plist').write_bytes(plistlib.dumps({
        'CFBundleIdentifier': harness.APP_BUNDLE_ID, 'GRAFSourceSHA': source_sha,
    }))
    facts = dict(path=app.relative_to(archive).as_posix(), source_sha=source_sha,
                 signing_identity='Historical Dev signer', designated_requirement='identifier pro.2brain.graf.dev',
                 entitlements_digest='sha256:' + '1' * 64)
    calls = []
    run_command = harness._run_command
    def verify(command, **kw):
        if command[0] == 'git':
            assert command[:3] == ['git', 'cat-file', '-e']
            return run_command(command, **kw)
        assert command[:4] == ['codesign', '--verify', '--deep', '--strict']
        calls.append(command)
        return ''
    monkeypatch.setattr(harness, '_run_command', verify)
    monkeypatch.setattr(harness.GrafLocalAdapter, '_measure_signed_app_identity',
                        lambda *a: tuple(facts[k] for k in ('signing_identity', 'designated_requirement', 'entitlements_digest')))
    plan = classification_plan(harness, tmp_path, root, other, archive)
    rewrite_classification(plan, lambda p: p['roots'][2].update(kind='artifact-only', artifacts=[dict(facts)]))
    return root, item, other, archive, app, facts, plan, calls


@pytest.mark.parametrize('case', ['valid', 'source', 'missing-commit', 'signature', 'unlisted', 'build', 'lock', 'no-evidence', 'no-apps',
                                  'outside-link', 'cycle-link', 'valid-link', 'extra-app', 'unknown-artifact-field'])
def test_classification_archived_apps_are_verified_and_never_registered(harness, tmp_path, monkeypatch, case):
    import plistlib
    root, item, other, archive, app, facts, plan, calls = archived_fixture(harness, tmp_path, monkeypatch)
    if case == 'source':
        (app / 'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier': harness.APP_BUNDLE_ID, 'GRAFSourceSHA': 'b' * 40}))
    elif case == 'missing-commit':
        facts['source_sha'] = 'b' * 40
        (app / 'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier': harness.APP_BUNDLE_ID, 'GRAFSourceSHA': 'b' * 40}))
        rewrite_classification(plan, lambda p: p['roots'][2]['artifacts'][0].update(source_sha='b' * 40))
    elif case == 'signature':
        monkeypatch.setattr(harness.GrafLocalAdapter, '_measure_signed_app_identity', lambda *a: ('wrong', 'wrong', 'sha256:' + '2' * 64))
    elif case == 'unlisted':
        (archive / 'runtime.json').write_text('{}')
    elif case == 'build':
        (app.parent / 'build').mkdir()
    elif case == 'lock':
        (archive / 'promote.lock').touch()
    elif case == 'outside-link':
        (app / 'Contents/link').symlink_to(tmp_path / 'outside')
    elif case == 'cycle-link':
        (app / 'Contents/link').symlink_to('link')
    elif case == 'valid-link':
        (app / 'Contents/link').symlink_to('Info.plist')
    elif case == 'extra-app':
        (archive / 'artifacts/other/GRAF Dev.app').mkdir(parents=True)
    rewrite_classification(plan, lambda p: p['roots'][2].update(tree_sha256=classification_digest(archive)))
    if case == 'no-evidence':
        rewrite_classification(plan, lambda p: p['roots'][2].update(evidence=''))
    elif case == 'no-apps':
        rewrite_classification(plan, lambda p: p['roots'][2].update(artifacts=[]))
    elif case == 'unknown-artifact-field':
        rewrite_classification(plan, lambda p: p['roots'][2]['artifacts'][0].update(force=True))
    before = [classification_digest(p) for p in (root, other, archive)]
    if case in ('valid', 'valid-link'):
        adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
        assert calls
        assert harness.global_state_dir() == root
    else:
        with pytest.raises(harness.HarnessError):
            adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
        assert not (harness._machine_state_base() / 'repository-state.json').exists()
    assert before == [classification_digest(p) for p in (root, other, archive)]
    assert not (archive / 'promote.lock').exists() or case == 'lock'


@pytest.mark.parametrize('change', ['tree', 'archive', 'build', 'build-link', 'metadata', 'new-root', 'plan', 'plan-inode', 'lock-inode', 'selected-lock-inode',
                                  'metadata-pointer', 'metadata-manifest', 'metadata-runtime', 'metadata-marker'])
def test_classification_real_wait_rechecks_complete_state(harness, tmp_path, monkeypatch, change):
    if change.startswith('metadata-'):
        root, item, other, _, _, manifest_path = historical_metadata_fixture(harness, tmp_path)
        plan = classification_plan(harness, tmp_path, root, other)
    elif change in ('archive', 'build', 'build-link'):
        root, item, other, archive, app, _, plan, _ = archived_fixture(harness, tmp_path, monkeypatch)
        if change != 'archive':
            build = app.parent / 'build'
            build.mkdir()
            (build / 'object').write_bytes(b'Never executed')
            (build / 'alias').symlink_to('object')
            rewrite_classification(plan, lambda p: p['roots'][2].update(
                build_archives=[build.relative_to(archive).as_posix()], tree_sha256=classification_digest(archive)))
    else:
        root, item, other, plan = classified_fixture(harness, tmp_path)
    ready, release, waiting = [tmp_path / n for n in ('ready', 'release', 'waiting')]
    locked_root = root if change == 'selected-lock-inode' else other
    inode = (locked_root / 'promote.lock').stat().st_ino
    holder = subprocess.Popen([sys.executable, '-c', '''
import fcntl,sys,time
from pathlib import Path
with Path(sys.argv[1]).open('r+') as f:
 fcntl.flock(f,fcntl.LOCK_EX); Path(sys.argv[2]).touch()
 while not Path(sys.argv[3]).exists(): time.sleep(.01)
''', str(locked_root / 'promote.lock'), str(ready), str(release)])
    process = None
    try:
        wait_file(ready, holder)
        process = child(harness, '''
from argparse import Namespace
import os
original=h.fcntl.flock
def observed(fd,mode):
 if os.fstat(fd).st_ino==p['inode']: Path(p['waiting']).touch()
 return original(fd,mode)
h.fcntl.flock=observed
h.operation_adopt_state(Namespace(state_root=Path(p['state']),expected_repository='github.com/example/graf',
 expected_active_sha='a'*40,expect_empty=False,confirm_repository_ownership=True,classification=Path(p['plan'])))
''', state=str(root), plan=str(plan), inode=inode, waiting=str(waiting))
        wait_file(waiting, process)
        assert process.poll() is None
        assert not (harness._machine_state_base() / 'repository-state.json').exists()
        if change == 'tree':
            (other / '.dev-boundary').write_text('changed while waiting')
        elif change == 'archive':
            (app / 'Contents/Info.plist').write_bytes(b'changed while waiting')
        elif change == 'build':
            (build / 'object').write_bytes(b'changed while waiting')
        elif change == 'build-link':
            (build / 'alias').unlink()
            (build / 'alias').symlink_to('./object')
        elif change == 'metadata':
            (other / '.dev-boundary').chmod(0o400)
        elif change in ('metadata-pointer', 'metadata-manifest'):
            path = other / 'active-manifest.json' if change == 'metadata-pointer' else manifest_path
            path.write_bytes(path.read_bytes() + b' ')
        elif change in ('metadata-runtime', 'metadata-marker'):
            (other / ('runtime.json' if change == 'metadata-runtime' else 'rollback-required.json')).write_text('{}')
        elif change == 'new-root':
            extra = harness._machine_state_base() / 'new' / 'harness'
            extra.mkdir(parents=True)
            (extra / 'promote.lock').touch()
        elif change == 'plan':
            plan.write_bytes(plan.read_bytes() + b' ')
        elif change == 'plan-inode':
            replacement = plan.with_suffix('.replacement')
            replacement.write_bytes(plan.read_bytes())
            replacement.replace(plan)
        elif change in ('lock-inode', 'selected-lock-inode'):
            (locked_root / 'promote.lock').rename(locked_root / 'previous.lock')
            (locked_root / 'promote.lock').touch()
        release.touch()
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode != 0, (stdout, stderr)
        assert not (harness._machine_state_base() / 'repository-state.json').exists()
    finally:
        release.touch()
        holder.wait(timeout=10)
        if process is not None and process.poll() is None:
            process.kill()
            process.communicate()


@pytest.mark.parametrize('after', [False, True])
def test_classification_crash_preserves_roots(harness, tmp_path, after):
    root, item, other, plan = classified_fixture(harness, tmp_path)
    before = [classification_digest(p) for p in (root, other)]
    process = child(harness, '''
from argparse import Namespace
import os
original=h._write_json
def interrupted(path,value):
 if p['after']: original(path,value)
 os._exit(9)
h._write_json=interrupted
h.operation_adopt_state(Namespace(state_root=Path(p['state']),expected_repository='github.com/example/graf',
 expected_active_sha='a'*40,expect_empty=False,confirm_repository_ownership=True,classification=Path(p['plan'])))
''', state=str(root), plan=str(plan), after=after)
    stdout, stderr = process.communicate(timeout=10)
    assert process.returncode == 9, (stdout, stderr)
    assert (harness._read_repository_binding() is not None) == after
    assert before == [classification_digest(p) for p in (root, other)]


@pytest.mark.parametrize('change', ['atime', 'symlink-race', 'replacement-race'])
def test_classification_plan_uses_nofollow_and_stable_identity(harness, tmp_path, monkeypatch, change):
    import os
    root, _, _, plan = classified_fixture(harness, tmp_path)
    baseline = harness._classification_input(plan)
    if change == 'atime':
        info = plan.stat()
        os.utime(plan, ns=(info.st_atime_ns - 10_000_000_000, info.st_mtime_ns))
        # utime changes ctime before the read, which is part of the new baseline.
        baseline = harness._classification_input(plan)
        assert harness._classification_input(plan) == baseline
        return
    original = harness.os.open
    def racing_open(path, flags, *args, **kwargs):
        if Path(path) == plan:
            assert flags & os.O_NOFOLLOW
            replacement = tmp_path / 'replacement.json'
            replacement.write_bytes(plan.read_bytes())
            if change == 'symlink-race':
                plan.unlink()
                plan.symlink_to(replacement)
            else:
                replacement.replace(plan)
        return original(path, flags, *args, **kwargs)
    monkeypatch.setattr(harness.os, 'open', racing_open)
    with pytest.raises(harness.HarnessError, match='invalid or changed classification plan'):
        harness._classification_input(plan)
    assert not (harness._machine_state_base() / 'repository-state.json').exists()


def test_classification_two_registrations_publish_only_one_root(harness, tmp_path):
    root, item, other, plan = classified_fixture(harness, tmp_path)
    # Both contenders have coherent historical operational state.
    import shutil
    shutil.copytree(root / 'manifests', other / 'manifests')
    for name in ('active-manifest.json', 'runtime.json'):
        shutil.copyfile(root / name, other / name)
    plan = classification_plan(harness, tmp_path, root, other)
    other_plan = tmp_path / 'other-plan.json'
    value = json.loads(plan.read_text())
    value['selected_root'] = str(other)
    for entry in value['roots']:
        entry['kind'] = 'selected' if entry['path'] == str(other) else 'preserved-state'
    other_plan.write_text(json.dumps(value))
    before = [classification_digest(p) for p in (root, other)]
    script = """
from argparse import Namespace
h.operation_adopt_state(Namespace(state_root=Path(p['state']),expected_repository='github.com/example/graf',
 expected_active_sha='a'*40,expect_empty=False,confirm_repository_ownership=True,classification=Path(p['plan'])))
"""
    processes = [child(harness, script, state=str(state), plan=str(path))
                 for state, path in ((root, plan), (other, other_plan))]
    try:
        for process in processes:
            process.communicate(timeout=10)
        assert sorted(p.returncode for p in processes) == [0, 1]
        assert harness.global_state_dir() in (root, other)
        assert before == [classification_digest(p) for p in (root, other)]
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()


@pytest.mark.parametrize('change', ['state', 'build', 'build-link', 'metadata-pointer', 'metadata-manifest', 'metadata-runtime', 'metadata-marker'])
def test_classification_rechecks_snapshot_immediately_before_publication(harness, tmp_path, monkeypatch, change):
    if change.startswith('metadata-'):
        root, item, other, _, _, manifest_path = historical_metadata_fixture(harness, tmp_path)
        plan = classification_plan(harness, tmp_path, root, other)
    else:
        root, item, other, plan = classified_fixture(harness, tmp_path)
    if change in ('build', 'build-link'):
        build = other / 'artifacts/fixture/build'
        build.mkdir(parents=True)
        (build.parent / 'GRAF Dev.app').mkdir()
        (build / 'object').write_bytes(b'Never executed')
        (build / 'alias').symlink_to('object')
        rewrite_classification(plan, lambda p: p['roots'][1].update(
            build_archives=[build.relative_to(other).as_posix()], tree_sha256=classification_digest(other)))
    original = harness._classification_preserved_state
    def changed_after_validation(path):
        original(path)
        if change == 'state':
            (path / '.dev-boundary').write_text('writer after validation')
        elif change == 'build':
            (build / 'object').write_bytes(b'writer after validation')
        elif change in ('metadata-pointer', 'metadata-manifest'):
            file = path / 'active-manifest.json' if change == 'metadata-pointer' else manifest_path
            file.write_bytes(file.read_bytes() + b' ')
        elif change in ('metadata-runtime', 'metadata-marker'):
            (path / ('runtime.json' if change == 'metadata-runtime' else 'rollback-required.json')).write_text('{}')
        else:
            (build / 'alias').unlink()
            (build / 'alias').symlink_to('./object')
    monkeypatch.setattr(harness, '_classification_preserved_state', changed_after_validation)
    with pytest.raises(harness.HarnessError, match='classified tree changed'):
        adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert not (harness._machine_state_base() / 'repository-state.json').exists()


@pytest.mark.parametrize('historical', [False, True])
def test_classification_failed_binding_write_preserves_roots(harness, tmp_path, monkeypatch, historical):
    if historical:
        root, item, other, _, _, _ = historical_metadata_fixture(harness, tmp_path)
        plan = classification_plan(harness, tmp_path, root, other)
    else:
        root, item, other, plan = classified_fixture(harness, tmp_path)
    before = [classification_digest(p) for p in (root, other)]
    def failed_write(*args):
        raise OSError('fixture publication failure')
    monkeypatch.setattr(harness, '_write_json', failed_write)
    with pytest.raises(OSError, match='fixture publication failure'):
        adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert not (harness._machine_state_base() / 'repository-state.json').exists()
    assert before == [classification_digest(p) for p in (root, other)]


@pytest.mark.parametrize('case', ['outside-and-back', 'dotdot-after-directory-link'])
def test_classification_rejects_every_external_symlink_step(harness, tmp_path, monkeypatch, case):
    import os
    root, item, other, archive, app, _, plan, _ = archived_fixture(harness, tmp_path, monkeypatch)
    outside = tmp_path / 'outside-directory'
    outside.mkdir()
    (outside / 'return').symlink_to(app / 'Contents', target_is_directory=True)
    target = os.path.relpath(outside / 'return', app / 'Contents')
    if case == 'outside-and-back':
        (app / 'Contents/link').symlink_to(target + '/Info.plist')
    else:
        (app / 'Contents/directory-link').symlink_to(target, target_is_directory=True)
        (app / 'Contents/link').symlink_to('directory-link/../Contents/Info.plist')
    # The final object is internal in both cases; the path taken is forbidden.
    assert (app / 'Contents/link').resolve(strict=True) == app / 'Contents/Info.plist'
    rewrite_classification(plan, lambda p: p['roots'][2].update(tree_sha256=classification_digest(archive)))
    before = [classification_digest(p) for p in (root, other, archive)]
    with pytest.raises(harness.HarnessError, match='symlink leaves its archived app'):
        adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert before == [classification_digest(p) for p in (root, other, archive)]
    assert not (harness._machine_state_base() / 'repository-state.json').exists()


def test_classification_framework_links_remain_supported(harness, tmp_path, monkeypatch):
    root, item, other, archive, app, _, plan, _ = archived_fixture(harness, tmp_path, monkeypatch)
    framework = app / 'Contents/Frameworks/Fixture.framework'
    (framework / 'Versions/A').mkdir(parents=True)
    (framework / 'Versions/A/Fixture').write_bytes(b'framework fixture')
    (framework / 'Versions/Current').symlink_to('A', target_is_directory=True)
    (framework / 'Fixture').symlink_to('Versions/Current/Fixture')
    # '..' must follow the actual directory symlink, not lexical simplification.
    (framework / 'Alias').symlink_to('Versions/Current/../A/Fixture')
    rewrite_classification(plan, lambda p: p['roots'][2].update(tree_sha256=classification_digest(archive)))
    before = [classification_digest(p) for p in (root, other, archive)]
    adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert before == [classification_digest(p) for p in (root, other, archive)]


def test_classification_rejects_preserved_pointer_manifest_disagreement(harness, tmp_path):
    root, item, other, plan = classified_fixture(harness, tmp_path)
    alternate = dict(item, manifest_id='dev-alternate')
    harness._write_json(other / 'manifests' / (item['manifest_id'] + '.json'), alternate)
    harness._write_json(other / 'active-manifest.json', {
        'schema_version': harness.POINTER_VERSION, 'manifest_id': item['manifest_id'], 'runtime_mode': 'live',
    })
    harness._write_json(other / 'runtime.json', {'source_sha': item['source_sha'], 'manifest_id': alternate['manifest_id']})
    plan = classification_plan(harness, tmp_path, root, other)
    before = [classification_digest(p) for p in (root, other)]
    with pytest.raises(harness.HarnessError, match='preserved.*manifest identity'):
        adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert before == [classification_digest(p) for p in (root, other)]
    assert not (harness._machine_state_base() / 'repository-state.json').exists()


@pytest.mark.parametrize('kind', ['artifact-only', 'preserved-state'])
def test_classification_preserves_explicit_build_archives(harness, tmp_path, monkeypatch, kind):
    root, item, other, archive, app, _, plan, calls = archived_fixture(harness, tmp_path, monkeypatch)
    owner = archive if kind == 'artifact-only' else other
    apps = [app] if kind == 'artifact-only' else [other / 'artifacts' / name / 'GRAF Dev.app' for name in ('first', 'second')]
    builds = []
    for bundle in apps:
        bundle.mkdir(parents=True, exist_ok=True)
        build = bundle.parent / 'build'
        (build / 'versions/current').mkdir(parents=True)
        (build / 'versions/current/object').write_bytes(b'Untrusted archive: never execute or import')
        (build / 'current').symlink_to('versions/current', target_is_directory=True)
        (build / 'object').symlink_to('current/object')
        (build / 'alias').symlink_to('current/../current/object')
        builds.append(build.relative_to(owner).as_posix())
    rewrite_classification(plan, lambda p: [e.update(build_archives=builds, tree_sha256=classification_digest(owner))
                                            for e in p['roots'] if e['path'] == str(owner)])
    before = [classification_digest(p) for p in (root, other, archive)]
    adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert before == [classification_digest(p) for p in (root, other, archive)]
    assert harness.global_state_dir() == root
    assert not (archive / 'promote.lock').exists()
    assert calls  # Only the separately listed app was verified, never a build binary.


@pytest.mark.parametrize('case', [
    'not-list', 'duplicate', 'absolute-path', 'dot-path', 'dotdot', 'app-boundary',
    'missing-app', 'boundary-link', 'absolute-link', 'cross-build', 'cross-app',
    'cross-root', 'outside-and-back', 'broken', 'cycle', 'special', 'mode', 'unreadable',
])
def test_classification_rejects_unsafe_build_archives(harness, tmp_path, monkeypatch, case):
    import os
    root, item, other, archive, app, _, plan, _ = archived_fixture(harness, tmp_path, monkeypatch)
    build = app.parent / 'build'
    build.mkdir()
    target = build / 'object'
    target.write_bytes(b'Unknown provenance; never execute')
    values = [build.relative_to(archive).as_posix()]
    if case == 'not-list':
        values = values[0]
    elif case == 'duplicate':
        values *= 2
    elif case == 'absolute-path':
        values = [str(build)]
    elif case == 'dot-path':
        values = ['artifacts/./dev-fixture/build']
    elif case == 'dotdot':
        values = ['artifacts/dev-fixture/../dev-fixture/build']
    elif case == 'app-boundary':
        values = [app.relative_to(archive).as_posix()]
    elif case == 'missing-app':
        app.rename(app.with_name('Unlisted.app'))
    elif case == 'boundary-link':
        build.rename(app.parent / 'saved-build')
        build.symlink_to('saved-build', target_is_directory=True)
    elif case == 'special':
        os.mkfifo(build / 'fifo')
    elif case == 'mode':
        target.chmod(0o666)
    elif case != 'unreadable':
        if case == 'absolute-link':
            destination = str(target)
        elif case == 'cross-build':
            second = archive / 'artifacts/second/build'
            second.mkdir(parents=True)
            (second.parent / 'GRAF Dev.app').mkdir()
            (second / 'object').write_bytes(b'Other build')
            values.append(second.relative_to(archive).as_posix())
            destination = '../../second/build/object'
        elif case == 'cross-app':
            destination = '../GRAF Dev.app/Contents/Info.plist'
        elif case == 'cross-root':
            destination = os.path.relpath(other / '.dev-boundary', build)
        elif case == 'outside-and-back':
            outside = tmp_path / 'outside'
            outside.mkdir()
            (outside / 'return').symlink_to(build, target_is_directory=True)
            destination = os.path.relpath(outside / 'return/object', build)
        else:
            destination = 'missing' if case == 'broken' else 'link'
        (build / 'link').symlink_to(destination)
    rewrite_classification(plan, lambda p: p['roots'][2].update(
        build_archives=values, tree_sha256=classification_digest(archive)))
    before = [classification_digest(p) for p in (root, other, archive)]
    if case == 'unreadable':
        original_open = harness.os.open
        def unreadable(path, *a, **kw):
            if Path(path) == target:
                raise PermissionError('fixture unreadable build object')
            return original_open(path, *a, **kw)
        monkeypatch.setattr(harness.os, 'open', unreadable)
    with pytest.raises(harness.HarnessError):
        adopt(harness, root, expect_empty=False, expected_active_sha=item['source_sha'], classification=plan)
    assert before == [classification_digest(p) for p in (root, other, archive)]
    assert not (harness._machine_state_base() / 'repository-state.json').exists()
    assert not (archive / 'promote.lock').exists()
