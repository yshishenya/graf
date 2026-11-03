"""Compare complete synthetic backup bytes; no production service is used."""

import gzip
import importlib.util
import io
import os
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from minio.error import S3Error
from urllib3.response import HTTPResponse

REPO = Path(__file__).parents[4]


@pytest.fixture
def checker():
    spec = importlib.util.spec_from_file_location("rec_object_verify", REPO / "infra/scripts/rec-object-verify.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "objects"
    root.mkdir(mode=0o700)
    (root / "папка с пробелом").mkdir(mode=0o700)
    for key, data in {"папка с пробелом/запись.bin": b"synthetic\x00bytes", "empty": b""}.items():
        (root / key).write_bytes(data)
        (root / key).chmod(0o600)
    return root


class Response:
    def __init__(self, data, failure=False):
        self.data, self.failure = data, failure
        self.closed = self.released = False

    def stream(self, size, *, decode_content):
        assert decode_content is False
        yield self.data[:2]
        if self.failure:
            raise TimeoutError("must not export private object key")
        yield self.data[2:]

    def close(self):
        self.closed = True

    def release_conn(self):
        self.released = True


class Client:
    def __init__(self, source):
        self.data = {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob("*") if p.is_file()}
        self.list_calls, self.responses = 0, []
        self.failure = ""

    def get_bucket_versioning(self, bucket):
        return SimpleNamespace(status="Enabled" if self.failure == "versioning" else None)

    def get_bucket_lifecycle(self, bucket):
        raise S3Error(response=None, code="NoSuchLifecycleConfiguration", message="synthetic",
                      resource="", request_id="", host_id="")

    def get_object_lock_config(self, bucket):
        raise S3Error(response=None, code="ObjectLockConfigurationNotFoundError", message="synthetic",
                      resource="", request_id="", host_id="")

    def stat_object(self, bucket, key):
        if self.failure == "head":
            raise OSError("private key")
        return SimpleNamespace(object_name=key, size=len(self.data[key]), etag="synthetic-etag",
                               last_modified=datetime(2026, 1, 1, tzinfo=UTC), version_id=None)

    def list_objects(self, bucket, recursive):
        assert recursive
        self.list_calls += 1
        for index, key in enumerate(sorted(self.data)):
            yield self.stat_object(bucket, key)
            if index == 0 and self.failure == "page":
                raise OSError("second page unavailable")
        if self.failure == "duplicate":
            yield self.stat_object(bucket, sorted(self.data)[0])
        if self.failure == "target-change" and self.list_calls > 1:
            yield SimpleNamespace(object_name="unexpected", size=0, etag="x", last_modified=datetime(2026, 1, 1, tzinfo=UTC), version_id=None)

    def get_object(self, bucket, key):
        data = self.data[key]
        if self.failure == "get":
            raise OSError("private key")
        if key != "empty":
            if self.failure == "same-size":
                data = b"X" * len(data)
            if self.failure == "short":
                data = data[:-1]
            if self.failure == "long":
                data += b"X"
        result = Response(data, failure=self.failure == "stream")
        self.responses.append(result)
        return result


def test_complete_readback_with_unicode_spaces_and_empty_file(checker, source):
    initial = checker.file_manifest(source, deadline=time.monotonic() + 10)
    client = Client(source)
    result = checker.verify(source, initial, client, "synthetic-bucket", deadline=time.monotonic() + 10)
    assert result == initial["files"]
    assert client.list_calls >= 2
    assert all(r.closed and r.released for r in client.responses)


def test_gzip_metadata_never_substitutes_decoded_bytes(checker, tmp_path):
    root = tmp_path / "objects"
    root.mkdir(mode=0o700)
    # Equal encoded/decoded sizes: a size-only safeguard cannot catch this.
    data = b"A" * 23
    encoded = gzip.compress(data)
    assert len(encoded) == len(data) and encoded != data
    (root / "object").write_bytes(data)
    (root / "object").chmod(0o600)
    expected = checker.file_manifest(root, deadline=time.monotonic() + 10)
    client = Client(root)
    client.get_object = lambda bucket, key: HTTPResponse(
        body=io.BytesIO(encoded), headers={"Content-Encoding": "gzip"}, preload_content=False)
    with pytest.raises(ValueError):
        checker.verify(root, expected, client, "synthetic-bucket", deadline=time.monotonic() + 10)


@pytest.mark.parametrize("failure", ["same-size", "short", "long", "page", "duplicate", "target-change", "head", "get", "stream", "versioning"])
def test_readback_rejects_incomplete_or_changed_objects(checker, source, failure):
    initial = checker.file_manifest(source, deadline=time.monotonic() + 10)
    client = Client(source)
    client.failure = failure
    with pytest.raises((ValueError, OSError, TimeoutError)):
        checker.verify(source, initial, client, "synthetic-bucket", deadline=time.monotonic() + 10)
    assert all(r.closed and r.released for r in client.responses)


@pytest.mark.parametrize("change", ["missing", "extra"])
def test_exact_set_of_keys_required(checker, source, change):
    initial = checker.file_manifest(source, deadline=time.monotonic() + 10)
    client = Client(source)
    if change == "missing":
        del client.data["empty"]
    else:
        client.data["extra"] = b""
    with pytest.raises(ValueError):
        checker.verify(source, initial, client, "synthetic-bucket", deadline=time.monotonic() + 10)


def test_empty_source_requires_empty_bucket(checker, tmp_path):
    root = tmp_path / "empty"
    root.mkdir(mode=0o700)
    initial = checker.file_manifest(root, deadline=time.monotonic() + 10)
    client = Client(root)
    assert checker.verify(root, initial, client, "synthetic-bucket", deadline=time.monotonic() + 10) == []
    client.data["extra"] = b""
    with pytest.raises(ValueError):
        checker.verify(root, initial, client, "synthetic-bucket", deadline=time.monotonic() + 10)


@pytest.mark.parametrize("kind", ["symlink-file", "symlink-directory", "hardlink", "fifo", "open-file", "open-directory"])
def test_source_trust_boundary(checker, source, tmp_path, kind):
    if kind == "symlink-file":
        (source / "link").symlink_to(source / "empty")
    elif kind == "symlink-directory":
        (source / "link").symlink_to(source / "папка с пробелом", target_is_directory=True)
    elif kind == "hardlink":
        os.link(source / "empty", source / "link")
    elif kind == "fifo":
        os.mkfifo(source / "fifo", 0o600)
    elif kind == "open-file":
        (source / "empty").chmod(0o644)
    else:
        source.chmod(0o755)
    with pytest.raises(ValueError):
        checker.file_manifest(source, deadline=time.monotonic() + 10)


def test_source_change_after_capture_is_rejected(checker, source):
    initial = checker.file_manifest(source, deadline=time.monotonic() + 10)
    client = Client(source)
    (source / "empty").write_bytes(b"modified")
    with pytest.raises(ValueError):
        checker.verify(source, initial, client, "synthetic-bucket", deadline=time.monotonic() + 10)


def test_source_change_during_get_is_rejected(checker, source):
    initial = checker.file_manifest(source, deadline=time.monotonic() + 10)
    client = Client(source)
    original = client.get_object

    def change(bucket, key):
        (source / "empty").write_bytes(b"late change")
        return original(bucket, key)

    client.get_object = change
    with pytest.raises(ValueError):
        checker.verify(source, initial, client, "synthetic-bucket", deadline=time.monotonic() + 10)


def test_expired_deadline_cannot_pass(checker, source):
    with pytest.raises(TimeoutError):
        checker.file_manifest(source, deadline=time.monotonic() - 1)


@pytest.mark.parametrize("key", ["../escape", "/absolute", "a//b", "a/./b", "a/../b", "", "e\u0301", "x" * 1025])
def test_unsupported_key_rejected_without_normalizing(checker, key):
    with pytest.raises(ValueError):
        checker.object_key(key)


def test_snapshot_is_create_only_and_host_identity_rechecked(source, tmp_path):
    manifest = tmp_path / "manifest.json"
    script = REPO / "infra/scripts/rec-object-verify.py"

    def run(action):
        return subprocess.run([sys.executable, str(script), action, str(source), str(manifest)],
                              text=True, capture_output=True, timeout=10)

    assert run("snapshot").returncode == 0
    original = manifest.read_bytes()
    assert manifest.stat().st_mode & 0o777 == 0o600
    assert run("snapshot").returncode != 0
    assert manifest.read_bytes() == original
    assert run("source").returncode == 0
    empty = source / "empty"
    replacement = tmp_path / "replacement"
    replacement.write_bytes(b"")
    replacement.chmod(0o600)
    replacement.replace(empty)
    result = run("source")
    assert result.returncode != 0
    assert "object_restore_result=pass" not in result.stdout
    assert str(source) not in result.stdout + result.stderr


def test_response_release_on_connection_cleanup_error(checker, source):
    initial = checker.file_manifest(source, deadline=time.monotonic() + 10)
    client = Client(source)
    original = client.get_object

    def failing_close(bucket, key):
        response = original(bucket, key)

        def close():
            raise OSError("private object name")

        response.close = close
        return response

    client.get_object = failing_close
    with pytest.raises(OSError):
        checker.verify(source, initial, client, "synthetic-bucket", deadline=time.monotonic() + 10)
    assert client.responses and all(r.released for r in client.responses)


@pytest.mark.parametrize("stop", [signal.SIGHUP, signal.SIGINT, signal.SIGTERM, signal.SIGALRM])
def test_cli_signal_and_alarm_reject_without_private_exception(source, tmp_path, stop):
    script = REPO / "infra/scripts/rec-object-verify.py"
    code = """
import importlib.util, signal, sys, time
spec = importlib.util.spec_from_file_location('checker', sys.argv[1])
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
number = int(sys.argv[4])
def interrupted_read(*args, **kwargs):
    if number == signal.SIGALRM:
        time.sleep(1)
    else:
        signal.raise_signal(number)
    raise AssertionError('private object must not appear in output')
checker.file_manifest = interrupted_read
if number == signal.SIGALRM:
    def alarm(seconds):
        assert seconds in (0, 600)
        signal.setitimer(signal.ITIMER_REAL, 0.05 if seconds else 0)
    checker.signal.alarm = alarm
raise SystemExit(checker.main(['snapshot', sys.argv[2], sys.argv[3]]))
"""
    manifest = tmp_path / "interrupted.json"
    result = subprocess.run([sys.executable, "-c", code, str(script), str(source), str(manifest), str(stop)],
                            text=True, capture_output=True, timeout=5)
    assert result.returncode == 1
    assert result.stdout == "object_restore_result=failed\nreason=object_restore_unverified\n"
    assert result.stderr == "" and not manifest.exists()
