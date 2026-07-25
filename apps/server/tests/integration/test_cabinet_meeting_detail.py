import asyncio
import re
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_cabinet_contract import (
    CALENDAR_ROSTER_EMAIL_SENTINEL,
    CALENDAR_ROSTER_NAMES,
    _attach_matched_calendar_roster,
)
from tests.contract.test_calendar_auto_context_contract import (
    _create_recurring_pointer_fixture,
)
from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from tests.fixtures.artifacts import deterministic_wav_bytes
from tests.fixtures.cabinet import (
    PRIVATE_EXTERNAL_JOB_ID,
    SAFE_SECOND_TRANSCRIPT_TEXT,
    SAFE_TRANSCRIPT_TEXT,
    create_summary_reported_meeting,
    seed_cabinet_meetings,
)
from tests.fixtures.cabinet_access import (
    add_retained_playback_m4a,
    add_workspace_user,
    set_meeting_visibility,
)
from tests.fixtures.cabinet_access import (
    auth_headers_for as shared_auth_headers,
)
from twobrain_rec_server.cabinet.templates import CABINET_STATIC_URL
from twobrain_rec_server.db.models import (
    CalendarEventSnapshot,
    CalendarParticipant,
    CalendarSource,
    ExternalCalendar,
    RecordingCalendarContextLink,
)


def test_cabinet_ready_detail_returns_ordered_transcript_speakers_and_provenance(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A detail")

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
    audio_artifact = next(
        artifact for artifact in payload["artifacts"] if artifact["artifact_class"] == "audio"
    )
    assert audio_artifact["state"] == "policy_blocked"
    assert audio_artifact["action"] == "disabled"
    assert {speaker["label"] for speaker in payload["speakers"]["speakers"]} == {
        "SPEAKER_00",
        "SPEAKER_01",
    }
    assert PRIVATE_EXTERNAL_JOB_ID not in response.text


def test_missing_canonical_object_projects_automatic_recovery_in_api_and_web(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A stale")
    client.app_state["storage"].delete_object(
        f"tests/cabinet/{seeds.ready_id}/meeting-review.m4a"
    )

    api_response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers()
    )
    web_response = client.get(f"/meetings/{seeds.ready_id}", headers=auth_headers())

    assert api_response.status_code == 200
    assert api_response.json()["playback"] | {
        "state": "preparing",
        "reason_code": "canonical_artifact_missing",
        "automatic_recovery": True,
        "can_play": False,
    } == api_response.json()["playback"]
    assert web_response.status_code == 200
    assert 'data-playback-state="preparing"' in web_response.text
    assert 'data-playback-reason="canonical_artifact_missing"' in web_response.text
    assert 'data-playback-poll-active="true"' in web_response.text
    assert "data-playback-player" not in web_response.text


def test_098_calendar_roster_uses_exact_invitee_not_speaker_copy_on_both_surfaces(
    client,
) -> None:
    # FR-020/FR-040/FR-044: roster copy describes invitations without claiming speaker truth.
    seeds = seed_cabinet_meetings(client)
    _attach_matched_calendar_roster(client, seeds.ready_id)

    for path in (f"/meetings/{seeds.ready_id}", f"/desktop/meetings/{seeds.ready_id}"):
        response = client.get(path, headers=auth_headers())

        assert response.status_code == 200, path
        assert response.text.count('class="calendar-context"') == 1
        context_match = re.search(
            r'<section class="calendar-context".*?</section>',
            response.text,
            flags=re.DOTALL,
        )
        assert context_match is not None
        context_block = context_match.group(0)
        assert context_block.count("Приглашённые участники, не подтверждённые спикеры") == 1
        assert context_block.count(f"Участники из календаря · {len(CALENDAR_ROSTER_NAMES)}") == 1
        for name in CALENDAR_ROSTER_NAMES:
            assert context_block.count(name) == 1
        for forbidden in (
            "SPEAKER_",
            "Доступ",
            "Поделиться",
            "Получатель",
            "recipient",
            CALENDAR_ROSTER_EMAIL_SENTINEL,
        ):
            assert forbidden not in context_block


def test_098_calendar_roster_stays_separate_from_transcript_speakers_and_permissions(
    client,
) -> None:
    # FR-021/FR-022/FR-044/SC-008: invitees stay in context; diarization stays SPEAKER_XX.
    seeds = seed_cabinet_meetings(client)
    _attach_matched_calendar_roster(client, seeds.ready_id)

    for path in (f"/meetings/{seeds.ready_id}", f"/desktop/meetings/{seeds.ready_id}"):
        response = client.get(path, headers=auth_headers())

        assert response.status_code == 200, path
        context_match = re.search(
            r'<section class="calendar-context".*?</section>',
            response.text,
            flags=re.DOTALL,
        )
        transcript_match = re.search(
            r'<section[^>]*id="detail-panel-recording"[^>]*>(.*?)</section>',
            response.text,
            flags=re.DOTALL,
        )
        assert context_match is not None
        assert transcript_match is not None
        context_block = context_match.group(0)
        transcript_panel = transcript_match.group(1)
        speaker_start = response.text.index(">Спикеры</h3>")
        speaker_end = response.text.index(">Активность</h3>", speaker_start)
        speaker_panel = response.text[speaker_start:speaker_end]

        assert response.text.index(context_block) < speaker_start
        for name in CALENDAR_ROSTER_NAMES:
            assert name in context_block
            assert name not in transcript_panel
            assert name not in speaker_panel
        for label in ("SPEAKER_00", "SPEAKER_01"):
            assert label not in context_block
            assert label in transcript_panel
            assert label in speaker_panel
        assert CALENDAR_ROSTER_EMAIL_SENTINEL not in response.text


def test_cabinet_processing_failed_and_partial_detail_states_are_truthful(client) -> None:
    seeds = seed_cabinet_meetings(client)

    processing = client.get(
        f"/api/v1/cabinet/meetings/{seeds.processing_id}", headers=auth_headers()
    ).json()
    failed = client.get(
        f"/api/v1/cabinet/meetings/{seeds.failed_id}", headers=auth_headers()
    ).json()
    partial = client.get(
        f"/api/v1/cabinet/meetings/{seeds.partial_id}", headers=auth_headers()
    ).json()

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


def test_manual_upload_detail_handoff_keeps_processing_truth_separate_from_review_readiness(
    client,
) -> None:
    uploaded = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Manual detail handoff",
            "duration_seconds": "60",
            "local_recording_id": "manual-detail-handoff",
        },
        files={"file": ("meeting.wav", deterministic_wav_bytes(80), "audio/wav")},
    )
    assert uploaded.status_code == 202
    meeting_id = uploaded.json()["meeting"]["meeting_id"]

    response = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())
    page = client.get(f"/meetings/{meeting_id}", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["meeting"]["source"] == "manual_upload"
    assert payload["processing"]["state"] == "submitted"
    assert payload["transcript"]["available"] is False
    assert payload["transcript"]["segments"] == []
    assert payload["notes"]["available"] is False
    assert payload["notes_action_truth"]["summary"]["state"] == "processing"
    assert page.status_code == 200
    assert "Транскрипт готовится" in page.text
    assert "Итоги готовятся" in page.text


def test_manual_upload_ready_playback_reports_uploaded_media_provenance(client) -> None:
    uploaded = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Manual playback provenance",
            "duration_seconds": "60",
            "local_recording_id": "manual-playback-provenance",
        },
        files={"file": ("meeting.wav", deterministic_wav_bytes(80), "audio/wav")},
    )
    assert uploaded.status_code == 202
    meeting_id = UUID(uploaded.json()["meeting"]["meeting_id"])
    add_retained_playback_m4a(client, meeting_id, b"\x00\x00\x00\x18ftypM4A manual")

    response = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["playback"]["included_sources"] == ["uploaded_media"]


def test_two_tabs_and_reconnect_read_the_same_automatic_playback_recovery(client) -> None:
    seeds = seed_cabinet_meetings(client)
    path = f"/meetings/{seeds.ready_id}"

    first_tab = client.get(path, headers=auth_headers())
    second_tab = client.get(path, headers=auth_headers())
    reconnect = client.get(path, headers=auth_headers() | {"HX-Request": "true"})

    assert first_tab.status_code == second_tab.status_code == reconnect.status_code == 200
    for response in (first_tab, second_tab, reconnect):
        assert 'data-playback-state="preparing"' in response.text
        assert 'data-playback-reason="normalization_queued"' in response.text
        assert 'data-playback-poll-active="true"' in response.text
        assert f'data-playback-poll-url="{path}"' in response.text
        assert "Повторить" not in response.text
        assert "retry-normalization" not in response.text
    assert 'data-cabinet-fragment="meeting-detail"' not in first_tab.text
    assert 'data-cabinet-fragment="meeting-detail"' in reconnect.text


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
        assert (
            sync_payload["review"]["media_revision_id"]
            == cabinet_payload["provenance"]["media_revision_id"]
        )
        assert (
            sync_payload["review"]["transcript_available"]
            == cabinet_payload["processing"]["transcript_available"]
        )
        assert (
            sync_payload["review"]["diarization_available"]
            == cabinet_payload["processing"]["diarization_available"]
        )
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
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A web")

    ready = client.get(f"/meetings/{seeds.ready_id}", headers=auth_headers())
    processing = client.get(f"/meetings/{seeds.processing_id}", headers=auth_headers())

    assert ready.status_code == 200
    assert "data-cabinet-shell" in ready.text
    assert "data-cabinet-navigation" in ready.text
    assert ready.text.count('id="cabinet-sidebar" data-cabinet-navigation') == 1
    assert ready.text.count('aria-label="Навигация кабинета"') == 1
    assert ready.text.count('aria-current="page"') == 1
    assert 'data-active-nav="meetings"' in ready.text
    assert f'href="{CABINET_STATIC_URL}/cabinet.css?v=' in ready.text
    assert "<style>" not in ready.text
    assert "Итоги" in ready.text
    assert "Расшифровка" in ready.text
    assert ready.text.count('role="tab"') == 2
    assert 'id="detail-tab-outcomes"' in ready.text
    assert 'id="detail-tab-recording"' in ready.text
    assert SAFE_TRANSCRIPT_TEXT in ready.text
    assert "Спикеры" in ready.text
    assert "Формат:" in ready.text
    assert "Все форматы…" in ready.text
    assert "Кратко" in ready.text
    assert "Действия" in ready.text
    assert "Итоги отложены" in ready.text
    assert "AI notes are reserved for a later feature" not in ready.text
    assert "feature 016" not in ready.text.lower()
    assert "feature:016" not in ready.text.lower()
    assert "016-meeting-detail" not in ready.text
    assert "Поделиться" in ready.text
    assert 'id="meeting-context-more"' in ready.text
    assert 'class="meeting-actions-menu"' in ready.text
    assert 'id="meeting-details-dialog"' in ready.text
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
    assert "data-cabinet-shell" in response.text
    assert 'data-cabinet-fragment="meeting-detail"' not in response.text
    assert response.headers.get("Vary") != "HX-Request"


def test_cabinet_embedded_ready_detail_keeps_review_governance_and_removes_native_capture_copy(
    client,
) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/desktop/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    assert "desktop-embedded" in response.text
    assert "data-cabinet-shell" in response.text
    assert "data-cabinet-navigation" in response.text
    assert response.text.count('id="cabinet-sidebar" data-cabinet-navigation') == 1
    assert response.text.count('aria-current="page"') == 1
    assert 'data-active-nav="meetings"' in response.text
    assert 'href="/desktop/meetings"' in response.text
    assert 'href="/desktop/settings"' in response.text
    assert "Расшифровка" in response.text
    assert "Recording &amp; Transcript" not in response.text
    assert SAFE_TRANSCRIPT_TEXT in response.text
    assert "Файлы" in response.text
    assert "Поделиться" in response.text
    assert "Ещё" in response.text
    assert 'class="meeting-actions-menu"' in response.text
    assert 'id="meeting-details-dialog"' in response.text
    assert "Record live" not in response.text
    assert "Krisp Devices" not in response.text


def test_cabinet_embedded_ready_detail_keeps_playback_and_seek_controls(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A embedded")

    response = client.get(f"/desktop/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    assert "desktop-embedded" in response.text
    assert "data-cabinet-navigation" in response.text
    assert 'class="playback-bar detail-playback"' in response.text
    assert "data-playback-shell" in response.text
    assert "data-playback-toggle" in response.text
    assert 'data-playback-skip="-15"' in response.text
    assert 'data-playback-skip="15"' in response.text
    assert f'src="/api/v1/cabinet/meetings/{seeds.ready_id}/playback"' in response.text
    assert 'data-source-mode="stored_review_m4a"' in response.text
    assert 'class="timestamp timestamp-seek"' in response.text
    assert 'data-seek-seconds="0.0"' in response.text
    assert 'data-seek-seconds="12.5"' in response.text
    assert "/downloads/audio" not in response.text


def test_098_ambiguous_owner_detail_renders_safe_chooser_with_web_embedded_parity(client) -> None:
    # FR-014/FR-033/FR-037/FR-048; SC-003/SC-012/SC-013: one safe chooser serves both review shells.
    meeting_id, candidates = _create_ambiguous_detail_meeting(
        client,
        local_recording_id="t050-owner-ambiguous-detail",
    )
    responses = {
        "web": client.get(f"/meetings/{meeting_id}", headers=auth_headers()),
        "embedded": client.get(
            f"/desktop/meetings/{meeting_id}",
            headers=auth_headers(),
        ),
    }

    for surface, response in responses.items():
        assert response.status_code == 200, surface
        assert (
            response.text.count("Несколько встреч подходят по времени. GRAF ничего не выбрал.") == 1
        )
        assert response.text.count(
            '<fieldset aria-describedby="calendar-context-choice-help">'
        ) == 1
        assert response.text.count("<legend>Выберите встречу</legend>") == 1
        assert response.text.count('type="radio" name="event_id"') == 2
        assert response.text.count('name="event_id"') == 2
        assert response.text.count("Synthetic Design Review") == 1
        assert response.text.count("Synthetic Planning Review") == 1
        assert response.text.count("Synthetic Work Calendar") == 2
        assert "12:00" in response.text
        assert "13:30" in response.text
        assert "Сохранить выбор" in response.text
        assert "Продолжить без календаря" in response.text
        assert 'aria-live="polite"' in response.text
        for candidate_id in candidates:
            assert f'value="{candidate_id}"' in response.text
        for forbidden in (
            "SYNTHETIC_PRIVATE_DESCRIPTION_DO_NOT_RENDER",
            "hidden-calendar-attendee@example.test",
            "synthetic-passcode",
            "multiple_time_candidates",
        ):
            assert forbidden not in response.text


def test_098_ambiguous_owner_detail_rejects_unsafe_calendar_source_labels(client) -> None:
    # FR-030/FR-033 and UI contract: candidate source labels fail closed like titles.
    meeting_id, _ = _create_ambiguous_detail_meeting(
        client,
        local_recording_id="t050-unsafe-calendar-label",
        calendar_display_label="https://calendar.example.test/private?token=synthetic-secret",
        provider_label="hidden-calendar-owner@example.test",
    )

    for path in (f"/meetings/{meeting_id}", f"/desktop/meetings/{meeting_id}"):
        response = client.get(path, headers=auth_headers())

        assert response.status_code == 200, path
        assert response.text.count("Календарь") == 2
        assert "calendar.example.test" not in response.text
        assert "synthetic-secret" not in response.text
        assert "hidden-calendar-owner@example.test" not in response.text


def test_098_ambiguous_non_owner_detail_is_generic_without_candidates_or_actions(client) -> None:
    # FR-033/FR-037; SC-011/SC-013: authorized non-owner review does not reveal candidate existence.
    meeting_id, _ = _create_ambiguous_detail_meeting(
        client,
        local_recording_id="t050-shared-context-detail",
    )
    add_workspace_user(client)
    set_meeting_visibility(client, meeting_id, "team")

    for path in (f"/meetings/{meeting_id}", f"/desktop/meetings/{meeting_id}"):
        response = client.get(path, headers=shared_auth_headers())
        assert response.status_code == 200, path
        assert response.text.count("Без календарного контекста") == 1
        assert "Нужно выбрать встречу" not in response.text
        assert "Несколько встреч подходят по времени" not in response.text
        assert "Synthetic Design Review" not in response.text
        assert "Synthetic Planning Review" not in response.text
        assert "Synthetic Work Calendar" not in response.text
        assert "Сохранить выбор" not in response.text
        assert "Продолжить без календаря" not in response.text
        assert '<fieldset aria-describedby="calendar-context-choice-help">' not in response.text
        assert "ambiguous" not in response.text
        assert "multiple_time_candidates" not in response.text


def test_098_owner_chooser_htmx_select_and_clear_keep_web_embedded_review_parity(client) -> None:
    # FR-014/FR-038/FR-039/FR-048: both shells mutate the same owner-only context row.
    meeting_id, candidates = _create_ambiguous_detail_meeting(
        client,
        local_recording_id="t057-owner-context-actions",
    )
    hx_headers = auth_headers() | {"HX-Request": "true"}

    selected = client.post(
        f"/meetings/{meeting_id}/calendar-context/choose",
        headers=hx_headers,
        data={"event_id": str(candidates[0])},
    )
    cleared = client.post(
        f"/desktop/meetings/{meeting_id}/calendar-context/clear",
        headers=hx_headers,
    )

    assert selected.status_code == 200
    assert 'data-calendar-context-state="matched_user"' in selected.text
    assert 'id="calendar-context-heading" tabindex="-1" autofocus' in selected.text
    assert "Выбрано вами" in selected.text
    assert "Убрать контекст" in selected.text
    assert cleared.status_code == 200
    assert 'data-calendar-context-state="cleared_by_user"' in cleared.text
    assert 'id="calendar-context-heading" tabindex="-1" autofocus' in cleared.text
    assert "Контекст убран вами" in cleared.text
    assert '<fieldset aria-describedby="calendar-context-choice-help">' not in cleared.text


def test_098_owner_can_reopen_safe_correction_chooser_in_web_and_embedded_review(client) -> None:
    # FR-038 and UI contract: matched context exposes a real owner-only Change action.
    meeting_id, candidates = _create_ambiguous_detail_meeting(
        client,
        local_recording_id="t057-owner-context-correction",
    )

    async def keep_both_candidates_near_the_recording_start() -> None:
        async with client.app_state["sessionmaker"]() as db:
            second = await db.get(CalendarEventSnapshot, candidates[1])
            assert second is not None
            second.starts_at = datetime(2026, 7, 13, 9, 5, tzinfo=UTC)
            second.ends_at = datetime(2026, 7, 13, 10, 5, tzinfo=UTC)
            await db.commit()

    client.portal.call(keep_both_candidates_near_the_recording_start)
    selected = client.post(
        f"/meetings/{meeting_id}/calendar-context/choose",
        headers=auth_headers() | {"HX-Request": "true"},
        data={"event_id": str(candidates[0])},
    )
    assert selected.status_code == 200

    surfaces = (
        (f"/meetings/{meeting_id}", "web"),
        (f"/desktop/meetings/{meeting_id}", "embedded"),
    )
    for path, surface in surfaces:
        detail = client.get(path, headers=auth_headers())
        correction = client.get(
            f"{path}?calendar_context_action=change",
            headers=auth_headers(),
        )

        assert detail.status_code == 200, surface
        assert "Изменить" in detail.text
        assert (
            f'href="{path}?calendar_context_action=change#calendar-context-chooser"' in detail.text
        )
        assert correction.status_code == 200, surface
        assert 'data-calendar-context-mode="correction"' in correction.text
        assert correction.text.count('type="radio" name="event_id"') == 2
        assert correction.text.count('name="event_id"') == 2
        assert 'name="context_reason" value="correction"' in correction.text
        assert "Выберите правильную встречу" in correction.text
        assert "Продолжить без календаря" not in correction.text
        assert 'id="calendar-context-chooser"' in correction.text
        assert 'tabindex="-1" autofocus' in correction.text
        for candidate_id in candidates:
            assert f'value="{candidate_id}"' in correction.text

    corrected = client.post(
        f"/desktop/meetings/{meeting_id}/calendar-context/choose",
        headers=auth_headers() | {"HX-Request": "true"},
        data={
            "event_id": str(candidates[1]),
            "context_reason": "correction",
        },
    )

    assert corrected.status_code == 200
    assert 'data-calendar-context-state="matched_user"' in corrected.text
    assert "Synthetic Planning Review" in corrected.text
    assert "12:05–13:05" in corrected.text
    assert "Контекст и список приглашённых исчезнут" in corrected.text

    api_context = client.get(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=auth_headers(),
    )
    assert api_context.status_code == 200
    assert api_context.json()["event_id"] == str(candidates[1])
    assert api_context.json()["matched_title"] == "Synthetic Planning Review"


def test_098_owner_chooser_keeps_strong_public_event_with_hidden_title_generic(client) -> None:
    # FR-030/FR-038: an otherwise safe explicit candidate may use a generic title label.
    meeting_id, candidates = _create_ambiguous_detail_meeting(
        client,
        local_recording_id="t057-owner-context-generic-title",
    )

    async def hide_one_candidate_title() -> None:
        async with client.app_state["sessionmaker"]() as db:
            event = await db.get(CalendarEventSnapshot, candidates[0])
            assert event is not None
            event.title = "hidden-title@example.test"
            event.safe_to_show_in_list = False
            event.safe_to_use_as_title = True
            await db.commit()

    client.portal.call(hide_one_candidate_title)
    detail = client.get(f"/meetings/{meeting_id}", headers=auth_headers())

    assert detail.status_code == 200
    assert detail.text.count('name="event_id"') == 2
    assert "Встреча без названия" in detail.text
    assert "hidden-title@example.test" not in detail.text


def test_098_non_owner_cannot_open_matched_context_correction_candidates(client) -> None:
    # FR-037/FR-038: the correction query does not grant candidate or mutation access.
    meeting_id, candidates = _create_ambiguous_detail_meeting(
        client,
        local_recording_id="t057-shared-context-correction",
    )
    selected = client.post(
        f"/meetings/{meeting_id}/calendar-context/choose",
        headers=auth_headers() | {"HX-Request": "true"},
        data={"event_id": str(candidates[0])},
    )
    assert selected.status_code == 200
    add_workspace_user(client)
    set_meeting_visibility(client, meeting_id, "team")

    for path in (f"/meetings/{meeting_id}", f"/desktop/meetings/{meeting_id}"):
        response = client.get(
            f"{path}?calendar_context_action=change",
            headers=shared_auth_headers(),
        )

        assert response.status_code == 200
        assert "Изменить" not in response.text
        assert "calendar-context-chooser" not in response.text
        assert 'name="event_id"' not in response.text
        assert "Synthetic Planning Review" not in response.text


def test_098_authorized_recurring_pointer_reuses_context_block_with_web_embedded_parity(
    client,
) -> None:
    # FR-024/FR-025/FR-045: owner review gets one safe pointer, not copied meeting content.
    previous_id, current_id = _create_recurring_pointer_fixture(
        client,
        local_recording_prefix="t077-review-pointer",
    )
    surfaces = {
        "web": (f"/meetings/{current_id}", f"/meetings/{previous_id}"),
        "embedded": (
            f"/desktop/meetings/{current_id}",
            f"/desktop/meetings/{previous_id}",
        ),
    }

    for surface, (path, previous_href) in surfaces.items():
        response = client.get(path, headers=auth_headers())

        assert response.status_code == 200, surface
        assert response.text.count('class="calendar-context"') == 1
        assert response.text.count("В серии") == 1
        assert response.text.count("Предыдущая встреча · 6 июл") == 1
        assert response.text.count("Обрабатывается") == 1
        assert f'href="{previous_href}"' in response.text
        pointer_tags = [
            tag
            for tag in re.findall(r"<a\b[^>]*>", response.text)
            if f'href="{previous_href}"' in tag
        ]
        assert len(pointer_tags) == 1
        pointer_tag = pointer_tags[0]
        assert 'aria-label="' in pointer_tag
        assert "Synthetic Previous Planning" in pointer_tag
        assert "6 июл" in pointer_tag
        assert "Обрабатывается" in pointer_tag

        assert "Synthetic Current Planning" in response.text
        assert "Synthetic Current Invitee" in response.text
        for forbidden in (
            "Synthetic Previous Invitee",
            "SYNTHETIC_PREVIOUS_DESCRIPTION_DO_NOT_RENDER",
            "synthetic-previous-transcript-do-not-render",
        ):
            assert forbidden not in response.text


def test_098_deleted_recurring_predecessor_has_no_block_or_disabled_placeholder(
    client,
) -> None:
    # FR-025/FR-026: deletion denial must not disclose that an earlier occurrence exists.
    previous_id, current_id = _create_recurring_pointer_fixture(
        client,
        local_recording_prefix="t077-deleted-review-pointer",
        previous_deleted=True,
    )

    for path, previous_href in (
        (f"/meetings/{current_id}", f"/meetings/{previous_id}"),
        (
            f"/desktop/meetings/{current_id}",
            f"/desktop/meetings/{previous_id}",
        ),
    ):
        response = client.get(path, headers=auth_headers())

        assert response.status_code == 200, path
        assert response.text.count('class="calendar-context"') == 1
        assert "Synthetic Current Planning" in response.text
        assert "Synthetic Current Invitee" in response.text
        assert "В серии" not in response.text
        assert "Предыдущая встреча" not in response.text
        assert f'href="{previous_href}"' not in response.text
        assert "data-previous-recurring-meeting" not in response.text
        for forbidden in (
            str(previous_id),
            "Synthetic Previous Planning",
            "Synthetic Previous Invitee",
            "SYNTHETIC_PREVIOUS_DESCRIPTION_DO_NOT_RENDER",
        ):
            assert forbidden not in response.text


def _create_ambiguous_detail_meeting(
    client,
    *,
    local_recording_id: str,
    calendar_display_label: str = "Synthetic Work Calendar",
    provider_label: str = "Synthetic Work Calendar",
) -> tuple[UUID, tuple[UUID, UUID]]:
    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": local_recording_id,
            "title": local_recording_id,
            "started_at": "2026-07-13T09:10:00Z",
            "ended_at": "2026-07-13T09:40:00Z",
            "recording_display_timezone_offset_minutes": 180,
            "duration_seconds": 1800,
        },
    )
    assert response.status_code == 200
    meeting_id = UUID(response.json()["meeting_id"])

    async def seed() -> tuple[UUID, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            source = CalendarSource(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                provider_family="caldav_yandex",
                provider_label=provider_label,
                auth_mode="app_password",
                credential_state="sealed",
                connection_state="active",
                sync_state="synced",
                sync_horizon_start=datetime(2026, 7, 13, 8, 0, tzinfo=UTC),
                sync_horizon_end=datetime(2026, 7, 14, 8, 0, tzinfo=UTC),
                last_sync_finished_at=datetime(2026, 7, 13, 8, 55, tzinfo=UTC),
                last_successful_sync_at=datetime(2026, 7, 13, 8, 55, tzinfo=UTC),
                capabilities_json={},
                selected_calendar_count=1,
            )
            db.add(source)
            await db.flush()
            calendar = ExternalCalendar(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                provider_calendar_id=f"{local_recording_id}-calendar",
                display_label=calendar_display_label,
                visibility="available",
                selected=True,
            )
            db.add(calendar)
            await db.flush()
            event_rows = []
            for sequence, (title, starts_at) in enumerate(
                (
                    ("Synthetic Design Review", datetime(2026, 7, 13, 9, 0, tzinfo=UTC)),
                    ("Synthetic Planning Review", datetime(2026, 7, 13, 9, 30, tzinfo=UTC)),
                ),
                start=1,
            ):
                event = CalendarEventSnapshot(
                    workspace_id=WORKSPACE_ID,
                    calendar_source_id=source.id,
                    external_calendar_id=calendar.id,
                    provider_event_id=f"{local_recording_id}-event-{sequence}",
                    ical_uid=f"{local_recording_id}-event-{sequence}@example.test",
                    source_version="synthetic-v1",
                    source_status="confirmed",
                    starts_at=starts_at,
                    ends_at=starts_at + timedelta(hours=1),
                    duration_seconds=3600,
                    timezone="Europe/Moscow",
                    all_day=False,
                    title=title,
                    description="SYNTHETIC_PRIVATE_DESCRIPTION_DO_NOT_RENDER",
                    location="https://meet.example.test/room?passcode=synthetic-passcode",
                    privacy_class="public",
                    conference_summary_json={"meeting_link_present": True},
                    attachments_metadata_json=[],
                    provider_extras_json={"roster_state": "available"},
                    safe_to_show_in_list=True,
                    safe_to_use_as_title=True,
                    sensitivity_reasons_json=[],
                    source_updated_at=datetime(2026, 7, 13, 8, 55, tzinfo=UTC),
                )
                db.add(event)
                await db.flush()
                db.add(
                    CalendarParticipant(
                        calendar_event_snapshot_id=event.id,
                        workspace_id=WORKSPACE_ID,
                        participant_kind="required_attendee",
                        response_status="accepted",
                        email="hidden-calendar-attendee@example.test",
                        email_hash=f"sha256:t050-hidden-{sequence}",
                        display_name="Synthetic Hidden Candidate Attendee",
                        workspace_relation="external",
                        recipient_candidate_class="external_attendee",
                    )
                )
                event_rows.append(event)

            context = await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.workspace_id == WORKSPACE_ID,
                    RecordingCalendarContextLink.meeting_id == meeting_id,
                )
            )
            assert context is not None
            context.calendar_event_snapshot_id = None
            context.context_state = "ambiguous"
            context.context_confidence = "ambiguous"
            context.context_reasons_json = ["multiple_time_candidates"]
            context.title_source = "generic"
            context.roster_source = "none"
            context.manual_override_state = "none"
            context.safe_reason_code = "multiple_time_candidates"
            context.decision_source = "automatic"
            context.matcher_version = "calendar_auto_match_v1"
            context.evaluated_at = datetime(2026, 7, 13, 9, 10, tzinfo=UTC)
            context.candidate_event_ids_json = [str(event.id) for event in event_rows]
            context.candidate_count = 2
            context.matched_title = None
            context.matched_title_state = "unavailable"
            context.matched_roster_json = []
            context.matched_roster_state = "not_available"
            context.matched_roster_count = 0
            await db.commit()
            return event_rows[0].id, event_rows[1].id

    candidate_ids = asyncio.run(seed())
    return meeting_id, candidate_ids
