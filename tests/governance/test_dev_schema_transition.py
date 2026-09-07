"""Cold schema transaction: graph, crash recovery and data-loss boundaries."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("schema_harness", ROOT / "scripts/dev-harness.py")
h = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(h)


def manifests(tmp_path):
    previous = h.build_manifest("a" * 40, "249", "test", "old", tmp_path)
    target = h.build_manifest("b" * 40, "249", "test", "merged", tmp_path)
    for manifest in (previous, target):
        for key in ("database", "storage", "temporal", "migration"):
            manifest["components"][key]["digest"] = "sha256:" + "1" * 64
    return previous, target


def transaction(tmp_path):
    previous, target = manifests(tmp_path)
    return {"schema_version": "dev-schema-transition.v1", "operation_id": "upgrade-1", "phase": "prepared", "previous": previous, "target": target, "volumes": {"graf-dev-postgres-data": {}, "graf-dev-minio-data": {}}, "snapshots": {}, "app_was_running": False}


def test_merge_upgrade_includes_the_other_branch():
    graph = {"heads": ["merged"], "parents": {"root": [], "old": ["root"], "other": ["root"], "merged": ["old", "other"]}}
    assert h._schema_upgrade_path(graph, "old", "merged") == ["merged", "other"]
    for current, target in (("unknown", "merged"), ("merged", "old"), ("old", "old")):
        with pytest.raises(h.HarnessError):
            h._schema_upgrade_path(graph, current, target)
    for bad in ({**graph, "heads": ["old", "other"]}, {**graph, "parents": {**graph["parents"], "orphan": []}}, {"heads": ["merged"], "parents": {"old": ["merged"], "merged": ["old"]}}):
        with pytest.raises(h.HarnessError):
            h._schema_upgrade_path(bad, "old", "merged")


@pytest.mark.parametrize("phase", ["prepared", "migrating", "restoring", "writers_may_have_started", "verified"])
def test_process_death_keeps_journal_and_blocks_normal_operations(tmp_path, phase, monkeypatch):
    journal = transaction(tmp_path)
    source = f'''import importlib.util, json, os
from pathlib import Path
s=importlib.util.spec_from_file_location('h', {str(ROOT / 'scripts/dev-harness.py')!r})
h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
a=h.GrafLocalAdapter(Path({str(ROOT)!r}),Path({str(tmp_path)!r}))
a._schema_phase(json.loads({json.dumps(journal)!r}),{phase!r})
os._exit(19)
'''
    assert subprocess.run([sys.executable, "-c", source], env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}).returncode == 19
    assert h._read_schema_transition(tmp_path)["phase"] == phase
    monkeypatch.setattr(h, "state_dir", lambda **kw: tmp_path)
    assert h.operation_status(type("Args", (), {})())["status"] == "rollback_required"
    for function, args in ((h.operation_smoke, {"live": True, "fixture": False}), (h.operation_rollback, {"live": True}), (h.operation_reset_data, {"confirm_dev_reset": True, "dry_run": False})):
        with pytest.raises(h.HarnessError, match="unfinished"):
            function(type("Args", (), args)())
    with pytest.raises(h.HarnessError, match="startup blocked"):
        h._schema_start_guard(tmp_path, "a" * 40)


def recovery_adapter(tmp_path, monkeypatch, journal):
    adapter = h.GrafLocalAdapter(ROOT, tmp_path)
    calls = []
    for method in ("_schema_stop", "_schema_check_volumes", "_schema_start_database", "_install_app", "_launch_dev_app"):
        monkeypatch.setattr(adapter, method, lambda *a, _m=method: calls.append(_m))
    monkeypatch.setattr(adapter, "_schema_revision", lambda manifest: manifest["migration_head"])
    monkeypatch.setattr(adapter, "_schema_compose", lambda *a: "temporal\ntemporal_visibility\ntwobrain_rec")
    monkeypatch.setattr(adapter, "_env", lambda manifest: {})
    monkeypatch.setattr(adapter, "smoke", lambda manifest: {"backend_health": "pass"})
    monkeypatch.setattr(adapter, "_assert_transition_smoke", lambda *a, **kw: None)
    def start(*args):
        assert h._read_schema_transition(tmp_path)["phase"] in {"writers_may_have_started", "previous_writers_may_have_started"}
        calls.append("start")
    monkeypatch.setattr(adapter, "_schema_start_authorized", start)
    monkeypatch.setattr(adapter, "_schema_restore_pair", lambda j: calls.append("restore"))
    adapter._schema_phase(journal, journal["phase"])
    return adapter, calls


@pytest.mark.parametrize("phase,restore,final", [("prepared", False, "recovered"), ("snapshots_complete", False, "recovered"), ("migrating", True, "recovered"), ("migrated", True, "recovered"), ("restoring", True, "recovered"), ("writers_may_have_started", False, "complete"), ("verified", False, "complete"), ("previous_writers_may_have_started", False, "recovered")])
def test_recovery_obeys_durable_writer_boundary(tmp_path, monkeypatch, phase, restore, final):
    journal = transaction(tmp_path); journal["phase"] = phase
    adapter, calls = recovery_adapter(tmp_path, monkeypatch, journal)
    adapter._schema_resume(journal, previous_adapter=adapter)
    assert ("restore" in calls) == restore
    assert h._read_schema_transition(tmp_path)["phase"] == final
    assert h._load_active(tmp_path)["source_sha"] == journal["target" if final == "complete" else "previous"]["source_sha"]


def test_publication_failure_cannot_allow_snapshot_rollback(tmp_path, monkeypatch):
    journal = transaction(tmp_path); journal["phase"] = "writers_may_have_started"
    adapter, calls = recovery_adapter(tmp_path, monkeypatch, journal)
    monkeypatch.setattr(h, "_publish_active", lambda *a: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError):
        adapter._schema_resume(journal, previous_adapter=adapter)
    assert "restore" not in calls
    assert h._read_schema_transition(tmp_path)["phase"] == "writers_may_have_started"


def test_restore_validates_both_before_deletion_and_retries_whole_pair(tmp_path, monkeypatch):
    journal = transaction(tmp_path)
    journal["snapshots"] = dict.fromkeys(journal["volumes"], {"sha256": "test"})
    adapter = h.GrafLocalAdapter(ROOT, tmp_path)
    monkeypatch.setattr(adapter, "_schema_check_volumes", lambda j: None)
    calls = []
    def tool(j, volume, action):
        calls.append((volume, action))
        if action == "restore" and volume.endswith("minio-data"):
            raise h.HarnessError("injected second-volume failure")
    monkeypatch.setattr(adapter, "_schema_volume_tool", tool)
    with pytest.raises(h.HarnessError):
        adapter._schema_restore_pair(journal)
    assert [a for _, a in calls] == ["verify", "verify", "restore", "restore"]
    assert h._read_schema_transition(tmp_path)["phase"] == "restoring"
    calls.clear()
    monkeypatch.setattr(adapter, "_schema_volume_tool", lambda j, v, a: calls.append((v, a)))
    adapter._schema_restore_pair(journal)
    assert [a for _, a in calls] == ["verify", "verify", "restore", "restore"]


def test_corrupt_journal_never_falls_back_to_active(tmp_path):
    (tmp_path / "schema-transition.json").write_text("{}")
    with pytest.raises(h.HarnessError):
        h._assert_no_schema_transition(tmp_path)


def test_stateful_image_change_refused_before_stop(tmp_path, monkeypatch):
    previous, target = manifests(tmp_path)
    target["components"]["database"]["digest"] = "sha256:" + "2" * 64
    adapter = h.GrafLocalAdapter(ROOT, tmp_path)
    monkeypatch.setattr(adapter, "_schema_stop", lambda *a: pytest.fail("must not stop"))
    with pytest.raises(h.HarnessError, match="stateful images"):
        adapter._promote_schema(previous, target, adapter)
    assert not (tmp_path / "schema-transition.json").exists()


def volume_tool(tmp_path, action, expected=None):
    volume, backup = tmp_path / 'volume', tmp_path / 'backup'
    volume.mkdir(exist_ok=True); backup.mkdir(exist_ok=True)
    code = h.SCHEMA_VOLUME_TOOL.replace("pathlib.Path('/volume'), pathlib.Path('/backup')", f"pathlib.Path({str(volume)!r}), pathlib.Path({str(backup)!r})").replace('os.sync()', 'None')
    return subprocess.run([sys.executable, '-c', code, action, 'fixture', json.dumps(expected)], capture_output=True, text=True)


def test_archive_round_trip_preserves_tree_and_removes_new_files(tmp_path):
    volume = tmp_path / 'volume'; volume.mkdir()
    (volume / 'nested').mkdir(mode=0o700)
    (volume / 'nested' / 'control').write_text('synthetic-before')
    (volume / 'nested' / 'control').chmod(0o600)
    snapshot = volume_tool(tmp_path, 'snapshot')
    assert snapshot.returncode == 0, snapshot.stderr
    receipt = json.loads(snapshot.stdout)
    (volume / 'nested' / 'control').write_text('after')
    (volume / 'new').write_text('new')
    restored = volume_tool(tmp_path, 'restore', receipt)
    assert restored.returncode == 0, restored.stderr
    assert (volume / 'nested' / 'control').read_text() == 'synthetic-before'
    assert not (volume / 'new').exists()
    assert (volume / 'nested' / 'control').stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize('kind', ['traversal', 'symlink', 'hardlink', 'duplicate', 'file_parent'])
def test_unsafe_archive_rejected_before_deleting_data(tmp_path, kind):
    import hashlib
    import tarfile
    volume = tmp_path / 'volume'; volume.mkdir()
    (volume / 'keep').write_text('untouched')
    backup = tmp_path / 'backup'; backup.mkdir()
    archive = backup / 'fixture.tar'
    with tarfile.open(archive, 'w') as tar:
        root = tarfile.TarInfo('.'); root.type = tarfile.DIRTYPE; tar.addfile(root)
        entry = tarfile.TarInfo('../escape' if kind == 'traversal' else 'entry')
        if kind in {'symlink', 'hardlink'}:
            entry.type = tarfile.SYMTYPE if kind == 'symlink' else tarfile.LNKTYPE
            entry.linkname = '/outside'
        tar.addfile(entry)
        if kind == 'duplicate': tar.addfile(entry)
        if kind == 'file_parent': tar.addfile(tarfile.TarInfo('entry/child'))
    receipt = {'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'tree_sha256': 'invalid', 'bytes': 0}
    assert volume_tool(tmp_path, 'restore', receipt).returncode != 0
    assert (volume / 'keep').read_text() == 'untouched'


def test_corrupt_pair_does_not_restore_either_volume(tmp_path, monkeypatch):
    journal = transaction(tmp_path)
    journal['snapshots'] = dict.fromkeys(journal['volumes'], {'sha256': 'test'})
    adapter = h.GrafLocalAdapter(ROOT, tmp_path)
    monkeypatch.setattr(adapter, '_schema_check_volumes', lambda j: None)
    calls = []
    def tool(j, v, action):
        calls.append(action)
        if len(calls) == 2: raise h.HarnessError('corrupt second archive')
    monkeypatch.setattr(adapter, '_schema_volume_tool', tool)
    with pytest.raises(h.HarnessError): adapter._schema_restore_pair(journal)
    assert calls == ['verify', 'verify']


@pytest.mark.parametrize('fault', ['image', 'volume_owner', 'unexpected_mount', 'external_enabled', 'missing_stateful', 'running_when_cold', 'wrong_volume', 'bind_mount', 'no_mount', 'nested_mount', 'pgdata', 'minio_command', 'subpath', 'subpath_source', 'valid'])
def test_observed_ownership_and_external_work_fail_before_mutation(tmp_path, monkeypatch, fault):
    previous, _ = manifests(tmp_path)
    adapter = h.GrafLocalAdapter(ROOT, tmp_path)
    names = {'graf-dev-postgres-data': 'rec-postgres-dev-data', 'graf-dev-minio-data': 'rec-minio-dev-data'}
    volumes = {n: {'Name': n, 'Driver': 'local', 'Options': {}, 'Mountpoint': '/var/lib/docker/volumes/' + n + '/_data', 'Labels': {'com.docker.compose.project': 'graf-dev', 'com.docker.compose.volume': key}} for n, key in names.items()}
    containers = {}
    for service in ('rec-postgres', 'rec-minio', 'rec-temporal'):
        containers[service] = {'Image': previous['components'][h.COMPOSE_IMAGE_COMPONENTS[service][0]]['digest'], 'State': {'Running': True}, 'Config': {'Labels': {'com.docker.compose.project': 'graf-dev', 'com.docker.compose.service': service}}, 'Mounts': []}
    containers['rec-postgres']['Config']['Env'] = ['PGDATA=/var/lib/postgresql/data']
    containers['rec-minio']['Config']['Cmd'] = ['server', '/data', '--console-address', ':9001']
    containers['rec-postgres']['Mounts'] = [{'Type': 'volume', 'Name': 'graf-dev-postgres-data', 'Source': '/var/lib/docker/volumes/graf-dev-postgres-data/_data', 'Destination': '/var/lib/postgresql/data'}]
    containers['rec-minio']['Mounts'] = [{'Type': 'volume', 'Name': 'graf-dev-minio-data', 'Source': '/var/lib/docker/volumes/graf-dev-minio-data/_data', 'Destination': '/data'}]
    if fault == 'subpath': containers['rec-minio']['HostConfig'] = {'Mounts': [{'Target': '/data', 'VolumeOptions': {'Subpath': 'current'}}]}
    if fault == 'subpath_source': containers['rec-minio']['Mounts'][0]['Source'] += '/current'
    if fault == 'nested_mount': containers['rec-minio']['Mounts'].append({'Type': 'bind', 'Destination': '/data/hidden'})
    if fault == 'pgdata': containers['rec-postgres']['Config']['Env'] = ['PGDATA=/elsewhere']
    if fault == 'minio_command': containers['rec-minio']['Config']['Cmd'] = ['server', '/elsewhere']
    if fault == 'wrong_volume': containers['rec-minio']['Mounts'][0]['Name'] = 'unrelated'
    if fault == 'bind_mount': containers['rec-minio']['Mounts'][0]['Type'] = 'bind'
    if fault == 'no_mount': containers['rec-minio']['Mounts'] = []
    if fault == 'image': containers['rec-postgres']['Image'] = 'sha256:' + '9' * 64
    if fault == 'volume_owner': volumes['graf-dev-minio-data']['Labels']['com.docker.compose.project'] = 'other'
    if fault == 'unexpected_mount': containers['rec-postgres']['Config']['Labels']['com.docker.compose.project'] = 'other'
    if fault == 'missing_stateful': del containers['rec-temporal']
    if fault == 'external_enabled':
        containers['api'] = {'Image': previous['components']['backend']['digest'], 'State': {'Running': True}, 'Config': {'Labels': {'com.docker.compose.project': 'graf-dev', 'com.docker.compose.service': 'api'}, 'Env': ['TWOBRAIN_OUTCOME_GENERATION_ENABLED=true']}}
    monkeypatch.setattr(adapter, '_schema_container_ids', lambda **kw: list(containers))
    def command(args, **kw):
        if args[:3] == ['docker', 'volume', 'inspect']: return json.dumps([volumes[args[3]]])
        if args[:2] == ['docker', 'inspect']: return json.dumps([containers[args[2]]])
        pytest.fail('must not mutate Docker')
    monkeypatch.setattr(h, '_run_command', command)
    if fault == 'valid':
        assert set(adapter._schema_inventory(previous)) == set(volumes)
    else:
        with pytest.raises(h.HarnessError): adapter._schema_inventory(previous, cold=fault == 'running_when_cold')


def test_observed_multiple_database_heads_are_not_accepted(tmp_path, monkeypatch):
    adapter = h.GrafLocalAdapter(ROOT, tmp_path)
    monkeypatch.setattr(adapter, '_schema_compose', lambda *a: 'first\nsecond')
    with pytest.raises(h.HarnessError, match='one observed'): adapter._schema_revision({})


@pytest.mark.parametrize('failure_phase,restores', [('migrating', True), ('migrated', True), ('writers_may_have_started', False), ('verified', False)])
def test_promote_failure_never_enters_old_compensation_after_writers(tmp_path, monkeypatch, failure_phase, restores):
    previous, target = manifests(tmp_path)
    adapter = h.GrafLocalAdapter(ROOT, tmp_path)
    volumes = dict.fromkeys(('graf-dev-postgres-data', 'graf-dev-minio-data'), {})
    h._write_json(adapter._runtime_record(), {'source_sha': previous['source_sha']})
    monkeypatch.setattr(adapter, '_schema_revision', lambda m: m['migration_head'])
    monkeypatch.setattr(adapter, '_checkout_adapter', lambda *a: adapter)
    monkeypatch.setattr(adapter, '_checked_app_bundle', lambda *a: None)
    monkeypatch.setattr(adapter, '_schema_graph', lambda *a: ['merged'])
    monkeypatch.setattr(adapter, '_schema_inventory', lambda *a, **kw: volumes)
    monkeypatch.setattr(adapter, '_schema_check_volumes', lambda *a: None)
    monkeypatch.setattr(adapter, '_app_is_running', lambda *a: False)
    monkeypatch.setattr(adapter, '_schema_volume_tool', lambda *a: {'sha256': 'fixture'})
    for method in ('_schema_stop', '_schema_start_database', '_schema_compose', '_install_app', '_launch_dev_app', '_assert_transition_smoke'):
        monkeypatch.setattr(adapter, method, lambda *a, **kw: None)
    monkeypatch.setattr(adapter, 'smoke', lambda *a: {'backend_health': 'pass'})
    calls = []
    monkeypatch.setattr(adapter, '_schema_resume', lambda *a, **kw: calls.append('restore'))
    monkeypatch.setattr(adapter, '_mark_rollback_required', lambda *a: calls.append('blocked'))
    def start(*a):
        assert h._read_schema_transition(tmp_path)['phase'] == 'writers_may_have_started'
        calls.append('start')
    monkeypatch.setattr(adapter, '_schema_start_authorized', start)
    original_phase = adapter._schema_phase
    def phase(j, value):
        original_phase(j, value)
        if value == failure_phase: raise h.HarnessError('injected interruption')
    monkeypatch.setattr(adapter, '_schema_phase', phase)
    with pytest.raises(h.HarnessError): adapter._promote_schema(previous, target, adapter)
    assert ('restore' in calls) == restores
    assert ('blocked' in calls) != restores
    if failure_phase == 'writers_may_have_started': assert 'start' not in calls


@pytest.mark.parametrize('release', [False, True])
def test_pipe_gate_prevents_unregistered_startup(tmp_path, release):
    import time
    marker = tmp_path / 'started'
    script = tmp_path / 'startup.sh'
    script.write_text('touch "' + str(marker) + '"\n')
    read_fd, write_fd = os.pipe()
    child = subprocess.Popen([sys.executable, '-c', h.SCHEMA_STARTUP_GATE, str(read_fd), str(script)], pass_fds=(read_fd,))
    os.close(read_fd)
    try:
        time.sleep(0.15)
        assert not marker.exists()
        if release: os.write(write_fd, b'1')
    finally:
        os.close(write_fd)
    assert child.wait(timeout=5) == (0 if release else 1)
    assert marker.exists() == release


def test_receipt_failure_never_releases_backend(tmp_path, monkeypatch):
    import time
    journal = transaction(tmp_path)
    adapter = h.GrafLocalAdapter(ROOT, tmp_path)
    adapter._schema_operation = journal['operation_id']
    adapter._schema_phase(journal, 'writers_may_have_started')
    marker = tmp_path / 'started'
    script = tmp_path / 'startup.sh'; script.write_text('touch "' + str(marker) + '"\n')
    adapter.start_script = script
    monkeypatch.setattr(adapter, '_runtime_definition_digest', lambda: 'sha256:' + '1' * 64)
    original_popen = subprocess.Popen
    children = []
    def spawn(*a, **kw):
        child = original_popen(*a, **kw); children.append(child); return child
    monkeypatch.setattr(h.subprocess, 'Popen', spawn)
    monkeypatch.setattr(h, '_write_json', lambda *a: (_ for _ in ()).throw(OSError('disk full')))
    with pytest.raises(OSError): adapter._start_backend(journal['target'], os.environ.copy())
    assert children[0].wait(timeout=5) == 1
    assert not marker.exists()


def test_startup_rejects_an_alternate_state_directory(tmp_path):
    with pytest.raises(h.HarnessError, match='repository-global'):
        h._schema_start_guard(tmp_path, 'b' * 40)


def test_startup_refuses_orphaned_controller(tmp_path, monkeypatch):
    journal = transaction(tmp_path)
    adapter = h.GrafLocalAdapter(ROOT, tmp_path)
    journal.update(controller_pid=os.getpid(), controller_start=adapter._process_start_token(os.getpid()))
    adapter._schema_phase(journal, 'writers_may_have_started')
    monkeypatch.setenv('GRAF_DEV_SCHEMA_CONTROLLER_PID', str(os.getpid()))
    monkeypatch.setenv('GRAF_DEV_SCHEMA_OPERATION', journal['operation_id'])
    monkeypatch.setattr(h, 'state_dir', lambda **kw: tmp_path)
    monkeypatch.setattr(h.GrafLocalAdapter, '_pid_alive', lambda *a: False)
    with pytest.raises(h.HarnessError, match='startup blocked'):
        h._schema_start_guard(tmp_path, journal['target']['source_sha'])
