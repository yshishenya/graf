import os
import stat
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import BinaryIO

from anyio import to_thread
from minio import Minio
from minio.error import S3Error

from twobrain_rec_server.config import Settings, get_settings

MISSING_OBJECT_CODES = {"NoSuchKey", "NoSuchObject"}
DOWNLOAD_CHUNK_BYTES = 4 * 1024 * 1024
STORAGE_READINESS_OBJECT_KEY = "_system/readiness/ready"


class StorageTransferError(RuntimeError):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"Storage transfer failed: {reason_code}")


@dataclass(frozen=True, slots=True)
class StorageObjectStat:
    """Metadata needed to validate an object before serving it to a user."""

    size: int


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
        try:
            self.client.stat_object(
                self.settings.minio_bucket,
                STORAGE_READINESS_OBJECT_KEY,
            )
        except S3Error as exc:
            if exc.code in MISSING_OBJECT_CODES:
                return False
            raise
        return True

    async def is_ready_async(self) -> bool:
        return await to_thread.run_sync(self.is_ready)

    def object_exists(self, object_key: str) -> bool:
        try:
            self.client.stat_object(self.settings.minio_bucket, object_key)
        except S3Error as exc:
            if exc.code in MISSING_OBJECT_CODES:
                return False
            raise
        return True

    async def object_exists_async(self, object_key: str) -> bool:
        return await to_thread.run_sync(self.object_exists, object_key)

    def stat_object(self, object_key: str) -> StorageObjectStat:
        try:
            result = self.client.stat_object(self.settings.minio_bucket, object_key)
        except S3Error as exc:
            if exc.code in MISSING_OBJECT_CODES:
                raise KeyError(object_key) from exc
            raise
        size = getattr(result, "size", None)
        if not isinstance(size, int) or size < 0:
            raise StorageTransferError("storage_unavailable")
        return StorageObjectStat(size=size)

    async def stat_object_async(self, object_key: str) -> StorageObjectStat:
        return await to_thread.run_sync(self.stat_object, object_key)

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

    def download_verified_to_path(
        self,
        object_key: str,
        destination_path: str | Path,
        *,
        expected_length: int,
        expected_sha256: str,
        max_bytes: int,
        chunk_size: int = DOWNLOAD_CHUNK_BYTES,
    ) -> int:
        if (
            expected_length <= 0
            or expected_length > max_bytes
            or len(expected_sha256) != 64
            or any(character not in "0123456789abcdef" for character in expected_sha256.lower())
            or chunk_size <= 0
        ):
            raise StorageTransferError("source_mismatch")
        try:
            response = self.client.get_object(self.settings.minio_bucket, object_key)
        except S3Error as exc:
            if exc.code in MISSING_OBJECT_CODES:
                raise StorageTransferError("source_missing") from exc
            raise StorageTransferError("storage_unavailable") from exc

        destination = Path(destination_path)
        descriptor = -1
        total = 0
        digest = sha256()
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(destination, flags, 0o600)
            while True:
                chunk = response.read(min(chunk_size, max_bytes - total + 1))
                if not chunk:
                    break
                total += len(chunk)
                if total > expected_length or total > max_bytes:
                    raise StorageTransferError("source_mismatch")
                digest.update(chunk)
                view = memoryview(chunk)
                while view:
                    written = os.write(descriptor, view)
                    view = view[written:]
            os.fsync(descriptor)
            if total != expected_length or digest.hexdigest() != expected_sha256.lower():
                raise StorageTransferError("source_mismatch")
            return total
        except StorageTransferError:
            destination.unlink(missing_ok=True)
            raise
        except OSError as exc:
            destination.unlink(missing_ok=True)
            raise StorageTransferError("temporary_storage_unavailable") from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            response.close()
            response.release_conn()

    async def download_verified_to_path_async(
        self,
        object_key: str,
        destination_path: str | Path,
        *,
        expected_length: int,
        expected_sha256: str,
        max_bytes: int,
        chunk_size: int = DOWNLOAD_CHUNK_BYTES,
    ) -> int:
        return await to_thread.run_sync(
            lambda: self.download_verified_to_path(
                object_key,
                destination_path,
                expected_length=expected_length,
                expected_sha256=expected_sha256,
                max_bytes=max_bytes,
                chunk_size=chunk_size,
            )
        )

    def upload_verified_path(
        self,
        object_key: str,
        source_path: str | Path,
        *,
        expected_length: int,
        expected_sha256: str,
        max_bytes: int,
        chunk_size: int = DOWNLOAD_CHUNK_BYTES,
    ) -> None:
        source = Path(source_path)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(source, flags)
        except OSError as exc:
            raise StorageTransferError("generated_output_invalid") from exc
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_size != expected_length
                or not 0 < before.st_size <= max_bytes
            ):
                raise StorageTransferError("generated_output_invalid")
            digest = sha256()
            total = 0
            while True:
                chunk = os.read(descriptor, chunk_size)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise StorageTransferError("generated_output_invalid")
                digest.update(chunk)
            if total != expected_length or digest.hexdigest() != expected_sha256.lower():
                raise StorageTransferError("generated_output_invalid")
            os.lseek(descriptor, 0, os.SEEK_SET)
            with os.fdopen(os.dup(descriptor), "rb", closefd=True) as stream:
                self.client.put_object(
                    self.settings.minio_bucket,
                    object_key,
                    stream,
                    length=expected_length,
                    part_size=max(chunk_size, 5 * 1024 * 1024),
                )
            after = os.fstat(descriptor)
            if (
                after.st_size != before.st_size
                or after.st_mtime_ns != before.st_mtime_ns
                or after.st_ctime_ns != before.st_ctime_ns
            ):
                raise StorageTransferError("generated_output_invalid")
        except S3Error as exc:
            raise StorageTransferError("storage_unavailable") from exc
        finally:
            os.close(descriptor)

    async def upload_verified_path_async(
        self,
        object_key: str,
        source_path: str | Path,
        *,
        expected_length: int,
        expected_sha256: str,
        max_bytes: int,
        chunk_size: int = DOWNLOAD_CHUNK_BYTES,
    ) -> None:
        await to_thread.run_sync(
            lambda: self.upload_verified_path(
                object_key,
                source_path,
                expected_length=expected_length,
                expected_sha256=expected_sha256,
                max_bytes=max_bytes,
                chunk_size=chunk_size,
            )
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
                if remaining:
                    raise StorageTransferError("storage_object_size_mismatch")
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
