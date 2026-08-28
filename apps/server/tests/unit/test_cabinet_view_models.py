from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from twobrain_rec_server.api.schemas import (
    ArtifactEgressState,
    GovernanceActionState,
    GovernanceActionSummary,
    MeetingAccessState,
    MeetingCalendarContextSummary,
    MeetingListItem,
    MeetingUploadProgressState,
    PlaybackPreparationState,
    SlotState,
)
from twobrain_rec_server.cabinet import view_models
from twobrain_rec_server.calendar.normalize import normalize_calendar_participants
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    MediaRevision,
    Meeting,
    ProcessingResult,
    ProcessingWorkflow,
    RecordingCalendarContextLink,
    TranscriptSegment,
)
from twobrain_rec_server.domain.media_filenames import (
    LEGACY_SERIALIZED_MEDIA_FILENAME_EXTENSIONS,
    SUPPORTED_MEDIA_FILENAME_EXTENSIONS,
)
from twobrain_rec_server.domain.statuses import (
    MediaRevisionSourceKind,
    MeetingStatus,
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
    ProcessingStatus,
    SummaryStatus,
)


def _meeting(processing_status: ProcessingStatus = ProcessingStatus.PROCESSED) -> Meeting:
    return Meeting(
        id=uuid4(),
        workspace_id=uuid4(),
        created_by_user_id=uuid4(),
        device_id=uuid4(),
        local_recording_id="local-id",
        title=None,
        started_at=datetime(2026, 6, 16, 8, 0, tzinfo=UTC),
        duration_seconds=60,
        status="ingested_pending_processing",
        processing_status=processing_status.value,
    )


def _lineaged_context(
    meeting: Meeting,
    result: ProcessingResult,
) -> tuple[MediaRevision, ProcessingWorkflow]:
    result.meeting_id = meeting.id
    result.workspace_id = meeting.workspace_id
    result.media_revision_id = result.media_revision_id or uuid4()
    result.processing_workflow_id = result.processing_workflow_id or uuid4()
    return (
        MediaRevision(
            id=result.media_revision_id,
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            local_media_revision_id=f"synthetic-{result.media_revision_id}",
            revision_number=1,
            source_kind=MediaRevisionSourceKind.INITIAL_MIXED_RECORDING.value,
            status="accepted",
        ),
        ProcessingWorkflow(
            id=result.processing_workflow_id,
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            media_revision_id=result.media_revision_id,
            workflow_id=f"processing/{result.media_revision_id}",
            purpose="transcription",
            status=ProcessingStatus.PROCESSED.value,
        ),
    )


def _transcript_evidence(rows: list[DiarizationSegment]) -> list[TranscriptSegment]:
    return [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=row.processing_result_id,
            meeting_id=row.meeting_id,
            workspace_id=row.workspace_id,
            sequence=row.sequence,
            start_seconds=row.start_seconds,
            end_seconds=row.end_seconds,
            text=row.text,
            source_role=row.source_role,
            source_role_original=row.source_role,
        )
        for row in rows
    ]


def _owner_access() -> MeetingAccessState:
    return MeetingAccessState(
        state="owner",
        label="Owner",
        reason="Synthetic owner access.",
        can_view=True,
        can_share=True,
        can_manage_team_visibility=True,
        can_download=True,
        can_export=True,
    )


def test_playback_read_model_is_independent_from_transcript_processing_state() -> None:
    durable = PlaybackPreparationState(
        state="available",
        reason_code="canonical_ready",
        label="Аудио готово",
        can_play=True,
    )

    for processing_state in ("processing", "failed", "ready"):
        playback = view_models.playback_state(
            _meeting(),
            processing_state,
            durable,
        )

        assert playback.state == "available"
        assert playback.can_play is True
        assert playback.available is True
        assert playback.playback_path is not None


def test_v5_mixed_review_keeps_one_canonical_source_and_transcript_when_playback_is_unavailable() -> (
    None
):
    meeting = _meeting()
    revision = MediaRevision(
        id=uuid4(),
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        local_media_revision_id="v5-mixed-cabinet-truth",
        revision_number=1,
        source_kind=MediaRevisionSourceKind.INITIAL_MIXED_RECORDING.value,
        status="accepted",
    )
    available_playback = view_models.playback_state(
        meeting,
        "ready",
        PlaybackPreparationState(
            state="available",
            reason_code="canonical_ready",
            label="Аудио готово",
            can_play=True,
        ),
        media_revision=revision,
    )
    unavailable_playback = view_models.playback_state(
        meeting,
        "ready",
        PlaybackPreparationState(
            state="unavailable",
            reason_code="corrupt_source",
            label="Файл повреждён и не может быть воспроизведён",
        ),
        media_revision=revision,
    )
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=uuid4(),
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("1.000"),
            text="synthetic transcript segment",
            source_role="mixed",
        )
    ]
    transcript_state = view_models.transcript_state(
        language="ru",
        transcript_segments=transcript,
        diarization_segments=[],
        status="ready",
        playback_available=unavailable_playback.available,
        playback_duration_seconds=unavailable_playback.duration_seconds,
    )

    assert available_playback.included_sources == ["canonical_mixed"]
    assert unavailable_playback.available is False
    assert transcript_state.available is False
    assert transcript_state.degraded_reason == "diarization_pending"


def test_playback_preparing_state_never_creates_a_dead_player_path() -> None:
    playback = view_models.playback_state(
        _meeting(),
        "ready",
        PlaybackPreparationState(
            state="preparing",
            reason_code="normalization_retry_wait",
            label="Подготовка занимает больше времени. GRAF продолжит автоматически",
            automatic_recovery=True,
        ),
    )

    assert playback.state == "preparing"
    assert playback.automatic_recovery is True
    assert playback.can_play is False
    assert playback.available is False
    assert playback.playback_path is None


def test_playback_reason_copy_has_complete_bounded_ru_en_pairs() -> None:
    expected = {
        "normalization_queued": (
            "Аудио готовится автоматически",
            "Audio is being prepared automatically",
        ),
        "normalization_running": (
            "Аудио готовится автоматически",
            "Audio is being prepared automatically",
        ),
        "normalization_publishing": (
            "Завершаем подготовку аудио",
            "Finishing audio preparation",
        ),
        "normalization_retry_wait": (
            "Подготовка занимает больше времени. GRAF продолжит автоматически",
            "Preparation is taking longer. GRAF will continue automatically",
        ),
        "reconciliation_pending": (
            "GRAF автоматически восстанавливает подготовку аудио",
            "GRAF is automatically recovering audio preparation",
        ),
        "canonical_artifact_missing": (
            "GRAF автоматически восстанавливает аудио",
            "GRAF is automatically recovering the audio",
        ),
        "empty_source": ("В исходном файле нет данных", "The source file is empty"),
        "no_audio": (
            "В файле нет пригодной аудиодорожки",
            "The file has no usable audio track",
        ),
        "ambiguous_audio_tracks": (
            "В файле несколько равноправных аудиодорожек",
            "The file has multiple equally valid audio tracks",
        ),
        "unsupported_media": (
            "Формат или кодек файла не поддерживается",
            "The file format or codec is not supported",
        ),
        "encrypted_media": (
            "Защищённый файл нельзя подготовить для воспроизведения",
            "Protected media cannot be prepared for playback",
        ),
        "corrupt_source": (
            "Файл повреждён и не может быть воспроизведён",
            "The file is corrupt and cannot be played",
        ),
        "limit_exceeded": (
            "Файл превышает допустимые параметры",
            "The file exceeds supported limits",
        ),
        "source_missing": (
            "Исходный файл больше не хранится в GRAF",
            "The source file is no longer retained by GRAF",
        ),
        "source_mismatch": (
            "Целостность исходного файла не подтверждена",
            "Source file integrity could not be confirmed",
        ),
    }

    for reason_code, (ru_copy, en_copy) in expected.items():
        assert view_models.playback_reason_copy(reason_code, locale="ru") == ru_copy
        assert view_models.playback_reason_copy(reason_code, locale="en") == en_copy
        assert "retry" not in en_copy.casefold()
        assert "re-upload" not in en_copy.casefold()

    assert view_models.playback_reason_copy("private-new-reason", locale="ru") == (
        "Аудио недоступно"
    )
    assert view_models.playback_reason_copy("private-new-reason", locale="en") == (
        "Audio is unavailable"
    )


def _governance() -> GovernanceActionSummary:
    disabled = GovernanceActionState(
        state="disabled", label="Disabled", reason="Synthetic.", destructive=False
    )
    return GovernanceActionSummary(
        share=disabled,
        export=disabled,
        download=disabled,
        retention=disabled,
        delete=GovernanceActionState(
            state="planned", label="Delete", reason="Synthetic.", destructive=True
        ),
    )


def _list_item(
    *,
    source: str = "desktop_recording",
    title: str = "Synthetic meeting",
    started_at: datetime | None = datetime(2026, 6, 16, 8, 0, tzinfo=UTC),
    uploaded_at: datetime | None = None,
    recording_display_timezone_offset_minutes: int | None = None,
    transcript_available: bool = False,
    artifacts: list[ArtifactEgressState] | None = None,
    status: str = "ready",
    primary_action: str = "open",
    upload: MeetingUploadProgressState | None = None,
    calendar_context: MeetingCalendarContextSummary | None = None,
    playback: PlaybackPreparationState | None = None,
) -> MeetingListItem:
    return MeetingListItem(
        meeting_id=uuid4(),
        title=title,
        started_at=started_at,
        uploaded_at=uploaded_at,
        ended_at=None,
        recording_display_timezone_offset_minutes=recording_display_timezone_offset_minutes,
        duration_seconds=65,
        source=source,
        status=status,
        status_label=status,
        status_reason=None,
        primary_action=primary_action,
        transcript_available=transcript_available,
        diarization_available=False,
        notes_available=False,
        updated_at=None,
        access=_owner_access(),
        artifacts=artifacts or [],
        governance=_governance(),
        future_slots=[SlotState(state="planned", label="Star", reason="Synthetic.")],
        upload=upload,
        calendar_context=calendar_context,
        playback=playback or PlaybackPreparationState(),
    )


def test_common_display_helpers_for_meeting_rows() -> None:
    audio = _list_item(
        artifacts=[
            ArtifactEgressState(
                artifact_class="audio",
                state="available",
                label="Audio",
                reason=None,
                action="download",
            )
        ]
    )
    transcript = _list_item(transcript_available=True)
    video = _list_item(source="video_recording")
    upload = _list_item(source="manual_upload")

    assert view_models.meeting_media_kind(audio) == "audio"
    assert view_models.meeting_media_label(audio) == "аудио"
    assert view_models.meeting_media_kind(transcript) == "transcript"
    assert view_models.meeting_media_label(video) == "видео"
    assert view_models.meeting_media_kind(upload) == "upload"
    assert view_models.meeting_media_label(upload) == "медиа"
    assert view_models.format_duration(65) == "1 мин"
    assert view_models.normalize_meeting_list_sort("duration_asc") == "duration_asc"
    assert view_models.normalize_meeting_list_sort("unknown") == "started_desc"
    assert (
        view_models.normalize_meeting_list_sort("unknown", fallback="updated_desc")
        == "updated_desc"
    )


def test_meeting_list_row_presentation_is_immutable_and_keeps_one_status_slot() -> None:
    item = _list_item(title="Запись")
    item.updated_at = datetime(2026, 6, 16, 11, 30, tzinfo=UTC)
    item.playback.state = "available"
    item.playback.reason_code = "canonical_ready"
    item.playback.label = "Аудио готово"
    item.playback.can_play = True

    presentation = view_models.meeting_list_row_presentation(item, time_basis="meeting")
    updated = view_models.meeting_list_row_presentation(item, time_basis="updated")

    assert presentation.display_title == "Запись"
    assert presentation.duration_label == "1 мин"
    assert presentation.time_label == "16 июн, 08:00"
    assert presentation.status_kind is None
    assert presentation.status_label is None
    assert presentation.progress_percent is None
    assert presentation.content_readiness_label == "Расшифровка и итоги пока недоступны"
    assert presentation.open_accessible_name == "Открыть встречу Запись, 16 июн, 08:00"
    assert updated.time_label == "Обновлено 16 июн, 11:30"
    with pytest.raises(FrozenInstanceError):
        presentation.display_title = "Другое"  # type: ignore[misc]


def test_meeting_list_row_presentation_exposes_content_readiness_without_extra_status() -> None:
    item = _list_item(
        transcript_available=True,
        playback=PlaybackPreparationState(
            state="available",
            reason_code="canonical_ready",
            label="Аудио готово",
            can_play=True,
        ),
    )

    processing = view_models.meeting_list_row_presentation(item, time_basis="meeting")
    item.notes_action_truth.source_basis = "stored_output"
    ready = view_models.meeting_list_row_presentation(item, time_basis="meeting")

    assert processing.content_readiness_label == "Расшифровка готова · итоги готовятся"
    assert ready.content_readiness_label == "Расшифровка и итоги готовы"
    assert processing.status_label is None
    assert ready.status_label is None


def test_meeting_list_row_presentation_never_relabels_meeting_time_as_update_time() -> None:
    item = _list_item(title="Планирование")

    presentation = view_models.meeting_list_row_presentation(item, time_basis="updated")

    assert presentation.time_label == "Без даты"


def test_meeting_list_row_presentation_preserves_authoritative_generated_looking_title() -> None:
    item = _list_item(title="Запись 21 июл, 19:22")

    presentation = view_models.meeting_list_row_presentation(item, time_basis="meeting")

    assert presentation.display_title == "Запись 21 июл, 19:22"
    assert presentation.open_accessible_name == "Открыть встречу Запись 21 июл, 19:22"


def test_recording_display_title_uses_calendar_title_and_recording_time_without_mutation() -> None:
    meeting = _meeting()
    meeting.title = "Планирование релиза"
    meeting.title_source = "calendar"
    meeting.recording_display_timezone_offset_minutes = 180

    assert view_models.recording_display_title(meeting) == "Планирование релиза — 16 июн, 11:00"
    assert meeting.title == "Планирование релиза"


def test_recording_display_title_uses_app_context_then_generic_fallback() -> None:
    app_context = _meeting()
    app_context.title = "Zoom - 2026-06-16 08:00"
    app_context.title_source = "app_context"
    app_context.recording_display_timezone_offset_minutes = 180

    generic = _meeting()
    generic.title = None
    generic.title_source = "generic"
    generic.recording_display_timezone_offset_minutes = 180

    assert view_models.recording_display_title(app_context) == "Zoom — 16 июн, 11:00"
    assert view_models.recording_display_title(generic) == "Запись 16 июн, 11:00"


def test_recording_display_title_preserves_authoritative_user_title() -> None:
    meeting = _meeting()
    meeting.title = "Моя встреча"
    meeting.title_source = "user_confirmed"

    assert view_models.recording_display_title(meeting) == "Моя встреча"


def test_meeting_list_title_neutralizes_generated_capture_without_rewriting_source() -> None:
    generated = _meeting()
    generated.title = "Current display system audio - 2026-07-13 12:14"
    generated.started_at = datetime(2026, 7, 13, 9, 14, tzinfo=UTC)
    generated.recording_display_timezone_offset_minutes = 180
    upload = _meeting()
    upload.title = "manual-upload-mrc4escf-hbo5nhsk"
    derived = _meeting()
    derived.title = "Quarterly_sync.mp3"
    derived.title_source = "file_name_derived"

    assert view_models.meeting_list_title(generated) == "Запись 13 июл, 12:14"
    assert view_models.meeting_list_title(upload, source="manual_upload") == "Загруженная запись"
    assert view_models.meeting_list_title(derived, source="manual_upload") == "Quarterly sync"
    assert generated.title == "Current display system audio - 2026-07-13 12:14"


@pytest.mark.parametrize("title_source", sorted(view_models.AUTHORITATIVE_TITLE_SOURCES))
def test_meeting_list_title_preserves_authoritative_fallback_looking_title(
    title_source: str,
) -> None:
    meeting = _meeting()
    meeting.title = "Запись без названия"
    meeting.title_source = title_source

    expected = (
        "Запись без названия — 16 июн, 08:00"
        if title_source == "calendar"
        else "Запись без названия"
    )
    assert view_models.meeting_list_title(meeting) == expected

    item = _list_item(title=view_models.meeting_list_title(meeting))
    presentation = view_models.meeting_list_row_presentation(item, time_basis="meeting")
    assert presentation.display_title == expected
    assert presentation.open_accessible_name == f"Открыть встречу {expected}"


@pytest.mark.parametrize(
    ("item", "kind", "label", "progress"),
    [
        (
            _list_item(status="deleted_future"),
            "deleting",
            "Удаляется",
            None,
        ),
        (
            _list_item(
                status="failed",
                calendar_context=MeetingCalendarContextSummary(
                    state="ambiguous",
                    label="Нужно выбрать встречу",
                    needs_owner_action=True,
                ),
            ),
            "failed",
            "Не удалось обработать",
            None,
        ),
        (
            _list_item(
                status="submitted",
                primary_action="wait",
                upload=MeetingUploadProgressState(
                    status="expired",
                    label="Нужна помощь",
                    uploaded_bytes=10,
                    total_bytes=100,
                    is_active=False,
                ),
            ),
            "failed",
            "Не удалось обработать",
            None,
        ),
        (
            _list_item(
                calendar_context=MeetingCalendarContextSummary(
                    state="ambiguous",
                    label="Нужно выбрать встречу",
                    needs_owner_action=True,
                ),
                playback=PlaybackPreparationState(
                    state="available",
                    reason_code="canonical_ready",
                    label="Аудио готово",
                    can_play=True,
                ),
            ),
            "calendar_choice",
            "Нужен выбор",
            None,
        ),
        (
            _list_item(status="local_only", primary_action="wait"),
            "saved_local",
            "Сохранено на Mac",
            None,
        ),
        (
            _list_item(
                status="uploading",
                primary_action="wait",
                upload=MeetingUploadProgressState(
                    status="uploading",
                    label="Отправляем",
                    uploaded_bytes=40,
                    total_bytes=100,
                    progress_percent=40,
                    is_active=True,
                ),
            ),
            "uploading_measured",
            "Отправляем 40%",
            40,
        ),
        (
            _list_item(
                status="uploading",
                primary_action="wait",
                upload=MeetingUploadProgressState(
                    status="uploading",
                    label="Отправляем",
                    uploaded_bytes=100,
                    total_bytes=100,
                    progress_percent=100,
                    is_active=True,
                ),
            ),
            "uploading",
            "Отправляем",
            None,
        ),
        (
            _list_item(status="processing", primary_action="wait"),
            "processing",
            "Обрабатывается",
            None,
        ),
        (
            _list_item(
                playback=PlaybackPreparationState(
                    state="preparing",
                    reason_code="normalization_running",
                    label="Аудио готовится автоматически",
                )
            ),
            "audio_preparing",
            "Аудио готовится",
            None,
        ),
        (
            _list_item(
                playback=PlaybackPreparationState(
                    state="unavailable",
                    reason_code="no_audio",
                    label="Аудио недоступно",
                )
            ),
            "without_audio",
            "Без аудио",
            None,
        ),
        (
            _list_item(
                status="partial",
                playback=PlaybackPreparationState(
                    state="available",
                    reason_code="canonical_ready",
                    label="Аудио готово",
                    can_play=True,
                ),
            ),
            "limited",
            "Готово с ограничениями",
            None,
        ),
        (
            _list_item(
                playback=PlaybackPreparationState(
                    state="available",
                    reason_code="canonical_ready",
                    label="Аудио готово",
                    can_play=True,
                )
            ),
            None,
            None,
            None,
        ),
    ],
)
def test_meeting_list_status_projection_uses_one_total_precedence(
    item: MeetingListItem,
    kind: str | None,
    label: str | None,
    progress: int | None,
) -> None:
    presentation = view_models.meeting_list_row_presentation(item, time_basis="meeting")

    assert presentation.status_kind == kind
    assert presentation.status_label == label
    assert presentation.progress_percent == progress


@pytest.mark.parametrize("upload_status", ["failed", "aborted", "expired"])
def test_meeting_list_presentation_status_projects_terminal_uploads_as_failed(
    upload_status: str,
) -> None:
    upload = MeetingUploadProgressState(
        status=upload_status,
        label="Нужна помощь",
        uploaded_bytes=10,
        total_bytes=100,
        is_active=False,
    )

    item = _list_item(status="uploading", primary_action="wait", upload=upload)
    deleting_item = _list_item(status="deleted_future", primary_action="wait", upload=upload)

    assert view_models.meeting_list_presentation_status(item) == "failed"
    assert view_models.meeting_list_presentation_status(deleting_item) == "deleted_future"


@pytest.mark.parametrize(
    "calendar_state", ["matched_auto", "matched_user", "no_context", "cleared_by_user"]
)
def test_meeting_list_ready_state_suppresses_playback_and_calendar_normality(
    calendar_state: str,
) -> None:
    item = _list_item(
        calendar_context=MeetingCalendarContextSummary(
            state=calendar_state,
            label="Обычная календарная истина",
            needs_owner_action=False,
        ),
        playback=PlaybackPreparationState(
            state="available",
            reason_code="canonical_ready",
            label="Аудио готово",
            can_play=True,
        ),
    )

    presentation = view_models.meeting_list_row_presentation(item, time_basis="meeting")

    assert presentation.status_label is None


def test_recording_time_labels_use_started_at_with_truthful_fallbacks() -> None:
    recorded = _list_item(started_at=datetime(2026, 6, 26, 23, 30, tzinfo=UTC))
    timezone_shifted = _list_item(
        started_at=datetime(2026, 6, 27, 2, 30, tzinfo=timezone(timedelta(hours=3)))
    )
    offset_shifted = _list_item(
        started_at=datetime(2026, 6, 26, 21, 30, tzinfo=UTC),
        recording_display_timezone_offset_minutes=180,
    )
    legacy = _list_item(title="legacy-no-recording-date", started_at=None)
    uploaded = _list_item(
        source="manual_upload",
        title="manual-upload-with-receipt",
        started_at=None,
        uploaded_at=datetime(2026, 6, 26, 21, 30, tzinfo=UTC),
    )

    assert view_models.meeting_time_label(recorded, time_basis="meeting") == "26 июн, 23:30"
    assert view_models.meeting_time_label(timezone_shifted, time_basis="meeting") == "27 июн, 02:30"
    assert view_models.meeting_time_label(offset_shifted, time_basis="meeting") == "27 июн, 00:30"
    assert view_models.meeting_time_label(legacy, time_basis="meeting") == "Без даты"
    assert (
        view_models.meeting_time_label(uploaded, time_basis="meeting") == "Загружено 26 июн, 21:30"
    )
    assert view_models.date_label(uploaded) == "Загружено 26 июн, 21:30"
    assert view_models.date_label(legacy) == "Без даты"
    assert view_models.meeting_time_label(recorded, time_basis="upload") == "Без даты"


def test_meeting_list_time_label_is_shared_with_visible_search_projection() -> None:
    value = datetime(2026, 7, 13, 23, 30, tzinfo=UTC)

    assert (
        view_models.meeting_list_time_label(
            value,
            timezone_offset_minutes=180,
            time_basis="meeting",
        )
        == "14 июл, 02:30"
    )
    assert (
        view_models.meeting_list_time_label(
            value,
            timezone_offset_minutes=180,
            time_basis="updated",
        )
        == "Обновлено 14 июл, 02:30"
    )


def test_safe_title_uses_legacy_local_recording_fallback_without_control_characters() -> None:
    meeting = _meeting()
    meeting.title = "\x00"
    meeting.local_recording_id = "legacy-no-title"

    assert view_models.safe_title(meeting) == "Запись 16 июн, 08:00"


def test_safe_title_suppresses_legacy_url_or_email_title() -> None:
    meeting = _meeting()
    meeting.title = "https://meet.example.com/private john@example.com"
    meeting.local_recording_id = "legacy-unsafe-title"

    assert view_models.safe_title(meeting) == "Запись 16 июн, 08:00"


def test_safe_title_suppresses_legacy_bare_meeting_link_title() -> None:
    meeting = _meeting()
    meeting.title = "meet.example.test/abc-defg-hij"
    meeting.local_recording_id = "legacy-bare-link-title"

    assert view_models.safe_title(meeting) == "Запись 16 июн, 08:00"


def test_safe_title_suppresses_unsafe_fallback_identity() -> None:
    meeting = _meeting()
    meeting.title = "meet.example.test/abc-defg-hij"
    meeting.local_recording_id = "john@example.com"

    assert view_models.safe_title(meeting) == "Запись 16 июн, 08:00"


def test_safe_title_does_not_suppress_normal_words_that_contain_sk_dash() -> None:
    meeting = _meeting()
    meeting.title = "Risk-review"

    assert view_models.safe_title(meeting) == "Risk-review"


def test_safe_title_keeps_only_the_file_name_when_legacy_title_contains_a_path() -> None:
    unix_path = _meeting()
    unix_path.title = "/Users/example/private/Team_sync.mp3"
    windows_path = _meeting()
    windows_path.title = r"C:\\Users\\example\\private\\Team_sync.mp3"

    assert view_models.safe_title(unix_path) == "Team sync"
    assert view_models.safe_title(windows_path) == "Team sync"


def test_safe_title_preserves_the_legacy_serialized_extension_contract() -> None:
    for extension in LEGACY_SERIALIZED_MEDIA_FILENAME_EXTENSIONS:
        meeting = _meeting()
        meeting.title = f"Team_sync.{extension}"

        assert view_models.safe_title(meeting) == "Team sync"


def test_safe_title_scrubs_paths_without_expanding_serialized_extension_cleanup() -> None:
    for extension in SUPPORTED_MEDIA_FILENAME_EXTENSIONS:
        meeting = _meeting()
        meeting.title = f"/Users/example/private/Team_sync.{extension}"

        expected = (
            "Team sync"
            if extension in LEGACY_SERIALIZED_MEDIA_FILENAME_EXTENSIONS
            else f"Team_sync.{extension}"
        )
        assert view_models.safe_title(meeting) == expected


def test_meeting_list_title_cleans_every_supported_media_extension() -> None:
    for extension in SUPPORTED_MEDIA_FILENAME_EXTENSIONS:
        meeting = _meeting()
        meeting.title = f"/Users/example/private/Team_sync.{extension}"

        assert view_models.meeting_list_title(meeting) == "Team sync"


def test_meeting_list_presentation_humanizes_generated_titles_files_and_durations() -> None:
    generated = _meeting()
    generated.title = "Current display system audio - 2026-07-13 12:14"
    generated.started_at = datetime(2026, 7, 13, 9, 14, tzinfo=UTC)
    generated.recording_display_timezone_offset_minutes = 180

    generated_without_time = _meeting()
    generated_without_time.title = "Yandex Telemost - 2026-07-10 13:00"
    generated_without_time.started_at = None

    manual = _meeting()
    manual.title = "manual-upload-mrc4escf-hbo5nhsk"
    manual.started_at = None

    file_title = _meeting()
    file_title.title = "4p_12_01 PM - Встреча с Технониколь_Инфобез.mp3"

    assert view_models.safe_title(generated) == "Запись 13 июл, 12:14"
    assert view_models.safe_title(generated_without_time) == "Запись без названия"
    assert view_models.safe_title(manual, source="manual_upload") == "Загруженная запись"
    assert view_models.safe_title(file_title) == "4p 12 01 PM - Встреча с Технониколь Инфобез"
    assert view_models.format_duration(27) == "27 с"
    assert view_models.format_duration(14 * 60) == "14 мин"
    assert view_models.format_duration(74 * 60) == "1 ч 14 мин"


def test_safe_title_preserves_authoritative_calendar_user_and_upload_titles() -> None:
    calendar = _meeting()
    calendar.title = "Meeting - 2026-07-13 12:14"
    calendar.title_source = "calendar"

    user = _meeting()
    user.title = "Roadmap.mp3"
    user.title_source = "user_confirmed"

    upload = _meeting()
    upload.title = "Quarterly_sync.mp3"
    upload.title_source = "upload_provided"

    derived = _meeting()
    derived.title = "Quarterly_sync.mp3"
    derived.title_source = "file_name_derived"

    assert view_models.safe_title(calendar) == "Meeting - 2026-07-13 12:14 — 16 июн, 08:00"
    assert view_models.safe_title(user) == "Roadmap.mp3"
    assert view_models.safe_title(upload) == "Quarterly_sync.mp3"
    assert view_models.safe_title(derived) == "Quarterly sync"


def test_safe_title_removes_local_path_from_authoritative_title_without_rewriting_name() -> None:
    meeting = _meeting()
    meeting.title = "/Users/example/private/Roadmap.mp3"
    meeting.title_source = "user_confirmed"

    assert view_models.safe_title(meeting) == "Roadmap.mp3"


def test_list_status_labels_are_user_results_not_pipeline_terms() -> None:
    assert view_models.STATUS_LABELS == {
        "local_only": "Сохранено на Mac",
        "uploading": "Отправляем",
        "submitted": "Обрабатывается",
        "processing": "Обрабатывается",
        "ready": "Готово",
        "partial": "Готово с замечаниями",
        "blocked": "Нужна помощь",
        "failed": "Нужна помощь",
        "unavailable": "Нужна помощь",
        "deleted_future": "Удаляется",
    }


def test_status_mapping_handles_ready_partial_processing_and_failed() -> None:
    ready = ProcessingResult(
        id=uuid4(),
        meeting_id=uuid4(),
        workspace_id=uuid4(),
        mediascribe_job_id=uuid4(),
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        diarization_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        segment_count=1,
        diarization_segment_count=1,
    )
    partial = ProcessingResult(
        id=uuid4(),
        meeting_id=uuid4(),
        workspace_id=uuid4(),
        mediascribe_job_id=uuid4(),
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        diarization_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
        segment_count=1,
        diarization_segment_count=0,
    )
    ready_meeting = _meeting()
    ready_revision, ready_workflow = _lineaged_context(ready_meeting, ready)
    partial_meeting = _meeting()
    partial_revision, partial_workflow = _lineaged_context(partial_meeting, partial)

    assert view_models.review_status(
        ready_meeting,
        result=ready,
        workflow=ready_workflow,
        media_revision_id=ready_revision.id,
    ) == "ready"
    assert view_models.review_status(
        partial_meeting,
        result=partial,
        workflow=partial_workflow,
        media_revision_id=partial_revision.id,
    ) == "partial"
    assert (
        view_models.review_status(_meeting(ProcessingStatus.POLLING), result=None, workflow=None)
        == "processing"
    )
    assert (
        view_models.review_status(
            _meeting(ProcessingStatus.FAILED_TERMINAL), result=None, workflow=None
        )
        == "failed"
    )
    for terminal_status in (MeetingStatus.ABORTED, MeetingStatus.EXPIRED):
        terminal = _meeting(ProcessingStatus.NOT_SUBMITTED)
        terminal.status = terminal_status.value
        assert view_models.review_status(terminal, result=None, workflow=None) == "submitted"
        item = view_models.build_list_item(terminal, result=None, workflow=None)
        assert item.status == "submitted"
        assert item.model_dump()["status"] == "submitted"
        assert view_models.meeting_list_presentation_status(item) == "failed"


def test_watchdog_status_is_consistent_in_meeting_list_projection() -> None:
    meeting = _meeting(ProcessingStatus.FAILED_RETRYABLE)
    workflow = ProcessingWorkflow(
        id=uuid4(),
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        workflow_id="processing/watchdog",
        purpose="transcription",
        status=ProcessingStatus.FAILED_RETRYABLE.value,
        retry_class="retryable",
        last_reason_code="processing_retry_deadline_exceeded",
    )

    item = view_models.build_list_item(meeting, result=None, workflow=workflow)
    row = view_models.meeting_list_row_presentation(item, time_basis="meeting")

    assert item.status == "processing"
    assert item.status_label == "Нужна проверка"
    assert item.status_reason == "processing_retry_deadline_exceeded"
    assert row.content_readiness_label == "Результат ещё не подтверждён · откройте встречу для проверки"


def test_previous_recurring_readiness_keeps_current_lineaged_transcript_ready() -> None:
    meeting = _meeting()
    result = ProcessingResult(
        id=uuid4(),
        meeting_id=meeting.id,
        workspace_id=meeting.workspace_id,
        media_revision_id=uuid4(),
        mediascribe_job_id=uuid4(),
        processing_workflow_id=uuid4(),
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        diarization_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        summary_status="not_requested",
        segment_count=1,
        diarization_segment_count=1,
    )
    assert (
        view_models.previous_recurring_meeting_readiness(
            meeting,
            result=result,
            outcome_set=None,
        ).value
        == "transcript_ready"
    )


def test_processing_reason_copy_covers_terminal_input_outcomes() -> None:
    assert view_models.reason_label("no_recognizable_speech") == (
        "MediaScribe обработал запись, но транскрипт не создан: распознаваемая речь не найдена."
    )
    assert (
        view_models.reason_label("invalid_audio_payload")
        == "Файл записи не является декодируемым аудио или поврежден."
    )


@pytest.mark.parametrize(
    ("failure_reason", "failure_source"),
    [
        ("no_recognizable_speech", None),
        ("invalid_audio_payload", "input_audio"),
    ],
)
def test_terminal_input_result_is_terminal_for_list_and_detail_projections(
    failure_reason: str,
    failure_source: str | None,
) -> None:
    result = ProcessingResult(
        id=uuid4(),
        meeting_id=uuid4(),
        workspace_id=uuid4(),
        mediascribe_job_id=uuid4(),
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
        diarization_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
        segment_count=0,
        diarization_segment_count=0,
        failure_reason=failure_reason,
        failure_source=failure_source,
    )
    meeting = _meeting(ProcessingStatus.POLLING)
    meeting_id = meeting.id
    result.meeting_id = meeting_id
    result.workspace_id = meeting.workspace_id
    media_revision, workflow = _lineaged_context(meeting, result)
    workflow.status = ProcessingStatus.POLLING.value

    assert view_models.review_status(
        meeting,
        result=result,
        workflow=workflow,
        media_revision_id=media_revision.id,
    ) == "failed"
    item = view_models.build_list_item(
        meeting,
        media_revision=media_revision,
        result=result,
        workflow=workflow,
    )
    assert item.status == "failed"
    assert view_models.meeting_list_row_presentation(item, time_basis="meeting").status_label == (
        "Не удалось обработать"
    )


def test_terminal_input_result_cannot_be_promoted_to_partial_by_artifact_rows() -> None:
    meeting = _meeting(ProcessingStatus.PROCESSED)
    result = ProcessingResult(
        id=uuid4(),
        meeting_id=meeting.id,
        workspace_id=meeting.workspace_id,
        media_revision_id=uuid4(),
        processing_workflow_id=uuid4(),
        mediascribe_job_id=uuid4(),
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
        diarization_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        summary_status=SummaryStatus.UNAVAILABLE.value,
        segment_count=0,
        diarization_segment_count=1,
        failure_reason="no_recognizable_speech",
    )
    workflow = ProcessingWorkflow(
        id=result.processing_workflow_id,
        meeting_id=meeting.id,
        workspace_id=meeting.workspace_id,
        media_revision_id=result.media_revision_id,
        workflow_id="processing/terminal-with-rows",
        purpose="transcription",
        status=ProcessingStatus.PROCESSED.value,
    )

    assert view_models.review_status(
        meeting,
        result=result,
        workflow=workflow,
        media_revision_id=result.media_revision_id,
    ) == "failed"


def test_previous_terminal_input_result_does_not_mask_active_attempt() -> None:
    meeting = _meeting(ProcessingStatus.POLLING)
    media_revision_id = uuid4()
    result = ProcessingResult(
        id=uuid4(),
        meeting_id=meeting.id,
        workspace_id=meeting.workspace_id,
        media_revision_id=media_revision_id,
        mediascribe_job_id=uuid4(),
        processing_workflow_id=uuid4(),
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
        diarization_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
        segment_count=0,
        diarization_segment_count=0,
        failure_reason="invalid_audio_payload",
        failure_source="input_audio",
    )
    current = ProcessingWorkflow(
        id=uuid4(),
        meeting_id=meeting.id,
        workspace_id=meeting.workspace_id,
        media_revision_id=media_revision_id,
        workflow_id="processing/current-attempt",
        purpose="transcription",
        status=ProcessingStatus.POLLING.value,
    )

    assert view_models.review_status(
        meeting,
        result=result,
        workflow=current,
        media_revision_id=media_revision_id,
    ) == "processing"
    result.failure_reason = None
    result.failure_source = None
    result.transcript_status = ProcessingAvailabilityStatus.AVAILABLE.value
    result.diarization_status = ProcessingAvailabilityStatus.AVAILABLE.value
    result.segment_count = 1
    result.diarization_segment_count = 1
    assert not view_models.transcript_available(
        result,
        media_revision_id=media_revision_id,
        processing_workflow_id=current.id,
    )
    assert view_models.review_status(
        meeting,
        result=result,
        workflow=current,
        media_revision_id=media_revision_id,
    ) == "processing"


def test_transcript_mapping_uses_timestamp_speaker_and_source_role_truth() -> None:
    meeting = _meeting()
    result_id = uuid4()
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("65.500"),
            end_seconds=Decimal("70.000"),
            text="hello",
            source_role="incoming",
        )
    ]
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("65.500"),
            end_seconds=Decimal("70.000"),
            text="hello",
            speaker_label="Speaker 2",
            source_role="incoming",
        )
    ]

    state = view_models.transcript_state(
        language="ru",
        transcript_segments=transcript,
        diarization_segments=diarization,
        status="ready",
    )

    assert state.available is True
    assert state.segments[0].timestamp_label == "01:05"
    assert state.segments[0].speaker_label == "Спикер не определён"
    assert state.segments[0].source_role == "incoming_system"
    assert state.segments[0].seekable is False
    assert state.segments[0].seek_seconds is None
    assert state.speaker_turns[0].speaker_label == "SPEAKER_00"


def test_transcript_mapping_matches_diarization_by_sequence_and_source_role() -> None:
    meeting = _meeting()
    result_id = uuid4()
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("10.000"),
            text="remote audio",
            source_role="incoming",
        ),
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("10.000"),
            text="local audio",
            source_role="mic",
        ),
    ]
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("10.000"),
            text="local audio",
            speaker_label="MIC",
            source_role="mic",
        ),
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("10.000"),
            text="remote audio",
            speaker_label="REMOTE_00",
            source_role="incoming",
        ),
    ]

    state = view_models.transcript_state(
        language="ru",
        transcript_segments=transcript,
        diarization_segments=diarization,
        status="ready",
    )

    by_source = {segment.source_role: segment.speaker_label for segment in state.speaker_turns}
    assert by_source == {
        "incoming_system": "SPEAKER_01",
        "local_microphone": "SPEAKER_00",
    }


def test_transcript_mapping_uses_diarization_time_when_sequence_conflicts() -> None:
    meeting = _meeting()
    result_id = uuid4()
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("30.000"),
            end_seconds=Decimal("35.000"),
            text="current speaker",
            source_role="incoming",
        )
    ]
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("10.000"),
            text="old speaker",
            speaker_label="OLD_REMOTE",
            source_role="incoming",
        ),
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=1,
            start_seconds=Decimal("29.000"),
            end_seconds=Decimal("40.000"),
            text="current speaker",
            speaker_label="CURRENT_REMOTE",
            source_role="incoming",
        ),
    ]

    state = view_models.transcript_state(
        language="ru",
        transcript_segments=transcript,
        diarization_segments=diarization,
        status="ready",
    )

    assert state.result_state == "degraded_provider_result"
    assert [segment.text for segment in state.segments] == ["current speaker"]
    assert state.segments[0].attribution_state == "uncertain"


def test_dual_track_mapping_canonicalizes_dependency_labels_when_speaker_style_label_is_present() -> (
    None
):
    meeting = _meeting()
    result_id = uuid4()
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("1.000"),
            text="local audio",
            source_role="mic",
        ),
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=1,
            start_seconds=Decimal("1.000"),
            end_seconds=Decimal("2.000"),
            text="remote audio",
            source_role="incoming",
        ),
    ]
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("1.000"),
            text="local audio",
            speaker_label="SPEAKER_00",
            source_role="mic",
        ),
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=1,
            start_seconds=Decimal("1.000"),
            end_seconds=Decimal("2.000"),
            text="remote audio",
            speaker_label="REMOTE_00",
            source_role="incoming",
        ),
    ]

    transcript_state = view_models.transcript_state(
        language="ru",
        transcript_segments=transcript,
        diarization_segments=diarization,
        status="ready",
    )
    speaker_state = view_models.speaker_state(diarization, transcript_segments=transcript)

    assert [segment.speaker_label for segment in transcript_state.speaker_turns] == [
        "SPEAKER_00",
        "SPEAKER_01",
    ]
    assert {speaker.label for speaker in speaker_state.speakers} == {"SPEAKER_00", "SPEAKER_01"}


def test_manual_upload_transcript_uses_diarization_rows_for_speaker_labels() -> None:
    meeting = _meeting()
    result_id = uuid4()
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.500"),
            end_seconds=Decimal("4.500"),
            text="speaker zero",
            source_role="incoming",
        ),
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=1,
            start_seconds=Decimal("5.500"),
            end_seconds=Decimal("9.500"),
            text="speaker one",
            source_role="incoming",
        ),
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=2,
            start_seconds=Decimal("10.500"),
            end_seconds=Decimal("12.000"),
            text="unknown dependency label",
            source_role="incoming",
        ),
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=3,
            start_seconds=Decimal("15.500"),
            end_seconds=Decimal("19.500"),
            text="speaker two sequence mismatch",
            source_role="incoming",
        ),
    ]
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("5.000"),
            text="speaker zero",
            speaker_label="SPEAKER_00",
            source_role="incoming",
        ),
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=1,
            start_seconds=Decimal("5.000"),
            end_seconds=Decimal("10.000"),
            text="speaker one",
            speaker_label="SPEAKER_01",
            source_role="incoming",
        ),
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=2,
            start_seconds=Decimal("10.000"),
            end_seconds=Decimal("13.000"),
            text="unknown dependency label",
            speaker_label="UNKNOWN",
            source_role="incoming",
        ),
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=99,
            start_seconds=Decimal("14.000"),
            end_seconds=Decimal("22.000"),
            text="speaker two",
            speaker_label=" SPEAKER_02 ",
            source_role="incoming",
        ),
    ]

    state = view_models.transcript_state(
        language="ru",
        transcript_segments=transcript,
        diarization_segments=diarization,
        status="ready",
    )

    assert state.result_state == "degraded_provider_result"
    assert {segment.speaker_label for segment in state.segments} == {"Спикер не определён"}
    assert [segment.text for segment in state.segments] == [
        "speaker zero",
        "speaker one",
        "unknown dependency label",
        "speaker two sequence mismatch",
    ]
    assert "Incoming system" not in {segment.speaker_label for segment in state.segments}
    assert {segment.attribution_state for segment in state.segments} == {"uncertain"}


def test_manual_upload_transcript_keeps_unknown_when_diarization_is_missing() -> None:
    meeting = _meeting()
    result_id = uuid4()
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("10.000"),
            text="single track text",
            source_role="incoming",
        ),
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=1,
            start_seconds=Decimal("11.000"),
            end_seconds=Decimal("20.000"),
            text="single track text",
            source_role="incoming",
        ),
    ]

    state = view_models.transcript_state(
        language="ru",
        transcript_segments=transcript,
        diarization_segments=[],
        status="ready",
    )

    assert state.available is False
    assert state.degraded_reason == "diarization_pending"
    assert state.segments == []


def test_manual_upload_review_response_preserves_unknown_without_diarization() -> None:
    meeting = _meeting()
    result_id = uuid4()
    result = ProcessingResult(
        id=result_id,
        meeting_id=meeting.id,
        media_revision_id=uuid4(),
        workspace_id=meeting.workspace_id,
        mediascribe_job_id=uuid4(),
        processing_workflow_id=uuid4(),
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        diarization_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
        segment_count=1,
        diarization_segment_count=0,
    )
    media_revision = MediaRevision(
        id=result.media_revision_id,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        local_media_revision_id="manual-review-speaker-labels",
        revision_number=1,
        source_kind=MediaRevisionSourceKind.MANUAL_UPLOAD.value,
        status="accepted",
    )
    workflow = ProcessingWorkflow(
        id=result.processing_workflow_id,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        media_revision_id=result.media_revision_id,
        workflow_id="processing/manual-review-diarization-source",
        purpose="transcription",
        status=ProcessingStatus.PROCESSED.value,
    )
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("10.000"),
            text="single track text",
            source_role="incoming",
        )
    ]

    response = view_models.build_review_response(
        meeting,
        media_revision=media_revision,
        result=result,
        workflow=workflow,
        transcript_segments=transcript,
        diarization_segments=[],
        dependency=None,
    )

    assert response.meeting.source == "manual_upload"
    assert response.transcript.available is False
    assert response.transcript.segments == []
    assert response.processing.transcript_available is False


def test_manual_upload_review_response_uses_diarization_as_transcript_source() -> None:
    meeting = _meeting()
    result_id = uuid4()
    result = ProcessingResult(
        id=result_id,
        meeting_id=meeting.id,
        media_revision_id=uuid4(),
        workspace_id=meeting.workspace_id,
        mediascribe_job_id=uuid4(),
        processing_workflow_id=uuid4(),
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        diarization_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        segment_count=1,
        diarization_segment_count=1,
    )
    media_revision = MediaRevision(
        id=result.media_revision_id,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        local_media_revision_id="manual-review-diarization-source",
        revision_number=1,
        source_kind=MediaRevisionSourceKind.MANUAL_UPLOAD.value,
        status="accepted",
    )
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("40.000"),
            end_seconds=Decimal("45.000"),
            text="transcript row should not be used",
            source_role="incoming",
        )
    ]
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("5.000"),
            text="diarization row is the review source",
            speaker_label="SPEAKER_01",
            source_role="incoming",
        )
    ]
    workflow = ProcessingWorkflow(
        id=result.processing_workflow_id,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        media_revision_id=result.media_revision_id,
        workflow_id="processing/manual-review-diarization-source",
        purpose="transcription",
        status=ProcessingStatus.PROCESSED.value,
    )

    response = view_models.build_review_response(
        meeting,
        media_revision=media_revision,
        result=result,
        workflow=workflow,
        transcript_segments=transcript,
        diarization_segments=diarization,
        dependency=None,
    )

    assert [segment.text for segment in response.transcript.segments] == [
        "transcript row should not be used"
    ]
    assert response.transcript.result_state == "degraded_provider_result"
    assert response.transcript.segments[0].attribution_state == "uncertain"


def test_normal_recording_and_manual_upload_share_canonical_speaker_projection() -> None:
    meeting = _meeting()
    result_id = uuid4()
    media_revision_id = uuid4()
    result = ProcessingResult(
        id=result_id,
        meeting_id=meeting.id,
        media_revision_id=media_revision_id,
        workspace_id=meeting.workspace_id,
        mediascribe_job_id=uuid4(),
        processing_workflow_id=uuid4(),
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        diarization_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        segment_count=1,
        diarization_segment_count=2,
    )
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("2.000"),
            text="alpha beta",
            source_role="mixed",
        )
    ]
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("1.000"),
            text="alpha",
            speaker_label="raw-a",
            source_role="mixed",
        ),
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=1,
            start_seconds=Decimal("1.000"),
            end_seconds=Decimal("2.000"),
            text="beta",
            speaker_label="raw-b",
            source_role="mixed",
        ),
    ]
    workflow = ProcessingWorkflow(
        id=result.processing_workflow_id,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        media_revision_id=media_revision_id,
        workflow_id="processing/canonical-speaker-projection",
        purpose="transcription",
        status=ProcessingStatus.PROCESSED.value,
    )

    def response_for(source_kind: str):
        return view_models.build_review_response(
            meeting,
            media_revision=MediaRevision(
                id=media_revision_id,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                local_media_revision_id=f"synthetic-{source_kind}",
                revision_number=1,
                source_kind=source_kind,
                status="accepted",
            ),
            result=result,
            workflow=workflow,
            transcript_segments=transcript,
            diarization_segments=diarization,
            dependency=None,
        )

    normal = response_for(MediaRevisionSourceKind.INITIAL_MIXED_RECORDING.value)
    manual = response_for(MediaRevisionSourceKind.MANUAL_UPLOAD.value)
    canonical_fields = {
        "start_seconds",
        "end_seconds",
        "speaker_key",
        "provider_speaker_key",
        "text",
        "attribution_state",
        "result_state",
    }

    assert normal.meeting.source == "desktop_recording"
    assert manual.meeting.source == "manual_upload"
    assert [
        turn.model_dump(include=canonical_fields) for turn in normal.transcript.speaker_turns
    ] == [turn.model_dump(include=canonical_fields) for turn in manual.transcript.speaker_turns]
    assert [turn.model_dump(include=canonical_fields) for turn in normal.speakers.turns] == [
        turn.model_dump(include=canonical_fields) for turn in normal.transcript.speaker_turns
    ]
    assert normal.speakers == manual.speakers


def test_valid_projection_ignores_historical_false_degraded_failure_reason() -> None:
    meeting = _meeting()
    result_id = uuid4()
    result = ProcessingResult(
        id=result_id,
        meeting_id=meeting.id,
        media_revision_id=uuid4(),
        workspace_id=meeting.workspace_id,
        mediascribe_job_id=uuid4(),
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        diarization_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        segment_count=1,
        diarization_segment_count=1,
        failure_reason="degraded_provider_result",
        failure_source="mediascribe",
    )
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("1.000"),
            text="alpha",
            source_role="mixed",
        )
    ]
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("1.000"),
            text="alpha",
            speaker_label="raw-a",
            source_role="mixed",
        )
    ]
    media_revision, workflow = _lineaged_context(meeting, result)

    response = view_models.build_review_response(
        meeting,
        media_revision=media_revision,
        result=result,
        workflow=workflow,
        transcript_segments=transcript,
        diarization_segments=diarization,
        dependency=None,
    )

    assert response.meeting.status == "ready"
    assert response.processing.reason_code is None
    assert response.transcript.result_state == "accepted"
    assert response.speakers.result_state == "accepted"


def test_manual_upload_transcript_falls_back_to_transcript_text_when_diarization_text_is_blank() -> (
    None
):
    meeting = _meeting()
    result_id = uuid4()
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("4.000"),
            text="first transcript row",
            source_role="incoming",
        ),
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=1,
            start_seconds=Decimal("10.000"),
            end_seconds=Decimal("14.000"),
            text="second transcript row",
            source_role="incoming",
        ),
    ]
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("5.000"),
            text="",
            speaker_label="SPEAKER_00",
            source_role="incoming",
        ),
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=1,
            start_seconds=Decimal("9.000"),
            end_seconds=Decimal("15.000"),
            text=" ",
            speaker_label="SPEAKER_01",
            source_role="incoming",
        ),
    ]

    state = view_models.transcript_state(
        language="ru",
        transcript_segments=transcript,
        diarization_segments=diarization,
        status="ready",
    )

    assert [segment.text for segment in state.segments] == [
        "first transcript row",
        "second transcript row",
    ]
    assert {segment.speaker_label for segment in state.segments} == {"Спикер не определён"}
    assert state.result_state == "degraded_provider_result"
    assert all(segment.text.strip() for segment in state.segments)


def test_manual_upload_transcript_omits_blank_diarization_display_rows() -> None:
    meeting = _meeting()
    result_id = uuid4()
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("5.000"),
            text="",
            speaker_label="SPEAKER_00",
            source_role="incoming",
        ),
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=1,
            start_seconds=Decimal("1.000"),
            end_seconds=Decimal("4.000"),
            text="speaker zero text",
            speaker_label="UNKNOWN",
            source_role="incoming",
        ),
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=2,
            start_seconds=Decimal("5.000"),
            end_seconds=Decimal("9.000"),
            text="speaker one text",
            speaker_label="SPEAKER_01",
            source_role="incoming",
        ),
    ]

    state = view_models.transcript_state(
        language="ru",
        transcript_segments=_transcript_evidence(diarization),
        diarization_segments=diarization,
        status="ready",
    )

    assert [segment.text for segment in state.segments] == [
        "",
        "speaker zero text",
        "speaker one text",
    ]
    assert [segment.text for segment in state.speaker_turns] == [
        "speaker zero text",
        "speaker one text",
    ]
    assert [segment.speaker_label for segment in state.speaker_turns] == [
        "Спикер не определён",
        "SPEAKER_00",
    ]
    assert all(segment.text.strip() for segment in state.speaker_turns)


def test_transcript_mapping_marks_valid_segments_seekable_when_playback_available() -> None:
    meeting = _meeting()
    result_id = uuid4()
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("0.000"),
            end_seconds=Decimal("10.000"),
            text="local audio",
            source_role="mic",
        ),
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=1,
            start_seconds=Decimal("12.500"),
            end_seconds=Decimal("20.000"),
            text="remote audio",
            source_role="incoming",
        ),
    ]

    state = view_models.transcript_state(
        language="ru",
        transcript_segments=transcript,
        diarization_segments=[],
        status="ready",
        playback_available=True,
        playback_duration_seconds=30,
    )

    assert state.available is False
    assert state.degraded_reason == "diarization_pending"
    assert state.segments == []


def test_speaker_mapping_calculates_talk_time_percentages() -> None:
    result_id = uuid4()
    meeting_id = uuid4()
    workspace_id = uuid4()
    segments = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            sequence=0,
            start_seconds=Decimal(0),
            end_seconds=Decimal(30),
            text="one",
            speaker_label="Speaker 1",
            source_role="mic",
        ),
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            sequence=1,
            start_seconds=Decimal(30),
            end_seconds=Decimal(60),
            text="two",
            speaker_label="Speaker 2",
            source_role="incoming",
        ),
    ]

    state = view_models.speaker_state(
        segments,
        transcript_segments=_transcript_evidence(segments),
    )

    assert state.available is True
    assert [(speaker.label, speaker.talk_time_percent) for speaker in state.speakers] == [
        ("SPEAKER_00", 50),
        ("SPEAKER_01", 50),
    ]


def test_manual_upload_speaker_mapping_hides_unknown_when_speaker_labels_are_present() -> None:
    result_id = uuid4()
    meeting_id = uuid4()
    workspace_id = uuid4()
    segments = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            sequence=0,
            start_seconds=Decimal(0),
            end_seconds=Decimal(10),
            text="one",
            speaker_label="SPEAKER_00",
            source_role="incoming",
        ),
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            sequence=1,
            start_seconds=Decimal(11),
            end_seconds=Decimal(12),
            text="unknown",
            speaker_label="UNKNOWN",
            source_role="incoming",
        ),
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            sequence=2,
            start_seconds=Decimal(20),
            end_seconds=Decimal(30),
            text="two",
            speaker_label="SPEAKER_01",
            source_role="incoming",
        ),
    ]

    state = view_models.speaker_state(
        segments,
        transcript_segments=_transcript_evidence(segments),
    )

    assert {speaker.label for speaker in state.speakers} == {
        "SPEAKER_00",
        "SPEAKER_01",
        "Спикер не определён",
    }
    assert sum(speaker.confirmed for speaker in state.speakers) == 2


def test_manual_upload_speaker_mapping_preserves_unknown_rows() -> None:
    result_id = uuid4()
    meeting_id = uuid4()
    workspace_id = uuid4()
    segments = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            sequence=0,
            start_seconds=Decimal(0),
            end_seconds=Decimal(10),
            text="unknown dependency label",
            speaker_label="UNKNOWN",
            source_role="incoming",
        )
    ]

    state = view_models.speaker_state(
        segments,
        transcript_segments=_transcript_evidence(segments),
    )

    assert [speaker.label for speaker in state.speakers] == ["Спикер не определён"]
    assert state.speakers[0].confirmed is False
    assert state.speakers[0].can_rename is False


def test_calendar_roster_does_not_rename_transcript_speakers_or_grant_access() -> None:
    roster = normalize_calendar_participants(
        [
            {
                "participant_kind": "required_attendee",
                "email": "speaker@example.test",
                "display_name": "Calendar Name",
            }
        ]
    )
    result_id = uuid4()
    meeting = _meeting()
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal(0),
            end_seconds=Decimal(10),
            text="hello",
            speaker_label="Speaker 1",
            source_role="mic",
        )
    ]

    state = view_models.speaker_state(
        diarization,
        transcript_segments=_transcript_evidence(diarization),
    )

    assert roster[0]["display_name"] == "Calendar Name"
    assert state.speakers[0].label == "SPEAKER_00"
    assert "access_grant" not in roster[0]
    assert "share_grant" not in roster[0]


def test_098_list_and_review_models_receive_the_same_safe_calendar_summary() -> None:
    # FR-033/FR-048: list and review share state while using their contracted copy.
    expected_list_summary = MeetingCalendarContextSummary(
        state="matched_auto",
        label="Из календаря",
        title_source="calendar",
        needs_owner_action=False,
    )
    expected_review_summary = expected_list_summary.model_copy(
        update={"label": "Подобрано автоматически"}
    )
    meeting = _meeting()
    meeting.title_source = "calendar"
    link = _calendar_context_link(context_state="matched_auto")

    item = view_models.build_list_item(
        meeting,
        result=None,
        workflow=None,
        calendar_context=link,
    )
    review = view_models.build_review_response(
        meeting,
        result=None,
        workflow=None,
        transcript_segments=[],
        diarization_segments=[],
        dependency=None,
        calendar_context=link,
    )

    assert item.calendar_context == expected_list_summary
    assert review.meeting.calendar_context == expected_list_summary
    assert review.calendar_context == expected_review_summary
    assert review.calendar_context.label == "Подобрано автоматически"


def test_098_auto_context_summary_and_roster_use_only_immutable_safe_link_snapshots() -> None:
    # FR-016/FR-020/FR-030: query projection never needs mutable provider rows.
    link = _calendar_context_link(
        context_state="matched_auto",
        matched_title="Synthetic Immutable Planning",
        matched_roster_json=[
            {
                "participant_kind": "organizer",
                "response_status": "organizer",
                "display_name": "Synthetic Immutable Owner",
                "email": "must-not-project@example.test",
                "email_present": True,
                "workspace_relation": "owner",
                "recipient_candidate_class": "organizer",
            }
        ],
        matched_roster_state="available",
        matched_roster_count=1,
    )

    summary = view_models.calendar_context_summary(link, meeting_title_source="calendar")
    roster = view_models.calendar_roster_snapshot_state(link)

    assert summary == MeetingCalendarContextSummary(
        state="matched_auto",
        label="Из календаря",
        title_source="calendar",
        needs_owner_action=False,
    )
    assert roster is not None
    assert roster.available is True
    assert roster.participant_count == 1
    assert roster.participants[0].display_name == "Synthetic Immutable Owner"
    assert roster.participants[0].email_present is True
    assert "must-not-project@example.test" not in roster.model_dump_json()
    assert 'email"' not in roster.model_dump_json()


def test_098_calendar_roster_snapshot_hides_email_like_display_name() -> None:
    # FR-030/SC-011: cabinet egress rechecks immutable snapshots fail closed.
    link = _calendar_context_link(
        context_state="matched_auto",
        matched_roster_json=[
            {
                "participant_kind": "required_attendee",
                "response_status": "accepted",
                "display_name": "person@example.test",
                "email_present": True,
                "workspace_relation": "external",
                "recipient_candidate_class": "external_attendee",
            }
        ],
        matched_roster_state="available",
        matched_roster_count=1,
    )

    roster = view_models.calendar_roster_snapshot_state(link)

    assert roster is not None
    assert roster.participants[0].display_name is None
    assert "person@example.test" not in roster.model_dump_json()


def test_098_private_and_no_context_states_ignore_stale_title_and_roster_payloads() -> None:
    # FR-009/FR-033/FR-037: protected/no-context state cannot leak stale snapshots.
    for state in ("skipped_private", "no_context"):
        link = _calendar_context_link(
            context_state=state,
            matched_title="Synthetic Hidden Calendar Title",
            matched_roster_json=[
                {
                    "participant_kind": "required_attendee",
                    "response_status": "accepted",
                    "display_name": "Synthetic Hidden Participant",
                    "email": "hidden-person@example.test",
                }
            ],
            matched_roster_state="available",
            matched_roster_count=1,
        )

        summary = view_models.calendar_context_summary(link, meeting_title_source="generic")
        roster = view_models.calendar_roster_snapshot_state(link)

        assert summary is not None
        assert summary.state == state
        assert "Synthetic Hidden" not in summary.model_dump_json()
        assert "hidden-person@example.test" not in summary.model_dump_json()
        assert roster is None


def test_098_private_skip_reason_is_owner_detail_only() -> None:
    # FR-010/FR-033/FR-042: list/non-owner truth is generic; owner detail is safe.
    link = _calendar_context_link(
        context_state="skipped_private",
        safe_reason_code="private_free_busy_skipped",
    )

    generic = view_models.calendar_context_summary(
        link,
        meeting_title_source="generic",
    )
    owner = view_models.calendar_context_summary(
        link,
        meeting_title_source="generic",
        owner_detail=True,
    )

    assert generic is not None
    assert owner is not None
    assert generic.label == owner.label == "Без контекста календаря"
    assert generic.reason_label is None
    assert owner.reason_label == "Приватное событие пропущено"

    meeting = _meeting()
    owner_review = view_models.build_review_response(
        meeting,
        result=None,
        workflow=None,
        transcript_segments=[],
        diarization_segments=[],
        dependency=None,
        access=_owner_access(),
        calendar_context=link,
    )
    team_review = view_models.build_review_response(
        meeting,
        result=None,
        workflow=None,
        transcript_segments=[],
        diarization_segments=[],
        dependency=None,
        access=_owner_access().model_copy(update={"state": "team"}),
        calendar_context=link,
    )

    assert owner_review.calendar_context is not None
    assert owner_review.meeting.calendar_context is not None
    assert team_review.calendar_context is not None
    assert owner_review.calendar_context.reason_label == "Приватное событие пропущено"
    assert owner_review.meeting.calendar_context.reason_label is None
    assert team_review.calendar_context.reason_label is None


def test_098_owner_no_context_reasons_use_bounded_product_copy() -> None:
    # FR-033/FR-042: owner detail explains safe outcomes without provider/internal text.
    expected_labels = {
        "all_day_skipped": "Событие на весь день пропущено",
        "selected_source_stale": "Данные календаря устарели",
        "latest_sync_failed": "Данные календаря устарели",
        "calendar_unavailable": "Календарь недоступен",
        "manual_upload_skipped": "Ручная загрузка не сопоставляется",
        "offline_or_unknown_skipped": "Офлайн-запись не сопоставляется",
        "no_matching_event": "Подходящая встреча не найдена",
        "prestart_not_reached": "Запись завершилась до начала встречи",
        "user_declined": "Вы начали запись без календарного контекста",
        "user_cleared": "Контекст убран вами",
    }

    for reason_code, expected_label in expected_labels.items():
        summary = view_models.calendar_context_summary(
            _calendar_context_link(
                context_state="no_context",
                safe_reason_code=reason_code,
            ),
            meeting_title_source="generic",
            owner_detail=True,
        )

        assert summary is not None
        assert summary.reason_label == expected_label
        assert reason_code not in summary.model_dump_json()


def test_us6_calendar_roster_stays_metadata_and_speaker_labels_stay_canonical() -> None:
    # T084; FR-020/FR-022; SC-008 (speaker-assignment slice): roster names stay separate.
    link = _calendar_context_link(
        context_state="matched_auto",
        matched_roster_json=[
            {
                "participant_kind": "required_attendee",
                "response_status": "accepted",
                "display_name": "Synthetic Calendar Person A",
                "email_present": True,
                "workspace_relation": "external",
                "recipient_candidate_class": "external_attendee",
            },
            {
                "participant_kind": "optional_attendee",
                "response_status": "tentative",
                "display_name": "Synthetic Calendar Person B",
                "email_present": True,
                "workspace_relation": "external",
                "recipient_candidate_class": "optional_attendee",
            },
        ],
        matched_roster_state="available",
        matched_roster_count=2,
    )
    roster = view_models.calendar_roster_snapshot_state(link)
    meeting = _meeting()
    result_id = uuid4()
    result = ProcessingResult(
        id=result_id,
        meeting_id=meeting.id,
        workspace_id=meeting.workspace_id,
        mediascribe_job_id=uuid4(),
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        diarization_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        segment_count=2,
        diarization_segment_count=2,
    )
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=index,
            start_seconds=Decimal(index * 10),
            end_seconds=Decimal(index * 10 + 10),
            text=f"synthetic transcript segment {index}",
            source_role="incoming",
        )
        for index in range(2)
    ]
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=index,
            start_seconds=Decimal(index * 10),
            end_seconds=Decimal(index * 10 + 10),
            text=f"synthetic transcript segment {index}",
            speaker_label=f"Synthetic Calendar Person {chr(ord('A') + index)}",
            source_role="incoming",
        )
        for index in range(2)
    ]
    media_revision, workflow = _lineaged_context(meeting, result)

    review = view_models.build_review_response(
        meeting,
        media_revision=media_revision,
        result=result,
        workflow=workflow,
        transcript_segments=transcript,
        diarization_segments=diarization,
        dependency=None,
        access=_owner_access(),
        calendar_roster=roster,
    )

    assert review.calendar_roster is not None
    assert review.calendar_roster.source == "calendar"
    assert [participant.display_name for participant in review.calendar_roster.participants] == [
        "Synthetic Calendar Person A",
        "Synthetic Calendar Person B",
    ]
    assert [segment.speaker_label for segment in review.transcript.speaker_turns] == [
        "SPEAKER_00",
        "SPEAKER_01",
    ]
    assert [speaker.label for speaker in review.speakers.speakers] == [
        "SPEAKER_00",
        "SPEAKER_01",
    ]
    assert review.access is not None
    assert review.access.state == "owner"
    assert review.access.can_view is True
    assert "speaker_label" not in review.calendar_roster.model_dump_json()
    assert "access_grant" not in review.calendar_roster.model_dump_json()
    assert "share_grant" not in review.calendar_roster.model_dump_json()


def _calendar_context_link(
    *,
    context_state: str,
    matched_title: str | None = None,
    matched_roster_json: list[dict] | None = None,
    matched_roster_state: str = "not_available",
    matched_roster_count: int = 0,
    safe_reason_code: str | None = None,
) -> RecordingCalendarContextLink:
    return RecordingCalendarContextLink(
        id=uuid4(),
        workspace_id=uuid4(),
        meeting_id=uuid4(),
        calendar_event_snapshot_id=None,
        context_state=context_state,
        context_confidence="high" if context_state == "matched_auto" else "none",
        context_reasons_json=[],
        title_source="calendar" if context_state == "matched_auto" else "generic",
        roster_source="calendar" if matched_roster_count else "none",
        manual_override_state="none",
        safe_reason_code=safe_reason_code
        or ("single_fresh_candidate" if context_state == "matched_auto" else "no_matching_event"),
        decision_source="automatic",
        matcher_version="calendar_auto_match_v1",
        evaluated_at=datetime(2026, 7, 13, 9, 0, tzinfo=UTC),
        candidate_event_ids_json=[],
        candidate_count=0,
        matched_title=matched_title,
        matched_title_state="available" if matched_title else "unavailable",
        matched_roster_json=matched_roster_json or [],
        matched_roster_state=matched_roster_state,
        matched_roster_count=matched_roster_count,
    )


def test_governance_states_are_non_mutating_and_truthful() -> None:
    governance = view_models.governance_summary()

    assert governance.share.state == "available"
    assert governance.export.state == "disabled"
    assert governance.download.state == "disabled"
    assert governance.retention.state == "planned"
    assert governance.delete.destructive is True
    assert governance.delete.label == "Удалить встречу…"
    assert "GRAF" in governance.delete.reason


def test_processing_state_uses_safe_reason_and_next_action() -> None:
    meeting = _meeting(ProcessingStatus.FAILED_TERMINAL)
    workflow = ProcessingWorkflow(
        id=uuid4(),
        meeting_id=meeting.id,
        workspace_id=meeting.workspace_id,
        workflow_id="private-workflow",
        status=ProcessingStatus.FAILED_TERMINAL.value,
        last_reason_code="mediascribe_validation_failed",
    )

    state = view_models.processing_state(meeting, result=None, workflow=workflow)

    assert state.state == "failed"
    assert state.reason_code == "mediascribe_validation_failed"
    assert state.next_action == "contact_operator"
    assert "private-workflow" not in state.model_dump_json()


def test_processing_failure_copy_covers_retryable_and_terminal_provider_reasons() -> None:
    assert "Повтор" in view_models.reason_label("mediascribe_timeout")
    assert (
        view_models.next_action_for_status("failed", reason_code="mediascribe_rate_limited")
        == "retry_future"
    )
    assert "некорректный ответ" in view_models.reason_label("mediascribe_malformed_response")
    assert (
        view_models.next_action_for_status("failed", reason_code="mediascribe_malformed_response")
        == "contact_operator"
    )


def test_transcript_state_derives_same_speaker_turns_and_preserves_raw_segments() -> None:
    meeting = _meeting()
    result_id = uuid4()
    segment_ids = [uuid4() for _ in range(4)]
    spans = [(0, 1), (1.8, 2.5), (3.5, 4), (6, 7)]
    transcript = [
        TranscriptSegment(
            id=segment_id,
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=index,
            start_seconds=Decimal(str(start)),
            end_seconds=Decimal(str(end)),
            text=f"synthetic fragment {index}",
            source_role="incoming",
        )
        for index, (segment_id, (start, end)) in enumerate(zip(segment_ids, spans, strict=True))
    ]
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=index,
            start_seconds=Decimal(str(start)),
            end_seconds=Decimal(str(end)),
            text=f"synthetic fragment {index}",
            speaker_label="remote-speaker",
            source_role="incoming",
        )
        for index, (start, end) in enumerate(spans)
    ]

    state = view_models.transcript_state(
        language="ru",
        transcript_segments=transcript,
        diarization_segments=diarization,
        status="ready",
        playback_available=True,
        playback_duration_seconds=60,
    )

    assert len(state.segments) == 4
    assert len(state.speaker_turns) == 4
    first, *_, second = state.speaker_turns
    assert first.speaker_key == second.speaker_key
    assert first.start_seconds == 0.0
    assert first.end_seconds == 1.0
    assert first.text == "synthetic fragment 0"
    assert len(first.source_segment_ids) == 1
    assert first.processing_result_id == result_id
    assert first.turn_id.startswith("turn_")
    assert first.seekable is True
    assert first.seek_seconds == 0.0
    assert second.start_seconds == 6.0
    assert second.end_seconds == 7.0
    assert [segment.text for segment in state.segments] == [
        f"synthetic fragment {index}" for index in range(4)
    ]
    assert {segment.speaker_label for segment in state.segments} == {"Спикер не определён"}
    assert {segment.attribution_state for segment in state.segments} == {"uncertain"}
    assert {segment.speaker_key for segment in state.segments} == {f"evidence:{result_id.hex}"}
    assert [turn.source_segment_ids for turn in state.speaker_turns] == [
        [str(row.id)] for row in diarization
    ]


def test_speaker_display_name_changes_labels_without_changing_keys() -> None:
    meeting = _meeting()
    result_id = uuid4()
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("1"),
            end_seconds=Decimal("3"),
            text="synthetic",
            speaker_label="SPEAKER_00",
            source_role="incoming",
        )
    ]

    stable_key = (
        view_models.canonical_speaker_model(
            _transcript_evidence(diarization),
            diarization,
            processing_result_id=result_id,
        )
        .turns[0]
        .speaker_key
    )
    transcript = view_models.transcript_state(
        language="ru",
        transcript_segments=_transcript_evidence(diarization),
        diarization_segments=diarization,
        status="ready",
        playback_available=True,
        playback_duration_seconds=10,
        speaker_names={stable_key: "Мария"},
    )
    speakers = view_models.speaker_state(
        diarization,
        transcript_segments=_transcript_evidence(diarization),
        speaker_names={stable_key: "Мария"},
        can_rename=True,
    )

    assert transcript.segments[0].speaker_key == f"evidence:{result_id.hex}"
    assert transcript.segments[0].speaker_label == "Спикер не определён"
    assert transcript.speaker_turns[0].speaker_key == stable_key
    assert transcript.speaker_turns[0].speaker_label == "Мария"
    assert speakers.speakers[0].speaker_key == stable_key
    assert speakers.speakers[0].label == "Мария"
    assert speakers.speakers[0].display_name == "Мария"
    assert speakers.can_rename is True


def test_transcript_turns_split_on_speaker_track_and_exact_threshold() -> None:
    meeting = _meeting()
    result_id = uuid4()
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=index,
            start_seconds=Decimal(str(start)),
            end_seconds=Decimal(str(end)),
            text=f"fragment {index}",
            source_role=source_role,
        )
        for index, (start, end, source_role) in enumerate(
            [(0, 1, "incoming"), (2, 3, "incoming"), (3.5, 4.5, "incoming"), (5, 6, "mic")]
        )
    ]
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=index,
            start_seconds=segment.start_seconds,
            end_seconds=segment.end_seconds,
            text=segment.text,
            speaker_label="remote" if index < 2 else ("other" if index == 2 else "local"),
            source_role=segment.source_role,
        )
        for index, segment in enumerate(transcript)
    ]

    state = view_models.transcript_state(
        language="ru",
        transcript_segments=transcript,
        diarization_segments=diarization,
        status="ready",
    )

    assert [turn.text for turn in state.speaker_turns] == [
        "fragment 0",
        "fragment 1",
        "fragment 2",
        "fragment 3",
    ]


def test_transcript_turns_do_not_merge_unconfirmed_mapping_or_incomplete_state() -> None:
    meeting = _meeting()
    result_id = uuid4()
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=index,
            start_seconds=Decimal(str(index)),
            end_seconds=Decimal(str(index + 0.5)),
            text=f"unmapped {index}",
            source_role="incoming",
        )
        for index in range(2)
    ]

    state = view_models.transcript_state(
        language="ru",
        transcript_segments=transcript,
        diarization_segments=[],
        status="ready",
    )
    processing_state = view_models.transcript_state(
        language="ru",
        transcript_segments=transcript,
        diarization_segments=[],
        status="processing",
    )
    partial_state = view_models.transcript_state(
        language="ru",
        transcript_segments=transcript,
        diarization_segments=[
            DiarizationSegment(
                id=uuid4(),
                processing_result_id=result_id,
                meeting_id=meeting.id,
                workspace_id=meeting.workspace_id,
                sequence=index,
                start_seconds=row.start_seconds,
                end_seconds=row.end_seconds,
                text=row.text,
                speaker_label="remote-speaker",
                source_role="incoming",
            )
            for index, row in enumerate(transcript)
        ],
        status="partial",
    )

    assert state.speaker_turns == []
    assert state.segments == []
    assert state.degraded_reason == "diarization_pending"
    assert processing_state.speaker_turns == []
    assert processing_state.available is False
    assert partial_state.speaker_turns == []
    assert partial_state.segments == []
    assert partial_state.available is False
    assert partial_state.degraded_reason == "partial_transcript"


def test_transcript_and_timeline_share_degraded_asr_fallback_without_provider_turns() -> None:
    meeting = _meeting()
    result_id = uuid4()
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("1.250"),
            end_seconds=Decimal("2.750"),
            text="synthetic fallback",
            source_role="incoming",
        )
    ]

    transcript_state = view_models.transcript_state(
        language="ru",
        transcript_segments=transcript,
        diarization_segments=[],
        status="ready",
    )
    speaker_state = view_models.speaker_state([], transcript_segments=transcript)

    assert transcript_state.result_state == "accepted"
    assert transcript_state.available is False
    assert transcript_state.degraded_reason == "diarization_pending"
    assert speaker_state.result_state == "degraded_provider_result"
    assert speaker_state.available is True
    assert speaker_state.can_rename is False
    assert len(speaker_state.speakers) == 1
    assert speaker_state.speakers[0].label == "Спикер не определён"
    assert speaker_state.speakers[0].confirmed is False
    assert speaker_state.turns != transcript_state.speaker_turns
    assert [
        (segment.start_seconds, segment.end_seconds)
        for segment in speaker_state.speakers[0].segments
    ] == [(1.25, 2.75)]


def test_canonical_provider_turns_are_stable_across_rebuilds() -> None:
    meeting = _meeting()
    result_id = uuid4()
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=index,
            start_seconds=Decimal(str(index * 1.5)),
            end_seconds=Decimal(str(index * 1.5 + 1)),
            text=f"manual fragment {index}",
            speaker_label="SPEAKER_01",
            source_role="incoming",
        )
        for index in range(3)
    ]

    first = view_models.transcript_state(
        language="ru",
        transcript_segments=_transcript_evidence(diarization),
        diarization_segments=diarization,
        status="ready",
    )
    second = view_models.transcript_state(
        language="ru",
        transcript_segments=_transcript_evidence(diarization),
        diarization_segments=diarization,
        status="ready",
    )

    assert first.speaker_turns == second.speaker_turns
    assert len(first.speaker_turns) == 3
    assert [turn.source_segment_ids for turn in first.speaker_turns] == [
        [str(row.id)] for row in diarization
    ]


def test_canonical_provider_turns_preserve_unknown_rows_as_singletons() -> None:
    meeting = _meeting()
    result_id = uuid4()
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=index,
            start_seconds=Decimal(str(index)),
            end_seconds=Decimal(str(index + 0.9)),
            text=f"unconfirmed {index}",
            speaker_label="UNKNOWN",
            source_role="incoming",
        )
        for index in range(2)
    ]

    state = view_models.transcript_state(
        language="ru",
        transcript_segments=_transcript_evidence(diarization),
        diarization_segments=diarization,
        status="ready",
    )

    assert [turn.attribution_state for turn in state.speaker_turns] == [
        "unknown",
        "unknown",
    ]
    assert [turn.text for turn in state.speaker_turns] == [
        "unconfirmed 0",
        "unconfirmed 1",
    ]
