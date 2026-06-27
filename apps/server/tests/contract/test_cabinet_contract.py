import json

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.processing import create_finalized_meeting


def test_cabinet_openapi_exposes_list_and_detail_contracts(client) -> None:
    schema = client.get("/openapi.json").json()

    assert "/api/v1/cabinet/meetings" in schema["paths"]
    assert "/api/v1/cabinet/meetings/{meeting_id}" in schema["paths"]
    assert schema["paths"]["/api/v1/cabinet/meetings"]["get"]["operationId"] == "listCabinetMeetings"
    assert schema["paths"]["/api/v1/cabinet/meetings/{meeting_id}"]["get"]["operationId"] == "getCabinetMeetingReview"


def test_cabinet_list_contract_shape_and_future_slots(client) -> None:
    seed_cabinet_meetings(client)

    response = client.get("/api/v1/cabinet/meetings", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"items", "filters", "generated_at"}
    assert payload["filters"] == {"q": None, "status": None, "access": None, "sort": "updated_desc"}
    assert len(payload["items"]) == 4
    first = payload["items"][0]
    assert {
        "meeting_id",
        "title",
        "duration_seconds",
        "status",
        "status_label",
        "primary_action",
        "transcript_available",
        "diarization_available",
        "notes_available",
        "access",
        "artifacts",
        "governance",
        "future_slots",
    }.issubset(first)
    assert set(first["governance"]) == {"share", "export", "download", "retention", "delete"}
    assert [slot["label"] for slot in first["future_slots"]] == ["Star", "Tag", "Access", "More"]


def test_cabinet_ready_detail_contract_shape(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert {
        "meeting",
        "provenance",
        "processing",
        "transcript",
        "speakers",
        "notes",
        "notes_action_truth",
        "playback",
        "governance",
        "access",
        "share",
        "artifacts",
        "activity",
        "deletion_truth_copy",
        "calendar_roster",
        "assistant",
        "template",
    } == set(payload)
    assert payload["meeting"]["status"] == "ready"
    assert payload["processing"]["state"] == "ready"
    assert payload["transcript"]["available"] is True
    assert payload["transcript"]["segments"][0]["timestamp_label"] == "00:00"
    assert payload["transcript"]["segments"][0]["speaker_label"] == "Speaker 1"
    assert payload["speakers"]["assignment_state"] == "reserved"
    assert payload["notes"] == {
        "available": False,
        "sections": [],
        "unavailable_reason": "generation_future",
    }
    assert payload["governance"]["delete"]["destructive"] is True
    assert "2brain Rec" in payload["governance"]["delete"]["label"]
    assert payload["access"]["state"] == "owner"
    assert payload["share"]["public_link_state"] == "disabled_by_default"
    assert payload["activity"]["redaction_state"] == "metadata_only"
    assert payload["calendar_roster"] is None


def test_cabinet_detail_includes_media_revision_provenance(client) -> None:
    finalized = create_finalized_meeting(client, "cabinet-media-revision-042")
    meeting = finalized["meeting"]

    response = client.get(f"/api/v1/cabinet/meetings/{meeting['meeting_id']}", headers=auth_headers())

    assert response.status_code == 200
    provenance = response.json()["provenance"]
    assert provenance["media_revision_id"] == meeting["media_revision"]["media_revision_id"]
    assert provenance["local_media_revision_id"] == meeting["local_media_revision_id"]


def test_cabinet_embedded_routes_are_contractually_bounded(client) -> None:
    seeds = seed_cabinet_meetings(client)

    list_response = client.get("/desktop/meetings", headers=auth_headers())
    detail_response = client.get(f"/desktop/meetings/{seeds.ready_id}", headers=auth_headers())

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    html = list_response.text + detail_response.text
    for forbidden in [
        "Record live",
        "Screen Recording",
        "Audio Recording",
        "Stop recording",
        "Krisp Devices",
        "Noise Cancellation",
        "Accent Conversion",
        "Diagnostics export",
        "local path",
    ]:
        assert forbidden not in html
    assert "desktop-embedded" in html
    assert 'aria-label="Статус медиа-ревизии"' in html
    assert "data-media-revision-id=" in html


def test_cabinet_review_html_has_localized_accessible_compact_revision_status(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/desktop/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    html = response.text
    assert '<html lang="ru">' in html
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in html
    assert 'class="app-shell desktop-embedded"' in html
    assert 'aria-label="Статус медиа-ревизии"' in html
    assert 'data-media-revision-id="' in html
    assert 'data-local-media-revision-id="' in html
    assert "Медиа-ревизия" in html
    assert "detail-layout" in html
    assert "detail-playback" in html


def test_cabinet_denied_detail_is_privacy_preserving(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.foreign_id}", headers=auth_headers())

    assert response.status_code == 404
    body = json.dumps(response.json(), ensure_ascii=False)
    assert "Foreign private meeting" not in body
    assert "foreign-private-recording" not in body
