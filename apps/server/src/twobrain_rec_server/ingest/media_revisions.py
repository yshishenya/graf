from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import MediaRevision
from twobrain_rec_server.domain.statuses import MediaRevisionSourceKind, MediaRevisionStatus


class MediaRevisionFingerprintConflict(ValueError):
    pass


def initial_local_media_revision_id(local_recording_id: str) -> str:
    return f"{local_recording_id}--initial"


def normalize_initial_local_media_revision_id(local_recording_id: str, local_media_revision_id: str | None) -> str:
    return local_media_revision_id or initial_local_media_revision_id(local_recording_id)


def initial_media_revision_id(existing_id: UUID | None = None) -> UUID:
    return existing_id or uuid4()


def initial_media_revision_status() -> MediaRevisionStatus:
    return MediaRevisionStatus.PENDING_UPLOAD


def initial_media_revision_source_kind() -> MediaRevisionSourceKind:
    return MediaRevisionSourceKind.INITIAL_RECORDING


def track_sha256_by_role(tracks: Iterable[object]) -> dict[str, str]:
    by_role: dict[str, str] = {}
    for track in tracks:
        if isinstance(track, Mapping):
            role = str(track["track_role"])
            digest = str(track["sha256"])
        else:
            role_value = track.track_role
            role = str(getattr(role_value, "value", role_value))
            digest = str(track.sha256)
        by_role[role] = digest
    return by_role


def ensure_media_revision_fingerprint_is_immutable(
    *,
    existing_manifest_sha256: str | None,
    existing_track_sha256_by_role: dict[str, str] | None,
    new_manifest_sha256: str,
    new_track_sha256_by_role: dict[str, str],
) -> None:
    if existing_manifest_sha256 is not None and existing_manifest_sha256 != new_manifest_sha256:
        raise MediaRevisionFingerprintConflict("manifest_sha256_changed")
    if existing_track_sha256_by_role and existing_track_sha256_by_role != new_track_sha256_by_role:
        raise MediaRevisionFingerprintConflict("track_sha256_by_role_changed")


async def mark_media_revision_accepted(
    db: AsyncSession | None,
    *,
    media_revision_id: UUID | None,
    manifest_sha256: str,
    tracks: Iterable[object],
) -> None:
    if db is None or media_revision_id is None:
        return
    revision = await db.get(MediaRevision, media_revision_id)
    if revision is None:
        return
    new_track_sha256_by_role = track_sha256_by_role(tracks)
    if revision.status == MediaRevisionStatus.ACCEPTED.value and revision.immutable:
        ensure_media_revision_fingerprint_is_immutable(
            existing_manifest_sha256=revision.manifest_sha256,
            existing_track_sha256_by_role=revision.track_sha256_by_role,
            new_manifest_sha256=manifest_sha256,
            new_track_sha256_by_role=new_track_sha256_by_role,
        )
    revision.status = MediaRevisionStatus.ACCEPTED.value
    revision.manifest_sha256 = manifest_sha256
    revision.track_sha256_by_role = new_track_sha256_by_role
    revision.immutable = True
    revision.accepted_at = revision.accepted_at or datetime.now(UTC)
    await db.commit()
