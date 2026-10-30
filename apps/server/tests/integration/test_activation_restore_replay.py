"""A real old dump, current deletion cases, and an isolated one-shot process."""

import asyncio
import importlib.util
import ipaddress
import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from tests.integration.test_deployment_backup_snapshot import REPO, capture, psql

pytestmark = pytest.mark.postgres
MODULE = "twobrain_rec_server.product_analytics.restore_replay"


def closed(path, value):
    path.write_text(value)
    path.chmod(0o600)
    return path


@pytest.fixture
def rehearsal_objects(tmp_path):
    import urllib3
    from minio import Minio

    token = uuid4().hex
    network = "graf-rehearsal-" + token
    container = "graf-rehearsal-minio-" + token
    user, password = uuid4().hex, uuid4().hex
    user_file = closed(tmp_path / "minio-user", user)
    password_file = closed(tmp_path / "minio-password", password)
    owned_network = owned_container = False

    def docker(*args):
        return subprocess.run(["docker", *args], capture_output=True, text=True, check=True,
                              timeout=45).stdout.strip()

    try:
        ids = docker("network", "ls", "--quiet").split()
        existing = json.loads(docker("network", "inspect", *ids)) if ids else []
        occupied = [ipaddress.ip_network(c["Subnet"]) for n in existing
                    for c in n["IPAM"]["Config"] or []
                    if c.get("Subnet") and ":" not in c["Subnet"]]
        subnet = next(n for n in ipaddress.ip_network("198.19.0.0/16").subnets(new_prefix=28)
                      if not any(n.overlaps(c) for c in occupied))
        network_id = docker("network", "create", "--subnet", str(subnet),
                            "--label", "org.2brain.graf.test-owner=" + token, network)
        owned_network = True
        image = docker("image", "inspect", "--format", "{{.Id}}",
                       "minio/minio:RELEASE.2025-05-24T17-08-30Z")
        mc_image = docker("image", "inspect", "--format", "{{.Id}}",
                          "minio/mc:RELEASE.2025-05-21T01-59-54Z")
        docker("run", "--detach", "--rm", "--pull=never", "--name", container,
               "--label", "org.2brain.graf.test-owner=" + token, "--network", network_id,
               "--network-alias", "rec-minio", "--publish", "127.0.0.1::9000",
               "--mount", f"type=bind,src={user_file},dst=/run/user-secret,readonly",
               "--mount", f"type=bind,src={password_file},dst=/run/password-secret,readonly",
               "--env", "MINIO_ROOT_USER_FILE=/run/user-secret",
               "--env", "MINIO_ROOT_PASSWORD_FILE=/run/password-secret",
               "--tmpfs", "/data:rw", image, "server", "/data")
        owned_container = True
        port = docker("port", container, "9000/tcp").rsplit(":", 1)[1]
        client = Minio(f"127.0.0.1:{port}", access_key=user, secret_key=password, secure=False,
                       http_client=urllib3.PoolManager(
                           timeout=urllib3.Timeout(connect=2, read=5), retries=False))
        deadline = time.monotonic() + 30
        while True:
            try:
                client.list_buckets()
                break
            except Exception:
                assert time.monotonic() < deadline, "owned_minio_start_timeout"
                time.sleep(.1)
        yield dict(client=client, network=network_id, mc_image=mc_image,
                   user_file=user_file, password_file=password_file)
    finally:
        if owned_container:
            labels = json.loads(docker("inspect", "--format", "{{json .Config.Labels}}", container))
            assert labels["org.2brain.graf.test-owner"] == token
            docker("rm", "--force", "--volumes", container)
        if owned_network:
            docker("network", "rm", network)


def test_staged_native_restore_replays_before_cleanup(replay_world, rehearsal_objects):
    import asyncpg
    from sqlalchemy import event, text

    from twobrain_rec_server.product_analytics import activation_operator as operator
    from twobrain_rec_server.product_analytics import restore_replay as replay

    world, objects = replay_world, rehearsal_objects
    reference = world["root"] / "reference"
    files = reference / "minio-objects"
    files.mkdir(mode=0o700)
    (files / "nested").mkdir(mode=0o700)
    closed(files / "nested/中文.txt", "Synthetic meeting only")
    closed(files / "empty.bin", "")

    async def run():
        url = world["url"]
        owner = await asyncpg.connect(host=url.host, port=url.port, user=url.username,
                                     password=url.password, database="postgres")
        pg_container = (await operator._command(
            ["docker", "inspect", "--format", "{{.Id}}", world["container"]],
            deadline=time.monotonic()+5)).decode().strip()
        cluster_id = await owner.fetchval("SELECT system_identifier::text FROM pg_control_system()")
        resources = None
        engines = []
        try:
            async with operator._rehearsal_resources(
                root=REPO, reference=reference, owner=owner, pg_container=pg_container,
                cluster_id=cluster_id, deadline=time.monotonic()+90, **objects,
            ) as resources:
                name, oid = resources["target"], resources["target_oid"]
                assert tuple(await owner.fetchrow(
                    "SELECT datallowconn,datconnlimit FROM pg_database WHERE oid=$1", oid
                )) == (True, 0)
                with pytest.raises(asyncpg.TooManyConnectionsError):
                    await asyncpg.connect(host=url.host, port=url.port,
                        user="twobrain_rec_maintenance", password=world["password"].read_text(),
                        database=name)
                sessions = []
                for database in (world["source"], name):
                    engine = create_async_engine(url.set(database=database), poolclass=NullPool)
                    engines.append(engine)

                    @event.listens_for(engine.sync_engine, "connect")
                    def reduce(dbapi_connection, _):
                        async def setup(connection):
                            await connection.execute("SET SESSION AUTHORIZATION twobrain_rec_maintenance")
                            await connection.execute("SET row_security=on")
                        dbapi_connection.run_async(setup)

                    sessions.append(async_sessionmaker(engine))
                now = datetime.now(UTC)
                cases = replay.parse_disposition_cases(world["operator"].read_text(), now=now)
                source_oid = world["binding"]["source_oid"]
                async with sessions[0]() as source:
                    await source.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
                    await replay.database_context(source, name=world["source"], oid=source_oid)
                    accounts, categories = replay.replay_accounts(
                        await replay.closure_snapshot(source), cases, required_categories=set(), now=now)
                    assert not categories
                    async with sessions[1]() as target:
                        await replay.database_context(target, name=name, oid=oid)
                        before = await replay.ledger(target)
                        assert len(before) == 9
                        expected = replay.expected_ledger(before, accounts, category=False)
                        assert len(expected) == 8
                        assert await replay.quarantine_milestone_deliveries(target, after_restore=True) == 8
                        for account in accounts:
                            assert await replay.delete_account_activation_decisions(
                                target, account_id=account) == 1
                        await replay.verify_ledger(target, expected)
                        await target.commit()
                    async with sessions[1]() as readback:
                        await replay.database_context(readback, name=name, oid=oid)
                        await replay.verify_ledger(readback, expected)
                for engine in engines:
                    await engine.dispose()
                assert resources["staging"].exists()
                assert len(operator._object_manifest(objects["client"], resources["bucket"],
                           deadline=time.monotonic()+5)) == 2
            assert not resources["staging"].exists()
            assert not objects["client"].bucket_exists(resources["bucket"])
            assert await owner.fetchval("SELECT count(*) FROM pg_database WHERE datname=ANY($1)",
                                       [resources["target"], resources["schema"]]) == 0
            assert b"absent" in await operator._command(
                ["docker", "exec", pg_container, "sh", "-c",
                 'test ! -e "$1" && echo absent', "sh", resources["pg_staging"]],
                deadline=time.monotonic()+5)
        finally:
            for engine in engines:
                await engine.dispose()
            await owner.close()

    asyncio.run(run())


@pytest.mark.parametrize("mode", ["success", "source_changed", "corrupt_copy", "invalid_register",
    "changed_register", "native_failure", "unknown_copy", "unknown_mc_create", "cleanup_failure",
    "fsync_failure", "parent_fsync_failure", "double_attempt_fsync_failure", "collision", "cancel_mirror", "cancel_cleanup",
    "unknown_native", "native_unresolved", "cancel_native"])
def test_coherent_copy_is_native_and_can_be_restored(replay_world, rehearsal_objects, monkeypatch, mode):
    import hashlib
    import io

    import asyncpg

    from twobrain_rec_server.product_analytics import activation_operator as operator
    from twobrain_rec_server.product_analytics.activation_fence import (
        ActivationHold,
        activation_fence,
    )

    world, objects = replay_world, rehearsal_objects
    world["owner"](f'ALTER DATABASE "{world["source"]}" RENAME TO twobrain_rec', "postgres")
    bucket = "source-" + uuid4().hex
    objects["client"].make_bucket(bucket)
    for key, payload in [("nested/中文.txt", b"Synthetic only"), ("empty.bin", b"")]:
        objects["client"].put_object(bucket, key, io.BytesIO(payload), len(payload))
    directory = world["root"] / "activation"
    directory.mkdir(mode=0o700)
    closed(directory / "activation.lock", json.dumps(dict(version=1, state="never_started")))
    backups = world["root"] / "backups"
    backups.mkdir(mode=0o700)

    async def run():
        url = world["url"]
        owner = await asyncpg.connect(host=url.host, port=url.port, user=url.username,
                                     password=url.password, database="postgres")
        source = await asyncpg.connect(host=url.host, port=url.port, user=url.username,
                                      password=url.password, database="twobrain_rec")
        await source.execute("SET SESSION AUTHORIZATION twobrain_rec_maintenance")
        await source.execute("SET row_security=on")
        cluster = await owner.fetchval("SELECT system_identifier::text FROM pg_control_system()")
        pg = (await operator._command(["docker", "inspect", "--format", "{{.Id}}", world["container"]],
                                     deadline=time.monotonic()+5)).decode().strip()
        image = (await operator._command(["docker", "inspect", "--format", "{{.Image}}", pg],
                                        deadline=time.monotonic()+5)).decode().strip()
        binding = dict(source_sha="a"*40, image_id=image, cluster_id=cluster,
                       db_name="twobrain_rec", db_oid=world["binding"]["source_oid"])
        original_command = operator._command
        containers, staging = [], []
        reached = asyncio.Event()

        async def command(argv, *, deadline):
            capturing = argv[:3] == ["docker", "exec", "--detach"] and "capture_dump=true" in argv
            if capturing and mode in {"unknown_native", "native_unresolved", "cancel_native"}:
                argv = [item.replace('umask 077; exec psql',
                    'umask 077; psql -XqAt -U twobrain_rec -d twobrain_rec -c "SELECT pg_sleep(1)"; exec psql')
                    for item in argv]
            if mode == "native_unresolved" and any("echo pending; exit;" in item for item in argv):
                return b"pending\n"
            if argv[:2] == ["docker", "create"] and mode == "cancel_mirror":
                argv = [*argv[:-1], argv[-1].replace("mc mirror", "sleep 10; mc mirror")]
            if argv[:3] == ["docker", "start", "--attach"] and mode == "cancel_mirror":
                reached.set()
            if "rm -rf --" in " ".join(argv) and mode == "cleanup_failure":
                raise ActivationHold("synthetic_cleanup_failure")
            raw = await original_command(argv, deadline=deadline)
            if capturing and mode in {"unknown_native", "native_unresolved", "cancel_native"}:
                if mode == "cancel_native":
                    reached.set()
                    await asyncio.sleep(30)
                raise TimeoutError("synthetic_native_response_lost")
            if "mkdir" in argv and argv[-1].startswith("/tmp/twobrain-rec-backup."):
                staging.append(argv[-1])
            if argv[:2] == ["docker", "create"]:
                containers.append(raw.decode().strip())
                if mode == "unknown_mc_create":
                    raise TimeoutError("synthetic_unknown_create")
            if argv[:2] == ["docker", "cp"] and argv[-2].endswith("/postgres.dump") and mode == "unknown_copy":
                raise TimeoutError("synthetic_unknown_copy")
            if argv[:2] == ["docker", "rm"] and mode == "cancel_cleanup":
                reached.set()
                await asyncio.sleep(.2)
            return raw

        monkeypatch.setattr(operator, "_command", command)
        if mode == "invalid_register":
            world["operator"].write_text("legal_basis_state_version=99\n")
        if mode in {"source_changed", "changed_register"}:
            original = operator._object_manifest
            calls = 0

            def changed(client, source_bucket, *, deadline):
                nonlocal calls
                calls += 1
                if calls == 2:
                    if mode == "source_changed":
                        client.put_object(source_bucket, "nested/中文.txt", io.BytesIO(b"different only"), 14)
                    else:
                        world["operator"].write_text(world["operator"].read_text() + "\n")
                return original(client, source_bucket, deadline=deadline)

            monkeypatch.setattr(operator, "_object_manifest", changed)
        if mode == "corrupt_copy":
            original_modes = operator._private_copy_modes

            def corrupt(path, *, deadline):
                original_modes(path, deadline=deadline)
                (path / "minio-objects/nested/中文.txt").write_bytes(b"X"*len(b"Synthetic only"))

            monkeypatch.setattr(operator, "_private_copy_modes", corrupt)
        if mode == "native_failure":
            original_pg = operator._pg_run

            async def failed(*args, deadline):
                return await original_pg(*args[:-1], ["sh", "-c", "exit 17"], deadline=deadline)

            monkeypatch.setattr(operator, "_pg_run", failed)
        if mode == "fsync_failure":
            original_manifest, original_fsync = operator._write_backup_manifest, os.fsync

            def failed_manifest(*args, **kwargs):
                import stat

                def fsync(fd):
                    if stat.S_ISDIR(os.fstat(fd).st_mode):
                        raise OSError("synthetic_directory_fsync")
                    return original_fsync(fd)

                with monkeypatch.context() as patch:
                    patch.setattr(os, "fsync", fsync)
                    return original_manifest(*args, **kwargs)

            monkeypatch.setattr(operator, "_write_backup_manifest", failed_manifest)
        if mode == "parent_fsync_failure":
            original_fsync = os.fsync
            parent_info = backups.stat()

            def failed_parent(fd):
                info = os.fstat(fd)
                if (info.st_dev, info.st_ino) == (parent_info.st_dev, parent_info.st_ino):
                    raise OSError("synthetic_parent_fsync")
                return original_fsync(fd)

            monkeypatch.setattr(os, "fsync", failed_parent)
        if mode == "double_attempt_fsync_failure":
            original_attempt, original_fsync = operator._write_backup_attempt, os.fsync
            completing = broken = False

            def attempt_write(fence, record):
                nonlocal completing
                if record["status"] == "completed":
                    completing = True
                return original_attempt(fence, record)

            def failed_attempt_fsync(fd):
                import stat

                nonlocal broken
                if completing and stat.S_ISDIR(os.fstat(fd).st_mode):
                    broken = True
                if broken:
                    raise OSError("synthetic_double_fsync")
                return original_fsync(fd)

            monkeypatch.setattr(operator, "_write_backup_attempt", attempt_write)
            monkeypatch.setattr(os, "fsync", failed_attempt_fsync)
        if mode == "collision":
            from types import SimpleNamespace

            token = "f" * 32
            monkeypatch.setattr(operator, "uuid4", lambda: SimpleNamespace(hex=token))
            occupied = backups / ("backup-" + token)
            occupied.mkdir(mode=0o700)
            closed(occupied / "keep", "do not change")
        try:
            with activation_fence(directory / "state.json", owner_uid=os.geteuid(),
                                  exclusive=True, readonly=False) as fence:
                fence.revoke()
                await operator.drain_product_database(fence, source=source, owner=owner,
                    name="twobrain_rec", oid=binding["db_oid"], cluster_id=cluster)
                task = asyncio.create_task(operator._create_coherent_backup(fence, root=REPO,
                    parent=backups, source=source, owner=owner, binding=binding, pg_container=pg,
                    bucket=bucket, register=world["operator"], deadline=time.monotonic()+90, **objects))
                if mode.startswith("cancel_"):
                    await asyncio.wait_for(reached.wait(), 10)
                    if mode == "cancel_native":
                        async with asyncio.timeout(3):
                            while not await owner.fetchval("SELECT count(*) FROM pg_stat_activity WHERE datid=$1 AND pid<>$2",
                                    binding["db_oid"], source.get_server_pid()):
                                await asyncio.sleep(.01)
                    else:
                        await asyncio.sleep(.05)
                    task.cancel()
                    await asyncio.sleep(.05)
                    task.cancel()
                if mode != "success":
                    with pytest.raises(asyncio.CancelledError if mode.startswith("cancel_") else ActivationHold):
                        await task
                    attempt = json.loads((directory / "backup-attempt.json").read_text())
                    assert attempt["status"] in {"failed", "in_progress"} and attempt["manifest_sha256"] is None
                    if mode == "double_attempt_fsync_failure":
                        with pytest.raises(ActivationHold):
                            operator._previous_backup_attempt(fence)
                    assert not source.is_in_transaction()
                    assert tuple(await owner.fetchrow("SELECT datallowconn,datconnlimit FROM pg_database WHERE oid=$1",
                                                      binding["db_oid"])) == (False, -1 if mode == "collision" else 0)
                    assert not (directory / "initial.json").exists()
                    assert json.loads((directory / "state.json").read_text())["status"] == "revoked"
                    if mode in {"unknown_copy", "cleanup_failure", "native_unresolved"}:
                        assert staging
                        assert b"preserved" in await original_command(["docker", "exec", pg, "sh", "-c",
                            'test -d "$1" && echo preserved', "sh", staging[0]], deadline=time.monotonic()+5)
                    if mode == "collision":
                        assert (occupied / "keep").read_text() == "do not change"
                    return
                result = await task
                first = result
                with pytest.raises(ActivationHold, match="activation_operator_backup_minimum_missing"):
                    await operator._settled_sql(asyncio.to_thread(operator._verified_backup_set,
                        fence, root=REPO, parent=backups, binding=binding,
                        now=await source.fetchval("SELECT clock_timestamp()"), deadline=time.monotonic()+30))
                result = await operator._create_coherent_backup(fence, root=REPO,
                    parent=backups, source=source, owner=owner, binding=binding, pg_container=pg,
                    bucket=bucket, register=world["operator"], deadline=time.monotonic()+90, **objects)
                verified = await operator._settled_sql(asyncio.to_thread(operator._verified_backup_set,
                    fence, root=REPO, parent=backups, binding=binding,
                    now=await source.fetchval("SELECT clock_timestamp()"), deadline=time.monotonic()+30))
                assert verified["latest"]["destination"] == result["destination"]
                assert verified["companion"]["destination"] == first["destination"]
                assert verified["latest"]["manifest_sha256"] == result["manifest_sha256"]
                assert verified["companion"]["manifest_sha256"] == first["manifest_sha256"]
                reference = backups / result["destination"]
                raw = (reference / "manifest.json").read_bytes()
                manifest = json.loads(raw)
                assert result["manifest_sha256"] == hashlib.sha256(raw).hexdigest()
                attempt = json.loads((directory / "backup-attempt.json").read_bytes())
                assert attempt["status"] == "completed" and attempt["manifest_sha256"] == result["manifest_sha256"]
                assert manifest["cleanup"] == "confirmed" and manifest["object_count"] == 2
                assert manifest["object_bytes"] == len(b"Synthetic only")
                assert not source.is_in_transaction()
                assert tuple(await owner.fetchrow("SELECT datallowconn,datconnlimit FROM pg_database WHERE oid=$1",
                                                  binding["db_oid"])) == (False, 0)
                async with operator._rehearsal_resources(root=REPO, reference=reference,
                    owner=owner, pg_container=pg, cluster_id=cluster,
                    deadline=time.monotonic()+90, **objects) as resources:
                    from sqlalchemy import event

                    from twobrain_rec_server.db.tenant_context import maintenance_context_settings
                    from twobrain_rec_server.product_analytics import restore_replay as replay

                    now = datetime.now(UTC)
                    cases = replay.parse_disposition_cases(world["operator"].read_text(), now=now)
                    async with source.transaction(isolation="repeatable_read", readonly=True):
                        for key, value in maintenance_context_settings(replay.CONTEXT).items():
                            await source.execute("SELECT set_config($1,$2,true)", key, value)
                        rows = [dict(row) for row in await source.fetch(replay.CLOSURE_ROWS_QUERY)]
                        accounts, categories = replay.replay_accounts(rows, cases, required_categories=set(), now=now)
                        assert not categories
                    engine = create_async_engine(url.set(database=resources["target"]), poolclass=NullPool)

                    @event.listens_for(engine.sync_engine, "connect")
                    def reduce(dbapi_connection, _):
                        async def setup(connection):
                            await connection.execute("SET SESSION AUTHORIZATION twobrain_rec_maintenance")
                            await connection.execute("SET row_security=on")
                        dbapi_connection.run_async(setup)

                    sessions = async_sessionmaker(engine)
                    try:
                        async with sessions() as target:
                            await replay.database_context(target, name=resources["target"], oid=resources["target_oid"])
                            before = await replay.ledger(target)
                            assert len(before) == 8
                            expected = replay.expected_ledger(before, accounts, category=False)
                            assert await replay.quarantine_milestone_deliveries(target, after_restore=True) == 7
                            for account in accounts:
                                assert await replay.delete_account_activation_decisions(target, account_id=account) == 0
                            await replay.verify_ledger(target, expected)
                            await target.commit()
                        async with sessions() as readback:
                            await replay.database_context(readback, name=resources["target"], oid=resources["target_oid"])
                            await replay.verify_ledger(readback, expected)
                    finally:
                        await engine.dispose()
                assert not (directory / "initial.json").exists()
                assert json.loads((directory / "state.json").read_text())["status"] == "revoked"
        finally:
            for cid in containers:
                await original_command(["docker", "rm", "--force", "--volumes", cid],
                                       deadline=time.monotonic()+10)
            await source.close()
            await owner.execute("ALTER DATABASE twobrain_rec ALLOW_CONNECTIONS true")
            await owner.execute(f'ALTER DATABASE twobrain_rec RENAME TO "{world["source"]}"')
            await owner.close()

    asyncio.run(run())


@pytest.mark.parametrize("mode", ["body_error", "cancel_create", "cancel_cleanup", "unknown_create",
                                   "cleanup_failure", "schema_mismatch", "byte_corruption",
                                   "cancel_native", "unknown_native", "native_unresolved",
                                   "unknown_mirror", "cleanup_identity_timeout"])
def test_staged_native_failures_preserve_ownership(replay_world, rehearsal_objects, monkeypatch, mode):
    import hashlib
    import io
    from types import SimpleNamespace

    import asyncpg

    from twobrain_rec_server.product_analytics import activation_operator as operator

    world, objects = replay_world, rehearsal_objects
    reference = world["root"] / "reference"
    files = reference / "minio-objects"
    files.mkdir(mode=0o700)
    closed(files / "synthetic.bin", "synthetic")
    if mode == "schema_mismatch":
        path = reference / "schema.sql"
        suffix = "--\n-- PostgreSQL database dump complete\n--\n\n"
        assert suffix in path.read_text()
        path.write_text(path.read_text().replace(
            suffix, "CREATE TABLE public.synthetic_extra(id int);\n\n" + suffix))
        closed(reference / "checksums.sha256", "".join(
            hashlib.sha256((reference / name).read_bytes()).hexdigest() + "  " + name + "\n"
            for name in ("postgres.dump", "schema.sql", "inventory.jsonl")))
    if mode == "byte_corruption":
        original = operator._object_manifest
        def corrupt(client, bucket, *, deadline):
            client.put_object(bucket, "synthetic.bin", io.BytesIO(b"corrupted"), 9)
            return original(client, bucket, deadline=deadline)
        monkeypatch.setattr(operator, "_object_manifest", corrupt)

    async def run():
        url = world["url"]
        owner = await asyncpg.connect(host=url.host, port=url.port, user=url.username,
                                     password=url.password, database="postgres")
        observed, release = asyncio.Event(), asyncio.Event()
        created, dropped, stage_paths, tool_ids, gates = [], [], [], [], []
        resources = None
        cleanup_started = None
        identity_calls = 0
        command = operator._command
        guarded_bucket_removal = []
        remove_bucket = objects["client"].remove_bucket

        def guarded_remove(bucket):
            for cid in tool_ids:
                result = subprocess.run(["docker", "ps", "--all", "--quiet", "--no-trunc",
                    "--filter", "id=" + cid], capture_output=True, check=True, timeout=5)
                assert not result.stdout, "native_mirror_still_owned_the_bucket"
            guarded_bucket_removal.append(True)
            return remove_bucket(bucket)
        monkeypatch.setattr(objects["client"], "remove_bucket", guarded_remove)

        async def track(argv, **kwargs):
            native_restore = argv[:3] == ["docker", "exec", "--detach"] and "pg_restore" in argv
            if native_restore and mode in {"cancel_native", "unknown_native"}:
                gate = argv[9] + ".gate"
                gates.append(gate)
                argv = [*argv[:11], "sh", "-c",
                        'while [ ! -f "$1" ]; do sleep 0.02; done; shift; exec "$@"',
                        "sh", gate, *argv[11:]]
            if native_restore and mode == "native_unresolved":
                raise TimeoutError("synthetic_unknown_spawn")
            if mode == "native_unresolved" and argv[:3] == ["docker", "exec", "--user=0"]:
                return b"invalid_completion\n"  # Neither a successful nor a failed native result.
            if mode == "unknown_mirror" and argv[:2] == ["docker", "create"] and "mc mirror" in argv[-1]:
                argv = [*argv[:-1], 'while [ ! -f /tmp/proceed ]; do sleep 0.02; done; ' + argv[-1]]
            if mode == "unknown_mirror" and argv[:3] == ["docker", "start", "--attach"] and len(tool_ids) == 2:
                await command(["docker", "start", tool_ids[-1]], **kwargs)
                raise TimeoutError("synthetic_lost_mirror_response")
            result = await command(argv, **kwargs)
            if native_restore and mode in {"cancel_native", "unknown_native"}:
                observed.set()
                if mode == "unknown_native":
                    raise TimeoutError("synthetic_lost_spawn_response")
            if argv[:2] == ["docker", "exec"] and argv[3:6] == ["mkdir", "-m", "700"]:
                stage_paths.append(argv[6])
            if argv[:2] == ["docker", "create"]:
                tool_ids.append(result.decode().strip())
            return result
        monkeypatch.setattr(operator, "_command", track)

        class TrackedOwner:
            def __getattr__(self, name):
                return getattr(owner, name)

            async def fetchrow(self, sql, *args):
                nonlocal identity_calls
                if "pg_control_system()" in sql:
                    identity_calls += 1
                    if mode == "cleanup_identity_timeout" and identity_calls >= 3:
                        # Release eventually even on the old unbounded implementation.
                        await asyncio.sleep(2)
                return await owner.fetchrow(sql, *args)

            async def execute(self, sql):
                creating, dropping = sql.startswith("CREATE DATABASE"), sql.startswith("DROP DATABASE")
                if dropping:
                    dropped.append(sql.split('"')[1])
                    if mode == "cleanup_failure" and len(dropped) == 1:
                        raise OSError("synthetic_drop_failure")
                result = await owner.execute(sql)
                if creating:
                    created.append(sql.split('"')[1])
                    if mode == "unknown_create" and len(created) == 1:
                        raise TimeoutError("synthetic_lost_create_response")
                if ((mode == "cancel_create" and creating and len(created) == 1)
                        or (mode == "cancel_cleanup" and dropping and len(dropped) == 1)):
                    observed.set()
                    await release.wait()
                return result

        task = None
        try:
            pg_container = (await command(["docker", "inspect", "--format", "{{.Id}}",
                world["container"]], deadline=time.monotonic()+5)).decode().strip()
            cluster_id = await owner.fetchval("SELECT system_identifier::text FROM pg_control_system()")
            async def attempt():
                nonlocal resources, cleanup_started
                async with operator._rehearsal_resources(
                    root=REPO, reference=reference, owner=TrackedOwner(), pg_container=pg_container,
                    cluster_id=cluster_id, deadline=time.monotonic()+90, **objects,
                ) as resources:
                    if mode == "body_error":
                        raise RuntimeError("synthetic_body_failure")
                    if mode == "cleanup_identity_timeout":
                        cleanup_started = time.monotonic()
                        # Compress the existing 30s cleanup window to 100ms, no new retry budget.
                        monkeypatch.setattr(operator, "time", SimpleNamespace(
                            monotonic=lambda: time.monotonic()-29.9))
            task = asyncio.create_task(attempt())
            if mode.startswith("cancel_") or mode == "unknown_native":
                await asyncio.wait_for(observed.wait(), 30)
                if mode.startswith("cancel_"):
                    task.cancel()
                    await asyncio.sleep(.02)
                    task.cancel()
                await asyncio.sleep(.02)
                assert not task.done()
                if gates:
                    # The live native process has not connected yet: no-PID alone permits no DROP.
                    assert await owner.fetchval("SELECT count(*) FROM pg_database WHERE datname=$1",
                                                created[0]) == 1
                    assert not dropped
                    await command(["docker", "exec", pg_container, "touch", gates[0]],
                                  deadline=time.monotonic()+5)
                release.set()
            expected = (asyncio.CancelledError if mode.startswith("cancel_") else
                        RuntimeError if mode == "body_error" else operator.ActivationHold)
            with pytest.raises(expected):
                await task
            remaining = await owner.fetch("SELECT datname FROM pg_database WHERE datname=ANY($1)", created)
            expected_remaining = (created if mode == "cleanup_identity_timeout" else created[:1]
                if mode in {"unknown_create", "cleanup_failure", "native_unresolved"} else [])
            assert sorted(r[0] for r in remaining) == sorted(expected_remaining)
            if mode == "cleanup_identity_timeout":
                assert time.monotonic()-cleanup_started < 1.5
                assert not dropped
            if mode == "unknown_create":
                assert not dropped  # An unknown CREATE response never grants deletion by name.
            if mode == "native_unresolved":
                assert not dropped  # The native process may still own the DB and dump file.
            if mode == "schema_mismatch":
                assert len(created) == 2  # Fail the native schema comparison, after both parses.
            if mode != "cleanup_identity_timeout":
                assert not list(objects["client"].list_buckets())
            if mode == "unknown_mirror":
                assert guarded_bucket_removal == [True]
            assert resources is None or not resources["staging"].exists()
            for path in stage_paths:
                await command(["docker", "exec", pg_container, "sh", "-c",
                               'test -d "$1"' if mode in {"native_unresolved", "cleanup_identity_timeout"}
                               else 'test ! -e "$1"',
                               "sh", path], deadline=time.monotonic()+5)
            if tool_ids and mode != "cleanup_identity_timeout":
                assert not (await command(["docker", "ps", "--all", "--quiet", "--no-trunc",
                    *[value for cid in tool_ids for value in ("--filter", "id=" + cid)]],
                    deadline=time.monotonic()+5)).strip()
        finally:
            release.set()
            if task is not None and not task.done():
                task.cancel()
                with suppress(BaseException):
                    await task
            # These names are known creations of this test, independent of operator knowledge.
            for name in created:
                if await owner.fetchval("SELECT count(*) FROM pg_database WHERE datname=$1", name):
                    await owner.execute(f'DROP DATABASE "{name}"')
            if mode == "cleanup_identity_timeout":
                for cid in tool_ids:
                    # Confirmed test-owned IDs only, even if the operator deadline expired.
                    subprocess.run(["docker", "rm", "--force", "--volumes", cid],
                                   capture_output=True, timeout=5)
            await owner.close()

    asyncio.run(run())


@pytest.fixture
def replay_world(postgres_isolated_cluster_database_url, tmp_path, monkeypatch, request):
    from twobrain_rec_server.product_analytics.restore_replay import digest

    tmp_path.chmod(0o700)
    # This fixture owns this fresh directory; retain logs, never fixture dumps/passwords.
    request.addfinalizer(lambda: shutil.rmtree(tmp_path))
    url = make_url(postgres_isolated_cluster_database_url)
    source_name = url.database
    suffix = source_name.removeprefix("twobrain_rec_test_")
    assert len(suffix) == 32 and all(c in "0123456789abcdef" for c in suffix)
    container = "graf-postgres-test-bootstrap-" + suffix
    spec = importlib.util.spec_from_file_location(
        "replay_bootstrap", REPO / "apps/server/scripts/bootstrap_runtime_database_roles.py")
    bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bootstrap)
    for key, value in (("HOST", url.host), ("PORT", str(url.port)), ("NAME", source_name)):
        monkeypatch.setenv("TWOBRAIN_DB_" + key, value)
    for role in ("OWNER", "APP", "MAINTENANCE", "MEDIA"):
        secret = closed(tmp_path / (role + "-password"),
                        url.password if role == "OWNER" else uuid4().hex)
        monkeypatch.setenv("TWOBRAIN_DB_" + role + "_PASSWORD_FILE", str(secret))
    asyncio.run(bootstrap._bootstrap())
    def owner(sql, db=source_name):
        return psql(container, sql, database=db, role="twobrain_rec")
    owner(f'ALTER DATABASE "{source_name}" RENAME TO twobrain_rec', "postgres")
    states = ["pending", "pre_send_retry", "dispatching", "submitted", "ambiguous",
              "confirmed", "cancelled", "rejected", "not_requested"]
    accounts = [uuid4() for _ in states]
    organization, workspace, closure = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    owner(f"INSERT INTO organizations(id,slug,name) VALUES('{organization}','synthetic','Synthetic')",
          "twobrain_rec")
    for index, (account, state) in enumerate(zip(accounts, states, strict=True)):
        owner(f"""INSERT INTO user_identities(id,organization_id,external_subject,locale,theme,status)
            VALUES('{account}','{organization}','synthetic-{index}','ru-RU','system','active');
            INSERT INTO product_activation_milestones
              (id,account_id,event_name,event_id,occurred_at,accepted_at,safe_payload,source_kind,
               posthog_state,yandex_state) VALUES('{uuid4()}','{account}','first_result_viewed',
               '{uuid4()}',now(),now(),'{{}}','browser','{state}','{states[-index-1]}')""", "twobrain_rec")
    for account in accounts:
        owner(f"""INSERT INTO client_acquisition_attributes
            (id,account_id,source,landing_path,attribution_confidence,captured_at,graf_attribution_id)
            VALUES('{uuid4()}','{account}','synthetic','/download','linked',now(),'graf_attr_synthetic123')""",
            "twobrain_rec")
    owner("""INSERT INTO public_visit_attributions(id,attribution_ref,landing_path,first_seen_at,expires_at)
        VALUES(gen_random_uuid(),'graf_visit_synthetic','/download',now(),now()+interval '90 days');
        INSERT INTO anonymous_page_aggregate_buckets(id,bucket_date,surface,landing_path)
        VALUES(gen_random_uuid(),current_date,'download','/download')""", "twobrain_rec")
    owner(f"""INSERT INTO workspaces(id,organization_id,slug,name,kind,owner_user_id,
                default_summary_template_key,default_summary_template_version)
          VALUES('{workspace}','{organization}','synthetic','Synthetic','personal','{accounts[0]}',
                 'graf-auto-v1',1);
        INSERT INTO account_closure_requests(id,workspace_id,requested_by_user_id,request_key,
                state,policy_version,requested_at,finalize_at,metadata_json)
          VALUES('{closure}','{workspace}','{accounts[0]}','synthetic-close','scheduled',
                 'account-close-v1','{now-timedelta(days=8)}','{now-timedelta(days=1)}','{{}}');
        INSERT INTO account_closure_requests(id,workspace_id,requested_by_user_id,request_key,
                state,policy_version,requested_at,finalize_at,metadata_json)
          SELECT md5('synthetic-request-'||g)::uuid,'{workspace}','{accounts[0]}',
                 'synthetic-'||g,'scheduled','account-close-v1',now(),now()+interval '7 days','{{}}'
          FROM generate_series(1,501) g;
        INSERT INTO account_closure_requests(id,workspace_id,requested_by_user_id,request_key,
                state,policy_version,requested_at,finalize_at,canceled_at,metadata_json)
          VALUES('{uuid4()}','{workspace}','{accounts[0]}','synthetic-canceled','canceled',
                 'account-close-v1',now(),now()+interval '7 days',now(),'{{}}')""", "twobrain_rec")
    reference = tmp_path / "reference"
    capture(container, "twobrain_rec", reference, dump=True)
    oid = int(owner("SELECT oid FROM pg_database WHERE datname='twobrain_rec'", "postgres"))
    owner(f'ALTER DATABASE twobrain_rec RENAME TO "{source_name}"', "postgres")
    assert oid == int(owner(f"SELECT oid FROM pg_database WHERE datname='{source_name}'", "postgres"))

    async def finalize():
        from twobrain_rec_server.auth.account_closure import finalize_account_close

        engine = create_async_engine(url, poolclass=NullPool)
        try:
            async with async_sessionmaker(engine)() as db:
                await finalize_account_close(db, request_id=closure, now=datetime.now(UTC))
                await db.commit()
        finally:
            await engine.dispose()

    asyncio.run(finalize())
    case = (f"disposition_case case_ref=case_synthetic decision_ref=decision_synthetic "
            f"scope=account_closure selector_ref={closure} owner_role=operator reason=account_closed "
            f"decided_at={now.isoformat()} due_at={(now+timedelta(days=1)).isoformat()} stage=accepted")
    operator = closed(tmp_path / "register", "legal_basis_state_version=2\n" + case + "\n")
    staging = tmp_path / "staging"
    staging.mkdir(mode=0o700)
    token = uuid4().hex
    target = "rec_restore_rehearsal_" + token
    owner(f'CREATE DATABASE "{target}"', "postgres")
    with (reference / "postgres.dump").open("rb") as stream:
        subprocess.run(["docker", "exec", "-i", container, "pg_restore", "--exit-on-error", "-U",
                        "twobrain_rec", "-d", target], stdin=stream, capture_output=True, check=True)
    restored = tmp_path / "restored"
    capture(container, target, restored, dump=False)
    canonical_db = "rec_restore_schema_" + token
    owner(f'CREATE DATABASE "{canonical_db}"', "postgres")
    owner((reference / "schema.sql").read_text(), canonical_db)
    canonical = tmp_path / "canonical"
    capture(container, canonical_db, canonical, dump=False)
    subprocess.run([sys.executable, str(REPO / "infra/scripts/rec-db-verify.py"), str(reference),
                    str(restored), target, str(canonical), canonical_db],
                   check=True, capture_output=True)
    binding = {"version": 1, "token": token, "source_database": source_name, "source_oid": oid,
               "target_database": target,
               "target_oid": int(owner(f"SELECT oid FROM pg_database WHERE datname='{target}'", "postgres")),
               "backup_sha256": digest((reference / "postgres.dump").read_bytes())}
    ownership = closed(tmp_path / "ownership", json.dumps(binding))
    image = os.environ.get("GRAF_REPLAY_TEST_IMAGE")
    if image:
        assert image.startswith("sha256:") and len(image) == 71
    yield {"url": url, "container": container, "source": source_name, "target": target,
           "owner": owner, "binding": binding, "ownership": ownership, "operator": operator,
           "staging": staging, "root": tmp_path, "accounts": accounts, "case": case,
           "password": tmp_path / "MAINTENANCE-password", "closure": closure,
           "image": image}
    # The existing owning cluster fixture removes all synthetic DBs and volumes.
    assert not list(staging.iterdir())


def test_native_local_access_catalog(replay_world, monkeypatch):
    import asyncpg

    from twobrain_rec_server.product_analytics import local_retention as module
    from twobrain_rec_server.product_analytics.activation_fence import ActivationHold

    world = replay_world

    async def run():
        url = world['url']
        db = await asyncpg.connect(host=url.host, port=url.port, user=url.username,
                                   password=url.password, database=url.database)
        queries, fault = [], None

        class ObservedSource:
            def is_in_transaction(self):
                return db.is_in_transaction()

            async def fetchval(self, query, *args):
                if fault == 'version' and query == 'SHOW server_version_num':
                    return '160000'
                return await db.fetchval(query, *args)

            async def fetch(self, query, *args):
                queries.append(query)
                if fault == 'query':
                    raise OSError('synthetic_read_failure')
                if fault == 'cancel':
                    raise asyncio.CancelledError
                return await db.fetch(query, *args)

        source = ObservedSource()

        async def read():
            queries.clear()
            async with db.transaction(readonly=True):
                return await module.local_retention_database_access(source)

        try:
            baseline = await read()
            assert baseline == module.EXPECTED_ACCESS_SHA256 and await read() == baseline
            with pytest.raises(ActivationHold, match='retention_access'):
                await module.local_retention_database_access(source)
            async with db.transaction():
                queries.clear()
                with pytest.raises(ActivationHold, match='retention_access'):
                    await module.local_retention_database_access(source)
                assert not queries
            for fault in ('version', 'query', 'cancel'):
                expected = asyncio.CancelledError if fault == 'cancel' else ActivationHold
                with pytest.raises(expected):
                    await read()
                assert not queries if fault == 'version' else len(queries) == 1
                assert not db.is_in_transaction()
            fault = None
            with monkeypatch.context() as patch:
                patch.setattr(module, 'EXPECTED_ACCESS_SHA256', '0' * 64)
                with pytest.raises(ActivationHold, match='retention_access'):
                    await read()
            assert await read() == baseline
            changes = [
                ('column_grant', 'GRANT SELECT(account_id) ON client_acquisition_attributes TO twobrain_rec_media',
                 'REVOKE SELECT(account_id) ON client_acquisition_attributes FROM twobrain_rec_media'),
                ('function_option', 'GRANT EXECUTE ON FUNCTION rec_maintenance_allowed() TO twobrain_rec_app WITH GRANT OPTION',
                 'REVOKE EXECUTE ON FUNCTION rec_maintenance_allowed() FROM twobrain_rec_app'),
                ('default_acl', 'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT UPDATE ON TABLES TO twobrain_rec_media',
                 'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE UPDATE ON TABLES FROM twobrain_rec_media'),
                ('incoming_fk', 'CREATE TABLE synthetic_access(id uuid REFERENCES client_acquisition_attributes(id) ON DELETE CASCADE)',
                 'DROP TABLE synthetic_access'),
                ('sibling_rule', 'CREATE RULE synthetic_access AS ON DELETE TO user_identities DO INSTEAD NOTHING',
                 'DROP RULE synthetic_access ON user_identities'),
                ('internal_fk', 'ALTER TABLE client_acquisition_attributes DISABLE TRIGGER ALL',
                 'ALTER TABLE client_acquisition_attributes ENABLE TRIGGER ALL'),
                ('sibling_policy', 'CREATE POLICY synthetic_access ON user_identities AS RESTRICTIVE USING(false)',
                 'DROP POLICY synthetic_access ON user_identities'),
                ('column_default', "ALTER TABLE public_visit_attributions ALTER landing_path SET DEFAULT '/synthetic'",
                 'ALTER TABLE public_visit_attributions ALTER landing_path DROP DEFAULT'),
                ('index', 'ALTER INDEX ix_public_visit_attribution_expiry SET (fillfactor=55)',
                 'ALTER INDEX ix_public_visit_attribution_expiry RESET (fillfactor)'),
                ('database_acl', f'GRANT CONNECT ON DATABASE "{url.database}" TO twobrain_rec_media WITH GRANT OPTION',
                 f'REVOKE GRANT OPTION FOR CONNECT ON DATABASE "{url.database}" FROM twobrain_rec_media'),
                ('schema_acl', 'GRANT CREATE ON SCHEMA public TO twobrain_rec_media',
                 'REVOKE CREATE ON SCHEMA public FROM twobrain_rec_media'),
                ('language_acl', 'REVOKE USAGE ON LANGUAGE plpgsql FROM PUBLIC',
                 'GRANT USAGE ON LANGUAGE plpgsql TO PUBLIC'),
                ('role', 'ALTER ROLE twobrain_rec_maintenance CONNECTION LIMIT 5',
                 'ALTER ROLE twobrain_rec_maintenance CONNECTION LIMIT -1'),
                ('membership', 'GRANT twobrain_rec TO twobrain_rec_media',
                 'REVOKE twobrain_rec FROM twobrain_rec_media'),
                ('role_setting', 'ALTER ROLE twobrain_rec_media SET statement_timeout=1234',
                 'ALTER ROLE twobrain_rec_media RESET statement_timeout'),
                ('cast', 'CREATE CAST(text AS integer) WITH INOUT AS ASSIGNMENT',
                 'DROP CAST(text AS integer)'),
                ('search_path', 'SET search_path=pg_catalog,public', 'RESET search_path'),
            ]
            for name, change, undo in changes:
                await db.execute(change)
                try:
                    with pytest.raises(ActivationHold, match='retention_access'):
                        await read()
                    if name == 'search_path':
                        assert not queries
                finally:
                    await db.execute(undo)
                assert await read() == baseline, name
            async with db.transaction(readonly=True):
                ordinary = await module.local_retention_database_catalog(db)
            await db.execute('ALTER TABLE product_activation_milestones ENABLE ALWAYS TRIGGER activation_decision_immutable')
            try:
                assert await read() == baseline
                async with db.transaction(readonly=True):
                    assert await module.local_retention_database_catalog(db) != ordinary
            finally:
                await db.execute('ALTER TABLE product_activation_milestones ENABLE TRIGGER activation_decision_immutable')
            assert await read() == baseline
            await db.execute('SET SESSION AUTHORIZATION twobrain_rec_maintenance')
            assert await read() == baseline
        finally:
            await db.close()
    asyncio.run(run())


def launch(world):
    command = [sys.executable, "-m", MODULE, "--host", world["url"].host,
               "--port", str(world["url"].port)]
    options = (("password-file", "password"), ("operator-file", "operator"),
               ("ownership-file", "ownership"), ("staging", "staging"))
    if world["image"]:
        # The same executable proof can be repeated in an immutable server image.
        # Mount only the one DB password and closed case/binding files, never env-file.
        uid, gid = os.getuid(), os.getgid()
        docker = shutil.which("docker")
        assert docker is not None
        command = [docker, "run", "--rm", "--pull=never", "--read-only", "--cap-drop=ALL",
                   "--security-opt=no-new-privileges", "--user", f"{uid}:{gid}",
                   "--network", "container:" + world["container"],
                   "--tmpfs", f"/run/replay:rw,noexec,nosuid,mode=0700,uid={uid},gid={gid}",
                   "--tmpfs", f"/staging:rw,noexec,nosuid,size=16m,mode=0700,uid={uid},gid={gid}"]
        for _name, key in options[:-1]:
            command += ["--mount", f"type=bind,src={world[key]},dst=/run/replay/{key},readonly"]
        # Same network namespace as the owned DB; it is not declared egress-free.
        # The audit hook permits DB sockets only and fails any attempted receiver call.
        audit = ("import runpy,sys\ndenied=[]\ndef guard(event,args):\n"
                 " if event=='socket.connect' and args[1]!=('127.0.0.1',5432):\n"
                 "  denied.append(True)\n  raise RuntimeError('non_database_socket')\n"
                 "sys.addaudithook(guard)\n"
                 f"runpy.run_module('{MODULE}',run_name='__main__')\n"
                 "assert not denied, 'receiver_call_attempted'\n")
        command += ["--entrypoint", "python", world["image"], "-c", audit,
                    "--host", "127.0.0.1", "--port", "5432"]
        for name, key in options:
            command += ["--" + name, "/staging" if key == "staging" else "/run/replay/" + key]
    else:
        for name, key in options:
            command += ["--" + name, str(world[key])]
    return subprocess.run(command, capture_output=True, text=True, timeout=45,
                          env={"PATH": os.defpath, "PYTHONPATH": str(REPO / "apps/server/src"),
                               "PYTHONDONTWRITEBYTECODE": "1"})


def test_source_lifecycle_proves_absence_without_hidden_rls_rows(replay_world, monkeypatch):
    import asyncpg

    from twobrain_rec_server.product_analytics import activation_operator as operator
    from twobrain_rec_server.product_analytics import restore_replay as replay
    from twobrain_rec_server.product_analytics.activation_fence import ActivationHold
    from twobrain_rec_server.product_analytics.restore_replay import ReplayHold

    world = replay_world

    async def run():
        url = world["url"]
        kwargs = dict(host=url.host, port=url.port, user=url.username,
                      password=url.password, database=url.database)
        owner, source = await asyncpg.connect(**kwargs), await asyncpg.connect(**kwargs)
        try:
            await source.execute("SET SESSION AUTHORIZATION twobrain_rec_maintenance")
            await source.execute("SET row_security=on")

            async def evaluate():
                try:
                    return await operator._backup_lifecycle(source, world["operator"], root=REPO)
                finally:
                    assert not source.is_in_transaction()

            baseline, raw = await evaluate()
            assert len(baseline) == 64 and raw == world["operator"].read_bytes()
            for invalid in (None, 'legal_basis_state_version=2\n', b'', b'x' * (10 * 1024 * 1024 + 1)):
                with pytest.raises(ActivationHold, match='lifecycle_register'):
                    await operator._local_lifecycle(source, invalid, root=REPO)
                assert not source.is_in_transaction()
            assert await operator._local_lifecycle(source, raw, root=REPO) == baseline
            database, oid = await source.fetchrow('SELECT current_database(),oid FROM pg_database WHERE datname=current_database()')
            assert not source.is_in_transaction()
            original_metadata = await owner.fetchrow('SELECT datallowconn,datconnlimit FROM pg_database WHERE oid=$1', oid)
            gate = await asyncpg.connect(**{**kwargs, "database": "postgres"})
            try:
                await gate.execute(f'ALTER DATABASE "{database}" CONNECTION LIMIT 0 ALLOW_CONNECTIONS false')
                try:
                    assert await operator._local_lifecycle(source, raw, root=REPO) == baseline
                finally:
                    await gate.execute(f'ALTER DATABASE "{database}" CONNECTION LIMIT {original_metadata[1]} '
                                       + ('ALLOW_CONNECTIONS true' if original_metadata[0] else 'ALLOW_CONNECTIONS false'))
            finally:
                await gate.close()
            assert await owner.fetchval("SELECT count(*) FROM product_activation_milestones") == 8
            remnant = uuid4()
            await owner.execute("""INSERT INTO product_activation_milestones
                (id,account_id,event_name,event_id,occurred_at,accepted_at,safe_payload,source_kind)
                VALUES($1,$2,'first_result_viewed',$3,now(),now(),'{}','browser')""",
                remnant, world["accounts"][0], uuid4())
            try:
                with pytest.raises((ActivationHold, ReplayHold)):
                    await evaluate()
            finally:
                await owner.execute("DELETE FROM product_activation_milestones WHERE id=$1", remnant)
            assert (await evaluate())[0] == baseline

            # Owner and wrong context cannot stand in for a current maintenance read.
            with pytest.raises(ActivationHold, match="lifecycle_context"):
                await operator._backup_lifecycle(owner, world["operator"], root=REPO)
            assert not owner.is_in_transaction()
            from twobrain_rec_server.db import tenant_context

            original_context = tenant_context.maintenance_context_settings
            with monkeypatch.context() as patch:
                patch.setattr(tenant_context, "maintenance_context_settings", lambda context: {
                    **original_context(context), "app.context_kind": "request"})
                with pytest.raises(ActivationHold, match="lifecycle_context"):
                    await evaluate()
            assert (await evaluate())[0] == baseline

            original_reader, reads = replay.private_bytes, 0

            def changed_register(path):
                nonlocal reads
                reads += 1
                if reads == 2:
                    closed(path, raw.decode()+"\n")
                return original_reader(path)

            try:
                with monkeypatch.context() as patch:
                    patch.setattr(replay, "private_bytes", changed_register)
                    with pytest.raises(ActivationHold, match="register_changed"):
                        await evaluate()
            finally:
                closed(world["operator"], raw.decode())
            assert (await evaluate())[0] == baseline

            predicate = await owner.fetchval("""SELECT pg_get_expr(polqual,polrelid) FROM pg_policy
                WHERE polrelid='public.product_activation_milestones'::regclass""")
            changes = [
                ("CREATE POLICY synthetic_hide ON product_activation_milestones AS RESTRICTIVE USING(false)",
                 "DROP POLICY synthetic_hide ON product_activation_milestones"),
                ("ALTER POLICY activation_account_isolation ON product_activation_milestones USING(false)",
                 "ALTER POLICY activation_account_isolation ON product_activation_milestones USING("+predicate+")"),
                ("ALTER TABLE product_activation_milestones NO FORCE ROW LEVEL SECURITY",
                 "ALTER TABLE product_activation_milestones FORCE ROW LEVEL SECURITY"),
                ("ALTER TABLE product_activation_milestones DISABLE ROW LEVEL SECURITY",
                 "ALTER TABLE product_activation_milestones ENABLE ROW LEVEL SECURITY"),
                ("REVOKE SELECT ON product_activation_milestones FROM twobrain_rec_maintenance",
                 "GRANT SELECT ON product_activation_milestones TO twobrain_rec_maintenance"),
            ]
            for change, undo in changes:
                await owner.execute(change)
                try:
                    with pytest.raises((ActivationHold, ReplayHold)):
                        await evaluate()
                finally:
                    await owner.execute(undo)
                assert (await evaluate())[0] == baseline

            due = await owner.fetchval("SELECT id FROM account_closure_requests WHERE state='scheduled' LIMIT 1")
            original = await owner.fetchval("SELECT finalize_at FROM account_closure_requests WHERE id=$1", due)
            await owner.execute("UPDATE account_closure_requests SET finalize_at=requested_at WHERE id=$1", due)
            try:
                with pytest.raises((ActivationHold, ReplayHold)):
                    await evaluate()
            finally:
                await owner.execute("UPDATE account_closure_requests SET finalize_at=$2 WHERE id=$1", due, original)
            assert (await evaluate())[0] == baseline

            now = await owner.fetchval("SELECT clock_timestamp()")
            # These are new replay results, not equality assertions about the original purge.
            completed = json.loads(await owner.fetchval("""SELECT row_to_json(r)::text FROM (
                SELECT metadata_json->>'activation_decisions_purged_at' AS purged_at
                FROM account_closure_requests WHERE id=$1) r""", world["closure"]))
            assert datetime.fromisoformat(completed["purged_at"]) < now
            reapplied = raw.decode().replace("stage=accepted", "stage=applied") + (
                f" applied_at={now.isoformat()} rows_affected=0\n")
            closed(world["operator"], reapplied)
            assert len((await evaluate())[0]) == 64
            closed(world["operator"], raw.decode())
            category = ("disposition_case case_ref=case_category decision_ref=decision_category "
                "scope=activation_milestone_decisions selector_ref=all owner_role=operator "
                f"reason=purpose_ended decided_at={now.isoformat()} "
                f"due_at={(now+timedelta(days=1)).isoformat()} stage=accepted\n")
            closed(world["operator"], raw.decode()+category)
            with pytest.raises((ActivationHold, ReplayHold)):
                await evaluate()
            applied = category.replace("stage=accepted", "stage=applied").strip()+(
                f" applied_at={now.isoformat()} rows_affected=8\n")
            closed(world["operator"], raw.decode()+applied)
            with pytest.raises((ActivationHold, ReplayHold)):
                await evaluate()
            await owner.execute("DELETE FROM product_activation_milestones")
            assert len((await evaluate())[0]) == 64
            closed(world["operator"], raw.decode()+category)
            with pytest.raises((ActivationHold, ReplayHold)):
                await evaluate()  # Empty is not evidence that an accepted case executed.
            closed(world["operator"], raw.decode()+applied)
            assert len((await evaluate())[0]) == 64
        finally:
            await source.close()
            await owner.close()

    asyncio.run(run())


def test_old_copy_replays_only_exact_account_and_quarantines_both(replay_world):
    world = replay_world
    source_before = world["owner"]("SELECT count(*) FROM product_activation_milestones")
    assert int(source_before) == 8
    assert int(world["owner"]("SELECT count(*) FROM account_closure_requests")) == 503
    result = launch(world)
    assert result.returncode == 0, result.stderr + result.stdout
    receipt = json.loads(result.stdout)
    assert receipt["replay_result"] == "verified" and receipt["readiness"] == "hold"
    assert receipt["quarantined_intents"] == 8 and receipt["deleted_rows"] == 2
    assert int(world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"])) == 8
    assert world["owner"]("SELECT count(*) FROM product_activation_milestones") == source_before
    again = launch(world)
    assert again.returncode == 0, again.stderr + again.stdout
    repeated = json.loads(again.stdout)
    assert repeated["quarantined_intents"] == repeated["deleted_rows"] == 0
    assert not list(world["staging"].iterdir())


def test_incomplete_cases_and_wrong_targets_refuse_before_any_mutation(replay_world):
    world = replay_world
    before = world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"])
    original = world["operator"].read_text()
    for broken in (original.replace("version=2", "version=1"), "legal_basis_state_version=2\n",
                   original.replace("stage=accepted", "stage=failed")):
        closed(world["operator"], broken)
        result = launch(world)
        assert result.returncode != 0 and json.loads(result.stdout)["readiness"] == "hold"
        assert world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"]) == before
    closed(world["operator"], original)
    for key, value in (("target_database", "twobrain_rec"), ("target_oid", 1),
                       ("source_database", "twobrain_rec")):
        closed(world["ownership"], json.dumps({**world["binding"], key: value}))
        assert launch(world).returncode != 0
    closed(world["ownership"], json.dumps(world["binding"]))
    world["operator"].chmod(0o644)
    assert launch(world).returncode != 0
    world["operator"].chmod(0o600)
    assert world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"]) == before


def test_category_case_erases_ledger_and_preserves_other_relations(replay_world):
    from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
        apply_basis_loss_disposition,
        plan_processing_stop,
    )

    world = replay_world
    now = datetime.now(UTC)
    category = ("disposition_case case_ref=case_category decision_ref=decision_category "
                "scope=activation_milestone_decisions selector_ref=all owner_role=operator "
                f"reason=purpose_ended decided_at={now.isoformat()} "
                f"due_at={(now+timedelta(days=1)).isoformat()} stage=accepted")
    closed(world["operator"], world["operator"].read_text() + category + "\n")

    async def erase_source():
        engine = create_async_engine(world["url"], poolclass=NullPool)
        try:
            async with async_sessionmaker(engine)() as db:
                plan = plan_processing_stop(
                    level_key="attribution_profiles", basis_lost_at=now, reason="purpose_ended",
                    affected_categories=("activation_milestone_decisions",),
                    deletion_deadlines={"activation_milestone_decisions": now+timedelta(days=1)},
                )
                assert (await apply_basis_loss_disposition(db, plan))[0].rows_affected == 8
        finally:
            await engine.dispose()

    asyncio.run(erase_source())
    outside = world["owner"]("SELECT md5(jsonb_agg(to_jsonb(t) ORDER BY id)::text) FROM user_identities t",
                             world["target"])
    result = launch(world)
    assert result.returncode == 0, result.stderr + result.stdout
    receipt = json.loads(result.stdout)
    assert receipt["cases"] == 2 and receipt["deleted_rows"] == 10
    assert world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"]).strip() == "0"
    assert world["owner"]("SELECT md5(jsonb_agg(to_jsonb(t) ORDER BY id)::text) FROM user_identities t",
                           world["target"]) == outside
    assert launch(world).returncode == 0


def test_unresolved_history_and_restrictive_policy_do_not_hide_cases(replay_world):
    world = replay_world
    scheduled = world["owner"]("SELECT id FROM account_closure_requests WHERE state='scheduled' LIMIT 1").strip()
    for state in ("finalizing", "blocked", "unknown"):
        world["owner"](f"UPDATE account_closure_requests SET state='{state}' WHERE id='{scheduled}'")
        assert launch(world).returncode != 0
    world["owner"](f"UPDATE account_closure_requests SET state='scheduled' WHERE id='{scheduled}'")
    original = world["operator"].read_text()
    for state in ("scheduled", "canceled"):
        selector = world["owner"](f"SELECT id FROM account_closure_requests WHERE state='{state}' LIMIT 1").strip()
        extra = world["case"].replace(str(world["closure"]), selector)
        extra = extra.replace("case_synthetic", "case_other").replace("decision_synthetic", "decision_other")
        closed(world["operator"], original + extra + "\n")
        assert launch(world).returncode != 0
    closed(world["operator"], original)
    world["owner"]("CREATE POLICY synthetic_hide ON account_closure_requests AS RESTRICTIVE USING(false)")
    assert launch(world).returncode != 0
    world["owner"]("DROP POLICY synthetic_hide ON account_closure_requests")
    assert int(world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"])) == 9


def test_transaction_rollback_and_unknown_after_commit(replay_world, monkeypatch):
    from twobrain_rec_server.product_analytics import restore_replay as replay

    world = replay_world
    kwargs = {"host": world["url"].host, "port": world["url"].port,
              "password_file": world["password"], "operator_file": world["operator"],
              "ownership_file": world["ownership"], "staging": world["staging"]}
    original = replay.verify_ledger
    before = world["owner"]("SELECT md5(jsonb_agg(to_jsonb(t) ORDER BY id)::text) "
                              "FROM product_activation_milestones t", world["target"])
    for fail_at in (1, 2):
        calls = 0

        async def fail_readback(db, expected, fail_at=fail_at):
            nonlocal calls
            calls += 1
            if calls == fail_at:
                raise replay.ReplayHold("replay_ledger_mismatch")
            await original(db, expected)

        monkeypatch.setattr(replay, "verify_ledger", fail_readback)
        with pytest.raises(replay.ReplayHold) as error:
            asyncio.run(replay.reconcile(**kwargs))
        if fail_at == 1:
            assert error.value.args == ("replay_ledger_mismatch",)
            assert world["owner"]("SELECT md5(jsonb_agg(to_jsonb(t) ORDER BY id)::text) "
                                   "FROM product_activation_milestones t", world["target"]) == before
        else:
            assert error.value.args == ("replay_result_unknown",)
            assert int(world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"])) == 8
    monkeypatch.setattr(replay, "verify_ledger", original)
    receipt = asyncio.run(replay.reconcile(**kwargs))
    assert receipt["quarantined_intents"] == receipt["deleted_rows"] == 0


def replay_kwargs(world):
    return {"host": world["url"].host, "port": world["url"].port,
            "password_file": world["password"], "operator_file": world["operator"],
            "ownership_file": world["ownership"], "staging": world["staging"]}


def test_lost_commit_response_is_unknown_even_when_database_applied(replay_world, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession

    from twobrain_rec_server.product_analytics import restore_replay as replay

    world = replay_world
    original = AsyncSession.commit

    async def commit_then_lose_response(db):
        await original(db)
        raise ConnectionError("synthetic_lost_ack")

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", commit_then_lose_response)
        with pytest.raises(replay.ReplayHold, match="replay_result_unknown"):
            asyncio.run(replay.reconcile(**replay_kwargs(world)))
    assert int(world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"])) == 8
    receipt = asyncio.run(replay.reconcile(**replay_kwargs(world)))
    assert receipt["quarantined_intents"] == receipt["deleted_rows"] == 0


def test_deadline_is_evaluated_at_verification_time(replay_world, monkeypatch):
    from twobrain_rec_server.product_analytics import restore_replay as replay

    started = datetime.now(UTC)

    class AdvancingClock(datetime):
        calls = 0

        @classmethod
        def now(cls, tz=None):
            cls.calls += 1
            return started + (timedelta(0) if cls.calls == 1 else timedelta(days=2))

    monkeypatch.setattr(replay, "datetime", AdvancingClock)
    receipt = asyncio.run(replay.reconcile(**replay_kwargs(replay_world)))
    assert receipt["overdue_cases"] == 1
    assert receipt["readiness"] == "hold"


def test_changed_operator_rolls_back_and_cleanup_failure_never_passes(replay_world, monkeypatch):
    from twobrain_rec_server.product_analytics import restore_replay as replay

    world = replay_world
    original_verify = replay.verify_ledger
    operator = world["operator"].read_text()

    async def mutate_operator(db, expected):
        await original_verify(db, expected)
        closed(world["operator"], operator + "# changed\n")

    with monkeypatch.context() as patch:
        patch.setattr(replay, "verify_ledger", mutate_operator)
        with pytest.raises(replay.ReplayHold, match="replay_inputs_changed"):
            asyncio.run(replay.reconcile(**replay_kwargs(world)))
    closed(world["operator"], operator)
    assert int(world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"])) == 9
    original_exists = Path.exists

    def uncertain_cleanup(path):
        return True if path.parent == world["staging"] and path.name.startswith("replay-") else original_exists(path)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "exists", uncertain_cleanup)
        with pytest.raises(replay.ReplayHold, match="replay_result_unknown"):
            asyncio.run(replay.reconcile(**replay_kwargs(world)))
    assert not list(world["staging"].iterdir())


def test_all_four_categories_replay_and_source_postconditions(replay_world):
    import asyncpg

    from twobrain_rec_server.product_analytics import activation_operator as operator
    from twobrain_rec_server.product_analytics import restore_replay as replay
    from twobrain_rec_server.product_analytics.activation_fence import ActivationHold
    from twobrain_rec_server.product_analytics.local_retention import TABLES

    world = replay_world
    assert int(world["owner"]("SELECT count(*) FROM client_acquisition_attributes")) == 8
    assert world["owner"]("SELECT metadata_json->>'acquisition_attributes_purged_count' "
                          "FROM account_closure_requests WHERE state='completed'").strip() == '1'
    original = world["operator"].read_text()
    now = datetime.now(UTC)
    cases = {}
    for scope in TABLES:
        cases[scope] = (f"disposition_case case_ref=case_{scope} decision_ref=decision_{scope} "
            f"scope={scope} selector_ref=all owner_role=operator reason=purpose_ended "
            f"decided_at={now.isoformat()} due_at={(now+timedelta(days=1)).isoformat()} stage=applied "
            f"applied_at={now.isoformat()} rows_affected=0\n")

    async def source_checks():
        url = world["url"]
        owner = await asyncpg.connect(host=url.host,port=url.port,user=url.username,
                                      password=url.password,database=url.database)
        source = await asyncpg.connect(host=url.host,port=url.port,user=url.username,
                                       password=url.password,database=url.database)
        try:
            await source.execute("SET SESSION AUTHORIZATION twobrain_rec_maintenance")
            await source.execute("SET row_security=on")
            async def evaluate():
                try:
                    return await operator._backup_lifecycle(source, world["operator"], root=REPO)
                finally:
                    assert not source.is_in_transaction()
            baseline = (await evaluate())[0]
            metadata = await owner.fetchval('SELECT metadata_json::text FROM account_closure_requests WHERE id=$1',world['closure'])
            legacy = {k:v for k,v in json.loads(metadata).items() if not k.startswith('acquisition_attributes_purged_')}
            for change, allowed in ((legacy,True),
                ({**legacy,'acquisition_attributes_purged_at':None},False),
                ({**legacy,'acquisition_attributes_purged_count':0},False),
                ({**json.loads(metadata),'acquisition_attributes_purged_count':'1'},False)):
                await owner.execute('UPDATE account_closure_requests SET metadata_json=$2::json WHERE id=$1',world['closure'],json.dumps(change))
                try:
                    if allowed:
                        assert len((await evaluate())[0]) == 64
                    else:
                        with pytest.raises((ActivationHold,replay.ReplayHold)):
                            await evaluate()
                finally:
                    await owner.execute('UPDATE account_closure_requests SET metadata_json=$2::json WHERE id=$1',world['closure'],metadata)
                assert (await evaluate())[0] == baseline
            remnant = uuid4()
            await owner.execute("""INSERT INTO client_acquisition_attributes
                (id,account_id,source,landing_path,attribution_confidence,captured_at)
                VALUES($1,$2,'synthetic','/download','linked',now())""",remnant,world['accounts'][0])
            try:
                with pytest.raises((ActivationHold,replay.ReplayHold)):
                    await evaluate()
            finally:
                await owner.execute('DELETE FROM client_acquisition_attributes WHERE id=$1',remnant)
            assert (await evaluate())[0] == baseline
            for scope, table in TABLES.items():
                if scope != 'activation_milestone_decisions':
                    for change, undo in (
                        (f'CREATE POLICY synthetic_hide ON {table} AS RESTRICTIVE USING(false)',
                         f'DROP POLICY synthetic_hide ON {table}'),
                        (f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY',
                         f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY'),
                        (f'REVOKE SELECT ON {table} FROM twobrain_rec_maintenance',
                         f'GRANT SELECT ON {table} TO twobrain_rec_maintenance'),
                    ):
                        await owner.execute(change)
                        try:
                            with pytest.raises((ActivationHold,replay.ReplayHold)):
                                await evaluate()
                        finally:
                            await owner.execute(undo)
                        assert (await evaluate())[0] == baseline
                closed(world["operator"], original+cases[scope])
                with pytest.raises((ActivationHold,replay.ReplayHold)):
                    await evaluate()  # Applied metadata cannot hide actual remaining rows.
                from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
                    LEVEL_RETENTION_CATEGORIES,
                    apply_basis_loss_disposition,
                    plan_processing_stop,
                )
                engine = create_async_engine(world["url"], poolclass=NullPool)
                try:
                    async with async_sessionmaker(engine)() as db:
                        plan = plan_processing_stop(
                            level_key=next(level for level, group in LEVEL_RETENTION_CATEGORIES.items() if scope in group),
                            basis_lost_at=now, reason="purpose_ended", affected_categories=(scope,),
                            deletion_deadlines={scope:now+timedelta(days=1)})
                        assert (await apply_basis_loss_disposition(db,plan))[0].disposition == 'delete'
                finally:
                    await engine.dispose()
                assert len((await evaluate())[0]) == 64
                closed(world["operator"], original+cases[scope].replace('stage=applied','stage=accepted').split(' applied_at=')[0]+'\n')
                with pytest.raises((ActivationHold,replay.ReplayHold)):
                    await evaluate()  # Even an empty category requires a result.
                closed(world["operator"], original)
                baseline = (await evaluate())[0]
            withdrawal = ("basis_withdrawal level=attribution_profiles state=withdrawn "
                "withdrawn_at="+now.date().isoformat()+" reason=purpose_ended\n")
            for missing in ('client_acquisition_attribute','visit_attribution','activation_milestone_decisions'):
                closed(world["operator"], original+withdrawal+''.join(v for k,v in cases.items() if k != missing))
                with pytest.raises((ActivationHold,replay.ReplayHold)):
                    await evaluate()
            closed(world["operator"], original+withdrawal+''.join(cases.values()))
            assert len((await evaluate())[0]) == 64
        finally:
            await source.close()
            await owner.close()

    asyncio.run(source_checks())
    closed(world["operator"], original)
    result = launch(world)
    assert result.returncode == 0, result.stdout+result.stderr
    assert json.loads(result.stdout)['deleted_rows'] == 2
    identities = world["owner"]("SELECT md5(jsonb_agg(to_jsonb(t) ORDER BY id)::text) FROM user_identities t",world["target"])
    for scope, table in TABLES.items():
        other = {name:world["owner"](f'SELECT md5(jsonb_agg(to_jsonb(t) ORDER BY id)::text) FROM {name} t',world["target"])
                 for name in TABLES.values() if name != table}
        closed(world["operator"], world["operator"].read_text()+cases[scope])
        result = launch(world)
        assert result.returncode == 0, result.stdout+result.stderr
        assert int(world["owner"](f'SELECT count(*) FROM {table}',world["target"])) == 0
        for name, expected in other.items():
            assert world["owner"](f'SELECT md5(jsonb_agg(to_jsonb(t) ORDER BY id)::text) FROM {name} t',world["target"]) == expected
    assert world["owner"]("SELECT md5(jsonb_agg(to_jsonb(t) ORDER BY id)::text) FROM user_identities t",world["target"]) == identities
    assert json.loads(launch(world).stdout)['deleted_rows'] == 0
    withdrawal = ("basis_withdrawal level=attribution_profiles state=withdrawn "
        "withdrawn_at="+now.date().isoformat()+" reason=purpose_ended\n")
    for missing in ('client_acquisition_attribute','visit_attribution','activation_milestone_decisions'):
        closed(world['operator'],original+withdrawal+''.join(v for k,v in cases.items() if k != missing))
        assert launch(world).returncode != 0  # Empty restored tables do not replace exact coverage.
    closed(world['operator'],original+withdrawal+''.join(cases.values()))
    assert launch(world).returncode == 0


def test_acquisition_finalizer_rolls_back_and_serializes_late_writer(replay_world, monkeypatch):
    import asyncpg
    from sqlalchemy import text

    from twobrain_rec_server.auth import account_closure
    from twobrain_rec_server.product_analytics import acquisition

    world = replay_world
    account = world['accounts'][0]
    world['owner'](f"""UPDATE user_identities SET status='active' WHERE id='{account}';
        UPDATE account_closure_requests SET state='scheduled',finalized_at=NULL,metadata_json='{{}}'
            WHERE id='{world['closure']}';
        INSERT INTO product_activation_milestones
            (id,account_id,event_name,event_id,occurred_at,accepted_at,safe_payload,source_kind)
            VALUES(gen_random_uuid(),'{account}','first_result_viewed',gen_random_uuid(),now(),now(),'{{}}','browser');
        INSERT INTO client_acquisition_attributes
            (id,account_id,source,landing_path,attribution_confidence,captured_at,graf_attribution_id)
            VALUES(gen_random_uuid(),'{account}','synthetic','/download','linked',now(),'graf_attr_synthetic123')""")

    async def run():
        engine = create_async_engine(world['url'],poolclass=NullPool)
        url = world['url']
        owner = await asyncpg.connect(host=url.host,port=url.port,user=url.username,
                                      password=url.password,database=url.database)
        task = None
        try:
            original = account_closure.delete_account_acquisition_attribute
            async def fail(*args,**kwargs):
                raise RuntimeError('synthetic_erasure_failure')
            with monkeypatch.context() as patch:
                patch.setattr(account_closure,'delete_account_acquisition_attribute',fail)
                async with async_sessionmaker(engine)() as db:
                    with pytest.raises(RuntimeError,match='synthetic_erasure_failure'):
                        await account_closure.finalize_account_close(db,request_id=world['closure'],now=datetime.now(UTC))
                    await db.rollback()
            assert account_closure.delete_account_acquisition_attribute is original
            assert await owner.fetchval('SELECT count(*) FROM product_activation_milestones WHERE account_id=$1',account) == 1
            assert await owner.fetchval('SELECT count(*) FROM client_acquisition_attributes WHERE account_id=$1',account) == 1
            assert await owner.fetchval('SELECT state FROM account_closure_requests WHERE id=$1',world['closure']) == 'scheduled'
            assert await owner.fetchval('SELECT status FROM user_identities WHERE id=$1',account) == 'active'
            monkeypatch.setattr(acquisition,'legal_basis_write_allowed',lambda *args,**kwargs:True)
            pid = asyncio.Future()
            async def late_writer():
                async with async_sessionmaker(engine)() as db:
                    pid.set_result(await db.scalar(text('SELECT pg_backend_pid()')))
                    attribute = acquisition.build_client_acquisition_attribute(account_id=account,landing_path='/download',source='synthetic')
                    result = await acquisition.record_client_acquisition_attribute_safely(db,attribute)
                    await db.commit()
                    return result
            async with async_sessionmaker(engine)() as db:
                await account_closure.finalize_account_close(db,request_id=world['closure'],now=datetime.now(UTC))
                task = asyncio.create_task(late_writer())
                writer_pid = await pid
                deadline = time.monotonic()+5
                while not await owner.fetchval('SELECT cardinality(pg_blocking_pids($1)) > 0',writer_pid):
                    assert time.monotonic() < deadline, 'writer_did_not_wait_on_identity'
                    await asyncio.sleep(.01)
                assert not task.done()
                await db.commit()
            assert await asyncio.wait_for(task,5) is False
            metadata = await owner.fetchval('SELECT metadata_json::text FROM account_closure_requests WHERE id=$1',world['closure'])
            result = json.loads(metadata)
            assert result['acquisition_attributes_purged_count'] == result['activation_decisions_purged_count'] == 1
            assert await owner.fetchval('SELECT count(*) FROM client_acquisition_attributes WHERE account_id=$1',account) == 0
            async with async_sessionmaker(engine)() as db:
                await account_closure.finalize_account_close(db,request_id=world['closure'],now=datetime.now(UTC))
                await db.commit()
            assert await owner.fetchval('SELECT metadata_json::text FROM account_closure_requests WHERE id=$1',world['closure']) == metadata
        finally:
            if task is not None and not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            await owner.close()
            await engine.dispose()
    asyncio.run(run())
