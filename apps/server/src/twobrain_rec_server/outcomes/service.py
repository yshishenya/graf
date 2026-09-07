from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from twobrain_rec_server.cabinet.speakers import speaker_names_for_result
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    MediaRevision,
    Meeting,
    MeetingOutcomeSet,
    MeetingSpeakerName,
    MeetingSummarySlot,
    ProcessingResult,
    TranscriptSegment,
)
from twobrain_rec_server.domain.speaker_turns import (
    canonical_speaker_model,
    canonical_speech_available,
)
from twobrain_rec_server.domain.statuses import OutcomeSetStatus, ProcessingResultStatus
from twobrain_rec_server.ingest.media_revisions import source_fingerprint_for_revision
from twobrain_rec_server.outcomes.models import PROTOCOL_SCHEMA_VERSION, OutcomeTranscriptSegment
from twobrain_rec_server.outcomes.prompts import canonical_json
from twobrain_rec_server.outcomes.store import project_protocol_wait
from twobrain_rec_server.processing.fences import (
    lock_meeting_fence,
    meeting_is_deleted_or_deleting,
)
from twobrain_rec_server.processing.results import (
    effective_processing_result_query,
    latest_processing_result_query,
    result_is_complete,
    result_is_terminal_input,
    result_source_hash_is_attested,
)
from twobrain_rec_server.processing.store import ProcessingLifecycleBlocked


class SummarySlotDefaultConflict(ValueError):
    """The meeting already has a different persisted default summary type."""


MAX_SUMMARY_STATE_VERSION = 2**63 - 1


class SummaryStateVersionExhausted(RuntimeError):
    """A summary type can no longer advance its signed client version."""


def advance_summary_slot_state_version(slot: MeetingSummarySlot) -> int:
    if slot.state_version >= MAX_SUMMARY_STATE_VERSION:
        raise SummaryStateVersionExhausted("summary_state_version_exhausted")
    slot.state_version += 1
    return slot.state_version


async def ensure_outcomes_for_meeting(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    meeting_id: UUID,
) -> MeetingOutcomeSet | None:
    async with sessionmaker() as db:
        latest_revision = await db.scalar(
            select(MediaRevision)
            .where(
                MediaRevision.meeting_id == meeting_id,
                MediaRevision.status == "accepted",
                MediaRevision.immutable.is_(True),
            )
            .order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc())
        )
        if latest_revision is None:
            return None
        result = await db.scalar(
            effective_processing_result_query(
                workspace_id=latest_revision.workspace_id,
                meeting_id=meeting_id,
                media_revision_id=latest_revision.id,
            )
        )
        if result is None:
            return None
        outcome_set = await ensure_outcomes_for_processing_result(
            db,
            result=result,
            enforce_latest_result=False,
        )
        await db.commit()
        return outcome_set


async def ensure_outcomes_for_processing_result(
    db: AsyncSession,
    *,
    result: ProcessingResult,
    ai_dispatch_planned: bool | None = None,
    enforce_latest_result: bool = True,
) -> MeetingOutcomeSet:
    meeting = await lock_meeting_fence(
        db, workspace_id=result.workspace_id, meeting_id=result.meeting_id
    )
    if meeting is None or meeting_is_deleted_or_deleting(meeting):
        raise ProcessingLifecycleBlocked("meeting_deleting")
    # The meeting lock serializes this projection with revision acceptance. Do
    # not let a result that lost the source race create a new outcome lineage.
    latest_revision = await db.scalar(
        select(MediaRevision)
        .where(
            MediaRevision.workspace_id == result.workspace_id,
            MediaRevision.meeting_id == result.meeting_id,
            MediaRevision.status == "accepted",
            MediaRevision.immutable.is_(True),
        )
        .order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc())
    )
    if (latest_revision.id if latest_revision is not None else None) != result.media_revision_id:
        raise ProcessingLifecycleBlocked("summary_source_revision_stale")
    latest_result = None
    if enforce_latest_result:
        latest_result = await db.scalar(
            latest_processing_result_query(
                workspace_id=result.workspace_id,
                meeting_id=result.meeting_id,
                media_revision_id=result.media_revision_id,
            )
        )
        # A callback may only create or update the lineage for the latest
        # imported row. Meeting-level reconciliation intentionally uses the
        # effective complete result, even when a newer partial row exists.
        if latest_result is None or latest_result.id != result.id:
            raise ProcessingLifecycleBlocked("summary_source_result_stale")
    if result_is_complete(result):
        effective_result = await db.scalar(
            effective_processing_result_query(
                workspace_id=result.workspace_id,
                meeting_id=result.meeting_id,
                media_revision_id=result.media_revision_id,
            )
        )
        if effective_result is None or effective_result.id != result.id:
            raise ProcessingLifecycleBlocked("summary_source_result_stale")
    if (
        latest_result is not None
        and latest_result.id == result.id
        and latest_result.source_result_hash is not None
        and result.source_result_hash is not None
        and latest_result.source_result_hash != result.source_result_hash
    ):
        raise ProcessingLifecycleBlocked("summary_source_result_stale")
    transcript_is_available = canonical_speech_available(result) and result_source_hash_is_attested(result)
    has_transcript_artifact = bool(
        result.transcript_status == "available" and int(result.segment_count or 0) > 0
    )
    if not has_transcript_artifact and not result_is_terminal_input(result):
        raise ProcessingLifecycleBlocked("summary_source_result_stale")
    # Reconciliation must never edit an accepted revision or a published slot.
    slot = await load_meeting_default_slot(
        db, workspace_id=meeting.workspace_id, meeting_id=meeting.id
    )
    current = await load_egress_default_outcome(db, meeting=meeting, slot=slot)
    if current is not None and current.processing_result_id == result.id:
        return current
    return await project_protocol_wait(
        db,
        meeting=meeting,
        result=result,
        source_fingerprint=await _result_source_fingerprint(db, result=result),
        ai_dispatch_planned=bool(ai_dispatch_planned),
        transcript_available=transcript_is_available,
    )


async def _result_source_fingerprint(
    db: AsyncSession,
    *,
    result: ProcessingResult,
) -> str:
    if result.media_revision_id is None:
        return f"result:{result.id}"
    revision = await db.get(MediaRevision, result.media_revision_id)
    if revision is None:
        raise ProcessingLifecycleBlocked("summary_source_revision_unavailable")
    try:
        return source_fingerprint_for_revision(revision)
    except ValueError as exc:
        raise ProcessingLifecycleBlocked("summary_source_revision_unavailable") from exc


async def load_summary_slot(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    template_key: str,
    for_update: bool = False,
) -> MeetingSummarySlot | None:
    query = select(MeetingSummarySlot).where(
        MeetingSummarySlot.workspace_id == workspace_id,
        MeetingSummarySlot.meeting_id == meeting_id,
        MeetingSummarySlot.template_key == template_key,
    )
    if for_update:
        query = query.with_for_update()
    return await db.scalar(query)


async def ensure_summary_slot(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    template_key: str,
    is_meeting_default: bool = False,
    default_resolution_source: str | None = None,
    default_resolution_version: str | None = None,
    default_resolved_at: datetime | None = None,
) -> MeetingSummarySlot:
    slot = await load_summary_slot(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        template_key=template_key,
    )
    if slot is not None:
        return slot
    if is_meeting_default and (
        default_resolution_source is None
        or default_resolution_version is None
        or default_resolved_at is None
    ):
        raise ValueError("default slot requires complete resolver provenance")
    slot = MeetingSummarySlot(
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        template_key=template_key,
        is_meeting_default=is_meeting_default,
        default_resolution_source=default_resolution_source,
        default_resolution_version=default_resolution_version,
        default_resolved_at=default_resolved_at,
    )
    try:
        # The unique slot key is the linearization point for concurrent first
        # ensure requests. Keep the outer transaction usable when another
        # request wins the insert race.
        async with db.begin_nested():
            db.add(slot)
            await db.flush()
    except IntegrityError as exc:
        if "uq_meeting_summary_slots_workspace_meeting_type" not in str(exc):
            raise
        existing = await load_summary_slot(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            template_key=template_key,
        )
        if existing is None:
            raise
        return existing
    return slot


async def load_meeting_default_slot(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    for_update: bool = False,
) -> MeetingSummarySlot | None:
    query = select(MeetingSummarySlot).where(
        MeetingSummarySlot.workspace_id == workspace_id,
        MeetingSummarySlot.meeting_id == meeting_id,
        MeetingSummarySlot.is_meeting_default.is_(True),
    )
    if for_update:
        query = query.with_for_update()
    return await db.scalar(query)


async def mark_meeting_default_slot(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    template_key: str,
    resolution_source: str,
    resolution_version: str,
    resolved_at: datetime,
) -> MeetingSummarySlot:
    """Persist the meeting default once; viewer preferences never participate."""
    meeting = await db.scalar(
        select(Meeting)
        .where(Meeting.workspace_id == workspace_id, Meeting.id == meeting_id)
        .with_for_update()
    )
    if meeting is None:
        raise ValueError("meeting_not_found")

    existing = await load_meeting_default_slot(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        for_update=True,
    )
    if existing is not None:
        if existing.template_key != template_key:
            raise SummarySlotDefaultConflict("summary_default_conflict")
        return existing

    slot = await ensure_summary_slot(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        template_key=template_key,
        is_meeting_default=True,
        default_resolution_source=resolution_source,
        default_resolution_version=resolution_version,
        default_resolved_at=resolved_at,
    )
    if not slot.is_meeting_default:
        slot.is_meeting_default = True
        slot.default_resolution_source = resolution_source
        slot.default_resolution_version = resolution_version
        slot.default_resolved_at = resolved_at
        advance_summary_slot_state_version(slot)
    return slot


async def load_egress_default_outcome(
    db: AsyncSession,
    *,
    meeting: Meeting,
    slot: MeetingSummarySlot | None,
) -> MeetingOutcomeSet | None:
    """Validate the pinned default revision without consulting viewer state."""

    if slot is None or slot.workspace_id != meeting.workspace_id or slot.meeting_id != meeting.id:
        return None
    slot = await db.scalar(
        select(MeetingSummarySlot).where(
            MeetingSummarySlot.id == slot.id,
            MeetingSummarySlot.workspace_id == meeting.workspace_id,
            MeetingSummarySlot.meeting_id == meeting.id,
            MeetingSummarySlot.is_meeting_default.is_(True),
            MeetingSummarySlot.current_binding_class == "verified_complete",
            MeetingSummarySlot.current_outcome_set_id.is_not(None),
        ).execution_options(populate_existing=True)
    )
    if slot is None:
        return None
    outcome = await load_pinned_egress_outcome(
        db,
        meeting=meeting,
        template_key=slot.template_key,
        outcome_set_id=slot.current_outcome_set_id,
    )
    return outcome if outcome is not None and outcome.revision_state == "accepted" else None


async def load_pinned_egress_outcome(
    db: AsyncSession,
    *,
    meeting: Meeting,
    template_key: str,
    outcome_set_id: UUID,
) -> MeetingOutcomeSet | None:
    """Validate one immutable template/revision pair for outward projection."""

    if meeting_is_deleted_or_deleting(meeting):
        return None
    outcome = await db.scalar(
        select(MeetingOutcomeSet)
        .join(Meeting, Meeting.id == MeetingOutcomeSet.meeting_id)
        .where(
            MeetingOutcomeSet.id == outcome_set_id,
            MeetingOutcomeSet.workspace_id == meeting.workspace_id,
            MeetingOutcomeSet.meeting_id == meeting.id,
            MeetingOutcomeSet.template_key == template_key,
            MeetingOutcomeSet.lifecycle_state == "active",
            MeetingOutcomeSet.status == OutcomeSetStatus.AVAILABLE.value,
            MeetingOutcomeSet.protocol_state == "available",
            MeetingOutcomeSet.protocol_schema_version == PROTOCOL_SCHEMA_VERSION,
            MeetingOutcomeSet.revision_state.in_(("accepted", "superseded")),
            MeetingOutcomeSet.accepted_at.is_not(None),
            MeetingOutcomeSet.deletion_epoch_at_start == Meeting.deletion_epoch,
            Meeting.workspace_id == meeting.workspace_id,
            Meeting.deleted_at.is_(None),
            or_(Meeting.deletion_state.is_(None), Meeting.deletion_state == "none"),
        )
        .execution_options(populate_existing=True)
    )
    if outcome is None:
        return None
    document = outcome.protocol_json
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != PROTOCOL_SCHEMA_VERSION
        or sha256(canonical_json(document).encode("utf-8")).hexdigest() != outcome.content_hash
    ):
        return None
    result = await db.scalar(
        select(ProcessingResult).where(
            ProcessingResult.id == outcome.processing_result_id,
            ProcessingResult.workspace_id == meeting.workspace_id,
            ProcessingResult.meeting_id == meeting.id,
            ProcessingResult.status == ProcessingResultStatus.IMPORTED.value,
        ).execution_options(populate_existing=True)
    )
    if not result_source_hash_is_attested(result) or outcome.media_revision_id != result.media_revision_id:
        return None
    return outcome if outcome.source_result_hash == result.source_result_hash else None


async def load_outcome_transcript_segments(
    db: AsyncSession,
    *,
    result: ProcessingResult,
) -> list[OutcomeTranscriptSegment]:
    rows = (
        await db.scalars(
            select(TranscriptSegment)
            .where(
                TranscriptSegment.workspace_id == result.workspace_id,
                TranscriptSegment.meeting_id == result.meeting_id,
                TranscriptSegment.processing_result_id == result.id,
            )
            .order_by(TranscriptSegment.sequence.asc(), TranscriptSegment.start_seconds.asc())
        )
    ).all()
    diarization_rows = (
        await db.scalars(
            select(DiarizationSegment)
            .where(
                DiarizationSegment.workspace_id == result.workspace_id,
                DiarizationSegment.meeting_id == result.meeting_id,
                DiarizationSegment.processing_result_id == result.id,
            )
            .order_by(DiarizationSegment.start_seconds, DiarizationSegment.sequence)
        )
    ).all()
    speaker_names = speaker_names_for_result(
        (
            await db.scalars(
                select(MeetingSpeakerName).where(
                    MeetingSpeakerName.workspace_id == result.workspace_id,
                    MeetingSpeakerName.meeting_id == result.meeting_id,
                )
            )
        ).all(),
        result_imported_at=result.imported_at,
    )
    model = canonical_speaker_model(
        rows,
        diarization_rows,
        processing_result_id=result.id,
        speaker_names=speaker_names,
        source_result_hash=result.source_result_hash,
    )
    segments: list[OutcomeTranscriptSegment] = []
    for turn in model.turns:
        segments.append(
            OutcomeTranscriptSegment(
                segment_id=UUID(turn.source_segment_id),
                sequence=turn.sequence,
                start_seconds=turn.start_seconds,
                end_seconds=turn.end_seconds,
                speaker_label=turn.speaker_label,
                speaker_key=turn.speaker_key,
                provider_speaker_key=turn.provider_speaker_key,
                attribution_state=turn.attribution_state,
                result_state=turn.result_state,
                source_role=turn.source_role,
                text=turn.text,
            )
        )
    return segments
