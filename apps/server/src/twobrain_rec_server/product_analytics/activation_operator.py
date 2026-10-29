"""Internal trusted-operator drain steps; no CLI, readiness writer or automatic resume.

The caller owns deployment lock, filesystem EX and both physical DB connections
until all work/cleanup finishes. A drained DB remains closed and its session EX
remains held through the caller's export. These steps never authorise admission.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import time
import unicodedata
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

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


def _object_key(key):
    try:
        _require(isinstance(key, str) and 0 < len(key.encode("utf-8")) <= 1024
                 and "\0" not in key and unicodedata.normalize("NFC", key) == key
                 and all(p not in {"", ".", ".."} for p in key.split("/")),
                 "activation_operator_object_key_invalid")
    except UnicodeError:
        raise ActivationHold("activation_operator_object_key_invalid") from None
    return key


def _distinct_keys(keys):
    _require(len(keys) == len(set(keys)), "activation_operator_object_key_collision")
    names = set(keys)
    for key in keys:
        parts = key.split("/")
        _require(not any("/".join(parts[:i]) in names for i in range(1, len(parts))),
                 "activation_operator_object_key_collision")


def _file_manifest(root, *, deadline):
    """Private immutable backup bytes, traversed by held no-follow directory FDs."""
    def snapshot(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_nlink,
                info.st_size, info.st_mtime_ns, info.st_ctime_ns)

    def private(info, directory):
        _require(info.st_uid == os.geteuid()
                 and (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
                 and stat.S_IMODE(info.st_mode) == (0o700 if directory else 0o600)
                 and (directory or info.st_nlink == 1),
                 "activation_operator_backup_permissions")

    def visit(fd, prefix, *, read):
        _require(time.monotonic() < deadline, "activation_operator_manifest_timeout")
        before = os.fstat(fd)
        private(before, True)
        tree, rows = {prefix: snapshot(before)}, []
        for name in sorted(os.listdir(fd)):
            key = _object_key(prefix + name)
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            directory = stat.S_ISDIR(info.st_mode)
            private(info, directory)
            child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                            | (os.O_DIRECTORY if directory else 0), dir_fd=fd)
            try:
                _require(snapshot(os.fstat(child)) == snapshot(info),
                         "activation_operator_backup_changed")
                if directory:
                    children, entries = visit(child, key + "/", read=read)
                    tree.update(children)
                    rows.extend(entries)
                else:
                    tree[key] = snapshot(info)
                    if read:
                        digest, size = hashlib.sha256(), 0
                        while chunk := os.read(child, 1024 * 1024):
                            _require(time.monotonic() < deadline,
                                     "activation_operator_manifest_timeout")
                            size += len(chunk)
                            _require(size <= info.st_size, "activation_operator_backup_changed")
                            digest.update(chunk)
                        _require(size == info.st_size, "activation_operator_backup_changed")
                        rows.append((key, size, digest.hexdigest()))
                _require(snapshot(os.fstat(child)) == snapshot(info)
                         and snapshot(os.stat(name, dir_fd=fd, follow_symlinks=False))
                         == snapshot(info), "activation_operator_backup_changed")
            finally:
                os.close(child)
        _require(snapshot(os.fstat(fd)) == snapshot(before), "activation_operator_backup_changed")
        return tree, rows

    try:
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            tree, rows = visit(fd, "", read=True)
            current, _ = visit(fd, "", read=False)
            _require(tree == current and snapshot(os.lstat(root)) == tree[""],
                     "activation_operator_backup_changed")
            _distinct_keys([r[0] for r in rows])
            _require(time.monotonic() < deadline, "activation_operator_manifest_timeout")
            return sorted(rows)
        finally:
            os.close(fd)
    except (OSError, ValueError):
        raise ActivationHold("activation_operator_backup_unverified") from None


def _object_manifest(client, bucket, *, deadline):
    """Run in an owned worker thread; client must have finite HTTP timeouts/no retries."""
    from minio.error import S3Error

    def remaining():
        _require(time.monotonic() < deadline, "activation_operator_manifest_timeout")

    def configuration():
        remaining()
        _require(client.get_bucket_versioning(bucket).status is None,
                 "activation_operator_bucket_versioning")
        try:
            _require(client.get_bucket_lifecycle(bucket) is None,
                     "activation_operator_bucket_lifecycle")
        except S3Error as error:
            _require(error.code == "NoSuchLifecycleConfiguration",
                     "activation_operator_bucket_lifecycle")
        try:
            client.get_object_lock_config(bucket)
        except S3Error as error:
            _require(error.code == "ObjectLockConfigurationNotFoundError",
                     "activation_operator_bucket_object_lock")
        else:
            raise ActivationHold("activation_operator_bucket_object_lock")
        remaining()

    def metadata(obj):
        remaining()
        key = _object_key(obj.object_name)
        _require(type(obj.size) is int and obj.size >= 0
                 and isinstance(obj.etag, str) and bool(obj.etag)
                 and isinstance(obj.last_modified, datetime)
                 and obj.last_modified.utcoffset() is not None
                 and getattr(obj, "version_id", None) is None,
                 "activation_operator_object_metadata")
        return key, obj.size, obj.etag, obj.last_modified

    def listing():
        result = sorted(metadata(o) for o in client.list_objects(bucket, recursive=True))
        _distinct_keys([r[0] for r in result])
        remaining()
        return result

    try:
        configuration()
        before, rows = listing(), []
        for entry in before:
            key, expected_size, _, _ = entry
            initial_stat = metadata(client.stat_object(bucket, key))
            # S3 list has milliseconds; HTTP Last-Modified in HEAD has whole seconds.
            _require(initial_stat[:3] == entry[:3],
                     "activation_operator_object_changed")
            response = client.get_object(bucket, key)
            try:
                digest, size = hashlib.sha256(), 0
                for chunk in response.stream(1024 * 1024):
                    remaining()
                    _require(isinstance(chunk, bytes), "activation_operator_object_stream")
                    size += len(chunk)
                    _require(size <= expected_size, "activation_operator_object_changed")
                    digest.update(chunk)
                _require(size == expected_size, "activation_operator_object_changed")
                rows.append((key, size, digest.hexdigest()))
            finally:
                try:
                    response.close()
                finally:
                    response.release_conn()
            _require(metadata(client.stat_object(bucket, key)) == initial_stat,
                     "activation_operator_object_changed")
        _require(listing() == before, "activation_operator_object_changed")
        configuration()
        return rows
    except ActivationHold:
        raise
    except Exception:
        raise ActivationHold("activation_operator_object_unverified") from None


def _create_initial(fence, *, started_at: datetime, history_proof_sha256: str) -> bytes:
    """Internal final step only: caller has completed the full stopped verifier.

    No CLI accepts these arguments. Mark attempted before O_EXCL creation so a
    lost/partial initial or failed fsync cannot silently allocate another T0.
    """
    _revoked(fence)
    _require(fence.initial_marker()["state"] == "never_started",
             "activation_initial_already_attempted")
    _require(isinstance(started_at, datetime) and started_at.tzinfo is not None
             and started_at.utcoffset() == UTC.utcoffset(started_at)
             and isinstance(history_proof_sha256, str)
             and re.fullmatch(r"[a-f0-9]{64}", history_proof_sha256) is not None,
             "activation_initial_arguments_invalid")
    try:
        os.stat("initial.json", dir_fd=fence.directory, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        raise ActivationHold("activation_initial_already_attempted")
    dev, ino = fence.identity()
    raw = (json.dumps(dict(version=1, started_at=started_at.isoformat(), lock_dev=dev,
                           lock_ino=ino, history_proof_sha256=history_proof_sha256),
                      sort_keys=True) + "\n").encode()
    marker = (json.dumps(dict(version=1, state="attempted",
                              initial_sha256=hashlib.sha256(raw).hexdigest()),
                         sort_keys=True) + "\n").encode()
    fd = os.open("activation.lock", os.O_WRONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                 dir_fd=fence.directory)
    try:
        info = os.fstat(fd)
        _require((info.st_dev, info.st_ino) == (dev, ino), "activation_lock_changed")
        fence.identity()
        os.ftruncate(fd, 0)
        _require(os.write(fd, marker) == len(marker), "activation_initial_marker_write_failed")
        os.fsync(fd)
    finally:
        os.close(fd)
    _require(fence.initial_marker()["initial_sha256"] == hashlib.sha256(raw).hexdigest(),
             "activation_initial_marker_mismatch")
    fd = os.open("initial.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=fence.directory)
    try:
        os.fchmod(fd, 0o600)
        if os.fstat(fd).st_uid != fence.owner_uid:
            os.fchown(fd, fence.owner_uid, -1)
        _require(os.write(fd, raw) == len(raw), "activation_initial_write_failed")
        os.fsync(fd)
    finally:
        os.close(fd)
    os.fsync(fence.directory)
    fence.identity()
    _require(fence._file("initial.json") == raw, "activation_initial_write_failed")
    return raw


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


async def _settled_sql(operation):
    """Resolve an owned SQL step before returning even repeated waiter cancellation."""
    task = asyncio.create_task(operation)
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
        except Exception:
            break
    if cancelled:
        with suppress(BaseException):
            task.result()
        raise asyncio.CancelledError
    return task.result()


@asynccontextmanager
async def _rehearsal_resources(*, root, reference, owner, pg_container, cluster_id,
                               mc_image, network, user_file, password_file, client, deadline):
    """Native ephemeral restore; trusted caller replays before leaving this context.

    Caller retains the deployment lock, immutable installation/backup binding and
    stopped source/export proof. No readiness, T0, product restore or resume here.
    Every caller SQL/CLI child must be settled and every target connection closed
    before leaving the body. Unknown creates never authorise deletion by name.
    """
    from .restore_replay import private_bytes

    token = uuid4().hex
    target, schema = "rec_restore_rehearsal_" + token, "rec_restore_schema_" + token
    bucket = "twobrain-rec-restore-rehearsal-" + token
    pg_staging = "/tmp/twobrain-rec-backup." + token
    databases, containers, unknown, pg_commands = {}, [], set(), {}
    staging = None
    staging_identity = None
    pg_owned = bucket_owned = False

    async def command(*argv, until=deadline):
        return await _command(list(argv), deadline=until)

    async def wait_pg_commands(until):
        for marker, digest in list(pg_commands.items()):
            while True:
                raw = await command("docker", "exec", "--user=0", pg_container, "sh", "-c",
                    'if [ ! -e "$1" ] && [ ! -L "$1" ]; then echo pending; exit; fi; '
                    'test -f "$1" && test ! -L "$1" '
                    '&& test "$(stat -c %u "$1")" = 0 '
                    '&& test "$(stat -c %a "$1")" = 600 '
                    '&& test "$(stat -c %h "$1")" = 1 '
                    '&& test "$(stat -c %s "$1")" -ge 67 '
                    '&& test "$(stat -c %s "$1")" -le 69 && cat "$1"',
                    "sh", marker, until=until)
                if raw != b"pending\n":
                    _require(re.fullmatch(digest.encode() + rb":[0-9]{1,3}\n", raw)
                             and int(raw.split(b":")[1]) <= 255,
                             "activation_operator_native_completion_invalid")
                    del pg_commands[marker]
                    break
                _require(time.monotonic() < until, "activation_operator_native_completion_timeout")
                await asyncio.sleep(.02)

    async def pg_run(argv):
        marker = pg_staging + "/exec-" + uuid4().hex + ".done"
        digest = hashlib.sha256(json.dumps(argv).encode()).hexdigest()
        pg_commands[marker] = digest  # Unknown spawn must preserve the resources it may use.
        await command("docker", "exec", "--detach", "--user=0", pg_container, "sh", "-c",
            'umask 077; final="$1"; digest="$2"; shift 2; '
            '"$@" >/dev/null 2>&1; status=$?; set -C; '
            'printf "%s:%s\\n" "$digest" "$status" > "$final.partial" '
            '&& mv -- "$final.partial" "$final"', "sh", marker, digest, *argv)
        await wait_pg_commands(deadline)
        raw = await command("docker", "exec", "--user=0", pg_container, "cat", marker)
        _require(raw == (digest + ":0\n").encode(), "activation_operator_native_command_failed")

    async def identity(until):
        _require(not owner.is_in_transaction(), "activation_operator_transaction_active")
        row = await owner.fetchrow("""SELECT current_database(),session_user::text,
            current_user::text,r.rolsuper,system_identifier::text
            FROM pg_roles r CROSS JOIN pg_control_system() WHERE r.rolname=session_user""")
        _require(row is not None and tuple(row) == (
            "postgres", "twobrain_rec", "twobrain_rec", True, cluster_id),
            "activation_operator_owner_identity")
        raw = await command("docker", "exec", pg_container, "psql", "-XqAt",
            "-v", "ON_ERROR_STOP=1", "-U", "twobrain_rec", "-d", "postgres", "-c",
            "SELECT current_database()||':'||session_user||':'||current_user||':'||"
            "rolsuper||':'||system_identifier::text FROM pg_roles CROSS JOIN pg_control_system() "
            "WHERE rolname=session_user", until=until)
        _require(raw.decode().strip() == "postgres:twobrain_rec:twobrain_rec:true:" + cluster_id,
                 "activation_operator_container_identity")

    async def mc(action):
        # Record the immutable container ID before starting any native bucket mutation.
        label = "org.2brain.graf.rehearsal=" + token
        unknown.add("mc_container")
        raw = await command("docker", "create", "--pull=never", "--network", network,
            "--label", label, "--entrypoint", "/bin/sh", "--env", "MC_CONFIG_DIR=/tmp/graf-mc",
            "--mount", f"type=bind,src={reference / 'minio-objects'},dst=/backup,readonly",
            "--mount", f"type=bind,src={user_file},dst=/run/secrets/user,readonly",
            "--mount", f"type=bind,src={password_file},dst=/run/secrets/password,readonly",
            mc_image, "-c", 'set -eu; umask 077; '
            'mc alias set rec http://rec-minio:9000 "$(cat /run/secrets/user)" '
            '"$(cat /run/secrets/password)" >/dev/null; ' + action)
        cid = raw.decode().strip()
        _require(re.fullmatch(r"[0-9a-f]{64}", cid), "activation_operator_container_create_unknown")
        containers.append(cid)
        unknown.remove("mc_container")
        await command("docker", "start", "--attach", cid)
        state = json.loads(await command("docker", "inspect", "--format", "{{json .State}}", cid))
        _require(state["Status"] == "exited" and state["ExitCode"] == 0
                 and state["Running"] is False, "activation_operator_mirror_failed")

    async def prepare():
        nonlocal staging, staging_identity, pg_owned, bucket_owned
        async with asyncio.timeout_at(deadline):
            _require(root.is_absolute() and reference.is_absolute()
                     and re.fullmatch(r"[0-9a-f]{64}", pg_container)
                     and re.fullmatch(r"[0-9]{1,20}", cluster_id)
                     and re.fullmatch(r"sha256:[0-9a-f]{64}", mc_image)
                     and re.fullmatch(r"[0-9a-f]{64}", network),
                     "activation_operator_rehearsal_binding")
            for secret in (user_file, password_file):
                private_bytes(secret, limit=16384)
            before = await _settled_sql(asyncio.to_thread(_file_manifest, reference, deadline=deadline))
            expected = [(key.removeprefix("minio-objects/"), size, digest)
                        for key, size, digest in before if key.startswith("minio-objects/")]
            _require((reference / "minio-objects").is_dir(),
                     "activation_operator_backup_objects_missing")
            await command(sys.executable, str(root / "infra/scripts/rec-db-verify.py"),
                          str(reference), "--inventory")
            await identity(deadline)
            staging = Path(tempfile.mkdtemp(prefix="graf-rec-restore-"))
            staging.chmod(0o700)
            info = staging.lstat()
            staging_identity = info.st_dev, info.st_ino
            unknown.add("pg_staging")
            await command("docker", "exec", pg_container, "mkdir", "-m", "700", pg_staging)
            pg_owned = True
            unknown.remove("pg_staging")
            for artifact in ("postgres.dump", "schema.sql"):
                unknown.add("pg_upload")
                await command("docker", "cp", str(reference / artifact),
                              pg_container + ":" + pg_staging + "/input-" + artifact)
                unknown.remove("pg_upload")
            unknown.add("pg_upload")
            await command("docker", "cp", str(root / "infra/scripts/rec-db-backup-inventory.sql"),
                          pg_container + ":" + pg_staging + "/capture.sql")
            unknown.remove("pg_upload")
            for database in (target, schema):
                unknown.add(database)
                await owner.execute(f'CREATE DATABASE "{database}" CONNECTION LIMIT 0')
                oid = await owner.fetchval("SELECT oid::bigint FROM pg_database WHERE datname=$1",
                                          database)
                _require(type(oid) is int and oid > 0, "activation_operator_create_unknown")
                databases[database] = oid
                unknown.remove(database)
                if database == target:
                    await pg_run(["pg_restore", "--exit-on-error", "-U", "twobrain_rec",
                                  "-d", database, pg_staging + "/input-postgres.dump"])
                else:
                    await pg_run(["psql", "-Xq",
                        "-v", "ON_ERROR_STOP=1", "-U", "twobrain_rec", "-d", database,
                        "-f", pg_staging + "/input-schema.sql"])
                await pg_run(["sh", "-c",
                    'umask 077; exec psql "$@"', "sh", "-XqAt", "-v", "ON_ERROR_STOP=1",
                    "-U", "twobrain_rec", "-d", database, "-v", "expected_db=" + database,
                    "-v", "capture_dump=false", "-v", "staging=" + pg_staging,
                    "-f", pg_staging + "/capture.sql"])
                destination = staging / database
                destination.mkdir(mode=0o700)
                for artifact in ("schema.sql", "inventory.jsonl"):
                    path = destination / artifact
                    await command("docker", "cp", pg_container + ":" + pg_staging + "/" + artifact,
                                  str(path))
                    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                    try:
                        info = os.fstat(fd)
                        _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                                 and info.st_uid == os.geteuid() and info.st_size > 0,
                                 "activation_operator_restore_metadata")
                        os.fchmod(fd, 0o600)
                    finally:
                        os.close(fd)
                row = await owner.fetchrow("SELECT oid::bigint,datallowconn,datconnlimit "
                                          "FROM pg_database WHERE datname=$1", database)
                _require(row is not None and tuple(row) == (oid, True, 0),
                         "activation_operator_target_changed")
            await command(sys.executable, str(root / "infra/scripts/rec-db-verify.py"),
                str(reference), str(staging / target), target, str(staging / schema), schema)
            unknown.add("bucket")
            await mc("mc mb rec/" + bucket + " >/dev/null")
            bucket_owned = True
            unknown.remove("bucket")
            await mc("mc mirror /backup rec/" + bucket + " >/dev/null")
            restored = await _settled_sql(asyncio.to_thread(_object_manifest, client, bucket,
                                                           deadline=deadline))
            _require(restored == expected, "activation_operator_restored_bytes_mismatch")
            after = await _settled_sql(asyncio.to_thread(_file_manifest, reference, deadline=deadline))
            _require(after == before, "activation_operator_backup_changed")
            await identity(deadline)
            return dict(target=target, target_oid=databases[target], schema=schema,
                        schema_oid=databases[schema], bucket=bucket, staging=staging,
                        pg_staging=pg_staging)

    async def cleanup():
        # Retain ownership through repeated cancellation; no ready follows a cleanup failure.
        if not databases and not containers and not unknown and staging is None and not bucket_owned:
            return
        until = time.monotonic() + 30
        failed = bool(unknown)
        try:
            async with asyncio.timeout_at(until):
                await identity(until)
            identity_ok = True
        except Exception:
            identity_ok = False
            failed = True
        try:
            async with asyncio.timeout_at(until):
                await wait_pg_commands(until)
            pg_safe = "pg_upload" not in unknown
        except Exception:
            pg_safe = False
        failed |= not pg_safe
        for database, oid in databases.items():
            try:
                _require(identity_ok and pg_safe, "activation_operator_owner_identity")
                async with asyncio.timeout_at(until):
                    actual = await owner.fetchval(
                        "SELECT oid::bigint FROM pg_database WHERE datname=$1", database)
                    _require(actual == oid, "activation_operator_cleanup_identity")
                    await owner.execute(f'DROP DATABASE "{database}"')
                    _require(await owner.fetchval("SELECT count(*) FROM pg_database WHERE oid=$1 "
                        "OR datname=$2", oid, database) == 0, "activation_operator_cleanup_database")
            except Exception:
                failed = True
        mc_safe = "mc_container" not in unknown
        for cid in containers:
            try:
                await command("docker", "rm", "--force", "--volumes", cid, until=until)
                _require(not (await command("docker", "ps", "--all", "--quiet", "--no-trunc",
                    "--filter", "id=" + cid, until=until)).strip(),
                    "activation_operator_cleanup_container")
            except Exception:
                mc_safe = False
                failed = True
        if bucket_owned and mc_safe:
            def remove_bucket():
                from minio.deleteobjects import DeleteObject
                def entries():
                    for entry in client.list_objects(bucket, recursive=True):
                        _require(time.monotonic() < until, "activation_operator_cleanup_timeout")
                        yield DeleteObject(_object_key(entry.object_name))
                errors = list(client.remove_objects(bucket, entries()))
                _require(not errors, "activation_operator_cleanup_objects")
                _require(time.monotonic() < until, "activation_operator_cleanup_timeout")
                client.remove_bucket(bucket)
                _require(not client.bucket_exists(bucket), "activation_operator_cleanup_bucket")
            try:
                await _settled_sql(asyncio.to_thread(remove_bucket))
            except Exception:
                failed = True
        if pg_owned:
            try:
                _require(identity_ok and pg_safe, "activation_operator_owner_identity")
                await command("docker", "exec", pg_container, "sh", "-c",
                    'rm -rf -- "$1"; test ! -e "$1"', "sh", pg_staging, until=until)
            except Exception:
                failed = True
        if staging is not None:
            try:
                info = staging.lstat()
                _require(stat.S_ISDIR(info.st_mode)
                         and (info.st_dev, info.st_ino) == staging_identity,
                         "activation_operator_cleanup_staging")
                shutil.rmtree(staging)
                _require(not staging.exists(), "activation_operator_cleanup_staging")
            except Exception:
                failed = True
        _require(not failed, "activation_operator_rehearsal_cleanup_unverified")

    try:
        try:
            resources = await _settled_sql(prepare())
        except asyncio.CancelledError:
            raise
        except Exception:
            raise ActivationHold("activation_operator_rehearsal_unverified") from None
        yield resources
        _require(time.monotonic() < deadline, "activation_operator_rehearsal_timeout")
    finally:
        await _settled_sql(cleanup())
    _require(time.monotonic() < deadline, "activation_operator_rehearsal_timeout")


async def _quiet_database(source, oid):
    _require(not source.is_in_transaction(), "activation_operator_transaction_active")
    await source.execute("SELECT pg_stat_clear_snapshot()")
    row = await source.fetchrow("""SELECT
        EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND database=$1
          AND locktype='advisory' AND classid=273 AND objid=3 AND objsubid=2
          AND mode='ExclusiveLock' AND granted),
        (SELECT count(*) FROM pg_stat_activity WHERE datid=$1 AND pid<>pg_backend_pid()),
        (SELECT count(*) FROM pg_prepared_xacts WHERE database=current_database())""", oid)
    _require(row is not None and tuple(row) == (True, 0, 0),
             "activation_operator_database_not_quiet")


@asynccontextmanager
async def _controlled_export(fence, *, source, owner, name, oid, cluster_id, deadline):
    """Internal export window only. Caller retains stopped writers, EX and connections.

    No readiness/CLI or resume is exposed. The caller must reap its export children
    before leaving the body. The original limit is returned for its explicit later
    resume; this context always leaves the source closed with limit0 after mutation.
    """
    _require(isinstance(name, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,62}", name)
             and name not in {"postgres", "template0", "template1"}
             and type(oid) is int and oid > 0,
             "activation_operator_database_binding")
    attempted = False

    async def gate(expected):
        row = await owner.fetchrow(
            "SELECT oid::bigint,datallowconn,datconnlimit FROM pg_database WHERE datname=$1", name
        )
        _require(row is not None and tuple(row) == (oid, expected, 0),
                 "activation_operator_export_gate_unverified")

    async def prepare():
        nonlocal attempted
        async with asyncio.timeout_at(deadline):
            _revoked(fence)
            await _database_identity(source, owner, name=name, oid=oid, cluster_id=cluster_id)
            await _closed(owner, name, oid)
            await _quiet_database(source, oid)
            limit = await owner.fetchval("SELECT datconnlimit FROM pg_database WHERE oid=$1", oid)
            _require(type(limit) is int and limit >= -1, "activation_operator_export_limit_invalid")
            _revoked(fence)
            attempted = True  # A lost ALTER response still requires a closing attempt.
            await owner.execute(f'ALTER DATABASE "{name}" CONNECTION LIMIT 0')
            await gate(False)
            await owner.execute(f'ALTER DATABASE "{name}" ALLOW_CONNECTIONS true')
            await gate(True)
            await _quiet_database(source, oid)
            _revoked(fence)
            return limit

    async def close():
        # Cleanup may outlive the operation deadline; it never grants success.
        async with asyncio.timeout(30):
            await owner.execute(f'ALTER DATABASE "{name}" ALLOW_CONNECTIONS false')
            await gate(False)
            while True:
                try:
                    await _quiet_database(source, oid)
                    break
                except ActivationHold as error:
                    if str(error) != "activation_operator_database_not_quiet":
                        raise
                    await asyncio.sleep(.02)
            await _database_identity(source, owner, name=name, oid=oid, cluster_id=cluster_id)
            await gate(False)
            _revoked(fence)

    try:
        try:
            limit = await _settled_sql(prepare())
        except asyncio.CancelledError:
            raise
        except Exception:
            raise ActivationHold("activation_operator_export_unverified") from None
        yield limit
        _require(time.monotonic() < deadline, "activation_operator_export_timeout")
    finally:
        if attempted:
            try:
                await _settled_sql(close())
            except asyncio.CancelledError:
                raise
            except Exception:
                raise ActivationHold("activation_operator_export_close_unverified") from None
    _require(time.monotonic() < deadline, "activation_operator_export_timeout")


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
