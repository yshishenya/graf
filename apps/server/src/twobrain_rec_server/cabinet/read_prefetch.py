"""Per-request batched reads for the cabinet meeting list.

The meeting list renders many per-meeting projections. Every projection helper
keeps its single-meeting query for the detail page, the shared-with-me list, the
embedded list and the API, and consults this prefetch first when the list path
has already batched the same rows for a whole set of meetings.

Nothing here changes a selection rule. Every batch query reproduces the single
helper's workspace fence, filter, ordering and default value; a key that was not
prefetched always falls back to the original single-meeting query.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from twobrain_rec_server.db.models import (
    MediaRevision,
    Meeting,
    MeetingArtifactPolicy,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeSet,
    MeetingShareGrant,
    MeetingSummarySlot,
    PlaybackNormalizationJob,
    ProcessingResult,
    ProcessingWorkflow,
    RecordingCalendarContextLink,
    TrackArtifact,
    UploadSession,
    WorkspaceMembership,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sqlalchemy.ext.asyncio import AsyncSession

    from twobrain_rec_server.cabinet.access import ShareRecipientAccessProof

_READ_PREFETCH_KEY = "cabinet_meeting_list_read_prefetch"


@dataclass(slots=True)
class CabinetReadPrefetch:
    """Batched rows shared by every per-meeting projection in one list read.

    A key that is present means the row was fetched for that meeting (possibly
    ``None`` when the single helper would also find nothing). A missing key means
    "not prefetched" and keeps the original single-meeting query in charge.
    """

    workspace_id: UUID
    viewer_user_id: UUID
    recipient_proof: ShareRecipientAccessProof | None = None

    # cabinet.queries._latest_media_revision
    media_revisions: dict[UUID, MediaRevision | None] = field(default_factory=dict)
    # cabinet.queries._latest_workflow, keyed by (meeting_id, media_revision_id)
    workflows: dict[tuple[UUID, UUID | None], ProcessingWorkflow | None] = field(
        default_factory=dict
    )
    # cabinet.queries._latest_result, keyed by (meeting_id, media_revision_id)
    results: dict[tuple[UUID, UUID | None], ProcessingResult | None] = field(
        default_factory=dict
    )
    # cabinet.egress._effective_complete_result, keyed by meeting_id
    effective_results: dict[UUID, ProcessingResult | None] = field(default_factory=dict)
    # cabinet.egress.current_outcome_set resolution, keyed by
    # (meeting_id, template_key); the value is the validated (outcome, result)
    # pair or None when the single helper would resolve nothing.
    outcome_resolutions: dict[
        tuple[UUID, str | None], tuple[MeetingOutcomeSet, ProcessingResult] | None
    ] = field(default_factory=dict)
    # cabinet.egress._latest_accepted_media_revision, keyed by meeting_id
    accepted_media_revisions: dict[UUID, MediaRevision | None] = field(default_factory=dict)
    # cabinet.egress.resolve_artifact_policy, keyed by meeting_id
    artifact_policies: dict[UUID, MeetingArtifactPolicy | None] = field(default_factory=dict)
    # ingest.store.archive_audio_for_revision, keyed by (meeting_id, media_revision_id)
    archive_audio: dict[tuple[UUID, UUID], bool] = field(default_factory=dict)
    # cabinet.egress._normalization_job_for_revision,
    # keyed by (meeting_id, media_revision_id)
    normalization_jobs: dict[tuple[UUID, UUID], PlaybackNormalizationJob | None] = field(
        default_factory=dict
    )
    # cabinet.egress._validated_canonical_artifact, keyed by job id
    canonical_artifacts: dict[UUID, TrackArtifact | None] = field(default_factory=dict)
    # cabinet.egress._transcript_visibility_confirmed presence check,
    # keyed by processing_result_id
    result_media_presence: dict[UUID, bool] = field(default_factory=dict)
    # cabinet.queries._latest_upload_progress, keyed by meeting_id
    upload_sessions: dict[UUID, UploadSession | None] = field(default_factory=dict)
    # accepted UploadPart byte totals, keyed by upload session id
    upload_part_bytes: dict[UUID, int] = field(default_factory=dict)
    # cabinet.queries._calendar_context_link, keyed by meeting_id
    calendar_links: dict[UUID, RecordingCalendarContextLink | None] = field(
        default_factory=dict
    )
    # cabinet.queries._previous_recurring_meeting candidate, keyed by meeting_id
    previous_links: dict[UUID, tuple[RecordingCalendarContextLink, Meeting] | None] = field(
        default_factory=dict
    )
    # cabinet.outcomes.progress summary slot, keyed by (meeting_id, template_key)
    summary_slots: dict[tuple[UUID, str | None], MeetingSummarySlot | None] = field(
        default_factory=dict
    )
    # outcomes.service.load_pinned_egress_outcome, keyed by
    # (meeting_id, outcome_set_id)
    pinned_outcomes: dict[UUID, MeetingOutcomeSet | None] = field(default_factory=dict)
    # cabinet.outcomes.progress.latest_summary_attempt, keyed by
    # (meeting_id, template_key, processing_result_id, media_revision_id)
    summary_attempts: dict[
        tuple[UUID, str, UUID, UUID | None], MeetingOutcomeGenerationAttempt | None
    ] = field(default_factory=dict)
    # Verified recipient e-mails, keyed by viewer user id (None means unread).
    viewer_verified_emails: dict[UUID, tuple[str, ...]] = field(default_factory=dict)
    # cabinet.access.active_workspace_membership, keyed by (workspace_id, user_id)
    memberships: dict[tuple[UUID, UUID], WorkspaceMembership | None] = field(
        default_factory=dict
    )
    # cabinet.access.active_user_grant, keyed by meeting_id
    user_grants: dict[UUID, MeetingShareGrant | None] = field(default_factory=dict)
    # cabinet.access workspace audience grant, keyed by meeting_id
    workspace_grants: dict[UUID, MeetingShareGrant | None] = field(default_factory=dict)
    # cabinet.access full-meeting workspace audience grant, keyed by meeting_id
    full_meeting_workspace_grants: dict[UUID, MeetingShareGrant | None] = field(
        default_factory=dict
    )


def install_read_prefetch(db: AsyncSession, prefetch: CabinetReadPrefetch) -> None:
    db.info[_READ_PREFETCH_KEY] = prefetch


def clear_read_prefetch(db: AsyncSession) -> None:
    db.info.pop(_READ_PREFETCH_KEY, None)


def active_read_prefetch(db: AsyncSession) -> CabinetReadPrefetch | None:
    prefetch = db.info.get(_READ_PREFETCH_KEY)
    return prefetch if isinstance(prefetch, CabinetReadPrefetch) else None
