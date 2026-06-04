from twobrain_rec_server.domain.statuses import MeetingStatus, UploadSessionStatus
from twobrain_rec_server.ingest.desktop_status import meeting_desktop_status, upload_session_desktop_status


def test_finalized_upload_maps_to_uploaded_label_without_processing_claim() -> None:
    status = upload_session_desktop_status(UploadSessionStatus.FINALIZED)
    assert status.label == "uploaded"
    assert "processing has not necessarily started" in status.truth_rule


def test_ingested_meeting_maps_to_uploaded_without_dashboard_claim() -> None:
    status = meeting_desktop_status(MeetingStatus.INGESTED_PENDING_PROCESSING)
    assert status.label == "uploaded"
    assert "no transcript" in status.truth_rule
