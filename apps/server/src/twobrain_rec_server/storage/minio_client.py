from collections.abc import AsyncIterator, Iterator
from typing import BinaryIO

from minio import Minio

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

    def put_stream(self, object_key: str, stream: BinaryIO, length: int) -> None:
        self.client.put_object(
            self.settings.minio_bucket,
            object_key,
            stream,
            length=length,
        )


def get_storage() -> MinioStorage:
    return MinioStorage()


async def iter_upload_chunks(stream: AsyncIterator[bytes]) -> Iterator[bytes]:
    async for chunk in stream:
        yield chunk
