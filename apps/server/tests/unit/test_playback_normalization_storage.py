from __future__ import annotations

from hashlib import sha256
from types import SimpleNamespace
from uuid import UUID

import pytest

from twobrain_rec_server.normalization import service as normalization_service
from twobrain_rec_server.normalization.media import MediaPolicyError, copy_regular_file
from twobrain_rec_server.storage.minio_client import MinioStorage, StorageTransferError
from twobrain_rec_server.storage.object_keys import (
    build_canonical_playback_object_key,
    build_playback_attempt_object_key,
)


class _Response:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.offset = 0
        self.closed = False

    def read(self, size: int) -> bytes:
        chunk = self.payload[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk

    def close(self) -> None:
        self.closed = True

    def release_conn(self) -> None:
        self.closed = True


class _Client:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.uploaded = b""

    def get_object(self, bucket: str, object_key: str) -> _Response:
        assert bucket == "test"
        assert object_key == "private-key"
        return _Response(self.payload)

    def put_object(
        self,
        bucket: str,
        object_key: str,
        stream,
        *,
        length: int,
        part_size: int,
    ) -> None:
        assert bucket == "test"
        assert object_key == "private-key"
        assert part_size >= 5 * 1024 * 1024
        self.uploaded = stream.read(length + 1)


def _storage(payload: bytes) -> MinioStorage:
    storage = object.__new__(MinioStorage)
    storage.settings = SimpleNamespace(minio_bucket="test")
    storage.client = _Client(payload)
    return storage


def test_attempt_and_canonical_builder_keep_one_immutable_uuid_key() -> None:
    values = {
        "organization_id": UUID("10000000-0000-0000-0000-000000000001"),
        "workspace_id": UUID("20000000-0000-0000-0000-000000000001"),
        "meeting_id": UUID("30000000-0000-0000-0000-000000000001"),
        "media_revision_id": UUID("40000000-0000-0000-0000-000000000001"),
        "attempt_id": UUID("50000000-0000-0000-0000-000000000001"),
    }

    attempt_key = build_playback_attempt_object_key(**values)
    canonical_key = build_canonical_playback_object_key(**values)

    assert attempt_key == canonical_key
    assert attempt_key.endswith("/50000000-0000-0000-0000-000000000001/meeting-review.m4a")
    assert "private" not in attempt_key


def test_verified_download_and_upload_are_disk_backed_and_digest_checked(tmp_path) -> None:
    payload = b"synthetic-normalization-output"
    digest = sha256(payload).hexdigest()
    storage = _storage(payload)
    destination = tmp_path / "50000000-0000-0000-0000-000000000001"

    downloaded = storage.download_verified_to_path(
        "private-key",
        destination,
        expected_length=len(payload),
        expected_sha256=digest,
        max_bytes=1024,
        chunk_size=5,
    )
    storage.upload_verified_path(
        "private-key",
        destination,
        expected_length=len(payload),
        expected_sha256=digest,
        max_bytes=1024,
        chunk_size=5,
    )

    assert downloaded == len(payload)
    assert storage.client.uploaded == payload
    assert destination.stat().st_mode & 0o777 == 0o600


def test_verified_download_removes_partial_file_on_digest_mismatch(tmp_path) -> None:
    payload = b"synthetic-normalization-output"
    storage = _storage(payload)
    destination = tmp_path / "partial"

    with pytest.raises(StorageTransferError) as exc_info:
        storage.download_verified_to_path(
            "private-key",
            destination,
            expected_length=len(payload),
            expected_sha256="0" * 64,
            max_bytes=1024,
            chunk_size=5,
        )
    assert exc_info.value.reason_code == "source_mismatch"
    assert not destination.exists()
    assert "private-key" not in str(exc_info.value)


def test_strict_byte_copy_is_exclusive_bounded_and_digest_verified(tmp_path) -> None:
    payload = b"synthetic-canonical-m4a"
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_bytes(payload)

    copied = copy_regular_file(source, destination, max_bytes=len(payload))

    assert destination.read_bytes() == payload
    assert copied.byte_length == len(payload)
    assert copied.sha256_hex == sha256(payload).hexdigest()
    assert destination.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        copy_regular_file(source, destination, max_bytes=len(payload))
    assert destination.read_bytes() == payload


def test_strict_byte_copy_removes_partial_destination_when_limit_is_exceeded(tmp_path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_bytes(b"synthetic-canonical-m4a")

    with pytest.raises(MediaPolicyError) as exc_info:
        copy_regular_file(source, destination, max_bytes=4)

    assert exc_info.value.reason_code == "generated_output_invalid"
    assert not destination.exists()


@pytest.mark.anyio
async def test_bmff_and_hash_scans_are_offloaded_through_anyio(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "meeting-review.m4a"
    source.write_bytes(b"synthetic")
    calls: list[object] = []
    expected_layout = object()
    expected_digest = object()

    def fake_inspect(path):
        assert path == source
        return expected_layout

    def fake_hash(path, *, max_bytes):
        assert path == source
        assert max_bytes == 100
        return expected_digest

    async def run_sync(function, *args):
        calls.append(function)
        return function(*args)

    monkeypatch.setattr(normalization_service, "inspect_bmff", fake_inspect)
    monkeypatch.setattr(normalization_service, "hash_regular_file", fake_hash)
    monkeypatch.setattr(normalization_service.to_thread, "run_sync", run_sync)

    assert await normalization_service._inspect_bmff(source) is expected_layout
    assert await normalization_service._hash_regular_file(source, max_bytes=100) is expected_digest
    assert len(calls) == 2
