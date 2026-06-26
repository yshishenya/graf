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
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    Meeting,
    ProcessingResult,
    ProcessingWorkflow,
    TranscriptSegment,
)
from twobrain_rec_server.domain.statuses import (
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
    transcript_available: bool = False,
    artifacts: list[ArtifactEgressState] | None = None,
) -> MeetingListItem:
    return MeetingListItem(
        meeting_id=uuid4(),
        title=title,
        started_at=started_at,
        ended_at=None,
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
    assert view_models.format_duration(65) == "1m"
    assert view_models.date_label(audio) == "16 июн"
    assert view_models.sort_label("duration_asc") == "Сначала короткие"
    assert view_models.sort_label("unknown") == "Недавно обновленные"


def test_recording_date_labels_and_sort_labels_use_started_at_with_truthful_fallbacks() -> None:
    recorded = _list_item(started_at=datetime(2026, 6, 26, 23, 30, tzinfo=UTC))
    timezone_shifted = _list_item(started_at=datetime(2026, 6, 27, 2, 30, tzinfo=timezone(timedelta(hours=3))))
    legacy = _list_item(title="legacy-no-recording-date", started_at=None)

    assert view_models.date_label(recorded) == "26 июн"
    assert view_models.date_label(timezone_shifted) == "27 июн"
    assert view_models.date_label(legacy) == "Без даты"
    assert view_models.sort_label("started_desc") == "Новые по дате записи"
    assert view_models.sort_label("started_asc") == "Старые по дате записи"


def test_safe_title_uses_legacy_local_recording_fallback_without_control_characters() -> None:
    meeting = _meeting()
    meeting.title = "\x00"
    meeting.local_recording_id = "legacy-no-title"

    assert view_models.safe_title(meeting) == "legacy-no-title"


def test_safe_title_suppresses_legacy_url_or_email_title() -> None:
    meeting = _meeting()
    meeting.title = "https://meet.example.com/private john@example.com"
    meeting.local_recording_id = "legacy-unsafe-title"

    assert view_models.safe_title(meeting) == "legacy-unsafe-title"


def test_safe_title_suppresses_legacy_bare_meeting_link_title() -> None:
    meeting = _meeting()
    meeting.title = "meet.google.com/abc-defg-hij"
    meeting.local_recording_id = "legacy-bare-link-title"

    assert view_models.safe_title(meeting) == "legacy-bare-link-title"


def test_safe_title_does_not_suppress_normal_words_that_contain_sk_dash() -> None:
    meeting = _meeting()
    meeting.title = "Risk-review"

    assert view_models.safe_title(meeting) == "Risk-review"


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
    assert state.segments[0].speaker_label == "Speaker 2"
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
        "incoming_system": "REMOTE_00",
        "local_microphone": "MIC",
    }


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
            start_seconds=Decimal("0"),
            end_seconds=Decimal("30"),
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
            start_seconds=Decimal("30"),
            end_seconds=Decimal("60"),
            text="two",
            speaker_label="Speaker 2",
            source_role="incoming",
        ),
    ]

    state = view_models.speaker_state(segments)

    assert state.available is True
    assert [(speaker.label, speaker.talk_time_percent) for speaker in state.speakers] == [
        ("Speaker 1", 50),
        ("Speaker 2", 50),
    ]


def test_governance_states_are_non_mutating_and_truthful() -> None:
    governance = view_models.governance_summary()

    assert governance.share.state == "available"
    assert governance.export.state == "disabled"
    assert governance.download.state == "disabled"
    assert governance.retention.state == "planned"
    assert governance.delete.destructive is True
    assert "2brain Rec" in governance.delete.label


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
