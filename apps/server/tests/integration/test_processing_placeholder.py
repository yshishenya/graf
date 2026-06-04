from tests.contract.test_ingest_openapi_contract import auth_headers
from twobrain_rec_server.ingest.processing_placeholder import get_processing_placeholder


def test_processing_placeholder_has_no_workflow_or_mediascribe_ids(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "placeholder", "duration_seconds": 60},
    ).json()
    placeholder = get_processing_placeholder(__import__("uuid").UUID(meeting["meeting_id"]))
    assert placeholder is not None
    assert placeholder.workflow_id is None
    assert placeholder.mediascribe_job_id is None
