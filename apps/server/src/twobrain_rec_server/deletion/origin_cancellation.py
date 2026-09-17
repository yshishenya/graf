"""Owner-scoped cancellation shares a transaction lock with first meeting creation."""

from hashlib import sha256

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import DeletionRequestResponse, OriginCancellationReceipt
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.db.models import Meeting, RecordingOriginCancellation
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY
from twobrain_rec_server.deletion.service import request_meeting_deletion


async def lock_recording_origin(db: AsyncSession, scope: TenantScope, origin: str) -> None:
    # Transaction-scoped, stable across processes; a hash collision only serializes two origins.
    identity = f"{scope.workspace_id}:{scope.user_id}:{origin}".encode()
    key = int.from_bytes(sha256(identity).digest()[:8], "big", signed=True)
    await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


async def origin_cancellation(db: AsyncSession, scope: TenantScope, origin: str):
    return await db.scalar(select(RecordingOriginCancellation).where(
        RecordingOriginCancellation.workspace_id == scope.workspace_id,
        RecordingOriginCancellation.created_by_user_id == scope.user_id,
        RecordingOriginCancellation.local_recording_id == origin,
    ))


async def cancel_recording_origin(
    db: AsyncSession, *, scope: TenantScope, local_recording_id: str,
    confirmation_boundary: str, storage: object,
    local_buffer_expiry_days: int | None, temporal_client: object | None = None,
) -> DeletionRequestResponse | OriginCancellationReceipt:
    if confirmation_boundary != BOUNDED_DELETE_COPY:
        raise ProblemDetail(status=422, code="invalid_deletion_confirmation", title="Invalid deletion confirmation")
    await lock_recording_origin(db, scope, local_recording_id)
    meeting = await db.scalar(select(Meeting).where(
        Meeting.workspace_id == scope.workspace_id,
        Meeting.created_by_user_id == scope.user_id,
        Meeting.local_recording_id == local_recording_id,
    ))
    if meeting is not None:
        receipt = await request_meeting_deletion(
            db, meeting=meeting, actor_user_id=scope.user_id, device_id=scope.device_id,
            confirmation_boundary=confirmation_boundary, storage=storage,
            local_buffer_expiry_days=local_buffer_expiry_days, temporal_client=temporal_client,
        )
        return receipt.model_copy(update={"local_recording_id": local_recording_id})
    cancellation = await origin_cancellation(db, scope, local_recording_id)
    if cancellation is None:
        cancellation = RecordingOriginCancellation(
            workspace_id=scope.workspace_id, created_by_user_id=scope.user_id,
            local_recording_id=local_recording_id,
        )
        db.add(cancellation)
        await db.flush()
    return OriginCancellationReceipt(
        request_id=cancellation.id, local_recording_id=local_recording_id,
        accepted_at=cancellation.accepted_at,
    )
