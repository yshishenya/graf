"""Private, transient evidence for T112; this module never admits an event."""

from __future__ import annotations

import base64
import binascii
import hmac
import json
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.schemas import (
    MeetingReviewResponse,
    NotesActionCategoryState,
    TranscriptSegmentView,
    TranscriptSpeakerTurnView,
)
from twobrain_rec_server.auth.context import AuthenticatedPrincipal
from twobrain_rec_server.cabinet.meeting_protocol import EMPTY
from twobrain_rec_server.cabinet.result_projection_budget import (
    _FIELD_BYTES,
    _TOTAL_BYTES,
    _TOTAL_ROWS,
)
from twobrain_rec_server.db.models import (
    IngestAuditEvent,
    MediaRevision,
    Meeting,
    MeetingOutcomeSet,
    ProcessingResult,
    ProcessingWorkflow,
    UploadSession,
)
from twobrain_rec_server.ingest.media_revisions import source_fingerprint_for_revision
from twobrain_rec_server.outcomes.templates import OUTCOME_CATEGORIES, built_in_template_for_version
from twobrain_rec_server.processing.fences import lock_meeting_fence
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


@dataclass(frozen=True, slots=True)
class ResultViewRenderSelection:
    owner_id: UUID
    workspace_id: UUID
    meeting_id: UUID
    media_revision_id: UUID
    source_fingerprint: str
    deletion_epoch: int
    transcript: tuple[UUID, int] | None
    outcome: tuple[UUID, UUID, int] | None


def matching_render_bindings(review, selection, bindings, *, owner):
    if not isinstance(selection, ResultViewRenderSelection):
        return {}
    matched = {}
    for key, block_type, text in result_view_text_blocks(review, owner=owner):
        owner.checkpoint()
        binding = bindings.get(key)
        if binding is None or binding.block_type != block_type:
            continue
        source = binding.source
        if (
            (source.owner_id, source.workspace_id, source.meeting_id, source.media_revision_id,
             source.source_fingerprint, source.deletion_epoch)
            != (selection.owner_id, selection.workspace_id, selection.meeting_id,
                selection.media_revision_id, selection.source_fingerprint, selection.deletion_epoch)
        ):
            continue
        reference = ((source.result_id, source.result_version) if binding.outcome_set_id is None
                     else (binding.outcome_set_id, source.result_id, source.result_version))
        if reference != (selection.transcript if binding.outcome_set_id is None else selection.outcome):
            continue
        digest = result_view_block_digest(
            source, block_type=block_type, texts=[text], outcome_set_id=binding.outcome_set_id,
        )
        owner.checkpoint()
        if digest == binding.block_digest:
            matched[key] = binding
    owner.checkpoint()
    return matched


def rendered_transcript_rows(
    review: MeetingReviewResponse,
) -> list[TranscriptSegmentView | TranscriptSpeakerTurnView]:
    return (
        review.transcript.speaker_turns or review.transcript.segments
        if review.transcript.available and review.transcript.search_enabled
        else []
    )


def ordered_outcome_sections(review: MeetingReviewResponse):
    titles = {
        "summary": "Summary", "key_points": "Key points", "decisions": "Decisions",
        "action_items": "Action Items", "followups": "Follow-ups", "risks": "Risks",
        "questions": "Questions", "evidence": "Evidence",
    }
    definition = built_in_template_for_version(
        review.template.reason, review.template.template_version or 1,
    )
    # Personal and historical unknown templates use the stable canonical order.
    order = definition.sections if definition is not None else OUTCOME_CATEGORIES
    return [(key, titles[key], getattr(review.notes_action_truth, key)) for key in order]


def rendered_outcome_items(state: NotesActionCategoryState):
    return [item for item in state.items if item.text] if state.state == "available" else []


def protocol_sections(document):
    for key, title, empty in (
        ("executive_summary", "Главное", "Краткие итоги не зафиксированы."),
        ("decisions", "Принятые решения", EMPTY["Принятые решения"]),
        ("action_items", "Задачи", "Задачи не зафиксированы."),
        ("open_questions", "Открытые вопросы и следующие шаги", EMPTY["Открытые вопросы и следующие шаги"]),
    ):
        rows = document[key]
        if key == "open_questions":
            rows = rows + document["next_steps"]
        yield key, title, empty, rows


def protocol_topic_parts(topic):
    for key, title in (("outcome", "Итог"), ("context", "Контекст"),
                       ("discussion", "Обсуждение"), ("proposals", "Предложения")):
        if topic[key]:
            yield key, title, topic[key]


def protocol_row_text(row):
    return row.get("text", row.get("task"))


def result_view_text_blocks(review: MeetingReviewResponse, *, owner=None) -> list[tuple[str, str, str]]:
    """Transient candidate bodies, not evidence of visibility or permission to admit."""
    blocks = []
    candidate_count = raw_bytes = 0

    def add(key, block_type, text):
        nonlocal candidate_count, raw_bytes
        if owner is not None:
            owner.checkpoint()
            candidate_count += 1
            if candidate_count > _TOTAL_ROWS:
                owner._refuse()
            if isinstance(text, str):
                # Bound the old product review before encoding, even if DB text shrank.
                if len(text) > _FIELD_BYTES:
                    owner._refuse()
                size = len(text.encode("utf-8"))
                raw_bytes += size
                if size > _FIELD_BYTES or raw_bytes > _TOTAL_BYTES:
                    owner._refuse()
            owner.checkpoint()
        if isinstance(text, str) and text.strip():
            blocks.append((key, block_type, text))
        if owner is not None:
            owner.checkpoint()

    for index, row in enumerate(rendered_transcript_rows(review)):
        add(f"transcript:{index}", "transcript", row.text)
    protocol = review.notes_action_truth.protocol
    if protocol is not None:
        if owner is not None and any(len(protocol[key]) > _TOTAL_ROWS for key in ("open_questions", "next_steps")):
            owner._refuse()  # protocol_sections concatenates these two lists.
        for key, _, _, rows in protocol_sections(protocol):
            block_type = "summary" if key == "executive_summary" else (
                "action_items" if key == "action_items" else "outcome"
            )
            for index, row in enumerate(rows):
                add(f"protocol:{key}:{index}", block_type, protocol_row_text(row))
        for topic_index, topic in enumerate(protocol["topics"]):
            if owner is not None:
                owner.checkpoint()
            for key, _, rows in protocol_topic_parts(topic):
                for index, row in enumerate(rows):
                    add(f"protocol:topic:{topic_index}:{key}:{index}", "outcome", protocol_row_text(row))
        for index, row in enumerate(protocol["notes"]):
            add(f"protocol:notes:{index}", "outcome", protocol_row_text(row))
    else:
        for key, _, state in ordered_outcome_sections(review):
            block_type = key if key in {"summary", "action_items"} else "outcome"
            index = 0
            for item in state.items if state.state == "available" else ():
                if owner is not None:
                    owner.checkpoint()
                if item.text:
                    add(f"outcome:{key}:{index}", block_type, item.text)
                    index += 1
    return blocks


def result_view_block_digest(
    source: ResultViewSource, *, block_type: str, texts: Sequence[str],
    outcome_set_id: UUID | None = None,
) -> str | None:
    if block_type not in USEFUL_RESULT_TYPES or isinstance(texts, str):
        return None
    body = [text for text in texts if text.strip()]
    if not body:
        return None
    data = {
        "type": block_type, "result_id": str(source.result_id),
        "result_version": source.result_version, "texts": body,
    }
    if outcome_set_id is not None:
        data["outcome_set_id"] = str(outcome_set_id)
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


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


async def load_result_view_bindings(
    db: AsyncSession,
    *,
    review: MeetingReviewResponse,
    owner_id: UUID,
    workspace_id: UUID,
    auth_session_id: UUID,
    session_device_id: UUID | None,
    started_at: datetime | None,
    now: datetime,
) -> dict[str, ResultViewBinding]:
    """Bind bodies of the caller's fresh authorized get_cabinet_meeting_review().

    The caller still owns current principal/access, T113 fences and budgets.
    This read neither proves visibility nor admits an event.
    """
    if (
        review.access is None or review.access.state != "owner" or not review.access.can_view
        or not review.access.can_view_full_meeting or review.provenance.media_revision_id is None
        or not isinstance(auth_session_id, UUID)
        or not _known_time(started_at) or not _known_time(now) or started_at > now
    ):
        return {}
    owner = getattr(db.sync_session, "_projection_owner", None)
    blocks = result_view_text_blocks(review, owner=owner)
    selections = []
    result_ids = {row.processing_result_id for row in rendered_transcript_rows(review)}
    if len(result_ids) == 1 and None not in result_ids:
        selections.append(("transcript", result_ids.pop(), None, None))
    if (
        review.template.outcome_set_id is not None
        and review.notes_action_truth.source_basis == "stored_output"
        and any(block_type != "transcript" for _, block_type, _ in blocks)
    ):
        outcome = (await db.execute(select(
            MeetingOutcomeSet.processing_result_id, MeetingOutcomeSet.deletion_epoch_at_start,
        ).where(
            MeetingOutcomeSet.id == review.template.outcome_set_id,
            MeetingOutcomeSet.workspace_id == workspace_id,
            MeetingOutcomeSet.meeting_id == review.meeting.meeting_id,
            MeetingOutcomeSet.media_revision_id == review.provenance.media_revision_id,
            MeetingOutcomeSet.lifecycle_state == "active",
            MeetingOutcomeSet.status.in_(("available", "partial")),
        ))).first()
        if outcome is not None:
            selections.append((
                "outcome", outcome.processing_result_id, review.template.outcome_set_id,
                outcome.deletion_epoch_at_start,
            ))
    bindings = {}
    for kind, result_id, outcome_id, epoch in selections:
        source = await load_result_view_source(
            db, owner_id=owner_id, workspace_id=workspace_id,
            meeting_id=review.meeting.meeting_id, media_revision_id=review.provenance.media_revision_id,
            processing_result_id=result_id, started_at=started_at, now=now,
        )
        if source is None or (outcome_id is not None and epoch != source.deletion_epoch):
            continue
        for key, block_type, text in blocks:
            if owner is not None:
                owner.checkpoint()
            if key.startswith("transcript:") != (kind == "transcript"):
                continue
            digest = result_view_block_digest(
                source, block_type=block_type, texts=[text], outcome_set_id=outcome_id,
            )
            if owner is not None:
                owner.checkpoint()
            if digest is not None:
                bindings[key] = ResultViewBinding(
                    source=source, auth_session_id=auth_session_id, session_device_id=session_device_id,
                    block_type=block_type, block_digest=digest, outcome_set_id=outcome_id,
                )
    return bindings


async def load_fresh_result_view_bindings(
    db: AsyncSession, *, principal: AuthenticatedPrincipal, workspace_id: UUID,
    meeting_id: UUID, started_at: datetime,
    selected_summary_template_key: str | None = None, source_result_id: UUID | None = None,
    rendered_review: MeetingReviewResponse | None = None, rendered_selection=None,
) -> dict[str, ResultViewBinding]:
    """Read under the admission owner's locked auth/session and bounded transaction.

    The owner supplies a fresh session and holds its T113/access fences through
    commit. This helper neither opens readiness nor commits; no product write or
    external storage operation is needed to verify the selected text.
    """
    from twobrain_rec_server.cabinet.queries import get_cabinet_meeting_review

    meeting = await lock_meeting_fence(db, workspace_id=workspace_id, meeting_id=meeting_id)
    if (
        meeting is None or meeting.created_by_user_id != principal.user_id
        or meeting.deletion_state != "none" or meeting.deleted_at is not None
        or meeting.deletion_requested_at is not None
    ):
        return {}
    review = await get_cabinet_meeting_review(
        db, workspace_id=workspace_id, meeting_id=meeting_id, viewer_user_id=principal.user_id,
        selected_summary_template_key=selected_summary_template_key,
        source_result_id=source_result_id, storage=None,
    )
    if review is None:
        return {}
    bindings = await load_result_view_bindings(
        db, review=review, owner_id=principal.user_id, workspace_id=workspace_id,
        auth_session_id=principal.session_id, session_device_id=principal.session_device_id,
        started_at=started_at, now=datetime.now(UTC),
    )
    if rendered_review is not None:
        owner = getattr(db.sync_session, "_projection_owner", None)
        return (matching_render_bindings(rendered_review, rendered_selection, bindings, owner=owner)
                if owner is not None else {})
    return bindings


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


def _decode_result_view_proof(proof, *, secret, now):
    if (
        not secret or not _known_time(now) or not isinstance(proof, str)
        or len(proof) > _PROOF_MAX_BYTES
        or not re.fullmatch(r"[A-Za-z0-9_-]+\.[0-9a-f]{64}", proof)
    ):
        return None
    encoded, signature = proof.split(".")
    expected_signature = hmac.new(
        secret.encode(), f"{_PROOF_DOMAIN}:{encoded}".encode(), sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return None
    try:
        payload = json.loads(base64.b64decode(
            encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True,
        ))
    except (ValueError, binascii.Error, UnicodeDecodeError, RecursionError):
        return None
    if (not isinstance(payload, dict) or set(payload) != {"v", "issued_at", "binding"}
            or type(payload["v"]) is not int or payload["v"] != 1
            or type(payload["issued_at"]) is not int or not isinstance(payload["binding"], dict)):
        return None
    issued_at = payload["issued_at"]
    try:
        if now.timestamp() - issued_at < 0:
            return None
    except OverflowError:
        return None
    return encoded, issued_at


def result_view_proof_age(proof, *, secret, now) -> Literal["valid", "expired", "invalid"]:
    decoded = _decode_result_view_proof(proof, secret=secret, now=now)
    if decoded is None:
        return "invalid"
    return "expired" if now.timestamp() - decoded[1] >= _PROOF_TTL_SECONDS else "valid"


def verify_result_view_proof(
    proof: str | None, binding: ResultViewBinding, *, secret: str | None, now: datetime,
) -> Literal["valid", "expired", "invalid"]:
    decoded = _decode_result_view_proof(proof, secret=secret, now=now)
    if decoded is None:
        return "invalid"
    encoded, issued_at = decoded
    if not hmac.compare_digest(encoded, _proof_payload(binding, issued_at)):
        return "invalid"
    return "expired" if now.timestamp() - issued_at >= _PROOF_TTL_SECONDS else "valid"
