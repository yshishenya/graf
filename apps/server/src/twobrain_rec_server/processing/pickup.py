from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.billing.entitlements import (
    effective_plan_code,
    entitlement_for_plan,
    processing_admission,
)
from twobrain_rec_server.billing.usage import (
    QuotaExceeded,
    moscow_window_for,
    reserve_free_usage,
)
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    FreeUsageWindow,
    MediaRevision,
    Meeting,
    UploadSession,
    UsageReservation,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.domain.statuses import MeetingStatus, ProcessingStatus
from twobrain_rec_server.ingest.media_revisions import source_fingerprint_for_revision
from twobrain_rec_server.processing import reasons, store
from twobrain_rec_server.processing.fences import meeting_is_deleted_or_deleting
from twobrain_rec_server.processing.store import ProcessingLifecycleBlocked
from twobrain_rec_server.workflows.temporal_client import (
    cancel_workflow_best_effort,
    connect_temporal_client,
    processing_workflow_id,
    start_processing_workflow,
)

OPEN_WORKFLOW_STATUSES = {
    ProcessingStatus.STARTING.value,
    ProcessingStatus.WORKFLOW_STARTED.value,
    ProcessingStatus.SUBMITTING.value,
    ProcessingStatus.SUBMITTED.value,
    ProcessingStatus.POLLING.value,
    ProcessingStatus.IMPORTING.value,
    ProcessingStatus.FAILED_RETRYABLE.value,
}


@dataclass(slots=True)
class ProcessingPickupResult:
    accepted: bool
    started_count: int = 0
    reused_count: int = 0
    blocked_count: int = 0
    meeting_ids: list[UUID] = field(default_factory=list)


async def pick_up_processing(
    *,
    db: AsyncSession,
    settings: Settings,
    workspace_id: UUID,
    meeting_id: UUID | None = None,
    limit: int = 25,
    temporal_client: object | None = None,
    tenant_scope: TenantScope | None = None,
    archive_audio: bool | None = None,
) -> ProcessingPickupResult:
    if tenant_scope is not None:
        await apply_tenant_scope(db, tenant_scope, context_kind="worker")
    meetings = await _candidate_meetings(db, workspace_id=workspace_id, meeting_id=meeting_id, limit=limit)
    result = ProcessingPickupResult(accepted=True)
    if not meetings:
        return result
    temporal_unavailable = False
    if temporal_client is None:
        if not settings.temporal_address:
            temporal_unavailable = True
        else:
            try:
                temporal_client = await connect_temporal_client(settings)
            except Exception:
                temporal_unavailable = True

    for meeting in meetings:
        meeting_archive_audio = await _archive_audio_for_meeting(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting.id,
            requested=archive_audio,
        )
        expected_meeting_status = meeting.status
        if meeting_is_deleted_or_deleting(meeting):
            result.blocked_count += 1
            continue
        media_revision = await store.latest_media_revision_for_meeting(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting.id,
        )
        media_revision_id = media_revision.id if media_revision is not None else None
        source_fingerprint = None
        if media_revision is not None:
            try:
                source_fingerprint = source_fingerprint_for_revision(media_revision)
            except ValueError:
                await _block_meeting(
                    db,
                    meeting,
                    media_revision_id=media_revision.id,
                    source_fingerprint=None,
                    reason_code=reasons.BLOCKED_MISSING_ARTIFACTS,
                    expected_meeting_status=expected_meeting_status,
                    expected_media_revision_id=media_revision.id,
                    archive_audio=meeting_archive_audio,
                )
                result.blocked_count += 1
                continue
        if temporal_unavailable:
            await _block_meeting(
                db,
                meeting,
                media_revision_id=media_revision_id,
                source_fingerprint=source_fingerprint,
                reason_code=reasons.BLOCKED_TEMPORAL_UNAVAILABLE,
                expected_meeting_status=expected_meeting_status,
                expected_media_revision_id=media_revision_id,
                archive_audio=meeting_archive_audio,
            )
            result.blocked_count += 1
            continue
        workflow = await store.get_processing_workflow(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting.id,
            media_revision_id=media_revision_id,
            source_fingerprint=source_fingerprint,
            active_only=True,
        )
        if workflow is not None and workflow.status in OPEN_WORKFLOW_STATUSES:
            result.reused_count += 1
            result.meeting_ids.append(meeting.id)
            await store.record_processing_audit_event(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting.id,
                processing_workflow_id=workflow.id,
                event_type="workflow_duplicate_reused",
                metadata={"workflow_id": workflow.workflow_id, "reason_code": reasons.DUPLICATE_WORKFLOW_REUSED},
            )
            continue
        if meeting.status != MeetingStatus.INGESTED_PENDING_PROCESSING.value:
            await _block_meeting(
                db,
                meeting,
                media_revision_id=media_revision_id,
                source_fingerprint=source_fingerprint,
                reason_code=reasons.BLOCKED_INVALID_MEETING_STATE,
                expected_meeting_status=expected_meeting_status,
                expected_media_revision_id=media_revision_id,
                archive_audio=meeting_archive_audio,
            )
            result.blocked_count += 1
            continue
        if media_revision_id is None:
            await _block_meeting(
                db,
                meeting,
                media_revision_id=None,
                source_fingerprint=None,
                reason_code=reasons.BLOCKED_MISSING_ARTIFACTS,
                expected_meeting_status=expected_meeting_status,
                archive_audio=meeting_archive_audio,
            )
            result.blocked_count += 1
            continue
        source = await store.load_processing_source(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting.id,
            media_revision_id=media_revision_id,
        )
        if source is None:
            await _block_meeting(
                db,
                meeting,
                media_revision_id=media_revision_id,
                source_fingerprint=source_fingerprint,
                reason_code=reasons.BLOCKED_MISSING_ARTIFACTS,
                expected_meeting_status=expected_meeting_status,
                expected_media_revision_id=media_revision_id,
                archive_audio=meeting_archive_audio,
            )
            result.blocked_count += 1
            continue

        workflow_id = processing_workflow_id(media_revision_id)
        try:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting.id,
                media_revision_id=media_revision_id,
                workflow_id=workflow_id,
                status=ProcessingStatus.STARTING,
                source_fingerprint=source_fingerprint,
                expected_meeting_status=MeetingStatus.INGESTED_PENDING_PROCESSING.value,
                expected_media_revision_id=media_revision_id,
                archive_audio=meeting_archive_audio,
                deadline_seconds=settings.processing_recovery_deadline_seconds,
            )
        except ProcessingLifecycleBlocked:
            await db.rollback()
            result.blocked_count += 1
            continue

        usage_admitted = await _reserve_processing_usage(
            db,
            workspace_id=workspace_id,
            media_revision=media_revision,
            archive_audio=meeting_archive_audio,
        )
        if usage_admitted is False:
            await _block_meeting(
                db,
                meeting,
                media_revision_id=media_revision_id,
                source_fingerprint=source_fingerprint,
                reason_code=reasons.BLOCKED_FREE_PROCESSING_EXHAUSTED,
                expected_meeting_status=expected_meeting_status,
                expected_media_revision_id=media_revision_id,
                archive_audio=meeting_archive_audio,
            )
            result.blocked_count += 1
            continue
        try:
            started = await start_processing_workflow(
                temporal_client=temporal_client,
                settings=settings,
                meeting_id=meeting.id,
                media_revision_id=media_revision_id,
                workspace_id=workspace_id,
                tenant_scope=tenant_scope,
                archive_audio=meeting_archive_audio,
            )
        except Exception:
            await cancel_workflow_best_effort(temporal_client, processing_workflow_id(media_revision_id))
            if usage_admitted:
                await store.release_processing_usage_reservation(
                    db,
                    workspace_id=workspace_id,
                    media_revision_id=media_revision_id,
                )
            await _block_meeting(
                db,
                meeting,
                media_revision_id=media_revision_id,
                source_fingerprint=source_fingerprint,
                reason_code=reasons.BLOCKED_TEMPORAL_UNAVAILABLE,
                expected_meeting_status=expected_meeting_status,
                expected_media_revision_id=media_revision_id,
                archive_audio=meeting_archive_audio,
            )
            result.blocked_count += 1
            continue
        try:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting.id,
                media_revision_id=media_revision_id,
                workflow_id=started.workflow_id,
                workflow_run_id=started.run_id,
                status=ProcessingStatus.WORKFLOW_STARTED,
                source_fingerprint=source_fingerprint,
                expected_meeting_status=MeetingStatus.INGESTED_PENDING_PROCESSING.value,
                expected_media_revision_id=media_revision_id,
                archive_audio=meeting_archive_audio,
                deadline_seconds=settings.processing_recovery_deadline_seconds,
            )
        except ProcessingLifecycleBlocked:
            await db.rollback()
            await cancel_workflow_best_effort(temporal_client, started.workflow_id)
            if usage_admitted:
                await store.release_processing_usage_reservation(
                    db,
                    workspace_id=workspace_id,
                    media_revision_id=media_revision_id,
                )
            result.blocked_count += 1
            continue
        event_type = "workflow_duplicate_reused" if started.reused else "workflow_started"
        await store.record_processing_audit_event(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting.id,
            processing_workflow_id=workflow.id,
            event_type=event_type,
            metadata={"workflow_id": workflow.workflow_id, "started_count": 1},
        )
        if started.reused:
            result.reused_count += 1
        else:
            result.started_count += 1
        result.meeting_ids.append(meeting.id)
    return result


async def _reserve_processing_usage(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    media_revision: MediaRevision,
    archive_audio: bool,
) -> UsageReservation | None | bool:
    """Reserve Free seconds once, while leaving paid/trial processing unlimited."""
    duration_seconds = media_revision.duration_seconds
    if not isinstance(duration_seconds, int) or isinstance(duration_seconds, bool) or duration_seconds <= 0:
        return False
    now = datetime.now(UTC)
    subscription = await db.scalar(
        select(WorkspaceSubscription)
        .where(WorkspaceSubscription.workspace_id == workspace_id)
        .with_for_update()
    )
    effective_plan = effective_plan_code(
        plan_code=(subscription.plan_code if subscription is not None else "free"),
        state=(subscription.state if subscription is not None else "free"),
        now=now,
        paid_through=subscription.paid_through if subscription is not None else None,
        trial_ends_at=subscription.trial_ends_at if subscription is not None else None,
    )
    entitlement = entitlement_for_plan(plan_code=effective_plan)
    window_start, _ = moscow_window_for(now)
    window = await db.scalar(
        select(FreeUsageWindow).where(
            FreeUsageWindow.workspace_id == workspace_id,
            FreeUsageWindow.window_start == window_start,
        )
    )
    committed = int(window.committed_seconds) if window is not None else 0
    admitted, _reason = processing_admission(
        entitlement=entitlement,
        committed_free_seconds=committed,
        accepted_seconds=duration_seconds,
        save_audio=archive_audio,
    )
    if not admitted:
        return False
    if entitlement.processing_unlimited:
        return None
    reservation_key = f"processing:{media_revision.id}"
    try:
        reservation = await reserve_free_usage(
            db,
            workspace_id=workspace_id,
            reservation_key=reservation_key,
            declared_seconds=duration_seconds,
            now=now,
            expires_at=now + timedelta(hours=24),
        )
    except QuotaExceeded:
        await db.rollback()
        return False
    await db.commit()
    return reservation


async def _candidate_meetings(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID | None,
    limit: int,
) -> list[Meeting]:
    query = select(Meeting).where(
        Meeting.workspace_id == workspace_id,
        Meeting.deleted_at.is_(None),
        (Meeting.deletion_state.is_(None) | (Meeting.deletion_state == "none")),
    )
    if meeting_id is not None:
        query = query.where(Meeting.id == meeting_id)
    else:
        query = query.where(Meeting.status == MeetingStatus.INGESTED_PENDING_PROCESSING.value).limit(limit)
    return list(await db.scalars(query))


async def _block_meeting(
    db: AsyncSession,
    meeting: Meeting,
    *,
    media_revision_id: UUID | None = None,
    source_fingerprint: str | None = None,
    reason_code: str,
    expected_meeting_status: str | None = None,
    expected_media_revision_id: UUID | None = None,
    archive_audio: bool = True,
) -> None:
    workflow_ref = media_revision_id or meeting.id
    try:
        workflow = await store.upsert_processing_workflow(
            db,
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            media_revision_id=media_revision_id,
            workflow_id=processing_workflow_id(workflow_ref),
            status=ProcessingStatus.BLOCKED,
            reason_code=reason_code,
            source_fingerprint=source_fingerprint,
            expected_meeting_status=expected_meeting_status,
            expected_media_revision_id=expected_media_revision_id,
            archive_audio=archive_audio,
        )
    except ProcessingLifecycleBlocked:
        await db.rollback()
        return
    await store.record_processing_audit_event(
        db,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        processing_workflow_id=workflow.id,
        event_type="processing_blocked",
        metadata={"reason_code": reason_code, "workflow_id": workflow.workflow_id},
    )


async def _archive_audio_for_meeting(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    requested: bool | None,
) -> bool:
    """Resolve the persisted upload choice before creating a workflow.

    The finalized upload session is authoritative.  The optional pickup value
    is only a compatibility fallback for legacy meetings without a finalized
    session; it must not let a later retry silently change custody policy.
    """

    persisted = await db.scalar(
        select(UploadSession.archive_audio)
        .where(
            UploadSession.workspace_id == workspace_id,
            UploadSession.meeting_id == meeting_id,
            UploadSession.status == "finalized",
        )
        .order_by(UploadSession.created_at.desc(), UploadSession.id.desc())
    )
    if persisted is not None:
        return bool(persisted)
    return True if requested is None else requested
