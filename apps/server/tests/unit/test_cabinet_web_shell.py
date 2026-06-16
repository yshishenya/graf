from datetime import UTC, datetime
from uuid import uuid4

from twobrain_rec_server.api.schemas import (
    ArtifactEgressState,
    GovernanceActionState,
    GovernanceActionSummary,
    MeetingAccessState,
    MeetingActivityResponse,
    MeetingFilterState,
    MeetingListItem,
    MeetingListResponse,
    MeetingProvenance,
    MeetingReviewResponse,
    NotesReviewState,
    PlaybackReviewState,
    ProcessingReviewState,
    SharePanelState,
    SlotState,
    SpeakerReviewState,
    TranscriptReviewState,
)
from twobrain_rec_server.cabinet.web import render_meeting_detail_page, render_meeting_list_page


def _governance() -> GovernanceActionSummary:
    return GovernanceActionSummary(
        share=GovernanceActionState(state="available", label="Share", reason="Login-required sharing", destructive=False),
        export=GovernanceActionState(state="disabled", label="Export package", reason="No package", destructive=False),
        download=GovernanceActionState(state="disabled", label="Download", reason="No artifact", destructive=False),
        retention=GovernanceActionState(state="planned", label="Retention policy planned", reason="future", destructive=False),
        delete=GovernanceActionState(
            state="planned",
            label="Delete this meeting everywhere 2brain Rec controls",
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
        deletion_truth_copy="Files already downloaded or exported are outside 2brain Rec deletion control.",
        assistant=SlotState(state="planned", label="Assistant", reason="future"),
        template=SlotState(state="planned", label="Template", reason="future"),
    )


def test_list_shell_renders_dense_controls_without_marketing_copy() -> None:
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[_item()],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
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
    assert "Team visibility" in page
    assert "Public links" in page
    assert "Files already downloaded" in page
    assert "Delete this meeting everywhere 2brain Rec controls" in page


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
