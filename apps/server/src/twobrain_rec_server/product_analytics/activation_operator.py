"""Internal trusted-operator drain steps; no CLI, readiness writer or automatic resume.

The caller owns deployment lock, filesystem EX and both physical DB connections
until all work/cleanup finishes. A drained DB remains closed and its session EX
remains held through the caller's export. These steps never authorise admission.
"""

from __future__ import annotations

import asyncio
import fcntl
import grp
import hashlib
import ipaddress
import json
import os
import pwd
import re
import runpy
import shlex
import shutil
import stat
import sys
import tempfile
import time
import unicodedata
from contextlib import ExitStack, asynccontextmanager, contextmanager, suppress
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from .activation_fence import READY_FIELDS, ActivationHold, _object, _require, _timestamp

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


async def _command(argv, *, deadline, cwd=None):
    """Own the CLI child through reap even when its waiter is cancelled twice."""

    async def owned():
        child = None
        try:
            async with asyncio.timeout_at(deadline):
                spawn = asyncio.create_task(
                    asyncio.create_subprocess_exec(
                        *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, cwd=cwd
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


BACKUP_BINDING = {"source_sha", "image_id", "cluster_id", "db_name", "db_oid"}
BACKUP_ATTEMPT_FIELDS = BACKUP_BINDING | {
    "version", "run_id", "destination", "status", "reason", "started_at", "finished_at",
    "manifest_sha256",
}


def _backup_binding(binding):
    _require(set(binding) == BACKUP_BINDING
             and isinstance(binding["source_sha"], str)
             and re.fullmatch(r"[0-9a-f]{40}", binding["source_sha"])
             and isinstance(binding["image_id"], str)
             and re.fullmatch(r"sha256:[0-9a-f]{64}", binding["image_id"])
             and isinstance(binding["cluster_id"], str)
             and re.fullmatch(r"[0-9]{1,20}", binding["cluster_id"])
             and binding["db_name"] == "twobrain_rec"
             and type(binding["db_oid"]) is int and binding["db_oid"] > 0,
             "activation_operator_backup_binding")


def _previous_backup_attempt(fence):
    _revoked(fence)
    try:
        raw = fence._file("backup-attempt.json")
    except FileNotFoundError:
        _require(fence.initial_marker()["state"] == "never_started",
                 "activation_operator_backup_attempt_missing")
        try:
            os.stat("initial.json", dir_fd=fence.directory, follow_symlinks=False)
        except FileNotFoundError:
            return
        raise ActivationHold("activation_operator_backup_attempt_missing") from None
    record = _object(raw)
    _require(set(record) == BACKUP_ATTEMPT_FIELDS and type(record["version"]) is int
             and record["version"] == 1 and isinstance(record["run_id"], str)
             and re.fullmatch(r"[0-9a-f]{32}", record["run_id"])
             and record["destination"] == "backup-" + record["run_id"],
             "activation_operator_backup_attempt_invalid")
    _backup_binding({key: record[key] for key in BACKUP_BINDING})
    _require(record["status"] in {"failed", "completed"},
             "activation_operator_backup_attempt_unresolved")
    start, finish = _timestamp(record["started_at"]), _timestamp(record["finished_at"])
    _require(start <= finish <= datetime.now(UTC), "activation_operator_backup_attempt_invalid")
    if record["status"] == "failed":
        _require(record["reason"] in {"backup_failed", "cancelled"}
                 and record["manifest_sha256"] is None,
                 "activation_operator_backup_attempt_invalid")
    else:
        _require(record["reason"] == "verified" and isinstance(record["manifest_sha256"], str)
                 and re.fullmatch(r"[0-9a-f]{64}", record["manifest_sha256"]),
                 "activation_operator_backup_attempt_invalid")
    return record


def _write_backup_attempt(fence, record):
    _revoked(fence)
    previous = None
    if record["status"] == "completed":
        previous = fence._file("backup-attempt.json")
        prior = _object(previous)
        _require(prior["status"] == "in_progress" and prior["run_id"] == record["run_id"],
                 "activation_operator_backup_attempt_changed")
    name = ".backup-attempt-" + uuid4().hex
    raw = (json.dumps(record, sort_keys=True) + "\n").encode()
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=fence.directory)
    try:
        os.fchmod(fd, 0o600)
        if os.fstat(fd).st_uid != fence.owner_uid:
            os.fchown(fd, fence.owner_uid, -1)
        _require(os.write(fd, raw) == len(raw), "activation_operator_backup_attempt_write")
        os.fsync(fd)
        os.replace(name, "backup-attempt.json", src_dir_fd=fence.directory,
                   dst_dir_fd=fence.directory)
        os.fsync(fence.directory)
        _revoked(fence)
        _require(fence._file("backup-attempt.json") == raw,
                 "activation_operator_backup_attempt_write")
    except BaseException:
        if previous is not None:
            # The completed rename may be visible even if its directory fsync failed.
            # Restore the prior in_progress bytes on this exact owned inode first;
            # a second failing fsync cannot leave a visible completed admission.
            with suppress(OSError, ActivationHold):
                current = os.stat("backup-attempt.json", dir_fd=fence.directory, follow_symlinks=False)
                owned = os.fstat(fd)
                _require((current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino),
                         "activation_operator_backup_attempt_changed")
                os.ftruncate(fd, 0)
                os.lseek(fd, 0, os.SEEK_SET)
                _require(os.write(fd, previous) == len(previous), "activation_operator_backup_attempt_write")
                os.fsync(fd)
        raise
    finally:
        os.close(fd)
        with suppress(FileNotFoundError):
            os.unlink(name, dir_fd=fence.directory)


def _private_copy_modes(root, *, deadline):
    """Only a newly owned copy: reject unsafe nodes before changing their modes."""
    def visit(fd):
        info = os.fstat(fd)
        directory = stat.S_ISDIR(info.st_mode)
        _require(time.monotonic() < deadline and info.st_uid == os.geteuid()
                 and (directory or (stat.S_ISREG(info.st_mode) and info.st_nlink == 1)),
                 "activation_operator_backup_permissions")
        os.fchmod(fd, 0o700 if directory else 0o600)
        if directory:
            for name in os.listdir(fd):
                _object_key(name)
                child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                try:
                    visit(child)
                finally:
                    os.close(child)
        os.fsync(fd)

    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        visit(fd)
    finally:
        os.close(fd)


def _json_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


async def _backup_lifecycle(source, register):
    from twobrain_rec_server.db.tenant_context import maintenance_context_settings

    from . import restore_replay as replay
    from .legal_basis_lifecycle import _version2_records

    raw = replay.private_bytes(register)
    async with source.transaction(isolation="repeatable_read", readonly=True):
        for key, value in maintenance_context_settings(replay.CONTEXT).items():
            await source.execute("SELECT set_config($1,$2,true)", key, value)
        _require(await source.fetchval("SELECT rec_maintenance_allowed()") is True,
                 "activation_operator_lifecycle_context")
        policy = [tuple(row) for row in await source.fetch(replay.CLOSURE_POLICY_QUERY)]
        _require(policy == [("account_closure_requests_owner", True, "*", "{0}",
                             replay.CLOSURE_POLICY, replay.CLOSURE_POLICY)]
                 and await source.fetchval(replay.CLOSURE_ACCESS_QUERY) is True,
                 "activation_operator_lifecycle_policy")
        now = await source.fetchval("SELECT clock_timestamp()")
        text = raw.decode("utf-8")
        cases = replay.parse_disposition_cases(text, now=now)
        withdrawn = any(kind == "basis_withdrawal" and item["level"] == "attribution_profiles"
                        for kind, item in _version2_records(text))
        rows = [dict(row) for row in await source.fetch(replay.CLOSURE_ROWS_QUERY)]
        replay.replay_accounts(rows, cases, withdrawn=withdrawn, now=now)
        _require(replay.private_bytes(register) == raw, "activation_operator_register_changed")
        digest = _json_digest(dict(rows=rows, register_sha256=hashlib.sha256(raw).hexdigest()))
    # The caller must be able to run identity/quiet queries outside this transaction.
    _require(not source.is_in_transaction(), "activation_operator_transaction_active")
    return digest, raw


def _backup_metadata(root, reference):
    verifier = runpy.run_path(str(root / "infra/scripts/rec-db-verify.py"))
    verifier["checksums"](reference)
    header, rows = verifier["inventory"](reference, "twobrain_rec")
    canonical = verifier["schema"](reference)
    values = [rows[key] for key in sorted(rows)]
    return dict(snapshot=header, schema_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
        schema_revision=next(r["name"] for r in values if r["kind"] == "revision"),
        roles_sha256=_json_digest([r for r in values if r["kind"] in
                                  {"role", "role_setting", "membership"}]),
        ledger_invariants_sha256=_json_digest([r for r in values if r.get("relation") ==
            "product_activation_milestones" or r["kind"] in {"ledger_column", "ledger_access"}]),
        inventory_sha256=_json_digest(values))


BACKUP_METADATA_FIELDS = {"snapshot", "schema_sha256", "schema_revision", "roles_sha256",
                          "ledger_invariants_sha256", "inventory_sha256"}
BACKUP_CODE_FIELDS = {"operator", "capture", "verifier", "lifecycle", "replay", "tenant_context"}
BACKUP_MANIFEST_FIELDS = BACKUP_METADATA_FIELDS | {
    "version", "run_id", "binding", "started_at", "export_started_at", "export_closed_at",
    "finished_at", "cleanup", "code_sha256", "disposition_coverage_sha256", "artifacts",
    "objects", "object_count", "object_bytes",
}


def _manifest_entries(value):
    _require(isinstance(value, list), "activation_operator_backup_manifest_invalid")
    result = []
    for row in value:
        _require(isinstance(row, list) and len(row) == 3
                 and type(row[1]) is int and row[1] >= 0
                 and isinstance(row[2], str) and re.fullmatch(r"[0-9a-f]{64}", row[2]),
                 "activation_operator_backup_manifest_invalid")
        result.append((_object_key(row[0]), row[1], row[2]))
    _require(result == sorted(result), "activation_operator_backup_manifest_invalid")
    _distinct_keys([row[0] for row in result])
    return result


def _read_coherent_backup(*, root, reference, now, deadline):
    """Verify actual private bytes and native metadata; never a readiness receipt."""
    from .restore_replay import private_bytes

    try:
        initial = reference.lstat()
        _require(re.fullmatch(r"backup-[0-9a-f]{32}", reference.name)
                 and stat.S_ISDIR(initial.st_mode) and initial.st_uid == os.geteuid()
                 and stat.S_IMODE(initial.st_mode) == 0o700,
                 "activation_operator_backup_reference_invalid")
        files = _file_manifest(reference, deadline=deadline)
        entry = next(row for row in files if row[0] == "manifest.json")
        raw = private_bytes(reference / "manifest.json", limit=entry[1])
        digest = hashlib.sha256(raw).hexdigest()
        _require(digest == entry[2], "activation_operator_backup_changed")
        manifest = _object(raw)
        _require(set(manifest) == BACKUP_MANIFEST_FIELDS
                 and type(manifest["version"]) is int and manifest["version"] == 1
                 and manifest["run_id"] == reference.name.removeprefix("backup-")
                 and manifest["cleanup"] == "confirmed",
                 "activation_operator_backup_manifest_invalid")
        _backup_binding(manifest["binding"])
        moments = [_timestamp(manifest[key]) for key in
                   ("started_at", "export_started_at", "export_closed_at", "finished_at")]
        _require(moments == sorted(moments) and moments[-1] <= now,
                 "activation_operator_backup_timestamp_invalid")
        for key in ("schema_sha256", "roles_sha256", "ledger_invariants_sha256",
                    "inventory_sha256", "disposition_coverage_sha256"):
            _require(isinstance(manifest[key], str) and re.fullmatch(r"[0-9a-f]{64}", manifest[key]),
                     "activation_operator_backup_digest_invalid")
        code = manifest["code_sha256"]
        _require(isinstance(code, dict) and set(code) == BACKUP_CODE_FIELDS
                 and all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
                         for value in code.values()), "activation_operator_backup_digest_invalid")
        artifacts, objects = (_manifest_entries(manifest[key]) for key in ("artifacts", "objects"))
        _require(artifacts == [row for row in files if row[0] != "manifest.json"]
                 and objects == [(k.removeprefix("minio-objects/"), n, h)
                                 for k, n, h in artifacts if k.startswith("minio-objects/")]
                 and type(manifest["object_count"]) is int and manifest["object_count"] == len(objects)
                 and type(manifest["object_bytes"]) is int and manifest["object_bytes"] == sum(r[1] for r in objects),
                 "activation_operator_backup_manifest_mismatch")
        info = (reference / "minio-objects").lstat()
        _require(stat.S_ISDIR(info.st_mode), "activation_operator_backup_objects_missing")
        actual = _backup_metadata(root, reference)
        _require(set(actual) == BACKUP_METADATA_FIELDS
                 and _json_digest({key: manifest[key] for key in BACKUP_METADATA_FIELDS}) == _json_digest(actual),
                 "activation_operator_backup_metadata_mismatch")
        _require(_file_manifest(reference, deadline=deadline) == files,
                 "activation_operator_backup_changed")
        final = reference.lstat()
        _require(stat.S_ISDIR(final.st_mode) and final.st_uid == os.geteuid()
                 and stat.S_IMODE(final.st_mode) == 0o700
                 and (final.st_dev, final.st_ino) == (initial.st_dev, initial.st_ino)
                 and time.monotonic() < deadline, "activation_operator_backup_changed")
        return dict(destination=reference.name, manifest_sha256=digest, manifest=manifest,
                    identity=(initial.st_dev, initial.st_ino))
    except ActivationHold:
        raise
    except (OSError, ValueError, TypeError, KeyError, StopIteration, RecursionError):
        raise ActivationHold("activation_operator_backup_unverified") from None


def _verified_backup_set(fence, *, root, parent, binding, now, deadline):
    """Physical latest plus a distinct complete historical point, never rehearsal."""
    parent_fd = None
    try:
        _revoked(fence)
        _backup_binding(binding)
        _require(isinstance(now, datetime) and now.tzinfo is not None
                 and now.utcoffset() == UTC.utcoffset(now)
                 and time.monotonic() < deadline <= time.monotonic()+600,
                 "activation_operator_backup_verification_arguments")
        parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK)
        initial = os.fstat(parent_fd)

        def parent_identity():
            info = parent.lstat()
            _require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
                     and stat.S_IMODE(info.st_mode) == 0o700
                     and (info.st_dev, info.st_ino) == (initial.st_dev, initial.st_ino),
                     "activation_operator_backup_parent_changed")
            _require(time.monotonic() < deadline, "activation_operator_backup_verification_timeout")

        parent_identity()
        before = fence._file("backup-attempt.json")
        attempt = _previous_backup_attempt(fence)
        _require(attempt == _object(before) and attempt["status"] == "completed"
                 and {key: attempt[key] for key in BACKUP_BINDING} == binding,
                 "activation_operator_backup_latest_unverified")
        latest = _read_coherent_backup(root=root, reference=parent / attempt["destination"], now=now, deadline=deadline)
        _require(latest["manifest_sha256"] == attempt["manifest_sha256"]
                 and latest["manifest"]["binding"] == binding
                 and latest["manifest"]["finished_at"] == attempt["finished_at"]
                 and 0 <= (now-_timestamp(attempt["finished_at"])).total_seconds() < 26*3600,
                 "activation_operator_backup_latest_unverified")
        names = sorted(name for name in os.listdir(parent_fd)
                       if re.fullmatch(r"backup-[0-9a-f]{32}", name) and name != latest["destination"])
        companion = None
        for name in names:
            parent_identity()
            try:
                companion = _read_coherent_backup(root=root, reference=parent / name, now=now, deadline=deadline)
            except ActivationHold:
                # A failed/old-layout point does not count. Parent/time failures
                # remain global and cannot disappear inside this candidate skip.
                parent_identity()
                continue
            break
        _require(companion is not None, "activation_operator_backup_minimum_missing")
        for selected in (latest, companion):
            reference = parent / selected["destination"]
            rows = _file_manifest(reference, deadline=deadline)
            info = reference.lstat()
            recorded = _manifest_entries(selected["manifest"]["artifacts"])
            _require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
                     and stat.S_IMODE(info.st_mode) == 0o700
                     and (info.st_dev, info.st_ino) == selected["identity"]
                     and [r for r in rows if r[0] != "manifest.json"] == recorded
                     and next(h for k, _, h in rows if k == "manifest.json") == selected["manifest_sha256"],
                     "activation_operator_backup_changed")
        parent_identity()
        _require(fence._file("backup-attempt.json") == before,
                 "activation_operator_backup_attempt_changed")
        _revoked(fence)
        return dict(latest=latest, companion=companion)
    except ActivationHold:
        raise
    except (OSError, ValueError, TypeError, KeyError, StopIteration, RecursionError):
        raise ActivationHold("activation_operator_backup_set_unverified") from None
    finally:
        if parent_fd is not None:
            os.close(parent_fd)


def _write_backup_manifest(reference, manifest, *, deadline):
    # Object lists can exceed the fence's 16 KiB receipt limit. Stream the private file.
    path = reference / "manifest.json"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w", closefd=False) as stream:
            for chunk in json.JSONEncoder(sort_keys=True).iterencode(manifest):
                _require(time.monotonic() < deadline, "activation_operator_backup_timeout")
                stream.write(chunk)
            stream.write("\n")
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(reference, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    rows = _file_manifest(reference, deadline=deadline)
    # Readback includes all bytes, ownership and modes, not just buffered JSON.
    expected = hashlib.sha256()
    for chunk in json.JSONEncoder(sort_keys=True).iterencode(manifest):
        expected.update(chunk.encode())
    expected.update(b"\n")
    actual = next(digest for key, _, digest in rows if key == "manifest.json")
    _require(actual == expected.hexdigest()
             and [row for row in rows if row[0] != "manifest.json"] == manifest["artifacts"],
             "activation_operator_backup_manifest_changed")
    return actual


async def _create_coherent_backup(fence, *, root, parent, source, owner, binding, pg_container,
                                  bucket, register, mc_image, network, user_file, password_file,
                                  client, deadline):
    """Internal stopped-copy stage; caller owns installation, writers and all locks.

    Never opens admission or resumes the product. Incomplete copies are preserved;
    unknown native outcomes retain staging. Source objects are only read.
    """
    from .restore_replay import private_bytes

    token = uuid4().hex
    reference = parent / ("backup-" + token)
    pg_staging = "/tmp/twobrain-rec-backup." + token
    containers, unknown, pg_commands = [], set(), {}
    pg_owned = False
    attempt = None
    parent_fd = None
    name, oid, cluster_id = binding["db_name"], binding["db_oid"], binding["cluster_id"]

    async def identity():
        await _database_identity(source, owner, name=name, oid=oid, cluster_id=cluster_id)
        await _closed(owner, name, oid)
        await _quiet_database(source, oid)
        _revoked(fence)

    async def cleanup():
        until = time.monotonic() + 30
        failed = bool(unknown)
        try:
            async with asyncio.timeout_at(until):
                await _database_identity(source, owner, name=name, oid=oid, cluster_id=cluster_id)
                await _wait_pg_commands(pg_container, pg_commands, deadline=until)
            pg_safe = not (unknown & {"pg_upload", "pg_staging"})
        except Exception:
            pg_safe = False
        failed |= not pg_safe
        for cid in containers:
            try:
                await _native_command("docker", "rm", "--force", "--volumes", cid, deadline=until)
                _require(not (await _native_command("docker", "ps", "--all", "--quiet",
                    "--no-trunc", "--filter", "id=" + cid, deadline=until)).strip(),
                    "activation_operator_cleanup_container")
            except Exception:
                failed = True
        if pg_owned and pg_safe:
            try:
                await _native_command("docker", "exec", pg_container, "sh", "-c",
                    'rm -rf -- "$1"; test ! -e "$1"', "sh", pg_staging, deadline=until)
            except Exception:
                failed = True
        _require(not failed, "activation_operator_backup_cleanup_unverified")

    async def copy():
        nonlocal attempt, pg_owned, parent_fd
        try:
            async with asyncio.timeout_at(deadline):
                _backup_binding(binding)
                _require(0 < deadline - time.monotonic() <= 600
                         and root.is_absolute() and parent.is_absolute()
                         and re.fullmatch(r"[0-9a-f]{64}", pg_container)
                         and re.fullmatch(r"sha256:[0-9a-f]{64}", mc_image)
                         and re.fullmatch(r"[0-9a-f]{64}", network)
                         and isinstance(bucket, str)
                         and re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", bucket),
                         "activation_operator_backup_binding")
                parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK)
                info = os.fstat(parent_fd)
                _require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
                         and stat.S_IMODE(info.st_mode) == 0o700
                         and (info.st_dev, info.st_ino) == (parent.lstat().st_dev, parent.lstat().st_ino),
                         "activation_operator_backup_permissions")
                parent_identity = info.st_dev, info.st_ino
                for secret in (user_file, password_file):
                    private_bytes(secret, limit=16384)
                await identity()
                raw = await _native_command("docker", "exec", pg_container, "psql", "-XqAt",
                    "-v", "ON_ERROR_STOP=1", "-U", "twobrain_rec", "-d", "postgres", "-c",
                    "SELECT system_identifier::text FROM pg_control_system()", deadline=deadline)
                _require(raw.decode().strip() == cluster_id, "activation_operator_container_identity")
                _previous_backup_attempt(fence)
                started = datetime.now(UTC).isoformat()
                attempt = dict(version=1, run_id=token, destination=reference.name, **binding,
                    started_at=started, finished_at=None, status="in_progress", reason="running",
                    manifest_sha256=None)
                _write_backup_attempt(fence, attempt)
                os.mkdir(reference.name, mode=0o700, dir_fd=parent_fd)
                reference_info = reference.lstat()
                reference_identity = reference_info.st_dev, reference_info.st_ino
                (reference / "minio-objects").mkdir(mode=0o700)
                export_started = datetime.now(UTC).isoformat()
                async with _controlled_export(fence, source=source, owner=owner, name=name,
                        oid=oid, cluster_id=cluster_id, deadline=deadline):
                    try:
                        coverage, register_raw = await _settled_sql(_backup_lifecycle(source, register))
                        before = await _settled_sql(asyncio.to_thread(_object_manifest, client, bucket,
                                                                     deadline=deadline))
                        unknown.add("pg_staging")
                        await _native_command("docker", "exec", pg_container, "mkdir", "-m", "700",
                                              pg_staging, deadline=deadline)
                        pg_owned = True
                        unknown.remove("pg_staging")
                        unknown.add("pg_upload")
                        await _native_command("docker", "cp", str(root / "infra/scripts/rec-db-backup-inventory.sql"),
                            pg_container + ":" + pg_staging + "/capture.sql", deadline=deadline)
                        unknown.remove("pg_upload")
                        await _pg_run(pg_container, pg_staging, pg_commands, ["sh", "-c",
                            'umask 077; exec psql "$@"', "sh", "-XqAt", "-v", "ON_ERROR_STOP=1",
                            "-U", "twobrain_rec", "-d", name, "-v", "expected_db=" + name,
                            "-v", "capture_dump=true", "-v", "staging=" + pg_staging,
                            "-f", pg_staging + "/capture.sql"], deadline=deadline)
                        for artifact in ("postgres.dump", "schema.sql", "inventory.jsonl", "checksums.sha256"):
                            unknown.add("pg_upload")
                            await _native_command("docker", "cp", pg_container + ":" + pg_staging + "/" + artifact,
                                                  str(reference / artifact), deadline=deadline)
                            unknown.remove("pg_upload")
                        await _mc_run("mc mirror rec/" + bucket + " /backup >/dev/null", token=token,
                            objects=reference / "minio-objects", writable=True, mc_image=mc_image,
                            network=network, user_file=user_file, password_file=password_file,
                            containers=containers, unknown=unknown, deadline=deadline)
                        await _settled_sql(asyncio.to_thread(_private_copy_modes, reference, deadline=deadline))
                        files = await _settled_sql(asyncio.to_thread(_file_manifest, reference, deadline=deadline))
                        metadata = await _settled_sql(asyncio.to_thread(_backup_metadata, root, reference))
                        after = await _settled_sql(asyncio.to_thread(_object_manifest, client, bucket,
                                                                    deadline=deadline))
                        copied = [(key.removeprefix("minio-objects/"), size, digest)
                                  for key, size, digest in files if key.startswith("minio-objects/")]
                        _require(before == after == copied, "activation_operator_backup_objects_changed")
                        _require(private_bytes(register) == register_raw, "activation_operator_register_changed")
                    finally:
                        await _settled_sql(cleanup())
                await identity()
                export_closed = datetime.now(UTC).isoformat()
                info = parent.lstat()
                _require((info.st_dev, info.st_ino) == parent_identity
                         and stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
                         and stat.S_IMODE(info.st_mode) == 0o700,
                         "activation_operator_backup_parent_changed")
                _require(await _settled_sql(asyncio.to_thread(_file_manifest, reference, deadline=deadline))
                         == files, "activation_operator_backup_changed")
                paths = {"operator": Path(__file__), "capture": root / "infra/scripts/rec-db-backup-inventory.sql",
                    "verifier": root / "infra/scripts/rec-db-verify.py",
                    "lifecycle": Path(__file__).with_name("legal_basis_lifecycle.py"),
                    "replay": Path(__file__).with_name("restore_replay.py"),
                    "tenant_context": Path(__file__).parents[1] / "db/tenant_context.py"}
                code = {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in paths.items()}
                manifest = dict(version=1, run_id=token, binding=binding, started_at=started,
                    export_started_at=export_started, export_closed_at=export_closed,
                    finished_at=datetime.now(UTC).isoformat(), cleanup="confirmed", **metadata,
                    code_sha256=code, disposition_coverage_sha256=coverage, artifacts=files,
                    objects=before, object_count=len(before), object_bytes=sum(row[1] for row in before))
                digest = await _settled_sql(asyncio.to_thread(_write_backup_manifest, reference,
                                                             manifest, deadline=deadline))
                info, current = os.fstat(parent_fd), parent.lstat()
                child = os.stat(reference.name, dir_fd=parent_fd, follow_symlinks=False)
                _require((info.st_dev, info.st_ino) == (current.st_dev, current.st_ino) == parent_identity
                         and stat.S_ISDIR(current.st_mode) and current.st_uid == os.geteuid()
                         and stat.S_IMODE(current.st_mode) == 0o700
                         and stat.S_ISDIR(child.st_mode)
                         and (child.st_dev, child.st_ino) == reference_identity,
                         "activation_operator_backup_parent_changed")
                os.fsync(parent_fd)  # Persist the backup-UUID entry before a completed attempt.
                _require(time.monotonic() < deadline, "activation_operator_backup_timeout")
                attempt.update(status="completed", reason="verified", finished_at=manifest["finished_at"],
                               manifest_sha256=digest)
                _write_backup_attempt(fence, attempt)
                _require(time.monotonic() < deadline, "activation_operator_backup_timeout")
                return dict(destination=reference.name, manifest_sha256=digest)
        except BaseException as error:
            if attempt is not None:
                attempt.update(status="failed", reason="cancelled" if isinstance(error, asyncio.CancelledError)
                               else "backup_failed", finished_at=datetime.now(UTC).isoformat(), manifest_sha256=None)
                _write_backup_attempt(fence, attempt)
            raise
        finally:
            if parent_fd is not None:
                os.close(parent_fd)

    task = asyncio.create_task(copy())
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            if not cancelled:
                cancelled = True
                task.cancel()
        except Exception:
            break
    if cancelled:
        with suppress(BaseException):
            task.result()
        raise asyncio.CancelledError
    try:
        return task.result()
    except Exception:
        raise ActivationHold("activation_operator_backup_unverified") from None


async def _native_command(*argv, deadline):
    return await _command(list(argv), deadline=deadline)


async def _wait_pg_commands(pg_container, pg_commands, *, deadline):
    for marker, digest in list(pg_commands.items()):
        while True:
            raw = await _native_command("docker", "exec", "--user=0", pg_container, "sh", "-c",
                'if [ ! -e "$1" ] && [ ! -L "$1" ]; then echo pending; exit; fi; '
                'test -f "$1" && test ! -L "$1" '
                '&& test "$(stat -c %u "$1")" = 0 '
                '&& test "$(stat -c %a "$1")" = 600 '
                '&& test "$(stat -c %h "$1")" = 1 '
                '&& test "$(stat -c %s "$1")" -ge 67 '
                '&& test "$(stat -c %s "$1")" -le 69 && cat "$1"',
                "sh", marker, deadline=deadline)
            if raw != b"pending\n":
                _require(re.fullmatch(digest.encode() + rb":[0-9]{1,3}\n", raw)
                         and int(raw.split(b":")[1]) <= 255,
                         "activation_operator_native_completion_invalid")
                del pg_commands[marker]
                break
            _require(time.monotonic() < deadline, "activation_operator_native_completion_timeout")
            await asyncio.sleep(.02)

async def _pg_run(pg_container, pg_staging, pg_commands, argv, *, deadline):
    marker = pg_staging + "/exec-" + uuid4().hex + ".done"
    digest = hashlib.sha256(json.dumps(argv).encode()).hexdigest()
    pg_commands[marker] = digest  # Unknown spawn must preserve the resources it may use.
    await _native_command("docker", "exec", "--detach", "--user=0", pg_container, "sh", "-c",
        'umask 077; final="$1"; digest="$2"; shift 2; '
        '"$@" >/dev/null 2>&1; status=$?; set -C; '
        'printf "%s:%s\\n" "$digest" "$status" > "$final.partial" '
        '&& mv -- "$final.partial" "$final"', "sh", marker, digest, *argv, deadline=deadline)
    await _wait_pg_commands(pg_container, pg_commands, deadline=deadline)
    raw = await _native_command("docker", "exec", "--user=0", pg_container, "cat", marker, deadline=deadline)
    _require(raw == (digest + ":0\n").encode(), "activation_operator_native_command_failed")


async def _mc_run(action, *, token, objects, writable, mc_image, network, user_file,
                  password_file, containers, unknown, deadline):
    # Record the immutable container ID before starting any native bucket mutation.
    label = "org.2brain.graf.rehearsal=" + token
    unknown.add("mc_container")
    raw = await _native_command("docker", "create", "--pull=never", "--network", network,
        "--label", label, "--user", f"{os.geteuid()}:{os.getegid()}", "--entrypoint", "/bin/sh", "--env", "MC_CONFIG_DIR=/tmp/graf-mc",
        "--mount", f"type=bind,src={objects},dst=/backup" + ("" if writable else ",readonly"),
        "--mount", f"type=bind,src={user_file},dst=/run/secrets/user,readonly",
        "--mount", f"type=bind,src={password_file},dst=/run/secrets/password,readonly",
        mc_image, "-c", 'set -eu; umask 077; '
        'mc alias set rec http://rec-minio:9000 "$(cat /run/secrets/user)" '
        '"$(cat /run/secrets/password)" >/dev/null; ' + action, deadline=deadline)
    cid = raw.decode().strip()
    _require(re.fullmatch(r"[0-9a-f]{64}", cid), "activation_operator_container_create_unknown")
    containers.append(cid)
    unknown.remove("mc_container")
    await _native_command("docker", "start", "--attach", cid, deadline=deadline)
    state = json.loads(await _native_command("docker", "inspect", "--format", "{{json .State}}", cid, deadline=deadline))
    _require(state["Status"] == "exited" and state["ExitCode"] == 0
             and state["Running"] is False, "activation_operator_mirror_failed")


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
        return await _mc_run(action, token=token, objects=reference / "minio-objects",
            writable=False, mc_image=mc_image, network=network, user_file=user_file,
            password_file=password_file, containers=containers, unknown=unknown, deadline=deadline)

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
                    await _pg_run(pg_container, pg_staging, pg_commands, ["pg_restore", "--exit-on-error", "-U", "twobrain_rec",
                                  "-d", database, pg_staging + "/input-postgres.dump"], deadline=deadline)
                else:
                    await _pg_run(pg_container, pg_staging, pg_commands, ["psql", "-Xq",
                        "-v", "ON_ERROR_STOP=1", "-U", "twobrain_rec", "-d", database,
                        "-f", pg_staging + "/input-schema.sql"], deadline=deadline)
                await _pg_run(pg_container, pg_staging, pg_commands, ["sh", "-c",
                    'umask 077; exec psql "$@"', "sh", "-XqAt", "-v", "ON_ERROR_STOP=1",
                    "-U", "twobrain_rec", "-d", database, "-v", "expected_db=" + database,
                    "-v", "capture_dump=false", "-v", "staging=" + pg_staging,
                    "-f", pg_staging + "/capture.sql"], deadline=deadline)
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
                await _wait_pg_commands(pg_container, pg_commands, deadline=until)
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


# Actual configuration is private; only its aggregate digest leaves this process.
RUNTIME_FORMAT = """{"id":{{json .Id}},"image":{{json .Image}},"config":{{json .Config}},"host":{{json .HostConfig}},"mounts":{{json .Mounts}},"state":{"status":{{json .State.Status}},"running":{{json .State.Running}},"restarting":{{json .State.Restarting}},"paused":{{json .State.Paused}},"pid":{{json .State.Pid}},"exit":{{json .State.ExitCode}},"started":{{json .State.StartedAt}},"health":{{with index .State "Health"}}{{json .Status}}{{else}}null{{end}}},"restarts":{{json .RestartCount}}}"""
IMAGE_FORMAT = """{"id":{{json .Id}},"os":{{json .Os}},"architecture":{{json .Architecture}},"config":{"User":{{json .Config.User}},"Env":{{json .Config.Env}},"Labels":{{json .Config.Labels}},"Entrypoint":{{json .Config.Entrypoint}},"Cmd":{{json .Config.Cmd}},"WorkingDir":{{json .Config.WorkingDir}},"Healthcheck":{{json (index .Config "Healthcheck")}}}}"""
DOCKER_ENDPOINT = "unix:///var/run/docker.sock"
GRAF_SERVICES = WRITERS | {"rec-migrate", "rec-db-runtime-bootstrap"}
INSTALLATION_UID = 1001
INSTALLATION_GID = 1002


def _local_docker():
    _require(os.environ.get("DOCKER_HOST") == DOCKER_ENDPOINT
             and not any(name in os.environ for name in
                         ("DOCKER_CONTEXT", "DOCKER_CONFIG", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH")),
             "activation_operator_docker_endpoint")
    info = Path("/var/run/docker.sock").lstat()
    _require(stat.S_ISSOCK(info.st_mode) and info.st_uid == 0
             and not info.st_mode & stat.S_IWOTH, "activation_operator_docker_socket")
    return info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode


def _process_identity(pid, *, proc_root=Path("/proc")):
    """Host metadata only, for a PID from the fixed local Docker endpoint."""
    try:
        _require(type(pid) is int and pid > 0, "activation_operator_process_invalid")
        directory = proc_root / str(pid)

        def start():
            raw = (directory / "stat").read_text()
            prefix, suffix = raw.rsplit(") ", 1)
            _require(prefix.startswith(str(pid) + " (") and len(suffix.split()) > 19,
                     "activation_operator_process_invalid")
            result = int(suffix.split()[19])  # suffix starts at field3, after comm.
            _require(result > 0, "activation_operator_process_invalid")
            return result

        before = start()
        status = dict(line.split(":", 1) for line in (directory / "status").read_text().splitlines()
                      if ":" in line)
        _require([int(i) for i in status["Uid"].split()] == [100] * 4
                 and [int(i) for i in status["Gid"].split()] == [101] * 4,
                 "activation_operator_process_owner")
        for name in ("uid_map", "gid_map"):
            _require([int(i) for i in (directory / name).read_text().split()]
                     == [0, 0, 4294967295], "activation_operator_process_namespace")
        groups = tuple(sorted(int(i) for i in status["Groups"].split()))
        _require(len(set(groups)) == len(groups) and all(i >= 0 for i in groups),
                 "activation_operator_process_groups")
        _require(start() == before, "activation_operator_process_changed")
        return pid, before, groups
    except (OSError, KeyError, TypeError, ValueError):
        raise ActivationHold("activation_operator_process_unverified") from None


def _settings_file_identity(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _settings_no_acl(fd):
    _require(not any("acl" in name.lower() for name in os.listxattr(fd)),
             "activation_operator_secret_acl")


def _settings_source_ancestors(path):
    _require(path.is_absolute() and str(path) == str(path.resolve(strict=True)),
             "activation_operator_secret_path")
    identities = []
    for parent in path.parents:
        info = parent.lstat()
        fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            _require(_settings_file_identity(os.fstat(fd)) == _settings_file_identity(info),
                     "activation_operator_secret_ancestry")
            _settings_no_acl(fd)
        finally:
            os.close(fd)
        _require(stat.S_ISDIR(info.st_mode) and info.st_uid in {0, INSTALLATION_UID}
                 and not info.st_mode & stat.S_IWOTH, "activation_operator_secret_ancestry")
        if info.st_mode & stat.S_IWGRP:
            _require(info.st_gid == INSTALLATION_GID, "activation_operator_secret_ancestry")
            members = set(grp.getgrgid(info.st_gid).gr_mem)
            actual = {p.pw_uid for p in pwd.getpwall()
                      if p.pw_gid == info.st_gid or p.pw_name in members}
            _require(actual == {INSTALLATION_UID}, "activation_operator_secret_group_unconfirmed")
        identities.append((info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode))
    return identities


@contextmanager
def _settings_destination(root_fd, path, groups):
    """Walk only the already selected exact file bind, after the proc-root hop."""
    with ExitStack() as owned:
        directory = root_fd
        for component in path.parts[1:-1]:
            info = os.fstat(directory)
            _settings_no_acl(directory)
            shift = 6 if info.st_uid == 100 else 3 if info.st_gid in groups else 0
            _require(stat.S_ISDIR(info.st_mode) and (info.st_mode >> shift) & 1,
                     "activation_operator_secret_traversal")
            directory = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=directory)
            owned.callback(os.close, directory)
        info = os.fstat(directory)
        _settings_no_acl(directory)
        shift = 6 if info.st_uid == 100 else 3 if info.st_gid in groups else 0
        _require(stat.S_ISDIR(info.st_mode) and (info.st_mode >> shift) & 1,
                 "activation_operator_secret_traversal")
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        owned.callback(os.close, fd)
        yield fd


@contextmanager
def _sealed_settings_file(raw):
    """Linux RAM-only snapshot; ordinary Settings Path validators read these bytes."""
    fd = os.memfd_create("graf-operator-secret", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        remaining = memoryview(raw)
        while remaining:
            written = os.write(fd, remaining)
            _require(written > 0, "activation_operator_secret_snapshot")
            remaining = remaining[written:]
        seals = fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE
        fcntl.fcntl(fd, fcntl.F_ADD_SEALS, seals)
        _require(fcntl.fcntl(fd, fcntl.F_GET_SEALS) == seals
                 and os.pread(fd, 65537, 0) == raw, "activation_operator_secret_snapshot")
        yield Path(f"/proc/self/fd/{fd}")
    finally:
        os.close(fd)


@contextmanager
def _runtime_settings(row, *, root, process, proc_root=Path("/proc")):
    """Private Settings live only while the verified source/mount/snapshot FDs do."""
    from pydantic import AliasChoices
    from pydantic_settings import EnvSettingsSource
    from pydantic_settings.sources.utils import parse_env_vars

    from twobrain_rec_server.config import Settings

    try:
        _require("FORWARDED_ALLOW_IPS" not in os.environ, "activation_operator_host_environment")
        environment = {}
        for item in row["config"]["Env"]:
            key, separator, value = item.partition("=")
            _require(separator and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key)
                     and key.lower() not in {k.lower() for k in environment},
                     "activation_operator_environment_invalid")
            environment[key] = value
        for address in environment.get("FORWARDED_ALLOW_IPS", "127.0.0.1").split(","):
            ipaddress.ip_address(address.strip())
        _require(_process_identity(row["state"]["pid"], proc_root=proc_root) == process,
                 "activation_operator_process_changed")
        groups = {101, *process[2]}
        files, placeholders, logical_paths = {}, set(), {}
        with ExitStack() as owned:
            proc_path = proc_root / str(process[0]) / "root"
            root_fd = os.open(proc_path, os.O_RDONLY | os.O_DIRECTORY)
            owned.callback(os.close, root_fd)
            root_identity = os.fstat(root_fd)

            def mapped(field, value):
                path = Path(value)
                _require(path.is_absolute() and str(path) == value and ".." not in path.parts,
                         "activation_operator_secret_path")
                mounts = [m for m in row["mounts"] if path.is_relative_to(m["Destination"])]
                _require(len(mounts) == 1 and mounts[0]["Destination"] == value
                         and mounts[0]["Type"] == "bind" and mounts[0]["RW"] is False,
                         "activation_operator_secret_mount")
                source = Path(mounts[0]["Source"])
                _require(str(source) == mounts[0]["Source"] and ".." not in source.parts,
                         "activation_operator_secret_path")
                ancestors = _settings_source_ancestors(source)
                fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                owned.callback(os.close, fd)
                info = os.fstat(fd)
                _settings_no_acl(fd)
                _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                         and info.st_uid in {0, INSTALLATION_UID} and info.st_size <= 65536,
                         "activation_operator_secret_file")
                raw = os.pread(fd, 65537, 0)
                placeholder = source == root / "infra/secret-placeholders/disabled_optional_provider_secret"
                if placeholder:
                    _require(raw == b"" and stat.S_IMODE(info.st_mode) == 0o644,
                             "activation_operator_secret_placeholder")
                    placeholders.add(field)
                else:
                    _require(stat.S_IMODE(info.st_mode) in {0o600, 0o640}
                             and info.st_gid in groups and info.st_mode & stat.S_IRGRP
                             and raw.decode("utf-8").strip(), "activation_operator_secret_private")
                identity = _settings_file_identity(info)
                _require(len(raw) == info.st_size and _settings_file_identity(source.lstat()) == identity
                         and _settings_file_identity(os.fstat(fd)) == identity,
                         "activation_operator_secret_changed")
                destination = owned.enter_context(_settings_destination(root_fd, path, groups))
                _settings_no_acl(destination)
                _require(_settings_file_identity(os.fstat(destination)) == identity
                         and os.pread(destination, 65537, 0) == raw,
                         "activation_operator_secret_bind_mismatch")
                files[field] = (source, path, fd, destination, identity, raw, ancestors)
                logical_paths[field] = value
                return owned.enter_context(_sealed_settings_file(raw))

            class ActualEnvironment(EnvSettingsSource):
                def _load_env_vars(self):
                    return parse_env_vars(environment, self.case_sensitive, self.env_ignore_empty,
                                          self.env_parse_none_str)

                def __call__(self):
                    data = super().__call__()
                    for url_field, password_field in (
                        ("database_url", "postgres_password_file"),
                        ("prompt_optimization_database_url", "prompt_optimization_postgres_password_file"),
                    ):
                        value = data.get(url_field)
                        if url_field == "database_url" or (isinstance(value, str) and value.strip()):
                            _require(isinstance(value, str)
                                     and urlsplit(value).password == "__POSTGRES_PASSWORD__"
                                     and bool(data.get(password_field)),
                                     "activation_operator_database_secret_binding")
                    for name, field in Settings.model_fields.items():
                        if not name.endswith("_file"):
                            continue
                        alias = field.validation_alias
                        keys = [name, *(alias.choices if isinstance(alias, AliasChoices)
                                        else [alias] if isinstance(alias, str) else [])]
                        for key in keys:
                            if key in data and data[key] is not None:
                                data[key] = mapped(name, data[key])
                    return data

            class ActualSettings(Settings):
                @classmethod
                def settings_customise_sources(cls, settings_cls, **_sources):
                    return (ActualEnvironment(settings_cls),)

            settings = ActualSettings(_env_file=None)
            _require(settings.env == "production" and all(name in files for name in
                     ("postgres_password_file", "minio_access_key_file", "minio_secret_key_file")),
                     "activation_operator_settings_incomplete")
            allowed_empty = {
                "billing_yookassa_secret_file": not (settings.billing_checkout_enabled
                                                      or settings.billing_provider_observation_enabled),
                "billing_yookassa_webhook_secret_file": not (settings.billing_checkout_enabled
                                                              or settings.billing_provider_observation_enabled),
                "billing_referral_secret_file": not settings.billing_checkout_enabled,
                "google_calendar_client_secret_file": not settings.google_calendar_enabled,
                "product_analytics_posthog_project_key_file": not settings.product_analytics_posthog_enabled,
                "product_analytics_yandex_oauth_token_file": not settings.product_analytics_yandex_offline_enabled,
                "litellm_api_key_file": not (settings.outcome_generation_enabled
                                             or settings.prompt_optimization_enabled),
            }
            _require(all(allowed_empty.get(name) is True for name in placeholders),
                     "activation_operator_secret_placeholder")
            semantics = settings.model_dump(mode="json")
            semantics.update(logical_paths)  # Internal memfd numbers are not configuration identity.
            proof = _json_digest(dict(settings=semantics, files={
                name: dict(identity=values[4], content=hashlib.sha256(values[5]).hexdigest())
                for name, values in files.items()}))
            yield settings, proof
            for source, path, fd, destination, identity, raw, ancestors in files.values():
                _settings_no_acl(fd)
                _settings_no_acl(destination)
                _require(_settings_source_ancestors(source) == ancestors
                         and _settings_file_identity(source.lstat()) == identity
                         and all(_settings_file_identity(os.fstat(f)) == identity
                                 and os.pread(f, 65537, 0) == raw for f in (fd, destination)),
                         "activation_operator_secret_changed")
                with _settings_destination(root_fd, path, groups) as current:
                    _require(_settings_file_identity(os.fstat(current)) == identity
                             and os.pread(current, 65537, 0) == raw,
                             "activation_operator_secret_changed")
            current_root = proc_path.stat()
            _require((current_root.st_dev, current_root.st_ino)
                     == (root_identity.st_dev, root_identity.st_ino)
                     and _process_identity(process[0], proc_root=proc_root) == process,
                     "activation_operator_process_changed")
    except Exception:
        raise ActivationHold("activation_operator_settings_unverified") from None


def _policy_static(value):
    _require(isinstance(value, str) and '$' not in value.replace('$$', ''),
             'activation_operator_policy_interpolation')
    return value.replace('$$', '$')


def _policy_quantity(value, *, duration=False):
    """Exact bytes/nanoseconds only; Compose's existing units, no float rounding."""
    units = {'ns': 1, 'ms': 10**6, 's': 10**9, 'm': 60 * 10**9, 'h': 3600 * 10**9} if duration else {
        '': 1, 'b': 1, 'k': 1024, 'kb': 1024, 'm': 1024**2, 'mb': 1024**2,
        'g': 1024**3, 'gb': 1024**3}
    parts = re.findall(r'([0-9]+(?:\.[0-9]+)?)([a-z]*)', str(value).lower())
    _require(parts and ''.join(n + u for n, u in parts) == str(value).lower()
             and (duration or len(parts) == 1) and all(u in units for _, u in parts),
             'activation_operator_policy_quantity')
    result = sum(Decimal(n) * units[u] for n, u in parts)
    _require(result.is_finite() and result >= 0 and result == int(result),
             'activation_operator_policy_quantity')
    return int(result)


def _runtime_policy(rows, images, model, *, ids, root, postal_network, volumes=None):
    """Compare actual Engine config with trusted Compose/image, without host env."""
    try:
        _require(model['name'] == 'twobrain-rec' and set(model['services']) == set(SERVICE_NETWORKS)
                 and len(ids) == len(rows) and len(set(ids.values())) == len(ids)
                 and {r['id'] for r in rows} == set(ids.values()), 'activation_operator_policy_inventory')
        registry, mounts_proof, secret_group = {}, {}, None
        volumes = volumes or {}
        by_id = {v: k for k, v in ids.items()}

        def argv(value):
            if value is None:
                return None
            if isinstance(value, str):
                return shlex.split(_policy_static(value))
            _require(isinstance(value, list), 'activation_operator_policy_command')
            return [_policy_static(v) for v in value]

        def environment(values):
            result = {}
            for item in values or []:
                key, sep, value = item.partition('=')
                _require(sep and key not in result, 'activation_operator_policy_environment')
                result[key] = value
            return result

        def source_path(value):
            value = _policy_static(value)
            path = Path(value)
            return path if path.is_absolute() else root / 'infra' / path

        def protected(path, *, secret, volume=False):
            _require(str(path) == str(path.resolve(strict=True)), 'activation_operator_policy_path')
            ancestors = _settings_source_ancestors(path)
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                info = os.fstat(fd)
                _settings_no_acl(fd)
                _require((volume or info.st_uid in {0, INSTALLATION_UID})
                         and (stat.S_ISDIR(info.st_mode) if volume else
                              stat.S_ISREG(info.st_mode) or (not secret and stat.S_ISDIR(info.st_mode)))
                         and not info.st_mode & 0o022, 'activation_operator_policy_file')
                if secret:
                    placeholder = path == root / 'infra/secret-placeholders/disabled_optional_provider_secret'
                    _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                             and info.st_size <= 65536
                             and (info.st_size == 0 and stat.S_IMODE(info.st_mode) == 0o644 if placeholder
                                  else stat.S_IMODE(info.st_mode) in {0o600, 0o640}),
                             'activation_operator_policy_secret')
                identity = _settings_file_identity(info)
                _require(_settings_file_identity(path.lstat()) == identity,
                         'activation_operator_policy_file_changed')
                return dict(path=str(path), identity=identity, ancestors=ancestors)
            finally:
                os.close(fd)

        for row in rows:
            name = by_id[row['id']]
            spec, actual, host = model['services'][name], row['config'], row['host']
            image = images[row['image']]['config']
            entrypoint, command = argv(spec.get('entrypoint')), argv(spec.get('command')) or []
            # Engine merge: empty command inherits image Cmd only with empty entrypoint.
            if not entrypoint:
                command = command or image.get('Cmd') or []
                if entrypoint is None:
                    entrypoint = image.get('Entrypoint')
            _require(actual.get('User', '') == _policy_static(spec.get('user', image.get('User', '')))
                     and (actual.get('Entrypoint') or []) == (entrypoint or [])
                     and (actual.get('Cmd') or []) == command
                     and actual.get('WorkingDir', '') == _policy_static(spec.get('working_dir', image.get('WorkingDir', ''))),
                     'activation_operator_policy_command')
            default_env, actual_env = environment(image.get('Env')), environment(actual.get('Env'))
            overrides = spec.get('environment') or {}
            for key in ('PATH', 'PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP', 'PYTHONINSPECT',
                        'LD_PRELOAD', 'LD_LIBRARY_PATH', 'LD_AUDIT', 'BASH_ENV', 'ENV'):
                expected = _policy_static(overrides[key]) if key in overrides else default_env.get(key)
                _require(actual_env.get(key) == expected, 'activation_operator_policy_loader')

            restart = _policy_static(spec.get('restart', 'no'))
            match = re.fullmatch(r'(no|always|unless-stopped|on-failure)(?::([1-9][0-9]*))?', restart)
            _require(match and (match[2] is None or match[1] == 'on-failure')
                     and host.get('AutoRemove') is False
                     and host['RestartPolicy'] == dict(Name=match[1], MaximumRetryCount=int(match[2] or 0)),
                     'activation_operator_policy_restart')
            for key in ('Privileged', 'CapAdd', 'Devices', 'DeviceRequests', 'DeviceCgroupRules',
                        'VolumesFrom', 'Links', 'ExtraHosts', 'Dns', 'DnsOptions', 'DnsSearch',
                        'Sysctls', 'PublishAllPorts'):
                _require(not host.get(key), 'activation_operator_policy_privilege')
            _require(all(not host.get(k) for k in ('PidMode', 'UTSMode', 'UsernsMode'))
                     and host.get('IpcMode') == 'private'
                     and host.get('CgroupnsMode', 'private') == 'private'
                     and host['NetworkMode'] in {postal_network if n == 'postal-network' else n
                                                for n in SERVICE_NETWORKS[name]},
                     'activation_operator_policy_namespace')
            for source_key, actual_key, default in (('read_only', 'ReadonlyRootfs', False), ('init', 'Init', None)):
                expected = spec.get(source_key, default)
                _require(expected in (True, False, None) and host.get(actual_key, default) is expected,
                         'activation_operator_policy_restriction')
            for source_key, actual_key in (('cap_drop', 'CapDrop'), ('security_opt', 'SecurityOpt')):
                expected, observed = spec.get(source_key) or [], host.get(actual_key) or []
                _require(len(set(expected)) == len(expected) and len(set(observed)) == len(observed)
                         and set(expected) == set(observed), 'activation_operator_policy_restriction')
            declared_groups, groups = spec.get('group_add') or [], host.get('GroupAdd') or []
            if declared_groups:
                _require(declared_groups == ['${TWOBRAIN_RUNTIME_SECRET_GID:-1001}']
                         and len(groups) == 1 and re.fullmatch(r'[1-9][0-9]*', groups[0]),
                         'activation_operator_policy_group')
                _require(secret_group is None or secret_group == groups[0], 'activation_operator_policy_group')
                secret_group = groups[0]
            else:
                _require(not groups, 'activation_operator_policy_group')
            limits = spec.get('deploy', {}).get('resources', {}).get('limits', {})
            for top, deploy, engine in (('mem_limit', 'memory', 'Memory'), ('cpus', 'cpus', 'NanoCpus'),
                                        ('pids_limit', 'pids', 'PidsLimit')):
                def quantity(value, top=top):
                    if top == 'mem_limit':
                        return _policy_quantity(value)
                    number = Decimal(str(value)) * (10**9 if top == 'cpus' else 1)
                    _require(number.is_finite() and number >= 0 and number == int(number),
                             'activation_operator_policy_quantity')
                    return int(number)
                values = [quantity(v) for v in (spec.get(top), limits.get(deploy)) if v is not None]
                observed = host.get(engine)
                _require((values and len(set(values)) == 1 and type(observed) is int and observed == values[0])
                         or (not values and observed in (None, 0, -1)), 'activation_operator_policy_limit')

            ports = {}
            for port in spec.get('ports') or []:
                _require(set(port) <= {'host_ip', 'published', 'target', 'protocol', 'mode'}
                         and port.get('mode', 'ingress') == 'ingress'
                         and port['host_ip'] == '127.0.0.1' and str(port['published']).isdigit()
                         and 0 < int(port['published']) < 65536 and 0 < int(port['target']) < 65536
                         and port.get('protocol', 'tcp') == 'tcp', 'activation_operator_policy_port')
                key = str(port['target']) + '/tcp'
                ports.setdefault(key, []).append(dict(HostIp=port['host_ip'], HostPort=str(port['published'])))
            _require((host.get('PortBindings') or {}) == ports, 'activation_operator_policy_port')
            logging = spec['logging']
            _require(logging == dict(driver='json-file', options={'max-size': '10m', 'max-file': '5'})
                     and host['LogConfig'] == dict(Type=logging['driver'], Config=logging['options']),
                     'activation_operator_policy_logging')

            health = dict(image.get('Healthcheck') or {})
            declared = spec.get('healthcheck') or {}
            _require(set(declared) <= {'test', 'disable', 'interval', 'timeout', 'start_period', 'start_interval', 'retries'},
                     'activation_operator_policy_health')
            for key, target in (('test', 'Test'), ('interval', 'Interval'), ('timeout', 'Timeout'),
                                ('start_period', 'StartPeriod'), ('start_interval', 'StartInterval'), ('retries', 'Retries')):
                if key in declared:
                    value = declared[key]
                    if key == 'test':
                        value = argv(value)
                    elif key == 'retries':
                        _require(type(value) is int and value >= 0, 'activation_operator_policy_health')
                    else:
                        value = _policy_quantity(value, duration=True)
                    if value:
                        health[target] = value
            if declared.get('disable') is True:
                health = {'Test': ['NONE']}
            observed_health = actual.get('Healthcheck') or {}
            fields = {'Test', 'Interval', 'Timeout', 'StartPeriod', 'StartInterval', 'Retries'}
            _require(set(health) <= fields and set(observed_health) <= fields
                     and all(health.get(k, [] if k == 'Test' else 0)
                             == observed_health.get(k, [] if k == 'Test' else 0) for k in fields),
                     'activation_operator_policy_health')

            tmpfs = {}
            for value in spec.get('tmpfs') or []:
                target, sep, options = _policy_static(value).partition(':')
                _require(target.startswith('/') and target not in tmpfs, 'activation_operator_policy_tmpfs')
                tmpfs[target] = options if sep else ''
            _require((host.get('Tmpfs') or {}) == tmpfs, 'activation_operator_policy_tmpfs')
            expected_mounts = {}
            for volume in spec.get('volumes') or []:
                _require(set(volume) <= {'type', 'source', 'target', 'read_only', 'bind', 'volume'},
                         'activation_operator_policy_mount')
                kind, target = volume['type'], _policy_static(volume['target'])
                _require(target.startswith('/') and target not in expected_mounts,
                         'activation_operator_policy_mount')
                options = volume.get(kind) or {}
                _require((kind == 'bind' and set(options) <= {'create_host_path', 'propagation'}
                          and options.get('create_host_path', True) in (True, False)
                          and options.get('propagation', 'rprivate') == 'rprivate')
                         or (kind == 'volume' and not options), 'activation_operator_policy_mount_options')
                source = volume['source']
                if kind == 'bind':
                    source = str(source_path(source))
                    mounts_proof[source] = protected(Path(source), secret=False)
                else:
                    _require(kind == 'volume', 'activation_operator_policy_mount')
                    declaration = model['volumes'][source]
                    _require(set(declaration) == {'name'}, 'activation_operator_policy_volume')
                    source = _policy_static(declaration['name'])
                expected_mounts[target] = (kind, source, not volume.get('read_only', False))
            for secret in spec.get('secrets') or []:
                _require(set(secret) <= {'source', 'target', 'uid', 'gid', 'mode'}, 'activation_operator_policy_secret')
                logical = secret['source']
                target = '/run/secrets/' + secret.get('target', logical)
                _require(target not in expected_mounts and Path(target).parent == Path('/run/secrets'),
                         'activation_operator_policy_secret')
                matched = [m for m in row['mounts'] if m['Destination'] == target]
                _require(len(matched) == 1, 'activation_operator_policy_secret')
                source = matched[0]['Source']
                declaration = model['secrets'][logical]
                _require(set(declaration) <= {'file', 'name'}
                         and declaration.get('name', 'twobrain-rec_' + logical) == 'twobrain-rec_' + logical,
                         'activation_operator_policy_secret')
                template = declaration['file']
                if '$' in template:
                    _require(re.fullmatch(r'\$\{[A-Za-z_][A-Za-z0-9_]*:-[^${}]+\}', template),
                             'activation_operator_policy_secret_template')
                else:
                    _require(source == str(source_path(template)), 'activation_operator_policy_secret_source')
                proof = protected(Path(source), secret=True)
                _require(logical not in registry or registry[logical] == proof,
                         'activation_operator_policy_secret_source')
                registry[logical] = proof
                expected_mounts[target] = ('bind', source, False)
            _require(not (set(expected_mounts) & set(tmpfs)), 'activation_operator_policy_mount')
            seen = set()
            for mount in row['mounts']:
                target, kind = mount['Destination'], mount['Type']
                _require(target not in seen and set(mount) <= {
                    'Type', 'Name', 'Source', 'Destination', 'Driver', 'Mode', 'RW', 'Propagation'},
                    'activation_operator_policy_mount')
                seen.add(target)
                if kind == 'tmpfs':
                    _require(target in tmpfs and not mount.get('Source') and not mount.get('Name')
                             and mount.get('Mode', '') in {'', tmpfs[target]}, 'activation_operator_policy_tmpfs')
                    continue
                _require(target in expected_mounts, 'activation_operator_policy_mount')
                expected_kind, source, writable = expected_mounts[target]
                _require(kind == expected_kind and mount['RW'] is writable
                         and mount.get('Mode', '') in {'', 'rw' if writable else 'ro'}
                         and mount.get('Propagation', '') in ({'', 'rprivate'} if kind == 'bind' else {''}),
                         'activation_operator_policy_mount')
                _require(mount['Source'] == source if kind == 'bind' else
                         mount['Name'] == source and mount.get('Driver') == 'local',
                         'activation_operator_policy_mount_source')
                if kind == 'volume':
                    metadata = volumes[source]
                    _require(set(metadata) == {'name', 'driver', 'scope', 'options', 'mountpoint'}
                             and metadata['name'] == source and metadata['driver'] == 'local'
                             and metadata['scope'] == 'local' and not metadata['options']
                             and metadata['mountpoint'] == mount['Source'], 'activation_operator_policy_volume')
                    mounts_proof[mount['Source']] = protected(Path(mount['Source']), secret=False, volume=True)
            _require(set(expected_mounts) <= seen, 'activation_operator_policy_mount')
            # Engine Mounts omits volume subpath/driver options: check their request too.
            for request in host.get('Mounts') or []:
                _require(set(request) <= {'Type', 'Source', 'Target', 'ReadOnly', 'Consistency', 'BindOptions', 'VolumeOptions'}
                         and request['Target'] in expected_mounts
                         and not request.get('Consistency')
                         and not request.get('VolumeOptions')
                         and set(request.get('BindOptions') or {}) <= {'CreateMountpoint', 'Propagation'}
                         and (request.get('BindOptions') or {}).get('Propagation', 'rprivate') == 'rprivate'
                         and (request.get('BindOptions') or {}).get('CreateMountpoint', True) in (True, False),
                         'activation_operator_policy_mount_options')
        return _json_digest(dict(model=model, secrets=registry, paths=mounts_proof, group=secret_group, volumes=volumes))
    except Exception:
        raise ActivationHold('activation_operator_policy_unverified') from None


async def _runtime_preflight(*, root, snapshot, source, deadline):
    """Bind actual runtime before further gates; never write ready or stop product."""
    _require(time.monotonic() < deadline and re.fullmatch(r"[a-f0-9]{40}", source),
             "activation_operator_runtime_input")
    socket = _local_docker()
    helper = [sys.executable, "-I", "-B", str(snapshot / "infra/scripts/release-images.py"),
              "current-override"]

    async def release():
        raw = await _command(helper, deadline=deadline, cwd=root)
        path = raw.decode().strip()
        _require(path and "\n" not in path and Path(path).is_absolute(),
                 "activation_operator_release_missing")
        data = Path(path).read_bytes()
        parsed = _object(data)
        _require(set(parsed) == {"services"}, "activation_operator_release_invalid")
        services = parsed["services"]
        _require(isinstance(services, dict) and services, "activation_operator_release_invalid")
        for name, row in services.items():
            _require(name in SERVICE_NETWORKS and isinstance(row, dict)
                     and set(row) == {"image", "pull_policy"} and row["pull_policy"] == "never"
                     and isinstance(row["image"], str)
                     and re.fullmatch(r"sha256:[a-f0-9]{64}", row["image"]),
                     "activation_operator_release_invalid")
        return path, data, services

    async def head():
        actual = await _command(["/usr/bin/git", "-c", "core.fsmonitor=false", "-c",
                                 "core.hooksPath=/dev/null", "-c", f"safe.directory={root}",
                                 "-C", str(root), "rev-parse", "HEAD"], deadline=deadline)
        _require(actual.decode().strip() == source, "activation_operator_source_changed")

    async def compose_model():
        raw = await _command([
            "docker", "compose", "--env-file", "/dev/null", "--profile", "operations",
            "-f", str(snapshot / "infra/docker-compose.yml"), "config", "--no-interpolate",
            "--no-env-resolution", "--no-path-resolution", "--format", "json",
        ], deadline=deadline, cwd=snapshot / "infra")
        _require(len(raw) <= 2 * 1024**2, "activation_operator_policy_size")
        return _object(raw)

    await head()
    model = await compose_model()
    pinned_path, pinned_bytes, pinned = await release()
    daemon = json.loads(await _command(
        ["docker", "info", "--format",
         '{"os":{{json .OSType}},"security":{{json .SecurityOptions}},"architecture":{{json .Architecture}}}'],
        deadline=deadline))
    _require(daemon["os"] == "linux" and isinstance(daemon["security"], list)
             and all(isinstance(s, str) and "rootless" not in s and "userns" not in s
                     for s in daemon["security"]), "activation_operator_docker_namespace")
    architecture = {"x86_64": "amd64", "aarch64": "arm64"}.get(daemon["architecture"], daemon["architecture"])
    _require(architecture in {"amd64", "arm64"}, "activation_operator_image_platform")
    rows, networks = await _inventory("twobrain-rec", deadline)
    api = [r for r in rows if r["service"] == "rec-api"]
    _require(len(api) == 1, "activation_operator_required_missing")
    postal = set(api[0]["networks"]) - {PRIVATE}
    _require(len(postal) == 1, "activation_operator_membership_invalid")
    postal = postal.pop()
    ids = _validate_inventory(rows, networks, project="twobrain-rec", postal_network=postal, stopped=False)

    async def inspect():
        raw = await _command(["docker", "inspect", "--format", RUNTIME_FORMAT, *sorted(ids.values())], deadline=deadline)
        data = [json.loads(line) for line in raw.splitlines()]
        _require(len(data) == len(ids) and {r["id"] for r in data} == set(ids.values()),
                 "activation_operator_runtime_incomplete")
        return sorted(data, key=lambda r: r["id"])

    async def postal_identity():
        return json.loads(await _command(
            ["docker", "network", "inspect", "--format", '{"id":{{json .Id}},"name":{{json .Name}}}', postal],
            deadline=deadline))

    actual = await inspect()
    postal_info = await postal_identity()
    _require(postal_info["name"] == postal and re.fullmatch(r"[a-f0-9]{64}", postal_info["id"]),
             "activation_operator_network_invalid")
    image_ids = sorted({r["image"] for r in actual})
    image_data = [json.loads(line) for line in (await _command(
        ["docker", "image", "inspect", "--format", IMAGE_FORMAT, *image_ids], deadline=deadline)).splitlines()]
    _require(len(image_data) == len(image_ids) and {r["id"] for r in image_data} == set(image_ids),
             "activation_operator_image_incomplete")
    images = {r["id"]: r for r in image_data}
    processes = {}
    by_id = {v: k for k, v in ids.items()}
    inventory_by_id = {r["id"]: r for r in rows}
    for row in actual:
        service = by_id[row["id"]]
        image = images[row["image"]]
        _require(service in pinned and row["image"] == pinned[service]["image"]
                 and image["os"] == "linux" and image["architecture"] == architecture,
                 "activation_operator_image_mismatch")
        state, config = row["state"], row["config"]
        expected_state = inventory_by_id[row["id"]]["state"]
        _require(all(state[k] == v and type(state[k]) is type(v) for k, v in expected_state.items())
                 and type(row["restarts"]) is int and row["restarts"] >= 0
                 and re.fullmatch(r"[a-f0-9]{64}", config["Labels"]["com.docker.compose.config-hash"])
                 and isinstance(row["host"], dict) and isinstance(row["mounts"], list),
                 "activation_operator_runtime_changed")
        if service in REQUIRED_WRITERS:
            _require(state["running"] is True, "activation_operator_required_stopped")
        if state["running"]:
            _require(state["health"] == "healthy" if service in INFRASTRUCTURE | {"rec-api"}
                     else state["health"] in {None, "healthy"}, "activation_operator_runtime_unhealthy")
            _timestamp(state["started"])
        if service in GRAF_SERVICES:
            _require(config["User"] == image["config"]["User"] == "twobrain"
                     and row["host"].get("UsernsMode") == ""
                     and image["config"]["Labels"].get("org.2brain.graf.dev.source-sha") == source,
                     "activation_operator_runtime_source")
            for cfg in (config, image["config"]):
                _require(isinstance(cfg["Env"], list)
                         and [v for v in cfg["Env"] if v.startswith("GRAF_DEV_SOURCE_SHA=")]
                         == ["GRAF_DEV_SOURCE_SHA=" + source], "activation_operator_runtime_source")
            if state["running"] and service in WRITERS:
                processes[row["id"]] = _process_identity(state["pid"])
        elif service == "rec-minio-init":
            _require(config["User"] == image["config"]["User"], "activation_operator_initializer_user")
    async def volume_metadata():
        names = sorted({m["Name"] for row in actual for m in row["mounts"] if m["Type"] == "volume"})
        if not names:
            return {}
        raw = await _command([
            "docker", "volume", "inspect", "--format",
            '{"name":{{json .Name}},"driver":{{json .Driver}},"scope":{{json .Scope}},'
            '"options":{{json .Options}},"mountpoint":{{json .Mountpoint}}}', *names,
        ], deadline=deadline)
        records = [json.loads(line) for line in raw.splitlines()]
        _require(len(records) == len(names) and {r["name"] for r in records} == set(names),
                 "activation_operator_volume_incomplete")
        return {r["name"]: r for r in records}

    policy = _runtime_policy(actual, images, model, ids=ids, root=root, postal_network=postal,
                             volumes=await volume_metadata())
    with ExitStack() as actual_settings:
        settings_proofs = {}
        for row in actual:
            if row["id"] in processes:
                _, proof = actual_settings.enter_context(_runtime_settings(
                    row, root=root, process=processes[row["id"]]))
                settings_proofs[row["id"]] = proof
        _require(await inspect() == actual, "activation_operator_runtime_changed")
        for row in actual:
            if row["id"] in processes:
                _require(_process_identity(row["state"]["pid"]) == processes[row["id"]],
                         "activation_operator_process_changed")
        _require(await _inventory("twobrain-rec", deadline) == (rows, networks)
                 and await postal_identity() == postal_info, "activation_operator_runtime_changed")
        path, data, _ = await release()
        _require(path == pinned_path and data == pinned_bytes, "activation_operator_release_changed")
        await head()
        _require(_runtime_policy(actual, images, await compose_model(), ids=ids, root=root,
                                 postal_network=postal, volumes=await volume_metadata()) == policy,
                 "activation_operator_policy_changed")
        _require(_local_docker() == socket and time.monotonic() < deadline,
                 "activation_operator_runtime_changed")
        return dict(runtime="verified", source_sha=source, container_count=len(ids),
                    runtime_sha256=_json_digest(dict(containers=actual, networks=networks,
                                                    postal=postal_info, processes=processes,
                                                    settings=settings_proofs, policy=policy)))


def _runtime_main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Read-only runtime binding, no readiness writer.")
    parser.add_argument("--runtime-preflight", action="store_true", required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args(argv)
    try:
        _require(sys.flags.isolated and sys.platform == "linux" and os.geteuid() == 0
                 and sys.version_info[:2] == (3, 13), "activation_operator_installed_runtime_required")
        prefix = Path(sys.prefix).resolve(strict=True)
        _require(Path(__file__).resolve().is_relative_to(prefix), "activation_operator_package_unpinned")
        result = asyncio.run(_runtime_preflight(
            root=Path("/opt/projects/2brain-rec"), snapshot=prefix.parent / "source",
            source=args.source_sha, deadline=time.monotonic() + 30))
    except Exception:
        print(json.dumps(dict(runtime="unverified", reason="activation_operator_runtime_unverified")))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0  # Only runtime bindings; the bootstrap still holds full admission.


if __name__ == "__main__":
    raise SystemExit(_runtime_main())
