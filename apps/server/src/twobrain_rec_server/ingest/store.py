from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.schemas import TrackDescriptor
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    IngestAuditEvent,
    ManifestSnapshot,
    MediaRevision,
    Meeting,
    ProcessingPlaceholder,
    TemporaryUploadObject,
    TrackArtifact,
    UploadPart,
    UploadSession,
    Workspace,
)
from twobrain_rec_server.domain.statuses import (
    MediaRevisionSourceKind,
    MediaRevisionStatus,
    MeetingStatus,
    ProcessingStatus,
    TrackRole,
    UploadSessionStatus,
    UploadStrategy,
)
from twobrain_rec_server.ingest.media_revisions import (
    initial_media_revision_id,
    initial_media_revision_source_kind,
    initial_media_revision_status,
    normalize_initial_local_media_revision_id,
)


@dataclass(slots=True)
class MeetingRecord:
    id: UUID
    workspace_id: UUID
    organization_id: UUID
    created_by_user_id: UUID
    device_id: UUID
    local_recording_id: str
    duration_seconds: int
    title: str | None
    title_source: str = "legacy_unknown"
    title_updated_at: datetime | None = None
    create_request_fingerprint_sha256: str | None = None
    local_media_revision_id: str | None = None
    media_revision_id: UUID | None = None
    media_revision_status: MediaRevisionStatus = field(default_factory=initial_media_revision_status)
    media_revision_source_kind: MediaRevisionSourceKind = field(default_factory=initial_media_revision_source_kind)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    recording_display_timezone_offset_minutes: int | None = None
    status: MeetingStatus = MeetingStatus.DRAFT
    processing_status: ProcessingStatus = ProcessingStatus.NOT_SUBMITTED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class UploadPartRecord:
    track_role: TrackRole
    part_number: int
    byte_offset: int
    byte_length: int
    sha256: str
    object_key: str
    data: bytes


@dataclass(slots=True)
class UploadSessionRecord:
    id: UUID
    meeting_id: UUID
    workspace_id: UUID
    organization_id: UUID
    device_id: UUID
    created_by_user_id: UUID
    status: UploadSessionStatus
    expires_at: datetime
    media_revision_id: UUID | None = None
    upload_strategy: UploadStrategy = UploadStrategy.SERVER_MEDIATED
    processing_status: ProcessingStatus = ProcessingStatus.NOT_SUBMITTED
    expected_track_roles: list[TrackRole] = field(
        default_factory=lambda: [TrackRole.MANIFEST, TrackRole.MICROPHONE, TrackRole.SYSTEM]
    )
    expected_track_sizes: dict[TrackRole, int] = field(default_factory=dict)
    finalized_at: datetime | None = None
    idempotency_key: str | None = None
    parts: dict[tuple[TrackRole, int], UploadPartRecord] = field(default_factory=dict)


@dataclass(slots=True)
class AuditEvent:
    event_type: str
    workspace_id: UUID
    meeting_id: UUID | None
    upload_session_id: UUID | None
    metadata: dict[str, object]
    media_revision_id: UUID | None = None
    actor_user_id: UUID | None = None
    device_id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class InMemoryIngestStore:
    def __init__(self) -> None:
        self.meetings: dict[UUID, MeetingRecord] = {}
        self.meetings_by_local_id: dict[tuple[UUID, UUID, str], UUID] = {}
        self.sessions: dict[UUID, UploadSessionRecord] = {}
        self.audit_events: list[AuditEvent] = []

    def create_or_get_meeting(
        self,
        *,
        settings: Settings,
        organization_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        device_id: UUID,
        local_recording_id: str,
        local_media_revision_id: str | None = None,
        duration_seconds: int,
        title: str | None,
        title_source: str,
        media_revision_source_kind: MediaRevisionSourceKind = MediaRevisionSourceKind.INITIAL_RECORDING,
    ) -> MeetingRecord:
        key = (workspace_id, user_id, local_recording_id)
        if key in self.meetings_by_local_id:
            return self.meetings[self.meetings_by_local_id[key]]
        if duration_seconds > settings.max_recording_duration_seconds:
            raise ValueError("recording_duration_exceeded")
        created_at = datetime.now(UTC)
        meeting = MeetingRecord(
            id=uuid4(),
            workspace_id=workspace_id,
            organization_id=organization_id,
            created_by_user_id=user_id,
            device_id=device_id,
            local_recording_id=local_recording_id,
            duration_seconds=duration_seconds,
            title=title,
            title_source=title_source,
            title_updated_at=created_at if title is not None else None,
            local_media_revision_id=normalize_initial_local_media_revision_id(
                local_recording_id,
                local_media_revision_id,
            ),
            media_revision_id=initial_media_revision_id(),
            media_revision_source_kind=media_revision_source_kind,
            created_at=created_at,
        )
        self.meetings[meeting.id] = meeting
        self.meetings_by_local_id[key] = meeting.id
        return meeting

    def create_upload_session(
        self,
        *,
        settings: Settings,
        meeting: MeetingRecord,
        device_id: UUID | None = None,
        expected_track_roles: list[TrackRole] | None = None,
        expected_track_sizes: dict[TrackRole, int] | None = None,
        idempotency_key: str | None = None,
    ) -> UploadSessionRecord:
        session = UploadSessionRecord(
            id=uuid4(),
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            organization_id=meeting.organization_id,
            device_id=device_id or meeting.device_id,
            created_by_user_id=meeting.created_by_user_id,
            media_revision_id=meeting.media_revision_id,
            status=UploadSessionStatus.PENDING,
            expires_at=datetime.now(UTC) + timedelta(seconds=settings.upload_session_ttl_seconds),
            expected_track_roles=expected_track_roles or [TrackRole.MANIFEST, TrackRole.MICROPHONE, TrackRole.SYSTEM],
            expected_track_sizes=expected_track_sizes or {},
            idempotency_key=idempotency_key,
        )
        meeting.status = MeetingStatus.UPLOADING
        self.sessions[session.id] = session
        return session


store = InMemoryIngestStore()


async def _finish_write(db: AsyncSession, *, commit: bool) -> None:
    if commit:
        await db.commit()
    else:
        await db.flush()


async def persist_meeting(db: AsyncSession | None, meeting: MeetingRecord, *, commit: bool = True) -> None:
    if db is None:
        return
    existing = await db.get(Meeting, meeting.id)
    local_media_revision_id = normalize_initial_local_media_revision_id(
        meeting.local_recording_id,
        meeting.local_media_revision_id,
    )
    media_revision_id = initial_media_revision_id(meeting.media_revision_id)
    meeting.local_media_revision_id = local_media_revision_id
    meeting.media_revision_id = media_revision_id
    if existing is None:
        meeting_model = Meeting(
            id=meeting.id,
            workspace_id=meeting.workspace_id,
            created_by_user_id=meeting.created_by_user_id,
            device_id=meeting.device_id,
            local_recording_id=meeting.local_recording_id,
            title=meeting.title,
            title_source=meeting.title_source,
            title_updated_at=meeting.title_updated_at,
            create_request_fingerprint_sha256=meeting.create_request_fingerprint_sha256,
            started_at=meeting.started_at,
            ended_at=meeting.ended_at,
            recording_display_timezone_offset_minutes=meeting.recording_display_timezone_offset_minutes,
            duration_seconds=meeting.duration_seconds,
            status=meeting.status.value,
            processing_status=meeting.processing_status.value,
            created_at=meeting.created_at,
        )
        db.add(meeting_model)
        await db.flush()
        db.add(
            MediaRevision(
                id=media_revision_id,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                local_media_revision_id=local_media_revision_id,
                revision_number=1,
                source_kind=meeting.media_revision_source_kind.value,
                status=meeting.media_revision_status.value,
                duration_seconds=meeting.duration_seconds,
                immutable=True,
            )
        )
        db.add(
            ProcessingPlaceholder(
                meeting_id=meeting.id,
                workspace_id=meeting.workspace_id,
                status=meeting.processing_status.value,
                meeting_status=meeting.status.value,
            )
        )
    else:
        media_revision = await db.scalar(
            select(MediaRevision).where(
                MediaRevision.workspace_id == meeting.workspace_id,
                MediaRevision.meeting_id == meeting.id,
                MediaRevision.revision_number == 1,
            )
        )
        if media_revision is None:
            db.add(
                MediaRevision(
                    id=media_revision_id,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    local_media_revision_id=local_media_revision_id,
                    revision_number=1,
                    source_kind=meeting.media_revision_source_kind.value,
                    status=meeting.media_revision_status.value,
                    duration_seconds=meeting.duration_seconds,
                    immutable=True,
                )
            )
        else:
            meeting.media_revision_id = media_revision.id
            meeting.local_media_revision_id = media_revision.local_media_revision_id
        existing.status = meeting.status.value
        existing.processing_status = meeting.processing_status.value
        existing.title = meeting.title
        existing.title_source = meeting.title_source
        existing.title_updated_at = meeting.title_updated_at
        if meeting.create_request_fingerprint_sha256 is not None:
            existing.create_request_fingerprint_sha256 = meeting.create_request_fingerprint_sha256
        existing.started_at = meeting.started_at
        existing.ended_at = meeting.ended_at
        existing.recording_display_timezone_offset_minutes = meeting.recording_display_timezone_offset_minutes
        placeholder = await db.scalar(select(ProcessingPlaceholder).where(ProcessingPlaceholder.meeting_id == meeting.id))
        if placeholder is not None:
            placeholder.status = meeting.processing_status.value
            placeholder.meeting_status = meeting.status.value
    await _finish_write(db, commit=commit)


async def load_meeting_record(
    db: AsyncSession | None,
    *,
    meeting_id: UUID | None = None,
    workspace_id: UUID | None = None,
    created_by_user_id: UUID | None = None,
    local_recording_id: str | None = None,
) -> MeetingRecord | None:
    if db is None:
        return None
    if meeting_id is not None:
        model = await db.get(Meeting, meeting_id)
    elif workspace_id is not None and created_by_user_id is not None and local_recording_id is not None:
        model = await db.scalar(
            select(Meeting).where(
                Meeting.workspace_id == workspace_id,
                Meeting.created_by_user_id == created_by_user_id,
                Meeting.local_recording_id == local_recording_id,
            )
        )
    else:
        return None
    if model is None:
        return None
    workspace = await db.get(Workspace, model.workspace_id)
    if workspace is None:
        return None
    media_revision = await db.scalar(
        select(MediaRevision)
        .where(MediaRevision.workspace_id == model.workspace_id, MediaRevision.meeting_id == model.id)
        .order_by(MediaRevision.revision_number.asc())
    )
    record = MeetingRecord(
        id=model.id,
        workspace_id=model.workspace_id,
        organization_id=workspace.organization_id,
        created_by_user_id=model.created_by_user_id,
        device_id=model.device_id,
        local_recording_id=model.local_recording_id,
        duration_seconds=model.duration_seconds,
        title=model.title,
        title_source=model.title_source,
        title_updated_at=model.title_updated_at,
        create_request_fingerprint_sha256=model.create_request_fingerprint_sha256,
        local_media_revision_id=(
            media_revision.local_media_revision_id
            if media_revision is not None
            else normalize_initial_local_media_revision_id(model.local_recording_id, None)
        ),
        media_revision_id=media_revision.id if media_revision is not None else None,
        media_revision_status=(
            MediaRevisionStatus(media_revision.status)
            if media_revision is not None
            else initial_media_revision_status()
        ),
        media_revision_source_kind=(
            MediaRevisionSourceKind(media_revision.source_kind)
            if media_revision is not None
            else initial_media_revision_source_kind()
        ),
        started_at=model.started_at,
        ended_at=model.ended_at,
        recording_display_timezone_offset_minutes=model.recording_display_timezone_offset_minutes,
        status=MeetingStatus(model.status),
        processing_status=ProcessingStatus(model.processing_status),
        created_at=model.created_at,
    )
    store.meetings[record.id] = record
    store.meetings_by_local_id[(record.workspace_id, record.created_by_user_id, record.local_recording_id)] = record.id
    return record


async def persist_upload_session(
    db: AsyncSession | None,
    session: UploadSessionRecord,
    settings: Settings | None = None,
    *,
    commit: bool = True,
) -> None:
    if db is None:
        return
    existing = await db.get(UploadSession, session.id)
    expected_roles = [role.value for role in session.expected_track_roles]
    expected_sizes = {role.value: size for role, size in session.expected_track_sizes.items()}
    if existing is None:
        if settings is None:
            raise RuntimeError("settings are required to create an upload session record")
        db.add(
            UploadSession(
                id=session.id,
                meeting_id=session.meeting_id,
                media_revision_id=session.media_revision_id,
                workspace_id=session.workspace_id,
                device_id=session.device_id,
                created_by_user_id=session.created_by_user_id,
                upload_strategy=session.upload_strategy.value,
                status=session.status.value,
                processing_status=session.processing_status.value,
                idempotency_key=session.idempotency_key,
                expected_track_roles=expected_roles,
                expected_track_sizes=expected_sizes,
                max_package_bytes_snapshot=settings.max_package_bytes,
                max_track_bytes_snapshot=settings.max_track_bytes,
                expires_at=session.expires_at,
            )
        )
    else:
        existing.status = session.status.value
        existing.processing_status = session.processing_status.value
        existing.expected_track_roles = expected_roles
        existing.expected_track_sizes = expected_sizes
        existing.finalized_at = session.finalized_at
    await _finish_write(db, commit=commit)


async def load_upload_session_record(
    db: AsyncSession | None,
    session_id: UUID,
) -> UploadSessionRecord | None:
    if db is None:
        return None
    model = await db.get(UploadSession, session_id)
    if model is None:
        return None
    meeting = await load_meeting_record(db, meeting_id=model.meeting_id)
    if meeting is None:
        return None
    expected_sizes = {
        TrackRole(role): int(size)
        for role, size in (model.expected_track_sizes or {}).items()
    }
    expected_roles = [TrackRole(role) for role in (model.expected_track_roles or [])] or [
        TrackRole.MANIFEST,
        TrackRole.MICROPHONE,
        TrackRole.SYSTEM,
    ]
    record = UploadSessionRecord(
        id=model.id,
        meeting_id=model.meeting_id,
        workspace_id=model.workspace_id,
        organization_id=meeting.organization_id,
        device_id=model.device_id,
        created_by_user_id=model.created_by_user_id,
        media_revision_id=model.media_revision_id or meeting.media_revision_id,
        status=UploadSessionStatus(model.status),
        expires_at=model.expires_at,
        upload_strategy=UploadStrategy(model.upload_strategy),
        processing_status=ProcessingStatus(model.processing_status),
        expected_track_roles=expected_roles,
        expected_track_sizes=expected_sizes,
        finalized_at=model.finalized_at,
        idempotency_key=model.idempotency_key,
    )
    parts = await db.scalars(select(UploadPart).where(UploadPart.upload_session_id == session_id))
    for part in parts:
        role = TrackRole(part.track_role)
        record.parts[(role, part.part_number)] = UploadPartRecord(
            track_role=role,
            part_number=part.part_number,
            byte_offset=part.byte_offset,
            byte_length=part.byte_length,
            sha256=part.sha256,
            object_key=part.storage_object_key,
            data=b"",
        )
    store.sessions[record.id] = record
    return record


async def load_active_upload_session_for_meeting(
    db: AsyncSession | None,
    meeting_id: UUID,
) -> UploadSessionRecord | None:
    if db is None:
        return None
    terminal_statuses = {
        UploadSessionStatus.FINALIZED.value,
        UploadSessionStatus.DEGRADED.value,
        UploadSessionStatus.FAILED.value,
        UploadSessionStatus.ABORTED.value,
        UploadSessionStatus.EXPIRED.value,
    }
    model = await db.scalar(
        select(UploadSession)
        .where(
            UploadSession.meeting_id == meeting_id,
            UploadSession.status.not_in(terminal_statuses),
        )
        .order_by(UploadSession.created_at.desc())
    )
    if model is None:
        return None
    return await load_upload_session_record(db, model.id)


async def persist_upload_part(
    db: AsyncSession | None,
    session: UploadSessionRecord,
    part: UploadPartRecord,
    *,
    commit: bool = True,
) -> None:
    if db is None:
        return
    existing = await db.scalar(
        select(UploadPart).where(
            UploadPart.upload_session_id == session.id,
            UploadPart.track_role == part.track_role.value,
            UploadPart.part_number == part.part_number,
        )
    )
    if existing is None:
        db.add(
            UploadPart(
                upload_session_id=session.id,
                track_role=part.track_role.value,
                part_number=part.part_number,
                byte_offset=part.byte_offset,
                byte_length=part.byte_length,
                sha256=part.sha256,
                storage_object_key=part.object_key,
                status="accepted",
            )
        )
    await _finish_write(db, commit=commit)


async def persist_temporary_upload_object(
    db: AsyncSession | None,
    session: UploadSessionRecord,
    part: UploadPartRecord,
    cleanup_status: str = "pending",
    object_role: str = "accepted_part",
    failure_reason: str | None = None,
    last_error: str | None = None,
    commit: bool = True,
) -> None:
    if db is None:
        return
    existing = await db.scalar(
        select(TemporaryUploadObject).where(
            TemporaryUploadObject.upload_session_id == session.id,
            TemporaryUploadObject.storage_object_key == part.object_key,
        )
    )
    if existing is None:
        db.add(
            TemporaryUploadObject(
                upload_session_id=session.id,
                media_revision_id=session.media_revision_id,
                workspace_id=session.workspace_id,
                storage_object_key=part.object_key,
                byte_length=part.byte_length,
                object_role=object_role,
                cleanup_status=cleanup_status,
                failure_reason=failure_reason,
                last_error=last_error,
            )
        )
    else:
        existing.cleanup_status = cleanup_status
        existing.object_role = object_role
        existing.failure_reason = failure_reason
        existing.last_error = last_error
    await _finish_write(db, commit=commit)


async def mark_temporary_upload_object_cleanup_status(
    db: AsyncSession | None,
    session: UploadSessionRecord,
    object_key: str,
    cleanup_status: str,
    failure_reason: str | None = None,
    last_error: str | None = None,
    commit: bool = True,
) -> None:
    if db is None:
        return
    existing = await db.scalar(
        select(TemporaryUploadObject).where(
            TemporaryUploadObject.upload_session_id == session.id,
            TemporaryUploadObject.storage_object_key == object_key,
        )
    )
    if existing is not None:
        existing.cleanup_status = cleanup_status
        existing.failure_reason = failure_reason
        existing.last_error = last_error
        await _finish_write(db, commit=commit)


async def persist_audit_event(db: AsyncSession | None, event: AuditEvent, *, commit: bool = True) -> None:
    if db is None:
        return
    db.add(
        IngestAuditEvent(
            workspace_id=event.workspace_id,
            meeting_id=event.meeting_id,
            media_revision_id=event.media_revision_id,
            upload_session_id=event.upload_session_id,
            actor_user_id=event.actor_user_id,
            device_id=event.device_id,
            event_type=event.event_type,
            metadata_json=event.metadata,
            created_at=event.created_at,
        )
    )
    await _finish_write(db, commit=commit)


async def persist_latest_audit_event(db: AsyncSession | None) -> None:
    if store.audit_events:
        await persist_audit_event(db, store.audit_events[-1])


async def persist_finalized_tracks(
    db: AsyncSession | None,
    meeting: MeetingRecord,
    session: UploadSessionRecord,
    tracks: list[TrackDescriptor],
    manifest_sha256: str,
    track_object_keys: dict[TrackRole, str] | None = None,
    *,
    commit: bool = True,
) -> None:
    if db is None:
        return
    track_object_keys = track_object_keys or {}
    for track in tracks:
        storage_object_key = track_object_keys.get(track.track_role)
        if storage_object_key is None:
            storage_object_key = session.parts[(track.track_role, 0)].object_key
        existing = await db.scalar(
            select(TrackArtifact).where(
                TrackArtifact.meeting_id == meeting.id,
                TrackArtifact.track_role == track.track_role.value,
                TrackArtifact.storage_object_key == storage_object_key,
            )
        )
        if existing is None:
            db.add(
                TrackArtifact(
                    meeting_id=meeting.id,
                    media_revision_id=session.media_revision_id or meeting.media_revision_id,
                    workspace_id=meeting.workspace_id,
                    track_role=track.track_role.value,
                    codec=track.codec,
                    sample_rate_hz=track.sample_rate_hz,
                    channel_count=track.channel_count,
                    duration_seconds=track.duration_seconds,
                    byte_length=track.byte_length,
                    sha256=track.sha256,
                    storage_object_key=storage_object_key,
                    status="candidate" if track.track_role is TrackRole.PLAYBACK else "stored",
                )
            )
    existing_manifest = await db.scalar(select(ManifestSnapshot).where(ManifestSnapshot.meeting_id == meeting.id))
    if existing_manifest is None:
        db.add(
            ManifestSnapshot(
                meeting_id=meeting.id,
                media_revision_id=session.media_revision_id or meeting.media_revision_id,
                workspace_id=meeting.workspace_id,
                manifest_sha256=manifest_sha256,
                manifest_json={
                    "manifest_sha256": manifest_sha256,
                    "tracks": [track.model_dump(mode="json") for track in tracks],
                },
            )
        )
    await _finish_write(db, commit=commit)
