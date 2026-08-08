import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from twobrain_rec_server.billing.catalog import (
    ADDON_CAPACITY_BYTES,
    PERSONAL_STORAGE_BYTES,
    classify_storage_threshold,
    storage_capacity_bytes,
)
from twobrain_rec_server.billing.storage import (
    CANONICAL_PLAYBACK_FILENAME,
    CANONICAL_PLAYBACK_PROFILE,
    StorageAdmissionError,
    StorageProjection,
    StorageReservation,
    admit_storage,
    commit_object_bytes,
    commit_storage_reservation,
    is_chargeable_playback_artifact,
    release_storage,
    reserve_storage,
)


class _ScalarQueueSession:
    def __init__(self, *rows: object) -> None:
        self.rows = list(rows)
        self.flushed = False

    async def scalar(self, _query: object) -> object:
        return self.rows.pop(0)

    async def flush(self) -> None:
        self.flushed = True


def test_storage_projection_uses_exact_decimal_capacities_and_thresholds() -> None:
    projection = StorageProjection(used_bytes=1_600_000_000, reserved_bytes=0, capacity_bytes=PERSONAL_STORAGE_BYTES)
    assert projection.threshold == "80%"
    assert StorageProjection(used_bytes=1_900_000_000, reserved_bytes=0, capacity_bytes=PERSONAL_STORAGE_BYTES).threshold == "95%"
    assert classify_storage_threshold(used_bytes=PERSONAL_STORAGE_BYTES, capacity_bytes=PERSONAL_STORAGE_BYTES) == "full"
    assert storage_capacity_bytes("personal", ADDON_CAPACITY_BYTES[0]) == ADDON_CAPACITY_BYTES[0]


def test_storage_reservation_rejects_admission_and_object_stat_overrun() -> None:
    with pytest.raises(StorageAdmissionError):
        admit_storage(StorageProjection(100, 50, 120), 1)
    reservation = StorageReservation("r1", 100)
    with pytest.raises(StorageAdmissionError):
        commit_object_bytes(reservation=reservation, actual_bytes=101)


def test_storage_projection_is_bounded_by_capacity() -> None:
    projection = StorageProjection(used_bytes=200, reserved_bytes=10, capacity_bytes=250)
    assert projection.available_bytes == 40


def test_storage_reservation_release_is_idempotent_and_capacity_validation_is_fail_closed() -> None:
    reservation = StorageReservation("r1", declared_bytes=100)
    release_storage(reservation)
    release_storage(reservation)
    assert reservation.state == "released"
    with pytest.raises(ValueError):
        StorageProjection(used_bytes=0, reserved_bytes=0, capacity_bytes=0)


def test_storage_admission_allows_exact_boundary_after_reserved_bytes() -> None:
    projection = StorageProjection(used_bytes=179, reserved_bytes=20, capacity_bytes=200)
    admit_storage(projection, 1)
    with pytest.raises(StorageAdmissionError):
        admit_storage(projection, 2)


def test_storage_commit_records_verified_smaller_object_without_rounding() -> None:
    reservation = StorageReservation("verified-smaller", declared_bytes=100)

    assert commit_object_bytes(reservation=reservation, actual_bytes=73) == 73
    assert reservation.committed_bytes == 73
    assert reservation.state == "committed"


def test_only_active_canonical_playback_object_counts_toward_customer_quota() -> None:
    common = {
        "track_role": "playback",
        "normalization_profile_version": CANONICAL_PLAYBACK_PROFILE,
        "storage_object_key": f"workspace/meeting/{CANONICAL_PLAYBACK_FILENAME}",
    }
    assert is_chargeable_playback_artifact(status="stored", **common)
    assert not is_chargeable_playback_artifact(status="deleted", **common)
    assert not is_chargeable_playback_artifact(
        status="stored",
        **{**common, "storage_object_key": common["storage_object_key"] + ".tmp"},
    )
    assert not is_chargeable_playback_artifact(
        status="stored", **{**common, "track_role": "media"}
    )


def test_transcription_and_legacy_source_filenames_never_count_as_playback_quota() -> None:
    for filename in ("meeting-transcription.wav", "mic.wav", "incoming.wav"):
        assert not is_chargeable_playback_artifact(
            track_role="playback",
            status="stored",
            normalization_profile_version=CANONICAL_PLAYBACK_PROFILE,
            storage_object_key=f"workspace/meeting/{filename}",
        )


def test_storage_reservation_rejects_expiry_at_or_before_admission() -> None:
    now = datetime(2026, 8, 7, 9, 0, tzinfo=UTC)

    async def reserve() -> None:
        with pytest.raises(ValueError, match="expiry must be in the future"):
            await reserve_storage(
                _ScalarQueueSession(),
                workspace_id=uuid4(),
                reservation_key="expired",
                declared_bytes=1,
                capacity_bytes=10,
                now=now,
                expires_at=now,
            )

    asyncio.run(reserve())


def test_storage_commit_requires_verified_canonical_artifact_and_fresh_reservation() -> None:
    now = datetime(2026, 8, 7, 9, 0, tzinfo=UTC)
    workspace_id = uuid4()
    reservation_id = uuid4()
    artifact_id = uuid4()
    reservation = SimpleNamespace(
        id=reservation_id,
        workspace_id=workspace_id,
        state="active",
        expires_at=now + timedelta(minutes=1),
        committed_bytes=0,
        declared_bytes=100,
        artifact_id=None,
    )
    unverified_artifact = SimpleNamespace(
        id=artifact_id,
        workspace_id=workspace_id,
        track_role="media",
        status="stored",
        normalization_profile_version=None,
        storage_object_key="workspace/meeting/meeting-transcription.wav",
        byte_length=80,
    )

    async def commit() -> None:
        with pytest.raises(StorageAdmissionError, match="verified canonical playback"):
            await commit_storage_reservation(
                _ScalarQueueSession(reservation, unverified_artifact),
                reservation_id=reservation_id,
                artifact_id=artifact_id,
                actual_bytes=80,
                now=now,
            )

    asyncio.run(commit())
    assert reservation.committed_bytes == 0


def test_storage_commit_rejects_expired_reservation_before_artifact_lookup() -> None:
    now = datetime(2026, 8, 7, 9, 0, tzinfo=UTC)
    reservation = SimpleNamespace(
        id=uuid4(),
        workspace_id=uuid4(),
        state="active",
        expires_at=now - timedelta(seconds=1),
        committed_bytes=0,
        declared_bytes=100,
        artifact_id=None,
    )

    async def commit() -> None:
        with pytest.raises(StorageAdmissionError, match="expired"):
            await commit_storage_reservation(
                _ScalarQueueSession(reservation),
                reservation_id=reservation.id,
                artifact_id=uuid4(),
                actual_bytes=80,
                now=now,
            )

    asyncio.run(commit())


def test_storage_commit_accepts_only_exact_verified_playback_bytes() -> None:
    now = datetime(2026, 8, 7, 9, 0, tzinfo=UTC)
    workspace_id = uuid4()
    reservation_id = uuid4()
    artifact_id = uuid4()
    reservation = SimpleNamespace(
        id=reservation_id,
        workspace_id=workspace_id,
        state="active",
        expires_at=now + timedelta(minutes=1),
        committed_bytes=0,
        declared_bytes=100,
        artifact_id=None,
    )
    artifact = SimpleNamespace(
        id=artifact_id,
        workspace_id=workspace_id,
        track_role="playback",
        status="stored",
        normalization_profile_version=CANONICAL_PLAYBACK_PROFILE,
        storage_object_key="workspace/meeting/meeting-review.m4a",
        byte_length=73,
    )

    async def commit() -> None:
        db = _ScalarQueueSession(reservation, artifact)
        assert await commit_storage_reservation(
            db,
            reservation_id=reservation_id,
            artifact_id=artifact_id,
            actual_bytes=73,
            now=now,
        ) == 73
        assert db.flushed is True

    asyncio.run(commit())
    assert reservation.committed_bytes == 73
    assert reservation.artifact_id == artifact_id
    assert reservation.state == "committed"
