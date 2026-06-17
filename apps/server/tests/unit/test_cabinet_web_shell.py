from datetime import UTC, datetime, timedelta
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
    PlaybackReviewState,
    ProcessingReviewState,
    SharePanelState,
    SlotState,
    SpeakerReviewState,
    TranscriptReviewState,
)
from twobrain_rec_server.cabinet.web import (
    render_deletion_report_page,
    render_meeting_detail_page,
    render_meeting_list_page,
)
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY
from twobrain_rec_server.domain.statuses import (
    DeletionArtifactState,
    DeletionControlScope,
    DeletionState,
    LocalPurgeTaskState,
    LocalPurgeTaskType,
)


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
        deletion_truth_copy="Files already downloaded or exported are outside 2brain Rec deletion control.",
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
                label="Delivered copies are outside 2brain Rec control",
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
    assert "Записи встреч" in page
    assert "Новая" in page
    assert "Сначала новые" in page
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
    assert "Request deletion" in page


def test_detail_shell_reserves_notes_assistant_template_without_internal_feature_labels() -> None:
    review = _review()
    review.notes = NotesReviewState(available=False, sections=[], unavailable_reason="generation_future")

    page = render_meeting_detail_page(review)

    assert "Summary" in page
    assert "Decisions" in page
    assert "Action Items" in page
    assert "Follow-ups" in page
    assert "Outcomes processing" in page
    assert "AI notes are reserved for a later feature" not in page
    assert "No generated summary is shown yet" not in page
    assert "<h3>Assistant</h3>" in page
    assert "<button type=\"button\" disabled>Assistant</button>" in page
    assert "<h3>Template</h3>" in page
    assert "016" not in page


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


def test_deletion_report_shell_renders_metadata_only_lifecycle_truth() -> None:
    page = render_deletion_report_page("Sensitive customer sync", _deletion_report())

    assert "Deletion report" in page
    assert "2brain Rec controlled artifacts" in page
    assert "External dependencies" in page
    assert "Post-egress limits" in page
    assert "Local device purge" in page
    assert "Lifecycle activity" in page
    assert "deletion requested" in page
    assert "local purge acknowledged" in page
    assert "Owner/Admin" in page
    assert "Desktop device" in page
    assert "pending" in page
    assert "acknowledged" in page
    assert "unreachable" in page
    assert BOUNDED_DELETE_COPY in page
    assert "Sensitive customer sync" in page
    assert "storage_object_key" not in page
    assert "external_job_id" not in page
    assert "/Users/" not in page
    assert "SAFE_TRANSCRIPT_TEXT" not in page
