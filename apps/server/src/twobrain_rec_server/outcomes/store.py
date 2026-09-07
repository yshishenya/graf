from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import Meeting, MeetingOutcomeSet, ProcessingResult
from twobrain_rec_server.outcomes.models import PROTOCOL_SCHEMA_VERSION

# Public provenance name retained for callers; this path stores state, not content.
OUTCOME_GENERATOR_VERSION = "meeting-protocol-wait-v2"


async def project_protocol_wait(
    session: AsyncSession,
    *,
    meeting: Meeting,
    result: ProcessingResult,
    source_fingerprint: str,
    ai_dispatch_planned: bool,
    transcript_available: bool,
) -> MeetingOutcomeSet:
    """Project processing state under the caller's Meeting/source fence.

    Real model candidates and immutable documents belong to ai_service. This
    record has no candidate identity, model attempt, items, or published slot.
    """
    outcome = await session.scalar(
        select(MeetingOutcomeSet).where(
            MeetingOutcomeSet.workspace_id == meeting.workspace_id,
            MeetingOutcomeSet.meeting_id == meeting.id,
            MeetingOutcomeSet.processing_result_id == result.id,
            MeetingOutcomeSet.media_revision_id == result.media_revision_id,
            MeetingOutcomeSet.source_result_hash == result.source_result_hash,
            MeetingOutcomeSet.source_fingerprint == source_fingerprint,
            MeetingOutcomeSet.deletion_epoch_at_start == int(meeting.deletion_epoch or 0),
            MeetingOutcomeSet.generator_version == OUTCOME_GENERATOR_VERSION,
            MeetingOutcomeSet.candidate_id.is_(None),
            MeetingOutcomeSet.revision_state == "candidate",
            MeetingOutcomeSet.lifecycle_state == "active",
            MeetingOutcomeSet.protocol_json.is_(None),
            MeetingOutcomeSet.content_hash.is_(None),
        )
    )
    if outcome is None:
        outcome = MeetingOutcomeSet(
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            processing_result_id=result.id,
            media_revision_id=result.media_revision_id,
            source_result_hash=result.source_result_hash,
            source_fingerprint=source_fingerprint,
            deletion_epoch_at_start=int(meeting.deletion_epoch or 0),
            generator_version=OUTCOME_GENERATOR_VERSION,
            generator_kind="none",
            source_kind="processing_state",
            revision_state="candidate",
            protocol_schema_version=PROTOCOL_SCHEMA_VERSION,
        )
        session.add(outcome)
    waiting = transcript_available and ai_dispatch_planned
    outcome.status = "generating" if waiting else "blocked"
    outcome.protocol_state = "processing" if waiting else "unavailable"
    outcome.failure_reason = (
        None if waiting
        else "summary_generation_unavailable" if transcript_available
        else result.failure_reason or "outcomes_transcript_unavailable"
    )
    outcome.failure_source = None if transcript_available else result.failure_source
    await session.flush()
    return outcome
