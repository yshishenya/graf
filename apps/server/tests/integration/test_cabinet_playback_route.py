from __future__ import annotations

import io
import wave

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import (
    audit_events,
    replace_retained_audio_with_test_wav,
    set_artifact_policy,
    set_meeting_deletion_state,
    set_retained_audio_source_status,
)
from twobrain_rec_server.domain.statuses import DeletionState, TrackRole

FORBIDDEN_MARKERS = (
    b"storage_object_key",
    b"sha256",
    b"X-Amz",
    b"private-run-id",
    b"fixture-mediascribe-private-job-id",
)


def _samples(body: bytes) -> list[int]:
    with wave.open(io.BytesIO(body), "rb") as wav:
        frames = wav.readframes(wav.getnframes())
    return [int.from_bytes(frames[index : index + 2], "little", signed=True) for index in range(0, len(frames), 2)]


def test_owner_playback_route_returns_combined_review_audio_without_storage_url(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, audio_download="allowed")
    replace_retained_audio_with_test_wav(client, seeds.ready_id)

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback", headers=auth_headers())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.headers["content-disposition"].startswith("inline;")
    assert _samples(response.content) == [1000, 1000, 2000, 2000]
    for marker in FORBIDDEN_MARKERS:
        assert marker not in response.content
    assert [event.event_type for event in audit_events(client, seeds.ready_id)] == [
        "playback_requested",
        "playback_completed",
    ]


def test_playback_route_blocks_foreign_workspace_without_disclosing_meeting(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.foreign_id}/playback", headers=auth_headers())

    assert response.status_code == 404
    assert response.json()["code"] == "meeting_not_found"
    assert audit_events(client, seeds.foreign_id) == []


def test_playback_route_blocks_disabled_policy_with_safe_audit(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback", headers=auth_headers())

    assert response.status_code == 409
    assert response.json()["code"] == "playback_unavailable"
    body = response.content
    for marker in FORBIDDEN_MARKERS:
        assert marker not in body
    events = audit_events(client, seeds.ready_id)
    assert [(event.event_type, event.outcome, event.policy_reason) for event in events] == [
        ("playback_denied", "denied", "Workspace policy disables this artifact egress.")
    ]
    assert events[0].metadata_json == {
        "artifact_class": "audio",
        "outcome": "denied",
        "request_class": "playback",
    }


def test_playback_route_blocks_deleting_meeting_with_safe_audit(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, audio_download="allowed")
    set_meeting_deletion_state(client, seeds.ready_id, DeletionState.REQUESTED.value)

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback", headers=auth_headers())

    assert response.status_code == 404
    assert response.json()["code"] == "meeting_not_found"
    assert audit_events(client, seeds.ready_id) == []


def test_playback_route_blocks_processing_and_failed_reviews_even_when_audio_policy_allows(client) -> None:
    seeds = seed_cabinet_meetings(client)
    for meeting_id in (seeds.processing_id, seeds.failed_id):
        set_artifact_policy(client, meeting_id, audio_download="allowed")
        replace_retained_audio_with_test_wav(client, meeting_id)

        response = client.get(f"/api/v1/cabinet/meetings/{meeting_id}/playback", headers=auth_headers())

        assert response.status_code == 409
        assert response.json()["code"] == "playback_unavailable"
        events = audit_events(client, meeting_id)
        assert [(event.event_type, event.outcome) for event in events] == [("playback_denied", "denied")]


def test_playback_route_requires_both_retained_sources_for_review_audio(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, audio_download="allowed")
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    set_retained_audio_source_status(client, seeds.ready_id, TrackRole.SYSTEM, "purged")

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback", headers=auth_headers())

    assert response.status_code == 409
    assert response.json()["code"] == "playback_unavailable"
    events = audit_events(client, seeds.ready_id)
    assert [(event.event_type, event.outcome, event.policy_reason) for event in events] == [
        ("playback_denied", "denied", "missing_audio_source")
    ]
