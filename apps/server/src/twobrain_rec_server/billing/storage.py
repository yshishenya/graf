from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.catalog import classify_storage_threshold
from twobrain_rec_server.db.models import TrackArtifact


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

    @property
    def available_bytes(self) -> int:
        return max(0, self.capacity_bytes - self.used_bytes - self.reserved_bytes)

    @property
    def threshold(self) -> str:
        return classify_storage_threshold(used_bytes=self.used_bytes, capacity_bytes=self.capacity_bytes)


class StorageAdmissionError(RuntimeError):
    pass


async def project_active_playback_storage(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    capacity_bytes: int,
    reserved_bytes: int = 0,
) -> StorageProjection:
    """Project quota from canonical normalized playback artifacts only."""
    used = await db.scalar(
        select(func.coalesce(func.sum(TrackArtifact.byte_length), 0)).where(
            TrackArtifact.workspace_id == workspace_id,
            TrackArtifact.track_role == "playback",
            TrackArtifact.status == "stored",
            TrackArtifact.normalization_profile_version == "review_m4a_aac_lc_48k_mono_64k_v1",
            TrackArtifact.storage_object_key.endswith("meeting-review.m4a"),
        )
    )
    return StorageProjection(
        used_bytes=int(used or 0),
        reserved_bytes=max(0, reserved_bytes),
        capacity_bytes=capacity_bytes,
    )


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
