from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import BinaryIO

from anyio import to_thread
from minio import Minio
from minio.error import S3Error

from twobrain_rec_server.config import Settings, get_settings

MISSING_OBJECT_CODES = {"NoSuchKey", "NoSuchObject"}
DOWNLOAD_CHUNK_BYTES = 4 * 1024 * 1024


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
        try:
            response = self.client.get_object(self.settings.minio_bucket, object_key)
        except S3Error as exc:
            if exc.code in MISSING_OBJECT_CODES:
                raise KeyError(object_key) from exc
            raise
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def get_bytes_async(self, object_key: str) -> bytes:
        return await to_thread.run_sync(self.get_bytes, object_key)

    def download_to_path(
        self,
        object_key: str,
        destination_path: str | Path,
        *,
        chunk_size: int = DOWNLOAD_CHUNK_BYTES,
    ) -> int:
        try:
            response = self.client.get_object(self.settings.minio_bucket, object_key)
        except S3Error as exc:
            if exc.code in MISSING_OBJECT_CODES:
                raise KeyError(object_key) from exc
            raise
        total = 0
        try:
            with Path(destination_path).open("wb") as destination:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    destination.write(chunk)
                    total += len(chunk)
            return total
        finally:
            response.close()
            response.release_conn()

    async def download_to_path_async(
        self,
        object_key: str,
        destination_path: str | Path,
        *,
        chunk_size: int = DOWNLOAD_CHUNK_BYTES,
    ) -> int:
        return await to_thread.run_sync(
            lambda: self.download_to_path(object_key, destination_path, chunk_size=chunk_size)
        )

    def iter_object(
        self,
        object_key: str,
        *,
        offset: int = 0,
        length: int | None = None,
        chunk_size: int = DOWNLOAD_CHUNK_BYTES,
    ) -> Iterator[bytes]:
        try:
            response = self.client.get_object(
                self.settings.minio_bucket,
                object_key,
                offset=offset,
                length=length or 0,
            )
        except S3Error as exc:
            if exc.code in MISSING_OBJECT_CODES:
                raise KeyError(object_key) from exc
            raise

        def chunks() -> Iterator[bytes]:
            remaining = length
            try:
                while remaining is None or remaining > 0:
                    read_size = chunk_size if remaining is None else min(chunk_size, remaining)
                    chunk = response.read(read_size)
                    if not chunk:
                        break
                    if remaining is not None:
                        remaining -= len(chunk)
                    yield chunk
            finally:
                response.close()
                response.release_conn()

        return chunks()

    def delete_object(self, object_key: str) -> None:
        try:
            self.client.remove_object(self.settings.minio_bucket, object_key)
        except S3Error as exc:
            if exc.code not in MISSING_OBJECT_CODES:
                raise

    async def delete_object_async(self, object_key: str) -> None:
        await to_thread.run_sync(self.delete_object, object_key)


def get_storage(settings: Settings | None = None) -> MinioStorage:
    return MinioStorage(settings)


async def iter_upload_chunks(stream: AsyncIterator[bytes]) -> Iterator[bytes]:
    async for chunk in stream:
        yield chunk
