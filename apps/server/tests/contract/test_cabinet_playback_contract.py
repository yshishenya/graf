from __future__ import annotations

import re

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import add_retained_playback_m4a


def test_ready_detail_reports_automatic_preparation_until_m4a_artifact_exists(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    playback = payload["playback"]
    assert playback["available"] is False
    assert playback["state"] == "preparing"
    assert playback["reason_code"] == "normalization_queued"
    assert playback["automatic_recovery"] is True
    assert playback["can_play"] is False
    assert playback["action"] == "disabled"
    assert playback["unavailable_reason"] == "processing"
    assert playback["source_mode"] == "none"
    assert "playback_path" not in playback or playback["playback_path"] is None
    assert playback["duration_seconds"] > 0
    assert playback["speed_options"] == [0.75, 1.0, 1.25, 1.5, 2.0]
    audio_artifact = next(
        artifact for artifact in payload["artifacts"] if artifact["artifact_class"] == "audio"
    )
    assert audio_artifact["state"] == "missing"
    assert audio_artifact["reason"] == "missing_playback_artifact"
    assert audio_artifact["action"] == "disabled"


def test_ready_detail_exposes_stored_m4a_playback_source_mode(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A detail")

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    playback = response.json()["playback"]
    assert playback["available"] is True
    assert playback["source_mode"] == "stored_review_m4a"
    assert playback["playback_path"] == f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback"
    assert "http" not in playback["playback_path"]
    assert "X-Amz" not in playback["playback_path"]


def test_ready_detail_exposes_seekable_transcript_segments_when_playback_available(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A seek")

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
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A desktop")

    api_response = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers())
    desktop_response = client.get(f"/desktop/meetings/{seeds.ready_id}", headers=auth_headers())

    assert api_response.status_code == 200
    assert desktop_response.status_code == 200
    playback = api_response.json()["playback"]
    html = desktop_response.text
    assert playback["available"] is True
    assert playback["playback_path"] in html
    assert 'data-source-mode="stored_review_m4a"' in html
    assert 'data-seek-seconds="0.0"' in html
    assert 'data-seek-seconds="12.5"' in html
    assert "data-timeline-track" in html
    assert "data-timeline-playhead" in html
    assert "desktop-embedded" in html


def test_browser_and_embedded_keep_the_same_persistent_timeline_fixture(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A parity")

    browser = client.get(f"/meetings/{seeds.ready_id}", headers=auth_headers())
    embedded = client.get(f"/desktop/meetings/{seeds.ready_id}", headers=auth_headers())

    assert browser.status_code == embedded.status_code == 200
    browser_speaker_keys = set(re.findall(r'data-speaker-key="([^"]+)"', browser.text))
    embedded_speaker_keys = set(re.findall(r'data-speaker-key="([^"]+)"', embedded.text))
    assert browser_speaker_keys == embedded_speaker_keys
    assert len(browser_speaker_keys) == 2
    for html in (browser.text, embedded.text):
        assert html.count("data-playback-shell") == 1
        assert html.count("data-timeline-track") == 2
        assert html.count("data-transcript-turn") == 2
        assert all(f'data-speaker-key="{key}"' in html for key in browser_speaker_keys)
        assert html.index('data-detail-panel="recording"') < html.index("data-playback-shell")
