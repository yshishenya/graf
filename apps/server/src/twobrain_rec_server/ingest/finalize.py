import tempfile
from collections.abc import Iterator
from contextlib import suppress
from datetime import UTC, datetime
from hashlib import sha256
from typing import BinaryIO, NoReturn
from uuid import UUID

from anyio import to_thread
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import TrackDescriptor
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.domain.statuses import (
    MediaRevisionStatus,
    MeetingStatus,
    ProcessingStatus,
    TrackRole,
    UploadSessionStatus,
)
from twobrain_rec_server.ingest import store as store_module
from twobrain_rec_server.ingest.audit import record_audit_event
from twobrain_rec_server.ingest.lifecycle_guards import ensure_upload_session_mutable
from twobrain_rec_server.ingest.manifest import ManifestValidationError, validate_required_tracks
from twobrain_rec_server.ingest.media_revisions import (
    MediaRevisionFingerprintConflict,
    mark_media_revision_accepted,
)
from twobrain_rec_server.ingest.parts import get_session_for_tenant
from twobrain_rec_server.ingest.store import (
    MeetingRecord,
    UploadPartRecord,
    UploadSessionRecord,
    persist_audit_event,
    persist_finalized_tracks,
    persist_meeting,
    persist_upload_session,
)
from twobrain_rec_server.normalization.service import upsert_playback_normalization_job
from twobrain_rec_server.storage.object_keys import build_final_artifact_prefix

FINALIZE_STREAM_CHUNK_BYTES = 4 * 1024 * 1024


async def _persist_degraded_finalize_failure(
    *,
    db: AsyncSession | None,
    tenant_scope: TenantScope,
    meeting: MeetingRecord,
    session: UploadSessionRecord,
    code: str,
    title: str,
) -> None:
    meeting.status = MeetingStatus.DEGRADED
    session.status = UploadSessionStatus.DEGRADED
    event = record_audit_event(
        event_type="finalize_degraded",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        upload_session_id=session.id,
        actor_user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
        metadata={"reason_code": code, "reason": title},
    )
    await persist_meeting(db, meeting)
    await persist_upload_session(db, session)
    await persist_audit_event(db, event)


async def _raise_degraded_finalize_problem(
    *,
    db: AsyncSession | None,
    tenant_scope: TenantScope,
    meeting: MeetingRecord,
    session: UploadSessionRecord,
    status: int,
    code: str,
    title: str,
    cause: Exception | None = None,
) -> NoReturn:
    await _persist_degraded_finalize_failure(
        db=db,
        tenant_scope=tenant_scope,
        meeting=meeting,
        session=session,
        code=code,
        title=title,
    )
    problem = ProblemDetail(status=status, code=code, title=title)
    if cause is not None:
        raise problem from cause
    raise problem


def _finalized_track_object_key(*, meeting: MeetingRecord, session: UploadSessionRecord, role: TrackRole) -> str:
    prefix = build_final_artifact_prefix(
        organization_id=session.organization_id,
        workspace_id=session.workspace_id,
        meeting_id=meeting.id,
    )
    media_revision_id = session.media_revision_id or meeting.media_revision_id or session.id
    return f"{prefix}/media-revisions/{media_revision_id}/tracks/{role.value}"


async def _put_storage_stream(storage: object, object_key: str, stream: BinaryIO, byte_length: int) -> None:
    ensure_bucket_async = getattr(storage, "ensure_bucket_async", None)
    if ensure_bucket_async is not None:
        await ensure_bucket_async()
    elif hasattr(storage, "ensure_bucket"):
        await to_thread.run_sync(storage.ensure_bucket)
    put_stream_async = getattr(storage, "put_stream_async", None)
    if put_stream_async is not None:
        await put_stream_async(object_key, stream, byte_length)
        return
    put_stream = getattr(storage, "put_stream", None)
    if put_stream is None:
        raise RuntimeError("storage writer unavailable")
    await to_thread.run_sync(put_stream, object_key, stream, byte_length)


async def _delete_storage_object(storage: object | None, object_key: str) -> None:
    if storage is None:
        return
    delete_object_async = getattr(storage, "delete_object_async", None)
    if delete_object_async is not None:
        await delete_object_async(object_key)
        return
    delete_object = getattr(storage, "delete_object", None)
    if delete_object is not None:
        await to_thread.run_sync(delete_object, object_key)


async def _cleanup_materialized_track_objects(storage: object | None, object_keys: list[str]) -> None:
    for object_key in object_keys:
        with suppress(Exception):
            await _delete_storage_object(storage, object_key)


def _iter_storage_chunks(storage: object, object_key: str) -> Iterator[bytes]:
    iter_object = getattr(storage, "iter_object", None)
    if iter_object is None:
        raise RuntimeError("storage streaming reader unavailable")
    try:
        return iter_object(object_key, chunk_size=FINALIZE_STREAM_CHUNK_BYTES)
    except TypeError:
        return iter_object(object_key)
    except KeyError as exc:
        raise RuntimeError("storage object missing") from exc


def _copy_part_to_stream(
    *,
    storage: object,
    part: UploadPartRecord,
    destination: BinaryIO,
    digest: object,
) -> int:
    copied = 0
    try:
        for chunk in _iter_storage_chunks(storage, part.object_key):
            if not chunk:
                continue
            copied += len(chunk)
            digest.update(chunk)
            destination.write(chunk)
    except KeyError as exc:
        raise RuntimeError("storage object missing") from exc
    except OSError as exc:
        raise RuntimeError("storage unavailable") from exc
    except Exception as exc:
        if isinstance(exc, AssertionError):
            raise
        raise RuntimeError("storage unavailable") from exc
    if copied != part.byte_length:
        raise RuntimeError("storage object size mismatch")
    return copied


async def _copy_part_to_stream_async(
    *,
    storage: object,
    part: UploadPartRecord,
    destination: BinaryIO,
    digest: object,
) -> int:
    return await to_thread.run_sync(
        lambda: _copy_part_to_stream(storage=storage, part=part, destination=destination, digest=digest)
    )


async def _materialize_track_object(
    *,
    meeting: MeetingRecord,
    session: UploadSessionRecord,
    role: TrackRole,
    parts: list[UploadPartRecord],
    storage: object | None,
) -> tuple[str, int, str]:
    ordered_parts = sorted(parts, key=lambda part: part.byte_offset)
    cursor = 0
    for part in ordered_parts:
        if part.byte_offset != cursor:
            raise ValueError("missing_required_parts")
        cursor += part.byte_length
    if len(ordered_parts) == 1:
        part = ordered_parts[0]
        return part.object_key, part.byte_length, part.sha256
    if storage is None:
        raise RuntimeError("storage unavailable")
    digest = sha256()
    object_key = _finalized_track_object_key(meeting=meeting, session=session, role=role)
    try:
        with tempfile.TemporaryFile(mode="w+b") as body:
            byte_length = 0
            for part in ordered_parts:
                byte_length += await _copy_part_to_stream_async(
                    storage=storage,
                    part=part,
                    destination=body,
                    digest=digest,
                )
            body.seek(0)
            await _put_storage_stream(storage, object_key, body, byte_length)
    except OSError as exc:
        with suppress(Exception):
            await _delete_storage_object(storage, object_key)
        raise RuntimeError("temporary storage unavailable") from exc
    except Exception:
        with suppress(Exception):
            await _delete_storage_object(storage, object_key)
        raise
    return object_key, byte_length, digest.hexdigest()


async def finalize_upload(
    *,
    tenant_scope: TenantScope,
    db: AsyncSession | None = None,
    session_id: UUID,
    manifest_sha256: str,
    tracks: list[TrackDescriptor],
    storage: object | None = None,
) -> tuple[object, object]:
    session = await get_session_for_tenant(session_id, tenant_scope, db)
    await ensure_upload_session_mutable(db=db, session=session, event_type="expired")
    meeting = store_module.store.meetings[session.meeting_id]
    try:
        validate_required_tracks(tracks)
    except ManifestValidationError as exc:
        await _raise_degraded_finalize_problem(
            db=db,
            tenant_scope=tenant_scope,
            meeting=meeting,
            session=session,
            status=400,
            code="manifest_validation_failed",
            title=str(exc),
            cause=exc,
        )

    tracks_by_role = {track.track_role: track for track in tracks}
    if len(tracks_by_role) != len(tracks):
        await _raise_degraded_finalize_problem(
            db=db,
            tenant_scope=tenant_scope,
            meeting=meeting,
            session=session,
            status=400,
            code="duplicate_track_role",
            title="Duplicate track role in finalize manifest",
        )
    manifest_track = tracks_by_role.get(TrackRole.MANIFEST)
    if manifest_track is None or manifest_track.sha256 != manifest_sha256:
        await _raise_degraded_finalize_problem(
            db=db,
            tenant_scope=tenant_scope,
            meeting=meeting,
            session=session,
            status=400,
            code="manifest_checksum_mismatch",
            title="Manifest checksum mismatch",
        )

    uploaded_roles = {role for role, _part_number in session.parts}
    expected_roles = {track.track_role for track in tracks}
    configured_roles = set(session.expected_track_roles)
    if expected_roles != configured_roles:
        await _raise_degraded_finalize_problem(
            db=db,
            tenant_scope=tenant_scope,
            meeting=meeting,
            session=session,
            status=409,
            code="expected_track_role_mismatch",
            title="Finalize track roles do not match expected track roles",
        )
    if not expected_roles.issubset(uploaded_roles):
        await _raise_degraded_finalize_problem(
            db=db,
            tenant_scope=tenant_scope,
            meeting=meeting,
            session=session,
            status=409,
            code="missing_required_parts",
            title="Missing required upload parts",
        )

    finalized_track_object_keys: dict[TrackRole, str] = {}
    materialized_track_object_keys: list[str] = []
    for role, track in tracks_by_role.items():
        role_parts = [part for (part_role, _part_number), part in session.parts.items() if part_role == role]
        if not role_parts:
            await _cleanup_materialized_track_objects(storage, materialized_track_object_keys)
            await _raise_degraded_finalize_problem(
                db=db,
                tenant_scope=tenant_scope,
                meeting=meeting,
                session=session,
                status=409,
                code="missing_required_parts",
                title="Missing required upload parts",
            )
        expected_size = session.expected_track_sizes.get(role)
        if expected_size is not None and expected_size != track.byte_length:
            await _cleanup_materialized_track_objects(storage, materialized_track_object_keys)
            await _raise_degraded_finalize_problem(
                db=db,
                tenant_scope=tenant_scope,
                meeting=meeting,
                session=session,
                status=409,
                code="expected_track_size_mismatch",
                title="Expected track size mismatch",
            )
        try:
            object_key, byte_length, checksum = await _materialize_track_object(
                meeting=meeting,
                session=session,
                role=role,
                parts=role_parts,
                storage=storage,
            )
        except ValueError as exc:
            await _cleanup_materialized_track_objects(storage, materialized_track_object_keys)
            await _raise_degraded_finalize_problem(
                db=db,
                tenant_scope=tenant_scope,
                meeting=meeting,
                session=session,
                status=409,
                code="missing_required_parts",
                title="Missing required upload parts",
                cause=exc,
            )
        except RuntimeError as exc:
            await _cleanup_materialized_track_objects(storage, materialized_track_object_keys)
            await _raise_degraded_finalize_problem(
                db=db,
                tenant_scope=tenant_scope,
                meeting=meeting,
                session=session,
                status=503,
                code="storage_unavailable",
                title="Storage unavailable",
                cause=exc,
            )
        if len(role_parts) > 1:
            materialized_track_object_keys.append(object_key)
        if byte_length != track.byte_length:
            await _cleanup_materialized_track_objects(storage, materialized_track_object_keys)
            await _raise_degraded_finalize_problem(
                db=db,
                tenant_scope=tenant_scope,
                meeting=meeting,
                session=session,
                status=400,
                code="track_length_mismatch",
                title="Track byte length mismatch",
            )
        if checksum != track.sha256:
            await _cleanup_materialized_track_objects(storage, materialized_track_object_keys)
            await _raise_degraded_finalize_problem(
                db=db,
                tenant_scope=tenant_scope,
                meeting=meeting,
                session=session,
                status=400,
                code="track_checksum_mismatch",
                title="Track checksum mismatch",
            )
        finalized_track_object_keys[role] = object_key

    try:
        await mark_media_revision_accepted(
            db,
            media_revision_id=session.media_revision_id or meeting.media_revision_id,
            manifest_sha256=manifest_sha256,
            tracks=tracks,
            commit=False,
        )
    except MediaRevisionFingerprintConflict as exc:
        await _cleanup_materialized_track_objects(storage, materialized_track_object_keys)
        await _raise_degraded_finalize_problem(
            db=db,
            tenant_scope=tenant_scope,
            meeting=meeting,
            session=session,
            status=409,
            code="media_revision_fingerprint_conflict",
            title="Accepted media revision fingerprint cannot be changed",
            cause=exc,
        )
    event = record_audit_event(
        event_type="finalized",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        upload_session_id=session.id,
        actor_user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
        metadata={"object_count": len(session.parts)},
    )
    previous_meeting_status = meeting.status
    previous_meeting_processing_status = meeting.processing_status
    previous_media_revision_status = meeting.media_revision_status
    previous_session_status = session.status
    previous_session_processing_status = session.processing_status
    previous_finalized_at = session.finalized_at
    try:
        meeting.status = MeetingStatus.INGESTED_PENDING_PROCESSING
        meeting.processing_status = ProcessingStatus.NOT_SUBMITTED
        meeting.media_revision_status = MediaRevisionStatus.ACCEPTED
        session.status = UploadSessionStatus.FINALIZED
        session.processing_status = ProcessingStatus.NOT_SUBMITTED
        session.finalized_at = datetime.now(UTC)
        await persist_meeting(db, meeting, commit=False)
        await persist_upload_session(db, session, commit=False)
        await persist_finalized_tracks(
            db,
            meeting,
            session,
            tracks,
            manifest_sha256,
            finalized_track_object_keys,
            commit=False,
        )
        await upsert_playback_normalization_job(
            db,
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            media_revision_id=session.media_revision_id or meeting.media_revision_id,
        )
        await persist_audit_event(db, event, commit=False)
    except Exception as exc:
        await _cleanup_materialized_track_objects(storage, materialized_track_object_keys)
        meeting.status = previous_meeting_status
        meeting.processing_status = previous_meeting_processing_status
        meeting.media_revision_status = previous_media_revision_status
        session.status = previous_session_status
        session.processing_status = previous_session_processing_status
        session.finalized_at = previous_finalized_at
        raise ProblemDetail(status=503, code="persistence_unavailable", title="Persistence unavailable") from exc
    return meeting, session
