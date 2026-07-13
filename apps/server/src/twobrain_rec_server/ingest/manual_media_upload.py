from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import TrackDescriptor
from twobrain_rec_server.api.upload_stream import BoundedUploadBody
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.calendar.matching import ensure_manual_upload_calendar_skip
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import RecordingCalendarContextLink
from twobrain_rec_server.domain.statuses import MediaRevisionSourceKind, TrackRole
from twobrain_rec_server.ingest.finalize import finalize_upload
from twobrain_rec_server.ingest.meetings import create_or_get_meeting
from twobrain_rec_server.ingest.parts import accept_part
from twobrain_rec_server.ingest.policy import IngestLimitViolation
from twobrain_rec_server.ingest.processing_dispatch import (
    FinalizeProcessingDispatchResult,
    dispatch_processing_after_finalize,
)
from twobrain_rec_server.ingest.sessions import create_upload_session
from twobrain_rec_server.ingest.store import MeetingRecord, UploadSessionRecord


@dataclass(frozen=True, slots=True)
class ManualMediaUploadResult:
    meeting: MeetingRecord
    calendar_context: RecordingCalendarContextLink | None
    upload_session: UploadSessionRecord
    object_count: int
    processing: FinalizeProcessingDispatchResult


def _track_descriptor(
    *,
    track_role: TrackRole,
    byte_length: int,
    content_sha256: str,
    codec: str,
    duration_seconds: int,
) -> TrackDescriptor:
    return TrackDescriptor(
        track_role=track_role,
        codec=codec,
        sample_rate_hz=1,
        channel_count=1,
        duration_seconds=duration_seconds,
        byte_length=byte_length,
        sha256=content_sha256,
    )


def _manifest_bytes(*, duration_seconds: int, media_sha256: str, media_byte_length: int, content_type: str) -> bytes:
    payload = {
        "schema_version": 1,
        "source_kind": MediaRevisionSourceKind.MANUAL_UPLOAD.value,
        "tracks": [
            {
                "track_role": TrackRole.MEDIA.value,
                "duration_seconds": duration_seconds,
                "byte_length": media_byte_length,
                "sha256": media_sha256,
                "content_type": content_type,
            }
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _display_title_from_upload(*, title: str | None, filename: str | None) -> str | None:
    cleaned_title = title.strip() if title is not None else ""
    if cleaned_title:
        return cleaned_title[:500]
    if not filename:
        return None
    basename = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    return basename[:500] or None


async def accept_manual_media_upload(
    *,
    settings: Settings,
    tenant_scope: TenantScope,
    db: AsyncSession | None,
    storage: object,
    file: BoundedUploadBody,
    filename: str | None,
    content_type: str,
    duration_seconds: int,
    title: str | None,
    local_recording_id: str | None,
    temporal_client: object | None,
) -> ManualMediaUploadResult:
    if file.byte_length == 0:
        file.stream.close()
        raise ProblemDetail(status=400, code="empty_media_upload", title="Uploaded media file is empty")
    if file.byte_length > settings.max_upload_part_bytes:
        file.stream.close()
        raise ProblemDetail(status=413, code="upload_part_bytes_exceeded", title="Upload part byte limit exceeded")

    media_sha256 = file.sha256
    recording_id = local_recording_id or f"manual-upload-{media_sha256[:32]}"
    media_revision_id = f"{recording_id}--manual"
    display_title = _display_title_from_upload(title=title, filename=filename)
    cleaned_title = title.strip() if title is not None else ""
    display_title_source = (
        "upload_provided"
        if cleaned_title
        else "file_name_derived"
        if display_title is not None
        else "generic"
    )
    manifest_bytes = _manifest_bytes(
        duration_seconds=duration_seconds,
        media_sha256=media_sha256,
        media_byte_length=file.byte_length,
        content_type=content_type,
    )
    manifest_sha256 = sha256(manifest_bytes).hexdigest()
    manifest = _track_descriptor(
        track_role=TrackRole.MANIFEST,
        byte_length=len(manifest_bytes),
        content_sha256=manifest_sha256,
        codec="application/json",
        duration_seconds=duration_seconds,
    )
    media = _track_descriptor(
        track_role=TrackRole.MEDIA,
        byte_length=file.byte_length,
        content_sha256=media_sha256,
        codec=content_type,
        duration_seconds=duration_seconds,
    )

    try:
        meeting = await create_or_get_meeting(
            settings=settings,
            tenant_scope=tenant_scope,
            db=db,
            local_recording_id=recording_id,
            local_media_revision_id=media_revision_id,
            duration_seconds=duration_seconds,
            title=display_title,
            title_source=display_title_source,
            media_revision_source_kind=MediaRevisionSourceKind.MANUAL_UPLOAD,
        )
        calendar_context = (
            await ensure_manual_upload_calendar_skip(
                db,
                tenant_scope,
                meeting=meeting,
            )
            if db is not None
            else None
        )
        session = await create_upload_session(
            settings=settings,
            tenant_scope=tenant_scope,
            db=db,
            meeting_id=meeting.id,
            expected_track_roles=[TrackRole.MANIFEST, TrackRole.MEDIA],
            expected_track_sizes={
                TrackRole.MANIFEST: len(manifest_bytes),
                TrackRole.MEDIA: file.byte_length,
            },
            idempotency_key=f"manual-upload-{recording_id}",
        )
        await accept_part(
            settings=settings,
            tenant_scope=tenant_scope,
            db=db,
            storage=storage,
            session_id=session.id,
            track_role=TrackRole.MANIFEST,
            part_number=0,
            byte_offset=0,
            content_sha256=manifest.sha256,
            data=manifest_bytes,
        )
        await accept_part(
            settings=settings,
            tenant_scope=tenant_scope,
            db=db,
            storage=storage,
            session_id=session.id,
            track_role=TrackRole.MEDIA,
            part_number=0,
            byte_offset=0,
            content_sha256=media.sha256,
            data=file,
        )
        meeting, session = await finalize_upload(
            tenant_scope=tenant_scope,
            db=db,
            session_id=session.id,
            manifest_sha256=manifest.sha256,
            tracks=[manifest, media],
            storage=storage,
        )
    except IngestLimitViolation as exc:
        raise ProblemDetail(
            status=413,
            code=exc.code,
            title="Ingest limit exceeded",
            detail=f"{exc.limit_name}={exc.limit_value}, actual={exc.actual_value}",
        ) from exc

    processing = await dispatch_processing_after_finalize(
        db=db,
        settings=settings,
        tenant_scope=tenant_scope,
        meeting=meeting,
        session=session,
        temporal_client=temporal_client,
    )
    return ManualMediaUploadResult(
        meeting=meeting,
        calendar_context=calendar_context,
        upload_session=session,
        object_count=len(session.parts),
        processing=processing,
    )
