from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from twobrain_rec_server.api.schemas import (
    ArtifactEgressState,
    GovernanceActionState,
    GovernanceActionSummary,
    MeetingAccessState,
    MeetingListItem,
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
    TranscriptSegment,
)
from twobrain_rec_server.domain.statuses import (
    MediaRevisionSourceKind,
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
    ProcessingStatus,
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


def _governance() -> GovernanceActionSummary:
    disabled = GovernanceActionState(state="disabled", label="Disabled", reason="Synthetic.", destructive=False)
    return GovernanceActionSummary(
        share=disabled,
        export=disabled,
        download=disabled,
        retention=disabled,
        delete=GovernanceActionState(state="planned", label="Delete", reason="Synthetic.", destructive=True),
    )


def _list_item(
    *,
    source: str = "desktop_recording",
    title: str = "Synthetic meeting",
    started_at: datetime | None = datetime(2026, 6, 16, 8, 0, tzinfo=UTC),
    recording_display_timezone_offset_minutes: int | None = None,
    transcript_available: bool = False,
    artifacts: list[ArtifactEgressState] | None = None,
) -> MeetingListItem:
    return MeetingListItem(
        meeting_id=uuid4(),
        title=title,
        started_at=started_at,
        ended_at=None,
        recording_display_timezone_offset_minutes=recording_display_timezone_offset_minutes,
        duration_seconds=65,
        source=source,
        status="ready",
        status_label="Ready",
        status_reason=None,
        primary_action="open",
        transcript_available=transcript_available,
        diarization_available=False,
        notes_available=False,
        updated_at=None,
        access=_owner_access(),
        artifacts=artifacts or [],
        governance=_governance(),
        future_slots=[SlotState(state="planned", label="Star", reason="Synthetic.")],
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
    assert view_models.date_label(audio) == "16 июн"
    assert view_models.sort_label("duration_asc") == "Сначала короткие"
    assert view_models.sort_label("unknown") == "Недавно обновлённые"


def test_recording_date_labels_and_sort_labels_use_started_at_with_truthful_fallbacks() -> None:
    recorded = _list_item(started_at=datetime(2026, 6, 26, 23, 30, tzinfo=UTC))
    timezone_shifted = _list_item(started_at=datetime(2026, 6, 27, 2, 30, tzinfo=timezone(timedelta(hours=3))))
    offset_shifted = _list_item(
        started_at=datetime(2026, 6, 26, 21, 30, tzinfo=UTC),
        recording_display_timezone_offset_minutes=180,
    )
    legacy = _list_item(title="legacy-no-recording-date", started_at=None)

    assert view_models.date_label(recorded) == "26 июн"
    assert view_models.date_label(timezone_shifted) == "27 июн"
    assert view_models.date_label(offset_shifted) == "27 июн"
    assert view_models.date_label(legacy) == "Без даты"
    assert view_models.sort_label("started_desc") == "Новые по дате записи"
    assert view_models.sort_label("started_asc") == "Старые по дате записи"


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

    assert view_models.review_status(_meeting(), result=ready, workflow=None) == "ready"
    assert view_models.review_status(_meeting(), result=partial, workflow=None) == "partial"
    assert view_models.review_status(_meeting(ProcessingStatus.POLLING), result=None, workflow=None) == "processing"
    assert view_models.review_status(_meeting(ProcessingStatus.FAILED_TERMINAL), result=None, workflow=None) == "failed"


def test_processing_state_uses_no_speech_and_invalid_audio_copy_from_result() -> None:
    no_speech = ProcessingResult(
        id=uuid4(),
        meeting_id=uuid4(),
        workspace_id=uuid4(),
        mediascribe_job_id=uuid4(),
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
        diarization_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
        segment_count=0,
        diarization_segment_count=0,
        failure_reason="no_recognizable_speech",
        failure_source="input_audio",
    )
    invalid_audio = ProcessingResult(
        id=uuid4(),
        meeting_id=uuid4(),
        workspace_id=uuid4(),
        mediascribe_job_id=uuid4(),
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
        diarization_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
        segment_count=0,
        diarization_segment_count=0,
        failure_reason="invalid_audio_payload",
        failure_source="input_audio",
    )

    no_speech_state = view_models.processing_state(_meeting(), result=no_speech, workflow=None)
    invalid_audio_state = view_models.processing_state(_meeting(), result=invalid_audio, workflow=None)

    assert no_speech_state.reason_label == (
        "MediaScribe обработал запись, но транскрипт не создан: распознаваемая речь не найдена."
    )
    assert invalid_audio_state.reason_label == "Файл записи не является декодируемым аудио или поврежден."
    assert no_speech_state.transcript_available is False
    assert invalid_audio_state.transcript_available is False


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
    assert state.segments[0].speaker_label == "SPEAKER_00"
    assert state.segments[0].source_role == "incoming_system"
    assert state.segments[0].seekable is False
    assert state.segments[0].seek_seconds is None


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

    by_source = {segment.source_role: segment.speaker_label for segment in state.segments}
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

    assert state.segments[0].speaker_label == "SPEAKER_01"


def test_dual_track_mapping_canonicalizes_dependency_labels_when_speaker_style_label_is_present() -> None:
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
    speaker_state = view_models.speaker_state(diarization)

    assert [segment.speaker_label for segment in transcript_state.segments] == [
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
        force_speaker_labels=True,
    )

    assert [segment.speaker_label for segment in state.segments] == [
        "SPEAKER_00",
        "SPEAKER_01",
        "SPEAKER_01",
        "SPEAKER_02",
    ]
    assert [segment.text for segment in state.segments] == [
        "speaker zero",
        "speaker one",
        "unknown dependency label",
        "speaker two",
    ]
    assert "Incoming system" not in {segment.speaker_label for segment in state.segments}
    assert "UNKNOWN" not in {segment.speaker_label for segment in state.segments}


def test_manual_upload_transcript_uses_speaker_zero_when_diarization_is_missing() -> None:
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
        force_speaker_labels=True,
    )

    assert [segment.speaker_label for segment in state.segments] == ["SPEAKER_00", "SPEAKER_00"]


def test_manual_upload_review_response_falls_back_to_speaker_zero_without_diarization() -> None:
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
        workflow=None,
        transcript_segments=transcript,
        diarization_segments=[],
        dependency=None,
    )

    assert response.meeting.source == "manual_upload"
    assert [segment.speaker_label for segment in response.transcript.segments] == ["SPEAKER_00"]


def test_manual_upload_review_response_uses_diarization_as_transcript_source() -> None:
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

    response = view_models.build_review_response(
        meeting,
        media_revision=media_revision,
        result=result,
        workflow=None,
        transcript_segments=transcript,
        diarization_segments=diarization,
        dependency=None,
    )

    assert [segment.text for segment in response.transcript.segments] == [
        "diarization row is the review source"
    ]
    assert [segment.speaker_label for segment in response.transcript.segments] == ["SPEAKER_01"]


def test_manual_upload_transcript_falls_back_to_transcript_text_when_diarization_text_is_blank() -> None:
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
        force_speaker_labels=True,
    )

    assert [segment.text for segment in state.segments] == [
        "first transcript row",
        "second transcript row",
    ]
    assert [segment.speaker_label for segment in state.segments] == ["SPEAKER_00", "SPEAKER_01"]
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
        transcript_segments=[],
        diarization_segments=diarization,
        status="ready",
        force_speaker_labels=True,
    )

    assert [segment.text for segment in state.segments] == [
        "speaker zero text",
        "speaker one text",
    ]
    assert [segment.speaker_label for segment in state.segments] == ["SPEAKER_00", "SPEAKER_01"]
    assert all(segment.text.strip() for segment in state.segments)


def test_mediascribe_speaker_time_matcher_handles_long_inputs_without_source_fallbacks() -> None:
    meeting = _meeting()
    result_id = uuid4()
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=sequence,
            start_seconds=Decimal(sequence * 5),
            end_seconds=Decimal(sequence * 5 + 4),
            text="single track text",
            source_role="incoming",
        )
        for sequence in range(1200)
    ]
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=speaker_index,
            start_seconds=Decimal(speaker_index * 500),
            end_seconds=Decimal((speaker_index + 1) * 500 - 1),
            text="speaker region",
            speaker_label=f"SPEAKER_{speaker_index:02d}",
            source_role="incoming",
        )
        for speaker_index in range(12)
    ]

    labels = view_models.mediascribe_speaker_labels_by_time(transcript, diarization)

    assert len(labels) == 1200
    assert set(labels) == {
        f"SPEAKER_{speaker_index:02d}" for speaker_index in range(12)
    }
    assert labels[0] == "SPEAKER_00"
    assert labels[100] == "SPEAKER_01"
    assert labels[-1] == "SPEAKER_11"


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

    assert [(segment.seekable, segment.seek_seconds) for segment in state.segments] == [
        (True, 0.0),
        (True, 12.5),
    ]


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

    state = view_models.speaker_state(segments)

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

    state = view_models.speaker_state(segments, force_speaker_labels=True)

    assert {speaker.label for speaker in state.speakers} == {"SPEAKER_00", "SPEAKER_01"}


def test_manual_upload_speaker_mapping_uses_speaker_zero_when_only_unknown_rows_exist() -> None:
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

    state = view_models.speaker_state(segments, force_speaker_labels=True)

    assert [speaker.label for speaker in state.speakers] == ["SPEAKER_00"]


def test_calendar_roster_does_not_rename_transcript_speakers_or_grant_access() -> None:
    roster = normalize_calendar_participants(
        [{"participant_kind": "required_attendee", "email": "speaker@example.test", "display_name": "Calendar Name"}]
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

    state = view_models.speaker_state(diarization)

    assert roster[0]["display_name"] == "Calendar Name"
    assert state.speakers[0].label == "SPEAKER_00"
    assert "access_grant" not in roster[0]
    assert "share_grant" not in roster[0]


def test_governance_states_are_non_mutating_and_truthful() -> None:
    governance = view_models.governance_summary()

    assert governance.share.state == "available"
    assert governance.export.state == "disabled"
    assert governance.download.state == "disabled"
    assert governance.retention.state == "planned"
    assert governance.delete.destructive is True
    assert "GRAF" in governance.delete.label


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
