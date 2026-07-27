from __future__ import annotations

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import add_retained_playback_m4a


def test_ready_detail_exposes_server_mediated_combined_playback_contract(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    playback = payload["playback"]
    assert playback["available"] is True
    assert playback["unavailable_reason"] == "none"
    assert playback["source_mode"] == "combined_review_stream"
    assert playback["included_sources"] == ["local_microphone", "incoming_system"]
    assert playback["playback_path"] == f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback"
    assert playback["duration_seconds"] > 0
    assert playback["speed_options"] == [0.75, 1.0, 1.25, 1.5, 2.0]
    assert "http" not in playback["playback_path"]
    assert "X-Amz" not in playback["playback_path"]
    audio_artifact = next(artifact for artifact in payload["artifacts"] if artifact["artifact_class"] == "audio")
    assert audio_artifact["state"] == "available"
    assert audio_artifact["action"] == "download"


def test_ready_detail_exposes_stored_m4a_playback_source_mode(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A detail")

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["playback"]["source_mode"] == "stored_review_m4a"


def test_ready_detail_exposes_seekable_transcript_segments_when_playback_available(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    segments = response.json()["transcript"]["segments"]
    assert len(segments) >= 2
    assert [segment["seekable"] for segment in segments] == [True, True]
    assert [segment["seek_seconds"] for segment in segments] == [0.0, 12.5]


def test_processing_detail_keeps_playback_unavailable_without_path(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.processing_id}", headers=auth_headers())

    assert response.status_code == 200
    playback = response.json()["playback"]
    assert playback["available"] is False
    assert playback["unavailable_reason"] == "processing"
    assert playback["source_mode"] == "none"
    assert "playback_path" not in playback or playback["playback_path"] is None


def test_desktop_embedded_detail_uses_same_playback_contract(client) -> None:
    seeds = seed_cabinet_meetings(client)

    api_response = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers())
    desktop_response = client.get(f"/desktop/meetings/{seeds.ready_id}", headers=auth_headers())

    assert api_response.status_code == 200
    assert desktop_response.status_code == 200
    playback = api_response.json()["playback"]
    html = desktop_response.text
    assert playback["available"] is True
    assert playback["playback_path"] in html
    assert 'data-source-mode="combined_review_stream"' in html
    assert 'data-seek-seconds="0.0"' in html
    assert 'data-seek-seconds="12.5"' in html
    assert "desktop-embedded" in html
