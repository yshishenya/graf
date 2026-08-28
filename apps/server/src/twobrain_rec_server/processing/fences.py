"""Shared source/deletion fences for asynchronous content operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import DeletionFence, Meeting, ProcessingAuditEvent
from twobrain_rec_server.processing.audit import safe_audit_metadata


@dataclass(frozen=True, slots=True)
class LifecycleFence:
    meeting_id: UUID
    workspace_id: UUID
    deletion_epoch: int
    source_fingerprint: str | None = None


def meeting_is_deleted_or_deleting(meeting: Meeting) -> bool:
    """Treat a tombstone timestamp as active even if state reconciliation lags."""

    return meeting.deleted_at is not None or (meeting.deletion_state or "none") != "none"


def snapshot_fence(meeting: Meeting, *, source_fingerprint: str | None = None) -> LifecycleFence:
    return LifecycleFence(
        meeting_id=meeting.id,
        workspace_id=meeting.workspace_id,
        deletion_epoch=int(meeting.deletion_epoch or 0),
        source_fingerprint=source_fingerprint,
    )


def fence_matches(
    meeting: Meeting,
    fence: LifecycleFence,
    *,
    source_fingerprint: str | None = None,
) -> bool:
    return (
        meeting.id == fence.meeting_id
        and meeting.workspace_id == fence.workspace_id
        and int(meeting.deletion_epoch or 0) == fence.deletion_epoch
        and not meeting_is_deleted_or_deleting(meeting)
        and (
            source_fingerprint is None
            or fence.source_fingerprint is not None
            and fence.source_fingerprint == source_fingerprint
        )
    )


def normalize_db_timestamp(value: datetime | None) -> datetime | None:
    """Normalize database timestamps before aware expiry comparisons."""

    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def is_expired(value: datetime | None, *, now: datetime | None = None) -> bool:
    expiry = normalize_db_timestamp(value)
    if expiry is None:
        return False
    current = now or datetime.now(UTC)
    current = current.replace(tzinfo=UTC) if current.tzinfo is None else current.astimezone(UTC)
    return expiry <= current


async def lock_meeting_fence(db: AsyncSession, *, workspace_id: UUID, meeting_id: UUID) -> Meeting | None:
    return await db.scalar(
        select(Meeting)
        .where(Meeting.workspace_id == workspace_id, Meeting.id == meeting_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


async def ensure_deletion_fence(db: AsyncSession, *, meeting: Meeting) -> DeletionFence:
    row = await db.scalar(
        select(DeletionFence)
        .where(
            DeletionFence.workspace_id == meeting.workspace_id,
            DeletionFence.meeting_id == meeting.id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        row = DeletionFence(
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            epoch=int(meeting.deletion_epoch or 0),
            state="active" if not meeting_is_deleted_or_deleting(meeting) else "deleting",
        )
        db.add(row)
        await db.flush()
    elif row.epoch < int(meeting.deletion_epoch or 0):
        row.epoch = int(meeting.deletion_epoch or 0)
    return row


async def record_stale_lifecycle_event(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    event_type: str,
    metadata: dict[str, object] | None = None,
) -> ProcessingAuditEvent:
    event = ProcessingAuditEvent(
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        event_type=event_type,
        metadata_json=safe_audit_metadata(metadata or {}),
        created_at=datetime.now(UTC),
    )
    db.add(event)
    await db.flush()
    return event
