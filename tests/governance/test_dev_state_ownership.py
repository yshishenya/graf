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
