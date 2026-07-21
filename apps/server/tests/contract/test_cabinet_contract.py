import json
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import WORKSPACE_ID
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.db.models import RecordingCalendarContextLink

CALENDAR_ROSTER_NAMES = (
    "Synthetic Calendar Invitee",
    "Synthetic Calendar Room",
    "Synthetic Calendar Resource",
)
CALENDAR_ROSTER_EMAIL_SENTINEL = "calendar-invitee-private@example.test"


def test_cabinet_openapi_exposes_list_and_detail_contracts(client) -> None:
    schema = client.get("/openapi.json").json()

    assert "/api/v1/cabinet/meetings" in schema["paths"]
    assert "/api/v1/cabinet/meetings/{meeting_id}" in schema["paths"]
    assert (
        schema["paths"]["/api/v1/cabinet/meetings"]["get"]["operationId"] == "listCabinetMeetings"
    )
    assert (
        schema["paths"]["/api/v1/cabinet/meetings/{meeting_id}"]["get"]["operationId"]
        == "getCabinetMeetingReview"
    )


def test_cabinet_list_contract_shape_and_future_slots(client) -> None:
    seed_cabinet_meetings(client)

    response = client.get("/api/v1/cabinet/meetings", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"items", "filters", "generated_at"}
    assert payload["filters"] == {"q": None, "status": None, "access": None, "sort": "updated_desc"}

    explicit_updated = client.get(
        "/api/v1/cabinet/meetings?sort=updated_desc",
        headers=auth_headers(),
    )
    assert explicit_updated.status_code == 200
    assert explicit_updated.json()["filters"]["sort"] == "updated_desc"
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
        "content_exports",
        "activity",
        "deletion_truth_copy",
        "calendar_context",
        "calendar_context_detail",
        "calendar_roster",
        "assistant",
        "template",
    } == set(payload)
    assert payload["meeting"]["status"] == "ready"
    assert payload["processing"]["state"] == "ready"
    assert payload["transcript"]["available"] is True
    assert payload["transcript"]["segments"][0]["timestamp_label"] == "00:00"
    assert payload["transcript"]["segments"][0]["speaker_label"] == "SPEAKER_00"
    assert payload["speakers"]["assignment_state"] == "reserved"
    assert payload["notes"] == {
        "available": False,
        "sections": [],
        "unavailable_reason": "generation_future",
    }
    assert payload["governance"]["delete"]["destructive"] is True
    assert "GRAF" in payload["governance"]["delete"]["label"]
    assert payload["access"]["state"] == "owner"
    assert payload["share"]["public_link_state"] == "disabled_by_default"
    assert payload["activity"]["redaction_state"] == "metadata_only"
    assert payload["calendar_context"] == {
        "state": "skipped_offline_or_unknown",
        "label": "Без контекста календаря",
        "reason_label": "Офлайн-запись не сопоставляется",
        "title_source": "generic",
        "needs_owner_action": False,
    }
    assert payload["calendar_roster"] is None


def test_cabinet_detail_includes_media_revision_provenance(client) -> None:
    finalized = create_finalized_meeting(client, "cabinet-media-revision-042")
    meeting = finalized["meeting"]

    response = client.get(
        f"/api/v1/cabinet/meetings/{meeting['meeting_id']}", headers=auth_headers()
    )

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


def test_cabinet_calendar_roster_is_metadata_only_and_does_not_relabel_speakers(
    client,
) -> None:
    # FR-020-FR-022/FR-040/FR-044/SC-008: roster context cannot become identity or access.
    seeds = seed_cabinet_meetings(client)
    path = f"/api/v1/cabinet/meetings/{seeds.ready_id}"
    before_response = client.get(path, headers=auth_headers())
    assert before_response.status_code == 200
    before = before_response.json()

    _attach_matched_calendar_roster(client, seeds.ready_id)
    after_response = client.get(path, headers=auth_headers())

    assert after_response.status_code == 200
    after = after_response.json()
    roster = after["calendar_roster"]
    assert roster["available"] is True
    assert roster["roster_state"] == "available"
    assert roster["participant_count"] == len(CALENDAR_ROSTER_NAMES)
    assert roster["source"] == "calendar"
    assert tuple(participant["display_name"] for participant in roster["participants"]) == (
        CALENDAR_ROSTER_NAMES
    )
    assert [participant["participant_kind"] for participant in roster["participants"]] == [
        "required_attendee",
        "room",
        "resource",
    ]

    assert after["transcript"] == before["transcript"]
    assert after["speakers"] == before["speakers"]
    assert [segment["speaker_label"] for segment in after["transcript"]["segments"]] == [
        "SPEAKER_00",
        "SPEAKER_01",
    ]
    assert [speaker["label"] for speaker in after["speakers"]["speakers"]] == [
        "SPEAKER_00",
        "SPEAKER_01",
    ]
    assert after["access"] == before["access"]
    assert after["share"] == before["share"]
    assert after["governance"] == before["governance"]
    assert {
        "recipients",
        "report_recipients",
        "summary_recipients",
        "email_recipients",
    }.isdisjoint(after)

    identity_or_delivery_surfaces = json.dumps(
        {
            "transcript": after["transcript"],
            "speakers": after["speakers"],
            "access": after["access"],
            "share": after["share"],
            "governance": after["governance"],
        },
        ensure_ascii=False,
    )
    for forbidden in (*CALENDAR_ROSTER_NAMES, CALENDAR_ROSTER_EMAIL_SENTINEL):
        assert forbidden not in identity_or_delivery_surfaces
    assert CALENDAR_ROSTER_EMAIL_SENTINEL not in after_response.text


def _attach_matched_calendar_roster(client, meeting_id: UUID) -> None:
    async def attach() -> None:
        async with client.app_state["sessionmaker"]() as db:
            context = await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.workspace_id == WORKSPACE_ID,
                    RecordingCalendarContextLink.meeting_id == meeting_id,
                )
            )
            assert context is not None
            context.context_state = "matched_auto"
            context.context_confidence = "high"
            context.context_reasons_json = ["single_fresh_candidate"]
            context.title_source = "calendar"
            context.roster_source = "calendar"
            context.manual_override_state = "none"
            context.safe_reason_code = "single_fresh_candidate"
            context.decision_source = "automatic"
            context.matcher_version = "calendar_auto_match_v1"
            context.candidate_event_ids_json = []
            context.candidate_count = 0
            context.matched_title = "Synthetic Calendar Review"
            context.matched_title_state = "available"
            context.matched_roster_json = [
                {
                    "participant_kind": "required_attendee",
                    "response_status": "accepted",
                    "display_name": CALENDAR_ROSTER_NAMES[0],
                    "email": CALENDAR_ROSTER_EMAIL_SENTINEL,
                    "email_present": True,
                    "workspace_relation": "external",
                    "recipient_candidate_class": "external_attendee",
                },
                {
                    "participant_kind": "room",
                    "response_status": "accepted",
                    "display_name": CALENDAR_ROSTER_NAMES[1],
                    "email_present": False,
                    "workspace_relation": "resource",
                    "recipient_candidate_class": "room",
                },
                {
                    "participant_kind": "resource",
                    "response_status": "accepted",
                    "display_name": CALENDAR_ROSTER_NAMES[2],
                    "email_present": False,
                    "workspace_relation": "resource",
                    "recipient_candidate_class": "resource",
                },
            ]
            context.matched_roster_state = "available"
            context.matched_roster_count = len(CALENDAR_ROSTER_NAMES)
            await db.commit()

    client.portal.call(attach)
