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


def test_guard_pinned_protection_path_is_explicit(tmp_path):
    from tests.fixtures.analytics_operations import write_runtime_guard
    from twobrain_rec_server.product_analytics.provider_readiness import runtime_guard_blockers

    now = int(time.time())
    environment = write_runtime_guard(tmp_path, now=now)
    assert runtime_guard_blockers(environment, now=now) == ()
    for path in ('', str(tmp_path / 'missing')):
        assert 'protection_state_unverified' in runtime_guard_blockers(
            environment, now=now, protection_state_file=path)
    pinned = tmp_path / 'pinned-protection'
    pinned.write_text(json.dumps(dict(protection_state_version=1, status='protected', reasons=[])))
    assert 'analytics_protection_latched' in runtime_guard_blockers(
        environment, now=now, protection_state_file=str(pinned))


@pytest.mark.skipif(sys.platform != 'linux' or os.geteuid() != 0, reason='Linux root/proc/memfd boundary')
@pytest.mark.parametrize('case', [
    'good', 'host_environment', 'sibling_update', 'bad_settings', 'legal_disabled',
    'disclosure_disabled', 'missing', 'version1', 'invalid_register', 'withdrawn',
    'expired_access', 'wrong_digest', 'wrong_expected', 'stale_guard', 'future_guard',
    'latched', 'writable_bind', 'overlapping_bind', 'exact_file_bind', 'wrong_inode',
    'file_symlink', 'file_hardlink', 'public_file', 'installed_mode', 'installed_changed',
    'directory_replaced', 'file_replaced', 'file_changed', 'guard_stale_on_exit',
    'access_expired_on_exit', 'budget_expired_on_exit', 'snapshot_changed',
])
def test_runtime_operations_use_actual_directory_binds(tmp_path, monkeypatch, case):
    directory = tmp_path.resolve()
    monkeypatch.setattr(operator, 'INSTALLATION_UID', os.getuid())
    # Native volume is /owned, with no world-writable source ancestors.
    for parent in (directory, *directory.parents):
        if str(parent).startswith('/owned'):
            parent.chmod(0o755)
    state = directory / 'state'
    state.mkdir(mode=0o750)
    os.chown(state, 0, 101)
    now = int(time.time())
    installed = directory / 'installed-guard'
    installed.write_text('#!/bin/sh\nexit 0\n')
    installed.chmod(0o755)
    snapshot = directory / 'snapshot'
    (snapshot / 'infra/scripts').mkdir(parents=True)
    pinned = snapshot / 'infra/scripts/posthog-runtime-guard.sh'
    pinned.write_bytes(installed.read_bytes())
    digest = 'sha256:' + hashlib.sha256(installed.read_bytes()).hexdigest()
    files = {
        'legal': state / 'legal-basis-withdrawals',
        'access': state / 'access-governance-state',
        'alert': state / 'alert-state',
        'protection': state / 'protection-state.json',
    }
    files['legal'].write_text('legal_basis_state_version=2\n')
    files['access'].write_text(
        f'access_governance_state_version=1\nreviewed_at={now}\nexpires_at={now + 3600}\n'
        'accepted_operator_count=2\nmfa_operator_count=2\n'
        f'repository_digest={digest}\nconfig_digest={digest}\ninstalled_guard_digest={digest}\n'
        'revocation_review=complete\ncredential_rotation_review=complete\naudit_review=complete\n')
    files['alert'].write_text(
        'alert_state_version=2\ncapacity_ready=true\ncapacity_input_verified=true\n'
        'capacity_budget_accepted=true\nprotection_status=observed\n'
        f'recorded_at_epoch={now}\ncapacity_sample_epoch={now}\n'
        f'capacity_budget_deadline_epoch={now + 3600}\n'
        f'capacity_inventory_version={"a" * 64}\ncapacity_budget_version={"b" * 64}\n')
    files['protection'].write_text(json.dumps(dict(protection_state_version=1, status='observed', reasons=[])))
    for file in files.values():
        file.chmod(0o640)
        os.chown(file, 0, 101)
    environment = {
        'GRAF_PRODUCT_ANALYTICS_LEGAL_BASIS_STATE_DIR': str(state),
        'GRAF_PRODUCT_ANALYTICS_ACCESS_GOVERNANCE_STATE_DIR': str(state),
        'GRAF_POSTHOG_GUARD_STATE_DIR': str(state),
    }
    row = dict(config=dict(Env=[k+'='+v for k, v in environment.items()]),
               mounts=[dict(Destination=str(state), Source=str(state), Type='bind', RW=False)],
               state=dict(pid=123))
    process = (123, 456, (101,))
    monkeypatch.setattr(operator, '_process_identity', lambda *a, **kw: process)
    monkeypatch.setattr(operator, 'INSTALLED_GUARD', installed, raising=False)
    proc = directory / 'proc/123'
    proc.mkdir(parents=True)
    (proc / 'root').symlink_to('/', target_is_directory=True)
    settings = SimpleNamespace(product_analytics_legal_approved=case != 'legal_disabled',
        product_analytics_disclosure_approved=case != 'disclosure_disabled',
        product_analytics_local_only_configuration_valid=lambda: case != 'bad_settings')
    if case == 'host_environment':
        for key in environment:
            monkeypatch.setenv(key, '/host/poison/must-not-be-read')
    if case == 'missing':
        files['legal'].unlink()
    if case == 'version1':
        files['legal'].write_text('legal_basis_state_version=1\n')
    if case == 'invalid_register':
        files['legal'].write_text('legal_basis_state_version=2\nunknown=record\n')
    if case == 'withdrawn':
        files['legal'].write_text('legal_basis_state_version=2\nbasis_withdrawal level=attribution_profiles '
            'state=withdrawn withdrawn_at='+datetime.now(UTC).date().isoformat()+' reason=owner_decision\n')
    if case == 'expired_access':
        files['access'].write_text(files['access'].read_text().replace(
            f'reviewed_at={now}\n', f'reviewed_at={now-60}\n').replace(str(now+3600), str(now)))
    if case == 'wrong_digest':
        files['access'].write_text(files['access'].read_text().replace(digest, 'sha256:'+'c'*64))
    if case == 'wrong_expected':
        row['config']['Env'].append('GRAF_PRODUCT_ANALYTICS_ACCESS_GOVERNANCE_EXPECTED_DIGEST=sha256:'+'d'*64)
    if case in {'stale_guard', 'future_guard'}:
        files['alert'].write_text(files['alert'].read_text().replace(f'={now}\n', f'={now-120 if case == "stale_guard" else now+1}\n'))
    if case == 'latched':
        files['protection'].write_text(json.dumps(dict(protection_state_version=1, status='protected', reasons=[])))
    if case == 'writable_bind':
        row['mounts'][0]['RW'] = True
    if case == 'overlapping_bind':
        row['mounts'].append(dict(row['mounts'][0]))
    if case == 'exact_file_bind':
        row['mounts'] = [dict(Destination=str(f), Source=str(f), Type='bind', RW=False) for f in files.values()]
    if case == 'wrong_inode':
        other = directory / 'other'
        other.mkdir(mode=0o750)
        os.chown(other, 0, 101)
        for file in files.values():
            target = other / file.name
            target.write_bytes(file.read_bytes())
            target.chmod(0o640)
            os.chown(target, 0, 101)
        row['mounts'][0]['Source'] = str(other)
    if case == 'file_symlink':
        files['legal'].unlink()
        files['legal'].symlink_to(files['access'])
    if case == 'file_hardlink':
        os.link(files['legal'], state / 'hardlink')
    if case == 'public_file':
        files['legal'].chmod(0o644)
    if case == 'installed_mode':
        installed.chmod(0o777)
    if case == 'access_expired_on_exit':
        files['access'].write_text(files['access'].read_text().replace(str(now+3600), str(now+1)))
    if case == 'budget_expired_on_exit':
        files['alert'].write_text(files['alert'].read_text().replace(str(now+3600), str(now+1)))
    before = set(os.listdir('/proc/self/fd'))
    reached = []
    def check():
        with operator._runtime_operations(row, settings=settings, root=directory,
                process=process, snapshot=snapshot, proc_root=directory / 'proc') as proof:
            reached.append(True)
            assert len(proof[0]) == 64
            assert proof[1] == files['legal'].read_bytes()
            assert type(proof[1]) is bytes
            if case == 'sibling_update':
                (state / 'unrelated').write_text('ordinary atomic sibling update')
            if case in {'installed_changed', 'snapshot_changed'}:
                (installed if case == 'installed_changed' else pinned).write_text('changed')
            if case == 'directory_replaced':
                state.rename(directory / 'prior-state')
                state.mkdir(mode=0o750)
            if case == 'file_replaced':
                old = files['legal'].with_suffix('.old')
                files['legal'].rename(old)
                files['legal'].write_bytes(old.read_bytes())
                files['legal'].chmod(0o640)
                os.chown(files['legal'], 0, 101)
            if case == 'file_changed':
                files['legal'].write_text('legal_basis_state_version=2\n#changed\n')
            if case.endswith('_on_exit'):
                monkeypatch.setattr(operator, 'time', SimpleNamespace(time=lambda: now+(120 if case == 'guard_stale_on_exit' else 1)))
    good = {'good', 'host_environment', 'sibling_update'}
    try:
        if case in good:
            check()
        else:
            with pytest.raises(ActivationHold):
                check()
            if case not in {'installed_changed', 'snapshot_changed', 'directory_replaced', 'file_replaced',
                            'file_changed', 'guard_stale_on_exit', 'access_expired_on_exit', 'budget_expired_on_exit'}:
                assert not reached
    finally:
        assert set(os.listdir('/proc/self/fd')) == before


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
    'rootless', 'remap', 'image_env', 'image_platform', 'process_changed', 'postal_changed', 'socket_changed', 'thirdparty_user', 'model_changed', 'registry_changed', 'policy_drift', 'poisoned_env', 'volume_good', 'volume_changed', 'volume_options', 'late_database_close', 'late_secret_close', 'operations_failure', 'operations_mismatch', 'raw_mismatch', 'late_operations_close', 'guard_failure', 'late_guard_exit',
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
    policy_root, model, policy_rows, _, policy_ids = _policy_sample(tmp_path, monkeypatch)
    policy_by_name = {name: next(r for r in policy_rows if r['id'] == ident)
                      for name, ident in policy_ids.items()}
    for row, detail, image in zip(rows, details, images_info, strict=True):
        sample = policy_by_name[row['service']]
        detail['host'] = copy.deepcopy(sample['host'])
        detail['mounts'] = copy.deepcopy(sample['mounts'])
        detail['config'].update(WorkingDir='/app', Healthcheck=sample['config']['Healthcheck'])
        detail['config']['Env'].append('PATH=/usr/bin')
        image['config'].update(WorkingDir='/app', Healthcheck=None)
        image['config']['Env'].append('PATH=/usr/bin')
    api = next(d for d in details if d['id'] == rows[0]['id'])
    volume_records = []
    if case in {'volume_good', 'volume_changed', 'volume_options'}:
        data = policy_root / 'volume-data'
        data.mkdir()
        model['volumes']['owned'] = dict(name='synthetic-owned')
        model['services']['rec-api']['volumes'].append(dict(type='volume', source='owned', target='/data'))
        api['mounts'].append(dict(Type='volume', Name='synthetic-owned', Source=str(data),
                                  Destination='/data', Driver='local', RW=True, Propagation=''))
        volume_records = [dict(name='synthetic-owned', driver='local', scope='local',
                               options={} if case != 'volume_options' else {'type': 'none', 'o': 'bind', 'device': '/foreign'},
                               mountpoint=str(data))]
    if case == 'policy_drift':
        api['host']['Privileged'] = True
    if case == 'poisoned_env':
        monkeypatch.setenv('COMPOSE_FILE', '/must/not/read')
        monkeypatch.setenv('TWOBRAIN_RUNTIME_SECRET_GID', '99999')
        (tmp_path / '.env').write_text('LD_PRELOAD=/must/not/read\n')
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
    model_count = volume_count = 0

    async def command(argv, *, deadline, cwd=None):
        nonlocal inspect_count, release_count, postal_count, model_count, volume_count
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
        if argv[1:3] == ['volume', 'inspect']:
            volume_count += 1
            assert argv[-1] == 'synthetic-owned'
            current = copy.deepcopy(volume_records)
            if volume_count == 2 and case == 'volume_changed':
                current[0]['options'] = {'type': 'none', 'o': 'bind', 'device': '/foreign'}
            return b'\n'.join(json.dumps(v).encode() for v in current)
        if argv[1] == 'compose':
            model_count += 1
            assert cwd == tmp_path / 'infra'
            assert argv == ['docker', 'compose', '--env-file', '/dev/null', '--profile', 'operations',
                            '-f', str(tmp_path / 'infra/docker-compose.yml'), 'config', '--no-interpolate',
                            '--no-env-resolution', '--no-path-resolution', '--format', 'json']
            current = copy.deepcopy(model)
            if model_count == 2 and case == 'model_changed':
                current['x-changed-source'] = True
            if model_count == 2 and case == 'registry_changed':
                replacement = policy_root / 'replacement'
                replacement.write_text('synthetic-only')
                replacement.chmod(0o640)
                replacement.replace(policy_root / 'shared-secret')
            return json.dumps(current).encode()
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

    def process(pid, **kwargs):
        nonlocal process_count
        process_count += 1
        return pid, process_count if case == 'process_changed' else 12345

    monkeypatch.setattr(operator, '_local_docker', socket)
    monkeypatch.setattr(operator, '_process_identity', process)
    from contextlib import asynccontextmanager, contextmanager

    guard_state = dict(active=False, exited=False)
    runtime_fingerprints = []
    original_digest = operator._json_digest

    def digest(value):
        if isinstance(value, dict) and 'containers' in value:
            runtime_fingerprints.append(value)
        return original_digest(value)

    monkeypatch.setattr(operator, '_json_digest', digest)

    @asynccontextmanager
    async def guard_units(**kwargs):
        assert kwargs['snapshot'] == tmp_path
        assert kwargs['deadline'] > time.monotonic()
        if case == 'guard_failure':
            raise ActivationHold('synthetic_guard_unverified')
        guard_state['active'] = True
        try:
            yield '6' * 64
            if case == 'late_guard_exit':
                raise ActivationHold('synthetic_guard_changed')
        finally:
            guard_state.update(active=False, exited=True)

    monkeypatch.setattr(operator, '_runtime_guard_units', guard_units, raising=False)
    checked_settings = []

    @contextmanager
    def settings(row, **kwargs):
        checked_settings.append(row['id'])
        yield None, 'f' * 64

    monkeypatch.setattr(operator, '_runtime_settings', settings)
    checked_operations = []

    @contextmanager
    def operations(row, **kwargs):
        checked_operations.append(row['id'])
        if case == 'operations_failure':
            raise ActivationHold('synthetic_operations_failure')
        yield (('9' if case == 'operations_mismatch' and len(checked_operations) > 1 else '8') * 64,
               b'changed' if case == 'raw_mismatch' and len(checked_operations) > 1
               else b'legal_basis_state_version=2\n# private-register-sentinel\n')
        if case == 'late_operations_close':
            monkeypatch.setattr(operator, 'time', SimpleNamespace(monotonic=lambda: time.monotonic()+60))

    monkeypatch.setattr(operator, '_runtime_operations', operations)
    @contextmanager
    def owner_password(row, **kwargs):
        assert row['id'] == next(r['id'] for r in rows if r['service'] == 'rec-postgres')
        yield 'synthetic-owner', 'e' * 64
        if case == 'late_secret_close':
            monkeypatch.setattr(operator, 'time', SimpleNamespace(monotonic=lambda: time.monotonic()+60))

    @asynccontextmanager
    async def databases(**kwargs):
        assert guard_state['active']
        assert kwargs['password'] == 'synthetic-owner'
        assert kwargs['register_raw'] == b'legal_basis_state_version=2\n# private-register-sentinel\n'
        assert set(kwargs['settings']) == {r['service'] for r in rows
            if r['service'] in operator.WRITERS and r['state']['running']}
        yield None, None, {'synthetic-database': True}
        assert guard_state['active']
        if case == 'late_database_close':
            monkeypatch.setattr(operator, 'time', SimpleNamespace(monotonic=lambda: time.monotonic()+60))

    pg = next(r for r in rows if r['service'] == 'rec-postgres')
    pg['networks'][operator.PRIVATE].update(IPAddress='172.19.0.2', IPPrefixLen=16)
    next(n for n in networks if n['name'] == operator.PRIVATE)['containers'][pg['id']].update(
        IPv4Address='172.19.0.2/16')
    monkeypatch.setattr(operator, '_runtime_owner_password', owner_password)
    monkeypatch.setattr(operator, '_runtime_databases', databases)
    if case in {'good', 'optional_absent', 'poisoned_env', 'volume_good'}:
        result = asyncio.run(operator._runtime_preflight(
            root=tmp_path, snapshot=tmp_path, source=source, deadline=time.monotonic() + 20))
        assert volume_count == (2 if case == 'volume_good' else 0)
        assert model_count == 2
        assert result['runtime'] == 'verified' and result['source_sha'] == source
        assert 'private-register-sentinel' not in json.dumps(result)
        assert result['container_count'] == len(rows)
        assert len(result['runtime_sha256']) == 64
        assert guard_state == dict(active=False, exited=True)
        assert len(runtime_fingerprints) == 1 and runtime_fingerprints[0]['guard_units_sha256'] == '6' * 64
        assert set(checked_settings) == {r['id'] for r in rows if r['service'] in operator.WRITERS and r['state']['running']}
        assert set(checked_operations) == set(checked_settings)
    else:
        with pytest.raises(ActivationHold, match='register_mismatch' if case == 'raw_mismatch' else None):
            asyncio.run(operator._runtime_preflight(
                root=tmp_path, snapshot=tmp_path, source=source,
                deadline=time.monotonic() + (-1 if case == 'deadline' else 20)))
    if case in {'policy_drift', 'volume_options'}:
        assert not checked_settings
    assert not any(set(c) & {'stop', 'start', 'restart', 'up', 'exec', 'create', 'run'} for c in calls)


@pytest.mark.parametrize('case', ['good', 'postgres', 'uid', 'gid', 'map', 'stat', 'missing', 'groups_invalid', 'groups_duplicate'])
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
    if case == 'postgres':
        (proc / 'status').write_text('Uid:\t70\t70\t70\t70\nGid:\t70\t70\t70\t70\nGroups:\t70\n')
        assert operator._process_identity(123, proc_root=tmp_path, uid=70, gid=70) == (123, 12345, (70,))
    elif case == 'good':
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
        def destination(_root_fd, path, _groups, *, uid=100):
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


def _policy_sample(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    monkeypatch.setattr(operator, 'INSTALLATION_UID', os.getuid())
    if sys.platform != 'linux':
        monkeypatch.setattr(operator, '_settings_source_ancestors', lambda p: [])
        monkeypatch.setattr(operator, '_settings_no_acl', lambda fd: None)
    secret = root / 'shared-secret'
    secret.write_text('synthetic-only')
    secret.chmod(0o640)
    downloads = root / 'infra/runtime/public-downloads'
    downloads.mkdir(parents=True)
    model = dict(name='twobrain-rec', services={}, secrets={
        'shared': dict(file='${GRAF_TEST_FILE:-./secrets/shared}')}, volumes={})
    rows, images, ids = [], {}, {}
    for number, name in enumerate(operator.SERVICE_NETWORKS, 1):
        identifier, image = f'{number:064x}', 'sha256:' + f'{number:064x}'
        ids[name] = identifier
        config = dict(Entrypoint=None, Cmd=['python', '-m', 'synthetic'], WorkingDir='/app',
                      Env=['PATH=/usr/bin'], Healthcheck=None)
        images[image] = dict(config=copy.deepcopy(config))
        model['services'][name] = dict(logging=dict(driver='json-file', options={
            'max-size': '10m', 'max-file': '5'}))
        host = dict(UsernsMode='', NetworkMode=next(iter(operator.SERVICE_NETWORKS[name])),
                    Privileged=False, AutoRemove=False, RestartPolicy={'Name': 'no', 'MaximumRetryCount': 0},
                    CapAdd=None, Devices=[], DeviceRequests=None,
                    DeviceCgroupRules=None, VolumesFrom=None, PidMode='', IpcMode='private',
                    UTSMode='', CgroupnsMode='private', Links=None, ExtraHosts=None, Dns=[],
                    DnsOptions=[], DnsSearch=[], Sysctls=None, ReadonlyRootfs=False, Init=None,
                    CapDrop=None, SecurityOpt=None, GroupAdd=None, Memory=0, NanoCpus=0,
                    PidsLimit=None, PortBindings={}, PublishAllPorts=False, Tmpfs=None,
                    LogConfig=dict(Type='json-file', Config={'max-size': '10m', 'max-file': '5'}))
        rows.append(dict(id=identifier, image=image, config=config, host=host, mounts=[]))
    api, worker = rows[:2]
    model['services']['rec-api'].update(
        ports=[dict(host_ip='127.0.0.1', published='18081', target=8080, protocol='tcp')],
        volumes=[dict(type='bind', source='./runtime/public-downloads',
                      target='/downloads', read_only=True)],
        healthcheck=dict(test=['CMD', 'python', '-c', 'pass'], interval='10s', timeout='8s',
                         start_period='20s', retries=3))
    api['host']['PortBindings'] = {'8080/tcp': [dict(HostIp='127.0.0.1', HostPort='18081')]}
    api['config']['Healthcheck'] = dict(Test=['CMD', 'python', '-c', 'pass'],
                                      Interval=10_000_000_000, Timeout=8_000_000_000,
                                      StartPeriod=20_000_000_000, StartInterval=0, Retries=3)
    api['mounts'].append(dict(Type='bind', Source=str(downloads), Destination='/downloads',
                              RW=False, Propagation='rprivate'))
    for row in (api, worker):
        name = next(n for n, identifier in ids.items() if identifier == row['id'])
        model['services'][name]['secrets'] = [dict(source='shared', target='shared-key')]
        row['mounts'].append(dict(Type='bind', Source=str(secret),
                                 Destination='/run/secrets/shared-key', RW=False, Propagation='rprivate'))
    return root, model, rows, images, ids


@pytest.mark.parametrize('defect', [
    'good', 'autoremove', 'restart', 'restart_retry', 'user', 'command', 'entrypoint', 'working_dir', 'loader', 'healthcheck', 'privileged',
    'cap_add', 'device', 'device_request', 'device_rule', 'pid', 'ipc', 'uts', 'userns',
    'network', 'sysctl', 'dns', 'extra_hosts', 'volumes_from', 'readonly', 'init',
    'cap_drop', 'security_opt', 'memory', 'cpu', 'pids', 'port', 'extra_port', 'publish_all',
    'missing_mount', 'extra_mount', 'writable_mount', 'wrong_bind', 'propagation',
    'secret_mismatch', 'static_secret', 'public_secret', 'secret_link', 'tmpfs', 'log',
    'command_interpolation', 'source_services',
])
def test_runtime_policy_rejects_actual_configuration_drift(tmp_path, monkeypatch, defect):
    root, model, rows, images, ids = _policy_sample(tmp_path, monkeypatch)
    api, worker = rows[:2]
    config, host = api['config'], api['host']
    changes = {
        'autoremove': ('AutoRemove', True),
        'restart': ('RestartPolicy', {'Name': 'always', 'MaximumRetryCount': 0}),
        'restart_retry': ('RestartPolicy', {'Name': 'no', 'MaximumRetryCount': 5}),
        'privileged': ('Privileged', True), 'cap_add': ('CapAdd', ['SYS_ADMIN']),
        'device': ('Devices', [dict(PathOnHost='/dev/mem')]),
        'device_request': ('DeviceRequests', [dict(Count=-1)]),
        'device_rule': ('DeviceCgroupRules', ['a *:* rwm']),
        'pid': ('PidMode', 'host'), 'ipc': ('IpcMode', 'host'), 'uts': ('UTSMode', 'host'),
        'userns': ('UsernsMode', 'host'), 'network': ('NetworkMode', 'host'),
        'sysctl': ('Sysctls', {'net.ipv4.ip_forward': '1'}), 'dns': ('Dns', ['192.0.2.1']),
        'extra_hosts': ('ExtraHosts', ['rec-postgres:192.0.2.1']),
        'volumes_from': ('VolumesFrom', ['foreign']), 'readonly': ('ReadonlyRootfs', True),
        'init': ('Init', True), 'cap_drop': ('CapDrop', ['ALL']),
        'security_opt': ('SecurityOpt', ['seccomp:unconfined']), 'memory': ('Memory', 1),
        'cpu': ('NanoCpus', 1), 'pids': ('PidsLimit', 1), 'publish_all': ('PublishAllPorts', True),
        'tmpfs': ('Tmpfs', {'/app': 'rw'}), 'log': ('LogConfig', {'Type': 'none', 'Config': {}}),
    }
    if defect in changes:
        key, value = changes[defect]
        host[key] = value
    if defect in {'command', 'entrypoint', 'working_dir'}:
        config[{'command': 'Cmd', 'entrypoint': 'Entrypoint', 'working_dir': 'WorkingDir'}[defect]] = (
            '/tmp' if defect == 'working_dir' else ['sh', '-c', 'true'])
    if defect == 'user':
        config['User'] = 'foreign'
    if defect == 'loader':
        config['Env'].append('LD_PRELOAD=/tmp/foreign.so')
    if defect == 'healthcheck':
        config['Healthcheck']['Test'] = ['CMD', 'true']
    if defect == 'port':
        host['PortBindings']['8080/tcp'][0]['HostIp'] = '0.0.0.0'
    if defect == 'extra_port':
        host['PortBindings']['5432/tcp'] = [dict(HostIp='0.0.0.0', HostPort='5432')]
    if defect == 'missing_mount':
        api['mounts'].pop(0)
    if defect == 'extra_mount':
        api['mounts'].append(dict(Type='bind', Source='/', Destination='/host', RW=True))
    if defect in {'writable_mount', 'wrong_bind', 'propagation'}:
        key, value = {'writable_mount': ('RW', True), 'wrong_bind': ('Source', str(root)),
                      'propagation': ('Propagation', 'rshared')}[defect]
        api['mounts'][0][key] = value
    if defect == 'secret_mismatch':
        alternate = root / 'alternate'
        alternate.write_text('synthetic-only')
        alternate.chmod(0o640)
        worker['mounts'][0]['Source'] = str(alternate)
    if defect == 'static_secret':
        model['secrets']['shared']['file'] = './secrets/other'
    if defect == 'public_secret':
        (root / 'shared-secret').chmod(0o644)
    if defect == 'secret_link':
        target = root / 'shared-secret'
        target.rename(root / 'actual-secret')
        target.symlink_to(root / 'actual-secret')
    if defect == 'command_interpolation':
        model['services']['rec-api']['command'] = ['sh', '-c', '$UNVERIFIED']
    if defect == 'source_services':
        model['services']['foreign'] = {}
    def call():
        return operator._runtime_policy(rows, images, model, ids=ids, root=root,
                                        postal_network='postal-network')
    if defect == 'good':
        assert len(call()) == 64
    else:
        with pytest.raises(ActivationHold):
            call()


@pytest.mark.parametrize('entrypoint,command,image_entrypoint,expected_entrypoint,expected_command', [
    (None, None, None, [], ['image-default']),
    ([], [], None, [], ['image-default']),
    (['sh', '-c', 'printf "$$HOME"\n'], None, None, ['sh', '-c', 'printf "$HOME"\n'], []),
    (None, ['custom', 'one argument'], ['wrapper'], ['wrapper'], ['custom', 'one argument']),
    ([], None, ['wrapper'], [], ['image-default']),
])
def test_runtime_policy_matches_native_docker_argv_merge(
    tmp_path, monkeypatch, entrypoint, command, image_entrypoint, expected_entrypoint, expected_command
):
    root, model, rows, images, ids = _policy_sample(tmp_path, monkeypatch)
    spec = model['services']['rec-api']
    spec.update(entrypoint=entrypoint, command=command)
    images[rows[0]['image']]['config'].update(Entrypoint=image_entrypoint, Cmd=['image-default'])
    rows[0]['config'].update(Entrypoint=expected_entrypoint, Cmd=expected_command)
    assert len(operator._runtime_policy(rows, images, model, ids=ids, root=root,
                                        postal_network='postal-network')) == 64


@pytest.mark.parametrize('defect', ['good', 'volume_name', 'volume_type', 'subpath', 'limit_conflict',
                                   'tmpfs_target', 'tmpfs_options', 'secret_replaced', 'health_interval',
                                   'volume_driver', 'volume_scope', 'volume_bind_device', 'volume_mountpoint',
                                   'volume_missing', 'volume_link', 'secret_generated_name', 'wrong_secret_name'])
def test_runtime_policy_restricted_profile_and_secret_aliases(tmp_path, monkeypatch, defect):
    root, model, rows, images, ids = _policy_sample(tmp_path, monkeypatch)
    api = rows[0]
    spec = model['services']['rec-api']
    spec.update(read_only=True, init=True, cap_drop=['ALL'], security_opt=['no-new-privileges:true'],
                cpus='1.0', mem_limit='1g', pids_limit=128,
                group_add=['${TWOBRAIN_RUNTIME_SECRET_GID:-1001}'],
                deploy=dict(resources=dict(limits=dict(cpus='1', memory='1073741824', pids=128))),
                tmpfs=['/tmp:rw,noexec,size=64m'])
    spec['secrets'].append(dict(source='shared', target='alias'))
    model['secrets']['shared']['file'] = str(root / 'shared-secret')
    spec['volumes'].append(dict(type='volume', source='owned', target='/owned'))
    model['volumes']['owned'] = dict(name='synthetic-owned')
    data = root / 'volume-data'
    data.mkdir()
    volumes = {'synthetic-owned': dict(name='synthetic-owned', driver='local', scope='local',
                                      options=None, mountpoint=str(data))}
    host = api['host']
    host.update(ReadonlyRootfs=True, Init=True, CapDrop=['ALL'], SecurityOpt=['no-new-privileges:true'],
                Memory=1024**3, NanoCpus=10**9, PidsLimit=128, GroupAdd=['1001'],
                Tmpfs={'/tmp': 'rw,noexec,size=64m'},
                Mounts=[dict(Type='volume', Source='synthetic-owned', Target='/owned', VolumeOptions={})])
    api['mounts'].extend([
        dict(Type='bind', Source=str(root / 'shared-secret'), Destination='/run/secrets/alias', RW=False, Propagation='rprivate'),
        dict(Type='volume', Name='synthetic-owned', Source=str(data),
             Driver='local', Destination='/owned', RW=True, Propagation=''),
    ])
    if defect in {'secret_generated_name', 'wrong_secret_name'}:
        model['secrets']['shared']['name'] = 'twobrain-rec_shared' if defect == 'secret_generated_name' else 'foreign'
    if defect.startswith('volume_') and defect not in {'volume_name', 'volume_type', 'volume_missing', 'volume_link'}:
        key, value = {'volume_driver': ('driver', 'foreign'), 'volume_scope': ('scope', 'global'),
                      'volume_bind_device': ('options', {'type': 'none', 'o': 'bind', 'device': '/foreign'}),
                      'volume_mountpoint': ('mountpoint', str(root))}[defect]
        volumes['synthetic-owned'][key] = value
    if defect == 'volume_missing':
        volumes.clear()
    if defect == 'volume_link':
        data.rmdir()
        data.symlink_to(root, target_is_directory=True)
    if defect == 'volume_name':
        api['mounts'][-1]['Name'] = 'foreign'
    if defect == 'volume_type':
        api['mounts'][-1]['Type'] = 'bind'
    if defect == 'subpath':
        host['Mounts'][0]['VolumeOptions'] = {'Subpath': 'foreign'}
    if defect == 'limit_conflict':
        spec['deploy']['resources']['limits']['memory'] = '2g'
    if defect == 'tmpfs_target':
        api['mounts'].append(dict(Type='tmpfs', Destination='/foreign', Source='', RW=True))
    if defect == 'tmpfs_options':
        host['Tmpfs']['/tmp'] = 'rw,exec'
    if defect == 'health_interval':
        api['config']['Healthcheck']['Interval'] += 1
    if defect == 'secret_replaced':
        original = operator._settings_no_acl
        calls = 0
        inode = (root / 'shared-secret').stat().st_ino

        def swap(fd):
            nonlocal calls
            original(fd)
            if os.fstat(fd).st_ino == inode:
                calls += 1
            if calls == 2:
                replacement = root / 'new-inode'
                replacement.write_text('synthetic-only')
                replacement.chmod(0o640)
                replacement.replace(root / 'shared-secret')

        monkeypatch.setattr(operator, '_settings_no_acl', swap)
    def call():
        return operator._runtime_policy(rows, images, model, ids=ids, root=root,
                                        postal_network='postal-network', volumes=volumes)
    if defect in {'good', 'secret_generated_name'}:
        assert len(call()) == 64
        # Daemon may also include tmpfs mounts; both shapes are legitimate.
        api['mounts'].append(dict(Type='tmpfs', Source='', Destination='/tmp', RW=True,
                                 Mode='rw,noexec,size=64m'))
        assert len(call()) == 64
    else:
        with pytest.raises(ActivationHold):
            call()


@pytest.mark.parametrize('case', ['good', 'dns', 'loopback', 'multicast', 'unspecified',
    'ipv6', 'network_id', 'peer_ip', 'missing', 'broadcast'])
def test_database_address_comes_from_both_actual_network_views(case):
    rows, networks = inventory()
    pg = next(r for r in rows if r['service'] == 'rec-postgres')
    endpoint = pg['networks'][operator.PRIVATE]
    endpoint.update(IPAddress='172.19.0.2', IPPrefixLen=16)
    network = next(n for n in networks if n['name'] == operator.PRIVATE)
    peer = network['containers'][pg['id']]
    peer['IPv4Address'] = '172.19.0.2/16'
    if case in {'dns', 'loopback', 'multicast', 'unspecified', 'ipv6', 'broadcast'}:
        endpoint['IPAddress'] = dict(dns='rec-postgres', loopback='127.0.0.1',
            multicast='224.0.0.1', unspecified='0.0.0.0', ipv6='::1',
            broadcast='172.19.255.255')[case]
    if case == 'network_id':
        endpoint['NetworkID'] = 'f' * 64
    if case == 'peer_ip':
        peer['IPv4Address'] = '172.19.0.3/16'
    if case == 'missing':
        endpoint.pop('IPAddress')
    if case == 'good':
        assert operator._runtime_database_address(rows, networks) == '172.19.0.2'
    else:
        with pytest.raises(ActivationHold):
            operator._runtime_database_address(rows, networks)


@pytest.mark.parametrize('case', ['good', 'host', 'driver', 'port', 'database', 'role',
    'query', 'password', 'prompt', 'missing_writer', 'unknown_writer'])
def test_runtime_database_urls_are_closed_before_connect(case):
    settings = {name: SimpleNamespace(database_url=
        f'postgresql+asyncpg://{role}:synthetic-password@rec-postgres:5432/twobrain_rec',
        prompt_optimization_database_url=None) for name, role in {
            'rec-api': 'twobrain_rec_app', 'rec-processing-worker': 'twobrain_rec_app',
            'rec-media-worker': 'twobrain_rec_media',
            'rec-maintenance': 'twobrain_rec_maintenance',
            'rec-prompt-optimization-worker': 'twobrain_rec_maintenance',
        }.items()}
    replacements = dict(host=('rec-postgres', 'other'), driver=('postgresql+asyncpg', 'postgresql'),
        port=(':5432/', ':6432/'), database=('/twobrain_rec', '/other'),
        role=('twobrain_rec_app:', 'twobrain_rec:'), password=('synthetic-password', ''))
    if case in replacements:
        before, after = replacements[case]
        settings['rec-api'].database_url = settings['rec-api'].database_url.replace(before, after)
    if case == 'query':
        settings['rec-api'].database_url += '?host=other'
    if case == 'prompt':
        settings['rec-prompt-optimization-worker'].prompt_optimization_database_url = settings['rec-api'].database_url
    if case == 'missing_writer':
        settings.pop('rec-media-worker')
    if case == 'unknown_writer':
        settings['unknown'] = settings['rec-api']
    if case == 'good':
        urls = operator._runtime_database_urls(settings)
        assert len(urls) == 5
        assert {u.username for u in urls} == {'twobrain_rec_app', 'twobrain_rec_media', 'twobrain_rec_maintenance'}
    else:
        with pytest.raises(ActivationHold):
            operator._runtime_database_urls(settings)


@pytest.mark.parametrize('stage', ['connect', 'connect_error', 'connect_race', 'body', 'close', 'close_error'])
def test_physical_connection_waits_through_repeated_cancellation(monkeypatch, stage):
    import asyncpg

    async def run():
        connected, closing, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
        counts = dict(closed=0, terminated=0)
        class Connection:
            async def close(self, *, timeout):
                assert timeout <= 3
                closing.set()
                if stage == 'close':
                    await release.wait()
                if stage == 'close_error':
                    raise TimeoutError
                counts['closed'] += 1
            def is_closed(self):
                return bool(counts['closed'])
            def terminate(self):
                counts['terminated'] += 1
        connection = Connection()
        async def connect(**kwargs):
            assert kwargs['timeout'] <= 3 and kwargs['command_timeout'] <= 3
            assert kwargs['server_settings']['search_path'] == '"$user", public'
            connected.set()
            if stage == 'connect_race':
                raise OSError('synthetic simultaneous connection failure')
            if stage in {'connect', 'connect_error'}:
                await release.wait()
            if stage == 'connect_error':
                raise OSError('synthetic connection failure')
            return connection
        monkeypatch.setattr(asyncpg, 'connect', connect)
        entered = asyncio.Event()
        async def operation():
            async with operator._physical_connection(host='172.19.0.2', user='synthetic',
                    password='synthetic', database='postgres', deadline=time.monotonic()+10):
                entered.set()
                if stage == 'body':
                    await release.wait()
        task = asyncio.create_task(operation())
        await asyncio.wait_for(connected.wait(), 2)
        if stage == 'body':
            await entered.wait()
        if stage in {'close', 'close_error'}:
            await closing.wait()
        if stage != 'close_error':
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
            if stage in {'connect', 'connect_error', 'close'}:
                assert not task.done()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert counts == dict(closed=0 if stage in {'connect_error', 'connect_race'} else 1, terminated=0)
        else:
            with pytest.raises(TimeoutError):
                await task
            assert counts == dict(closed=0, terminated=1)
    asyncio.run(run())


@pytest.mark.parametrize('case', ['good', 'password_env', 'auth_env', 'duplicate', 'path',
    'empty', 'changed', 'process_changed', 'root_changed'])
def test_postgres_owner_secret_uses_bound_file_without_daemon_leaf_read(tmp_path, monkeypatch, case):
    from contextlib import contextmanager

    secret = tmp_path / 'owner-secret'
    secret.write_bytes(b'synthetic-owner-password\n')
    secret.chmod(0o600)  # Deliberately no daemon group-read; root entrypoint reads it.
    proc = tmp_path / 'proc/123'
    proc.mkdir(parents=True)
    first_root, other_root = tmp_path / 'first-root', tmp_path / 'other-root'
    first_root.mkdir()
    other_root.mkdir()
    (proc / 'root').symlink_to(first_root, target_is_directory=True)
    process = (123, 456, (70,))
    calls = 0
    def identity(pid, *, uid, gid, **kwargs):
        nonlocal calls
        assert (pid, uid, gid) == (123, 70, 70)
        calls += 1
        return (123, 457, (70,)) if case == 'process_changed' and calls > 1 else process
    monkeypatch.setattr(operator, '_process_identity', identity)
    monkeypatch.setattr(operator, 'INSTALLATION_UID', os.geteuid())
    monkeypatch.setattr(operator, '_settings_source_ancestors', lambda p: [])
    monkeypatch.setattr(operator, '_settings_no_acl', lambda fd: None)
    @contextmanager
    def destination(root_fd, path, groups, *, uid):
        assert uid == 70 and groups == {70}
        assert str(path) == '/run/secrets/twobrain_postgres_password'
        fd = os.open(secret, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            yield fd
        finally:
            os.close(fd)
    monkeypatch.setattr(operator, '_settings_destination', destination)
    environment = ['POSTGRES_USER=twobrain_rec', 'POSTGRES_DB=twobrain_rec',
                   'POSTGRES_PASSWORD_FILE=/run/secrets/twobrain_postgres_password']
    if case == 'password_env':
        environment.append('POSTGRES_PASSWORD=synthetic')
    if case == 'auth_env':
        environment.append('POSTGRES_HOST_AUTH_METHOD=trust')
    if case == 'duplicate':
        environment.append('postgres_user=twobrain_rec')
    if case == 'path':
        environment[-1] += '-other'
    if case == 'empty':
        secret.write_bytes(b'')
    row = dict(config=dict(Env=environment), mounts=[dict(Type='bind', RW=False,
        Source=str(secret), Destination='/run/secrets/twobrain_postgres_password')])
    def check():
        with operator._runtime_owner_password(row, root=tmp_path, process=process,
                proc_root=tmp_path / 'proc') as (password, proof):
            assert password == 'synthetic-owner-password' and len(proof) == 64
            if case == 'changed':
                secret.write_bytes(b'changed')
            if case == 'root_changed':
                (proc / 'root').unlink()
                (proc / 'root').symlink_to(other_root, target_is_directory=True)
    if case == 'good':
        check()
    else:
        with pytest.raises(ActivationHold):
            check()


def _guard_unit_sample(directory):
    service, timer = ("graf-posthog-runtime-guard." + suffix for suffix in ("service", "timer"))
    installed = directory / "installed-units"
    installed.mkdir()
    snapshot = directory / "snapshot"
    (snapshot / "infra/posthog").mkdir(parents=True)
    for name in (service, timer):
        (installed / name).write_text("synthetic unit " + name)
        (installed / name).chmod(0o644)
        (snapshot / "infra/posthog" / name).write_bytes((installed / name).read_bytes())
    properties = {}
    for name in (service, timer):
        for key, pair in {
            "Id": ("s", name),
            "Names": ("as", [name]),
            "FragmentPath": ("s", str(installed / name)),
            "SourcePath": ("s", ""),
            "DropInPaths": ("as", []),
            "LoadState": ("s", "loaded"),
            "NeedDaemonReload": ("b", False),
            "Transient": ("b", False),
            "UnitFileState": ("s", "enabled" if name == timer else "static"),
            "ActiveState": ("s", "active" if name == timer else "activating"),
            "SubState": ("s", "waiting" if name == timer else "start"),
        }.items():
            properties[name, "Unit", key] = dict(type=pair[0], data=pair[1])
    for key, pair in {
        "Unit": ("s", service),
        "TimersMonotonic": (
            "a(stt)",
            [["OnBootUSec", 120000000, 5], ["OnUnitActiveUSec", 60000000, 6]],
        ),
        "TimersCalendar": ("a(sst)", []),
        "AccuracyUSec": ("t", 1000000),
        "RandomizedDelayUSec": ("t", 0),
        "Persistent": ("b", True),
        "WakeSystem": ("b", False),
        "RemainAfterElapse": ("b", True),
        "OnClockChange": ("b", False),
        "OnTimezoneChange": ("b", False),
    }.items():
        properties[timer, "Timer", key] = dict(type=pair[0], data=pair[1])
    argv = [
        "/usr/bin/env",
        "GRAF_POSTHOG_STORAGE_STATE_DIR=/var/lib/graf-posthog-storage",
        "GRAF_POSTHOG_STORAGE_STATE_FILE=/var/lib/graf-posthog-storage/storage-growth-state",
        "/usr/local/libexec/graf-posthog-runtime-guard.sh",
    ]
    for key, pair in {
        "Type": ("s", "oneshot"),
        "User": ("s", "root"),
        "Group": ("s", ""),
        "DynamicUser": ("b", False),
        "RemainAfterExit": ("b", False),
        "ExecStart": ("a(sasbttttuii)", [["/usr/bin/env", argv, False, *([0] * 7)]]),
        "ExecStartEx": ("a(sasasttttuii)", [["/usr/bin/env", argv, [], *([0] * 7)]]),
        **{
            key: ("a(sasbttttuii)", [])
            for key in (
                "ExecCondition",
                "ExecStartPre",
                "ExecStartPost",
                "ExecReload",
                "ExecStop",
                "ExecStopPost",
            )
        },
        **{key: ("as", []) for key in ("Environment", "PassEnvironment", "UnsetEnvironment")},
        "EnvironmentFiles": ("a(sb)", [["/etc/graf-posthog-runtime-guard.env", True]]),
        "ProtectSystem": ("s", "strict"),
        "ProtectHome": ("s", "yes"),
        "PrivateTmp": ("b", True),
        "NoNewPrivileges": ("b", True),
        "RootDirectory": ("s", ""),
        "RootImage": ("s", ""),
        "BindPaths": ("a(ssbt)", []),
        "BindReadOnlyPaths": ("a(ssbt)", []),
        "TemporaryFileSystem": ("a(ss)", []),
        "ReadWritePaths": (
            "as",
            [
                "/var/lib/graf-posthog-runtime-guard",
                "/var/lib/graf-posthog-storage",
                "/opt/projects/2brain-rec",
            ],
        ),
    }.items():
        properties[service, "Service", key] = dict(type=pair[0], data=pair[1])
    return installed, snapshot, properties, service, timer


@pytest.mark.skipif(
    sys.platform != "linux" or os.geteuid() != 0, reason="Linux root installed unit boundary"
)
@pytest.mark.parametrize(
    "case",
    [
        "good",
        "tick",
        "write_paths_order",
        "missing",
        "mode",
        "owner",
        "gid",
        "hardlink",
        "symlink",
        "ancestor_link",
        "ancestor_owner",
        "ancestor_writable",
        "acl",
        "empty",
        "oversize_file",
        "file_before_yield",
        "file_after_yield",
        "file_replaced",
        "source_changed",
        "directory_replaced",
        "bad_json",
        "duplicate_key",
        "extra_key",
        "wrong_signature",
        "oversize_response",
        "bus_override",
        "bus_override_during_query",
        "bus_override_after_yield",
        "command_failed",
        "cancel_property",
        "wrong_fragment",
        "dropin",
        "reload",
        "transient",
        "disabled",
        "stopped",
        "failed_service",
        "calendar",
        "extra_interval",
        "bad_interval",
        "negative_tick",
        "bool_tick",
        "wrong_accuracy",
        "random_delay",
        "bool_as_int",
        "extra_command",
        "wrong_argv",
        "ignore_failure",
        "exec_flags",
        "flags_string",
        "exec_history_bool",
        "extra_environment",
        "wrong_envfile",
        "sandbox",
        "root_directory",
        "bind",
        "wrong_write_paths",
        "exit_drift",
        "deadline",
    ],
)
def test_runtime_guard_units_pin_files_and_effective_properties(tmp_path, monkeypatch, case):
    directory = tmp_path.resolve()
    for parent in (directory, *directory.parents):
        if str(parent).startswith("/owned"):
            parent.chmod(0o755)
    installed, snapshot, properties, service, timer = _guard_unit_sample(directory)
    monkeypatch.setattr(operator, "SYSTEMD_UNIT_DIR", installed, raising=False)
    monkeypatch.delenv("DBUS_SYSTEM_BUS_ADDRESS", raising=False)
    selected = installed / timer
    if case == "missing":
        selected.unlink()
    if case == "mode":
        selected.chmod(0o666)
    if case == "owner":
        os.chown(selected, 1, 0)
    if case == "gid":
        os.chown(selected, 0, 1)
    if case == "hardlink":
        os.link(selected, directory / "linked")
    if case == "symlink":
        selected.unlink()
        selected.symlink_to(installed / service)
    if case == "ancestor_link":
        installed.rename(directory / "actual-units")
        installed.symlink_to(directory / "actual-units", target_is_directory=True)
    if case == "ancestor_owner":
        os.chown(installed, 1, 0)
    if case == "ancestor_writable":
        installed.chmod(0o777)
    if case == "acl":
        import struct

        entries = [(1, 6, 0xffffffff), (2, 4, 12345), (4, 4, 0xffffffff),
                   (16, 4, 0xffffffff), (32, 4, 0xffffffff)]
        acl = struct.pack("<I", 2) + b"".join(struct.pack("<HHI", *e) for e in entries)
        os.setxattr(selected, "system.posix_acl_access", acl)
        assert selected.stat().st_mode & 0o777 == 0o644
    if case == "empty":
        selected.write_bytes(b"")
    if case == "oversize_file":
        selected.write_bytes(b"x" * 65537)
    if case == "bus_override":
        monkeypatch.setenv("DBUS_SYSTEM_BUS_ADDRESS", "unix:path=/must-not-be-read")
    defects = {
        "wrong_fragment": (timer, "Unit", "FragmentPath", "/foreign"),
        "dropin": (timer, "Unit", "DropInPaths", ["/foreign"]),
        "reload": (timer, "Unit", "NeedDaemonReload", True),
        "transient": (timer, "Unit", "Transient", True),
        "disabled": (timer, "Unit", "UnitFileState", "disabled"),
        "stopped": (timer, "Unit", "ActiveState", "inactive"),
        "failed_service": (service, "Unit", "ActiveState", "failed"),
        "calendar": (timer, "Timer", "TimersCalendar", [["OnCalendar", "*-*-* 00:00:00", 1]]),
        "wrong_accuracy": (timer, "Timer", "AccuracyUSec", 60000000),
        "random_delay": (timer, "Timer", "RandomizedDelayUSec", 1),
        "bool_as_int": (timer, "Timer", "Persistent", 1),
        "extra_command": (
            service,
            "Service",
            "ExecStartPre",
            [["/foreign", [], False, *([0] * 7)]],
        ),
        "extra_environment": (
            service,
            "Service",
            "Environment",
            ["SECRET_SENTINEL=must-not-be-exported"],
        ),
        "wrong_envfile": (service, "Service", "EnvironmentFiles", [["/foreign", True]]),
        "sandbox": (service, "Service", "ProtectSystem", "no"),
        "root_directory": (service, "Service", "RootDirectory", "/foreign"),
        "bind": (service, "Service", "BindPaths", [["/foreign", "/usr", False, 0]]),
        "wrong_write_paths": (service, "Service", "ReadWritePaths", ["/"]),
    }
    if case in defects:
        name, interface, key, data = defects[case]
        properties[name, interface, key]["data"] = data
    monotonic = properties[timer, "Timer", "TimersMonotonic"]["data"]
    if case == "extra_interval":
        monotonic.append(["OnActiveUSec", 1, 1])
    if case == "bad_interval":
        monotonic[0][1] = 1
    if case == "negative_tick":
        monotonic[0][2] = -1
    if case == "bool_tick":
        monotonic[0][2] = True
    if case == "wrong_argv":
        properties[service, "Service", "ExecStart"]["data"][0][1] = ["/foreign"]
    if case == "ignore_failure":
        properties[service, "Service", "ExecStart"]["data"][0][2] = True
    if case == "exec_flags":
        properties[service, "Service", "ExecStartEx"]["data"][0][2] = ["privileged"]
    if case == "flags_string":
        properties[service, "Service", "ExecStartEx"]["data"][0][2] = ""
    if case == "exec_history_bool":
        properties[service, "Service", "ExecStartEx"]["data"][0][3] = False
    calls, reached, pids = [], [], []
    original_command = operator._command

    async def command(argv, *, deadline, cwd=None):
        assert argv[:5] == [
            "/usr/bin/busctl",
            "--json=short",
            "--system",
            "get-property",
            "org.freedesktop.systemd1",
        ]
        assert len(argv) == 8 and cwd is None
        calls.append(argv)
        if case == "cancel_property":
            pidfile = directory / "owned-property-child"
            program = (
                "import os,pathlib,time; pathlib.Path("
                + repr(str(pidfile))
                + ").write_text(str(os.getpid())); time.sleep(30)"
            )
            return await original_command([sys.executable, "-I", "-c", program], deadline=deadline)
        if case == "command_failed":
            raise ActivationHold("synthetic_property_unavailable")
        if case == "bus_override_during_query":
            monkeypatch.setenv("DBUS_SYSTEM_BUS_ADDRESS", "unix:path=/foreign")
        if case == "file_before_yield" and len(calls) == 1:
            selected.write_text("changed")
        if case == "bad_json":
            return b"not json"
        if case == "duplicate_key":
            return b'{"type":"s","type":"b","data":"loaded"}'
        if case == "oversize_response":
            return b" " * 65537
        name = (
            argv[5]
            .removeprefix("/org/freedesktop/systemd1/unit/")
            .replace("_2d", "-")
            .replace("_2e", ".")
        )
        interface = argv[6].removeprefix("org.freedesktop.systemd1.")
        data = copy.deepcopy(properties[name, interface, argv[7]])
        if case == "extra_key":
            data["untrusted"] = True
        if case == "wrong_signature":
            data["type"] = "v"
        return json.dumps(data).encode()

    monkeypatch.setattr(operator, "_command", command)
    before = set(os.listdir("/proc/self/fd"))

    async def check():
        async with operator._runtime_guard_units(
            snapshot=snapshot, deadline=time.monotonic() + (-1 if case == "deadline" else 10)
        ) as proof:
            reached.append(True)
            assert len(proof) == 64 and "SECRET_SENTINEL" not in proof
            if case == "tick":
                properties[service, "Unit", "ActiveState"]["data"] = "inactive"
                properties[service, "Unit", "SubState"]["data"] = "dead"
                properties[timer, "Unit", "SubState"]["data"] = "running"
                for row in monotonic:
                    row[2] += 100
                for key in ("ExecStart", "ExecStartEx"):
                    properties[service, "Service", key]["data"][0][3:] = list(range(7))
            if case == "write_paths_order":
                properties[service, "Service", "ReadWritePaths"]["data"].reverse()
            if case == "file_after_yield":
                selected.write_text("changed")
            if case == "file_replaced":
                selected.rename(directory / "old-unit")
                selected.write_bytes((directory / "old-unit").read_bytes())
                selected.chmod(0o644)
            if case == "source_changed":
                (snapshot / "infra/posthog" / timer).write_text("changed")
            if case == "directory_replaced":
                installed.rename(directory / "old-directory")
                installed.mkdir()
            if case == "exit_drift":
                properties[timer, "Timer", "AccuracyUSec"]["data"] = 60000000
            if case == "bus_override_after_yield":
                monkeypatch.setenv("DBUS_SYSTEM_BUS_ADDRESS", "unix:path=/foreign")

    async def cancel():
        task = asyncio.create_task(check())
        pidfile = directory / "owned-property-child"
        try:
            for _ in range(500):
                if pidfile.exists():
                    break
                await asyncio.sleep(0.01)
            assert pidfile.exists() and not reached
            pids.append(int(pidfile.read_text()))
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    try:
        if case in {"good", "tick", "write_paths_order"}:
            asyncio.run(check())
        elif case == "cancel_property":
            asyncio.run(cancel())
            with pytest.raises(ProcessLookupError):
                os.kill(pids[0], 0)
        else:
            with pytest.raises(ActivationHold):
                asyncio.run(check())
            if case not in {
                "file_after_yield",
                "file_replaced",
                "source_changed",
                "directory_replaced",
                "exit_drift",
                "bus_override_after_yield",
            }:
                assert not reached
        if case in {
            "bus_override",
            "missing",
            "mode",
            "owner",
            "gid",
            "hardlink",
            "symlink",
            "ancestor_link",
            "ancestor_owner",
            "ancestor_writable",
            "acl",
            "empty",
            "oversize_file",
            "deadline",
        }:
            assert not calls
    finally:
        assert set(os.listdir("/proc/self/fd")) == before
