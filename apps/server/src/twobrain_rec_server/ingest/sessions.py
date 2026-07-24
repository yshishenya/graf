from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import MediaRevision, UploadSession
from twobrain_rec_server.db.models import Meeting as MeetingModel
from twobrain_rec_server.domain.statuses import (
    MediaRevisionSourceKind,
    MediaRevisionStatus,
    TrackRole,
    UploadSessionStatus,
)
from twobrain_rec_server.ingest import store as store_module
from twobrain_rec_server.ingest.audit import record_audit_event
from twobrain_rec_server.ingest.lifecycle_guards import ensure_meeting_accepts_uploads
from twobrain_rec_server.ingest.manifest import (
    ManifestValidationError,
    validate_required_track_roles,
)
from twobrain_rec_server.ingest.policy import IngestLimitViolation, validate_recording_duration
from twobrain_rec_server.ingest.store import (
    UploadSessionRecord,
    load_active_upload_session_for_meeting,
    load_meeting_record,
    load_upload_session_record,
    persist_audit_event,
    persist_meeting,
    persist_upload_session,
)

_TERMINAL_UPLOAD_STATUSES = {
    UploadSessionStatus.FINALIZED.value,
    UploadSessionStatus.DEGRADED.value,
    UploadSessionStatus.FAILED.value,
    UploadSessionStatus.ABORTED.value,
    UploadSessionStatus.EXPIRED.value,
}


def _default_revision_track_roles(source_kind: MediaRevisionSourceKind) -> list[TrackRole]:
    if source_kind == MediaRevisionSourceKind.INITIAL_RECORDING:
        return [TrackRole.MANIFEST, TrackRole.MICROPHONE, TrackRole.SYSTEM]
    if source_kind == MediaRevisionSourceKind.INITIAL_MIXED_RECORDING:
        return [TrackRole.MANIFEST, TrackRole.MEDIA, TrackRole.PLAYBACK]
    return [TrackRole.MANIFEST, TrackRole.MEDIA]


async def create_media_revision_upload_session(
    *,
    settings: Settings,
    tenant_scope: TenantScope,
    db: AsyncSession | None,
    meeting_id: UUID,
    local_media_revision_id: str,
    source_kind: MediaRevisionSourceKind,
    duration_seconds: int,
    expected_track_roles: list[TrackRole] | None = None,
    expected_track_sizes: dict[TrackRole, int] | None = None,
    idempotency_key: str | None = None,
) -> tuple[MediaRevision, UploadSessionRecord]:
    """Create one durable revision and its upload session.

    The revision is intentionally pending and immutable only after finalize. A
    caller may safely repeat the request with the same local revision and
    idempotency key; an accepted revision is never rewritten.
    """
    if db is None:
        raise ProblemDetail(status=503, code="ingest_store_unavailable", title="Ingest store unavailable")
    meeting_model = await db.scalar(
        select(MeetingModel)
        .where(MeetingModel.id == meeting_id, MeetingModel.workspace_id == tenant_scope.workspace_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if meeting_model is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    if meeting_model.created_by_user_id != tenant_scope.user_id:
        raise ProblemDetail(status=403, code="meeting_scope_denied", title="Meeting scope denied")
    await ensure_meeting_accepts_uploads(db=db, meeting_id=meeting_id)
    if duration_seconds <= 0:
        raise ProblemDetail(status=400, code="invalid_duration", title="Duration must be positive")
    try:
        validate_recording_duration(settings, duration_seconds)
    except IngestLimitViolation as exc:
        raise ProblemDetail(
            status=400,
            code=exc.code,
            title="Ingest limit exceeded",
            detail=f"{exc.limit_name}={exc.limit_value}, actual={exc.actual_value}",
        ) from exc
    roles = expected_track_roles or _default_revision_track_roles(source_kind)
    sizes = expected_track_sizes or {}
    if any(size < 0 for size in sizes.values()):
        raise ProblemDetail(status=400, code="invalid_expected_track_size", title="Expected track size must be non-negative")
    if set(sizes) - set(roles):
        raise ProblemDetail(status=400, code="unexpected_expected_track_size_role", title="Expected track size provided for an unexpected role")
    try:
        validate_required_track_roles(set(roles), source_kind=source_kind)
    except ManifestValidationError as exc:
        raise ProblemDetail(status=400, code="invalid_expected_track_roles", title=str(exc)) from exc

    revision = await db.scalar(
        select(MediaRevision)
        .where(
            MediaRevision.workspace_id == tenant_scope.workspace_id,
            MediaRevision.meeting_id == meeting_id,
            MediaRevision.local_media_revision_id == local_media_revision_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if revision is None:
        latest_number = int(
            await db.scalar(
                select(func.max(MediaRevision.revision_number)).where(
                    MediaRevision.workspace_id == tenant_scope.workspace_id,
                    MediaRevision.meeting_id == meeting_id,
                )
            )
            or 0
        )
        revision = MediaRevision(
            id=uuid4(),
            workspace_id=tenant_scope.workspace_id,
            meeting_id=meeting_id,
            local_media_revision_id=local_media_revision_id,
            revision_number=latest_number + 1,
            source_kind=source_kind.value,
            status=MediaRevisionStatus.PENDING_UPLOAD.value,
            duration_seconds=duration_seconds,
            immutable=False,
        )
        db.add(revision)
        await db.flush()
    else:
        if revision.source_kind != source_kind.value or revision.duration_seconds != duration_seconds:
            raise ProblemDetail(status=409, code="idempotency_conflict", title="Media revision conflicts with existing request")
        if revision.status == MediaRevisionStatus.ACCEPTED.value and revision.immutable:
            raise ProblemDetail(status=409, code="media_revision_immutable", title="Accepted media revision cannot be changed")

    active_model = await db.scalar(
        select(UploadSession)
        .where(
            UploadSession.workspace_id == tenant_scope.workspace_id,
            UploadSession.meeting_id == meeting_id,
            UploadSession.media_revision_id == revision.id,
            UploadSession.status.not_in(_TERMINAL_UPLOAD_STATUSES),
        )
        .order_by(UploadSession.created_at.desc())
    )
    if active_model is not None:
        active = await load_upload_session_record(db, active_model.id)
        if active is not None:
            if idempotency_key and active.idempotency_key == idempotency_key:
                if active.expected_track_roles == roles and active.expected_track_sizes == sizes:
                    return revision, active
                raise ProblemDetail(status=409, code="idempotency_conflict", title="Idempotency key conflict")
            raise ProblemDetail(status=409, code="active_upload_session_exists", title="Active upload session already exists for revision")

    # Meeting lock above serializes reprocess requests across revisions.  Do
    # not allow two active upload sessions for one meeting merely because each
    # request chose a different local revision id.
    meeting_active = await load_active_upload_session_for_meeting(db, meeting_id)
    if meeting_active is not None and meeting_active.media_revision_id != revision.id:
        raise ProblemDetail(
            status=409,
            code="active_upload_session_exists",
            title="Active upload session already exists for meeting",
        )

    meeting = await load_meeting_record(db, meeting_id=meeting_id)
    if meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    meeting.media_revision_id = revision.id
    meeting.local_media_revision_id = revision.local_media_revision_id
    meeting.media_revision_number = revision.revision_number
    meeting.media_revision_status = MediaRevisionStatus(revision.status)
    meeting.media_revision_source_kind = MediaRevisionSourceKind(revision.source_kind)
    session = store_module.store.create_upload_session(
        settings=settings,
        meeting=meeting,
        device_id=tenant_scope.device_id,
        expected_track_roles=roles,
        expected_track_sizes=sizes,
        idempotency_key=idempotency_key,
    )
    session.media_revision_id = revision.id
    event = record_audit_event(
        event_type="media_revision_upload_session_created",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        upload_session_id=session.id,
        media_revision_id=revision.id,
        actor_user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
        metadata={"revision_number": revision.revision_number, "source_kind": revision.source_kind},
    )
    await persist_meeting(db, meeting, commit=False)
    await persist_upload_session(db, session, settings, commit=False)
    await persist_audit_event(db, event, commit=False)
    return revision, session


async def create_upload_session(
    *,
    settings: Settings,
    tenant_scope: TenantScope,
    db: AsyncSession | None = None,
    meeting_id: UUID,
    expected_track_roles: list[TrackRole] | None = None,
    expected_track_sizes: dict[TrackRole, int] | None = None,
    idempotency_key: str | None = None,
) -> UploadSessionRecord:
    if db is not None:
        # Serialize the legacy endpoint's active-session check with creation;
        # revision-scoped creation already takes this fence above.
        meeting_model = await db.scalar(
            select(MeetingModel)
            .where(
                MeetingModel.id == meeting_id,
                MeetingModel.workspace_id == tenant_scope.workspace_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if meeting_model is None:
            raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
        if meeting_model.created_by_user_id != tenant_scope.user_id:
            raise ProblemDetail(status=403, code="meeting_scope_denied", title="Meeting scope denied")
    meeting = await load_meeting_record(db, meeting_id=meeting_id)
    if meeting is None:
        meeting = store_module.store.meetings.get(meeting_id)
    if meeting is None or meeting.workspace_id != tenant_scope.workspace_id:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    if meeting.created_by_user_id != tenant_scope.user_id:
        raise ProblemDetail(status=403, code="meeting_scope_denied", title="Meeting scope denied")
    if not expected_track_roles:
        if meeting.media_revision_source_kind == "initial_mixed_recording":
            expected_track_roles = [TrackRole.MANIFEST, TrackRole.MEDIA, TrackRole.PLAYBACK]
        else:
            expected_track_roles = [TrackRole.MANIFEST, TrackRole.MICROPHONE, TrackRole.SYSTEM]
    for size in (expected_track_sizes or {}).values():
        if size < 0:
            raise ProblemDetail(
                status=400,
                code="invalid_expected_track_size",
                title="Expected track size must be non-negative",
            )
    unexpected_size_roles = set(expected_track_sizes or {}) - set(expected_track_roles)
    if unexpected_size_roles:
        raise ProblemDetail(
            status=400,
            code="unexpected_expected_track_size_role",
            title="Expected track size provided for a role that is not expected",
        )
    try:
        validate_required_track_roles(
            set(expected_track_roles),
            source_kind=meeting.media_revision_source_kind,
        )
    except ManifestValidationError as exc:
        raise ProblemDetail(
            status=400,
            code="invalid_expected_track_roles",
            title=str(exc),
        ) from exc
    await ensure_meeting_accepts_uploads(
        db=db,
        meeting_id=meeting.id,
        media_revision_status=meeting.media_revision_status,
    )
    active_session = await load_active_upload_session_for_meeting(db, meeting.id)
    if active_session is not None:
        if idempotency_key and active_session.idempotency_key == idempotency_key:
            if (
                active_session.expected_track_roles == expected_track_roles
                and active_session.expected_track_sizes == (expected_track_sizes or {})
            ):
                return active_session
            raise ProblemDetail(status=409, code="idempotency_conflict", title="Idempotency key conflict")
        raise ProblemDetail(
            status=409,
            code="active_upload_session_exists",
            title="Active upload session already exists for meeting",
        )
    session = store_module.store.create_upload_session(
        settings=settings,
        meeting=meeting,
        device_id=tenant_scope.device_id,
        expected_track_roles=expected_track_roles,
        expected_track_sizes=expected_track_sizes,
        idempotency_key=idempotency_key,
    )
    await persist_meeting(db, meeting, commit=False)
    event = record_audit_event(
        event_type="session_created",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        upload_session_id=session.id,
        actor_user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
    )
    await persist_upload_session(db, session, settings, commit=False)
    await persist_audit_event(db, event, commit=False)
    return session
