from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.catalog import classify_storage_threshold
from twobrain_rec_server.db.models import StorageReservation as StorageReservationRow
from twobrain_rec_server.db.models import TrackArtifact, Workspace

CANONICAL_PLAYBACK_PROFILE = "review_m4a_aac_lc_48k_mono_64k_v1"
CANONICAL_PLAYBACK_FILENAME = "meeting-review.m4a"


@dataclass(slots=True)
class StorageReservation:
    reservation_id: str
    declared_bytes: int
    state: str = "active"
    committed_bytes: int = 0


@dataclass(frozen=True, slots=True)
class StorageProjection:
    used_bytes: int
    reserved_bytes: int
    capacity_bytes: int

    def __post_init__(self) -> None:
        if self.used_bytes < 0 or self.reserved_bytes < 0 or self.capacity_bytes <= 0:
            raise ValueError("storage projection values are invalid")

    @property
    def available_bytes(self) -> int:
        return max(0, self.capacity_bytes - self.used_bytes - self.reserved_bytes)

    @property
    def threshold(self) -> str:
        return classify_storage_threshold(used_bytes=self.used_bytes, capacity_bytes=self.capacity_bytes)


class StorageAdmissionError(RuntimeError):
    pass


def is_chargeable_playback_artifact(
    *,
    track_role: str,
    status: str,
    normalization_profile_version: str | None,
    storage_object_key: str,
) -> bool:
    """Return whether one artifact contributes to customer storage.

    The filename comparison is path-segment exact.  A similarly suffixed
    provider temporary (for example ``meeting-review.m4a.tmp``) is never
    chargeable, and deleted/superseded artifacts release quota immediately.
    """

    return (
        track_role == "playback"
        and status == "stored"
        and normalization_profile_version == CANONICAL_PLAYBACK_PROFILE
        and storage_object_key.rsplit("/", 1)[-1] == CANONICAL_PLAYBACK_FILENAME
    )


async def project_active_playback_storage(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    capacity_bytes: int,
    reserved_bytes: int = 0,
) -> StorageProjection:
    """Project quota from canonical normalized playback artifacts only."""
    if capacity_bytes <= 0:
        raise ValueError("storage capacity must be positive")
    if reserved_bytes < 0:
        raise ValueError("reserved bytes cannot be negative")
    used = await db.scalar(
        select(func.coalesce(func.sum(TrackArtifact.byte_length), 0)).where(
            TrackArtifact.workspace_id == workspace_id,
            TrackArtifact.track_role == "playback",
            TrackArtifact.status == "stored",
            TrackArtifact.normalization_profile_version == CANONICAL_PLAYBACK_PROFILE,
            TrackArtifact.storage_object_key.endswith("/meeting-review.m4a"),
        )
    )
    return StorageProjection(
        used_bytes=int(used or 0),
        reserved_bytes=max(0, reserved_bytes),
        capacity_bytes=capacity_bytes,
    )


async def logically_release_playback_quota(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> int:
    """Remove a meeting's playback bytes from quota before object purge.

    Deletion owns the physical object purge separately.  Marking the canonical
    artifact as ``deleted`` under the meeting tombstone releases user quota
    immediately while keeping its object key available to the purge journal.
    """

    artifacts = list(
        await db.scalars(
            select(TrackArtifact)
            .where(
                TrackArtifact.workspace_id == workspace_id,
                TrackArtifact.meeting_id == meeting_id,
                TrackArtifact.track_role == "playback",
                TrackArtifact.status == "stored",
                TrackArtifact.normalization_profile_version == CANONICAL_PLAYBACK_PROFILE,
            )
            .with_for_update()
        )
    )
    released = 0
    for artifact in artifacts:
        if artifact.storage_object_key.rsplit("/", 1)[-1] != CANONICAL_PLAYBACK_FILENAME:
            continue
        released += artifact.byte_length
        artifact.status = "deleted"
        artifact.normalization_profile_version = None
        artifact.validated_at = None
        artifact.derivation_kind = None
        artifact.source_fingerprint_sha256 = None
        artifact.validation_version = None
    await db.flush()
    return released


def admit_storage(projection: StorageProjection, incoming_bytes: int) -> None:
    if incoming_bytes <= 0:
        raise ValueError("incoming bytes must be positive")
    if projection.used_bytes + projection.reserved_bytes + incoming_bytes > projection.capacity_bytes:
        raise StorageAdmissionError("storage capacity exceeded")


def commit_object_bytes(*, reservation: StorageReservation, actual_bytes: int) -> int:
    """Commit exact object-stat bytes; never silently charges an overrun."""
    if reservation.state != "active":
        raise ValueError("reservation is not active")
    if actual_bytes <= 0:
        raise ValueError("object bytes must be positive")
    if actual_bytes > reservation.declared_bytes:
        raise StorageAdmissionError("object stat exceeds reservation")
    reservation.committed_bytes = actual_bytes
    reservation.state = "committed"
    return actual_bytes


def release_storage(reservation: StorageReservation) -> None:
    if reservation.state == "active":
        reservation.state = "released"


async def _active_reserved_bytes(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    now: datetime,
) -> int:
    reserved = await db.scalar(
        select(
            func.coalesce(
                func.sum(StorageReservationRow.declared_bytes - StorageReservationRow.committed_bytes),
                0,
            )
        ).where(
            StorageReservationRow.workspace_id == workspace_id,
            StorageReservationRow.state == "active",
            (StorageReservationRow.expires_at.is_(None) | (StorageReservationRow.expires_at > now)),
        )
    )
    return max(0, int(reserved or 0))


async def reserve_storage(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    reservation_key: str,
    declared_bytes: int,
    capacity_bytes: int,
    now: datetime | None = None,
    expires_at: datetime | None = None,
) -> StorageReservationRow:
    """Atomically reserve playback capacity with idempotent admission.

    A workspace row lock serializes reservations even when there are no
    existing reservation rows to lock. Object bytes remain authoritative at
    commit time, so an object-stat mismatch never silently overcharges.
    """
    if declared_bytes <= 0 or not reservation_key.strip():
        raise ValueError("storage reservation is invalid")
    now = now or datetime.now(UTC)
    workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_id).with_for_update())
    if workspace is None:
        raise ValueError("workspace is missing")
    existing = await db.scalar(
        select(StorageReservationRow)
        .where(
            StorageReservationRow.workspace_id == workspace_id,
            StorageReservationRow.idempotency_key == reservation_key,
        )
        .with_for_update()
    )
    if existing is not None:
        return existing
    reserved = await _active_reserved_bytes(db, workspace_id=workspace_id, now=now)
    projection = await project_active_playback_storage(
        db,
        workspace_id=workspace_id,
        capacity_bytes=capacity_bytes,
        reserved_bytes=reserved,
    )
    admit_storage(projection, declared_bytes)
    reservation = StorageReservationRow(
        workspace_id=workspace_id,
        idempotency_key=reservation_key,
        declared_bytes=declared_bytes,
        expires_at=expires_at or now + timedelta(minutes=15),
    )
    db.add(reservation)
    await db.flush()
    return reservation


async def commit_storage_reservation(
    db: AsyncSession,
    *,
    reservation_id: UUID,
    artifact_id: UUID | None,
    actual_bytes: int,
) -> int:
    """Commit exact normalized object-stat bytes to a reservation."""
    reservation = await db.scalar(
        select(StorageReservationRow).where(StorageReservationRow.id == reservation_id).with_for_update()
    )
    if reservation is None:
        raise ValueError("storage reservation is missing")
    if reservation.state == "committed":
        return reservation.committed_bytes
    if reservation.state != "active":
        raise ValueError("storage reservation is not active")
    if actual_bytes <= 0:
        raise ValueError("object bytes must be positive")
    if actual_bytes > reservation.declared_bytes:
        raise StorageAdmissionError("object stat exceeds reservation")
    reservation.committed_bytes = actual_bytes
    reservation.artifact_id = artifact_id
    reservation.state = "committed"
    await db.flush()
    return actual_bytes


async def release_storage_reservation(
    db: AsyncSession,
    *,
    reservation_id: UUID,
) -> bool:
    """Release an active reservation without changing playback usage."""
    reservation = await db.scalar(
        select(StorageReservationRow).where(StorageReservationRow.id == reservation_id).with_for_update()
    )
    if reservation is None or reservation.state != "active":
        return False
    reservation.state = "released"
    await db.flush()
    return True


async def release_expired_storage_reservations(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    now: datetime,
) -> int:
    """Close 15-minute transient reservations so capacity becomes reusable."""
    rows = list(
        await db.scalars(
            select(StorageReservationRow)
            .where(
                StorageReservationRow.workspace_id == workspace_id,
                StorageReservationRow.state == "active",
                StorageReservationRow.expires_at.is_not(None),
                StorageReservationRow.expires_at <= now,
            )
            .with_for_update()
        )
    )
    for reservation in rows:
        reservation.state = "released"
    await db.flush()
    return len(rows)
