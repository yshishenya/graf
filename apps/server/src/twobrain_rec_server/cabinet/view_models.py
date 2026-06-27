from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import cast

from twobrain_rec_server.api.schemas import (
    ArtifactEgressState,
    CalendarRosterParticipantView,
    CalendarRosterReviewState,
    GovernanceActionState,
    GovernanceActionSummary,
    MeetingAccessState,
    MeetingActivityResponse,
    MeetingListItem,
    MeetingProvenance,
    MeetingReviewResponse,
    MeetingReviewStatus,
    NotesActionCategoryState,
    NotesActionTruthState,
    NotesReviewState,
    OutcomeItemView,
    OutcomeProvenanceView,
    OutcomeSourceReferenceView,
    PlaybackReviewState,
    ProcessingReviewState,
    SharePanelState,
    SlotState,
    SourceRoleView,
    SpeakerLane,
    SpeakerLaneSegment,
    SpeakerReviewState,
    TranscriptReviewState,
    TranscriptSegmentView,
)
from twobrain_rec_server.cabinet.access import owner_access_state
from twobrain_rec_server.cabinet.constants import DELETION_TRUTH_COPY
from twobrain_rec_server.db.models import (
    CalendarParticipant,
    DiarizationSegment,
    MediaRevision,
    Meeting,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    ProcessingDependencyState,
    ProcessingResult,
    ProcessingWorkflow,
    TranscriptSegment,
)
from twobrain_rec_server.domain.statuses import (
    DeletionState,
    MediaRevisionSourceKind,
    MeetingStatus,
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
    ProcessingStatus,
    SummaryStatus,
)

STATUS_LABELS: dict[str, str] = {
    "local_only": "Local only",
    "uploading": "Uploading",
    "submitted": "Submitted",
    "processing": "Processing",
    "ready": "Ready",
    "partial": "Partial",
    "blocked": "Blocked",
    "failed": "Failed",
    "unavailable": "Unavailable",
    "deleted_future": "Delete planned",
}

SORT_LABELS: dict[str, str] = {
    "updated_desc": "Недавно обновленные",
    "updated_asc": "Давно обновленные",
    "started_desc": "Новые по дате записи",
    "started_asc": "Старые по дате записи",
    "duration_desc": "Сначала длинные",
    "duration_asc": "Сначала короткие",
    "title_asc": "По названию",
}

PROCESSING_STATUSES = {
    ProcessingStatus.PENDING_PROCESSING.value,
    ProcessingStatus.STARTING.value,
    ProcessingStatus.WORKFLOW_STARTED.value,
    ProcessingStatus.SUBMITTING.value,
    ProcessingStatus.SUBMITTED.value,
    ProcessingStatus.POLLING.value,
    ProcessingStatus.IMPORTING.value,
}

UNSAFE_TITLE_RE = re.compile(
    r"https?://|www\.|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|token=|password|bearer\s|(?:^|[^A-Z0-9])sk-[A-Z0-9_-]{8,}|\b(?:meet\.google\.com/[A-Z0-9_-]+|zoom\.us/(?:j|my)/[A-Z0-9._-]+|teams\.microsoft\.com/l/meetup-join|whereby\.com/[A-Z0-9_-]+|webex\.com/meet/[A-Z0-9._-]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CabinetNavigationItem:
    id: str
    label: str
    href: str
    icon: str
    enabled: bool = True
    count: int | None = None


@dataclass(frozen=True)
class CabinetNavigationModel:
    active: str
    items: tuple[CabinetNavigationItem, ...]
    workspace_title: str = "Личный"
    workspace_subtitle: str = "Бесплатный план"


def cabinet_navigation(*, active: str = "meetings", pending_actions: int = 6) -> CabinetNavigationModel:
    return CabinetNavigationModel(
        active=active,
        items=(
            CabinetNavigationItem("search", "Поиск", "#", "filter", enabled=False),
            CabinetNavigationItem("meetings", "Мои встречи", "/meetings", "audio"),
            CabinetNavigationItem("shared", "Общие", "#", "bookmark", enabled=False),
            CabinetNavigationItem("actions", "Действия", "#", "check", enabled=False, count=pending_actions),
            CabinetNavigationItem("activity", "Активность", "#", "sort", enabled=False),
            CabinetNavigationItem("settings", "Настройки", "#", "filter", enabled=False),
        ),
    )


def source_role_label(source_role: str | None) -> SourceRoleView:
    normalized = (source_role or "").lower()
    if normalized in {"mic", "microphone", "local_microphone"}:
        return "local_microphone"
    if normalized in {"incoming", "system", "incoming_system"}:
        return "incoming_system"
    return "unknown"


def format_timestamp(seconds: Decimal | float | int) -> str:
    total_seconds = max(0, int(float(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, second = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{second:02d}"
    return f"{minutes:02d}:{second:02d}"


def format_duration(seconds: int) -> str:
    minutes, second = divmod(max(0, seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m"
    return f"{second}s"


def date_label(item: MeetingListItem) -> str:
    if item.started_at is None:
        return "Без даты"
    months = {
        1: "янв",
        2: "фев",
        3: "мар",
        4: "апр",
        5: "май",
        6: "июн",
        7: "июл",
        8: "авг",
        9: "сен",
        10: "окт",
        11: "ноя",
        12: "дек",
    }
    return f"{item.started_at.day} {months[item.started_at.month]}"


def sort_label(sort: str) -> str:
    return SORT_LABELS.get(sort, SORT_LABELS["updated_desc"])


def meeting_media_kind(item: MeetingListItem) -> str:
    if item.source == "manual_upload":
        return "upload"
    if item.source == "video_recording":
        return "video"
    has_audio = any(artifact.artifact_class == "audio" and artifact.state == "available" for artifact in item.artifacts)
    has_transcript = item.transcript_available or any(
        artifact.artifact_class == "transcript" and artifact.state == "available" for artifact in item.artifacts
    )
    if has_transcript and not has_audio:
        return "transcript"
    return "audio"


def meeting_media_label(item: MeetingListItem) -> str:
    return {
        "audio": "аудио",
        "video": "видео",
        "transcript": "транскрипт",
        "upload": "upload",
    }[meeting_media_kind(item)]


def safe_title(meeting: Meeting) -> str:
    title = (meeting.title or "").strip()
    title = "".join(char for char in title if char >= " " and char != "\x7f").strip()
    if UNSAFE_TITLE_RE.search(title):
        title = ""
    if not title:
        title = (meeting.local_recording_id or "").strip()
    if not title:
        title = "Untitled meeting"
    return "".join(char for char in title if char >= " " and char != "\x7f")[:500]


def transcript_available(result: ProcessingResult | None) -> bool:
    return bool(
        result is not None
        and result.status == ProcessingResultStatus.IMPORTED.value
        and result.transcript_status == ProcessingAvailabilityStatus.AVAILABLE.value
        and result.segment_count > 0
    )


def diarization_available(result: ProcessingResult | None) -> bool:
    return bool(
        result is not None
        and result.status == ProcessingResultStatus.IMPORTED.value
        and result.diarization_status == ProcessingAvailabilityStatus.AVAILABLE.value
        and result.diarization_segment_count > 0
    )


def review_status(
    meeting: Meeting,
    *,
    result: ProcessingResult | None,
    workflow: ProcessingWorkflow | None,
) -> MeetingReviewStatus:
    if (meeting.deletion_state or DeletionState.NONE.value) != DeletionState.NONE.value:
        return "deleted_future"
    has_transcript = transcript_available(result)
    has_diarization = diarization_available(result)
    if has_transcript and has_diarization:
        return "ready"
    if has_transcript or has_diarization:
        return "partial"

    lifecycle_status = workflow.status if workflow is not None else meeting.processing_status
    if lifecycle_status in PROCESSING_STATUSES:
        return "processing"
    if lifecycle_status == ProcessingStatus.NOT_SUBMITTED.value:
        return "submitted"
    if lifecycle_status == ProcessingStatus.BLOCKED.value:
        return "blocked"
    if lifecycle_status in {ProcessingStatus.FAILED_RETRYABLE.value, ProcessingStatus.FAILED_TERMINAL.value}:
        return "failed"
    if lifecycle_status == ProcessingStatus.CANCELED.value:
        return "unavailable"

    if meeting.status == MeetingStatus.DRAFT.value:
        return "local_only"
    if meeting.status == MeetingStatus.UPLOADING.value:
        return "uploading"
    if meeting.status in {MeetingStatus.FAILED.value, MeetingStatus.DEGRADED.value}:
        return "failed"
    return "unavailable"


def governance_summary(
    *,
    access: MeetingAccessState | None = None,
    artifacts: list[ArtifactEgressState] | None = None,
) -> GovernanceActionSummary:
    access = access or owner_access_state()
    artifacts = artifacts or []
    download_available = any(
        artifact.artifact_class in {"audio", "transcript", "summary"} and artifact.state == "available"
        for artifact in artifacts
    )
    export_available = any(
        artifact.artifact_class == "package" and artifact.state == "available"
        for artifact in artifacts
    )
    return GovernanceActionSummary(
        share=GovernanceActionState(
            state="available" if access.can_share else "disabled",
            label="Share",
            reason="Login-required sharing is available." if access.can_share else "Only permitted owners can manage sharing.",
            destructive=False,
        ),
        export=GovernanceActionState(
            state="available" if export_available and access.can_export else "disabled",
            label="Export package",
            reason="Includes only currently policy-allowed artifacts."
            if export_available and access.can_export
            else "No policy-allowed export package is available.",
            destructive=False,
        ),
        download=GovernanceActionState(
            state="available" if download_available and access.can_download else "disabled",
            label="Download",
            reason="Server-mediated artifact download is available."
            if download_available and access.can_download
            else "No policy-allowed artifact download is available.",
            destructive=False,
        ),
        retention=GovernanceActionState(
            state="planned",
            label="Retention policy planned",
            reason="Retention controls will show policy truth before activation.",
            destructive=False,
        ),
        delete=GovernanceActionState(
            state="planned",
            label="Delete this meeting everywhere 2brain Rec controls",
            reason="Planned; this does not promise deletion outside 2brain Rec control.",
            destructive=True,
        ),
    )


def future_slots() -> list[SlotState]:
    return [
        SlotState(state="planned", label="Star", reason="Saved meetings are planned."),
        SlotState(state="planned", label="Tag", reason="Tags are planned."),
        SlotState(state="planned", label="Access", reason="Collaboration access is planned."),
        SlotState(state="planned", label="More", reason="More actions are planned."),
    ]


def slot_state(label: str) -> SlotState:
    return SlotState(state="planned", label=label, reason="Planned for a later feature slice.")


def build_list_item(
    meeting: Meeting,
    *,
    media_revision: MediaRevision | None = None,
    result: ProcessingResult | None,
    workflow: ProcessingWorkflow | None,
    access: MeetingAccessState | None = None,
    artifacts: list[ArtifactEgressState] | None = None,
    outcome_set: MeetingOutcomeSet | None = None,
    outcome_items: list[MeetingOutcomeItem] | None = None,
) -> MeetingListItem:
    status = review_status(meeting, result=result, workflow=workflow)
    access_state = access or owner_access_state()
    artifact_states = artifacts or []
    notes_truth = notes_action_truth_state(status=status, result=result, outcome_set=outcome_set, outcome_items=outcome_items or [])
    return MeetingListItem(
        meeting_id=meeting.id,
        title=safe_title(meeting),
        started_at=meeting.started_at,
        ended_at=meeting.ended_at,
        duration_seconds=max(0, meeting.duration_seconds),
        source=_meeting_source(media_revision),
        status=status,
        status_label=STATUS_LABELS[status],
        status_reason=workflow.last_reason_code if workflow is not None and status in {"blocked", "failed"} else None,
        primary_action=primary_action_for_status(status),
        transcript_available=transcript_available(result),
        diarization_available=diarization_available(result),
        notes_available=notes_truth.summary.state == "available",
        notes_action_truth=notes_truth,
        updated_at=meeting.updated_at,
        access=access_state,
        artifacts=artifact_states,
        governance=governance_summary(access=access_state, artifacts=artifact_states),
        future_slots=future_slots(),
    )


def primary_action_for_status(status: MeetingReviewStatus) -> str:
    if status in {"ready", "partial"}:
        return "open"
    if status in {"processing", "submitted", "uploading"}:
        return "wait"
    if status == "blocked":
        return "open_status"
    if status == "failed":
        return "retry_future"
    return "unavailable"


def _meeting_source(media_revision: MediaRevision | None) -> str:
    if media_revision is not None and media_revision.source_kind == MediaRevisionSourceKind.VIDEO_CAPTURE.value:
        return "video_recording"
    return "desktop_recording"


def processing_state(
    meeting: Meeting,
    *,
    result: ProcessingResult | None,
    workflow: ProcessingWorkflow | None,
) -> ProcessingReviewState:
    status = review_status(meeting, result=result, workflow=workflow)
    has_transcript = transcript_available(result)
    has_diarization = diarization_available(result)
    summary_available = bool(result is not None and result.summary_status == SummaryStatus.AVAILABLE.value)
    reason_code = workflow.last_reason_code if workflow is not None and status in {"blocked", "failed"} else None
    return ProcessingReviewState(
        state=status,
        stage=stage_for_status(status, workflow.status if workflow is not None else meeting.processing_status),
        reason_code=reason_code,
        reason_label=reason_label(reason_code),
        content_available=has_transcript or has_diarization or summary_available,
        transcript_available=has_transcript,
        diarization_available=has_diarization,
        summary_available=summary_available,
        updated_at=(workflow.updated_at if workflow is not None else meeting.updated_at),
        next_action=next_action_for_status(status),
    )


def stage_for_status(status: str, lifecycle_status: str) -> str | None:
    if status in {"ready", "partial"}:
        return "ready"
    if status == "processing":
        if lifecycle_status in {ProcessingStatus.SUBMITTED.value, ProcessingStatus.POLLING.value}:
            return "mediascribe"
        if lifecycle_status == ProcessingStatus.IMPORTING.value:
            return "importing"
        return "submitted"
    if status == "submitted":
        return "stored"
    if status in {"blocked", "failed"}:
        return status
    if status in {"uploading", "local_only"}:
        return "upload"
    return None


def next_action_for_status(status: str) -> str:
    if status in {"processing", "submitted", "uploading"}:
        return "wait"
    if status == "blocked":
        return "contact_operator"
    if status == "failed":
        return "contact_operator"
    if status in {"local_only"}:
        return "open_desktop_queue"
    return "none"


def reason_label(reason_code: str | None) -> str | None:
    if reason_code is None:
        return None
    return {
        "mediascribe_validation_failed": "Processing result could not be imported safely.",
        "blocked_config": "Processing is blocked by server configuration.",
    }.get(reason_code, "Processing needs operator review.")


def transcript_state(
    *,
    language: str | None,
    transcript_segments: Iterable[TranscriptSegment],
    diarization_segments: Iterable[DiarizationSegment],
    status: MeetingReviewStatus,
    playback_available: bool = False,
    playback_duration_seconds: int | None = None,
) -> TranscriptReviewState:
    transcripts = sorted(transcript_segments, key=lambda row: (row.sequence, row.start_seconds))
    diarization_by_segment_key = {
        (row.sequence, source_role_label(row.source_role)): row for row in diarization_segments
    }
    if status not in {"ready", "partial"} or not transcripts:
        return TranscriptReviewState(
            available=False,
            language=language,
            degraded_reason="processing" if status in {"processing", "submitted"} else "unavailable",
            search_enabled=False,
            segments=[],
        )
    segments = []
    for segment in transcripts:
        seek_seconds = _seek_seconds(
            segment.start_seconds,
            playback_available=playback_available,
            playback_duration_seconds=playback_duration_seconds,
        )
        segments.append(
            TranscriptSegmentView(
            segment_id=str(segment.id),
            sequence=segment.sequence,
            start_seconds=float(segment.start_seconds),
            end_seconds=float(segment.end_seconds),
            timestamp_label=format_timestamp(segment.start_seconds),
            speaker_label=speaker_label_for_segment(
                segment,
                diarization_by_segment_key.get((segment.sequence, source_role_label(segment.source_role))),
            ),
            source_role=source_role_label(segment.source_role),
            text=segment.text,
            confidence_label="unknown",
            seekable=seek_seconds is not None,
            seek_seconds=seek_seconds,
        )
        )
    return TranscriptReviewState(
        available=True,
        language=language,
        degraded_reason=None if status == "ready" else "partial_transcript",
        search_enabled=True,
        segments=segments,
    )


def _seek_seconds(
    value: Decimal,
    *,
    playback_available: bool,
    playback_duration_seconds: int | None,
) -> float | None:
    if not playback_available:
        return None
    seconds = float(value)
    if seconds < 0:
        return None
    if playback_duration_seconds is not None and seconds > playback_duration_seconds:
        return None
    return seconds


def speaker_label_for_segment(segment: TranscriptSegment, diarization: DiarizationSegment | None) -> str:
    if diarization is not None and diarization.speaker_label:
        return diarization.speaker_label
    source_role = source_role_label(segment.source_role)
    return {
        "local_microphone": "Local microphone",
        "incoming_system": "Incoming system",
        "unknown": "Unknown speaker",
    }[source_role]


def speaker_state(diarization_segments: Iterable[DiarizationSegment]) -> SpeakerReviewState:
    rows = sorted(diarization_segments, key=lambda row: (row.start_seconds, row.sequence))
    if not rows:
        return SpeakerReviewState(
            available=False,
            assignment_state="reserved",
            degraded_reason="diarization_unavailable",
            speakers=[],
        )

    grouped: dict[str, list[DiarizationSegment]] = defaultdict(list)
    for row in rows:
        grouped[row.speaker_label].append(row)
    total = sum(max(0.0, float(row.end_seconds) - float(row.start_seconds)) for row in rows) or 1.0
    speakers: list[SpeakerLane] = []
    for speaker_label, speaker_rows in grouped.items():
        duration = sum(max(0.0, float(row.end_seconds) - float(row.start_seconds)) for row in speaker_rows)
        source_roles = _unique(source_role_label(row.source_role) for row in speaker_rows)
        speakers.append(
            SpeakerLane(
                speaker_key=speaker_label.lower().replace(" ", "-"),
                label=speaker_label,
                talk_time_percent=round(duration / total * 100),
                source_roles=source_roles,
                segments=[
                    SpeakerLaneSegment(start_seconds=float(row.start_seconds), end_seconds=float(row.end_seconds))
                    for row in speaker_rows
                ],
                confidence_label="unknown",
            )
        )
    return SpeakerReviewState(available=True, assignment_state="reserved", degraded_reason=None, speakers=speakers)


def calendar_roster_state(participants: Iterable[CalendarParticipant]) -> CalendarRosterReviewState:
    views = [
        CalendarRosterParticipantView(
            participant_kind=participant.participant_kind,
            response_status=participant.response_status,
            display_name=participant.display_name,
            email_present=bool(participant.email_hash or participant.email),
            workspace_relation=participant.workspace_relation,
            recipient_candidate_class=participant.recipient_candidate_class,
        )
        for participant in participants
    ]
    return CalendarRosterReviewState(
        available=bool(views),
        roster_state="available" if views else "not_available",
        participant_count=len(views),
        source="calendar" if views else "none",
        participants=views,
    )


def notes_state(status: MeetingReviewStatus) -> NotesReviewState:
    if status in {"ready", "partial"}:
        return NotesReviewState(available=False, sections=[], unavailable_reason="generation_future")
    if status in {"processing", "submitted", "uploading"}:
        return NotesReviewState(available=False, sections=[], unavailable_reason="processing")
    return NotesReviewState(available=False, sections=[], unavailable_reason="not_requested")


def _notes_action_category(
    *,
    state: str,
    label: str,
    reason: str,
    readiness_impact: str,
    copy_key: str,
    items: list[OutcomeItemView] | None = None,
) -> NotesActionCategoryState:
    return NotesActionCategoryState(
        state=state,
        label=label,
        reason=reason,
        readiness_impact=readiness_impact,
        copy_key=copy_key,
        items=items or [],
    )


def notes_action_truth_state(
    *,
    status: MeetingReviewStatus,
    result: ProcessingResult | None,
    outcome_set: MeetingOutcomeSet | None = None,
    outcome_items: list[MeetingOutcomeItem] | None = None,
) -> NotesActionTruthState:
    if outcome_set is not None and status in {"ready", "partial"}:
        return stored_outcome_truth_state(outcome_set, outcome_items or [])
    if status in {"processing", "submitted", "uploading"}:
        category = _notes_action_category(
            state="processing",
            label="Outcomes processing",
            reason="Transcript and generated outcomes may still be processing.",
            readiness_impact="keeps_gap_open",
            copy_key="notes.outcomes.processing",
        )
        return NotesActionTruthState(
            summary=category,
            key_points=category,
            decisions=category,
            action_items=category,
            followups=category,
            risks=category,
            questions=category,
            evidence=category,
            source_basis="processing_status",
        )

    if status in {"blocked", "failed"}:
        category = _notes_action_category(
            state="blocked",
            label="Outcomes blocked",
            reason="Meeting processing needs operator review before outcomes can be trusted.",
            readiness_impact="keeps_gap_open",
            copy_key="notes.outcomes.blocked",
        )
        return NotesActionTruthState(
            summary=category,
            key_points=category,
            decisions=category,
            action_items=category,
            followups=category,
            risks=category,
            questions=category,
            evidence=category,
            source_basis="processing_status",
        )

    if status in {"ready", "partial"}:
        if result is not None and result.summary_status == SummaryStatus.AVAILABLE.value:
            summary = _notes_action_category(
                state="blocked",
                label="Summary unavailable",
                reason="Summary availability was reported, but no stored launch-safe summary content is available.",
                readiness_impact="keeps_gap_open",
                copy_key="notes.summary.blocked_missing_stored_output",
            )
            deferred = _notes_action_category(
                state="deferred",
                label="Outcome deferred",
                reason="This outcome is deferred until generated content is stored and reviewable.",
                readiness_impact="keeps_gap_open",
                copy_key="notes.outcomes.deferred",
            )
            return NotesActionTruthState(
                summary=summary,
                key_points=deferred,
                decisions=deferred,
                action_items=deferred,
                followups=deferred,
                risks=deferred,
                questions=deferred,
                evidence=deferred,
                source_basis="processing_status",
            )
        category = _notes_action_category(
            state="deferred",
            label="Outcomes deferred",
            reason="Transcript review is available, but generated meeting outcomes are not part of this stored result.",
            readiness_impact="keeps_gap_open",
            copy_key="notes.outcomes.deferred",
        )
        return NotesActionTruthState(
            summary=category,
            key_points=category,
            decisions=category,
            action_items=category,
            followups=category,
            risks=category,
            questions=category,
            evidence=category,
            source_basis="policy_deferral",
        )

    category = _notes_action_category(
        state="unavailable",
        label="Outcomes unavailable",
        reason="No reviewable transcript or generated outcome source is available for this meeting.",
        readiness_impact="keeps_gap_open",
        copy_key="notes.outcomes.unavailable",
    )
    return NotesActionTruthState(
        summary=category,
        key_points=category,
        decisions=category,
        action_items=category,
        followups=category,
        risks=category,
        questions=category,
        evidence=category,
        source_basis="not_supported",
    )


def stored_outcome_truth_state(
    outcome_set: MeetingOutcomeSet,
    outcome_items: list[MeetingOutcomeItem],
) -> NotesActionTruthState:
    by_category: dict[str, list[OutcomeItemView]] = defaultdict(list)
    if outcome_set.status in {"available", "partial"}:
        for item in sorted(outcome_items, key=lambda row: (row.category, row.sequence)):
            by_category[item.category].append(_outcome_item_view(item))

    def category_state(category: str, label: str) -> NotesActionCategoryState:
        state = getattr(outcome_set, f"{category}_state")
        return _notes_action_category(
            state=state,
            label=_outcome_state_label(state, label),
            reason=_outcome_state_reason(state),
            readiness_impact="closes_gap" if state in {"available", "not_found", "not_inferable"} else "keeps_gap_open",
            copy_key=f"notes.{category}.{state}",
            items=by_category.get(category, []),
        )

    return NotesActionTruthState(
        summary=category_state("summary", "Итоги готовы"),
        key_points=category_state("key_points", "Ключевые пункты"),
        decisions=category_state("decisions", "Решения"),
        action_items=category_state("action_items", "Действия"),
        followups=category_state("followups", "Follow-ups"),
        risks=category_state("risks", "Риски"),
        questions=category_state("questions", "Вопросы"),
        evidence=category_state("evidence", "Evidence"),
        source_basis=_outcome_source_basis(outcome_set),
        provenance=OutcomeProvenanceView(
            generator_kind=outcome_set.generator_kind,
            generator_version=outcome_set.generator_version,
            generated_at=outcome_set.generated_at,
            latency_ms=outcome_set.latency_ms,
        ),
    )


def _outcome_source_basis(outcome_set: MeetingOutcomeSet) -> str:
    if outcome_set.status in {"queued", "generating"}:
        return "processing_status"
    if outcome_set.status in {"blocked", "failed", "unsafe"}:
        return "blocked"
    return "stored_output"


def _outcome_item_view(item: MeetingOutcomeItem) -> OutcomeItemView:
    refs = [OutcomeSourceReferenceView(**ref) for ref in item.source_refs_json]
    return OutcomeItemView(
        category=item.category,
        sequence=item.sequence,
        text=item.text,
        owner_text=item.owner_text,
        due_date_text=item.due_date_text,
        truth_label=item.truth_label,
        source_refs=refs,
    )


def _outcome_state_label(state: str, available_label: str) -> str:
    return {
        "available": available_label,
        "not_found": "Не найдено",
        "not_inferable": "Не удалось надежно определить",
        "processing": "Готовится",
        "blocked": "Заблокировано",
        "unsafe": "Нужна проверка",
        "unavailable": "Недоступно",
    }.get(state, state)


def _outcome_state_reason(state: str) -> str:
    return {
        "available": "Сохраненный итог доступен и связан с расшифровкой.",
        "not_found": "В расшифровке нет надежной опоры для этой категории.",
        "not_inferable": "Эту категорию нельзя надежно вывести из расшифровки.",
        "processing": "Итоги еще формируются.",
        "blocked": "Итоги заблокированы безопасной проверкой.",
        "unsafe": "Итоги требуют проверки перед показом.",
        "unavailable": "Итоги недоступны.",
    }.get(state, "Состояние итогов неизвестно.")


def playback_state(
    meeting: Meeting,
    status: MeetingReviewStatus,
    review_playback: ArtifactEgressState | None = None,
) -> PlaybackReviewState:
    duration_seconds = max(0, meeting.duration_seconds)
    if status in {"processing", "submitted", "blocked", "local_only", "uploading"}:
        return PlaybackReviewState(
            available=False,
            duration_seconds=duration_seconds,
            unavailable_reason="processing",
            policy_label="Аудио еще готовится",
        )
    if status == "failed":
        return PlaybackReviewState(
            available=False,
            duration_seconds=duration_seconds,
            unavailable_reason="failed",
            policy_label="Аудио недоступно из-за ошибки обработки",
        )
    if status == "deleted_future":
        return PlaybackReviewState(
            available=False,
            duration_seconds=duration_seconds,
            unavailable_reason="deleting",
            policy_label="Аудио удаляется",
        )
    if review_playback is None or review_playback.state == "missing":
        return PlaybackReviewState(
            available=False,
            duration_seconds=duration_seconds,
            unavailable_reason="no_audio",
            policy_label="Аудио недоступно",
        )
    if review_playback.state in {"policy_blocked", "owner_only"}:
        reason = "access_denied" if review_playback.label == "Access required" else "policy_disabled"
        return PlaybackReviewState(
            available=False,
            duration_seconds=duration_seconds,
            unavailable_reason=reason,
            policy_label="Аудио закрыто политикой доступа",
        )
    if review_playback.state == "deleted":
        return PlaybackReviewState(
            available=False,
            duration_seconds=duration_seconds,
            unavailable_reason="deleting",
            policy_label="Аудио удаляется",
        )
    if status not in {"ready", "partial"} or review_playback.state != "available":
        return PlaybackReviewState(
            available=False,
            duration_seconds=duration_seconds,
            unavailable_reason="review_audio_unavailable",
            policy_label="Аудио для проверки недоступно",
        )
    return PlaybackReviewState(
        available=True,
        duration_seconds=duration_seconds,
        unavailable_reason="none",
        playback_path=f"/api/v1/cabinet/meetings/{meeting.id}/playback",
        policy_label="Аудио доступно для проверки",
        source_mode="combined_review_stream",
        included_sources=["local_microphone", "incoming_system"],
    )


def provenance_state(
    *,
    media_revision: MediaRevision | None,
    transcript_segments: Iterable[TranscriptSegment],
    diarization_segments: Iterable[DiarizationSegment],
    dependency: ProcessingDependencyState | None,
) -> MeetingProvenance:
    roles = _unique(
        [source_role_label(row.source_role) for row in transcript_segments]
        + [source_role_label(row.source_role) for row in diarization_segments]
    )
    return MeetingProvenance(
        media_revision_id=media_revision.id if media_revision is not None else None,
        local_media_revision_id=media_revision.local_media_revision_id if media_revision is not None else None,
        source_roles=roles,
        processing_dependency=dependency.dependency if dependency is not None else None,
        content_policy="authorized_detail_only",
    )


def build_review_response(
    meeting: Meeting,
    *,
    media_revision: MediaRevision | None = None,
    result: ProcessingResult | None,
    workflow: ProcessingWorkflow | None,
    transcript_segments: list[TranscriptSegment],
    diarization_segments: list[DiarizationSegment],
    dependency: ProcessingDependencyState | None,
    access: MeetingAccessState | None = None,
    share: SharePanelState | None = None,
    artifacts: list[ArtifactEgressState] | None = None,
    review_playback: ArtifactEgressState | None = None,
    calendar_roster: CalendarRosterReviewState | None = None,
    activity: MeetingActivityResponse | None = None,
    outcome_set: MeetingOutcomeSet | None = None,
    outcome_items: list[MeetingOutcomeItem] | None = None,
) -> MeetingReviewResponse:
    access_state = access or owner_access_state()
    artifact_states = artifacts or []
    item = build_list_item(
        meeting,
        media_revision=media_revision,
        result=result,
        workflow=workflow,
        access=access_state,
        artifacts=artifact_states,
    )
    status = cast(MeetingReviewStatus, item.status)
    notes_truth = notes_action_truth_state(status=status, result=result, outcome_set=outcome_set, outcome_items=outcome_items or [])
    item.notes_available = notes_truth.summary.state == "available"
    item.notes_action_truth = notes_truth
    playback = playback_state(meeting, status, review_playback)
    return MeetingReviewResponse(
        meeting=item,
        provenance=provenance_state(
            media_revision=media_revision,
            transcript_segments=transcript_segments,
            diarization_segments=diarization_segments,
            dependency=dependency,
        ),
        processing=processing_state(meeting, result=result, workflow=workflow),
        transcript=transcript_state(
            language=result.language if result is not None else None,
            transcript_segments=transcript_segments,
            diarization_segments=diarization_segments,
            status=status,
            playback_available=playback.available,
            playback_duration_seconds=playback.duration_seconds,
        ),
        speakers=speaker_state(diarization_segments),
        calendar_roster=calendar_roster,
        notes=notes_state(status),
        notes_action_truth=notes_truth,
        playback=playback,
        governance=governance_summary(access=access_state, artifacts=artifact_states),
        access=access_state,
        share=share,
        artifacts=artifact_states,
        activity=activity,
        deletion_truth_copy=DELETION_TRUTH_COPY,
        assistant=slot_state("Assistant"),
        template=slot_state("Template"),
    )


def _unique(values: Iterable[SourceRoleView]) -> list[SourceRoleView]:
    seen: set[str] = set()
    result: list[SourceRoleView] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
