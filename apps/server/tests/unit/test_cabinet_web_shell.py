from datetime import UTC, datetime
from uuid import uuid4

from twobrain_rec_server.api.schemas import (
    GovernanceActionState,
    GovernanceActionSummary,
    MeetingFilterState,
    MeetingListItem,
    MeetingListResponse,
    MeetingProvenance,
    MeetingReviewResponse,
    NotesReviewState,
    PlaybackReviewState,
    ProcessingReviewState,
    SlotState,
    SpeakerReviewState,
    TranscriptReviewState,
)
from twobrain_rec_server.cabinet.web import render_meeting_detail_page, render_meeting_list_page


def _governance() -> GovernanceActionSummary:
    planned = GovernanceActionState(state="planned", label="Share planned", reason="future", destructive=False)
    return GovernanceActionSummary(
        share=planned,
        export=planned,
        download=planned,
        retention=planned,
        delete=GovernanceActionState(
            state="planned",
            label="Delete this meeting everywhere 2brain Rec controls",
            reason="future",
            destructive=True,
        ),
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
        assistant=SlotState(state="planned", label="Assistant", reason="future"),
        template=SlotState(state="planned", label="Template", reason="future"),
    )


def test_list_shell_renders_dense_controls_without_marketing_copy() -> None:
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, sort="updated_desc"),
            generated_at=datetime.now(UTC),
        )
    )

    assert "My Meetings" in page
    assert "Upcoming" in page
    assert "Meeting notes" in page
    assert "Upload file" in page
    assert "Newest first" in page
    assert "updated_desc" not in page
    assert ":focus-visible" in page
    assert "hero" not in page.lower()


def test_detail_shell_renders_tabs_and_gated_actions() -> None:
    page = render_meeting_detail_page(_review())

    assert "Notes" in page
    assert "Recording &amp; Transcript" in page
    assert "Транскрипт готовится" in page
    assert "Share planned" in page
    assert "Delete this meeting everywhere 2brain Rec controls" in page


def test_embedded_shell_removes_native_capture_controls_and_copy() -> None:
    list_page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, sort="updated_desc"),
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
