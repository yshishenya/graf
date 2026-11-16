import asyncio
import json
import os
from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO
from threading import Event
from time import monotonic
from uuid import uuid4

import pytest
from minio.error import S3Error
from urllib3.exceptions import ProtocolError

from twobrain_rec_server.config import Settings
from twobrain_rec_server.storage.minio_client import (
    STORAGE_READINESS_OBJECT_KEY,
    MinioStorage,
    StorageTransferError,
)
from twobrain_rec_server.storage.recovery import storage_read_fence
from twobrain_rec_server.storage.strict_upload_cleanup import ATTEMPT_METADATA


class _Settings:
    minio_bucket = "test-bucket"
    minio_endpoint = "127.0.0.1:9000"
    minio_secure = False


class _FailingGetObjectClient:
    def __init__(self, code: str) -> None:
        self.code = code

    def get_object(self, *_args: object) -> object:
        raise S3Error(None, self.code, "storage failed", "object", "request", "host")


class _FakeGetObjectResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self._offset = 0
        self.closed = False
        self.released = False

    def read(self, length: int | None = None) -> bytes:
        if length is None:
            length = len(self._data) - self._offset
        chunk = self._data[self._offset : self._offset + length]
        self._offset += len(chunk)
        return chunk

    def close(self) -> None:
        self.closed = True

    def release_conn(self) -> None:
        self.released = True


class _FakeGetObjectClient:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.response = _FakeGetObjectResponse(data)
        self.calls: list[dict[str, object]] = []

    def get_object(self, *_args: object, **kwargs: object) -> _FakeGetObjectResponse:
        self.calls.append(kwargs)
        offset = int(kwargs.get("offset") or 0)
        length = int(kwargs.get("length") or 0)
        body = self.data[offset:] if length == 0 else self.data[offset : offset + length]
        self.response = _FakeGetObjectResponse(body)
        return self.response


class _ReadinessClient:
    def __init__(self, error_code: str | None = None) -> None:
        self.error_code = error_code
        self.calls: list[tuple[str, str]] = []

    def stat_object(self, bucket: str, object_key: str) -> object:
        self.calls.append((bucket, object_key))
        if self.error_code is not None:
            raise S3Error(
                None,
                self.error_code,
                "storage failed",
                object_key,
                "request",
                "host",
            )
        return object()


class _StatClient:
    def __init__(self, size: int) -> None:
        self.size = size

    def stat_object(self, _bucket: str, _object_key: str) -> object:
        return type("Stat", (), {"size": self.size})()


def _storage_with_client(client: object) -> MinioStorage:
    storage = MinioStorage.__new__(MinioStorage)
    storage.settings = _Settings()
    storage.client = client
    return storage


def test_minio_async_wrappers_delegate_to_sync_sdk_methods_off_event_loop() -> None:
    calls: list[tuple[str, object]] = []
    storage = MinioStorage.__new__(MinioStorage)

    def ensure_bucket() -> None:
        calls.append(("ensure_bucket", None))

    def is_ready() -> bool:
        calls.append(("is_ready", None))
        return True

    def put_stream(object_key: str, stream: BytesIO, length: int) -> None:
        calls.append(("put_stream", (object_key, stream.read(), length)))

    storage.ensure_bucket = ensure_bucket
    storage.is_ready = is_ready
    storage.put_stream = put_stream

    async def run_wrappers() -> None:
        await MinioStorage.ensure_bucket_async(storage)
        assert await MinioStorage.is_ready_async(storage) is True
        await MinioStorage.put_stream_async(storage, "objects/part.wav", BytesIO(b"abc"), 3)

    asyncio.run(run_wrappers())

    assert calls == [
        ("ensure_bucket", None),
        ("is_ready", None),
        ("put_stream", ("objects/part.wav", b"abc", 3)),
    ]


def test_get_bytes_normalizes_missing_object_errors() -> None:
    storage = _storage_with_client(_FailingGetObjectClient("NoSuchKey"))

    with pytest.raises(KeyError, match="objects/missing.wav"):
        MinioStorage.get_bytes(storage, "objects/missing.wav")


def test_readiness_uses_exact_sentinel_without_bucket_listing() -> None:
    client = _ReadinessClient()
    storage = _storage_with_client(client)

    assert MinioStorage.is_ready(storage) is True
    assert client.calls == [("test-bucket", STORAGE_READINESS_OBJECT_KEY)]


def test_readiness_is_false_when_sentinel_is_missing() -> None:
    storage = _storage_with_client(_ReadinessClient("NoSuchKey"))

    assert MinioStorage.is_ready(storage) is False


def test_stat_object_returns_safe_size_metadata_and_async_wrapper() -> None:
    storage = _storage_with_client(_StatClient(123))

    assert MinioStorage.stat_object(storage, "objects/audio.m4a").size == 123
    assert asyncio.run(MinioStorage.stat_object_async(storage, "objects/audio.m4a")).size == 123


def test_stat_object_normalizes_missing_object_errors() -> None:
    storage = _storage_with_client(_ReadinessClient("NoSuchKey"))

    with pytest.raises(KeyError, match="objects/missing.m4a"):
        MinioStorage.stat_object(storage, "objects/missing.m4a")


def test_get_bytes_preserves_non_missing_storage_errors() -> None:
    storage = _storage_with_client(_FailingGetObjectClient("AccessDenied"))

    with pytest.raises(S3Error, match="AccessDenied"):
        MinioStorage.get_bytes(storage, "objects/private.wav")


def test_download_to_path_streams_chunks_and_releases_storage_response(tmp_path) -> None:
    client = _FakeGetObjectClient(b"abcdef")
    storage = _storage_with_client(client)
    target = tmp_path / "object.wav"

    downloaded = MinioStorage.download_to_path(storage, "objects/audio.wav", target, chunk_size=2)

    assert downloaded == 6
    assert target.read_bytes() == b"abcdef"
    assert client.response.closed is True
    assert client.response.released is True


@pytest.mark.parametrize("family", [
    "artifacts/media-revisions/revision/attempts/incomplete",
    "sessions/session/tracks/media/parts/00000001/calendar-attempts/incomplete",
])
def test_ordinary_storage_readers_reject_reserved_sources_before_get(tmp_path, family) -> None:
    client = _FakeGetObjectClient(b"x")
    storage = _storage_with_client(client)
    key = f"organizations/org/workspaces/workspace/meetings/meeting/{family}"
    target = tmp_path / "source"
    for read in (
        lambda: storage.get_bytes(key),
        lambda: storage.iter_object(key, offset=0, length=1),
        lambda: storage.download_to_path(key, target),
        lambda: storage.download_verified_to_path(
            key, target, expected_length=1, expected_sha256=sha256(b"x").hexdigest(), max_bytes=1,
        ),
    ):
        with pytest.raises(StorageTransferError, match="strict_upload_requires_dedicated_client"):
            read()
    assert client.calls == []
    assert not target.exists()


def test_iter_object_streams_full_object_and_releases_storage_response() -> None:
    client = _FakeGetObjectClient(b"abcdef")
    storage = _storage_with_client(client)

    chunks = list(MinioStorage.iter_object(storage, "objects/audio.m4a", chunk_size=2))

    assert chunks == [b"ab", b"cd", b"ef"]
    assert client.calls == [{"offset": 0, "length": 0}]
    assert client.response.closed is True
    assert client.response.released is True


def test_iter_object_streams_requested_range_and_releases_storage_response() -> None:
    client = _FakeGetObjectClient(b"abcdef")
    storage = _storage_with_client(client)

    chunks = list(
        MinioStorage.iter_object(storage, "objects/audio.m4a", offset=2, length=3, chunk_size=2)
    )

    assert chunks == [b"cd", b"e"]
    assert client.calls == [{"offset": 2, "length": 3}]
    assert client.response.closed is True
    assert client.response.released is True


def test_iter_object_rejects_short_range_and_releases_storage_response() -> None:
    client = _FakeGetObjectClient(b"ab")
    storage = _storage_with_client(client)

    with pytest.raises(StorageTransferError, match="storage_object_size_mismatch"):
        list(MinioStorage.iter_object(storage, "objects/audio.m4a", length=3, chunk_size=2))

    assert client.response.closed is True
    assert client.response.released is True


@pytest.mark.parametrize("pause", ["body", "fsync"])
async def test_strict_source_cancel_keeps_fence_until_response_closes(tmp_path, monkeypatch, pause) -> None:
    entered = Event()
    finish = Event()
    closed = Event()
    fence_path = tmp_path / "read.lock"
    fence_path.touch()
    payload = b"synthetic audio"
    destination = tmp_path / "output"
    key = (
        f"organizations/{uuid4()}/workspaces/{uuid4()}/meetings/{uuid4()}/"
        f"artifacts/media-revisions/{uuid4()}/attempts/1/2/tracks/media"
    )

    attempt_id = uuid4()
    disconnect = False

    def pause_worker():
        entered.set()
        assert finish.wait(5)

    if pause == "fsync":
        fsync = os.fsync

        def held_fsync(fd):
            pause_worker()
            fsync(fd)

        monkeypatch.setattr(os, "fsync", held_fsync)

    class HeldResponse(_FakeGetObjectResponse):
        headers = {ATTEMPT_METADATA: str(attempt_id)}

        def read(self, length: int | None = None) -> bytes:
            if pause == "body":
                pause_worker()
            if disconnect:
                if self._offset:
                    raise ProtocolError("synthetic body disconnect")
                length = 1
            return super().read(length)

        def release_conn(self) -> None:
            assert self.closed
            super().release_conn()
            closed.set()

    class Client:
        def get_object(self, bucket, name):
            assert bucket == _Settings.minio_bucket and name == key
            return HeldResponse(payload)

    async def admit() -> bool:
        with storage_read_fence(fence_path, exclusive=True) as exclusive:
            assert exclusive is None
        return True

    storage = _storage_with_client(Client())
    monkeypatch.setattr(storage, "_strict_source_client", lambda _http: storage.client)
    request = dict(
        epoch=1, deadline=monotonic() + 15, attempt_id=attempt_id, fence_path=fence_path, admit=admit, expected_length=len(payload),
        expected_sha256=sha256(payload).hexdigest(), max_bytes=len(payload),
    )
    task = asyncio.create_task(storage.download_strict_source_to_path_async(
        key, destination, **request,
    ))
    try:
        assert await asyncio.to_thread(entered.wait, 2)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done() and not closed.is_set()
        assert not destination.exists()
        with storage_read_fence(fence_path, exclusive=True) as exclusive:
            assert exclusive is None
    finally:
        finish.set()

    async with asyncio.timeout(2):
        with pytest.raises(asyncio.CancelledError):
            await task
    assert closed.is_set()
    with storage_read_fence(fence_path, exclusive=True) as exclusive:
        assert exclusive is not None
    assert not destination.exists()
    assert not list(tmp_path.glob(".graf-source-*"))

    disconnect = True
    with pytest.raises(StorageTransferError, match="storage_unavailable"):
        await storage.download_strict_source_to_path_async(key, destination, **request)
    assert not destination.exists()
    assert not list(tmp_path.glob(".graf-source-*"))
    disconnect = False

    async def deny() -> bool:
        return False

    with pytest.raises(StorageTransferError, match="source_read_not_admitted"):
        await storage.download_strict_source_to_path_async(key, destination, **(request | {"admit": deny}))
    with pytest.raises(StorageTransferError, match="source_mismatch"):
        await storage.download_strict_source_to_path_async(key, destination, **(request | {"epoch": 2}))
    assert await storage.download_strict_source_to_path_async(key, destination, **request) == len(payload)
    assert destination.read_bytes() == payload
    with pytest.raises(StorageTransferError, match="source_mismatch"):
        await storage.download_strict_source_to_path_async(key, destination, **(request | {"attempt_id": uuid4()}))
    with pytest.raises(StorageTransferError, match="temporary_storage_unavailable"):
        await storage.download_strict_source_to_path_async(key, destination, **request)
    assert destination.read_bytes() == payload


@pytest.mark.parametrize("mode", ["header_drip", "body_drip", "body_stall", "redirect", "retry"])
async def test_strict_read_http_stops_unfinished_responses_without_replay(tmp_path, mode) -> None:
    attempt_id = uuid4()
    requests = []
    handlers = set()
    payload = b"synthetic source" * 64

    async def respond(reader, writer):
        task = asyncio.current_task()
        handlers.add(task)
        try:
            request = await reader.readuntil(b"\r\n\r\n")
            target = request.split(b" ", 2)[1]
            requests.append(target)
            if target.endswith(b"?location="):
                region = b"<LocationConstraint>us-east-1</LocationConstraint>"
                writer.write(f"HTTP/1.1 200 OK\r\nContent-Length: {len(region)}\r\nConnection: close\r\n\r\n".encode())
                writer.write(region)
                await writer.drain()
                return
            if mode in {"redirect", "retry"}:
                status = "307 Temporary Redirect" if mode == "redirect" else "503 Service Unavailable"
                writer.write(f"HTTP/1.1 {status}\r\nLocation: /unexpected\r\nContent-Length: 0\r\n\r\n".encode())
                await writer.drain()
                return
            headers = (
                f"HTTP/1.1 200 OK\r\nContent-Length: {len(payload)}\r\n"
                f"{ATTEMPT_METADATA}: {attempt_id}\r\n\r\n"
            ).encode()
            if mode != "header_drip":
                writer.write(headers + payload[:1])
                await writer.drain()
            if mode == "body_stall":
                await asyncio.sleep(2)
            else:
                data = headers if mode == "header_drip" else payload[1:]
                for byte in data[:60]:
                    writer.write(bytes([byte]))
                    await writer.drain()
                    await asyncio.sleep(0.035)
        except (OSError, asyncio.IncompleteReadError):
            pass
        finally:
            writer.close()
            handlers.discard(task)

    server = await asyncio.start_server(respond, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    storage = MinioStorage(Settings(
        minio_endpoint=f"127.0.0.1:{port}", minio_access_key="synthetic-access",
        minio_secret_key="synthetic-secret", minio_bucket="synthetic-bucket", minio_secure=False,
    ))
    fence = tmp_path / "read.lock"
    fence.touch()
    destination = tmp_path / "output"
    key = (
        f"organizations/{uuid4()}/workspaces/{uuid4()}/meetings/{uuid4()}/"
        f"artifacts/media-revisions/{uuid4()}/attempts/1/2/tracks/media"
    )

    async def admit():
        return True

    try:
        async with server:
            start = monotonic()
            expected = "storage_unavailable" if mode in {"redirect", "retry"} else "source_read_deadline"
            with pytest.raises(StorageTransferError, match=expected):
                await storage.download_strict_source_to_path_async(
                    key, destination, epoch=1, attempt_id=attempt_id, deadline=start + 0.7,
                    fence_path=fence, admit=admit, expected_length=len(payload),
                    expected_sha256=sha256(payload).hexdigest(), max_bytes=len(payload),
                )
            assert monotonic() - start < 1.5
            assert requests == [b"/synthetic-bucket?location=", f"/synthetic-bucket/{key}".encode()]
            assert not destination.exists() and not list(tmp_path.glob(".graf-source-*"))
            with storage_read_fence(fence, exclusive=True) as exclusive:
                assert exclusive is not None
    finally:
        pending = list(handlers)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)


async def test_strict_read_does_not_admit_or_hold_fence_during_dns(tmp_path, monkeypatch) -> None:
    loop = asyncio.get_running_loop()
    started = asyncio.Event()
    fence = tmp_path / "read.lock"
    fence.touch()

    async def stall(*args, **kwargs):
        started.set()
        await asyncio.Future()

    async def admit():
        pytest.fail("DNS must finish before storage admission")

    monkeypatch.setattr(loop, "getaddrinfo", stall)
    storage = _storage_with_client(object())
    key = (
        f"organizations/{uuid4()}/workspaces/{uuid4()}/meetings/{uuid4()}/"
        f"artifacts/media-revisions/{uuid4()}/attempts/1/2/tracks/media"
    )
    task = asyncio.create_task(storage.download_strict_source_to_path_async(
        key, tmp_path / "output", epoch=1, attempt_id=uuid4(), deadline=monotonic() + 0.25,
        fence_path=fence, admit=admit, expected_length=1, expected_sha256="0" * 64, max_bytes=1,
    ))
    await asyncio.wait_for(started.wait(), timeout=1)
    with storage_read_fence(fence, exclusive=True) as exclusive:
        assert exclusive is not None
    with pytest.raises(StorageTransferError, match="source_read_deadline"):
        await task
    assert not (tmp_path / "output").exists()


async def test_accepted_cleanup_holds_matching_recovery_during_worker_admission(tmp_path) -> None:
    recovery_id = uuid4()
    path = tmp_path / "recovery"
    lock_path = path.with_suffix(".lock")
    lock_path.touch()
    path.write_text(json.dumps({
        "schema": 1, "scope": "synthetic-scope", "state": "reconciled", "recovery_id": str(recovery_id),
    }))
    key = (
        f"organizations/{uuid4()}/workspaces/{uuid4()}/meetings/{uuid4()}/"
        f"artifacts/media-revisions/{uuid4()}/attempts/1/2/tracks/media"
    )
    checks = []

    @contextmanager
    def admission(*args):
        with storage_read_fence(lock_path, exclusive=True) as exclusive:
            assert exclusive is None
        checks.append(args)
        yield None  # No storage operations in this admission test.

    storage = MinioStorage(Settings(
        strict_storage_scope="synthetic-scope", strict_storage_recovery_file=path,
        strict_storage_recovery_id=recovery_id,
    ), strict_upload_cleanup_admission=admission)
    args = dict(scope="synthetic-scope", epoch=1, key=key, upload_id="synthetic",
                attempt_id=uuid4(), deadline=monotonic()+5)
    assert not await storage.purge_strict_upload_attempt(**args, expected_recovery=str(uuid4()))
    assert not checks
    assert not await storage.purge_strict_upload_attempt(**args, expected_recovery=str(recovery_id))
    assert len(checks) == 1
    with storage_read_fence(lock_path, exclusive=True) as exclusive:
        assert exclusive is not None
