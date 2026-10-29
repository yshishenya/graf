"""Real owned PostgreSQL17: late PID, advisory SH and prepared transaction barriers."""

import asyncio
import ipaddress
import json
import os
import subprocess
import time
from contextlib import suppress
from types import SimpleNamespace
from uuid import uuid4

import asyncpg
import pytest

from twobrain_rec_server.product_analytics import activation_operator as operator
from twobrain_rec_server.product_analytics.activation_fence import ActivationHold, activation_fence

pytestmark = pytest.mark.postgres


@pytest.fixture(scope="module")
def cluster():
    token = uuid4().hex
    container = "graf-drain-test-" + token
    password = uuid4().hex

    def docker(*args):
        return subprocess.run(
            ["docker", *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=45,
            env={**os.environ, "POSTGRES_PASSWORD": password},
        ).stdout.strip()

    started = False
    try:
        docker(
            "run",
            "--detach",
            "--rm",
            "--pull=never",
            "--name",
            container,
            "--label",
            "org.2brain.graf.test-owner=" + token,
            "--env",
            "POSTGRES_PASSWORD",
            "--env",
            "POSTGRES_USER=twobrain_rec",
            "--env",
            "POSTGRES_DB=postgres",
            "--tmpfs",
            "/var/lib/postgresql/data:rw",
            "--publish",
            "127.0.0.1::5432",
            "postgres:17-alpine",
            "-c",
            "max_prepared_transactions=10",
        )
        started = True
        port = int(docker("port", container, "5432/tcp").rsplit(":", 1)[1])

        async def initialise():
            deadline = time.monotonic() + 30
            while True:
                try:
                    if "PostgreSQL init process complete; ready for start up." not in docker(
                        "logs", container
                    ):
                        if time.monotonic() >= deadline:
                            raise RuntimeError("owned_cluster_start_timeout")
                        await asyncio.sleep(0.1)
                        continue
                    owner = await asyncpg.connect(
                        host="127.0.0.1",
                        port=port,
                        user="twobrain_rec",
                        password=password,
                        database="postgres",
                        timeout=2,
                    )
                    try:
                        await owner.execute(
                            "CREATE ROLE twobrain_rec_maintenance NOSUPERUSER "
                            "NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT"
                        )
                        return
                    finally:
                        await owner.close()
                except (OSError, asyncpg.PostgresError):
                    if time.monotonic() >= deadline:
                        raise
                    await asyncio.sleep(0.1)

        asyncio.run(initialise())
        yield dict(host="127.0.0.1", port=port, user="twobrain_rec", password=password)
    finally:
        if started:
            info = json.loads(docker("inspect", "--format", "{{json .Config.Labels}}", container))
            assert info["org.2brain.graf.test-owner"] == token
            docker("rm", "--force", "--volumes", container)


@pytest.fixture
def fence(tmp_path):
    tmp_path.chmod(0o700)
    lock = tmp_path / "activation.lock"
    lock.write_bytes(b"lock")
    lock.chmod(0o600)
    with activation_fence(
        tmp_path / "state.json", owner_uid=os.geteuid(), exclusive=True, readonly=False
    ) as value:
        value.revoke()
        yield value


@pytest.mark.parametrize(
    "barrier",
    [
        "late_pid",
        "shared_transaction",
        "prepared",
        "cancel",
        "invalid_identity",
        "active_transaction",
        "timeout",
        "unknown_alter",
    ],
)
def test_native_database_drain(cluster, fence, barrier, monkeypatch):
    async def run():
        name = "twobrain_rec_test_" + uuid4().hex
        owner = await asyncpg.connect(**cluster, database="postgres")
        connections = []
        task = None
        try:
            await owner.execute(f'CREATE DATABASE "{name}"')
            oid = await owner.fetchval("SELECT oid::bigint FROM pg_database WHERE datname=$1", name)
            cluster_id = await owner.fetchval(
                "SELECT system_identifier::text FROM pg_control_system()"
            )
            source = await asyncpg.connect(**cluster, database=name)
            connections.append(source)
            await source.execute(
                "GRANT EXECUTE ON FUNCTION pg_control_system() TO twobrain_rec_maintenance"
            )
            await source.execute("SET SESSION AUTHORIZATION twobrain_rec_maintenance")
            late = await asyncpg.connect(**cluster, database=name)
            connections.append(late)
            if barrier in {"shared_transaction", "timeout"}:
                await late.execute("BEGIN; SELECT pg_advisory_xact_lock_shared(273,3)")
            if barrier == "prepared":
                await late.execute("CREATE TABLE synthetic(id int)")
                await late.execute(
                    "BEGIN; INSERT INTO synthetic VALUES(1); PREPARE TRANSACTION 'synthetic'"
                )
                await late.close()
            if barrier == "active_transaction":
                await source.execute("BEGIN")
            if barrier in {"invalid_identity", "active_transaction"}:
                with pytest.raises(ActivationHold):
                    await operator.drain_product_database(
                        fence,
                        source=source,
                        owner=owner,
                        name=name,
                        oid=oid,
                        cluster_id="0" if barrier == "invalid_identity" else cluster_id,
                    )
                assert await owner.fetchval(
                    "SELECT datallowconn FROM pg_database WHERE oid=$1", oid
                )
                return
            prepared_seen, release_prepared = asyncio.Event(), asyncio.Event()

            class PreparedControl:
                # No extra source PID: resolve only after a real 0 PID/1 prepared read.
                def __getattr__(self, key):
                    return getattr(source, key)

                async def fetchval(self, sql, *args):
                    value = await source.fetchval(sql, *args)
                    if "pg_prepared_xacts" in sql and value:
                        assert (
                            await source.fetchval(
                                "SELECT count(*) FROM pg_stat_activity "
                                "WHERE datid=$1 AND pid<>pg_backend_pid()",
                                oid,
                            )
                            == 0
                        )
                        prepared_seen.set()
                        await release_prepared.wait()
                        await source.execute("RESET SESSION AUTHORIZATION")
                        await source.execute("ROLLBACK PREPARED 'synthetic'")
                        await source.execute("SET SESSION AUTHORIZATION twobrain_rec_maintenance")
                    return value

            class UnknownOwner:
                def __getattr__(self, key):
                    return getattr(owner, key)

                async def execute(self, sql):
                    result = await owner.execute(sql)
                    if sql.startswith("ALTER DATABASE"):
                        raise TimeoutError
                    return result

            if barrier == "timeout":
                # Accelerate only the chosen deadline; exercise native blocked SQL.
                monkeypatch.setattr(
                    operator, "time", SimpleNamespace(monotonic=lambda: time.monotonic() - 29.5)
                )
            task = asyncio.create_task(
                operator.drain_product_database(
                    fence,
                    source=PreparedControl() if barrier == "prepared" else source,
                    owner=UnknownOwner() if barrier == "unknown_alter" else owner,
                    name=name,
                    oid=oid,
                    cluster_id=cluster_id,
                )
            )
            async with asyncio.timeout(5):
                while await owner.fetchval(
                    "SELECT datallowconn FROM pg_database WHERE oid=$1", oid
                ):
                    if task.done():
                        await task
                    await asyncio.sleep(0.01)
            if barrier == "unknown_alter":
                with pytest.raises(ActivationHold):
                    await task
                assert not await owner.fetchval(
                    "SELECT datallowconn FROM pg_database WHERE oid=$1", oid
                )
                return
            await asyncio.sleep(0.1)
            assert not task.done()
            with pytest.raises(asyncpg.PostgresError):
                await asyncpg.connect(**cluster, database=name, timeout=1)
            if barrier == "shared_transaction":
                assert await owner.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_locks "
                    "WHERE locktype='advisory' AND classid=273 AND objid=3 "
                    "AND mode='ShareLock' AND granted)"
                )
            if barrier == "timeout":
                with pytest.raises(ActivationHold):
                    await asyncio.wait_for(task, 2)
            elif barrier == "cancel":
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            else:
                if barrier == "prepared":
                    await asyncio.wait_for(prepared_seen.wait(), 2)
                    assert not task.done()
                    release_prepared.set()
                if not late.is_closed():
                    await late.close()
                result = await asyncio.wait_for(task, 5)
                assert result == dict(db_oid=oid, other_sessions=0, prepared_transactions=0)
                assert await owner.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_locks "
                    "WHERE locktype='advisory' AND classid=273 AND objid=3 AND mode='ExclusiveLock' AND granted)"
                )
            assert not await owner.fetchval(
                "SELECT datallowconn FROM pg_database WHERE oid=$1", oid
            )
            assert json.loads(fence.path.read_bytes())["status"] == "revoked"
        finally:
            if task is not None and not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            for c in connections:
                if not c.is_closed():
                    await c.close()
            # Failure cleanup is restricted to this owned cluster/database.
            if barrier == "prepared" and await owner.fetchval(
                "SELECT count(*) FROM pg_prepared_xacts WHERE database=$1", name
            ):
                await owner.execute(f'ALTER DATABASE "{name}" ALLOW_CONNECTIONS true')
                resolver = await asyncpg.connect(**cluster, database=name)
                try:
                    await resolver.execute("ROLLBACK PREPARED 'synthetic'")
                finally:
                    await resolver.close()
            # Only this test-owned DB is removed, after its sessions close.
            await owner.execute(f'DROP DATABASE "{name}"')
            await owner.close()

    asyncio.run(run())


def test_native_compose_stop_on_owned_networks(fence, tmp_path, monkeypatch):
    token = uuid4().hex
    project = "grafdrain" + token
    # Production network names already exist locally; never attach to them.
    replacements = {
        name: project + "-" + name for name in (operator.PRIVATE, operator.MEDIA, "postal-network")
    }
    expected = {
        service: {replacements[n] for n in names}
        for service, names in operator.SERVICE_NETWORKS.items()
    }
    monkeypatch.setattr(operator, "PRIVATE", replacements[operator.PRIVATE])
    monkeypatch.setattr(operator, "MEDIA", replacements[operator.MEDIA])
    monkeypatch.setattr(operator, "SERVICE_NETWORKS", expected)
    root = tmp_path / "compose"
    (root / "infra").mkdir(parents=True)
    compose = root / "infra/docker-compose.yml"
    existing_ids = subprocess.run(
        ["docker", "network", "ls", "--quiet"], capture_output=True, text=True, check=True
    ).stdout.split()
    existing = json.loads(
        subprocess.run(
            ["docker", "network", "inspect", *existing_ids],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    occupied = [
        ipaddress.ip_network(c["Subnet"])
        for n in existing
        for c in (n["IPAM"]["Config"] or [])
        if c.get("Subnet") and ":" not in c["Subnet"]
    ]
    candidates = list(ipaddress.ip_network("198.19.0.0/16").subnets(new_prefix=28))
    subnets = [str(n) for n in candidates if not any(n.overlaps(c) for c in occupied)][:3]
    assert len(subnets) == 3
    document = dict(
        services={
            service: dict(
                image="postgres:17-alpine",
                entrypoint=[
                    "/bin/sh",
                    "-c",
                    "exit 0" if service in operator.INITIALIZERS else "exec sleep 600",
                ],
                networks=sorted(names),
                labels={"org.2brain.graf.test-owner": token},
            )
            for service, names in expected.items()
        },
        networks={
            n: dict(
                name=n,
                internal=n == operator.MEDIA,
                labels={"org.2brain.graf.test-owner": token},
                ipam={"config": [{"subnet": subnet}]},
            )
            for n, subnet in zip(replacements.values(), subnets, strict=True)
        },
    )
    compose.write_text(json.dumps(document))
    command = ["docker", "compose", "--project-name", project, "--file", str(compose)]

    def run(args):
        result = subprocess.run(args, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
        return result.stdout

    attempted = False
    try:
        attempted = True
        run([*command, "up", "--detach", "--no-build", "--pull", "never"])
        # Initializers must be observed exited0 before admission to stop.
        deadline = time.monotonic() + 10
        while True:
            ids = run([*command, "ps", "--all", "--quiet"]).split()
            records = [
                json.loads(line)
                for line in run(
                    ["docker", "inspect", "--format", operator.CONTAINER_FORMAT, *ids]
                ).splitlines()
            ]
            if all(
                r["state"]["status"] == "exited"
                for r in records
                if r["service"] in operator.INITIALIZERS
            ):
                break
            assert time.monotonic() < deadline
            time.sleep(0.05)
        result = asyncio.run(
            operator.stop_product_writers(
                fence,
                root=root.resolve(),
                project=project,
                postal_network=replacements["postal-network"],
            )
        )
        assert set(result) == set(expected)
        after = [
            json.loads(line)
            for line in run(
                ["docker", "inspect", "--format", operator.CONTAINER_FORMAT, *result.values()]
            ).splitlines()
        ]
        assert all(
            r["state"]["status"] == "exited" for r in after if r["service"] in operator.WRITERS
        )
        assert all(r["state"]["running"] for r in after if r["service"] in operator.INFRASTRUCTURE)
    finally:
        if attempted:
            # Project UUID and ownership labels restrict cleanup to this fixture.
            ids = run([*command, "ps", "--all", "--quiet"]).split()
            if ids:
                labels = [
                    json.loads(line)
                    for line in run(
                        ["docker", "inspect", "--format", "{{json .Config.Labels}}", *ids]
                    ).splitlines()
                ]
                assert all(x.get("org.2brain.graf.test-owner") == token for x in labels)
            run([*command, "down", "--volumes"])
            assert not run(
                [
                    "docker",
                    "container",
                    "ls",
                    "--all",
                    "--quiet",
                    "--filter",
                    "label=com.docker.compose.project=" + project,
                ]
            ).strip()
            assert not run(
                [
                    "docker",
                    "network",
                    "ls",
                    "--quiet",
                    "--filter",
                    "label=org.2brain.graf.test-owner=" + token,
                ]
            ).strip()
