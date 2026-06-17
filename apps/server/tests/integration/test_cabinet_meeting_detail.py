from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import (
    PRIVATE_EXTERNAL_JOB_ID,
    SAFE_SECOND_TRANSCRIPT_TEXT,
    SAFE_TRANSCRIPT_TEXT,
    create_summary_reported_meeting,
    seed_cabinet_meetings,
)


def test_cabinet_ready_detail_returns_ordered_transcript_speakers_and_provenance(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert [segment["text"] for segment in payload["transcript"]["segments"]] == [
        SAFE_TRANSCRIPT_TEXT,
        SAFE_SECOND_TRANSCRIPT_TEXT,
    ]
    assert [segment["source_role"] for segment in payload["transcript"]["segments"]] == [
        "local_microphone",
        "incoming_system",
    ]
    assert payload["provenance"]["source_roles"] == ["local_microphone", "incoming_system"]
    assert payload["provenance"]["processing_dependency"] == "mediascribe"
    assert payload["playback"]["available"] is True
    assert {speaker["label"] for speaker in payload["speakers"]["speakers"]} == {"Speaker 1", "Speaker 2"}
    assert PRIVATE_EXTERNAL_JOB_ID not in response.text


def test_cabinet_processing_failed_and_partial_detail_states_are_truthful(client) -> None:
    seeds = seed_cabinet_meetings(client)

    processing = client.get(f"/api/v1/cabinet/meetings/{seeds.processing_id}", headers=auth_headers()).json()
    failed = client.get(f"/api/v1/cabinet/meetings/{seeds.failed_id}", headers=auth_headers()).json()
    partial = client.get(f"/api/v1/cabinet/meetings/{seeds.partial_id}", headers=auth_headers()).json()

    assert processing["processing"]["state"] == "processing"
    assert processing["processing"]["next_action"] == "wait"
    assert processing["transcript"]["available"] is False
    assert processing["notes_action_truth"]["summary"]["state"] == "processing"
    assert processing["notes_action_truth"]["action_items"]["state"] == "processing"
    assert failed["processing"]["state"] == "failed"
    assert failed["processing"]["reason_code"] == "mediascribe_validation_failed"
    assert failed["processing"]["next_action"] == "contact_operator"
    assert failed["notes_action_truth"]["summary"]["state"] == "blocked"
    assert failed["notes_action_truth"]["decisions"]["state"] == "blocked"
    assert partial["processing"]["state"] == "partial"
    assert partial["transcript"]["available"] is True
    assert partial["speakers"]["available"] is False
    assert partial["notes_action_truth"]["summary"]["state"] == "deferred"
    assert partial["notes_action_truth"]["followups"]["state"] == "deferred"


def test_cabinet_summary_reported_without_stored_output_is_blocked(client) -> None:
    meeting_id = create_summary_reported_meeting(client)

    response = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())

    assert response.status_code == 200
    truth = response.json()["notes_action_truth"]
    assert truth["summary"]["state"] == "blocked"
    assert truth["summary"]["copy_key"] == "notes.summary.blocked_missing_stored_output"
    assert truth["decisions"]["state"] == "deferred"
    assert truth["action_items"]["state"] == "deferred"


def test_cabinet_detail_denies_foreign_meeting_without_existence_proof(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.foreign_id}", headers=auth_headers())

    assert response.status_code == 404
    assert response.json()["code"] == "meeting_not_found"
    assert "Foreign private meeting" not in response.text


def test_cabinet_ready_and_processing_web_detail_shells(client) -> None:
    seeds = seed_cabinet_meetings(client)

    ready = client.get(f"/meetings/{seeds.ready_id}", headers=auth_headers())
    processing = client.get(f"/meetings/{seeds.processing_id}", headers=auth_headers())

    assert ready.status_code == 200
    assert "Notes" in ready.text
    assert "Recording &amp; Transcript" in ready.text
    assert SAFE_TRANSCRIPT_TEXT in ready.text
    assert "Assign speakers" in ready.text
    assert "Assistant" in ready.text
    assert "Template" in ready.text
    assert "Summary" in ready.text
    assert "Action Items" in ready.text
    assert "Outcomes deferred" in ready.text
    assert "AI notes are reserved for a later feature" not in ready.text
    assert "016" not in ready.text
    assert "Access" in ready.text
    assert "Team visibility" in ready.text
    assert "Artifacts" in ready.text
    assert processing.status_code == 200
    assert "Транскрипт готовится" in processing.text
    assert "Outcomes processing" in processing.text
    assert SAFE_TRANSCRIPT_TEXT not in processing.text


def test_cabinet_embedded_ready_detail_keeps_review_governance_and_removes_native_capture_copy(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/desktop/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    assert "desktop-embedded" in response.text
    assert "Transcript" in response.text
    assert "Recording &amp; Transcript" not in response.text
    assert SAFE_TRANSCRIPT_TEXT in response.text
    assert "Open in browser" in response.text
    assert "Access" in response.text
    assert "Share" in response.text
    assert "Report" in response.text
    assert "Record live" not in response.text
    assert "Krisp Devices" not in response.text
