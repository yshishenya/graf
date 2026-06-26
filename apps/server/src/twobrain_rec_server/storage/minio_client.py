from collections.abc import AsyncIterator, Iterator
from typing import BinaryIO

from anyio import to_thread
from minio import Minio
from minio.error import S3Error

from twobrain_rec_server.config import Settings, get_settings


class MinioStorage:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = Minio(
            self.settings.minio_endpoint,
            access_key=self.settings.minio_access_key,
            secret_key=self.settings.minio_secret_key,
            secure=self.settings.minio_secure,
        )

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.settings.minio_bucket):
            self.client.make_bucket(self.settings.minio_bucket)

    async def ensure_bucket_async(self) -> None:
        await to_thread.run_sync(self.ensure_bucket)

    def is_ready(self) -> bool:
        return self.client.bucket_exists(self.settings.minio_bucket)

    async def is_ready_async(self) -> bool:
        return await to_thread.run_sync(self.is_ready)

    def put_stream(self, object_key: str, stream: BinaryIO, length: int) -> None:
        self.client.put_object(
            self.settings.minio_bucket,
            object_key,
            stream,
            length=length,
        )

    async def put_stream_async(self, object_key: str, stream: BinaryIO, length: int) -> None:
        await to_thread.run_sync(self.put_stream, object_key, stream, length)

    def get_bytes(self, object_key: str) -> bytes:
        response = self.client.get_object(self.settings.minio_bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def get_bytes_async(self, object_key: str) -> bytes:
        return await to_thread.run_sync(self.get_bytes, object_key)

    def delete_object(self, object_key: str) -> None:
        try:
            self.client.remove_object(self.settings.minio_bucket, object_key)
        except S3Error as exc:
            if exc.code not in {"NoSuchKey", "NoSuchObject"}:
                raise

    async def delete_object_async(self, object_key: str) -> None:
        await to_thread.run_sync(self.delete_object, object_key)


def get_storage(settings: Settings | None = None) -> MinioStorage:
    return MinioStorage(settings)


async def iter_upload_chunks(stream: AsyncIterator[bytes]) -> Iterator[bytes]:
    async for chunk in stream:
        yield chunk
