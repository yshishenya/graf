from __future__ import annotations

import errno
import os
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from minio.error import S3Error

from twobrain_rec_server.normalization import service as normalization_service
from twobrain_rec_server.normalization.media import MediaPolicyError, copy_regular_file
from twobrain_rec_server.processing import submit as processing_submit
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
        self.released = False
        self.read_sizes: list[int] = []

    def read(self, size: int) -> bytes:
        self.read_sizes.append(size)
        chunk = self.payload[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk

    def close(self) -> None:
        self.closed = True

    def release_conn(self) -> None:
        self.released = True


class _Client:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.uploaded = b""
        self.response = _Response(payload)

    def get_object(self, bucket: str, object_key: str) -> _Response:
        assert bucket == "test"
        assert object_key == "private-key"
        return self.response

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


# Only the transport and injected failure are synthetic; file operations stay real.
def _watch_download(monkeypatch, destination):
    descriptors = []
    unlinks = []
    real_open, real_unlink = os.open, Path.unlink

    def open_file(path, flags, mode=0o777, **kwargs):
        if path == destination:
            assert flags & os.O_EXCL
            assert flags & getattr(os, "O_NOFOLLOW", 0) == getattr(os, "O_NOFOLLOW", 0)
            assert mode == 0o600
        descriptor = real_open(path, flags, mode, **kwargs)
        if path == destination:
            descriptors.append(descriptor)
        return descriptor

    def unlink_file(path, **kwargs):
        if path == destination:
            unlinks.append(path)
        return real_unlink(path, **kwargs)

    monkeypatch.setattr(os, "open", open_file)
    monkeypatch.setattr(Path, "unlink", unlink_file)
    return descriptors, unlinks


def _assert_transfer_released(storage, descriptors):
    assert storage.client.response.closed
    assert storage.client.response.released
    for descriptor in descriptors:
        with pytest.raises(OSError) as error:
            os.fstat(descriptor)
        assert error.value.errno == errno.EBADF


@pytest.mark.parametrize(
    ("leaf", "failure"),
    [("regular", None), ("symlink", None)]
    + [
        (leaf, failure)
        for leaf in ("regular", "symlink", "absent")
        for failure in (errno.ENOSPC, errno.EACCES)
    ],
)
def test_verified_download_preserves_destination_before_create(
    tmp_path,
    monkeypatch,
    leaf,
    failure,
):
    payload = b"synthetic-download"
    storage = _storage(payload)
    destination, target = tmp_path / "destination", tmp_path / "target"
    target.write_bytes(b"synthetic-existing")
    if leaf == "regular":
        destination.write_bytes(b"synthetic-existing")
    elif leaf == "symlink":
        destination.symlink_to(target)
    previous = destination.lstat() if leaf != "absent" else None
    target_stat = target.stat()
    descriptors, unlinks = _watch_download(monkeypatch, destination)
    if failure is not None:
        real_open = os.open

        def fail_create(path, *args, **kwargs):
            if path == destination:
                raise OSError(failure, "synthetic create failure")
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr(os, "open", fail_create)
    with pytest.raises(StorageTransferError) as error:
        storage.download_verified_to_path(
            "private-key",
            destination,
            expected_length=len(payload),
            expected_sha256=sha256(payload).hexdigest(),
            max_bytes=1024,
        )
    assert error.value.reason_code == "temporary_storage_unavailable"
    assert unlinks == []
    assert descriptors == []
    assert storage.client.response.read_sizes == []
    if previous is None:
        assert not destination.exists()
    else:
        assert destination.lstat() == previous
        assert destination.read_bytes() == b"synthetic-existing"
        if leaf == "symlink":
            assert destination.readlink() == target
    assert (target.stat().st_ino, target.stat().st_mode, target.stat().st_mtime_ns) == (
        target_stat.st_ino,
        target_stat.st_mode,
        target_stat.st_mtime_ns,
    )
    assert target.read_bytes() == b"synthetic-existing"
    assert storage.client.payload == payload
    _assert_transfer_released(storage, descriptors)


@pytest.mark.parametrize("chunk_size", [5, None])
def test_verified_download_success_is_bounded_and_releases_resources(
    tmp_path,
    monkeypatch,
    chunk_size,
):
    payload = b"s" * (4 * 1024 * 1024 + 3) if chunk_size is None else b"synthetic"
    storage = _storage(payload)
    destination = tmp_path / "destination"
    descriptors, unlinks = _watch_download(monkeypatch, destination)
    options = {} if chunk_size is None else {"chunk_size": chunk_size}
    assert storage.download_verified_to_path(
        "private-key",
        destination,
        expected_length=len(payload),
        expected_sha256=sha256(payload).hexdigest(),
        max_bytes=len(payload),
        **options,
    ) == len(payload)
    assert destination.read_bytes() == payload
    assert destination.stat().st_mode & 0o777 == 0o600
    assert unlinks == []
    assert len(descriptors) == 1
    assert all(
        0 < size <= (chunk_size or 4 * 1024 * 1024) for size in storage.client.response.read_sizes
    )
    assert len(storage.client.response.read_sizes) > 1
    assert storage.client.payload == payload
    _assert_transfer_released(storage, descriptors)


@pytest.mark.parametrize("failure", ["write", "fsync", "short", "extra", "max", "digest"])
def test_verified_download_cleans_only_created_partial(tmp_path, monkeypatch, failure):
    payload = b"synthetic-download"
    storage = _storage(payload)
    destination = tmp_path / "destination"
    descriptors, unlinks = _watch_download(monkeypatch, destination)
    expected_length = len(payload) + (
        1 if failure == "short" else -1 if failure in {"extra", "max"} else 0
    )
    if failure in {"write", "fsync"}:
        real_write = os.write

        def fail_io(*args):
            if failure == "write":
                real_write(args[0], args[1][:1])
            raise OSError(errno.ENOSPC, "synthetic post-create failure")

        monkeypatch.setattr(os, failure, fail_io)
    with pytest.raises(StorageTransferError) as error:
        storage.download_verified_to_path(
            "private-key",
            destination,
            expected_length=expected_length,
            expected_sha256="0" * 64 if failure == "digest" else sha256(payload).hexdigest(),
            max_bytes=expected_length if failure == "max" else 1024,
            chunk_size=5,
        )
    assert error.value.reason_code == (
        "temporary_storage_unavailable" if failure in {"write", "fsync"} else "source_mismatch"
    )
    assert not destination.exists()
    assert unlinks == [destination]
    assert len(descriptors) == 1
    assert storage.client.payload == payload
    _assert_transfer_released(storage, descriptors)


@pytest.mark.parametrize(
    "consumer",
    ["async", "normalization_async", "normalization_sync", "submit_async", "submit_sync"],
)
@pytest.mark.parametrize("scenario", ["success", "collision", "missing", "digest", "unavailable"])
@pytest.mark.anyio
async def test_verified_download_shared_callers_keep_preservation_and_errors(
    tmp_path,
    monkeypatch,
    consumer,
    scenario,
):
    payload = b"synthetic-download"
    storage = _storage(payload)
    destination = tmp_path / "destination"
    if scenario == "collision":
        destination.write_bytes(b"synthetic-existing")
    descriptors, unlinks = _watch_download(monkeypatch, destination)
    if scenario in {"missing", "unavailable"}:

        def fail_get(*args):
            raise S3Error(
                response=None,
                code="NoSuchKey" if scenario == "missing" else "InternalError",
                message="synthetic",
                resource="synthetic",
                request_id="synthetic",
                host_id="synthetic",
            )

        monkeypatch.setattr(storage.client, "get_object", fail_get)
    digest = "0" * 64 if scenario == "digest" else sha256(payload).hexdigest()
    view = (
        SimpleNamespace(download_verified_to_path=storage.download_verified_to_path)
        if consumer.endswith("_sync")
        else storage
    )

    async def run():
        if consumer == "async":
            await storage.download_verified_to_path_async(
                "private-key",
                destination,
                expected_length=len(payload),
                expected_sha256=digest,
                max_bytes=len(payload),
            )
        elif consumer.startswith("normalization"):
            await normalization_service._download_verified_artifact(
                view,
                SimpleNamespace(
                    storage_object_key="private-key", byte_length=len(payload), sha256=digest
                ),
                destination,
                max_bytes=len(payload),
            )
        else:
            await processing_submit._stage_artifact(
                view,
                "private-key",
                destination,
                expected_bytes=len(payload),
                expected_sha256=digest,
            )

    if scenario == "success":
        await run()
        assert destination.read_bytes() == payload
        assert len(descriptors) == 1
        assert unlinks == []
    else:
        if consumer.startswith("submit"):
            exception = (
                processing_submit.ArtifactStagingError
                if scenario in {"missing", "digest"}
                else processing_submit.TempStorageUnavailableError
            )
        else:
            exception = StorageTransferError
        with pytest.raises(exception) as error:
            await run()
        if consumer.startswith("submit"):
            expected = {
                "missing": "storage_object_missing",
                "digest": "storage_object_digest_mismatch",
            }.get(
                scenario,
                processing_submit.PROCESSING_TEMP_STORAGE_UNAVAILABLE,
            )
            assert expected in str(error.value)
        else:
            assert (
                error.value.reason_code
                == {
                    "collision": "temporary_storage_unavailable",
                    "missing": "source_missing",
                    "digest": "source_mismatch",
                    "unavailable": "storage_unavailable",
                }[scenario]
            )
        if scenario == "collision":
            assert destination.read_bytes() == b"synthetic-existing"
            assert unlinks == []
        else:
            assert not destination.exists()
    if scenario not in {"missing", "unavailable"}:
        _assert_transfer_released(storage, descriptors)
    assert storage.client.payload == payload


@pytest.mark.parametrize("invalid", ["length", "digest", "chunk"])
def test_verified_download_invalid_input_preserves_existing_leaf(tmp_path, invalid):
    storage = _storage(b"synthetic")
    destination = tmp_path / "destination"
    destination.write_bytes(b"synthetic-existing")
    with pytest.raises(StorageTransferError) as error:
        storage.download_verified_to_path(
            "private-key",
            destination,
            expected_length=0 if invalid == "length" else 9,
            expected_sha256="invalid" if invalid == "digest" else sha256(b"synthetic").hexdigest(),
            max_bytes=1024,
            chunk_size=0 if invalid == "chunk" else 5,
        )
    assert error.value.reason_code == "source_mismatch"
    assert destination.read_bytes() == b"synthetic-existing"
    assert not storage.client.response.closed
    assert not storage.client.response.released
    assert storage.client.response.read_sizes == []
