import asyncio
from io import BytesIO

import pytest
from minio.error import S3Error

from twobrain_rec_server.storage.minio_client import MinioStorage


class _Settings:
    minio_bucket = "test-bucket"


class _FailingGetObjectClient:
    def __init__(self, code: str) -> None:
        self.code = code

    def get_object(self, *_args: object) -> object:
        raise S3Error(None, self.code, "storage failed", "object", "request", "host")


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


def test_get_bytes_preserves_non_missing_storage_errors() -> None:
    storage = _storage_with_client(_FailingGetObjectClient("AccessDenied"))

    with pytest.raises(S3Error, match="AccessDenied"):
        MinioStorage.get_bytes(storage, "objects/private.wav")
