import asyncio
from io import BytesIO

import pytest
from minio.error import S3Error

from twobrain_rec_server.storage.minio_client import (
    STORAGE_READINESS_OBJECT_KEY,
    MinioStorage,
    StorageTransferError,
)


class _Settings:
    minio_bucket = "test-bucket"


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
