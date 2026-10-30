"""Concrete Docker inventory and owned subprocess lifetime, without product writes."""

import asyncio
import copy
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from twobrain_rec_server.product_analytics import activation_operator as operator
from twobrain_rec_server.product_analytics.activation_fence import ActivationHold, activation_fence


@pytest.fixture
def fence(tmp_path):
    directory = tmp_path / "operator"
    directory.mkdir(mode=0o700)
    (directory / "activation.lock").write_bytes(b"lock")
    (directory / "activation.lock").chmod(0o600)
    with activation_fence(
        directory / "state.json", owner_uid=os.geteuid(), exclusive=True, readonly=False
    ) as value:
        value.revoke()
        yield value


def inventory():
    rows = []
    for index, (service, names) in enumerate(operator.SERVICE_NETWORKS.items()):
        running = service in operator.REQUIRED_WRITERS | operator.INFRASTRUCTURE
        rows.append(
            dict(
                id=f"{index + 1:064x}",
                service=service,
                project="synthetic",
                oneoff="False",
                state=dict(
                    status="running" if running else "exited",
                    running=running,
                    restarting=False,
                    paused=False,
                    pid=123 if running else 0,
                    exit=0,
                ),
                networks={
                    n: {"NetworkID": f"{9 if n.endswith('media-private') else 8:064x}"}
                    for n in names
                },
            )
        )
    networks = [
        dict(
            id=f"{i:064x}",
            name=name,
            internal=internal,
            project="synthetic",
            containers={
                r["id"]: {} for r in rows if r["state"]["running"] and name in r["networks"]
            },
        )
        for i, name, internal in [
            (8, "twobrain-rec-private", False),
            (9, "twobrain-rec-media-private", True),
        ]
    ]
    return rows, networks


@pytest.mark.parametrize(
    "change",
    [
        "good",
        "optional_absent",
        "bootstrap_absent",
        "optional_created",
        "required_absent",
        "required_created",
        "dead",
        "removing",
        "initializer_failed",
        "duplicate",
        "foreign_network",
        "wrong_network",
        "oneoff",
    ],
)
def test_concrete_inventory_matrix(change):
    rows, networks = inventory()
    optional = next(r for r in rows if r["service"] == "rec-maintenance")
    required = next(r for r in rows if r["service"] == "rec-api")
    if change == "optional_absent":
        rows.remove(optional)
    if change == "bootstrap_absent":
        rows.remove(next(r for r in rows if r["service"] == "rec-db-runtime-bootstrap"))
    if change == "optional_created":
        optional["state"]["status"] = "created"
        optional["networks"] = {}
    if change == "required_absent":
        rows.remove(required)
    if change == "required_created":
        required["state"].update(status="created", running=False, pid=0)
    if change in {"dead", "removing"}:
        optional["state"]["status"] = change
    if change == "initializer_failed":
        next(r for r in rows if r["service"] == "rec-migrate")["state"]["exit"] = 1
    if change == "duplicate":
        rows.append(copy.deepcopy(optional))
    if change == "foreign_network":
        networks[0]["containers"]["f" * 64] = {}
    if change == "wrong_network":
        optional["networks"] = {"unexpected": {}}
    if change == "oneoff":
        optional["oneoff"] = "True"
    if change in {"good", "optional_absent", "bootstrap_absent", "optional_created"}:
        operator._validate_inventory(
            rows, networks, project="synthetic", postal_network="postal-network", stopped=False
        )
    else:
        with pytest.raises(ActivationHold):
            operator._validate_inventory(
                rows, networks, project="synthetic", postal_network="postal-network", stopped=False
            )


def test_stop_uses_one_fixed_command_and_rechecks_ids_and_revocation(fence, tmp_path, monkeypatch):
    async def run(replace=False):
        rows, networks = inventory()
        before = copy.deepcopy(rows)
        calls = []

        async def command(argv, *, deadline):
            calls.append(argv)
            assert deadline - time.monotonic() <= 120
            if "stop" in argv:
                assert set(argv[argv.index("stop") + 1 :]) == operator.WRITERS
                for row in rows:
                    if row["service"] in operator.WRITERS:
                        row["state"].update(status="exited", running=False, pid=0, exit=137)
                for net in networks:
                    net["containers"] = {
                        r["id"]: {}
                        for r in rows
                        if r["state"]["running"] and net["name"] in r["networks"]
                    }
                if replace:
                    rows[0]["id"] = "e" * 64
                return b""
            if argv[1:3] == ["container", "ls"]:
                return ("\n".join(r["id"] for r in rows)).encode()
            if argv[1:3] == ["network", "inspect"]:
                return ("\n".join(json.dumps(n) for n in networks)).encode()
            assert argv[1] == "inspect"
            return ("\n".join(json.dumps(r) for r in rows)).encode()

        monkeypatch.setattr(operator, "_command", command)
        if replace:
            with pytest.raises(ActivationHold):
                await operator.stop_product_writers(
                    fence, root=tmp_path, project="synthetic", postal_network="postal-network"
                )
        else:
            result = await operator.stop_product_writers(
                fence, root=tmp_path, project="synthetic", postal_network="postal-network"
            )
            assert result == {r["service"]: r["id"] for r in before}
        assert len([c for c in calls if "stop" in c]) == 1
        assert not any(set(c) & {"start", "restart", "kill", "up"} for c in calls)
        fence.exclusive = False
        count = len(calls)
        with pytest.raises(ActivationHold):
            await operator.stop_product_writers(
                fence, root=tmp_path, project="synthetic", postal_network="postal-network"
            )
        assert count == len(calls)
        fence.exclusive = True

    asyncio.run(run())
    asyncio.run(run(True))


@pytest.mark.parametrize("mode", ["timeout", "cancel_twice", "spawn_timeout", "spawn_cancel"])
def test_real_cli_child_is_reaped_before_cancel_or_timeout_returns(tmp_path, mode, monkeypatch):
    async def run():
        if mode.startswith("spawn_"):
            original = asyncio.create_subprocess_exec

            async def delayed(*args, **kwargs):
                child = await original(*args, **kwargs)
                await asyncio.sleep(0.2)
                return child

            monkeypatch.setattr(asyncio, "create_subprocess_exec", delayed)
        pidfile = tmp_path / "pid"
        # Delayed TERM proves repeated cancellation cannot interrupt the reap owner.
        script = (
            "import os,signal,time,pathlib; "
            "signal.signal(signal.SIGTERM,lambda *_: (time.sleep(.15),exit(0))); "
            f"pathlib.Path({str(pidfile)!r}).write_text(str(os.getpid())); time.sleep(30)"
        )
        task = asyncio.create_task(
            operator._command(
                [sys.executable, "-c", script],
                deadline=time.monotonic()
                + (0.1 if mode == "spawn_timeout" else 0.3 if mode == "timeout" else 5),
            )
        )
        async with asyncio.timeout(3):
            while not pidfile.exists():
                await asyncio.sleep(0.005)
        pid = int(pidfile.read_text())
        if mode in {"cancel_twice", "spawn_cancel"}:
            task.cancel()
            await asyncio.sleep(0.03)
            task.cancel()
        with pytest.raises(
            ActivationHold if mode in {"timeout", "spawn_timeout"} else asyncio.CancelledError
        ):
            await task
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)

    asyncio.run(run())


@pytest.mark.parametrize("postal", ["postal_postal-network", "custom_postal-net"])
def test_actual_postal_name_is_resolved_separately_from_compose_key(postal):
    rows, networks = inventory()
    for row in rows:
        if "postal-network" in row["networks"]:
            row["networks"][postal] = row["networks"].pop("postal-network")
    operator._validate_inventory(
        rows, networks, project="synthetic", postal_network=postal, stopped=False
    )
    with pytest.raises(ActivationHold):
        operator._validate_inventory(
            rows, networks, project="synthetic", postal_network="postal-network", stopped=False
        )


def test_one_database_deadline_starts_before_identity_sql(fence, monkeypatch):
    from types import SimpleNamespace

    async def run():
        calls = []

        class Connection:
            def is_in_transaction(self):
                return False

            async def fetchrow(self, sql):
                calls.append(sql)
                await asyncio.sleep(1)

            async def execute(self, sql):
                pytest.fail("ALTER cannot follow expired identity check")

        # Leave 150ms of the same original budget; do not change asyncio's clock.
        monkeypatch.setattr(
            operator, "time", SimpleNamespace(monotonic=lambda: time.monotonic() - 29.85)
        )
        start = time.monotonic()
        with pytest.raises(ActivationHold):
            await operator.drain_product_database(
                fence,
                source=Connection(),
                owner=Connection(),
                name="synthetic",
                oid=1,
                cluster_id="123",
            )
        assert time.monotonic() - start < 0.5 and len(calls) == 1

    asyncio.run(run())


@pytest.mark.parametrize("defect", ["good", "empty", "symlink", "hardlink", "mode",
                                    "directory_mode", "decomposed", "special"])
def test_private_backup_object_manifest(tmp_path, defect):
    tmp_path.chmod(0o700)
    objects = tmp_path / "objects"
    objects.mkdir(mode=0o700)
    nested = objects / "notes"
    nested.mkdir(mode=0o700)
    payload = nested / "中文.txt"
    payload.write_bytes(b"educational only")
    payload.chmod(0o600)
    (objects / "empty.bin").touch(mode=0o600)
    if defect == "empty":
        payload.unlink()
    if defect == "symlink":
        (objects / "link").symlink_to(payload)
    if defect == "hardlink":
        os.link(payload, objects / "link")
    if defect == "mode":
        payload.chmod(0o644)
    if defect == "directory_mode":
        nested.chmod(0o755)
    if defect == "decomposed":
        (objects / "e\u0301").touch(mode=0o600)
    if defect == "special":
        os.mkfifo(objects / "pipe", 0o600)
    if defect in {"good", "empty"}:
        result = operator._file_manifest(objects, deadline=time.monotonic() + 5)
        expected = [("empty.bin", 0, hashlib.sha256(b"").hexdigest())]
        if defect == "good":
            expected.append(("notes/中文.txt", len(b"educational only"),
                             hashlib.sha256(b"educational only").hexdigest()))
        assert result == expected
    else:
        with pytest.raises(ActivationHold):
            operator._file_manifest(objects, deadline=time.monotonic() + 5)


@pytest.mark.parametrize("key", ["", "/leading", "trailing/", "double//slash", "./dot",
                                 "parent/../x", "nul\0x", "e\u0301", "x" * 1025, "\ud800"])
def test_ambiguous_object_key_is_refused(key):
    with pytest.raises(ActivationHold):
        operator._object_key(key)


@pytest.mark.parametrize("defect", ["good", "versioning", "lifecycle", "object_lock",
                                    "changed_stat", "changed_list", "short_stream", "read_error",
                                    "empty", "collision", "missing_list", "extra_list"])
def test_sdk_byte_manifest_closes_responses_and_detects_change(defect):
    from minio.error import S3Error

    closed = []
    stamp = datetime.now(UTC)

    class Client:
        lists = 0
        stats = 0

        def get_bucket_versioning(self, bucket):
            return SimpleNamespace(status="Suspended" if defect == "versioning" else None)

        def get_bucket_lifecycle(self, bucket):
            return object() if defect == "lifecycle" else None

        def get_object_lock_config(self, bucket):
            if defect != "object_lock":
                raise S3Error(response=None, code="ObjectLockConfigurationNotFoundError",
                              message="synthetic", resource="", request_id="", host_id="")
            return object()

        def list_objects(self, bucket, *, recursive):
            self.lists += 1
            if defect == "empty" or (defect == "missing_list" and self.lists > 1):
                return []
            rows = [SimpleNamespace(object_name="nested/中文", size=3,
                etag="different" if defect == "changed_list" and self.lists > 1 else "stable",
                last_modified=stamp)]
            if defect == "collision" or (defect == "extra_list" and self.lists > 1):
                rows.append(SimpleNamespace(object_name="nested", size=0, etag="extra",
                                            last_modified=stamp))
            return rows

        def stat_object(self, bucket, key):
            self.stats += 1
            return SimpleNamespace(object_name=key, size=3, last_modified=stamp,
                etag="different" if defect == "changed_stat" and self.stats > 1 else "stable")

        def get_object(self, bucket, key, **kwargs):
            class Response:
                def stream(self, size):
                    if defect == "read_error":
                        raise OSError("synthetic stream failure")
                    yield b"ab" if defect == "short_stream" else b"abc"

                def close(self):
                    closed.append("close")

                def release_conn(self):
                    closed.append("release")

            return Response()

    if defect == "empty":
        assert operator._object_manifest(Client(), "synthetic", deadline=time.monotonic()+5) == []
    elif defect == "good":
        assert operator._object_manifest(Client(), "synthetic", deadline=time.monotonic()+5) == [
            ("nested/中文", 3, hashlib.sha256(b"abc").hexdigest())]
    else:
        with pytest.raises((ActivationHold, OSError)):
            operator._object_manifest(Client(), "synthetic", deadline=time.monotonic()+5)
    assert closed == ([] if defect in {"versioning", "lifecycle", "object_lock", "empty", "collision"}
                      else ["close", "release"])


@pytest.mark.parametrize("prior", ["missing", "running", "bad_json", "unknown_version",
                                   "failed", "completed", "extra_field", "lost_initial"])
def test_backup_attempt_requires_known_durable_previous_outcome(fence, prior):
    marker = {"version": 1, "state": "never_started"}
    path = fence.path.parent / "activation.lock"
    path.write_text(json.dumps(marker))
    binding = dict(source_sha="a" * 40, image_id="sha256:" + "b" * 64,
                   cluster_id="123", db_name="twobrain_rec", db_oid=123)
    now = datetime.now(UTC).isoformat()
    record = dict(version=1, run_id="c" * 32, destination="backup-" + "c" * 32,
                  **binding, status="failed", reason="backup_failed", started_at=now,
                  finished_at=now, manifest_sha256=None)
    if prior == "running":
        record.update(status="in_progress", reason="running", finished_at=None)
    if prior == "completed":
        record.update(status="completed", reason="verified", manifest_sha256="d" * 64)
    if prior == "extra_field":
        record["extra"] = True
    if prior == "unknown_version":
        record["version"] = 2
    if prior == "lost_initial":
        path.write_text(json.dumps(dict(version=1, state="attempted", initial_sha256="e" * 64)))
    if prior not in {"missing", "lost_initial"}:
        attempt = fence.path.parent / "backup-attempt.json"
        attempt.write_text("{" if prior == "bad_json" else json.dumps(record))
        attempt.chmod(0o600)
    if prior in {"missing", "failed", "completed"}:
        operator._previous_backup_attempt(fence)
    else:
        with pytest.raises(ActivationHold):
            operator._previous_backup_attempt(fence)


@pytest.mark.parametrize("defect", ["good", "one_copy", "failed_latest", "manifest_version", "duplicate",
    "extra_field", "bool_count", "wrong_bytes", "artifact_order", "missing_artifact", "object_key",
    "native_metadata", "current_binding", "future", "age_26h", "parent_link", "changed_attempt",
    "deleted_companion", "object_corruption", "dump_corruption", "extra_file", "invalid_old",
    "historical_companion", "manifest_hash", "missing_attempt", "deadline", "float_metadata",
    "replaced_companion", "deep_manifest"])
def test_two_complete_copies_and_latest_attempt_are_verified(fence, tmp_path, monkeypatch, defect):
    parent = tmp_path / "backups"
    parent.mkdir(mode=0o700)
    now = datetime.now(UTC)
    binding = dict(source_sha="a"*40, image_id="sha256:"+"b"*64, cluster_id="123",
                   db_name="twobrain_rec", db_oid=123)
    metadata = dict(snapshot=dict(kind="snapshot", format_version=2, database="twobrain_rec",
        role="twobrain_rec", snapshot="00000001-00000002-1", server_version="170006"),
        schema_revision="0106_activation_milestones", schema_sha256="c"*64,
        roles_sha256="d"*64, ledger_invariants_sha256="e"*64, inventory_sha256="f"*64)
    monkeypatch.setattr(operator, "_backup_metadata", lambda *_: copy.deepcopy(metadata))

    def make(token):
        reference = parent / ("backup-"+token)
        reference.mkdir(mode=0o700)
        objects = reference / "minio-objects"
        objects.mkdir(mode=0o700)
        for key, value in [("postgres.dump", b"synthetic"), ("schema.sql", b"schema"),
                           ("inventory.jsonl", b"inventory"), ("checksums.sha256", b"checksums"),
                           ("minio-objects/中文.txt", b"Synthetic"), ("minio-objects/empty.bin", b"")]:
            (reference/key).write_bytes(value)
            (reference/key).chmod(0o600)
        files = operator._file_manifest(reference, deadline=time.monotonic()+5)
        obj = [(k.removeprefix("minio-objects/"), n, h) for k, n, h in files if k.startswith("minio-objects/")]
        record = dict(version=1, run_id=token, binding=dict(binding), **copy.deepcopy(metadata),
            started_at=(now-timedelta(minutes=4)).isoformat(), export_started_at=(now-timedelta(minutes=3)).isoformat(),
            export_closed_at=(now-timedelta(minutes=2)).isoformat(), finished_at=(now-timedelta(minutes=1)).isoformat(),
            cleanup="confirmed", disposition_coverage_sha256="1"*64,
            code_sha256={k: "2"*64 for k in ("operator", "capture", "verifier", "lifecycle", "replay", "tenant_context")},
            artifacts=files, objects=obj, object_count=2, object_bytes=9)
        return reference, record

    first, _ = make("1"*32)
    latest, manifest = make("2"*32)
    # Unit cases isolate strict input contracts; the native integration case uses
    # the real producer/inventory verifier for both copies and no metadata mock.
    first_manifest = copy.deepcopy(manifest)
    first_manifest["run_id"] = "1"*32
    if defect == "historical_companion":
        first_manifest["binding"].update(source_sha="c"*40, image_id="sha256:"+"d"*64, db_oid=321, cluster_id="321")
    for reference, record in ((first, first_manifest), (latest, manifest)):
        path = reference / "manifest.json"
        path.write_text(json.dumps(record, sort_keys=True)+"\n")
        path.chmod(0o600)
    if defect == "one_copy":
        import shutil
        shutil.rmtree(first)
    if defect == "manifest_version":
        manifest["version"] = 2
    if defect == "extra_field":
        manifest["extra"] = "not allowed"
    if defect == "bool_count":
        manifest["object_count"] = True
    if defect == "wrong_bytes":
        manifest["object_bytes"] += 1
    if defect == "artifact_order":
        manifest["artifacts"] = list(reversed(manifest["artifacts"]))
    if defect == "missing_artifact":
        manifest["artifacts"] = manifest["artifacts"][1:]
    if defect == "object_key":
        manifest["objects"][0] = ("../escape", 0, "3"*64)
    if defect == "native_metadata":
        manifest["roles_sha256"] = "3"*64
    if defect == "float_metadata":
        manifest["snapshot"]["format_version"] = 2.0
    if defect == "current_binding":
        manifest["binding"]["source_sha"] = "f"*40
    if defect == "future":
        manifest["finished_at"] = (now+timedelta(seconds=1)).isoformat()
    if defect == "age_26h":
        for key in ("started_at", "export_started_at", "export_closed_at", "finished_at"):
            manifest[key] = (now-timedelta(hours=26)).isoformat()
    raw = json.dumps(manifest, sort_keys=True)+"\n"
    if defect == "duplicate":
        raw = raw.replace('"version": 1', '"version": 1, "version": 1')
    if defect == "deep_manifest":
        raw = raw.rstrip()[:-1] + ', "nested": ' + "["*10000 + "0" + "]"*10000 + "}"
    (latest / "manifest.json").write_text(raw)
    attempt = dict(version=1, run_id="2"*32, destination=latest.name, **manifest["binding"],
        started_at=manifest["started_at"], finished_at=manifest["finished_at"],
        status="completed", reason="verified", manifest_sha256=hashlib.sha256(raw.encode()).hexdigest())
    if defect == "failed_latest":
        attempt.update(status="failed", reason="backup_failed", manifest_sha256=None)
    if defect == "manifest_hash":
        attempt["manifest_sha256"] = "0"*64
    if defect in {"object_corruption", "dump_corruption", "extra_file"}:
        name = {"object_corruption": "minio-objects/中文.txt", "dump_corruption": "postgres.dump",
                "extra_file": "extra"}[defect]
        path = latest / name
        path.write_bytes(b"X"*len(path.read_bytes()) if path.exists() else b"new")
        path.chmod(0o600)
    if defect == "invalid_old":
        old = parent / ("backup-"+"0"*32)
        old.mkdir(mode=0o700)
        (old / "postgres.dump").touch(mode=0o600)
    state = fence.path.parent / "backup-attempt.json"
    state.write_text(json.dumps(attempt))
    state.chmod(0o600)
    if defect == "missing_attempt":
        state.unlink()
        (fence.path.parent / "activation.lock").write_text(json.dumps(dict(version=1, state="never_started")))
    selected_parent = parent
    if defect == "parent_link":
        selected_parent = tmp_path / "link"
        selected_parent.symlink_to(parent, target_is_directory=True)
    if defect in {"changed_attempt", "deleted_companion", "replaced_companion"}:
        original = operator._read_coherent_backup

        def changing(*args, **kwargs):
            result = original(*args, **kwargs)
            if result["destination"] == first.name:
                if defect == "changed_attempt":
                    state.write_text(state.read_text()+"\n")
                elif defect == "replaced_companion":
                    import shutil

                    moved = parent / "previous"
                    first.rename(moved)
                    shutil.copytree(moved, first)
                else:
                    (first / "postgres.dump").unlink()
            return result

        monkeypatch.setattr(operator, "_read_coherent_backup", changing)
    kwargs = dict(root=Path(__file__).resolve().parents[4], parent=selected_parent, binding=binding,
                  now=now, deadline=time.monotonic()+(-1 if defect == "deadline" else 5))
    if defect in {"good", "invalid_old", "historical_companion"}:
        verified = operator._verified_backup_set(fence, **kwargs)
        assert verified["latest"]["destination"] == latest.name
        assert verified["companion"]["destination"] == first.name
        assert not (fence.path.parent / "initial.json").exists()
    else:
        with pytest.raises(ActivationHold) as held:
            operator._verified_backup_set(fence, **kwargs)
        if defect == "deep_manifest":
            assert str(held.value) in {"activation_operator_backup_unverified", "activation_operator_backup_set_unverified"}


@pytest.mark.parametrize('case', [
    'good', 'optional_absent', 'wrong_image', 'wrong_source', 'duplicate_source',
    'wrong_user', 'userns', 'required_exited', 'unhealthy', 'config_changed',
    'pid_changed', 'override_changed', 'no_release', 'deadline', 'foreign_network',
    'rootless', 'remap', 'image_env', 'image_platform', 'process_changed', 'postal_changed', 'socket_changed', 'thirdparty_user',
])
def test_runtime_preflight_binds_actual_release_and_processes(tmp_path, monkeypatch, case):
    rows, networks = inventory()
    if case == 'optional_absent':
        rows = [r for r in rows if r['service'] not in operator.OPTIONAL_WRITERS]
    for row in rows:
        row['project'] = 'twobrain-rec'
    for network in networks:
        network['project'] = 'twobrain-rec'
    source = 'a' * 40
    images = {r['service']: 'sha256:' + f'{i + 1:064x}' for i, r in enumerate(rows)}
    override = tmp_path / 'override.json'
    override.write_text(json.dumps({'services': {
        name: dict(image=image, pull_policy='never') for name, image in images.items()
    }}))
    details = [{
        'id': r['id'], 'image': images[r['service']], 'config': {
            'User': 'twobrain' if r['service'] in operator.WRITERS | {'rec-migrate', 'rec-db-runtime-bootstrap'} else '',
            'Labels': {'com.docker.compose.config-hash': 'c' * 64},
            'Env': ['GRAF_DEV_SOURCE_SHA=' + source], 'Entrypoint': ['synthetic'], 'Cmd': [],
        },
        'host': {'UsernsMode': ''}, 'mounts': [],
        'state': dict(r['state'], started='2026-10-30T01:00:00Z', health='healthy'),
        'restarts': 0,
    } for r in rows]
    images_info = [{
        'id': images[r['service']], 'os': 'linux', 'architecture': 'amd64',
        'config': copy.deepcopy(d['config']),
    } for r, d in zip(rows, details, strict=True)]
    for image in images_info:
        image['config']['Labels']['org.2brain.graf.dev.source-sha'] = source
    api = next(d for d in details if d['id'] == rows[0]['id'])
    if case == 'wrong_image':
        api['image'] = 'sha256:' + 'f' * 64
    if case == 'wrong_source':
        images_info[0]['config']['Labels']['org.2brain.graf.dev.source-sha'] = 'b' * 40
    if case == 'duplicate_source':
        api['config']['Env'].append('GRAF_DEV_SOURCE_SHA=' + source)
    if case == 'image_env':
        images_info[0]['config']['Env'] = []
    if case == 'image_platform':
        images_info[0]['architecture'] = 'unexpected'
    if case == 'thirdparty_user':
        next(d for r, d in zip(rows, details, strict=True) if r['service'] == 'rec-minio-init')['config']['User'] = 'root'
    if case == 'wrong_user':
        api['config']['User'] = 'root'
    if case == 'userns':
        api['host']['UsernsMode'] = 'host'
    if case == 'required_exited':
        api['state'].update(status='exited', running=False, pid=0)
    if case == 'unhealthy':
        api['state']['health'] = 'unhealthy'
    if case == 'foreign_network':
        networks[0]['containers']['f' * 64] = {}
    calls, inspect_count, release_count, postal_count, socket_count, process_count = [], 0, 0, 0, 0, 0

    async def command(argv, *, deadline, cwd=None):
        nonlocal inspect_count, release_count, postal_count
        calls.append(argv)
        if argv[0] == '/usr/bin/git':
            return (source + '\n').encode()
        if 'current-override' in argv:
            release_count += 1
            if case == 'no_release':
                return b'\n'
            if case == 'override_changed' and release_count == 2:
                override.write_text(override.read_text() + '\n')
            return (str(override) + '\n').encode()
        if argv[1] == 'info':
            return json.dumps({'os': 'linux', 'security': ['name=' + ('userns' if case == 'remap' else case)] if case in {'rootless', 'remap'} else ['name=seccomp'], 'architecture': 'x86_64'}).encode()
        if argv[1:3] == ['image', 'inspect']:
            return b'\n'.join(json.dumps(v).encode() for v in images_info)
        if argv[1] == 'inspect':
            inspect_count += 1
            current = copy.deepcopy(details)
            if inspect_count == 2 and case == 'config_changed':
                current[0]['mounts'] = [{'Destination': '/synthetic-changed'}]
            if inspect_count == 2 and case == 'pid_changed':
                current[0]['state']['pid'] += 1
            return b'\n'.join(json.dumps(v).encode() for v in current)
        if argv[1:3] == ['network', 'inspect']:
            postal_count += 1
            return json.dumps({'id': ('f' if case == 'postal_changed' and postal_count == 2 else 'e') * 64, 'name': 'postal-network'}).encode()
        pytest.fail('unexpected runtime command')

    async def get_inventory(*_):
        return copy.deepcopy(rows), copy.deepcopy(networks)

    monkeypatch.setattr(operator, '_command', command)
    monkeypatch.setattr(operator, '_inventory', get_inventory)
    def socket():
        nonlocal socket_count
        socket_count += 1
        return ('changed' if case == 'socket_changed' and socket_count == 2 else 'synthetic-socket',)

    def process(pid):
        nonlocal process_count
        process_count += 1
        return pid, process_count if case == 'process_changed' else 12345

    monkeypatch.setattr(operator, '_local_docker', socket)
    monkeypatch.setattr(operator, '_process_identity', process)
    from contextlib import contextmanager

    checked_settings = []

    @contextmanager
    def settings(row, **kwargs):
        checked_settings.append(row['id'])
        yield None, 'f' * 64

    monkeypatch.setattr(operator, '_runtime_settings', settings)
    if case in {'good', 'optional_absent'}:
        result = asyncio.run(operator._runtime_preflight(
            root=tmp_path, snapshot=tmp_path, source=source, deadline=time.monotonic() + 20))
        assert result['runtime'] == 'verified' and result['source_sha'] == source
        assert result['container_count'] == len(rows)
        assert len(result['runtime_sha256']) == 64
        assert set(checked_settings) == {r['id'] for r in rows if r['service'] in operator.WRITERS and r['state']['running']}
    else:
        with pytest.raises(ActivationHold):
            asyncio.run(operator._runtime_preflight(
                root=tmp_path, snapshot=tmp_path, source=source,
                deadline=time.monotonic() + (-1 if case == 'deadline' else 20)))
    assert not any(set(c) & {'stop', 'start', 'restart', 'up', 'exec', 'create', 'run'} for c in calls)


@pytest.mark.parametrize('case', ['good', 'uid', 'gid', 'map', 'stat', 'missing', 'groups_invalid', 'groups_duplicate'])
def test_runtime_process_identity_reads_all_ids_and_parses_comm(tmp_path, case):
    proc = tmp_path / '123'
    proc.mkdir()
    (proc / 'status').write_text('Uid:\t100\t100\t100\t100\nGid:\t101\t101\t101\t101\nGroups:\t101 1001\n')
    (proc / 'stat').write_text('123 (odd ) process name) S ' + '0 ' * 18 + '12345 0\n')
    for name in ('uid_map', 'gid_map'):
        (proc / name).write_text('         0          0 4294967295\n')
    if case in {'uid', 'gid'}:
        name, before, after = ('Uid', '100\t100', '100\t0') if case == 'uid' else ('Gid', '101\t101', '101\t0')
        (proc / 'status').write_text((proc / 'status').read_text().replace(name + ':\t' + before, name + ':\t' + after))
    if case == 'map':
        (proc / 'gid_map').write_text('0 100000 65536\n')
    if case == 'stat':
        (proc / 'stat').write_text('malformed')
    if case == 'missing':
        (proc / 'status').unlink()
    if case.startswith('groups_'):
        (proc / 'status').write_text((proc / 'status').read_text().replace('101 1001', '-1' if case == 'groups_invalid' else '101 101'))
    if case == 'good':
        assert operator._process_identity(123, proc_root=tmp_path) == (123, 12345, (101, 1001))
    else:
        with pytest.raises(ActivationHold):
            operator._process_identity(123, proc_root=tmp_path)


@pytest.mark.parametrize('case', ['good', 'remote', 'context', 'config', 'tls', 'symlink', 'world_write', 'owner'])
def test_runtime_docker_endpoint_is_the_existing_local_socket(monkeypatch, case):
    import stat

    for name in ('DOCKER_CONTEXT', 'DOCKER_CONFIG', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('DOCKER_HOST', operator.DOCKER_ENDPOINT if case != 'remote' else 'ssh://synthetic.invalid')
    if case in {'context', 'config', 'tls'}:
        monkeypatch.setenv({'context': 'DOCKER_CONTEXT', 'config': 'DOCKER_CONFIG', 'tls': 'DOCKER_TLS_VERIFY'}[case], 'poison')
    info = SimpleNamespace(st_dev=1, st_ino=2, st_uid=9 if case == 'owner' else 0,
                           st_gid=0, st_mode=(stat.S_IFLNK if case == 'symlink' else stat.S_IFSOCK)
                           | (0o666 if case == 'world_write' else 0o660))
    monkeypatch.setattr(Path, 'lstat', lambda _: info)
    if case == 'good':
        assert operator._local_docker()[:2] == (1, 2)
    else:
        with pytest.raises(ActivationHold):
            operator._local_docker()


@pytest.mark.parametrize('case', [
    'good', 'alias', 'json_and_nodecode', 'caller_env', 'dotenv', 'bad_proxy',
    'duplicate_env', 'case_collision', 'development', 'missing_core',
    'readwrite', 'not_bind', 'parent_mount', 'missing', 'symlink', 'hardlink',
    'public', 'writable', 'empty', 'oversize', 'relative', 'dotdot',
    'placeholder_disabled', 'placeholder_enabled', 'arbitrary_empty',
    'changed', 'replaced', 'sealed_bytes', 'host_proxy',
    'inline_password', 'marker_username', 'maintenance_inline', 'maintenance_marker_path',
])
def test_actual_runtime_settings_use_bound_files_and_canonical_validators(tmp_path, monkeypatch, case):
    from contextlib import contextmanager
    from urllib.parse import quote

    directory = tmp_path.resolve()
    monkeypatch.setattr(operator, 'INSTALLATION_UID', os.getuid(), raising=False)
    monkeypatch.delenv('FORWARDED_ALLOW_IPS', raising=False)
    files = {}
    for name, raw in [('db', b'S@fe/p%?word'), ('access', b'graf_runtime_api'),
                      ('secret', b'non-placeholder-production-secret')]:
        path = directory / name
        path.write_bytes(raw)
        path.chmod(0o640)
        if sys.platform == 'linux':
            os.chown(path, -1, 101)
        files[name] = path
    environment = {
        'TWOBRAIN_ENV': 'production', 'TWOBRAIN_WEB_RUNTIME_ENABLED': 'false',
        'TWOBRAIN_AUTH_RU_LOCAL_STORAGE_ATTESTED': 'true',
        'TWOBRAIN_DATABASE_URL': 'postgresql+asyncpg://twobrain_rec_app:__POSTGRES_PASSWORD__@rec-postgres:5432/twobrain_rec',
        'TWOBRAIN_POSTGRES_PASSWORD_FILE': str(files['db']),
        'TWOBRAIN_MINIO_ENDPOINT': 'rec-minio:9000',
        'TWOBRAIN_MINIO_ACCESS_KEY_FILE': str(files['access']),
        'TWOBRAIN_MINIO_SECRET_KEY_FILE': str(files['secret']),
    }
    mounts = [dict(Destination=str(p), Source=str(p), Type='bind', RW=False) for p in files.values()]
    process = (123, 456, tuple(sorted({101, os.getgid()})))
    monkeypatch.setattr(operator, '_process_identity', lambda *a, **kw: process)
    proc = directory / 'proc/123'
    proc.mkdir(parents=True)
    (proc / 'root').symlink_to('/', target_is_directory=True)
    if sys.platform == 'linux':
        # Native tests use /owned as basetemp, never a world-writable host ancestor.
        for parent in (directory, *directory.parents):
            if str(parent).startswith('/owned'):
                parent.chmod(0o755)
    else:
        # macOS native ACL/memfd/proc boundaries are tested separately on Linux.
        monkeypatch.setattr(operator, '_settings_no_acl', lambda fd: None, raising=False)
        @contextmanager
        def snapshot(raw):
            path = directory / ('snapshot-' + str(len(list(directory.glob('snapshot-*')))))
            path.write_bytes(raw)
            try:
                yield path
            finally:
                path.unlink()

        @contextmanager
        def destination(_root_fd, path, _groups):
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                yield fd
            finally:
                os.close(fd)

        monkeypatch.setattr(operator, '_sealed_settings_file', snapshot, raising=False)
        monkeypatch.setattr(operator, '_settings_destination', destination, raising=False)
        monkeypatch.setattr(operator, '_settings_source_ancestors', lambda p: [], raising=False)
    if case == 'alias':
        environment['GRAF_CREDENTIAL_ENCRYPTION_KEY_FILE'] = str(files['secret'])
    if case == 'json_and_nodecode':
        environment.update(TWOBRAIN_BILLING_CHECKOUT_WORKSPACE_IDS='["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"]',
                           TWOBRAIN_PRODUCT_ANALYTICS_INTERNAL_HOSTS='192.0.2.0/24,198.51.100.3')
    if case == 'caller_env':
        monkeypatch.setenv('TWOBRAIN_DATABASE_URL', 'poison://must-not-be-read')
        monkeypatch.setenv('TWOBRAIN_ENV', 'development')
        monkeypatch.setenv('GRAF_CREDENTIAL_ENCRYPTION_KEY_FILE', '/missing/caller-secret')
    if case == 'dotenv':
        monkeypatch.chdir(directory)
        (directory / '.env').write_text('TWOBRAIN_DATABASE_URL=poison://dotenv\n')
    if case == 'bad_proxy':
        environment['FORWARDED_ALLOW_IPS'] = '*'
    if case == 'host_proxy':
        monkeypatch.setenv('FORWARDED_ALLOW_IPS', '*')
    if case == 'development':
        environment['TWOBRAIN_ENV'] = 'development'
    if case == 'missing_core':
        del environment['TWOBRAIN_POSTGRES_PASSWORD_FILE']
    if case == 'inline_password':
        environment['TWOBRAIN_DATABASE_URL'] = environment['TWOBRAIN_DATABASE_URL'].replace('__POSTGRES_PASSWORD__', 'inline-password')
    if case == 'marker_username':
        environment['TWOBRAIN_DATABASE_URL'] = 'postgresql+asyncpg://__POSTGRES_PASSWORD__:inline-password@rec-postgres:5432/twobrain_rec'
    if case.startswith('maintenance_'):
        environment['TWOBRAIN_PROMPT_OPTIMIZATION_DATABASE_URL'] = 'postgresql+asyncpg://twobrain_rec_maintenance:inline-password@rec-postgres:5432/' + ('__POSTGRES_PASSWORD__' if case == 'maintenance_marker_path' else 'twobrain_rec')
        environment['TWOBRAIN_PROMPT_OPTIMIZATION_POSTGRES_PASSWORD_FILE'] = str(files['db'])
    if case == 'readwrite':
        mounts[0]['RW'] = True
    if case == 'not_bind':
        mounts[0]['Type'] = 'volume'
    if case == 'parent_mount':
        mounts.append(dict(Destination=str(directory), Source=str(directory), Type='bind', RW=False))
    if case == 'missing':
        files['db'].unlink()
    if case == 'symlink':
        files['db'].unlink()
        files['db'].symlink_to(files['secret'])
    if case == 'hardlink':
        os.link(files['db'], directory / 'other-link')
    if case in {'public', 'writable'}:
        files['db'].chmod(0o644 if case == 'public' else 0o660)
    if case in {'empty', 'oversize'}:
        files['db'].write_bytes(b'' if case == 'empty' else b'X' * 65537)
    if case in {'relative', 'dotdot'}:
        environment['TWOBRAIN_POSTGRES_PASSWORD_FILE'] = 'db' if case == 'relative' else str(directory) + '/x/../db'
    if case.startswith('placeholder') or case == 'arbitrary_empty':
        placeholder = directory / 'infra/secret-placeholders/disabled_optional_provider_secret'
        placeholder.parent.mkdir(parents=True)
        placeholder.parent.parent.chmod(0o755)
        placeholder.parent.chmod(0o755)
        placeholder.write_bytes(b'')
        placeholder.chmod(0o644)
        if case == 'arbitrary_empty':
            placeholder.rename(directory / 'arbitrary-empty')
            placeholder = directory / 'arbitrary-empty'
        environment['TWOBRAIN_GOOGLE_CALENDAR_CLIENT_SECRET_FILE'] = str(placeholder)
        environment['TWOBRAIN_GOOGLE_CALENDAR_ENABLED'] = 'true' if case == 'placeholder_enabled' else 'false'
        mounts.append(dict(Destination=str(placeholder), Source=str(placeholder), Type='bind', RW=False))
    row = dict(config=dict(Env=[k + '=' + v for k, v in environment.items()]),
               mounts=mounts, state=dict(pid=123))
    if case == 'duplicate_env':
        row['config']['Env'].append('TWOBRAIN_ENV=production')
    if case == 'case_collision':
        row['config']['Env'].append('twobrain_env=production')

    admitted = []

    def check():
        with operator._runtime_settings(row, root=directory, process=process, proc_root=directory / 'proc') as (settings, digest):
            admitted.append(True)
            assert settings.env == 'production'
            assert quote('S@fe/p%?word', safe='') in settings.database_url
            assert settings.minio_access_key == 'graf_runtime_api'
            assert len(digest) == 64
            if case == 'alias':
                assert settings.credential_encryption_key_file.read_bytes() == files['secret'].read_bytes()
            if case == 'json_and_nodecode':
                assert len(settings.billing_checkout_workspace_ids) == 1
                assert settings.product_analytics_internal_hosts == ('192.0.2.0/24', '198.51.100.3')
            if case in {'changed', 'sealed_bytes'}:
                files['db'].write_bytes(b'changed-after-snapshot')
                # Canonical validators and later consumers still see verified immutable bytes.
                assert settings.postgres_password_file.read_bytes() == b'S@fe/p%?word'
            if case == 'replaced':
                replacement = directory / 'replacement'
                replacement.write_bytes(b'other-inode')
                replacement.replace(files['db'])

    good = {'good', 'alias', 'json_and_nodecode', 'caller_env', 'dotenv', 'placeholder_disabled'}
    if case in good:
        check()
    else:
        with pytest.raises(ActivationHold) as held:
            check()
        if case not in {'changed', 'replaced', 'sealed_bytes'}:
            assert not admitted, 'invalid configuration reached the caller'
        assert str(held.value) == 'activation_operator_settings_unverified'
        assert str(directory) not in str(held.value) and 'S@fe' not in str(held.value)


@pytest.mark.skipif(sys.platform != 'linux', reason='Linux sealed memfd boundary')
def test_settings_snapshot_cannot_be_written_or_truncated():
    with operator._sealed_settings_file(b'synthetic secret') as path:
        assert path.read_bytes() == b'synthetic secret'
        with pytest.raises(OSError):
            path.write_bytes(b'changed')
        with pytest.raises(OSError):
            os.truncate(path, 0)
    assert not path.exists()


@pytest.mark.parametrize('case', ['good', 'world_write', 'wrong_owner', 'group_unconfirmed', 'link'])
def test_settings_source_ancestry_is_protected(monkeypatch, case):
    import stat

    monkeypatch.setattr(Path, 'resolve', lambda self, **kwargs: self)
    monkeypatch.setattr(operator, '_settings_no_acl', lambda fd: None)
    monkeypatch.setattr(operator.os, 'open', lambda *args, **kwargs: 999)
    monkeypatch.setattr(operator.os, 'close', lambda fd: None)
    monkeypatch.setattr(Path, 'lstat', lambda self: SimpleNamespace(
        st_dev=1, st_ino=2, st_nlink=1, st_size=0, st_mtime_ns=1, st_ctime_ns=1,
        st_uid=9999 if case == 'wrong_owner' else 0,
        st_gid=operator.INSTALLATION_GID,
        st_mode=(stat.S_IFLNK if case == 'link' else stat.S_IFDIR)
        | (0o777 if case == 'world_write' else 0o775 if case == 'group_unconfirmed' else 0o755)))
    monkeypatch.setattr(operator.os, 'fstat', lambda fd: Path('/synthetic').lstat())
    monkeypatch.setattr(operator.grp, 'getgrgid', lambda _gid: SimpleNamespace(gr_mem=['unconfirmed']))
    monkeypatch.setattr(operator.pwd, 'getpwall', lambda: [
        SimpleNamespace(pw_uid=1003, pw_gid=operator.INSTALLATION_GID, pw_name='unconfirmed')])
    if case == 'good':
        assert operator._settings_source_ancestors(Path('/synthetic/file'))
    else:
        with pytest.raises(ActivationHold):
            operator._settings_source_ancestors(Path('/synthetic/file'))


@pytest.mark.skipif(sys.platform != 'linux', reason='Linux native FD lifetime')
def test_runtime_settings_closes_fds_after_success_and_failures(tmp_path, monkeypatch):
    before = set(os.listdir('/proc/self/fd'))
    for case in ('good', 'empty', 'changed', 'placeholder_enabled'):
        path = tmp_path / case
        path.mkdir()
        with monkeypatch.context() as isolated:
            test_actual_runtime_settings_use_bound_files_and_canonical_validators(path, isolated, case)
        assert set(os.listdir('/proc/self/fd')) == before


@pytest.mark.skipif(sys.platform != 'linux', reason='Linux POSIX ACL boundary')
@pytest.mark.parametrize('case', ['runtime_deny', 'foreign_read', 'directory_write'])
def test_settings_reject_extended_acl_on_pinned_files_and_directories(tmp_path, monkeypatch, case):
    import struct

    path = tmp_path / 'acl-target'
    if case == 'directory_write':
        path.mkdir(mode=0o770)
    else:
        path.write_bytes(b'synthetic')
        path.chmod(0o640)
    fd = os.open(path, os.O_RDONLY | (os.O_DIRECTORY if path.is_dir() else 0))
    try:
        uid = 100 if case == 'runtime_deny' else 1003
        mask = 7 if case == 'directory_write' else 4
        permission = 0 if case == 'runtime_deny' else mask
        entries = [(1, 7 if case == 'directory_write' else 6, 0xffffffff),
                   (2, permission, uid), (4, mask, 0xffffffff),
                   (16, mask, 0xffffffff), (32, 0, 0xffffffff)]
        acl = struct.pack('<I', 2) + b''.join(struct.pack('<HHI', *e) for e in entries)
        operator._settings_no_acl(fd)
        os.setxattr(fd, 'system.posix_acl_access', acl)
        assert os.fstat(fd).st_mode & 0o777 == (0o770 if case == 'directory_write' else 0o640)
        with pytest.raises(ActivationHold):
            operator._settings_no_acl(fd)
    finally:
        os.close(fd)
