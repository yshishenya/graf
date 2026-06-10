import asyncio
from io import BytesIO

from twobrain_rec_server.storage.minio_client import MinioStorage


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
