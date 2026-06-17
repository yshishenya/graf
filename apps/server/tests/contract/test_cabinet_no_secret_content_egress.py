import json

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import (
    PRIVATE_EXTERNAL_JOB_ID,
    SAFE_SECOND_TRANSCRIPT_TEXT,
    SAFE_TRANSCRIPT_TEXT,
    seed_cabinet_meetings,
)


def _dump_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def test_cabinet_list_does_not_egress_transcript_or_dependency_secrets(client) -> None:
    seed_cabinet_meetings(client)

    response = client.get("/api/v1/cabinet/meetings", headers=auth_headers())

    assert response.status_code == 200
    body = _dump_json(response.json())
    assert SAFE_TRANSCRIPT_TEXT not in body
    assert SAFE_SECOND_TRANSCRIPT_TEXT not in body
    assert PRIVATE_EXTERNAL_JOB_ID not in body
    assert "storage_object_key" not in body
    assert "sha256" not in body
    assert "private-run-id" not in body


def test_cabinet_ready_detail_keeps_dependency_and_storage_identifiers_private(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    body = _dump_json(response.json())
    assert SAFE_TRANSCRIPT_TEXT in body
    assert PRIVATE_EXTERNAL_JOB_ID not in body
    assert "storage_object_key" not in body
    assert "sha256" not in body
    assert "private-run-id" not in body


def test_cabinet_processing_detail_does_not_invent_transcript_notes_or_success(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.processing_id}", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    body = _dump_json(payload)
    assert payload["processing"]["state"] == "processing"
    assert payload["transcript"]["segments"] == []
    assert payload["notes"]["available"] is False
    assert SAFE_TRANSCRIPT_TEXT not in body
    assert "share_token_hash" not in body
    assert "storage_object_key" not in body
    assert payload["share"]["public_link_state"] == "disabled_by_default"


def test_notes_action_truth_egresses_only_metadata_safe_states(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    truth = response.json()["notes_action_truth"]
    body = _dump_json(truth)
    assert truth["summary"]["state"] in {"available", "processing", "blocked", "unavailable", "deferred"}
    assert truth["action_items"]["copy_key"].startswith("notes.")
    assert SAFE_TRANSCRIPT_TEXT not in body
    assert SAFE_SECOND_TRANSCRIPT_TEXT not in body
    assert PRIVATE_EXTERNAL_JOB_ID not in body
    assert "storage_object_key" not in body
    assert "session_token" not in body
