from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import MediaRevision
from twobrain_rec_server.domain.statuses import MediaRevisionSourceKind, MediaRevisionStatus


class MediaRevisionFingerprintConflict(ValueError):
    pass


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


async def _load_media_revision(
    db: AsyncSession,
    media_revision_id: UUID,
    *,
    for_update: bool,
) -> MediaRevision | None:
    statement = (
        select(MediaRevision)
        .where(MediaRevision.id == media_revision_id)
        .execution_options(populate_existing=True)
    )
    if for_update:
        statement = statement.with_for_update()
    result = await db.execute(statement)
    return result.scalar_one_or_none()


def initial_local_media_revision_id(local_recording_id: str) -> str:
    return f"{local_recording_id}--initial"


def normalize_initial_local_media_revision_id(local_recording_id: str, local_media_revision_id: str | None) -> str:
    return local_media_revision_id or initial_local_media_revision_id(local_recording_id)


def initial_media_revision_id(existing_id: UUID | None = None) -> UUID:
    return existing_id or uuid4()


def initial_media_revision_status() -> MediaRevisionStatus:
    return MediaRevisionStatus.PENDING_UPLOAD


def initial_media_revision_source_kind() -> MediaRevisionSourceKind:
    # This is the legacy API default for older clients. New first-party v5
    # uploads explicitly declare INITIAL_MIXED_RECORDING in their request.
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
        if role != "playback":
            by_role[role] = digest
    return by_role


def authoritative_track_roles(
    source_kind: MediaRevisionSourceKind | str,
) -> tuple[str, ...]:
    source_kind_value = str(getattr(source_kind, "value", source_kind))
    if source_kind_value == MediaRevisionSourceKind.INITIAL_RECORDING.value:
        # Historical-only dual source identity; do not use for new captures.
        return ("microphone", "system")
    if source_kind_value in {
        MediaRevisionSourceKind.INITIAL_MIXED_RECORDING.value,
        MediaRevisionSourceKind.MANUAL_UPLOAD.value,
        MediaRevisionSourceKind.LOCAL_TRIM.value,
        MediaRevisionSourceKind.REPLACE.value,
        MediaRevisionSourceKind.RESTORE.value,
        MediaRevisionSourceKind.REPROCESS.value,
        MediaRevisionSourceKind.VIDEO_CAPTURE.value,
    }:
        return ("media",)
    raise ValueError("unsupported media revision source kind")


def authoritative_track_sha256_by_role(
    *,
    source_kind: MediaRevisionSourceKind | str,
    digests_by_role: Mapping[str, str],
) -> dict[str, str]:
    authoritative_roles = authoritative_track_roles(source_kind)
    missing = [role for role in authoritative_roles if role not in digests_by_role]
    if missing:
        raise ValueError("accepted media revision is missing authoritative source digests")
    return {role: str(digests_by_role[role]) for role in authoritative_roles}


def source_fingerprint_sha256(
    *,
    media_revision_id: UUID,
    source_kind: MediaRevisionSourceKind | str,
    manifest_sha256: str,
    track_sha256_by_role: Mapping[str, str],
    duration_seconds: int | None,
) -> str:
    source_kind_value = str(getattr(source_kind, "value", source_kind))
    authoritative = authoritative_track_sha256_by_role(
        source_kind=source_kind_value,
        digests_by_role=track_sha256_by_role,
    )
    canonical_value = {
        "duration_seconds": duration_seconds,
        "manifest_sha256": manifest_sha256,
        "media_revision_id": str(media_revision_id),
        "source_kind": source_kind_value,
        "tracks": [
            {"role": role, "sha256": authoritative[role]}
            for role in sorted(authoritative)
        ],
    }
    encoded = json.dumps(
        canonical_value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def source_fingerprint_for_revision(revision: MediaRevision) -> str:
    """Return a fingerprint only for an immutable, fully attested revision.

    Revision-scoped processing and generation must fail closed.  The
    ``revision:<id>`` fallback is intentionally not valid here; it is kept
    only for explicit legacy rows that have no media revision at all.
    """
    if (
        revision.status != MediaRevisionStatus.ACCEPTED.value
        or not revision.immutable
        or not _is_sha256(revision.manifest_sha256)
    ):
        raise ValueError("media revision is not an immutable accepted source")
    digests = revision.track_sha256_by_role or {}
    try:
        authoritative = authoritative_track_sha256_by_role(
            source_kind=revision.source_kind,
            digests_by_role=digests,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("media revision is missing authoritative source digests") from exc
    if any(not _is_sha256(digest) for digest in authoritative.values()):
        raise ValueError("media revision has invalid authoritative source digests")
    return source_fingerprint_sha256(
        media_revision_id=revision.id,
        source_kind=revision.source_kind,
        manifest_sha256=revision.manifest_sha256,
        track_sha256_by_role=digests,
        duration_seconds=revision.duration_seconds,
    )


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


async def ensure_media_revision_acceptance_is_safe(
    db: AsyncSession | None,
    *,
    media_revision_id: UUID | None,
    manifest_sha256: str,
    tracks: Iterable[object],
) -> None:
    """Check an accepted revision before any new storage object is materialized."""
    if db is None or media_revision_id is None:
        return
    revision = await _load_media_revision(db, media_revision_id, for_update=True)
    if revision is None:
        return
    if revision.status == MediaRevisionStatus.ACCEPTED.value and revision.immutable:
        ensure_media_revision_fingerprint_is_immutable(
            existing_manifest_sha256=revision.manifest_sha256,
            existing_track_sha256_by_role=revision.track_sha256_by_role,
            new_manifest_sha256=manifest_sha256,
            new_track_sha256_by_role=track_sha256_by_role(tracks),
        )


async def mark_media_revision_accepted(
    db: AsyncSession | None,
    *,
    media_revision_id: UUID | None,
    manifest_sha256: str,
    tracks: Iterable[object],
    commit: bool = True,
) -> None:
    if db is None or media_revision_id is None:
        return
    revision = await _load_media_revision(db, media_revision_id, for_update=True)
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
    if commit:
        await db.commit()
    else:
        await db.flush()
