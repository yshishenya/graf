from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import CalendarUploadSessionProof
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.calendar.matching import active_calendar_match_access
from twobrain_rec_server.db.models import (
    MediaRevision,
    Meeting,
    RecordingCalendarMatchAttempt,
    UploadSession,
)
from twobrain_rec_server.domain.statuses import (
    DeletionState,
    MediaRevisionSourceKind,
    MediaRevisionStatus,
    UploadSessionStatus,
)
from twobrain_rec_server.ingest.store import UploadSessionRecord, preferred_meeting_revision


async def require_calendar_upload_access(
    db: AsyncSession | None, session: UploadSessionRecord, tenant_scope: TenantScope,
) -> None:
    if session.calendar_match_attempt_id is None:
        return
    if session.media_revision_id is None:
        raise ProblemDetail(status=404, code="upload_session_not_found", title="Upload session not found")
    await get_calendar_upload_session_proof(
        session.meeting_id, session.id, session.media_revision_id, tenant_scope, db,
        expected_attempt_id=session.calendar_match_attempt_id,
    )


async def get_calendar_upload_session_proof(
    meeting_id: UUID,
    session_id: UUID,
    expected_revision_id: UUID,
    tenant_scope: TenantScope,
    db: AsyncSession | None,
    *,
    expected_attempt_id: UUID | None = None,
) -> CalendarUploadSessionProof:
    if db is None:
        raise ProblemDetail(status=503, code="ingest_store_unavailable", title="Ingest store unavailable")
    if tenant_scope.auth_session_id is None:
        raise ProblemDetail(status=403, code="device_scope_denied", title="Trusted device session required")

    preferred = (
        preferred_meeting_revision(tenant_scope.workspace_id, meeting_id)
        .with_only_columns(MediaRevision.id).correlate(None).scalar_subquery()
    )
    # Read the actual revision FK and access together. Legacy loaders can
    # substitute the meeting's current revision and answer from process memory.
    attempt = RecordingCalendarMatchAttempt
    query = (
        select(UploadSession)
        .join(Meeting, Meeting.id == UploadSession.meeting_id)
        .join(MediaRevision, MediaRevision.id == UploadSession.media_revision_id)
        .join(attempt, attempt.id == UploadSession.calendar_match_attempt_id)
        .where(
            UploadSession.id == session_id,
            UploadSession.meeting_id == meeting_id,
            UploadSession.media_revision_id == expected_revision_id,
            UploadSession.workspace_id == tenant_scope.workspace_id,
            UploadSession.created_by_user_id == tenant_scope.user_id,
            UploadSession.device_id == tenant_scope.device_id,
            UploadSession.status.in_([UploadSessionStatus.PENDING.value, UploadSessionStatus.UPLOADING.value]),
            UploadSession.expires_at > func.statement_timestamp(),
            Meeting.workspace_id == UploadSession.workspace_id,
            Meeting.created_by_user_id == UploadSession.created_by_user_id,
            Meeting.device_id == UploadSession.device_id,
            Meeting.deleted_at.is_(None),
            Meeting.deletion_state == DeletionState.NONE.value,
            attempt.consumed_by_meeting_id == Meeting.id,
            attempt.workspace_id == Meeting.workspace_id,
            attempt.owner_user_id == Meeting.created_by_user_id,
            attempt.device_id == Meeting.device_id,
            attempt.local_recording_id == Meeting.local_recording_id,
            attempt.consumed_at < attempt.expires_at,
            or_(
                (attempt.decision_intent == "user_selected") & (attempt.attempt_state == "matched_user"),
                (attempt.decision_intent == "user_declined") & (attempt.attempt_state == "declined_by_user"),
            ),
            MediaRevision.meeting_id == Meeting.id,
            MediaRevision.workspace_id == Meeting.workspace_id,
            MediaRevision.id == preferred,
            MediaRevision.revision_number == 1,
            MediaRevision.local_media_revision_id == Meeting.local_recording_id + "--initial",
            MediaRevision.source_kind == MediaRevisionSourceKind.INITIAL_MIXED_RECORDING.value,
            MediaRevision.status.in_([
                MediaRevisionStatus.PENDING_UPLOAD.value,
                MediaRevisionStatus.UPLOADING.value,
                MediaRevisionStatus.BLOCKED.value,
            ]),
            *active_calendar_match_access(tenant_scope),
        )
        .execution_options(populate_existing=True)
    )
    if expected_attempt_id is not None:
        query = query.where(UploadSession.calendar_match_attempt_id == expected_attempt_id)
    session = await db.scalar(query)
    missing = ProblemDetail(status=404, code="upload_session_not_found", title="Upload session not found")
    if session is None:
        raise missing
    roles, sizes = session.expected_track_roles, session.expected_track_sizes
    required_roles = {"manifest", "media", "playback"}
    if (
        not isinstance(roles, list)
        or len(roles) != len(required_roles)
        or any(not isinstance(role, str) for role in roles)
        or not isinstance(sizes, dict)
        or set(roles) != required_roles
        or set(sizes) != required_roles
        or any(type(size) is not int or size <= 0 for size in sizes.values())
    ):
        raise missing
    return CalendarUploadSessionProof(
        session_id=session.id,
        meeting_id=session.meeting_id,
        media_revision_id=session.media_revision_id,
        status=session.status,
        expires_at=session.expires_at,
        expected_tracks=roles,
        expected_track_sizes=sizes,
    )
