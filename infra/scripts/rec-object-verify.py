#!/usr/bin/env python3
"""Private backup snapshot and full readback of a disposable MinIO bucket."""

import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time
import unicodedata


def require(condition):
    if not condition:
        raise ValueError("object_restore_contract_mismatch")


def remaining(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError("object_restore_timeout")


def object_key(key):
    require(isinstance(key, str) and 0 < len(key.encode("utf-8")) <= 1024
            and "\0" not in key and unicodedata.normalize("NFC", key) == key
            and all(part not in {"", ".", ".."} for part in key.split("/")))
    return key


def identity(info):
    return [info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def private(info, directory):
    require(info.st_uid == os.geteuid()
            and (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            and stat.S_IMODE(info.st_mode) == (0o700 if directory else 0o600)
            and (directory or info.st_nlink == 1))


def file_manifest(root, *, deadline):
    root = Path(root)
    require(root.is_absolute() and root.resolve(strict=True) == root)

    def visit(fd, prefix, *, read):
        remaining(deadline)
        before = os.fstat(fd)
        private(before, True)
        tree, files = {prefix: identity(before)}, []
        for name in sorted(os.listdir(fd)):
            key = object_key(prefix + name)
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            directory = stat.S_ISDIR(info.st_mode)
            private(info, directory)
            child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                            | (os.O_DIRECTORY if directory else 0), dir_fd=fd)
            try:
                require(identity(os.fstat(child)) == identity(info))
                if directory:
                    children, entries = visit(child, key + "/", read=read)
                    tree.update(children)
                    files.extend(entries)
                else:
                    tree[key] = identity(info)
                    if read:
                        digest, size = hashlib.sha256(), 0
                        while chunk := os.read(child, 1024 * 1024):
                            remaining(deadline)
                            size += len(chunk)
                            require(size <= info.st_size)
                            digest.update(chunk)
                        require(size == info.st_size)
                        files.append([key, size, digest.hexdigest()])
                require(identity(os.fstat(child)) == identity(info)
                        and identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) == identity(info))
            finally:
                os.close(child)
        require(identity(os.fstat(fd)) == identity(before))
        return tree, files

    # Open each component relative to a held parent without following links.
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in root.parts[1:]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        tree, files = visit(fd, "", read=True)
        current, _ = visit(fd, "", read=False)
        require(tree == current and identity(root.lstat()) == tree[""]
                and root.resolve(strict=True) == root)
        remaining(deadline)
        return {"version": 1, "files": sorted(files), "tree": tree}
    finally:
        os.close(fd)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def read_manifest(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        private(before, False)
        with os.fdopen(fd, "r", closefd=False) as stream:
            result = json.load(stream, object_pairs_hook=unique_object)
        require(identity(os.fstat(fd)) == identity(before))
    finally:
        os.close(fd)
    require(isinstance(result, dict) and set(result) == {"version", "files", "tree"}
            and type(result["version"]) is int and result["version"] == 1
            and isinstance(result["files"], list) and isinstance(result["tree"], dict))
    keys = []
    for row in result["files"]:
        require(isinstance(row, list) and len(row) == 3)
        key, size, digest = row
        object_key(key)
        require(type(size) is int and size >= 0 and isinstance(digest, str)
                and re.fullmatch(r"[0-9a-f]{64}", digest))
        keys.append(key)
    require(keys == sorted(set(keys)))
    return result


def verify(root, expected, client, bucket, *, deadline):
    from minio.error import S3Error

    source = file_manifest(root, deadline=deadline)
    # Bind mounts may report different device IDs; the host checks its own full identity.
    require(source["files"] == expected["files"])

    def configuration():
        remaining(deadline)
        require(client.get_bucket_versioning(bucket).status is None)
        try:
            require(client.get_bucket_lifecycle(bucket) is None)
        except S3Error as error:
            require(error.code == "NoSuchLifecycleConfiguration")
        try:
            client.get_object_lock_config(bucket)
        except S3Error as error:
            require(error.code == "ObjectLockConfigurationNotFoundError")
        else:
            require(False)
        remaining(deadline)

    def metadata(obj):
        remaining(deadline)
        key = object_key(obj.object_name)
        require(type(obj.size) is int and obj.size >= 0
                and isinstance(obj.etag, str) and bool(obj.etag)
                and obj.last_modified is not None and obj.last_modified.utcoffset() is not None
                and getattr(obj, "version_id", None) is None and not getattr(obj, "is_dir", False))
        return key, obj.size, obj.etag, obj.last_modified

    def listing():
        rows = sorted(metadata(obj) for obj in client.list_objects(bucket, recursive=True))
        require(len(rows) == len({row[0] for row in rows}))
        remaining(deadline)
        return rows

    configuration()
    before = listing()
    require([(key, size) for key, size, _, _ in before]
            == [(key, size) for key, size, _ in expected["files"]])
    rows = []
    for entry in before:
        key, expected_size, _, _ = entry
        initial = metadata(client.stat_object(bucket, key))
        # List timestamps have milliseconds; HEAD uses HTTP whole seconds.
        require(initial[:3] == entry[:3])
        response = client.get_object(bucket, key)
        try:
            digest, size = hashlib.sha256(), 0
            for chunk in response.stream(1024 * 1024, decode_content=False):
                remaining(deadline)
                require(isinstance(chunk, bytes))
                size += len(chunk)
                require(size <= expected_size)
                digest.update(chunk)
            require(size == expected_size)
            rows.append([key, size, digest.hexdigest()])
        finally:
            try:
                response.close()
            finally:
                response.release_conn()
        require(metadata(client.stat_object(bucket, key)) == initial)
    require(rows == expected["files"] and listing() == before)
    configuration()
    require(file_manifest(root, deadline=deadline) == source)
    remaining(deadline)
    return rows


def interrupted(number, frame):
    # selectors used by subprocess/HTTP may swallow InterruptedError as a syscall retry.
    raise RuntimeError("object_restore_interrupted")


def cleanup_budget(manifest, notify_fd=None, *, expected_parent):
    """Persist one host-monotonic deadline so supervisor loss cannot renew it."""
    manifest = Path(manifest)
    require(manifest.parent.resolve(strict=True) == manifest.parent and not manifest.is_symlink())
    parent = os.open(manifest.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        private(os.fstat(parent), True)
        info = os.fstat(parent)
        require((info.st_dev, info.st_ino, info.st_uid) == expected_parent)
        name = manifest.name + ".deadline"
        try:
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        except FileExistsError:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            with os.fdopen(fd) as stream:
                before = os.fstat(stream.fileno())
                private(before, False)
                require(0 < before.st_size <= 128)
                deadline = float(stream.read(128))
                require(identity(os.fstat(stream.fileno())) == identity(before))
        else:
            deadline = time.monotonic() + 60
            with os.fdopen(fd, "w") as stream:
                stream.write(str(deadline))
                stream.flush()
                os.fsync(stream.fileno())
        require(math.isfinite(deadline) and 0 < deadline <= time.monotonic() + 60)
    finally:
        os.close(parent)
    notified = True
    if notify_fd is not None:
        require(stat.S_ISFIFO(os.fstat(int(notify_fd)).st_mode))
        try:
            os.write(int(notify_fd), (str(deadline) + "\n").encode("ascii"))
        except BrokenPipeError:
            notified = False
    return deadline, notified


def container_readback(root, manifest, bucket, image, user, password, *, deadline):
    """Own one read-only SDK container; publish cleanup proof only after removal."""
    require(re.fullmatch(r"twobrain-rec-restore-rehearsal-[0-9a-f]{32}", bucket)
            and re.fullmatch(r"sha256:[0-9a-f]{64}", image))
    manifest = Path(manifest)
    private(manifest.parent.stat(), True)
    require(manifest.is_absolute() and manifest.resolve(strict=True) == manifest)
    marker = Path(str(manifest) + ".cleanup")
    require(not marker.exists() and not marker.is_symlink())
    manifest_identity = identity(manifest.lstat())
    parent_identity = identity(manifest.parent.lstat())[:5]
    expected = read_manifest(manifest)
    name = "graf-rec-readback-" + bucket.rsplit("-", 1)[1]
    label = "org.2brain.graf.restore-readback"
    attempted = cli_unknown = stopped = False

    def command(args, until):
        nonlocal cli_unknown
        remaining(until)
        child = subprocess.Popen(["docker", *args], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            output, _ = child.communicate(timeout=max(0.001, until - time.monotonic()))
        except BaseException:
            cli_unknown = True
            try:
                child.kill()
            except ProcessLookupError:
                pass
            try:
                child.communicate(timeout=max(0.001, min(3, until - time.monotonic())))
                cli_unknown = False
            except subprocess.TimeoutExpired:
                pass
            raise
        require(child.returncode == 0)
        remaining(until)
        return output.decode("utf-8").strip()

    def owned(until):
        rows = json.loads(command(["container", "inspect", name], until))
        require(isinstance(rows, list) and len(rows) == 1)
        row = rows[0]
        require(row["Name"] == "/" + name and row["Image"] == image
                and row["Config"]["Labels"].get(label) == bucket
                and re.fullmatch(r"[0-9a-f]{64}", row["Id"]))
        return row

    try:
        require(file_manifest(root, deadline=deadline) == expected)
        mounts = []
        for source, target in ((root, "/source"), (manifest, "/manifest"),
                               (Path(__file__).resolve(), "/checker.py"),
                               (user, "/run/secrets/user"), (password, "/run/secrets/password")):
            source = Path(source)
            require(source.is_absolute() and source.resolve(strict=True) == source and "," not in str(source))
            if target.startswith("/run/secrets/"):
                fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                try:
                    info = os.fstat(fd)
                    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size > 0)
                finally:
                    os.close(fd)
            mounts.extend(["--mount", f"type=bind,source={source},destination={target},readonly"])
        attempted = True
        created = command(["create", "--pull", "never", "--name", name, "--label", f"{label}={bucket}",
                           "--network", "twobrain-rec-private", "--user", f"{os.geteuid()}:{os.getegid()}",
                           "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                           *mounts, "--entrypoint", "python", image,
                           "/checker.py", "verify", "/source", "/manifest", bucket], deadline)
        row = owned(deadline)
        require(created == row["Id"] and not row["State"]["Running"])
        output = command(["start", "--attach", row["Id"]], deadline)
        final = owned(deadline)
        require(final["Id"] == row["Id"] and final["State"]["Running"] is False
                and final["State"]["Status"] == "exited" and final["State"]["ExitCode"] == 0
                and output == "object_restore_result=pass")
        require(read_manifest(manifest) == expected)
    finally:
        # Finish our cleanup despite repeated stop signals, then reject the operation.
        signal.alarm(0)
        def remember_stop(number, frame):
            nonlocal stopped
            stopped = True
        for number in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
            signal.signal(number, remember_stop)
        require(identity(manifest.parent.lstat())[:5] == parent_identity)
        cleanup_deadline, notified = cleanup_budget(
            manifest, os.environ.get("GRAF_RESTORE_CLEANUP_FD"),
            expected_parent=(parent_identity[0], parent_identity[1], parent_identity[3]))
        stopped = stopped or not notified
        signal.setitimer(signal.ITIMER_REAL, max(0.001, cleanup_deadline - time.monotonic()))
        try:
            require(not cli_unknown)
            if attempted:
                target = owned(cleanup_deadline)
                command(["rm", "--force", target["Id"]], cleanup_deadline)
                require(command(["container", "ls", "--all", "--quiet", "--no-trunc",
                                 "--filter", f"name=^/{name}$"], cleanup_deadline) == "")
            require(identity(manifest.lstat()) == manifest_identity
                    and manifest.resolve(strict=True) == manifest)
            parent_fd = os.open(manifest.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                require(identity(os.fstat(parent_fd))[:5] == parent_identity)
                fd = os.open(marker.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=parent_fd)
                with os.fdopen(fd, "w") as stream:
                    stream.write("container_cleanup=pass\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                require(identity(manifest.parent.lstat())[:5] == parent_identity)
            finally:
                os.close(parent_fd)
            remaining(cleanup_deadline)
        finally:
            signal.alarm(0)
            for number in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
                signal.signal(number, interrupted)
    require(not stopped)
    require(file_manifest(root, deadline=deadline) == expected
            and read_manifest(manifest) == expected
            and identity(manifest.lstat()) == manifest_identity
            and identity(manifest.parent.lstat())[:5] == parent_identity
            and manifest.resolve(strict=True) == manifest)


def main(argv):
    deadline = time.monotonic() + 600
    pool = None
    for number in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(number, interrupted)
    signal.signal(signal.SIGALRM, interrupted)
    signal.alarm(600)
    try:
        require(len(argv) >= 3)
        action, root, manifest = argv[:3]
        if action == "snapshot":
            require(len(argv) == 3)
            value = file_manifest(root, deadline=deadline)
            fd = os.open(manifest, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "w") as stream:
                json.dump(value, stream, ensure_ascii=True, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            require(read_manifest(manifest) == value)
        elif action == "source":
            require(len(argv) == 3)
            require(file_manifest(root, deadline=deadline) == read_manifest(manifest))
        elif action == "container":
            require(len(argv) == 7)
            container_readback(root, manifest, *argv[3:], deadline=deadline)
        else:
            require(action == "verify" and len(argv) == 4
                    and re.fullmatch(r"twobrain-rec-restore-rehearsal-[0-9a-f]{32}", argv[3]))
            import minio
            import urllib3

            require(minio.__version__ == "7.2.20" and urllib3.__version__ == "2.7.0")
            pool = urllib3.PoolManager(timeout=urllib3.Timeout(connect=5, read=15), retries=False)
            # Pin the local MinIO region: SDK region-cache HEAD redirects must not retry.
            client = minio.Minio("rec-minio:9000", secure=False, region="us-east-1",
                           access_key=Path("/run/secrets/user").read_text().strip(),
                           secret_key=Path("/run/secrets/password").read_text().strip(), http_client=pool)
            value = read_manifest(manifest)
            verify(root, value, client, argv[3], deadline=deadline)
            require(read_manifest(manifest) == value)
        if pool is not None:
            pool.clear()
            pool = None
        remaining(deadline)
        print("object_restore_result=pass")
        return 0
    except Exception:
        # SDK exceptions can include private keys; only the fixed reason leaves this process.
        print("object_restore_result=failed\nreason=object_restore_unverified")
        return 1
    finally:
        signal.alarm(0)
        if pool is not None:
            try:
                pool.clear()
            except Exception:
                pass  # The failure path already rejects this process; never expose SDK text.


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
