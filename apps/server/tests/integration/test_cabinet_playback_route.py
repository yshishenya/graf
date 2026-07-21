from __future__ import annotations

import asyncio
import io
import wave

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import (
    SHARED_USER_ID,
    add_retained_playback_m4a,
    add_workspace_user,
    audit_events,
    auth_headers_for,
    replace_retained_audio_with_test_wav,
    set_artifact_policy,
    set_meeting_deletion_state,
    set_retained_audio_source_status,
)
from twobrain_rec_server.db.models import TrackArtifact
from twobrain_rec_server.domain.statuses import DeletionState, TrackRole

FORBIDDEN_MARKERS = (
    b"storage_object_key",
    b"sha256",
    b"X-Amz",
    b"private-run-id",
    b"fixture-mediascribe-private-job-id",
)


class PlaybackStreamingOnlyStorage:
    def __init__(self, delegate: object) -> None:
        self.delegate = delegate

    def get_bytes(self, _object_key: str) -> bytes:
        raise AssertionError("playback route must not load full audio objects into memory")

    async def get_bytes_async(self, _object_key: str) -> bytes:
        raise AssertionError("playback route must not load full audio objects into memory")

    def stat_object(self, object_key: str):
        return self.delegate.stat_object(object_key)

    async def stat_object_async(self, object_key: str):
        return await self.delegate.stat_object_async(object_key)

    def iter_object(self, object_key: str, *, offset: int = 0, length: int | None = None):
        return self.delegate.iter_object(object_key, offset=offset, length=length)


class PlaybackLoopCheckingStorage(PlaybackStreamingOnlyStorage):
    def iter_object(self, object_key: str, *, offset: int = 0, length: int | None = None):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise AssertionError(
                "playback route must not initialize sync storage streams on the event loop"
            )
        return self.delegate.iter_object(object_key, offset=offset, length=length)


class PlaybackReaderFailingStorage(PlaybackStreamingOnlyStorage):
    def iter_object(self, _object_key: str, *, offset: int = 0, length: int | None = None):
        raise RuntimeError("storage backend unavailable")


def _samples(body: bytes) -> list[int]:
    with wave.open(io.BytesIO(body), "rb") as wav:
        frames = wav.readframes(wav.getnframes())
    return [
        int.from_bytes(frames[index : index + 2], "little", signed=True)
        for index in range(0, len(frames), 2)
    ]


def test_owner_playback_route_returns_combined_review_audio_without_storage_url(client) -> None:
    seeds = seed_cabinet_meetings(client)
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    m4a_body = add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A review")

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback", headers=auth_headers()
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mp4")
    assert response.headers["content-disposition"].startswith("inline;")
    assert response.content == m4a_body
    for marker in FORBIDDEN_MARKERS:
        assert marker not in response.content
    assert [event.event_type for event in audit_events(client, seeds.ready_id)] == [
        "playback_requested",
        "playback_stream_prepared",
    ]


def test_owner_playback_route_prefers_stored_m4a_review_artifact(client) -> None:
    seeds = seed_cabinet_meetings(client)
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    m4a_body = add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A review")

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback", headers=auth_headers()
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mp4")
    assert response.headers["content-disposition"] == 'inline; filename="meeting-review.m4a"'
    assert response.content == m4a_body
    events = audit_events(client, seeds.ready_id)
    assert events[-1].metadata_json["source_mode"] == "stored_review_m4a"
    for marker in FORBIDDEN_MARKERS:
        assert marker not in response.content


def test_owner_playback_route_reports_storage_unavailable_when_stored_m4a_object_is_missing(
    client,
) -> None:
    seeds = seed_cabinet_meetings(client)
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A stale")
    client.app_state["storage"].delete_object(f"tests/cabinet/{seeds.ready_id}/meeting-review.m4a")

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback", headers=auth_headers()
    )

    assert response.status_code == 503
    assert response.json()["code"] == "storage_unavailable"
    events = audit_events(client, seeds.ready_id)
    assert [(event.event_type, event.outcome, event.policy_reason) for event in events] == [
        ("playback_denied", "denied", "storage_unavailable")
    ]


def test_owner_playback_route_rejects_stale_storage_size_before_serving_headers(client) -> None:
    seeds = seed_cabinet_meetings(client)
    m4a_body = add_retained_playback_m4a(client, seeds.ready_id, b"0123456789abcdef")
    object_key = f"tests/cabinet/{seeds.ready_id}/meeting-review.m4a"
    client.app_state["storage"].objects[object_key] = m4a_body[:-1]

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback", headers=auth_headers()
    )

    assert response.status_code == 409
    assert response.json()["code"] == "review_audio_unavailable"
    events = audit_events(client, seeds.ready_id)
    assert [(event.event_type, event.outcome, event.policy_reason) for event in events] == [
        ("playback_denied", "denied", "storage_object_size_mismatch")
    ]


def test_owner_playback_route_requires_m4a_playback_metadata(client) -> None:
    seeds = seed_cabinet_meetings(client)
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A wrong-metadata")

    async def mark_wrong_codec() -> None:
        async with client.app_state["sessionmaker"]() as db:
            artifact = await db.scalar(
                select(TrackArtifact).where(
                    TrackArtifact.meeting_id == seeds.ready_id,
                    TrackArtifact.track_role == TrackRole.PLAYBACK.value,
                )
            )
            assert artifact is not None
            artifact.codec = "wav-pcm-s16le"
            await db.commit()

    asyncio.run(mark_wrong_codec())

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback", headers=auth_headers()
    )

    assert response.status_code == 409
    assert response.json()["code"] == "playback_unavailable"
    assert [
        (event.event_type, event.outcome, event.policy_reason)
        for event in audit_events(client, seeds.ready_id)
    ] == [("playback_denied", "denied", "canonical_artifact_missing")]


def test_owner_playback_route_reports_storage_unavailable_when_reader_is_missing(client) -> None:
    seeds = seed_cabinet_meetings(client)
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A storage")
    original_storage = client.app.state.storage
    client.app.state.storage = object()
    try:
        response = client.get(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback", headers=auth_headers()
        )
    finally:
        client.app.state.storage = original_storage

    assert response.status_code == 503
    assert response.json()["code"] == "storage_unavailable"
    events = audit_events(client, seeds.ready_id)
    assert [(event.event_type, event.outcome, event.policy_reason) for event in events] == [
        ("playback_denied", "denied", "storage_unavailable")
    ]


def test_owner_playback_route_audits_storage_reader_failure(client) -> None:
    seeds = seed_cabinet_meetings(client)
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A storage")
    original_storage = client.app.state.storage
    client.app.state.storage = PlaybackReaderFailingStorage(client.app_state["storage"])
    try:
        response = client.get(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback", headers=auth_headers()
        )
    finally:
        client.app.state.storage = original_storage

    assert response.status_code == 503
    assert response.json()["code"] == "storage_unavailable"
    assert [
        (event.event_type, event.outcome, event.policy_reason)
        for event in audit_events(client, seeds.ready_id)
    ] == [("playback_denied", "denied", "storage_unavailable")]


def test_shared_viewer_playback_route_uses_stored_m4a_review_artifact(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    m4a_body = add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A shared")
    share = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers(),
        json={"grantee_user_id": str(SHARED_USER_ID)},
    )
    assert share.status_code == 201

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback", headers=auth_headers_for()
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mp4")
    assert response.content == m4a_body


def test_owner_playback_route_supports_byte_range_without_audio_download_policy(client) -> None:
    seeds = seed_cabinet_meetings(client)
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    m4a_body = add_retained_playback_m4a(client, seeds.ready_id, b"0123456789abcdefXYZ")

    full_response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback", headers=auth_headers()
    )
    range_response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback",
        headers={**auth_headers(), "Range": "bytes=0-15"},
    )

    assert full_response.status_code == 200
    assert range_response.status_code == 206
    assert range_response.headers["accept-ranges"] == "bytes"
    assert range_response.headers["content-range"] == f"bytes 0-15/{len(m4a_body)}"
    assert range_response.headers["content-length"] == "16"
    assert range_response.content == m4a_body[:16]
    events = audit_events(client, seeds.ready_id)
    assert [(event.event_type, event.outcome) for event in events] == [
        ("playback_requested", "allowed"),
        ("playback_stream_prepared", "prepared"),
        ("playback_requested", "allowed"),
        ("playback_stream_prepared", "prepared"),
    ]
    assert events[-1].metadata_json == {
        "artifact_class": "audio",
        "byte_length": 16,
        "outcome": "prepared",
        "range_end": 15,
        "range_start": 0,
        "source_mode": "stored_review_m4a",
        "stream_state": "prepared",
    }
    for marker in FORBIDDEN_MARKERS:
        assert marker not in range_response.content


def test_owner_playback_range_streams_stored_m4a_without_full_object_read(client) -> None:
    seeds = seed_cabinet_meetings(client)
    m4a_body = add_retained_playback_m4a(client, seeds.ready_id, b"0123456789abcdefXYZ")
    original_storage = client.app.state.storage
    client.app.state.storage = PlaybackStreamingOnlyStorage(client.app_state["storage"])
    try:
        response = client.get(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback",
            headers={**auth_headers(), "Range": "bytes=4-9"},
        )
    finally:
        client.app.state.storage = original_storage

    assert response.status_code == 206
    assert response.headers["content-range"] == f"bytes 4-9/{len(m4a_body)}"
    assert response.headers["content-length"] == "6"
    assert response.content == m4a_body[4:10]


def test_owner_playback_sync_storage_stream_initializes_off_event_loop(client) -> None:
    seeds = seed_cabinet_meetings(client)
    m4a_body = add_retained_playback_m4a(client, seeds.ready_id, b"0123456789abcdefXYZ")
    original_storage = client.app.state.storage
    client.app.state.storage = PlaybackLoopCheckingStorage(client.app_state["storage"])
    try:
        response = client.get(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback",
            headers={**auth_headers(), "Range": "bytes=1-3"},
        )
    finally:
        client.app.state.storage = original_storage

    assert response.status_code == 206
    assert response.content == m4a_body[1:4]


def test_playback_route_blocks_foreign_workspace_without_disclosing_meeting(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.foreign_id}/playback", headers=auth_headers()
    )

    assert response.status_code == 404
    assert response.json()["code"] == "meeting_not_found"
    assert audit_events(client, seeds.foreign_id) == []


def test_playback_route_allows_review_when_audio_download_policy_is_disabled(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, audio_download="disabled")
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    m4a_body = add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A policy")

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback", headers=auth_headers()
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mp4")
    assert response.content == m4a_body
    for marker in FORBIDDEN_MARKERS:
        assert marker not in response.content
    events = audit_events(client, seeds.ready_id)
    assert [(event.event_type, event.outcome) for event in events] == [
        ("playback_requested", "allowed"),
        ("playback_stream_prepared", "prepared"),
    ]


def test_playback_route_blocks_deleting_meeting_with_safe_audit(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, audio_download="allowed")
    set_meeting_deletion_state(client, seeds.ready_id, DeletionState.REQUESTED.value)

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback", headers=auth_headers()
    )

    assert response.status_code == 404
    assert response.json()["code"] == "meeting_not_found"
    assert audit_events(client, seeds.ready_id) == []


def test_playback_route_blocks_processing_and_failed_reviews_even_when_audio_policy_allows(
    client,
) -> None:
    seeds = seed_cabinet_meetings(client)
    for meeting_id in (seeds.processing_id, seeds.failed_id):
        set_artifact_policy(client, meeting_id, audio_download="allowed")
        replace_retained_audio_with_test_wav(client, meeting_id)

        response = client.get(
            f"/api/v1/cabinet/meetings/{meeting_id}/playback", headers=auth_headers()
        )

        assert response.status_code == 409
        assert response.json()["code"] == "playback_unavailable"
        events = audit_events(client, meeting_id)
        assert [(event.event_type, event.outcome) for event in events] == [
            ("playback_denied", "denied")
        ]


def test_playback_route_requires_stored_review_m4a_artifact(client) -> None:
    seeds = seed_cabinet_meetings(client)
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    set_retained_audio_source_status(client, seeds.ready_id, TrackRole.SYSTEM, "purged")

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback", headers=auth_headers()
    )

    assert response.status_code == 409
    assert response.json()["code"] == "playback_unavailable"
    events = audit_events(client, seeds.ready_id)
    assert [(event.event_type, event.outcome, event.policy_reason) for event in events] == [
        ("playback_denied", "denied", "normalization_queued")
    ]
    detail = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}",
        headers=auth_headers(),
    )
    assert detail.status_code == 200
    assert detail.json()["meeting"]["playback"] == {
        "state": "preparing",
        "reason_code": "normalization_queued",
        "label": "Аудио готовится автоматически",
        "automatic_recovery": True,
        "can_play": False,
        "action": "disabled",
    }


def test_playback_route_rejects_malformed_and_unsatisfiable_ranges_safely(client) -> None:
    seeds = seed_cabinet_meetings(client)
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    add_retained_playback_m4a(client, seeds.ready_id, b"0123456789abcdefXYZ")

    malformed = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback",
        headers={**auth_headers(), "Range": "items=0-10"},
    )
    unsatisfiable = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback",
        headers={**auth_headers(), "Range": "bytes=999999-1000000"},
    )

    assert malformed.status_code == 416
    assert malformed.json()["code"] == "playback_range_not_satisfiable"
    assert unsatisfiable.status_code == 416
    assert unsatisfiable.json()["code"] == "playback_range_not_satisfiable"
    for response in (malformed, unsatisfiable):
        for marker in FORBIDDEN_MARKERS:
            assert marker not in response.content
