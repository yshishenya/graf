import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from tests.fixtures.local_upload_custody import (
    custody_problem_extension_fixture,
    custody_read_model_fixture,
)
from twobrain_rec_server.api.problems import ProblemDetail, problem_response
from twobrain_rec_server.api.schemas import (
    CustodyReadModel,
    DesktopRecordingSyncStateResponse,
    DesktopSyncConflict,
    MeetingListItem,
    Problem,
)
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.domain.statuses import (
    CustodyMetadataSafety,
    CustodyNormalUserAction,
    CustodyOwner,
    CustodyProcessingState,
    CustodyRetryClass,
    CustodyState,
    CustodyUploadState,
    MeetingStatus,
    ProcessingStatus,
    SyncConflictState,
    UploadSessionStatus,
)
from twobrain_rec_server.ingest.desktop_status import (
    meeting_desktop_status,
    upload_session_desktop_status,
)
from twobrain_rec_server.ingest.desktop_sync import (
    _custody_read_model,
    get_desktop_recording_sync_state,
)


def test_finalized_upload_maps_to_uploaded_label_without_processing_claim() -> None:
    status = upload_session_desktop_status(UploadSessionStatus.FINALIZED)
    assert status.label == "uploaded"
    assert "processing has not necessarily started" in status.truth_rule


def test_ingested_meeting_maps_to_uploaded_without_dashboard_claim() -> None:
    status = meeting_desktop_status(MeetingStatus.INGESTED_PENDING_PROCESSING)
    assert status.label == "uploaded"
    assert "no transcript" in status.truth_rule


def test_custody_read_model_accepts_057_handoff_fixture() -> None:
    custody = CustodyReadModel.model_validate(custody_read_model_fixture())

    assert custody.state == CustodyState.PARTIAL_UPLOADED
    assert custody.owner == CustodyOwner.PRODUCT_AUTOMATIC
    assert custody.retry_class == CustodyRetryClass.AUTOMATIC
    assert custody.normal_user_action == CustodyNormalUserAction.NONE
    assert custody.metadata_safety == CustodyMetadataSafety.METADATA_ONLY
    assert custody.model_dump(mode="json")["copy_key"] == "custody.uploading"


def test_problem_supports_metadata_safe_custody_extensions() -> None:
    problem = Problem.model_validate(
        {
            "title": "Policy blocked",
            "status": 409,
            "code": "policy_blocked",
            **custody_problem_extension_fixture(),
        }
    )

    assert problem.custody_owner == CustodyOwner.WORKSPACE_ADMIN
    assert problem.retry_class == CustodyRetryClass.PAUSED_UNTIL_ADMIN_ACTION
    assert problem.normal_user_action == CustodyNormalUserAction.COPY_SAFE_REPORT
    assert problem.metadata_safety == CustodyMetadataSafety.METADATA_ONLY


def test_meeting_list_item_exposes_structured_custody_for_058() -> None:
    fields = MeetingListItem.model_fields

    assert "custody" in fields
    assert fields["custody"].default is None


def test_desktop_sync_state_exposes_structured_custody_for_058() -> None:
    fields = DesktopRecordingSyncStateResponse.model_fields

    assert "custody" in fields
    assert fields["custody"].default is None
    payload = {
        "local_recording_id": "local-recording-057",
        "local_media_revision_id": "local-recording-057--initial",
        "meeting": {
            "meeting_id": str(uuid4()),
            "status": MeetingStatus.INGESTED_PENDING_PROCESSING,
            "processing_status": ProcessingStatus.PENDING_PROCESSING,
        },
        "media_revision": {"media_revision_id": str(uuid4())},
        "upload_session": {
            "status": UploadSessionStatus.FINALIZED,
            "accepted_bytes_by_track": {"microphone": 120},
        },
        "processing": {"status": ProcessingStatus.PENDING_PROCESSING},
        "review": {"available": True, "status": "processing"},
        "custody": custody_read_model_fixture(
            state="finalized",
            upload_state="finalized",
            processing_state="pending_processing",
            review_available=False,
            review_desktop_url=None,
            copy_key="custody.known_by_server",
        ),
    }
    response = DesktopRecordingSyncStateResponse.model_validate(payload)

    assert response.custody is not None
    assert response.custody.state == CustodyState.FINALIZED
    assert response.custody.upload_state == CustodyUploadState.FINALIZED


def test_custody_read_model_exposes_metadata_safe_incident_fields() -> None:
    payload = custody_read_model_fixture(
        state="retained_awaiting_condition",
        upload_state="blocked",
        owner="workspace_admin",
        retry_class="paused_until_admin_action",
        normal_user_action="copy_safe_report",
        safe_incident_available=True,
        copy_key="custody.needs_admin",
        incident={
            "safe_recording_identity": "server:meeting-057",
            "reason_category": "server_meeting_deleted",
            "problem_code": "server_meeting_deleted",
            "owner": "workspace_admin",
            "retry_class": "paused_until_admin_action",
            "normal_user_action": "copy_safe_report",
            "lifecycle_state": "retained_awaiting_condition",
            "server_identity_present": True,
            "metadata_safety": "metadata_only",
        },
    )

    custody = CustodyReadModel.model_validate(payload)

    assert custody.incident is not None
    assert custody.incident.metadata_safety == CustodyMetadataSafety.METADATA_ONLY
    assert custody.incident.owner == CustodyOwner.WORKSPACE_ADMIN
    assert custody.incident.problem_code == "server_meeting_deleted"
    assert "/Users/" not in custody.incident.safe_recording_identity
    assert "signed" not in custody.incident.model_dump_json().lower()


def test_desktop_sync_custody_mapping_is_structured_not_label_driven() -> None:
    meeting = SimpleNamespace(status=MeetingStatus.INGESTED_PENDING_PROCESSING)
    pending = _custody_read_model(
        meeting=meeting,
        session=None,
        accepted_bytes_by_track={},
        processing_status=ProcessingStatus.PENDING_PROCESSING,
        conflict=DesktopSyncConflict(),
        review_available=False,
        review_desktop_url=None,
    )
    ready = _custody_read_model(
        meeting=meeting,
        session=None,
        accepted_bytes_by_track={},
        processing_status=ProcessingStatus.PROCESSED,
        conflict=DesktopSyncConflict(),
        review_available=True,
        review_desktop_url="/desktop/meetings/ready-057",
    )

    assert pending.state == CustodyState.PROCESSING
    assert pending.upload_state == CustodyUploadState.FINALIZED
    assert pending.processing_state == CustodyProcessingState.PENDING_PROCESSING
    assert pending.normal_user_action == CustodyNormalUserAction.NONE
    assert pending.review_available is False
    assert ready.state == CustodyState.DELIVERED
    assert ready.normal_user_action == CustodyNormalUserAction.OPEN_REVIEW
    assert ready.review_desktop_url == "/desktop/meetings/ready-057"


def test_desktop_sync_populates_safe_incident_for_admin_blocker() -> None:
    meeting = SimpleNamespace(
        id=uuid4(),
        status=MeetingStatus.INGESTED_PENDING_PROCESSING,
        created_at=None,
        updated_at=None,
    )
    conflict = DesktopSyncConflict(
        state=SyncConflictState.SERVER_MEETING_DELETED,
        reason="server_meeting_deleted",
        next_action="stop_upload",
    )

    custody = _custody_read_model(
        meeting=meeting,
        session=None,
        accepted_bytes_by_track={},
        processing_status=ProcessingStatus.PENDING_PROCESSING,
        conflict=conflict,
        review_available=False,
        review_desktop_url=None,
    )

    assert custody.safe_incident_available is True
    assert custody.incident is not None
    assert custody.incident.owner == CustodyOwner.WORKSPACE_ADMIN
    assert custody.incident.normal_user_action == CustodyNormalUserAction.COPY_SAFE_REPORT
    assert custody.incident.problem_code == "server_meeting_deleted"
    assert custody.incident.safe_recording_identity.startswith("server:")
    assert "stop_upload" not in custody.incident.model_dump_json()


@pytest.mark.asyncio
async def test_recording_not_found_problem_keeps_local_custody_active() -> None:
    tenant_scope = TenantScope(
        organization_id=uuid4(),
        workspace_id=uuid4(),
        user_id=uuid4(),
        device_id=uuid4(),
    )

    with pytest.raises(ProblemDetail) as exc:
        await get_desktop_recording_sync_state(
            tenant_scope=tenant_scope,
            db=None,
            local_recording_id="local-only-recording",
            local_media_revision_id="local-only-recording--initial",
        )

    problem = exc.value
    response = problem_response(problem)
    body = json.loads(response.body)
    assert problem.status == 404
    assert body["code"] == "recording_not_found"
    assert body["custody_owner"] == "product_automatic"
    assert body["retry_class"] == "automatic"
    assert body["normal_user_action"] == "none"
    assert body["metadata_safety"] == "metadata_only"
