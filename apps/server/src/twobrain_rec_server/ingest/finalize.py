from uuid import UUID

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import TrackDescriptor
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.domain.statuses import MeetingStatus, ProcessingStatus, UploadSessionStatus
from twobrain_rec_server.ingest.audit import record_audit_event
from twobrain_rec_server.ingest.manifest import ManifestValidationError, validate_required_tracks
from twobrain_rec_server.ingest.parts import get_session_for_tenant
from twobrain_rec_server.ingest.store import store


def finalize_upload(
    *,
    tenant_scope: TenantScope,
    session_id: UUID,
    tracks: list[TrackDescriptor],
) -> tuple[object, object]:
    session = get_session_for_tenant(session_id, tenant_scope)
    meeting = store.meetings[session.meeting_id]
    try:
        validate_required_tracks(tracks)
    except ManifestValidationError as exc:
        meeting.status = MeetingStatus.DEGRADED
        session.status = UploadSessionStatus.DEGRADED
        raise ProblemDetail(status=400, code="manifest_validation_failed", title=str(exc)) from exc

    uploaded_roles = {role for role, _part_number in session.parts}
    expected_roles = {track.track_role for track in tracks}
    if not expected_roles.issubset(uploaded_roles):
        raise ProblemDetail(status=409, code="missing_required_parts", title="Missing required upload parts")

    meeting.status = MeetingStatus.INGESTED_PENDING_PROCESSING
    meeting.processing_status = ProcessingStatus.NOT_SUBMITTED
    session.status = UploadSessionStatus.FINALIZED
    session.processing_status = ProcessingStatus.NOT_SUBMITTED
    record_audit_event(
        event_type="finalized",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        upload_session_id=session.id,
        metadata={"object_count": len(session.parts)},
    )
    return meeting, session
