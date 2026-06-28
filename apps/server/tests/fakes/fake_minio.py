from dataclasses import dataclass, field
from typing import BinaryIO


@dataclass
class FakeMinioStorage:
    objects: dict[str, bytes] = field(default_factory=dict)
    ensured: bool = False
    fail_put: bool = False

    def ensure_bucket(self) -> None:
        self.ensured = True

    def is_ready(self) -> bool:
        return True

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

    def delete_object(self, object_key: str) -> None:
        self.objects.pop(object_key, None)
