import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.cabinet import (
    PRIVATE_EXTERNAL_JOB_ID,
    SAFE_SECOND_TRANSCRIPT_TEXT,
    SAFE_TRANSCRIPT_TEXT,
    create_outcome_ready_meeting,
    seed_cabinet_meetings,
)
from tests.fixtures.cabinet_access import (
    add_retained_playback_m4a,
    replace_retained_audio_with_test_wav,
)
from tests.fixtures.cabinet_components import COMPONENT_FORBIDDEN_MARKERS, COMPONENT_SAFE_FIXTURE
from tests.fixtures.processing import create_finalized_meeting, enable_processing_autostart
from twobrain_rec_server.cabinet.templates import get_cabinet_templates
from twobrain_rec_server.db.models import MeetingOutcomeItem
from twobrain_rec_server.outcomes.service import ensure_outcomes_for_meeting

SERVER_ROOT = Path(__file__).resolve().parents[2] / "src" / "twobrain_rec_server"


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


def test_cabinet_component_fixtures_are_metadata_safe() -> None:
    template = get_cabinet_templates().from_string(
        """
        {% import "cabinet/components/sections.html" as sections %}
        {{ sections.workspace_header(fixture.workspace_name, fixture.workspace_subtitle, "2B") }}
        {{ sections.meeting_row(fixture.meeting_title, "/meetings/synthetic", fixture.status_label, "audio", "26 июн") }}
        """
    )

    rendered = template.render(fixture=COMPONENT_SAFE_FIXTURE)
    evidence = _dump_json({"fixture": COMPONENT_SAFE_FIXTURE, "rendered": rendered})

    for marker in COMPONENT_FORBIDDEN_MARKERS:
        assert marker not in evidence


def test_create_meeting_rejects_unsafe_title_without_echoing_raw_input(client) -> None:
    unsafe_url = "https" + "://meet." + "example" + ".com/private"
    unsafe_email = "john" + "@example" + ".com"
    unsafe_token = "token" + "=secret"
    unsafe_title = f"{unsafe_url} {unsafe_email} {unsafe_token}"

    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "unsafe-title-input",
            "title": unsafe_title,
            "duration_seconds": 60,
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "unsafe_meeting_title"
    assert unsafe_url not in response.text
    assert unsafe_email not in response.text
    assert unsafe_token not in response.text

    unsafe_control_title = "Safe" + chr(0) + "Title"
    control_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "unsafe-control-title",
            "title": unsafe_control_title,
            "duration_seconds": 60,
        },
    )

    assert control_response.status_code in {400, 422}
    assert control_response.json()["code"] in {"unsafe_meeting_title", "request_validation_error"}
    assert "\\u0000" not in control_response.text

    bare_link = "meet.example.test/abc-defg-hij"
    bare_link_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "unsafe-bare-link-title",
            "title": bare_link,
            "duration_seconds": 60,
        },
    )

    assert bare_link_response.status_code == 400
    assert bare_link_response.json()["code"] == "unsafe_meeting_title"
    assert bare_link not in bare_link_response.text

    ordinary_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "ordinary-sk-dash-title",
            "title": "Risk-review",
            "duration_seconds": 60,
        },
    )

    assert ordinary_response.status_code == 200


def test_rendered_cabinet_pages_do_not_include_storage_or_dependency_identifiers(client) -> None:
    seeds = seed_cabinet_meetings(client)
    forbidden = {
        PRIVATE_EXTERNAL_JOB_ID,
        "storage_object_key",
        "share_token_hash",
        "signed_url",
        "X-Amz",
        "/Users/",
        "mediascribe_api_key",
        "private-run-id",
    }

    list_response = client.get("/meetings", headers=auth_headers())
    detail_response = client.get(f"/meetings/{seeds.ready_id}", headers=auth_headers())

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    body = list_response.text + detail_response.text
    for marker in forbidden:
        assert marker not in body


def test_ordinary_meeting_list_does_not_render_internal_state_fields(client) -> None:
    seed_cabinet_meetings(client)

    response = client.get("/desktop/meetings", headers=auth_headers())

    assert response.status_code == 200
    for marker in {
        "local_recording_id",
        "processing_status",
        "status_reason",
        "mediascribe",
        "schema_version",
        "/Users/",
    }:
        assert marker not in response.text.lower()


def test_manual_upload_surface_and_error_copy_are_metadata_safe(client) -> None:
    response = client.get("/meetings", headers=auth_headers())

    assert response.status_code == 200
    forbidden = {
        "storage_object_key",
        "signed_url",
        "object_key",
        "private_path",
        "raw_transcript",
        "raw_audio",
        "external_job_id",
        "mediascribe_job",
        "/Users/",
    }
    for marker in forbidden:
        assert marker not in response.text

    script = (SERVER_ROOT / "cabinet" / "static" / "cabinet" / "cabinet.js").read_text()
    assert "mediascribe_job" not in script


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


def test_cabinet_list_omits_stored_outcome_item_text(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "no-secret-outcome-list")
    asyncio.run(ensure_outcomes_for_meeting(client.app_state["sessionmaker"], meeting_id=meeting_id))
    outcome_text = asyncio.run(_first_outcome_text(client, meeting_id))
    assert outcome_text

    response = client.get("/api/v1/cabinet/meetings", headers=auth_headers())

    assert response.status_code == 200
    body = _dump_json(response.json())
    assert outcome_text not in body
    assert "source_refs" not in body
    assert "storage_object_key" not in body


def test_finalize_autostart_payloads_do_not_egress_content_or_secrets(client) -> None:
    enable_processing_autostart(client, FakeTemporalClient())

    finalized = create_finalized_meeting(client, "finalize-autostart-no-secret")
    status = client.get(f"/api/v1/meetings/{finalized['meeting']['meeting_id']}/processing", headers=auth_headers())

    assert status.status_code == 200
    body = _dump_json({"finalize": finalized["finalize"], "processing": status.json()})
    forbidden = {
        "transcript_text",
        "transcriptText",
        "raw_audio",
        "rawAudio",
        "audio_download_url",
        "signed_url",
        "api_key",
        "mediascribe_api_key",
        "storage_object_key",
        "private-run-id",
        "local speaker",
        "remote speaker",
    }
    for marker in forbidden:
        assert marker not in body


async def _first_outcome_text(client, meeting_id) -> str:
    async with client.app_state["sessionmaker"]() as db:
        text = await db.scalar(
            select(MeetingOutcomeItem.text)
            .where(MeetingOutcomeItem.meeting_id == meeting_id)
            .where(MeetingOutcomeItem.text.is_not(None))
            .order_by(MeetingOutcomeItem.category, MeetingOutcomeItem.sequence)
        )
        assert text is not None
        return text


def test_playback_processing_denial_does_not_egress_audio_or_storage_identifiers(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.processing_id}/playback", headers=auth_headers())

    assert response.status_code == 409
    body = _dump_json(response.json())
    forbidden = {
        SAFE_TRANSCRIPT_TEXT,
        SAFE_SECOND_TRANSCRIPT_TEXT,
        PRIVATE_EXTERNAL_JOB_ID,
        "storage_object_key",
        "sha256",
        "private-run-id",
        "signed_url",
        "X-Amz",
        "raw_audio",
    }
    for marker in forbidden:
        assert marker not in body


def test_playback_range_response_does_not_egress_storage_identifiers_or_signed_urls(client) -> None:
    seeds = seed_cabinet_meetings(client)
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    add_retained_playback_m4a(client, seeds.ready_id, b"0123456789abcdefXYZ")

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback",
        headers={**auth_headers(), "Range": "bytes=0-15"},
    )

    assert response.status_code == 206
    assert response.headers["accept-ranges"] == "bytes"
    body = response.content + str(dict(response.headers)).encode("utf-8")
    forbidden = {
        b"storage_object_key",
        b"sha256",
        b"private-run-id",
        b"signed_url",
        b"X-Amz",
        b"raw_audio",
    }
    for marker in forbidden:
        assert marker not in body
