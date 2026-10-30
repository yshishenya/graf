"""Concrete Docker inventory and owned subprocess lifetime, without product writes."""

import asyncio
import copy
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
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
