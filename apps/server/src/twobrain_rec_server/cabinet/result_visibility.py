"""Private, transient evidence for T112; this module never admits an event."""

from __future__ import annotations

import base64
import binascii
import hmac
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from typing import Literal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import (
    IngestAuditEvent,
    MediaRevision,
    Meeting,
    ProcessingResult,
    ProcessingWorkflow,
    UploadSession,
)
from twobrain_rec_server.ingest.media_revisions import source_fingerprint_for_revision
from twobrain_rec_server.processing.results import complete_processing_result_clause
from twobrain_rec_server.product_analytics.milestones import USEFUL_RESULT_TYPES

_PROOF_DOMAIN = "f273-result-view-v1"
_PROOF_MAX_BYTES = 1536
_PROOF_TTL_SECONDS = 600


@dataclass(frozen=True, slots=True)
class ResultViewSource:
    owner_id: UUID
    workspace_id: UUID
    meeting_id: UUID
    media_revision_id: UUID
    source_fingerprint: str
    result_id: UUID
    result_version: int
    deletion_epoch: int
    first_recording_completed: bool | None


@dataclass(frozen=True, slots=True)
class ResultViewBinding:
    source: ResultViewSource
    auth_session_id: UUID
    session_device_id: UUID | None
    block_type: str
    block_digest: str
    outcome_set_id: UUID | None


def _known_time(value: datetime | None) -> bool:
    return isinstance(value, datetime) and value.utcoffset() is not None


def _has_audit(event_types: tuple[str, ...], *, session: bool, started_at: datetime, now: datetime):
    event = IngestAuditEvent
    statement = select(event.id).where(
        event.workspace_id == Meeting.workspace_id,
        event.meeting_id == Meeting.id,
        event.actor_user_id == Meeting.created_by_user_id,
        event.device_id == (UploadSession.device_id if session else Meeting.device_id),
        event.event_type.in_(event_types),
        event.created_at >= started_at,
        event.created_at <= now,
    )
    if session:
        statement = statement.where(
            event.upload_session_id == UploadSession.id,
            event.created_at >= UploadSession.created_at,
            or_(
                event.media_revision_id == MediaRevision.id,
                # The normal initial-session and finalize audit rows have no revision.
                event.media_revision_id.is_(None)
                & event.event_type.in_(("session_created", "finalized")),
            ),
        )
    return statement.correlate(Meeting, MediaRevision, UploadSession).exists()


async def load_result_view_source(
    db: AsyncSession,
    *,
    owner_id: UUID,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID,
    processing_result_id: UUID,
    started_at: datetime | None,
    now: datetime,
) -> ResultViewSource | None:
    """Validate the exact result selected by the authorized render projection.

    The caller owns T113 readiness, access/session/identity/source locks and the
    request budget. A passed date or this source fact alone authorizes no write.
    """
    if not _known_time(started_at) or not _known_time(now) or started_at > now:
        return None
    row = (await db.execute(
        select(Meeting, MediaRevision, ProcessingResult, ProcessingWorkflow)
        .join(MediaRevision, MediaRevision.meeting_id == Meeting.id)
        .join(ProcessingResult, ProcessingResult.media_revision_id == MediaRevision.id)
        .join(ProcessingWorkflow, ProcessingWorkflow.id == ProcessingResult.processing_workflow_id)
        .join(UploadSession, UploadSession.media_revision_id == MediaRevision.id)
        .where(
            Meeting.id == meeting_id,
            Meeting.workspace_id == workspace_id,
            Meeting.created_by_user_id == owner_id,
            Meeting.created_at >= started_at,
            Meeting.created_at <= now,
            Meeting.deletion_state == "none",
            Meeting.deleted_at.is_(None),
            Meeting.deletion_requested_at.is_(None),
            Meeting.deletion_epoch >= 0,
            MediaRevision.id == media_revision_id,
            MediaRevision.workspace_id == workspace_id,
            MediaRevision.source_kind != "initial_recording",
            MediaRevision.accepted_at >= started_at,
            MediaRevision.accepted_at >= Meeting.created_at,
            MediaRevision.accepted_at <= now,
            ProcessingResult.id == processing_result_id,
            ProcessingResult.meeting_id == meeting_id,
            ProcessingResult.workspace_id == workspace_id,
            complete_processing_result_clause(),
            ProcessingResult.result_version >= 1,
            ProcessingResult.imported_at >= MediaRevision.accepted_at,
            ProcessingResult.imported_at <= now,
            ProcessingResult.deletion_epoch_at_start == Meeting.deletion_epoch,
            ProcessingWorkflow.meeting_id == meeting_id,
            ProcessingWorkflow.workspace_id == workspace_id,
            ProcessingWorkflow.media_revision_id == media_revision_id,
            ProcessingWorkflow.deletion_epoch_at_start == Meeting.deletion_epoch,
            UploadSession.workspace_id == workspace_id,
            UploadSession.meeting_id == meeting_id,
            UploadSession.created_by_user_id == owner_id,
            UploadSession.status == "finalized",
            UploadSession.created_at >= started_at,
            UploadSession.created_at >= Meeting.created_at,
            UploadSession.finalized_at >= UploadSession.created_at,
            UploadSession.finalized_at <= now,
            _has_audit(("meeting_created",), session=False, started_at=started_at, now=now),
            _has_audit(
                ("session_created", "media_revision_upload_session_created"),
                session=True, started_at=started_at, now=now,
            ),
            _has_audit(("finalized",), session=True, started_at=started_at, now=now),
        )
        .limit(1)
        .execution_options(populate_existing=True)
    )).first()
    if row is None:
        return None
    meeting, revision, result, workflow = row
    if not re.fullmatch(r"[0-9a-f]{64}", meeting.create_request_fingerprint_sha256 or ""):
        return None
    try:
        fingerprint = source_fingerprint_for_revision(revision)
    except ValueError:
        return None
    if fingerprint != workflow.source_fingerprint:
        return None
    return ResultViewSource(
        owner_id=owner_id, workspace_id=workspace_id, meeting_id=meeting.id,
        media_revision_id=revision.id, source_fingerprint=fingerprint,
        result_id=result.id, result_version=result.result_version, deletion_epoch=meeting.deletion_epoch,
        first_recording_completed=False if revision.source_kind == "manual_upload" else None,
    )


def _proof_payload(binding: ResultViewBinding, issued_at: int) -> str:
    data = {"v": 1, "issued_at": issued_at, "binding": asdict(binding)}
    raw = json.dumps(data, default=str, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def issue_result_view_proof(
    binding: ResultViewBinding, *, secret: str | None, issued_at: datetime,
) -> str | None:
    if (
        not secret or not _known_time(issued_at)
        or binding.block_type not in USEFUL_RESULT_TYPES
        or not re.fullmatch(r"[0-9a-f]{64}", binding.block_digest)
    ):
        return None
    encoded = _proof_payload(binding, int(issued_at.timestamp()))
    signature = hmac.new(secret.encode(), f"{_PROOF_DOMAIN}:{encoded}".encode(), sha256).hexdigest()
    proof = f"{encoded}.{signature}"
    return proof if len(proof) <= _PROOF_MAX_BYTES else None


def verify_result_view_proof(
    proof: str | None, binding: ResultViewBinding, *, secret: str | None, now: datetime,
) -> Literal["valid", "expired", "invalid"]:
    if (
        not secret or not _known_time(now) or not isinstance(proof, str)
        or len(proof) > _PROOF_MAX_BYTES
        or not re.fullmatch(r"[A-Za-z0-9_-]+\.[0-9a-f]{64}", proof)
    ):
        return "invalid"
    encoded, signature = proof.split(".")
    expected_signature = hmac.new(
        secret.encode(), f"{_PROOF_DOMAIN}:{encoded}".encode(), sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return "invalid"
    try:
        payload = json.loads(base64.b64decode(
            encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True,
        ))
    except (ValueError, binascii.Error, UnicodeDecodeError):
        return "invalid"
    if not isinstance(payload, dict) or type(payload.get("issued_at")) is not int:
        return "invalid"
    issued_at = payload["issued_at"]
    if not hmac.compare_digest(encoded, _proof_payload(binding, issued_at)):
        return "invalid"
    age = now.timestamp() - issued_at
    if age < 0:
        return "invalid"
    return "expired" if age >= _PROOF_TTL_SECONDS else "valid"
