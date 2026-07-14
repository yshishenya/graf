from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO

DOWNLOAD_CHUNK_BYTES = 4 * 1024 * 1024


@dataclass
class FakeMinioStorage:
    objects: dict[str, bytes] = field(default_factory=dict)
    deleted_keys: list[str] = field(default_factory=list)
    ensured: bool = False
    fail_put: bool = False

    def ensure_bucket(self) -> None:
        self.ensured = True

    def is_ready(self) -> bool:
        return True

    def object_exists(self, object_key: str) -> bool:
        return object_key in self.objects

    async def object_exists_async(self, object_key: str) -> bool:
        return self.object_exists(object_key)

    def put_bytes(self, object_key: str, data: bytes) -> None:
        self.objects[object_key] = data

    def put_stream(self, object_key: str, stream: BinaryIO, length: int) -> None:
        if self.fail_put:
            raise RuntimeError("configured fake storage failure")
        data = stream.read(length)
        if len(data) != length:
            raise ValueError("stream length mismatch")
        trailing = stream.read(1)
        if trailing:
            raise ValueError("stream longer than declared length")
        self.objects[object_key] = data

    def get_bytes(self, object_key: str) -> bytes:
        return self.objects[object_key]

    async def get_bytes_async(self, object_key: str) -> bytes:
        return self.get_bytes(object_key)

    def download_to_path(
        self,
        object_key: str,
        destination_path: str | Path,
        *,
        chunk_size: int = DOWNLOAD_CHUNK_BYTES,
    ) -> int:
        data = self.objects[object_key]
        total = 0
        with Path(destination_path).open("wb") as destination:
            for offset in range(0, len(data), chunk_size):
                chunk = data[offset : offset + chunk_size]
                destination.write(chunk)
                total += len(chunk)
        return total

    async def download_to_path_async(
        self,
        object_key: str,
        destination_path: str | Path,
        *,
        chunk_size: int = DOWNLOAD_CHUNK_BYTES,
    ) -> int:
        return self.download_to_path(object_key, destination_path, chunk_size=chunk_size)

    def iter_object(
        self,
        object_key: str,
        *,
        offset: int = 0,
        length: int | None = None,
        chunk_size: int = DOWNLOAD_CHUNK_BYTES,
    ):
        data = self.objects[object_key]
        end = len(data) if length is None else min(offset + length, len(data))

        def chunks():
            for current in range(offset, end, chunk_size):
                yield data[current : min(current + chunk_size, end)]

        return chunks()

    def delete_object(self, object_key: str) -> None:
        self.deleted_keys.append(object_key)
        self.objects.pop(object_key, None)


class FailOnceDeleteStorage:
    """Delegate storage that fails the first delete after a selected object exists."""

    def __init__(self, delegate: FakeMinioStorage) -> None:
        self.delegate = delegate
        self.fail_keys: set[str] = set()
        self.failed_keys: set[str] = set()

    def arm(self, object_key: str) -> None:
        self.fail_keys.add(object_key)

    def delete_object(self, object_key: str) -> None:
        if (
            object_key in self.fail_keys
            and object_key not in self.failed_keys
            and self.delegate.object_exists(object_key)
        ):
            self.failed_keys.add(object_key)
            raise RuntimeError("configured one-shot delete failure")
        self.delegate.delete_object(object_key)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.delegate, name)
