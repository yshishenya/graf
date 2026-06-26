from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import (
    PRIVATE_EXTERNAL_JOB_ID,
    SAFE_SECOND_TRANSCRIPT_TEXT,
    SAFE_TRANSCRIPT_TEXT,
    create_summary_reported_meeting,
    seed_cabinet_meetings,
)
from twobrain_rec_server.cabinet.templates import CABINET_STATIC_URL


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
    audio_artifact = next(artifact for artifact in payload["artifacts"] if artifact["artifact_class"] == "audio")
    assert audio_artifact["state"] == "policy_blocked"
    assert audio_artifact["action"] == "disabled"
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
    assert failed["transcript"]["available"] is False
    assert failed["transcript"]["segments"] == []
    assert SAFE_TRANSCRIPT_TEXT not in str(failed)
    assert failed["notes_action_truth"]["summary"]["state"] == "blocked"
    assert failed["notes_action_truth"]["decisions"]["state"] == "blocked"
    assert partial["processing"]["state"] == "partial"
    assert partial["transcript"]["available"] is True
    assert partial["speakers"]["available"] is False
    assert partial["notes_action_truth"]["summary"]["state"] == "deferred"
    assert partial["notes_action_truth"]["followups"]["state"] == "deferred"


def test_cabinet_and_desktop_sync_review_states_match_for_result_states(client) -> None:
    seeds = seed_cabinet_meetings(client)
    cases = [
        ("cabinet-ready", seeds.ready_id),
        ("cabinet-partial", seeds.partial_id),
        ("cabinet-processing", seeds.processing_id),
        ("cabinet-failed", seeds.failed_id),
    ]

    for local_recording_id, meeting_id in cases:
        cabinet = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())
        sync = client.get(
            f"/api/v1/desktop/recordings/{local_recording_id}/sync-state",
            headers=auth_headers(),
            params={"local_media_revision_id": f"{local_recording_id}--initial"},
        )

        assert cabinet.status_code == 200
        assert sync.status_code == 200
        cabinet_payload = cabinet.json()
        sync_payload = sync.json()
        assert sync_payload["review"]["status"] == cabinet_payload["meeting"]["status"]
        assert sync_payload["review"]["available"] is True
        assert sync_payload["review"]["media_revision_id"] == cabinet_payload["provenance"]["media_revision_id"]
        assert sync_payload["review"]["transcript_available"] == cabinet_payload["processing"]["transcript_available"]
        assert sync_payload["review"]["diarization_available"] == cabinet_payload["processing"]["diarization_available"]
        assert sync_payload["review"]["web_url"] == f"/meetings/{meeting_id}"
        assert sync_payload["review"]["desktop_url"] == f"/desktop/meetings/{meeting_id}"


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
    assert 'data-cabinet-shell' in ready.text
    assert 'data-cabinet-navigation' in ready.text
    assert 'data-active-nav="meetings"' in ready.text
    assert f'href="{CABINET_STATIC_URL}/cabinet.css"' in ready.text
    assert "<style>" not in ready.text
    assert "Итоги" in ready.text
    assert "Запись и расшифровка" in ready.text
    assert SAFE_TRANSCRIPT_TEXT in ready.text
    assert "Спикеры" in ready.text
    assert "Ассистент" in ready.text
    assert "Шаблон" in ready.text
    assert "Кратко" in ready.text
    assert "Действия" in ready.text
    assert "Итоги отложены" in ready.text
    assert "AI notes are reserved for a later feature" not in ready.text
    assert "feature 016" not in ready.text.lower()
    assert "feature:016" not in ready.text.lower()
    assert "016-meeting-detail" not in ready.text
    assert "Доступ" in ready.text
    assert "Видимость для команды" in ready.text
    assert "Файлы" in ready.text
    assert 'class="playback-bar detail-playback"' in ready.text
    assert f'src="/api/v1/cabinet/meetings/{seeds.ready_id}/playback"' in ready.text
    assert "/downloads/audio" not in ready.text
    assert processing.status_code == 200
    assert "Транскрипт готовится" in processing.text
    assert "Итоги готовятся" in processing.text
    assert SAFE_TRANSCRIPT_TEXT not in processing.text


def test_cabinet_detail_full_page_fallback_without_hx_header(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    assert "<!doctype html>" in response.text
    assert 'data-cabinet-shell' in response.text
    assert 'data-cabinet-fragment="meeting-detail"' not in response.text
    assert response.headers.get("Vary") != "HX-Request"


def test_cabinet_embedded_ready_detail_keeps_review_governance_and_removes_native_capture_copy(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/desktop/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    assert "desktop-embedded" in response.text
    assert 'data-cabinet-shell' in response.text
    assert 'data-cabinet-navigation' in response.text
    assert 'data-active-nav="meetings"' in response.text
    assert "Расшифровка" in response.text
    assert "Recording &amp; Transcript" not in response.text
    assert SAFE_TRANSCRIPT_TEXT in response.text
    assert "Открыть в браузере" in response.text
    assert "Доступ" in response.text
    assert "Поделиться" in response.text
    assert "Отчет" in response.text
    assert "Record live" not in response.text
    assert "Krisp Devices" not in response.text


def test_cabinet_embedded_ready_detail_keeps_playback_and_seek_controls(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/desktop/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    assert "desktop-embedded" in response.text
    assert 'data-cabinet-navigation' in response.text
    assert 'class="playback-bar detail-playback"' in response.text
    assert 'data-playback-shell' in response.text
    assert 'data-playback-toggle' in response.text
    assert 'data-playback-skip="-15"' in response.text
    assert 'data-playback-skip="15"' in response.text
    assert f'src="/api/v1/cabinet/meetings/{seeds.ready_id}/playback"' in response.text
    assert 'data-source-mode="combined_review_stream"' in response.text
    assert 'class="timestamp timestamp-seek"' in response.text
    assert 'data-seek-seconds="0.0"' in response.text
    assert 'data-seek-seconds="12.5"' in response.text
    assert "/downloads/audio" not in response.text
