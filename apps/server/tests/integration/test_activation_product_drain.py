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
def owned_cluster():
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
                        for role in ("twobrain_rec_maintenance", "twobrain_rec_app", "twobrain_rec_media"):
                            await owner.execute(
                                f"CREATE ROLE {role} LOGIN NOSUPERUSER NOBYPASSRLS "
                                f"NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD '{password}'"
                            )
                        return
                    finally:
                        await owner.close()
                except (OSError, asyncpg.PostgresError):
                    if time.monotonic() >= deadline:
                        raise
                    await asyncio.sleep(0.1)

        asyncio.run(initialise())
        yield dict(host="127.0.0.1", port=port, user="twobrain_rec", password=password), container
    finally:
        if started:
            info = json.loads(docker("inspect", "--format", "{{json .Config.Labels}}", container))
            assert info["org.2brain.graf.test-owner"] == token
            docker("rm", "--force", "--volumes", container)


@pytest.fixture(scope="module")
def cluster(owned_cluster):
    return owned_cluster[0]


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


@pytest.mark.parametrize("mode", ["success", "body_error", "cancel_open", "cancel_close",
                                  "unknown_open", "missing_ex", "late_pid", "expired"])
def test_native_controlled_export(owned_cluster, fence, mode):
    cluster, container = owned_cluster

    async def run():
        name = "twobrain_rec_test_" + uuid4().hex
        owner = await asyncpg.connect(**cluster, database="postgres")
        source = late = task = None
        altered, release = asyncio.Event(), asyncio.Event()
        yielded = False
        try:
            await owner.execute(f'CREATE DATABASE "{name}" CONNECTION LIMIT 7')
            oid = await owner.fetchval("SELECT oid::bigint FROM pg_database WHERE datname=$1", name)
            cluster_id = await owner.fetchval("SELECT system_identifier::text FROM pg_control_system()")
            source = await asyncpg.connect(**cluster, database=name)
            await source.execute("CREATE TABLE synthetic(id int); INSERT INTO synthetic VALUES(41)")
            await source.execute("GRANT EXECUTE ON FUNCTION pg_control_system() TO twobrain_rec_maintenance")
            await source.execute("SET SESSION AUTHORIZATION twobrain_rec_maintenance")
            if mode == "late_pid":
                late = await asyncpg.connect(**cluster, database=name)
            await owner.execute(f'ALTER DATABASE "{name}" ALLOW_CONNECTIONS false')
            if mode != "missing_ex":
                await source.execute("SELECT pg_advisory_lock(273,3)")

            class DelayedOwner:
                def __getattr__(self, key):
                    return getattr(owner, key)

                async def execute(self, sql):
                    result = await owner.execute(sql)
                    opening = sql.endswith("ALLOW_CONNECTIONS true")
                    closing = sql.endswith("ALLOW_CONNECTIONS false")
                    if opening and mode == "unknown_open":
                        raise TimeoutError
                    if (opening and mode == "cancel_open") or (closing and mode == "cancel_close"):
                        altered.set()
                        await release.wait()  # Delay receipt after the real server committed.
                    return result

            async def export():
                nonlocal yielded
                async with operator._controlled_export(
                    fence, source=source, owner=DelayedOwner(), name=name, oid=oid,
                    cluster_id=cluster_id,
                    deadline=time.monotonic() + (-1 if mode == "expired" else 5),
                ) as original_limit:
                    yielded = True
                    assert original_limit == 7
                    assert tuple(await owner.fetchrow(
                        "SELECT datallowconn,datconnlimit FROM pg_database WHERE oid=$1", oid
                    )) == (True, 0)
                    # Ordinary roles remain denied while the trusted native dump can connect.
                    for role in ("twobrain_rec_app", "twobrain_rec_media", "twobrain_rec_maintenance"):
                        with pytest.raises(asyncpg.TooManyConnectionsError):
                            await asyncpg.connect(**{**cluster, "user": role}, database=name)
                    await operator._command([
                        "docker", "exec", container, "pg_dump", "-U", "twobrain_rec", "-d", name,
                        "--format=custom", "--file=/tmp/controlled.dump",
                    ], deadline=time.monotonic() + 5)
                    assert b"synthetic" in await operator._command([
                        "docker", "exec", container, "pg_restore", "--list", "/tmp/controlled.dump",
                    ], deadline=time.monotonic() + 5)
                    if mode == "body_error":
                        raise RuntimeError("synthetic_export_failure")

            task = asyncio.create_task(export())
            if mode.startswith("cancel_"):
                await asyncio.wait_for(altered.wait(), 5)
                task.cancel()
                await asyncio.sleep(.02)
                task.cancel()
                await asyncio.sleep(.02)
                assert not task.done()
                release.set()
            expected = (asyncio.CancelledError if mode.startswith("cancel_") else
                        RuntimeError if mode == "body_error" else ActivationHold)
            if mode == "success":
                await task
            else:
                with pytest.raises(expected):
                    await task
            assert yielded is (mode in {"success", "body_error", "cancel_close"})
            assert tuple(await owner.fetchrow(
                "SELECT datallowconn,datconnlimit FROM pg_database WHERE oid=$1", oid
            )) == (False, 7 if mode in {"missing_ex", "late_pid", "expired"} else 0)
            if mode not in {"missing_ex", "late_pid", "expired"}:
                assert await source.fetchval("""SELECT EXISTS(SELECT 1 FROM pg_locks
                    WHERE pid=pg_backend_pid() AND locktype='advisory' AND classid=273
                    AND objid=3 AND objsubid=2 AND mode='ExclusiveLock' AND granted)""")
                await source.execute("SELECT pg_stat_clear_snapshot()")
                assert await source.fetchval("SELECT count(*) FROM pg_stat_activity WHERE datid=$1 AND pid<>pg_backend_pid()", oid) == 0
            assert json.loads(fence.path.read_bytes())["status"] == "revoked"
        finally:
            release.set()
            if task is not None and not task.done():
                task.cancel()
                with suppress(BaseException):
                    await task
            for connection in (late, source):
                if connection is not None and not connection.is_closed():
                    await connection.close()
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


@pytest.mark.parametrize('case', ['good', 'revision', 'grant', 'role', 'membership', 'cancel_query',
                                'catalog_changed', 'access_initial', 'access_changed',
                                'catalog_always', 'catalog_state_changed', 'lifecycle_version', 'lifecycle_malformed',
                                'lifecycle_withdrawal', 'lifecycle_accepted', 'lifecycle_failed',
                                'lifecycle_applied', 'lifecycle_remnant', 'lifecycle_changed',
                                'lifecycle_closure', 'lifecycle_closure_changed', 'cancel_lifecycle',
                                'data_directory_initial', 'data_directory_changed'])
def test_native_runtime_database_preflight_full_schema(
    postgres_isolated_cluster_database_url, tmp_path, monkeypatch, case,
):
    """Only transport host/port are redirected on Mac; all SQL/verifier are real."""
    import runpy
    from contextlib import asynccontextmanager
    from datetime import UTC, datetime, timedelta
    from pathlib import Path

    from sqlalchemy.engine import make_url

    from twobrain_rec_server.product_analytics.legal_basis_lifecycle import LegalBasisLifecycleError
    from twobrain_rec_server.product_analytics.restore_replay import (
        CLOSURE_POLICY_QUERY,
        ReplayHold,
    )

    root = Path(__file__).resolve().parents[4]
    url = make_url(postgres_isolated_cluster_database_url)
    assert url.host == '127.0.0.1' and url.database.startswith('twobrain_rec_test_')
    bootstrap = runpy.run_path(str(root / 'apps/server/scripts/bootstrap_runtime_database_roles.py'))
    monkeypatch.setenv('TWOBRAIN_DB_HOST', url.host)
    monkeypatch.setenv('TWOBRAIN_DB_PORT', str(url.port))
    monkeypatch.setenv('TWOBRAIN_DB_NAME', url.database)
    for role in ('OWNER', 'APP', 'MAINTENANCE', 'MEDIA'):
        path = tmp_path / role
        path.write_text(url.password)
        path.chmod(0o600)
        monkeypatch.setenv('TWOBRAIN_DB_' + role + '_PASSWORD_FILE', str(path))
    asyncio.run(bootstrap['_bootstrap']())  # Own disposable cluster only, never operator code.
    original = operator._physical_connection

    directory_reads = []

    @asynccontextmanager
    async def local_transport(**kwargs):
        assert kwargs.pop('host') == '172.19.0.2' and kwargs.pop('port') == 5432
        if case == 'role' and kwargs['user'] == 'twobrain_rec_app':
            kwargs['user'] = 'twobrain_rec'  # Simulate credentials reaching a stronger actual role.
        async with original(host=url.host, port=url.port, **kwargs) as connection:
            class ObservedConnection:
                def __getattr__(self, name):
                    return getattr(connection, name)

                async def fetchval(self, query, *args):
                    result = await connection.fetchval(query, *args)
                    if query == 'SHOW data_directory':
                        directory_reads.append(result)
                        assert result == '/var/lib/postgresql/data'
                        if case == 'data_directory_initial' or (
                                case == 'data_directory_changed' and len(directory_reads) > 1):
                            return '/synthetic-wrong-directory'
                    return result

            yield ObservedConnection()
    monkeypatch.setattr(operator, '_physical_connection', local_transport)

    async def run():
        admin = await asyncpg.connect(host=url.host, port=url.port,
            user=url.username, password=url.password, database='postgres')
        locker = None
        try:
            await admin.execute(f'ALTER DATABASE "{url.database}" RENAME TO twobrain_rec')
            setup = await asyncpg.connect(host=url.host, port=url.port,
                user=url.username, password=url.password, database='twobrain_rec')
            now = datetime.now(UTC) - timedelta(minutes=1)
            register = 'legal_basis_state_version=2\n'
            if case == 'lifecycle_version':
                register = 'legal_basis_state_version=1\n'
            if case == 'lifecycle_malformed':
                register += 'disposition_case invalid\n'
            if case == 'lifecycle_withdrawal':
                register += ('basis_withdrawal level=anonymous_aggregate state=withdrawn '
                             f'withdrawn_at={now.date()} reason=purpose_ended\n')
            if case in {'lifecycle_accepted', 'lifecycle_failed', 'lifecycle_applied',
                        'lifecycle_remnant', 'lifecycle_changed'}:
                stage = {'lifecycle_accepted': 'accepted', 'lifecycle_failed': 'failed'}.get(case, 'applied')
                register += ('disposition_case case_ref=case_category decision_ref=decision_category '
                    'scope=anonymous_page_aggregate selector_ref=all owner_role=operator '
                    f'reason=purpose_ended decided_at={now.isoformat()} '
                    f'due_at={(now+timedelta(days=1)).isoformat()} stage={stage}')
                if stage == 'applied':
                    register += f' applied_at={now.isoformat()} rows_affected=0'
                register += '\n'
            register_raw = register.encode()
            closure_id = uuid4()
            insert_bucket = """INSERT INTO anonymous_page_aggregate_buckets
                (id,bucket_date,surface,landing_path)
                VALUES(gen_random_uuid(),current_date,'download','/download')"""
            try:
                if case in {'lifecycle_closure', 'lifecycle_closure_changed'}:
                    organization, account, workspace = uuid4(), uuid4(), uuid4()
                    await setup.execute("INSERT INTO organizations(id,slug,name) VALUES($1,'synthetic','Synthetic')", organization)
                    await setup.execute("""INSERT INTO user_identities
                        (id,organization_id,external_subject,locale,theme,status)
                        VALUES($1,$2,'synthetic','ru-RU','system','active')""", account, organization)
                    await setup.execute("""INSERT INTO workspaces
                        (id,organization_id,slug,name,kind,owner_user_id,
                         default_summary_template_key,default_summary_template_version)
                        VALUES($1,$2,'synthetic','Synthetic','personal',$3,'graf-auto-v1',1)""",
                        workspace, organization, account)
                    await setup.execute("""INSERT INTO account_closure_requests
                        (id,workspace_id,requested_by_user_id,request_key,state,finalize_at)
                        VALUES($1,$2,$3,'synthetic', $4, now()+interval '1 day')""",
                        closure_id, workspace, account,
                        'failed' if case == 'lifecycle_closure' else 'scheduled')
                if case == 'lifecycle_remnant':
                    await setup.execute(insert_bucket)
                if case == 'revision':
                    await setup.execute("UPDATE alembic_version SET version_num='synthetic_wrong_revision'")
                if case == 'grant':
                    await setup.execute('GRANT DELETE ON public.meetings TO twobrain_rec_media')
                if case == 'membership':
                    await setup.execute('CREATE ROLE synthetic_group; GRANT synthetic_group TO twobrain_rec_app')
                if case == 'access_initial':
                    await setup.execute('GRANT SELECT(account_id) ON client_acquisition_attributes TO twobrain_rec_media')
                if case == 'catalog_always':
                    await setup.execute('ALTER TABLE product_activation_milestones ENABLE ALWAYS TRIGGER activation_decision_immutable')
            finally:
                await setup.close()
            settings = {service: SimpleNamespace(database_url=make_url(
                'postgresql+asyncpg://role@rec-postgres:5432/twobrain_rec').set(
                    username=role, password=url.password).render_as_string(hide_password=False),
                prompt_optimization_database_url=None) for service, role in {
                    'rec-api': 'twobrain_rec_app', 'rec-processing-worker': 'twobrain_rec_app',
                    'rec-media-worker': 'twobrain_rec_media',
                    'rec-maintenance': 'twobrain_rec_maintenance',
                    'rec-prompt-optimization-worker': 'twobrain_rec_maintenance',
                }.items()}
            if case == 'good':
                with pytest.raises(TypeError, match='register_raw'):
                    operator._runtime_databases(settings=settings, password=url.password,
                        host='172.19.0.2', snapshot=root, deadline=time.monotonic()+15)
            entered = asyncio.Event()
            async def operation():
                async with operator._runtime_databases(settings=settings, password=url.password,
                        host='172.19.0.2', snapshot=root, deadline=time.monotonic()+15,
                        register_raw=register_raw) as (owner, source, proof):
                    assert await owner.fetchval('SELECT current_database()') == 'postgres'
                    assert await source.fetchval('SELECT session_user') == 'twobrain_rec_maintenance'
                    assert not source.is_in_transaction()
                    assert proof['db_name'] == 'twobrain_rec' and proof['db_oid'] > 0
                    assert len(proof['roles_sha256']) == 64
                    assert len(proof['retention_catalog_sha256']) == 64
                    assert len(proof['retention_access_sha256']) == 64
                    assert len(proof['lifecycle_sha256']) == 64
                    assert 'legal_basis_state_version' not in json.dumps(proof)
                    entered.set()
                    if case == 'cancel_query':
                        await source.execute('SELECT pg_sleep(3)')
                    if case in {'lifecycle_changed', 'lifecycle_closure_changed'}:
                        modifier = await asyncpg.connect(host=url.host, port=url.port,
                            user=url.username, password=url.password, database='twobrain_rec')
                        try:
                            if case == 'lifecycle_changed':
                                await modifier.execute(insert_bucket)
                            else:
                                await modifier.execute("UPDATE account_closure_requests SET state='failed' WHERE id=$1", closure_id)
                        finally:
                            await modifier.close()
                    if case in ('catalog_changed', 'access_changed', 'catalog_state_changed'):
                        modifier = await asyncpg.connect(host=url.host, port=url.port,
                            user=url.username, password=url.password, database='twobrain_rec')
                        try:
                            changes = {
                                'catalog_changed': 'ALTER TABLE product_activation_milestones DISABLE TRIGGER activation_decision_immutable',
                                'catalog_state_changed': 'ALTER TABLE product_activation_milestones ENABLE ALWAYS TRIGGER activation_decision_immutable',
                                'access_changed': 'GRANT SELECT(account_id) ON client_acquisition_attributes TO twobrain_rec_media',
                            }
                            await modifier.execute(changes[case])
                        finally:
                            await modifier.close()
            if case in {'cancel_query', 'cancel_lifecycle'}:
                if case == 'cancel_lifecycle':
                    locker = await asyncpg.connect(host=url.host, port=url.port,
                        user=url.username, password=url.password, database='twobrain_rec')
                    original_lifecycle = operator._local_lifecycle
                    source_pid = None
                    async def locked_lifecycle(source, raw, **kwargs):
                        nonlocal source_pid
                        source_pid = source.get_server_pid()
                        await locker.execute('BEGIN')
                        await locker.execute('LOCK TABLE account_closure_requests IN ACCESS EXCLUSIVE MODE')
                        return await original_lifecycle(source, raw, **kwargs)
                    monkeypatch.setattr(operator, '_local_lifecycle', locked_lifecycle)
                task = asyncio.create_task(operation())
                if case == 'cancel_lifecycle':
                    async def wait_for_actual_lifecycle_query():
                        while not await admin.fetchval("""SELECT EXISTS(SELECT FROM pg_stat_activity
                            WHERE application_name='graf-activation-preflight' AND wait_event_type='Lock'
                              AND left(query,128)=ANY($1::text[]) AND pid=$3::int
                              AND $2::int=ANY(pg_blocking_pids(pid)))""",
                                [CLOSURE_POLICY_QUERY[:128]],
                                locker.get_server_pid(), source_pid):
                            if task.done():
                                await task
                                raise AssertionError('lifecycle query was not observed')
                            await asyncio.sleep(.01)
                    await asyncio.wait_for(wait_for_actual_lifecycle_query(), 10)
                else:
                    await asyncio.wait_for(entered.wait(), 10)
                await asyncio.sleep(.03)
                task.cancel()
                await asyncio.sleep(0)
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            elif case in ('good', 'catalog_always', 'lifecycle_applied'):
                await operation()
            elif case in ('data_directory_initial', 'data_directory_changed'):
                with pytest.raises(operator.ActivationHold, match='staging_directory'):
                    await operation()
                assert entered.is_set() == (case == 'data_directory_changed')
                assert len(directory_reads) == (2 if entered.is_set() else 1)
            elif case in ('access_initial', 'access_changed'):
                with pytest.raises(operator.ActivationHold, match='retention_access'):
                    await operation()
            elif case == 'catalog_state_changed':
                with pytest.raises(operator.ActivationHold, match='retention_catalog_changed'):
                    await operation()
            else:
                with pytest.raises((operator.ActivationHold, ReplayHold, LegalBasisLifecycleError, RuntimeError)):
                    await operation()
            assert await admin.fetchval("SELECT count(*) FROM pg_stat_activity "
                "WHERE application_name='graf-activation-preflight'") == 0
        finally:
            if locker is not None:
                try:
                    await locker.execute('ROLLBACK')
                finally:
                    await locker.close()
            await admin.close()
    asyncio.run(run())
