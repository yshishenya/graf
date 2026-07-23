from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from twobrain_rec_server.api.schemas import (
    ArtifactDeletionState,
    ArtifactEgressState,
    CalendarContextCandidateView,
    ContentExportCapabilityResponse,
    ContentExportDefaults,
    ContentExportReadiness,
    DeletionVerificationReport,
    GovernanceActionState,
    GovernanceActionSummary,
    LifecycleActivityItem,
    LocalPurgeTask,
    MeetingAccessState,
    MeetingActivityResponse,
    MeetingCalendarContextSummary,
    MeetingFilterState,
    MeetingListItem,
    MeetingListResponse,
    MeetingProvenance,
    MeetingReviewResponse,
    MeetingUploadProgressState,
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
    TranscriptSpeakerTurnView,
)
from twobrain_rec_server.cabinet import view_models as cabinet_view_models
from twobrain_rec_server.cabinet.deletion_rendering import render_deletion_report_page
from twobrain_rec_server.cabinet.rendering import (
    render_calendar_settings_page,
    render_login_page,
    render_meeting_detail_page,
    render_meeting_list_page,
    render_meeting_unavailable_page,
    render_settings_page,
    render_signup_page,
)
from twobrain_rec_server.cabinet.templates import CABINET_STATIC_URL
from twobrain_rec_server.cabinet.view_models import calendar_settings_surface
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
        share=GovernanceActionState(
            state="available", label="Share", reason="Login-required sharing", destructive=False
        ),
        export=GovernanceActionState(
            state="disabled", label="Export package", reason="No package", destructive=False
        ),
        download=GovernanceActionState(
            state="disabled", label="Download", reason="No artifact", destructive=False
        ),
        retention=GovernanceActionState(
            state="planned", label="Retention policy planned", reason="future", destructive=False
        ),
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


def _item(*, calendar_context: MeetingCalendarContextSummary | None = None) -> MeetingListItem:
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
        calendar_context=calendar_context,
        future_slots=[
            SlotState(state="planned", label="Star", reason="future"),
            SlotState(state="planned", label="Tag", reason="future"),
        ],
    )


def _review(
    *, calendar_context: MeetingCalendarContextSummary | None = None
) -> MeetingReviewResponse:
    item = _item(calendar_context=calendar_context)
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
        transcript=TranscriptReviewState(
            available=False,
            language=None,
            degraded_reason="processing",
            search_enabled=False,
            segments=[],
        ),
        speakers=SpeakerReviewState(
            available=False, assignment_state="reserved", degraded_reason="processing", speakers=[]
        ),
        calendar_context=calendar_context,
        notes=NotesReviewState(available=False, sections=[], unavailable_reason="processing"),
        playback=PlaybackReviewState(
            available=False, duration_seconds=120, speed_options=[0.75, 1.0, 1.25, 1.5, 2.0]
        ),
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
        ),
        csrf_token="test-csrf-token",
    )

    assert "Мои встречи" in page
    assert "Ближайшие" not in page
    assert "Подключить календари" not in page
    assert "Пробный период" not in page
    assert "Пригласить" not in page
    assert 'data-playback-status-surface="list"' in page
    assert 'data-playback-state="unavailable"' in page
    assert 'data-playback-reason="no_audio"' in page
    assert "Командный синк" not in page
    assert "Записи встреч" in page
    assert "<span>Загрузить</span>" in page
    assert "Загрузить медиа" not in page
    assert page.count('id="meeting-search"') == 1
    assert 'aria-label="Поиск встреч"' in page
    assert "data-filter-disclosure" in page
    assert "data-sort-disclosure" in page
    assert 'aria-label="Фильтры"' in page
    assert 'aria-label="Сортировка: Недавно обновлённые"' in page
    assert 'value="updated_desc" selected>Недавно обновлённые</option>' in page
    css = _cabinet_css()
    assert "max-width: min(1120px, calc(100vw - 48px))" in css
    assert "min-height: 64px;" in css
    assert ".meeting-title { display: block; min-width: 0;" in css
    assert (
        ".meeting-row.cabinet-row { grid-template-columns: 20px 20px minmax(0, 1fr) 32px auto;"
        in css
    )
    assert (
        ".cabinet-list-controls {\n  width: auto;\n  min-width: 0;\n  margin-left: auto;\n  display: flex;"
        in css
    )
    assert ":focus-visible" in css
    assert "hero" not in page.lower()
    assert "data-selection-toolbar" in page
    assert "data-manual-upload-open" in page
    assert "data-manual-upload-dialog" in page
    assert 'data-upload-endpoint="/api/v1/cabinet/media-uploads"' in page
    assert "data-manual-upload-dropzone" in page
    assert "data-manual-upload-file-card" in page
    assert "data-manual-upload-file-name" in page
    assert 'accept="audio/*' not in page
    assert "video/*" not in page
    for extension in (".rf64", ".w64", ".adts", ".flac", ".mkv"):
        assert extension in page
    assert "data-upload-activity-list" in page
    assert "data-manual-upload-validation" in page
    assert "data-manual-upload-percent" not in page
    assert "data-manual-upload-progress" not in page
    assert "data-manual-upload-accepted" not in page
    assert "Перетащите файл сюда" in page
    assert 'name="duration_seconds"' in page
    assert 'type="hidden" name="duration_seconds"' in page
    assert 'type="number" name="duration_seconds"' not in page
    assert "Автозаполним" not in page
    assert "data-manual-upload-submit" in page
    assert 'aria-live="polite"' in page
    assert "data-selection-toggle" in page
    assert 'class="cabinet-list-controls"' in page
    assert 'method="get"' in page
    assert 'data-hx-target="#meeting-list-region"' in page
    assert 'data-hx-select="#meeting-list-region"' in page
    assert "data-clear-selection" in page
    assert "data-list-title" in page
    assert "Выбрано 0 / 1" in page
    assert "Выбрать все видимые записи" in page
    assert "Скачивание появится позже" not in page
    assert "data-download-disabled" not in page
    assert 'aria-label="Сохраненные"' not in page
    assert 'aria-label="Применить фильтры"' not in page
    assert 'class="toolbar-icons"' not in page
    assert '<input class="row-check selection-toggle" type="checkbox" data-selection-toggle' in page
    assert "padding-left: 13px;" in css
    assert ".selection-toggle {\n  flex: 0 0 16px;" in css
    assert (
        ".row-check {\n  accent-color: var(--accent);\n  width: 16px;\n  height: 16px;\n  min-height: 16px;\n  margin: 0;"
        in css
    )
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
    assert 'data-icon="bookmark"' not in page
    assert 'data-icon="download"' not in page
    assert 'data-icon="filter"' in page
    assert 'data-icon="sort"' in page
    assert 'data-icon="trash"' in page
    assert "data-meeting-select" in page
    assert '<span class="row-select-hit">' in page
    assert '<span class="row-select-hit" aria-hidden="true">' not in page
    assert "data-row-delete" in page
    assert "data-row-delete-form" in page
    assert 'data-hx-post="/meetings/' in page
    assert 'name="confirmation_boundary"' in page
    assert 'id="delete-feedback-region"' in page
    assert "Отчет удаления" not in page
    assert "data-delete-dialog" in page
    assert "Удалить запись?" in page
    assert 'role="status" aria-live="polite" data-delete-error' in page
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
    assert "row.remove()" in script
    assert "row.dataset.deletionRequested" not in script


def test_feature_104_removed_main_window_fragments_have_no_current_entry_point() -> None:
    sections = (
        SERVER_ROOT / "cabinet" / "templates" / "cabinet" / "components" / "sections.html"
    ).read_text()
    meeting_list = (
        SERVER_ROOT / "cabinet" / "templates" / "cabinet" / "pages" / "meeting_list_content.html"
    ).read_text()
    css = _cabinet_css()

    for marker in [
        "Пробный период 7 дней",
        "Пригласить",
        "Ближайшие встречи появятся",
        "Подключить календари",
        "Сохраненные",
        "Скачать выбранные записи",
        "selection_toolbar",
    ]:
        assert marker not in sections
        assert marker not in meeting_list

    assert "item.enabled" not in sections
    assert "item.count" not in sections

    for obsolete_selector in [
        ".trial {",
        ".upcoming {",
        ".metric-grid {",
        ".metric {",
        ".toolbar {",
        ".toolbar-icons {",
        ".cabinet-selection-toolbar,",
        ".first-run-download {",
        ".selection-actions {",
        ".selection-divider {",
        ".tooltip-wrap {",
        ".cabinet-sidebar-nav__count {",
        ".cabinet-list-control-icon {",
        ".desktop-embedded .cabinet-list-controls select,",
    ]:
        assert obsolete_selector not in css


def test_empty_meeting_list_reuses_toolbar_upload_and_native_recording() -> None:
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        )
    )

    assert "Пока нет записей" in page
    assert "Начните запись в приложении или загрузите файл кнопкой выше." in page
    assert "Первый запуск" not in page
    assert "Установите GRAF" not in page
    assert 'href="/download"' not in page
    assert "data-manual-upload-empty-open" not in page
    assert page.count("data-manual-upload-open") == 1
    assert "Подключить календари" not in page


def test_non_empty_meeting_list_does_not_show_first_run_download_handoff() -> None:
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        )
    )

    assert "Первый запуск" not in page
    assert 'href="/download">Скачать приложение</a>' not in page


def test_active_list_filters_expose_one_reset_without_extra_request_control() -> None:
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(
                q="синк", status="processing", access=None, sort="started_desc"
            ),
            generated_at=datetime.now(UTC),
        )
    )

    assert page.count('id="meeting-search"') == 1
    assert page.count("data-filter-reset") == 1
    assert 'href="/meetings"' in page
    assert 'aria-label="Сбросить поиск и фильтры"' in page
    assert 'aria-label="Активных фильтров: 1"' in page
    assert 'aria-label="Применить фильтры"' not in page
    assert (
        'data-hx-trigger="input changed delay:150ms from:#meeting-search, change from:select, submit"'
        in page
    )


def test_meeting_list_dynamic_selection_keeps_one_shell_boundary() -> None:
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        )
    )

    assert page.count("data-cabinet-shell") == 1
    assert page.count('id="cabinet-sidebar" data-cabinet-navigation') == 1
    assert page.count('id="meeting-list-region"') == 1
    assert 'data-hx-target="#meeting-list-region"' in page
    assert 'data-hx-select="#meeting-list-region"' in page


def test_web_shell_uses_base_template_and_static_assets() -> None:
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        )
    )

    assert f'href="{CABINET_STATIC_URL}/cabinet.css?v=' in page
    assert f'src="{CABINET_STATIC_URL}/htmx-2.0.10.min.js"' in page
    assert f'src="{CABINET_STATIC_URL}/cabinet.js?v=' in page
    assert f'src="{CABINET_STATIC_URL}/graf-wordmark-dark.png"' in page
    assert f'src="{CABINET_STATIC_URL}/graf-icon.png"' in page
    assert f'src="{CABINET_STATIC_URL}/graf-logo.svg"' not in page
    assert "Бесплатный" not in page
    assert '<body data-surface-mode="standalone_browser"' in page
    assert 'data-icon="audio"' in page
    assert 'fill="none" stroke="currentColor" stroke-width="2"' in page
    assert "<style>" not in page
    assert "max-width: min(1120px, calc(100vw - 48px))" not in page
    assert ".meeting-row.cabinet-row" not in page


def test_full_cabinet_pages_share_one_primary_sidebar_contract() -> None:
    list_page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        )
    )
    detail_page = render_meeting_detail_page(_review())
    deletion_page = render_deletion_report_page("Синтетическая встреча", _deletion_report())
    settings_page = render_settings_page()
    calendar_settings_page = render_calendar_settings_page(
        calendar_settings_surface(provider_payloads=[], sources=[]),
    )

    for page in (list_page, detail_page, deletion_page):
        assert page.count("data-cabinet-shell") == 1
        assert page.count('data-shell-scroll="contained"') == 1
        assert '<a class="skip-link" href="#cabinet-main">К содержимому</a>' in page
        assert page.count('id="cabinet-sidebar" data-cabinet-navigation') == 1
        assert page.count('aria-label="Навигация кабинета"') == 1
        assert page.count('aria-current="page"') == 1
        assert 'data-active-nav="meetings"' in page
        assert 'href="/meetings"' in page
        assert 'href="/settings/integrations/calendar"' in page
        assert "Пробный период" not in page
        assert "Пригласить" not in page
        assert "GRAF" in page

    assert settings_page.count("data-cabinet-shell") == 1
    assert settings_page.count('data-shell-scroll="contained"') == 1
    assert '<a class="skip-link" href="#cabinet-main">К содержимому</a>' in settings_page
    assert settings_page.count('id="cabinet-sidebar" data-cabinet-navigation') == 1
    assert settings_page.count('aria-label="Навигация кабинета"') == 1
    assert settings_page.count('aria-current="page"') == 1
    assert 'data-active-nav="settings"' in settings_page
    assert 'href="/settings/integrations/calendar"' in settings_page

    assert calendar_settings_page.count("data-cabinet-shell") == 1
    assert calendar_settings_page.count('data-shell-scroll="contained"') == 1
    assert (
        '<a class="skip-link" href="#calendar-settings-region">К содержимому</a>'
        in calendar_settings_page
    )
    assert calendar_settings_page.count('id="cabinet-sidebar" data-cabinet-navigation') == 1
    assert calendar_settings_page.count('aria-label="Навигация кабинета"') == 1
    assert calendar_settings_page.count('aria-current="page"') == 1
    assert 'data-active-nav="settings"' in calendar_settings_page
    assert 'href="/settings/integrations/calendar"' in calendar_settings_page


def test_meeting_unavailable_page_uses_safe_shell_and_matching_list_link() -> None:
    for embedded, list_path in ((False, "/meetings"), (True, "/desktop/meetings")):
        page = render_meeting_unavailable_page(embedded=embedded)

        assert page.count("data-cabinet-shell") == 1
        assert '<main id="cabinet-main" class="cabinet-main" tabindex="-1">' in page
        assert "Страница недоступна" in page
        assert "Эта страница больше недоступна или у вас нет доступа к ней." in page
        assert f'href="{list_path}"' in page
        assert "meeting_not_found" not in page
        assert "11111111-1111-1111-1111-111111111111" not in page


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
        assert '<body data-surface-mode="standalone_browser"' in page
        assert 'class="app-shell" data-shell-scroll="contained" data-cabinet-shell' in page
        assert '<a class="skip-link" href="#cabinet-main">К содержимому</a>' in page
        assert f'href="{CABINET_STATIC_URL}/cabinet.css?v=' in page
        assert f'src="{CABINET_STATIC_URL}/cabinet.js?v=' in page


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
        assert (
            'class="app-shell desktop-embedded" data-shell-scroll="contained" data-cabinet-shell'
            in page
        )
        assert '<body data-surface-mode="desktop_embedded"' in page
        assert 'href="/desktop/meetings"' in page

    assert "data-manual-upload-open" in list_page
    assert (
        'class="new-button manual-upload-trigger" type="button" data-manual-upload-open'
        in list_page
    )
    assert "data-manual-upload-dialog" in list_page
    assert 'data-upload-surface="desktop_embedded"' in list_page
    assert 'href="/desktop/upload"' not in list_page
    assert "Администрирование" not in list_page
    assert "Экспорт" not in list_page
    assert "Record live" not in list_page + detail_page
    assert "Screen Recording" not in list_page + detail_page


def test_web_shell_keeps_sidebar_pinned_without_scrollbar() -> None:
    css = _cabinet_css()

    assert (
        ".app-shell {\n"
        "  --playback-inline-start: var(--app-sidebar-width);\n"
        "  height: 100vh;\n"
        "  min-height: 0;\n"
        "  overflow: hidden;\n"
        "  display: grid;\n"
        "  grid-template-columns: var(--app-sidebar-width) minmax(0, 1fr);\n"
        "}"
    ) in css
    assert (
        ".app-shell.desktop-embedded {\n"
        "  grid-template-columns: var(--app-sidebar-width) minmax(0, 1fr);\n"
        "}"
    ) in css
    assert ".sidebar {\n  position: sticky;" in css
    assert "  height: 100vh;\n  overflow-x: hidden;\n  overflow-y: auto;" in css
    assert (
        ".main,\n.cabinet-main {\n  height: 100vh;\n  min-height: 0;\n  overflow-y: auto;\n}"
    ) in css
    assert "max-height: calc(100vh - 48px);" in css
    assert '.app-shell[data-mobile-scroll="page"] {' in css
    assert ".desktop-embedded .main {\n  padding: 22px" in css
    assert ".desktop-embedded .cabinet-main {\n  padding: 24px" in css


def test_embedded_window_breakpoints_keep_sidebar_stable_until_tight_width() -> None:
    css = _cabinet_css()

    assert "  flex-wrap: wrap;\n  justify-content: space-between;" in css
    assert "  width: min(760px, 100%);\n  min-width: 0;" in css
    assert (
        "@media (max-width: 980px) {\n"
        "  .app-shell { grid-template-columns: 1fr; }\n"
        "  .app-shell:not(.desktop-embedded) { --playback-inline-start: 0px; }\n"
        "  .app-shell.desktop-embedded { grid-template-columns: var(--app-sidebar-width) minmax(0, 1fr); }"
    ) in css
    assert "  .desktop-embedded .sidebar { display: flex; }" in css
    assert "  .desktop-embedded .cabinet-rail-toggle { display: none; }" in css
    assert (
        "@media (max-width: 720px) {\n"
        "  .app-shell.desktop-embedded { grid-template-columns: var(--app-rail-width) minmax(0, 1fr); }"
    ) in css
    assert "    width: var(--app-rail-width);" in css
    assert "  .desktop-embedded .sidebar:hover," not in css
    assert ".desktop-embedded.is-rail-pinned .sidebar {" in css
    assert "--playback-inline-start: var(--app-rail-width);" in css
    assert "--playback-inline-start: var(--app-sidebar-width);" in css
    assert "left: var(--playback-inline-start);" in css
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
    assert page.count('id="cabinet-sidebar" data-cabinet-navigation') == 1
    assert page.count('aria-label="Навигация кабинета"') == 1
    assert page.count('aria-current="page"') == 1
    assert 'href="#">' not in page
    assert "data-cabinet-rail-toggle" in page
    assert 'aria-controls="cabinet-sidebar"' in page
    assert 'aria-expanded="false"' in page
    assert 'data-icon="panel-left-open"' in page
    assert 'aria-current="page"' in page
    assert 'href="/desktop/meetings"' in page
    assert 'href="/desktop/settings/integrations/calendar"' in page
    for icon in ("search", "calendar-days", "settings"):
        assert f'data-icon="{icon}"' in page
    for removed_icon in ("users-round", "list-checks", "activity"):
        assert f'data-icon="{removed_icon}"' not in page


def test_settings_shell_renders_calendar_connection_anchor() -> None:
    page = render_settings_page()

    assert 'data-active-nav="settings"' in page
    assert 'id="calendar-connections"' in page
    assert "Подключить календари" in page
    assert 'href="/settings/integrations/calendar"' in page
    assert 'href="/desktop/settings/integrations/calendar"' not in page


def test_calendar_settings_reuses_common_cabinet_shell() -> None:
    page = render_calendar_settings_page(
        calendar_settings_surface(provider_payloads=[], sources=[]), embedded=True
    )

    assert page.count("data-cabinet-shell") == 1
    assert '<aside class="sidebar" id="cabinet-sidebar" data-cabinet-navigation>' in page
    assert "data-cabinet-rail-toggle" in page
    assert 'data-active-nav="settings"' in page
    assert 'href="/desktop/settings/integrations/calendar"' in page
    assert page.count('class="sidebar-foot"') == 1
    assert "Пробный период" not in page
    assert "GRAF" in page


def test_098_calendar_settings_renders_auto_context_filter_boundary_once() -> None:
    page = render_calendar_settings_page(
        calendar_settings_surface(provider_payloads=[], sources=[]),
        embedded=True,
    )

    copy = (
        "Эти фильтры управляют подсказками и списком ближайших встреч. "
        "Приватные события и события на весь день не используются для "
        "автоматического контекста записи."
    )
    assert page.count(copy) == 1


def test_sidebar_markup_lives_in_reusable_sections_macro() -> None:
    pages_dir = SERVER_ROOT / "cabinet" / "templates" / "cabinet" / "pages"
    sections_template = (
        SERVER_ROOT / "cabinet" / "templates" / "cabinet" / "components" / "sections.html"
    ).read_text()

    assert all(
        '<aside class="sidebar"' not in path.read_text() for path in pages_dir.glob("*.html")
    )
    assert sections_template.count('<aside class="sidebar"') == 1
    assert "{% macro cabinet_sidebar(" in sections_template
    assert "{{ cabinet_sidebar(" in sections_template


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
    assert 'data-media-kind="медиа"' in page
    assert "▣" not in page


def test_list_shell_renders_server_upload_progress_in_recording_row() -> None:
    item = _item()
    item.status = "uploading"
    item.status_label = "Uploading"
    item.upload = MeetingUploadProgressState(
        status="uploading",
        label="Отправляем",
        uploaded_bytes=24,
        total_bytes=40,
        progress_percent=60,
        is_active=True,
    )

    page = render_meeting_list_page(
        MeetingListResponse(
            items=[item],
            filters=MeetingFilterState(
                q="uploading", status=None, access=None, sort="updated_desc"
            ),
            generated_at=datetime.now(UTC),
        ),
        poll_url="/meetings?q=uploading",
    )

    assert "Отправляем 60%" in page
    assert 'aria-label="Прогресс отправки записи"' in page
    assert 'aria-valuenow="60"' in page
    assert 'style="width: 60%"' in page
    assert "data-upload-progress-active" in page
    assert 'hx-trigger="every 1s"' in page
    assert 'hx-get="/meetings?q=uploading"' in page
    assert "◁" not in page


def test_list_shell_polls_processing_recordings_until_review_ready() -> None:
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        ),
        poll_url="/meetings",
    )

    assert "Проектный синк" in page
    assert 'hx-trigger="every 1s"' in page
    assert 'hx-get="/meetings"' in page


def test_desktop_empty_list_polls_for_new_local_uploads() -> None:
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        ),
        embedded=True,
        poll_url="/desktop/meetings",
    )

    assert "Пока нет записей" in page
    assert 'hx-trigger="every 1s"' in page
    assert 'hx-get="/desktop/meetings"' in page


def test_ready_meeting_list_polls_while_playback_is_preparing() -> None:
    item = _item().model_copy(
        update={
            "status": "ready",
            "playback": PlaybackReviewState(
                state="preparing",
                reason_code="normalization_running",
                label="Аудио готовится",
                automatic_recovery=True,
            ),
        }
    )
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[item],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        ),
        poll_url="/meetings",
    )

    assert "data-upload-progress-poll" in page
    assert 'hx-get="/meetings"' in page


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
    monkeypatch.setattr(
        "twobrain_rec_server.cabinet.rendering.BOUNDED_DELETE_COPY", 'Delete "quoted"\ncopy'
    )

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
    assert "fetch(form.action" in script
    assert "if (!response.ok)" in script
    assert '"HX-Request": "true"' in script
    assert "playbackRecoveryRequest = fetch(pollUrl" in script


def test_detail_shell_renders_tabs_and_gated_actions() -> None:
    page = render_meeting_detail_page(_review())

    assert "Итоги" in page
    assert "Расшифровка" in page
    assert 'role="tablist" aria-label="Содержимое встречи"' in page
    assert 'data-detail-tab="recording"' in page
    assert 'aria-selected="true" aria-controls="detail-panel-recording"' in page
    assert 'data-detail-panel="outcomes" hidden' in page
    assert 'data-detail-panel="recording"' in page
    assert "const activateDetailTab = (name)" in _cabinet_js()
    assert "Транскрипт готовится" in page
    assert "Поделиться" in page
    assert 'data-share-dialog-open' in page
    assert "Ещё" in page
    assert 'data-meeting-panel-open="more"' in page
    assert "Видимость для команды" not in page
    assert "Публичные ссылки" not in page
    assert 'data-boundary-copy="Files already downloaded' in page
    assert "Удалить встречу…" not in page
    assert "Request deletion" not in page
    assert "Удалить встречу?" not in page


def test_detail_shell_hides_more_when_no_action_or_detail_is_available() -> None:
    review = _review()
    review.content_exports = None
    review.governance.download.state = "disabled"
    review.governance.delete.state = "planned"
    review.artifacts = []
    review.activity.items = []
    review.speakers.speakers = []
    review.provenance.media_revision_id = None
    review.provenance.local_media_revision_id = None
    review.calendar_context = None
    review.deletion_truth_copy = ""

    page = render_meeting_detail_page(review)

    assert 'data-meeting-panel-open="more"' not in page
    assert 'id="meeting-context-more"' not in page


def test_detail_shell_renders_playback_player_and_seekable_timestamps() -> None:
    review = _review()
    review.playback = PlaybackReviewState(
        available=True,
        duration_seconds=120,
        speed_options=[0.75, 1.0, 1.25, 1.5, 2.0],
        unavailable_reason="none",
        playback_path=f"/api/v1/cabinet/meetings/{review.meeting.meeting_id}/playback",
        policy_label="Аудио доступно для проверки",
        source_mode="stored_review_m4a",
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
                speaker_label="SPEAKER_00",
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
                speaker_label="SPEAKER_01",
                source_role="incoming_system",
                text="Еще один безопасный синтетический текст.",
                seekable=True,
                seek_seconds=12.5,
            ),
        ],
    )

    page = render_meeting_detail_page(review)

    assert 'class="playback-bar detail-playback"' in page
    assert "data-playback-transcript" in page
    assert 'data-playback-live-status role="status" aria-live="polite"' in page
    assert "data-playback-shell" in page
    assert '<audio class="playback-audio" data-playback-player preload="metadata"' in page
    assert '<audio data-playback-player controls preload="metadata"' not in page
    assert f'src="/api/v1/cabinet/meetings/{review.meeting.meeting_id}/playback"' in page
    assert 'data-source-mode="stored_review_m4a"' in page
    assert "data-playback-toggle" in page
    assert 'data-playback-toggle aria-label="Воспроизвести">▶</button>' in page
    assert "data-playback-error" in page
    assert 'role="status" aria-live="polite" hidden' in page
    assert "Воспроизведение временно недоступно." in page
    assert 'data-playback-skip="-15"' in page
    assert 'data-playback-skip="15"' in page
    assert "data-playback-current" in page
    assert "data-playback-duration" in page
    assert "data-playback-speed-toggle" in page
    assert 'data-seek-seconds="0.0"' in page
    assert 'data-seek-seconds="12.5"' in page
    assert 'class="timestamp timestamp-seek"' in page
    script = _cabinet_js()
    assert "seekTo(seekSeconds, { autoplay: true })" in script
    assert "syncTime();" in script
    assert (
        'toggle.setAttribute("aria-label", playing ? "Приостановить" : "Воспроизвести")' in script
    )
    assert 'player.addEventListener("error", reportPlaybackFailure)' in script
    assert "recoverySignature(currentPlayback) === recoverySignature(nextPlayback)" in script
    assert "currentPlayback.replaceWith(nextPlayback)" in script
    assert "currentTranscript.replaceWith(nextTranscript)" in script
    assert "response.status === 404 || response.status === 410" in script
    assert "renderPlaybackTerminalState(detail)" in script
    assert "!response.ok || response.redirected" in script
    assert "showPlaybackRecoveryNotice(detail)" in script
    assert "clearPlaybackRecoveryNotice(detail)" in script
    assert "Не удалось обновить статус. GRAF попробует снова автоматически." in script
    assert "dataset.playbackRecoveryCopy" in script
    assert "stopPlaybackRecoveryPolling()" in script


def test_detail_shell_prefers_derived_turns_and_keeps_raw_fallback_safe() -> None:
    review = _review()
    review.playback = PlaybackReviewState(
        available=True,
        duration_seconds=120,
        speed_options=[0.75, 1.0, 1.25, 1.5, 2.0],
        unavailable_reason="none",
        playback_path=f"/api/v1/cabinet/meetings/{review.meeting.meeting_id}/playback",
        policy_label="Аудио доступно для проверки",
        source_mode="stored_review_m4a",
        included_sources=["local_microphone", "incoming_system"],
    )
    review.transcript = TranscriptReviewState(
        available=True,
        language="ru",
        search_enabled=True,
        segments=[
            TranscriptSegmentView(
                segment_id="raw-only-id",
                sequence=0,
                start_seconds=10.0,
                end_seconds=11.0,
                timestamp_label="00:10",
                speaker_label="SPEAKER_00",
                source_role="incoming_system",
                text="raw fragment must not be rendered when a turn exists",
                seekable=True,
                seek_seconds=10.0,
            )
        ],
        speaker_turns=[
            TranscriptSpeakerTurnView(
                turn_id="turn-id",
                sequence=0,
                start_seconds=10.0,
                end_seconds=12.0,
                timestamp_label="00:10",
                speaker_label="SPEAKER_00",
                source_role="incoming_system",
                text="<synthetic merged turn>",
                source_segment_ids=["raw-only-id", "raw-second-id"],
                seekable=True,
                seek_seconds=10.0,
            )
        ],
    )

    page = render_meeting_detail_page(review)

    assert "&lt;synthetic merged turn&gt;" in page
    assert "raw fragment must not be rendered when a turn exists" not in page
    assert 'data-seek-seconds="10.0"' in page
    assert "data-playback-transcript" in page


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


def test_auth_pages_do_not_render_disabled_placeholders_as_links() -> None:
    pages = [
        render_login_page(workspace_id=uuid4(), providers=[]),
        render_signup_page(workspace_id=uuid4(), providers=[]),
    ]

    for page in pages:
        assert 'href="#"' not in page
        assert 'aria-disabled="true"' in page
        assert '<span class="mini-link is-disabled" aria-disabled="true">' in page


def test_login_page_links_to_app_download_handoff() -> None:
    page = render_login_page(workspace_id=uuid4(), providers=[])

    assert "Приложение нужно для записи встреч." in page
    assert 'href="/download">Скачать GRAF</a>' in page


def test_detail_shell_renders_speaker_timeline_segments() -> None:
    review = _review()
    review.playback = PlaybackReviewState(
        available=True,
        duration_seconds=120,
        speed_options=[0.75, 1.0, 1.25, 1.5, 2.0],
        unavailable_reason="none",
        playback_path=f"/api/v1/cabinet/meetings/{review.meeting.meeting_id}/playback",
        policy_label="Аудио доступно для проверки",
        source_mode="stored_review_m4a",
        included_sources=["local_microphone", "incoming_system"],
    )
    review.speakers = SpeakerReviewState(
        available=True,
        assignment_state="reserved",
        degraded_reason=None,
        speakers=[
            SpeakerLane(
                speaker_key="speaker_00",
                label="SPEAKER_00",
                talk_time_percent=35,
                source_roles=["local_microphone"],
                segments=[SpeakerLaneSegment(start_seconds=0.0, end_seconds=12.0)],
            ),
            SpeakerLane(
                speaker_key="speaker_01",
                label="SPEAKER_01",
                talk_time_percent=65,
                source_roles=["incoming_system"],
                segments=[SpeakerLaneSegment(start_seconds=30.0, end_seconds=90.0)],
            ),
        ],
    )
    review.transcript = TranscriptReviewState(
        available=True,
        language="ru",
        search_enabled=True,
        speaker_turns=[
            TranscriptSpeakerTurnView(
                turn_id="synthetic-turn",
                sequence=0,
                start_seconds=0,
                end_seconds=40,
                timestamp_label="00:00",
                speaker_key="speaker_00",
                speaker_label="Очень длинное имя спикера для проверки подписи",
                source_role="local_microphone",
                text="Безопасный синтетический текст.",
                seekable=True,
                seek_seconds=0,
            )
        ],
    )

    page = render_meeting_detail_page(review)

    assert "data-speaker-timeline" in page
    assert 'data-speaker-lane="speaker_00"' in page
    assert 'data-speaker-lane="speaker_01"' in page
    assert page.count('data-timeline-track role="button"') == 2
    assert 'aria-label="Перейти по дорожке SPEAKER_00"' in page
    assert page.count("data-timeline-playhead") == 2
    assert page.count("data-lane-segment") == 2
    assert 'title="SPEAKER_00 00:00-00:12"' in page
    assert 'aria-label="SPEAKER_01 00:30-01:30"' in page
    css = _cabinet_css()
    assert "--timeline-label-width: 86px" in css
    assert (
        "grid-template-columns: var(--timeline-label-width) minmax(0, 1fr) var(--timeline-value-width)"
        in css
    )
    assert ".playback-range-thumb" in css
    assert "width: 16px" in css
    assert ".timeline-lane.is-active" in css
    assert ".segment.is-current" in css
    assert ".speaker-color-1 { --speaker-color: #7a65ff; }" in css
    assert "background: var(--speaker-color)" in css
    assert ".speaker-color-6 { --speaker-color: #d96aa6; }" in css
    assert 'class="timeline-lane speaker-color-1"' in page
    assert 'class="timeline-lane speaker-color-2"' in page
    assert page.count("speaker-color-1") >= 4
    assert 'class="segment speaker-color-1"' in page
    assert "left:0.00%" in page
    assert "width:10.00%" in page
    assert "left:25.00%" in page
    assert "width:50.00%" in page
    script = _cabinet_js()
    assert "const seekTo = (seconds, { follow = true, autoplay = false } = {}) =>" in script
    assert "const followTranscript = (seconds) =>" in script
    assert 'track.addEventListener("click"' in script
    assert 'lane.classList.toggle("is-active"' in script


def test_detail_shell_renders_speaker_name_editor_only_for_authorized_review() -> None:
    review = _review()
    review.speakers = SpeakerReviewState(
        available=True,
        assignment_state="reserved",
        can_rename=True,
        speakers=[
            SpeakerLane(
                speaker_key="speaker_00",
                label="Мария",
                display_name="Мария",
                talk_time_percent=100,
                segments=[SpeakerLaneSegment(start_seconds=0, end_seconds=10)],
            )
        ],
    )

    editable = render_meeting_detail_page(review, csrf_token="synthetic-csrf")
    review.speakers.can_rename = False
    readonly = render_meeting_detail_page(review, csrf_token="synthetic-csrf")

    assert "data-speaker-name-form" in editable
    assert 'name="display_name" value="Мария"' in editable
    assert 'name="csrf_token" value="synthetic-csrf"' in editable
    assert f'action="/meetings/{review.meeting.meeting_id}/speakers/speaker_00"' in editable
    assert "data-speaker-name-error" in editable
    assert "initSpeakerNameForms" in _cabinet_js()
    assert "data-speaker-name-form" not in readonly
    assert "Мария" in readonly


def test_playback_timeline_keeps_full_width_lanes_and_separate_speaker_manager() -> None:
    review = _review()
    review.playback = PlaybackReviewState(
        available=True,
        can_play=True,
        state="available",
        duration_seconds=40,
        speed_options=[1.0],
        playback_path="/synthetic.wav",
        policy_label="Аудио доступно",
        source_mode="stored_review_m4a",
        included_sources=["local_microphone", "incoming_system"],
    )
    review.speakers = SpeakerReviewState(
        available=True,
        assignment_state="available",
        can_rename=True,
        speakers=[
            SpeakerLane(
                speaker_key="speaker_00",
                label="Очень длинное имя спикера для проверки подписи",
                talk_time_percent=100,
                segments=[SpeakerLaneSegment(start_seconds=0, end_seconds=40)],
            )
        ],
    )

    page = render_meeting_detail_page(review, csrf_token="synthetic-csrf")
    css = _cabinet_css()
    script = _cabinet_js()

    assert 'class="timeline-scale playback-scale"' in page
    assert 'class="timeline-scale lane-scale"' in page
    assert "data-speaker-name-open" in page
    assert "Очень длинное имя спикера для проверки подписи" in page
    assert "data-speaker-manager" in page
    assert "data-speaker-manager-toggle" in page
    assert 'aria-controls="speaker-manager-popover"' in page
    assert 'id="speaker-manager-popover"' in page
    assert 'aria-controls="speaker-manager-form-speaker_00"' in page
    assert 'id="speaker-manager-form-speaker_00"' in page
    assert page.count("data-speaker-name-form") == 1
    assert ".timeline-scale" in css
    assert ".playback-scale .playback-progress" in css
    assert ".playback-range-thumb" in css
    assert "grid-column: 2;" in css
    assert ".lane-scale" in css
    assert ".timeline-speaker-name {" not in css
    assert ".speaker-manager-popover" in css
    assert ".speaker-manager-popover[hidden]" in css
    assert "row-gap: 1px;" in css
    assert "max-height: 96px;" in css
    assert "overflow-wrap: anywhere;" in css
    assert "data-speaker-name-open" in script
    assert "data-speaker-manager-toggle" in script
    assert "data-speaker-name-cancel" in script
    assert 'event.key !== "Escape"' in script


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

    assert 'class="playback-bar detail-playback is-unavailable"' in page
    assert 'data-playback-state="unavailable"' in page
    assert 'data-playback-reason="no_audio"' in page
    assert 'data-source-mode="none"' in page
    assert "Аудио закрыто политикой доступа" in page
    assert "<audio" not in page


def test_detail_shell_renders_all_non_playable_states_without_repair_controls() -> None:
    cases = (
        (
            "preparing",
            "normalization_retry_wait",
            "Подготовка занимает больше времени. GRAF продолжит автоматически",
            True,
        ),
        ("unavailable", "unsupported_media", "Формат файла не поддерживается", False),
        ("deleting", "meeting_deleting", "Аудио удаляется", False),
        ("deleted", "meeting_deleted", "Аудио удалено", False),
    )

    for state, reason_code, label, automatic_recovery in cases:
        review = _review()
        review.playback = PlaybackReviewState(
            state=state,
            reason_code=reason_code,
            label=label,
            automatic_recovery=automatic_recovery,
            can_play=False,
            action="disabled",
            available=False,
            duration_seconds=120,
            unavailable_reason=(
                "processing"
                if state == "preparing"
                else "deleting"
                if state == "deleting"
                else "deleted"
                if state == "deleted"
                else "failed"
            ),
        )

        page = render_meeting_detail_page(review)

        assert f'data-playback-state="{state}"' in page
        assert f'data-playback-reason="{reason_code}"' in page
        assert label in page
        assert "<audio" not in page
        forbidden_controls = (
            "data-playback-retry",
            "reprocess-playback",
            "start-playback-backfill",
            ">повторить<",
            ">загрузить заново<",
        )
        assert not any(marker in page.casefold() for marker in forbidden_controls)
        if state == "preparing":
            assert 'aria-live="polite"' in page
    assert "data-playback-player" not in page


def test_terminal_playback_copy_renders_as_plain_status_without_user_work() -> None:
    review = _review()
    review.playback = PlaybackReviewState(
        state="unavailable",
        reason_code="corrupt_source",
        label=cabinet_view_models.playback_reason_copy("corrupt_source", locale="ru"),
        can_play=False,
        action="disabled",
        available=False,
        duration_seconds=120,
        unavailable_reason="failed",
    )

    page = render_meeting_detail_page(review)

    assert "Файл повреждён и не может быть воспроизведён" in page
    assert 'role="status" tabindex="0"' in page
    assert "<audio" not in page
    forbidden = (
        "retry",
        "reprocess",
        "backfill",
        "повторить",
        "загрузить заново",
        "обратитесь к администратору",
    )
    assert not any(marker in page.casefold() for marker in forbidden)


def test_detail_shell_keeps_simple_outcomes_copy_without_internal_feature_labels() -> None:
    review = _review()
    review.notes = NotesReviewState(
        available=False, sections=[], unavailable_reason="generation_future"
    )

    page = render_meeting_detail_page(review)

    assert "Кратко" in page
    assert "Решения" in page
    assert "Действия" in page
    assert "Продолжение" in page
    assert "Итоги готовятся" in page
    assert "AI notes are reserved for a later feature" not in page
    assert "No generated summary is shown yet" not in page
    assert "Итоги встречи" in page
    assert "<h3>Ассистент</h3>" not in page
    assert '<button type="button" disabled>Ассистент</button>' not in page
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
        source_mode="stored_review_m4a",
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
        source_mode="stored_review_m4a",
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
                speaker_label="SPEAKER_00",
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
                speaker_key="speaker_00",
                label="SPEAKER_00",
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
    assert "data-playback-shell" in page
    assert "data-playback-player" in page
    assert "data-playback-progress" in page
    assert 'data-seek-seconds="0.0"' in page
    assert "data-speaker-timeline" in page
    assert 'data-speaker-lane="speaker_00"' in page
    assert page.count("data-lane-segment") == 1
    assert 'data-outcome-source-basis="stored_output"' in page
    assert page.count("data-outcome-category=") == 8
    css = _cabinet_css()
    assert "@media (max-width: 980px)" in css
    assert "@media (max-width: 540px)" in css
    assert ".detail-page-main { padding-bottom: 172px; }" in css
    assert ".detail-playback { --timeline-label-width: 68px; --timeline-value-width: 34px; }" in css
    assert ".speaker-timeline { gap: 4px; }" in css


def test_052_owner_review_keeps_recording_playback_timeline_and_outcomes_separate() -> None:
    review = _review()
    review.playback = PlaybackReviewState(
        available=True,
        duration_seconds=180,
        speed_options=[0.75, 1.0, 1.25, 1.5, 2.0],
        unavailable_reason="none",
        playback_path=f"/api/v1/cabinet/meetings/{review.meeting.meeting_id}/playback",
        policy_label="Аудио доступно для проверки",
        source_mode="stored_review_m4a",
        included_sources=["local_microphone", "incoming_system"],
    )
    review.speakers = SpeakerReviewState(
        available=True,
        assignment_state="reserved",
        degraded_reason=None,
        speakers=[
            SpeakerLane(
                speaker_key="speaker_00",
                label="SPEAKER_00",
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

    assert 'class="tab active" role="tab" id="detail-tab-outcomes"' in page
    assert 'id="detail-tab-outcomes" aria-selected="true"' in page
    assert 'data-detail-panel="outcomes"' in page
    assert 'data-detail-panel="recording" hidden' in page
    assert "data-playback-shell" in page
    assert 'data-source-mode="stored_review_m4a"' in page
    assert "data-speaker-timeline" in page
    assert 'data-outcome-source-basis="stored_output"' in page
    assert "60%" in page
    assert 'window.location.hash === "#outcomes"' in _cabinet_js()
    assert page.count("data-outcome-category=") == 8


def test_098_auto_calendar_context_renders_once_in_web_and_embedded_list_and_detail() -> None:
    # FR-033/FR-043/FR-048: all cabinet surfaces reuse one exact product label.
    summary = MeetingCalendarContextSummary(
        state="matched_auto",
        label="Из календаря",
        title_source="calendar",
        needs_owner_action=False,
    )
    item = _item(calendar_context=summary)
    list_response = MeetingListResponse(
        items=[item],
        filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
        generated_at=datetime.now(UTC),
    )
    review = _review(calendar_context=summary)

    pages = {
        "web-list": render_meeting_list_page(list_response),
        "embedded-list": render_meeting_list_page(list_response, embedded=True),
        "web-detail": render_meeting_detail_page(review),
        "embedded-detail": render_meeting_detail_page(review, embedded=True),
    }

    for surface, page in pages.items():
        assert page.count("Из календаря") == 1, surface
        assert "calendar context title" not in page.lower()
        assert "attendee@example.test" not in page


def test_098_private_skip_reason_renders_only_in_owner_detail() -> None:
    # FR-010/FR-033/FR-042: protected reason is absent from list/accessibility text.
    generic = MeetingCalendarContextSummary(
        state="skipped_private",
        label="Без контекста календаря",
        title_source="generic",
        needs_owner_action=False,
    )
    owner = MeetingCalendarContextSummary(
        state="skipped_private",
        label="Без контекста календаря",
        reason_label="Приватное событие пропущено",
        title_source="generic",
        needs_owner_action=False,
    )

    list_page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item(calendar_context=generic)],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        )
    )
    detail_page = render_meeting_detail_page(_review(calendar_context=owner))

    assert "Приватное событие пропущено" not in list_page
    assert detail_page.count("Приватное событие пропущено") == 1


def test_098_ambiguity_chooser_uses_safe_native_controls_and_graf_primitives() -> None:
    # FR-014/FR-033/FR-037; SC-003/SC-013: owner choice is explicit, safe and keyboard-native.
    context = MeetingCalendarContextSummary(
        state="ambiguous",
        label="Нужно выбрать встречу",
        title_source="generic",
        needs_owner_action=True,
    )
    candidates = [
        CalendarContextCandidateView(
            event_id=UUID("98000000-0000-0000-0000-000000000001"),
            safe_title="Синтетический дизайн-ревью",
            starts_at=datetime(2026, 7, 13, 9, 0, tzinfo=UTC),
            ends_at=datetime(2026, 7, 13, 10, 0, tzinfo=UTC),
            safe_source_label="Рабочий календарь",
        ),
        CalendarContextCandidateView(
            event_id=UUID("98000000-0000-0000-0000-000000000002"),
            safe_title="Синтетический планинг",
            starts_at=datetime(2026, 7, 13, 9, 30, tzinfo=UTC),
            ends_at=datetime(2026, 7, 13, 10, 30, tzinfo=UTC),
            safe_source_label="Рабочий календарь",
        ),
    ]
    # T050 is deliberately test-first: attach the planned bounded projection without
    # weakening the current strict response schema before T052/T055/T056 implement it.
    object.__setattr__(context, "candidates", candidates)
    object.__setattr__(context, "can_change", True)
    object.__setattr__(context, "can_clear", False)

    page = render_meeting_detail_page(
        _review(calendar_context=context),
        csrf_token="synthetic-calendar-context-csrf",
    )

    assert "Несколько встреч подходят по времени. GRAF ничего не выбрал." in page
    assert "data-calendar-context-chooser" in page
    chooser_tag = page[page.rfind("<section", 0, page.index("data-calendar-context-chooser")) :]
    assert 'class="' in chooser_tag
    chooser_classes = chooser_tag.split(">", 1)[0].split('class="', 1)[1].split('"', 1)[0].split()
    assert "panel" in chooser_classes
    assert "<fieldset" in page
    assert "<legend>Выберите встречу</legend>" in page
    assert page.count('type="radio"') == 2
    assert page.count('name="event_id"') == 2
    assert 'aria-describedby="calendar-context-choice-help"' in page
    assert 'id="calendar-context-chooser-heading"' in page
    assert 'tabindex="-1"' in page
    assert "autofocus" in page
    assert 'id="calendar-context-result"' in page
    assert 'aria-live="polite"' in page
    assert "Сохранить выбор" in page
    assert "Продолжить без календаря" in page
    assert "Синтетический дизайн-ревью" in page
    assert "Синтетический планинг" in page
    assert page.count("Рабочий календарь") == 2
    assert "09:00" in page
    assert "10:30" in page
    assert "private-candidate-title" not in page
    assert "hidden-calendar-attendee@example.test" not in page
    assert "passcode=" not in page


def test_098_calendar_context_state_copy_has_bounded_ru_en_pairs() -> None:
    # FR-033/FR-042/FR-051: ambiguity/correction copy is localized product language, not enum text.
    expected = {
        "matched_user": ("Выбрано вами", "Selected by you"),
        "ambiguous": ("Нужно выбрать встречу", "Choose a meeting"),
        "no_context": ("Без календарного контекста", "No calendar context"),
        "declined_by_user": (
            "Вы начали запись без календарного контекста",
            "You started recording without calendar context",
        ),
        "cleared_by_user": ("Контекст убран вами", "Context removed by you"),
    }

    for state, (ru_copy, en_copy) in expected.items():
        assert cabinet_view_models.calendar_context_state_copy(state, locale="ru") == ru_copy
        assert cabinet_view_models.calendar_context_state_copy(state, locale="en") == en_copy


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
    for forbidden in [
        "Record live",
        "Stop",
        "Screen Recording",
        "Noise",
        "Accent",
        "Krisp Devices",
    ]:
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
        source_mode="stored_review_m4a",
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
                speaker_label="SPEAKER_00",
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
    assert 'data-source-mode="stored_review_m4a"' in page
    assert "data-playback-toggle" in page
    assert 'data-playback-skip="-15"' in page
    assert 'data-playback-skip="15"' in page
    assert 'data-seek-seconds="12.5"' in page
    assert "seekTo(seekSeconds, { autoplay: true })" in _cabinet_js()


def test_120_meeting_detail_renders_one_accessible_metadata_only_export_dialog() -> None:
    review = _review()
    result_id = uuid4()
    review.content_exports = ContentExportCapabilityResponse(
        processing_result_id=result_id,
        outcome_set_id=None,
        transcript=ContentExportReadiness(state="available"),
        summary=ContentExportReadiness(state="missing", reason="stored_summary_missing"),
        combined=ContentExportReadiness(state="missing", reason="combined_components_unavailable"),
        formats={
            "transcript": ["txt", "md", "csv", "xlsx", "json", "srt"],
            "summary": ["txt", "md", "xlsx", "json"],
            "combined": ["txt", "md", "xlsx", "json"],
        },
        defaults=ContentExportDefaults(),
        language="ru",
        duration_seconds=3661,
    )

    page = render_meeting_detail_page(review, csrf_token="synthetic-csrf")
    embedded_page = render_meeting_detail_page(
        review,
        csrf_token="synthetic-csrf",
        embedded=True,
    )

    assert page.count("data-export-dialog-open") == 1
    assert 'aria-controls="content-export-dialog"' in page
    assert 'aria-labelledby="content-export-title"' in page
    assert 'id="content-export-title" tabindex="-1" data-export-dialog-title' in page
    assert f'data-processing-result-id="{result_id}"' in page
    assert '<select name="content_scope" data-export-scope>' in page
    assert '<select name="format" data-export-format>' in page
    assert "Расшифровка" in page
    assert "Итоги" in page
    assert "недоступно" in page
    assert page.count("<optgroup") == 4
    assert "Файл останется на компьютере после удаления встречи из GRAF." in page
    assert "SAFE_TRANSCRIPT_TEXT" not in page
    assert "data-export-status" in page
    assert 'aria-live="polite"' in page
    assert "<summary>Дополнительно</summary>" in page
    assert "data-export-options-details" in page
    assert "open data-export-options-details" not in page
    assert "Технические детали" not in page
    assert "data-export-technical-details" not in page
    assert "data-export-preview" not in page
    assert "Ревизия" not in page
    assert "Длительность" not in page
    assert "Хранение файла" not in page
    assert 'class="primary" data-export-submit>Скачать файл</button>' in page
    assert 'class="primary" data-export-submit>Сохранить…</button>' in embedded_page
    assert "data-export-copy" in page
    assert "setBusy(true)" in _cabinet_js()
    assert 'requestExport("txt")' in _cabinet_js()
    assert "navigator.clipboard.writeText" in _cabinet_js()
    assert "export_generation_failed" in _cabinet_js()
    assert "audit_unavailable" in _cabinet_js()
    assert "format.replaceChildren(...groups)" in _cabinet_js()
    assert "select:not([disabled])" in _cabinet_js()
    assert "URL.createObjectURL(blob)" in _cabinet_js()
    assert "returnFocus?.isConnected" in _cabinet_js()
    assert "@media (prefers-reduced-motion: reduce)" in _cabinet_css()
    assert "@media (forced-colors: active)" in _cabinet_css()


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
