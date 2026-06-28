from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from twobrain_rec_server.api.schemas import (
    ArtifactDeletionState,
    ArtifactEgressState,
    DeletionVerificationReport,
    GovernanceActionState,
    GovernanceActionSummary,
    LifecycleActivityItem,
    LocalPurgeTask,
    MeetingAccessState,
    MeetingActivityResponse,
    MeetingFilterState,
    MeetingListItem,
    MeetingListResponse,
    MeetingProvenance,
    MeetingReviewResponse,
    NotesActionCategoryState,
    NotesActionTruthState,
    NotesReviewState,
    OutcomeItemView,
    OutcomeSourceReferenceView,
    PlaybackReviewState,
    ProcessingReviewState,
    SharePanelState,
    SlotState,
    SpeakerLane,
    SpeakerLaneSegment,
    SpeakerReviewState,
    TranscriptReviewState,
    TranscriptSegmentView,
)
from twobrain_rec_server.cabinet.rendering import (
    render_deletion_report_page,
    render_meeting_detail_page,
    render_meeting_list_page,
    render_settings_page,
)
from twobrain_rec_server.cabinet.templates import CABINET_STATIC_URL
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY
from twobrain_rec_server.domain.statuses import (
    DeletionArtifactState,
    DeletionControlScope,
    DeletionState,
    LocalPurgeTaskState,
    LocalPurgeTaskType,
)

SERVER_ROOT = Path(__file__).resolve().parents[2] / "src" / "twobrain_rec_server"
CABINET_CSS = SERVER_ROOT / "cabinet" / "static" / "cabinet" / "cabinet.css"
CABINET_JS = SERVER_ROOT / "cabinet" / "static" / "cabinet" / "cabinet.js"
CABINET_WEB = SERVER_ROOT / "cabinet" / "web.py"
CABINET_AUTH_TEMPLATES = SERVER_ROOT / "cabinet" / "templates" / "cabinet" / "auth"


def _cabinet_css() -> str:
    return CABINET_CSS.read_text()


def _cabinet_js() -> str:
    return CABINET_JS.read_text()


def _governance() -> GovernanceActionSummary:
    return GovernanceActionSummary(
        share=GovernanceActionState(state="available", label="Share", reason="Login-required sharing", destructive=False),
        export=GovernanceActionState(state="disabled", label="Export package", reason="No package", destructive=False),
        download=GovernanceActionState(state="disabled", label="Download", reason="No artifact", destructive=False),
        retention=GovernanceActionState(state="planned", label="Retention policy planned", reason="future", destructive=False),
        delete=GovernanceActionState(
            state="planned",
            label="Delete this meeting everywhere GRAF controls",
            reason="future",
            destructive=True,
        ),
    )


def _access() -> MeetingAccessState:
    return MeetingAccessState(
        state="owner",
        label="Owner",
        reason="You own this meeting.",
        can_view=True,
        can_share=True,
        can_manage_team_visibility=True,
        can_download=True,
        can_export=True,
    )


def _artifacts() -> list[ArtifactEgressState]:
    return [
        ArtifactEgressState(
            artifact_class="transcript",
            state="processing",
            label="Transcript",
            reason="Transcript is still processing.",
            action="disabled",
        )
    ]


def _notes_truth() -> NotesActionTruthState:
    category = NotesActionCategoryState(
        state="processing",
        label="Outcomes processing",
        reason="Transcript and generated outcomes may still be processing.",
        readiness_impact="keeps_gap_open",
        copy_key="notes.outcomes.processing",
    )
    return NotesActionTruthState(
        summary=category,
        decisions=category,
        action_items=category,
        followups=category,
        source_basis="processing_status",
    )


def _item() -> MeetingListItem:
    return MeetingListItem(
        meeting_id=uuid4(),
        title="Проектный синк",
        started_at=datetime(2026, 6, 16, 8, 0, tzinfo=UTC),
        ended_at=None,
        duration_seconds=120,
        source="desktop_recording",
        status="processing",
        status_label="Processing",
        status_reason=None,
        primary_action="wait",
        transcript_available=False,
        diarization_available=False,
        notes_available=False,
        updated_at=None,
        access=_access(),
        artifacts=_artifacts(),
        governance=_governance(),
        future_slots=[
            SlotState(state="planned", label="Star", reason="future"),
            SlotState(state="planned", label="Tag", reason="future"),
        ],
    )


def _review() -> MeetingReviewResponse:
    item = _item()
    return MeetingReviewResponse(
        meeting=item,
        provenance=MeetingProvenance(
            source_roles=["local_microphone", "incoming_system"],
            processing_dependency="mediascribe",
            content_policy="authorized_detail_only",
        ),
        processing=ProcessingReviewState(
            state="processing",
            stage="mediascribe",
            reason_code=None,
            reason_label=None,
            content_available=False,
            transcript_available=False,
            diarization_available=False,
            summary_available=False,
            updated_at=None,
            next_action="wait",
        ),
        transcript=TranscriptReviewState(available=False, language=None, degraded_reason="processing", search_enabled=False, segments=[]),
        speakers=SpeakerReviewState(available=False, assignment_state="reserved", degraded_reason="processing", speakers=[]),
        notes=NotesReviewState(available=False, sections=[], unavailable_reason="processing"),
        playback=PlaybackReviewState(available=False, duration_seconds=120, speed_options=[0.75, 1.0, 1.25, 1.5, 2.0]),
        governance=_governance(),
        access=_access(),
        share=SharePanelState(
            team_visibility="disabled",
            active_grants=[],
            copy_link_state="available",
            public_link_state="disabled_by_default",
        ),
        artifacts=_artifacts(),
        activity=MeetingActivityResponse(meeting_id=item.meeting_id, items=[]),
        notes_action_truth=_notes_truth(),
        deletion_truth_copy="Files already downloaded or exported are outside GRAF deletion control.",
        assistant=SlotState(state="planned", label="Assistant", reason="future"),
        template=SlotState(state="planned", label="Template", reason="future"),
    )


def _deletion_report() -> DeletionVerificationReport:
    expires_at = datetime.now(UTC) + timedelta(days=7)
    return DeletionVerificationReport(
        meeting_id=uuid4(),
        request_id=uuid4(),
        overall_state=DeletionState.DELETING,
        bounded_copy=BOUNDED_DELETE_COPY,
        artifact_states=[
            ArtifactDeletionState(
                artifact_class="audio_object",
                control_scope=DeletionControlScope.CONTROLLED,
                state=DeletionArtifactState.PURGE_REQUESTED,
                label="Server audio purge requested",
                safe_reason="artifact_lifecycle_state",
            )
        ],
        backup=ArtifactDeletionState(
            artifact_class="backup",
            control_scope=DeletionControlScope.BACKUP,
            state=DeletionArtifactState.PENDING_EXPIRY,
            label="Backup expiry pending",
            safe_reason="backup_expiry_pending",
        ),
        dependencies=[
            ArtifactDeletionState(
                artifact_class="mediascribe",
                control_scope=DeletionControlScope.EXTERNAL,
                state=DeletionArtifactState.UNKNOWN,
                label="External deletion support is not confirmed",
                safe_reason="dependency_unconfirmed",
            )
        ],
        post_egress_limits=[
            ArtifactDeletionState(
                artifact_class="post_egress_copy",
                control_scope=DeletionControlScope.POST_EGRESS,
                state=DeletionArtifactState.OUTSIDE_2BRAIN_CONTROL,
                label="Delivered copies are outside GRAF control",
                safe_reason="outside_control",
            )
        ],
        local_purge=[
            LocalPurgeTask(
                task_id=uuid4(),
                meeting_id=uuid4(),
                task_type=LocalPurgeTaskType.PURGE_LOCAL_BUFFERS,
                state=LocalPurgeTaskState.PENDING,
                safe_reason="delete_requested",
                expires_at=expires_at,
            ),
            LocalPurgeTask(
                task_id=uuid4(),
                meeting_id=uuid4(),
                task_type=LocalPurgeTaskType.PURGE_LOCAL_EXPORTS,
                state=LocalPurgeTaskState.ACKNOWLEDGED,
                safe_reason="local_buffers_purged",
                expires_at=expires_at,
            ),
            LocalPurgeTask(
                task_id=uuid4(),
                meeting_id=uuid4(),
                task_type=LocalPurgeTaskType.CONFIRM_LOCAL_EXPIRY,
                state=LocalPurgeTaskState.UNREACHABLE,
                safe_reason="device_unreachable",
                expires_at=expires_at,
            ),
        ],
        activity=[
            LifecycleActivityItem(
                event_id=uuid4(),
                event_type="deletion_requested",
                actor_label="Owner/Admin",
                outcome="accepted",
                safe_reason="user_request",
                created_at=datetime.now(UTC),
            ),
            LifecycleActivityItem(
                event_id=uuid4(),
                event_type="local_purge_acknowledged",
                actor_label="Desktop device",
                outcome="completed",
                safe_reason="local_buffers_purged",
                created_at=datetime.now(UTC),
            ),
        ],
    )


def test_list_shell_renders_dense_controls_without_marketing_copy() -> None:
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        )
    )

    assert "Мои встречи" in page
    assert "Ближайшие" in page
    assert "Ближайшие встречи появятся после подключения календаря." in page
    assert 'href="/settings#calendar-connections"' in page
    assert "Подключить календари" in page
    assert "Командный синк" not in page
    assert "Записи встреч" in page
    assert "Новая" in page
    assert "Недавно обновленные" in page
    assert 'value="updated_desc" selected>Недавно обновленные</option>' in page
    css = _cabinet_css()
    assert "max-width: min(1120px, calc(100vw - 48px))" in css
    assert "min-height: 46px;" in css
    assert ".meeting-title { display: block; min-width: 0;" in css
    assert ".meeting-row.cabinet-row { grid-template-columns: 20px 20px minmax(0, 1fr) 32px auto;" in css
    assert ".desktop-embedded .cabinet-list-controls {" in css
    assert "grid-template-columns: minmax(0, 1fr) 32px;" in css
    assert ":focus-visible" in css
    assert "hero" not in page.lower()
    assert 'data-selection-toolbar' in page
    assert 'data-selection-toggle' in page
    assert 'class="cabinet-list-controls"' in page
    assert 'method="get"' in page
    assert 'data-hx-target="#meeting-list-region"' in page
    assert 'data-hx-select="#meeting-list-region"' in page
    assert 'data-clear-selection' not in page
    assert 'data-list-title' in page
    assert "Выбрано 0 / 1" in page
    assert "Выбрать все видимые записи" in page
    assert "Скачивание появится позже" in page
    assert 'data-tooltip="Скачивание появится позже"' in page
    assert "disabled aria-disabled=\"true\" data-download-disabled" in page
    assert '<input class="row-check selection-toggle" type="checkbox" data-selection-toggle' in page
    assert "padding-left: 13px;" in css
    assert ".selection-toggle {\n  flex: 0 0 16px;" in css
    assert ".row-check {\n  accent-color: var(--accent);\n  width: 16px;\n  height: 16px;\n  min-height: 16px;\n  margin: 0;" in css
    assert "selectionToggle.indeterminate = rows.length > 0 && !allSelected" in _cabinet_js()
    assert ".row-check {\n  appearance: none;" not in css
    assert ".row-check:checked::after" not in css
    assert "line-height: 32px;" in css
    assert ".icon-control {\n  width: 32px;\n  height: 32px;\n  min-height: 32px;" in css
    assert "padding: 0;" in css
    assert ".ui-icon {\n  width: 16px;\n  height: 16px;" in css
    assert ".row-icon .ui-icon { width: 14px; height: 14px; }" in css
    assert "stroke-width: 2;" in css
    assert 'data-icon="audio"' in page
    assert 'data-icon="bookmark"' in page
    assert 'data-icon="download"' in page
    assert 'data-icon="filter"' in page
    assert 'data-icon="sort"' in page
    assert 'data-icon="trash"' in page
    assert 'data-meeting-select' in page
    assert 'data-row-delete' in page
    assert 'data-row-delete-form' in page
    assert 'data-hx-post="/meetings/' in page
    assert 'name="confirmation_boundary"' in page
    assert 'id="delete-feedback-region"' in page
    assert 'data-delete-dialog' in page
    assert "Удалить запись?" in page
    assert "Удалить записи?" in page
    assert "Отмена" in page
    assert "Удалить" in page
    assert "Пометить непрочитанной" not in page
    assert "Mark as unread" not in page
    assert "□" not in page
    assert "≡" not in page
    assert "↕" not in page
    assert "⇩" not in page
    assert "⌫" not in page
    script = _cabinet_js()
    assert 'toolbar.dataset.selectionState = allSelected ? "all" : "partial"' in script
    assert "Снять выбор" in script
    assert "const shouldSelectAll = selectedRows().length !== rows.length" in script


def test_web_shell_uses_base_template_and_static_assets() -> None:
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        )
    )

    assert f'href="{CABINET_STATIC_URL}/cabinet.css"' in page
    assert f'src="{CABINET_STATIC_URL}/htmx-2.0.10.min.js"' in page
    assert f'src="{CABINET_STATIC_URL}/cabinet.js"' in page
    assert '<body data-surface-mode="standalone_browser">' in page
    assert 'data-icon="audio"' in page
    assert 'fill="none" stroke="currentColor" stroke-width="2"' in page
    assert "<style>" not in page
    assert "max-width: min(1120px, calc(100vw - 48px))" not in page
    assert ".meeting-row.cabinet-row" not in page


def test_legacy_render_helpers_keep_full_page_contract_after_template_refactor() -> None:
    list_page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        )
    )
    detail_page = render_meeting_detail_page(_review())
    deletion_page = render_deletion_report_page("Синтетическая встреча", _deletion_report())

    for page in (list_page, detail_page, deletion_page):
        assert "<!doctype html>" in page
        assert '<html lang="ru">' in page
        assert '<body data-surface-mode="standalone_browser">' in page
        assert 'class="app-shell" data-cabinet-shell' in page
        assert f'href="{CABINET_STATIC_URL}/cabinet.css"' in page
        assert f'src="{CABINET_STATIC_URL}/cabinet.js"' in page


def test_legacy_embedded_render_helpers_keep_webview_shell_contract() -> None:
    list_page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        ),
        embedded=True,
    )
    detail_page = render_meeting_detail_page(_review(), embedded=True)

    for page in (list_page, detail_page):
        assert "<!doctype html>" in page
        assert 'class="app-shell desktop-embedded"' in page
        assert '<body data-surface-mode="desktop_embedded">' in page
        assert 'href="/desktop/meetings"' in page

    assert "Record live" not in list_page + detail_page
    assert "Screen Recording" not in list_page + detail_page


def test_web_shell_keeps_sidebar_pinned_without_scrollbar() -> None:
    css = _cabinet_css()

    assert (
        ".app-shell.desktop-embedded {\n"
        "  grid-template-columns: 184px minmax(0, 1fr);\n"
        "  height: 100vh;\n"
        "  min-height: 0;\n"
        "  overflow: hidden;\n"
        "}"
    ) in css
    assert ".sidebar {\n  position: sticky;" in css
    assert "  height: 100vh;\n  overflow: hidden;" in css
    assert (
        ".desktop-embedded .main,\n"
        ".desktop-embedded .cabinet-main {\n"
        "  height: 100vh;\n"
        "  min-height: 0;\n"
        "  overflow-y: auto;\n"
        "}"
    ) in css
    assert ".desktop-embedded .main {\n  padding: 22px" in css
    assert ".desktop-embedded .cabinet-main {\n  padding: 24px" in css


def test_embedded_window_breakpoint_keeps_compact_rail_visible() -> None:
    css = _cabinet_css()

    assert (
        "@media (max-width: 980px) {\n"
        "  .app-shell { grid-template-columns: 1fr; }\n"
        "  .app-shell.desktop-embedded { grid-template-columns: 52px minmax(0, 1fr); }"
    ) in css
    assert ".desktop-embedded .sidebar {\n    display: flex;" in css
    assert "    width: 52px;" in css
    assert ".desktop-embedded .sidebar:hover," in css
    assert ".desktop-embedded.is-rail-pinned .sidebar {" in css
    assert ".desktop-embedded .cabinet-main { padding: 18px 14px 172px; }" in css


def test_embedded_shell_exposes_compact_rail_toggle_and_lucide_nav_icons() -> None:
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        ),
        embedded=True,
    )

    assert '<aside class="sidebar" id="cabinet-sidebar" data-cabinet-navigation>' in page
    assert 'data-cabinet-rail-toggle' in page
    assert 'aria-controls="cabinet-sidebar"' in page
    assert 'aria-expanded="false"' in page
    assert 'data-icon="panel-left-open"' in page
    assert 'aria-current="page"' in page
    assert 'href="/desktop/settings#calendar-connections"' in page
    for icon in ("search", "calendar-days", "users-round", "list-checks", "activity", "settings"):
        assert f'data-icon="{icon}"' in page


def test_settings_shell_renders_calendar_connection_anchor() -> None:
    page = render_settings_page()

    assert 'data-active-nav="settings"' in page
    assert 'id="calendar-connections"' in page
    assert "Подключить календари" in page
    assert 'href="/settings#calendar-connections"' in page
    assert 'href="/desktop/settings#calendar-connections"' not in page


def test_cabinet_rail_toggle_js_contract() -> None:
    js = _cabinet_js()

    assert "data-cabinet-rail-toggle" in js
    assert "is-rail-pinned" in js
    assert 'event.key === "Escape"' in js
    assert 'toggle.setAttribute("aria-expanded"' in js


def test_list_shell_renders_audio_video_transcript_and_upload_icons() -> None:
    audio = _item()
    audio.artifacts = [
        ArtifactEgressState(
            artifact_class="audio",
            state="available",
            label="Audio",
            reason=None,
            action="download",
        )
    ]
    video = _item()
    video.source = "video_recording"
    text = _item()
    text.transcript_available = True
    text.artifacts = [
        ArtifactEgressState(
            artifact_class="transcript",
            state="available",
            label="Transcript",
            reason=None,
            action="download",
        )
    ]
    upload = _item()
    upload.source = "manual_upload"
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[audio, video, text, upload],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        )
    )

    assert 'data-icon="audio"' in page
    assert 'data-icon="video"' in page
    assert 'data-icon="transcript"' in page
    assert 'data-icon="upload"' in page
    assert 'data-media-kind="аудио"' in page
    assert 'data-media-kind="видео"' in page
    assert 'data-media-kind="транскрипт"' in page
    assert 'data-media-kind="upload"' in page
    assert "▣" not in page
    assert "◁" not in page


def test_list_delete_ui_keeps_bounded_copy_and_metadata_only_surface() -> None:
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        )
    )

    assert "GRAF" in page
    assert "везде, где ее контролирует GRAF" in page
    assert "Это действие нельзя отменить" in page
    assert "Обсудили запуск кабинета встреч" not in page
    assert "fixture-mediascribe-private-job-id" not in page
    assert "storage_object_key" not in page
    assert "signed_url" not in page


def test_list_delete_script_json_encodes_bounded_copy(monkeypatch) -> None:
    monkeypatch.setattr("twobrain_rec_server.cabinet.rendering.BOUNDED_DELETE_COPY", 'Delete "quoted"\ncopy')

    page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        )
    )
    script = _cabinet_js()

    assert 'name="confirmation_boundary"' in page
    assert "Delete &quot;quoted&quot;" in page
    assert 'confirmation_boundary: "Delete' not in script
    assert "new FormData(form)" in script
    assert "fetch(" not in script
    assert 'window.htmx.ajax("POST"' in script


def test_detail_shell_renders_tabs_and_gated_actions() -> None:
    page = render_meeting_detail_page(_review())

    assert "Итоги" in page
    assert "Запись и расшифровка" in page
    assert 'role="tablist" aria-label="Содержимое встречи"' in page
    assert 'data-detail-tab="recording"' in page
    assert 'aria-selected="true" aria-controls="detail-panel-recording"' in page
    assert 'data-detail-panel="outcomes" hidden' in page
    assert 'data-detail-panel="recording"' in page
    assert "const activateDetailTab = (name)" in _cabinet_js()
    assert "Транскрипт готовится" in page
    assert "Видимость для команды" in page
    assert "Публичные ссылки" in page
    assert "Уже скачанные или экспортированные файлы" in page
    assert 'data-boundary-copy="Files already downloaded' in page
    assert "Удалить встречу в системах GRAF" in page
    assert "Request deletion" not in page
    assert "Запросить удаление" in page


def test_detail_shell_renders_playback_player_and_seekable_timestamps() -> None:
    review = _review()
    review.playback = PlaybackReviewState(
        available=True,
        duration_seconds=120,
        speed_options=[0.75, 1.0, 1.25, 1.5, 2.0],
        unavailable_reason="none",
        playback_path=f"/api/v1/cabinet/meetings/{review.meeting.meeting_id}/playback",
        policy_label="Аудио доступно для проверки",
        source_mode="combined_review_stream",
        included_sources=["local_microphone", "incoming_system"],
    )
    review.transcript = TranscriptReviewState(
        available=True,
        language="ru",
        search_enabled=True,
        segments=[
            TranscriptSegmentView(
                segment_id="safe-segment-1",
                sequence=0,
                start_seconds=0.0,
                end_seconds=10.0,
                timestamp_label="00:00",
                speaker_label="Speaker 1",
                source_role="local_microphone",
                text="Безопасный синтетический текст.",
                seekable=True,
                seek_seconds=0.0,
            ),
            TranscriptSegmentView(
                segment_id="safe-segment-2",
                sequence=1,
                start_seconds=12.5,
                end_seconds=20.0,
                timestamp_label="00:12",
                speaker_label="Speaker 2",
                source_role="incoming_system",
                text="Еще один безопасный синтетический текст.",
                seekable=True,
                seek_seconds=12.5,
            ),
        ],
    )

    page = render_meeting_detail_page(review)

    assert 'class="playback-bar detail-playback"' in page
    assert "data-playback-shell" in page
    assert '<audio class="playback-audio" data-playback-player preload="metadata"' in page
    assert '<audio data-playback-player controls preload="metadata"' not in page
    assert f'src="/api/v1/cabinet/meetings/{review.meeting.meeting_id}/playback"' in page
    assert 'data-source-mode="combined_review_stream"' in page
    assert 'data-playback-toggle' in page
    assert 'data-playback-skip="-15"' in page
    assert 'data-playback-skip="15"' in page
    assert "data-playback-current" in page
    assert "data-playback-duration" in page
    assert "data-playback-speed-toggle" in page
    assert 'data-seek-seconds="0.0"' in page
    assert 'data-seek-seconds="12.5"' in page
    assert 'class="timestamp timestamp-seek"' in page
    script = _cabinet_js()
    assert "currentTime = seekSeconds" in script
    assert "syncTime();" in script


def test_cabinet_web_py_no_longer_owns_inline_page_scripts() -> None:
    source = CABINET_WEB.read_text()

    assert "<script" not in source
    assert "_meeting_list_script" not in source
    assert "_detail_tabs_script" not in source
    assert "_playback_script" not in source
    assert "_render_code_entry_script" not in source
    assert "_render_auth_transition_script" not in source


def test_auth_page_composition_lives_in_templates() -> None:
    source = CABINET_WEB.read_text()

    assert 'class="auth-page"' not in source
    assert 'class="auth-panel"' not in source
    assert (CABINET_AUTH_TEMPLATES / "login.html").exists()
    assert (CABINET_AUTH_TEMPLATES / "signup.html").exists()
    assert (CABINET_AUTH_TEMPLATES / "email_code.html").exists()


def test_detail_shell_renders_speaker_timeline_segments() -> None:
    review = _review()
    review.playback = PlaybackReviewState(
        available=True,
        duration_seconds=120,
        speed_options=[0.75, 1.0, 1.25, 1.5, 2.0],
        unavailable_reason="none",
        playback_path=f"/api/v1/cabinet/meetings/{review.meeting.meeting_id}/playback",
        policy_label="Аудио доступно для проверки",
        source_mode="combined_review_stream",
        included_sources=["local_microphone", "incoming_system"],
    )
    review.speakers = SpeakerReviewState(
        available=True,
        assignment_state="reserved",
        degraded_reason=None,
        speakers=[
            SpeakerLane(
                speaker_key="speaker-1",
                label="Speaker 1",
                talk_time_percent=35,
                source_roles=["local_microphone"],
                segments=[SpeakerLaneSegment(start_seconds=0.0, end_seconds=12.0)],
            ),
            SpeakerLane(
                speaker_key="speaker-2",
                label="Speaker 2",
                talk_time_percent=65,
                source_roles=["incoming_system"],
                segments=[SpeakerLaneSegment(start_seconds=30.0, end_seconds=90.0)],
            ),
        ],
    )

    page = render_meeting_detail_page(review)

    assert "data-speaker-timeline" in page
    assert 'data-speaker-lane="speaker-1"' in page
    assert 'data-speaker-lane="speaker-2"' in page
    assert page.count("data-lane-segment") == 2
    assert 'title="Спикер 1 00:00-00:12"' in page
    assert 'aria-label="Спикер 2 00:30-01:30"' in page
    css = _cabinet_css()
    assert ".timeline-lane:nth-child(6n+1) .timeline-segment" in css
    assert ".timeline-lane:nth-child(6n+6) .timeline-segment" in css
    assert "left:0.00%" in page
    assert "width:10.00%" in page
    assert "left:25.00%" in page
    assert "width:50.00%" in page


def test_detail_shell_renders_unavailable_playback_without_audio_element() -> None:
    review = _review()
    review.playback = PlaybackReviewState(
        available=False,
        duration_seconds=120,
        unavailable_reason="policy_disabled",
        playback_path=None,
        policy_label="Аудио закрыто политикой доступа",
        source_mode="none",
        included_sources=[],
    )

    page = render_meeting_detail_page(review)

    assert '<section class="playback-bar detail-playback is-unavailable" data-source-mode="none">' in page
    assert "Аудио закрыто политикой доступа" in page
    assert "<audio" not in page
    assert "data-playback-player" not in page


def test_detail_shell_reserves_notes_assistant_template_without_internal_feature_labels() -> None:
    review = _review()
    review.notes = NotesReviewState(available=False, sections=[], unavailable_reason="generation_future")

    page = render_meeting_detail_page(review)

    assert "Кратко" in page
    assert "Решения" in page
    assert "Действия" in page
    assert "Продолжение" in page
    assert "Итоги готовятся" in page
    assert "AI notes are reserved for a later feature" not in page
    assert "No generated summary is shown yet" not in page
    assert "<h3>Ассистент</h3>" in page
    assert "<button type=\"button\" disabled>Ассистент</button>" in page
    assert "<h3>Шаблон</h3>" in page
    assert "feature 016" not in page.lower()
    assert "feature:016" not in page.lower()
    assert "016-meeting-detail" not in page


def test_detail_shell_renders_stored_outcomes_with_long_content_and_playback_spacing() -> None:
    review = _review()
    review.playback = PlaybackReviewState(
        available=True,
        duration_seconds=120,
        speed_options=[0.75, 1.0, 1.25, 1.5, 2.0],
        unavailable_reason="none",
        playback_path=f"/api/v1/cabinet/meetings/{review.meeting.meeting_id}/playback",
        policy_label="Аудио доступно для проверки",
        source_mode="combined_review_stream",
        included_sources=["local_microphone", "incoming_system"],
    )
    summary = NotesActionCategoryState(
        state="available",
        label="Итоги готовы",
        reason="Сохраненный итог доступен и связан с расшифровкой.",
        readiness_impact="closes_gap",
        copy_key="notes.summary.available",
        items=[
            OutcomeItemView(
                category="summary",
                sequence=0,
                text=(
                    "Синтетический длинный итог встречи занимает несколько строк, "
                    "чтобы проверить переносы, ширину карточки и совместимость с нижним плеером."
                ),
                truth_label="supported",
                source_refs=[
                    OutcomeSourceReferenceView(
                        sequence=1,
                        start_seconds=12.5,
                        end_seconds=20.0,
                        evidence_kind="segment",
                    )
                ],
            )
        ],
    )
    deferred = NotesActionCategoryState(
        state="not_found",
        label="Не найдено",
        reason="В расшифровке нет надежной опоры для этой категории.",
        readiness_impact="closes_gap",
        copy_key="notes.outcomes.not_found",
    )
    review.notes_action_truth = NotesActionTruthState(
        summary=summary,
        key_points=deferred,
        decisions=deferred,
        action_items=deferred,
        followups=deferred,
        risks=deferred,
        questions=deferred,
        evidence=summary,
        source_basis="stored_output",
    )

    page = render_meeting_detail_page(review)

    assert 'data-outcome-source-basis="stored_output"' in page
    assert 'data-outcome-category="summary"' in page
    assert 'data-outcome-state="available"' in page
    assert "Синтетический длинный итог встречи" in page
    assert "Источник: 00:12" in page
    assert "Ключевое" in page
    css = _cabinet_css()
    assert ".notes-outcome-row .outcome-item" in css
    assert "grid-column: 1 / -1" in css
    assert 'class="playback-bar detail-playback"' in page


def test_detail_shell_exposes_active_review_player_timeline_and_mobile_safe_contract() -> None:
    review = _review()
    review.playback = PlaybackReviewState(
        available=True,
        duration_seconds=180,
        speed_options=[0.75, 1.0, 1.25, 1.5, 2.0],
        unavailable_reason="none",
        playback_path=f"/api/v1/cabinet/meetings/{review.meeting.meeting_id}/playback",
        policy_label="Аудио доступно для проверки",
        source_mode="combined_review_stream",
        included_sources=["local_microphone", "incoming_system"],
    )
    review.transcript = TranscriptReviewState(
        available=True,
        language="ru",
        search_enabled=True,
        segments=[
            TranscriptSegmentView(
                segment_id="safe-review-segment-1",
                sequence=0,
                start_seconds=0.0,
                end_seconds=8.0,
                timestamp_label="00:00",
                speaker_label="Speaker 1",
                source_role="local_microphone",
                text="Безопасная синтетическая строка для проверки review.",
                seekable=True,
                seek_seconds=0.0,
            )
        ],
    )
    review.speakers = SpeakerReviewState(
        available=True,
        assignment_state="reserved",
        degraded_reason=None,
        speakers=[
            SpeakerLane(
                speaker_key="speaker-1",
                label="Speaker 1",
                talk_time_percent=60,
                source_roles=["local_microphone"],
                segments=[SpeakerLaneSegment(start_seconds=0.0, end_seconds=8.0)],
            )
        ],
    )
    category = NotesActionCategoryState(
        state="not_found",
        label="Не найдено",
        reason="Синтетический review не содержит надежного решения.",
        readiness_impact="closes_gap",
        copy_key="notes.outcomes.not_found",
    )
    review.notes_action_truth = NotesActionTruthState(
        summary=category,
        key_points=category,
        decisions=category,
        action_items=category,
        followups=category,
        risks=category,
        questions=category,
        evidence=category,
        source_basis="stored_output",
    )

    page = render_meeting_detail_page(review)

    assert 'class="tab active" role="tab" id="detail-tab-recording"' in page
    assert 'aria-selected="true" aria-controls="detail-panel-recording"' in page
    assert 'data-detail-panel="recording"' in page
    assert 'data-playback-shell' in page
    assert 'data-playback-player' in page
    assert 'data-playback-progress' in page
    assert 'data-seek-seconds="0.0"' in page
    assert 'data-speaker-timeline' in page
    assert 'data-speaker-lane="speaker-1"' in page
    assert page.count("data-lane-segment") == 1
    assert 'data-outcome-source-basis="stored_output"' in page
    assert page.count("data-outcome-category=") == 8
    css = _cabinet_css()
    assert "@media (max-width: 980px)" in css
    assert "@media (max-width: 540px)" in css
    assert ".detail-page-main { padding-bottom: 172px; }" in css
    assert ".timeline-lane { grid-template-columns: 68px minmax(0, 1fr) 34px; gap: 7px; }" in css


def test_052_owner_review_keeps_recording_playback_timeline_and_outcomes_separate() -> None:
    review = _review()
    review.playback = PlaybackReviewState(
        available=True,
        duration_seconds=180,
        speed_options=[0.75, 1.0, 1.25, 1.5, 2.0],
        unavailable_reason="none",
        playback_path=f"/api/v1/cabinet/meetings/{review.meeting.meeting_id}/playback",
        policy_label="Аудио доступно для проверки",
        source_mode="combined_review_stream",
        included_sources=["local_microphone", "incoming_system"],
    )
    review.speakers = SpeakerReviewState(
        available=True,
        assignment_state="reserved",
        degraded_reason=None,
        speakers=[
            SpeakerLane(
                speaker_key="speaker-1",
                label="Speaker 1",
                talk_time_percent=60,
                source_roles=["local_microphone"],
                segments=[SpeakerLaneSegment(start_seconds=0.0, end_seconds=8.0)],
            )
        ],
    )
    category = NotesActionCategoryState(
        state="available",
        label="Итоги готовы",
        reason="Сохраненный итог доступен и связан с расшифровкой.",
        readiness_impact="closes_gap",
        copy_key="notes.summary.available",
    )
    review.notes_action_truth = NotesActionTruthState(
        summary=category,
        key_points=category,
        decisions=category,
        action_items=category,
        followups=category,
        risks=category,
        questions=category,
        evidence=category,
        source_basis="stored_output",
    )

    page = render_meeting_detail_page(review)

    assert 'class="tab active" role="tab" id="detail-tab-recording"' in page
    assert 'id="detail-tab-outcomes" aria-selected="false"' in page
    assert 'data-detail-panel="outcomes" hidden' in page
    assert 'data-detail-panel="recording"' in page
    assert 'data-playback-shell' in page
    assert 'data-source-mode="combined_review_stream"' in page
    assert 'data-speaker-timeline' in page
    assert 'data-outcome-source-basis="stored_output"' in page
    assert "60%" in page
    assert 'window.location.hash === "#outcomes"' in _cabinet_js()
    assert page.count("data-outcome-category=") == 8


def test_embedded_shell_removes_native_capture_controls_and_copy() -> None:
    list_page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        ),
        embedded=True,
    )
    detail_page = render_meeting_detail_page(_review(), embedded=True)
    html = list_page + detail_page

    assert "desktop-embedded" in html
    assert "Recording &amp; Transcript" not in html
    for forbidden in ["Record live", "Stop", "Screen Recording", "Noise", "Accent", "Krisp Devices"]:
        assert forbidden not in html


def test_embedded_detail_preserves_playback_player_and_timestamp_seek() -> None:
    review = _review()
    review.playback = PlaybackReviewState(
        available=True,
        duration_seconds=120,
        speed_options=[0.75, 1.0, 1.25, 1.5, 2.0],
        unavailable_reason="none",
        playback_path=f"/api/v1/cabinet/meetings/{review.meeting.meeting_id}/playback",
        policy_label="Аудио доступно для проверки",
        source_mode="combined_review_stream",
        included_sources=["local_microphone", "incoming_system"],
    )
    review.transcript = TranscriptReviewState(
        available=True,
        language="ru",
        search_enabled=True,
        segments=[
            TranscriptSegmentView(
                segment_id="safe-segment-embedded",
                sequence=0,
                start_seconds=12.5,
                end_seconds=20.0,
                timestamp_label="00:12",
                speaker_label="Speaker 2",
                source_role="incoming_system",
                text="Безопасный синтетический текст.",
                seekable=True,
                seek_seconds=12.5,
            )
        ],
    )

    page = render_meeting_detail_page(review, embedded=True)

    assert 'class="app-shell desktop-embedded"' in page
    assert 'class="playback-bar detail-playback"' in page
    assert "data-playback-shell" in page
    assert '<audio class="playback-audio" data-playback-player preload="metadata"' in page
    assert '<audio data-playback-player controls preload="metadata"' not in page
    assert f'src="/api/v1/cabinet/meetings/{review.meeting.meeting_id}/playback"' in page
    assert 'data-source-mode="combined_review_stream"' in page
    assert 'data-playback-toggle' in page
    assert 'data-playback-skip="-15"' in page
    assert 'data-playback-skip="15"' in page
    assert 'data-seek-seconds="12.5"' in page
    assert "currentTime = seekSeconds" in _cabinet_js()


def test_deletion_report_shell_renders_metadata_only_lifecycle_truth() -> None:
    page = render_deletion_report_page("Sensitive customer sync", _deletion_report())

    assert "Отчет удаления" in page
    assert "Файлы под контролем GRAF" in page
    assert "Внешние зависимости" in page
    assert "Ограничения после выгрузки" in page
    assert "Очистка на устройстве" in page
    assert "События удаления" in page
    assert "удаление запрошено" in page
    assert "локальная очистка подтверждена" in page
    assert "Владелец/админ" in page
    assert "Десктоп" in page
    assert "ожидает" in page
    assert "подтверждено" in page
    assert "недоступно" in page
    assert BOUNDED_DELETE_COPY in page
    assert "Sensitive customer sync" in page
    assert "storage_object_key" not in page
    assert "external_job_id" not in page
    assert "/Users/" not in page
    assert "SAFE_TRANSCRIPT_TEXT" not in page
