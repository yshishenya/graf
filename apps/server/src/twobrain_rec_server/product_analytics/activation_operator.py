"""Internal trusted-operator drain steps; no CLI, readiness writer or automatic resume.

The caller owns deployment lock, filesystem EX and both physical DB connections
until all work/cleanup finishes. A drained DB remains closed and its session EX
remains held through the caller's export. These steps never authorise admission.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from contextlib import suppress
from pathlib import Path

from .activation_fence import READY_FIELDS, ActivationHold, _object, _require

REQUIRED_WRITERS = frozenset({"rec-api", "rec-processing-worker", "rec-media-worker"})
OPTIONAL_WRITERS = frozenset({"rec-prompt-optimization-worker", "rec-maintenance"})
WRITERS = REQUIRED_WRITERS | OPTIONAL_WRITERS
INITIALIZERS = frozenset({"rec-migrate", "rec-db-runtime-bootstrap", "rec-minio-init"})
OPTIONAL_INITIALIZERS = frozenset({"rec-db-runtime-bootstrap"})
INFRASTRUCTURE = frozenset({"rec-postgres", "rec-minio", "rec-temporal"})
PRIVATE = "twobrain-rec-private"
MEDIA = "twobrain-rec-media-private"
SERVICE_NETWORKS = {
    "rec-api": {PRIVATE, "postal-network"},
    "rec-processing-worker": {PRIVATE, "postal-network"},
    "rec-prompt-optimization-worker": {PRIVATE},
    "rec-media-worker": {MEDIA},
    "rec-maintenance": {PRIVATE, "postal-network"},
    "rec-migrate": {PRIVATE},
    "rec-db-runtime-bootstrap": {PRIVATE},
    "rec-minio-init": {PRIVATE},
    "rec-postgres": {PRIVATE, MEDIA},
    "rec-minio": {PRIVATE, MEDIA},
    "rec-temporal": {PRIVATE, MEDIA},
}
# Read only selected metadata; never inspect Env, Cmd, query text or private rows.
CONTAINER_FORMAT = """{"id":{{json .Id}},"service":{{json (index .Config.Labels "com.docker.compose.service")}},"project":{{json (index .Config.Labels "com.docker.compose.project")}},"oneoff":{{json (index .Config.Labels "com.docker.compose.oneoff")}},"state":{"status":{{json .State.Status}},"running":{{json .State.Running}},"restarting":{{json .State.Restarting}},"paused":{{json .State.Paused}},"pid":{{json .State.Pid}},"exit":{{json .State.ExitCode}}},"networks":{{json .NetworkSettings.Networks}}}"""
NETWORK_FORMAT = """{"id":{{json .Id}},"name":{{json .Name}},"internal":{{json .Internal}},"project":{{json (index .Labels "com.docker.compose.project")}},"containers":{{json .Containers}}}"""


def _revoked(fence):
    _require(fence.exclusive, "activation_exclusive_required")
    dev, ino = fence.identity()
    record = _object(fence._file(fence.state_name))
    _require(
        set(record) == READY_FIELDS
        and type(record["version"]) is int
        and record["version"] == 1
        and record["status"] == "revoked"
        and record["reason"] == "operator_revoked"
        and record["mode"] == "local_only"
        and type(record["lock_dev"]) is int
        and type(record["lock_ino"]) is int
        and (record["lock_dev"], record["lock_ino"]) == (dev, ino),
        "activation_operator_not_revoked",
    )


async def _command(argv, *, deadline):
    """Own the CLI child through reap even when its waiter is cancelled twice."""

    async def owned():
        child = None
        try:
            async with asyncio.timeout_at(deadline):
                spawn = asyncio.create_task(
                    asyncio.create_subprocess_exec(
                        *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
                    )
                )
                try:
                    child = await asyncio.shield(spawn)
                except asyncio.CancelledError:
                    while not spawn.done():
                        with suppress(asyncio.CancelledError):
                            await asyncio.shield(spawn)
                    child = spawn.result()
                    raise
                output, _ = await child.communicate()
                _require(child.returncode == 0, "activation_operator_command_failed")
                return output
        finally:
            if child is not None and child.returncode is None:

                async def reap():
                    with suppress(ProcessLookupError):
                        child.terminate()
                    try:
                        await asyncio.wait_for(child.communicate(), 1)
                    except TimeoutError:
                        with suppress(ProcessLookupError):
                            child.kill()  # The CLI child only, never a Docker container.
                        await child.communicate()

                cleanup = asyncio.create_task(reap())
                while not cleanup.done():
                    with suppress(asyncio.CancelledError):
                        await asyncio.shield(cleanup)
                cleanup.result()

    task = asyncio.create_task(owned())
    cancelled = False
    try:
        while True:
            try:
                result = await asyncio.shield(task)
                break
            except asyncio.CancelledError:
                if not cancelled:
                    cancelled = True
                    task.cancel()
                if task.done():
                    break
        if cancelled:
            with suppress(BaseException):
                task.result()
            raise asyncio.CancelledError
        return result
    except TimeoutError:
        raise ActivationHold("activation_operator_command_timeout") from None


def _validate_inventory(rows, networks, *, project, postal_network, stopped):
    try:
        ids, services = set(), set()
        network_ids = {n["name"]: n["id"] for n in networks}
        _require(
            len(networks) == 2
            and set(network_ids) == {PRIVATE, MEDIA}
            and all(re.fullmatch(r"[0-9a-f]{64}", i) for i in network_ids.values())
            and len(set(network_ids.values())) == 2
            and all(
                n["internal"] is (n["name"] == MEDIA) and n["project"] == project for n in networks
            ),
            "activation_operator_network_invalid",
        )
        active = {PRIVATE: set(), MEDIA: set()}
        for row in rows:
            service, cid, state = row["service"], row["id"], row["state"]
            _require(
                service in SERVICE_NETWORKS
                and service not in services
                and re.fullmatch(r"[0-9a-f]{64}", cid) is not None
                and cid not in ids
                and row["project"] == project
                and row["oneoff"] == "False",
                "activation_operator_inventory_invalid",
            )
            services.add(service)
            ids.add(cid)
            status = state["status"]
            _require(
                type(state["pid"]) is int
                and type(state["exit"]) is int
                and state["restarting"] is False
                and state["paused"] is False,
                "activation_operator_container_state",
            )
            if service in INFRASTRUCTURE:
                allowed = {"running"}
            elif service in INITIALIZERS:
                allowed = {"exited"}
                _require(state["exit"] == 0, "activation_operator_initializer_failed")
            else:
                allowed = {"exited"} if stopped else {"running", "exited"}
                if service in OPTIONAL_WRITERS:
                    allowed |= {"created"}
            _require(
                status in allowed
                and state["running"] is (status == "running")
                and (state["pid"] > 0 if status == "running" else state["pid"] == 0),
                "activation_operator_container_state",
            )
            # A never-started optional Compose container has no attached networks.
            _require(
                set(row["networks"])
                == {
                    postal_network if n == "postal-network" else n
                    for n in SERVICE_NETWORKS[service]
                }
                or (service in OPTIONAL_WRITERS and status == "created" and row["networks"] == {}),
                "activation_operator_membership_invalid",
            )
            for name, endpoint in row["networks"].items():
                if name in active:
                    _require(
                        endpoint["NetworkID"]
                        in (
                            {network_ids[name]} if status == "running" else {"", network_ids[name]}
                        ),
                        "activation_operator_membership_invalid",
                    )
                    if status == "running":
                        active[name].add(cid)
        _require(
            services >= REQUIRED_WRITERS | (INITIALIZERS - OPTIONAL_INITIALIZERS) | INFRASTRUCTURE,
            "activation_operator_required_missing",
        )
        _require(
            all(set(n["containers"] or {}) == active[n["name"]] for n in networks),
            "activation_operator_foreign_membership",
        )
        return {r["service"]: r["id"] for r in rows}
    except (KeyError, TypeError, ValueError):
        raise ActivationHold("activation_operator_inventory_invalid") from None


async def _inventory(project, deadline):
    raw = await _command(
        [
            "docker",
            "container",
            "ls",
            "--all",
            "--no-trunc",
            "--quiet",
            "--filter",
            "label=com.docker.compose.project=" + project,
        ],
        deadline=deadline,
    )
    ids = raw.decode("ascii").split()
    _require(
        bool(ids)
        and len(set(ids)) == len(ids)
        and all(re.fullmatch(r"[0-9a-f]{64}", i) for i in ids),
        "activation_operator_inventory_invalid",
    )
    raw = await _command(
        ["docker", "inspect", "--format", CONTAINER_FORMAT, *ids], deadline=deadline
    )
    rows = [json.loads(line) for line in raw.splitlines()]
    _require(sorted(r["id"] for r in rows) == sorted(ids), "activation_operator_inventory_invalid")
    raw = await _command(
        ["docker", "network", "inspect", "--format", NETWORK_FORMAT, PRIVATE, MEDIA],
        deadline=deadline,
    )
    return rows, [json.loads(line) for line in raw.splitlines()]


async def stop_product_writers(fence, *, root: Path, project: str, postal_network: str):
    deadline = time.monotonic() + 120
    _revoked(fence)
    _require(
        root.is_absolute()
        and root.is_dir()
        and isinstance(project, str)
        and re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,62}", project)
        and isinstance(postal_network, str)
        and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", postal_network)
        and postal_network not in {PRIVATE, MEDIA},
        "activation_operator_configuration_invalid",
    )
    try:
        before, networks = await _inventory(project, deadline)
        expected = _validate_inventory(
            before, networks, project=project, postal_network=postal_network, stopped=False
        )
        _revoked(fence)
        await _command(
            [
                "docker",
                "compose",
                "--project-directory",
                str(root),
                "--project-name",
                project,
                "--file",
                str(root / "infra/docker-compose.yml"),
                "stop",
                *sorted(WRITERS & expected.keys()),
            ],
            deadline=deadline,
        )
        after, final_networks = await _inventory(project, deadline)
        actual = _validate_inventory(
            after, final_networks, project=project, postal_network=postal_network, stopped=True
        )
        _require(
            actual == expected
            and {n["name"]: n["id"] for n in networks}
            == {n["name"]: n["id"] for n in final_networks}
            and all(
                r["networks"].keys()
                == next(b for b in before if b["id"] == r["id"])["networks"].keys()
                for r in after
            ),
            "activation_operator_inventory_changed",
        )
        _revoked(fence)
        _require(time.monotonic() < deadline, "activation_operator_command_timeout")
        return actual
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        raise ActivationHold("activation_operator_inventory_unverified") from None


async def _database_identity(source, owner, *, name, oid, cluster_id):
    _require(
        not source.is_in_transaction() and not owner.is_in_transaction(),
        "activation_operator_transaction_active",
    )
    # The source has already been reduced by the trusted connection owner.
    source_row = await source.fetchrow("""SELECT current_database(), d.oid::bigint,
        session_user::text,current_user::text,current_setting('row_security'),
        r.rolsuper,r.rolbypassrls,r.rolcreatedb,r.rolcreaterole,r.rolinherit,
        system_identifier::text FROM pg_database d CROSS JOIN pg_roles r
        CROSS JOIN pg_control_system()
        WHERE d.datname=current_database() AND r.rolname=session_user""")
    _require(
        source_row is not None
        and tuple(source_row)
        == (
            name,
            oid,
            "twobrain_rec_maintenance",
            "twobrain_rec_maintenance",
            "on",
            False,
            False,
            False,
            False,
            False,
            cluster_id,
        ),
        "activation_operator_source_identity",
    )
    owner_row = await owner.fetchrow("""SELECT current_database(),session_user::text,
        current_user::text,r.rolsuper,system_identifier::text
        FROM pg_roles r CROSS JOIN pg_control_system() WHERE r.rolname=session_user""")
    _require(
        owner_row is not None
        and owner_row[0] == "postgres"
        and owner_row[1] == owner_row[2]
        and owner_row[3] is True
        and owner_row[4] == cluster_id,
        "activation_operator_owner_identity",
    )


async def _closed(owner, name, oid):
    row = await owner.fetchrow(
        "SELECT oid::bigint,datallowconn FROM pg_database WHERE datname=$1", name
    )
    _require(
        row is not None and tuple(row) == (oid, False), "activation_operator_database_not_closed"
    )


async def drain_product_database(fence, *, source, owner, name: str, oid: int, cluster_id: str):
    """One <=30s DB attempt. Caller retains connections and EX on every outcome."""
    deadline = time.monotonic() + 30
    _revoked(fence)
    _require(
        isinstance(name, str)
        and re.fullmatch(r"[a-z][a-z0-9_]{0,62}", name)
        and name not in {"postgres", "template0", "template1"}
        and type(oid) is int
        and oid > 0
        and isinstance(cluster_id, str)
        and re.fullmatch(r"[0-9]{1,20}", cluster_id),
        "activation_operator_database_binding",
    )
    try:
        async with asyncio.timeout_at(deadline):
            await _database_identity(source, owner, name=name, oid=oid, cluster_id=cluster_id)
            _revoked(fence)
            await owner.execute(f'ALTER DATABASE "{name}" ALLOW_CONNECTIONS false')
            await _closed(owner, name, oid)
            while not await source.fetchval("SELECT pg_try_advisory_lock(273,3)"):
                await asyncio.sleep(0.02)
            while True:
                await source.execute("SELECT pg_stat_clear_snapshot()")
                other = await source.fetchval(
                    """SELECT count(*) FROM pg_stat_activity
                    WHERE datid=$1 AND pid<>pg_backend_pid()""",
                    oid,
                )
                prepared = await source.fetchval("""SELECT count(*) FROM pg_prepared_xacts
                    WHERE database=current_database()""")
                if other == 0 and prepared == 0:
                    break
                await asyncio.sleep(0.02)
            await _database_identity(source, owner, name=name, oid=oid, cluster_id=cluster_id)
            await _closed(owner, name, oid)
            _revoked(fence)
            _require(time.monotonic() < deadline, "activation_operator_database_timeout")
            return {"db_oid": oid, "other_sessions": 0, "prepared_transactions": 0}
    except asyncio.CancelledError:
        raise
    except Exception:
        # Never expose driver/CLI errors with connection details or private text.
        raise ActivationHold("activation_operator_database_unverified") from None
