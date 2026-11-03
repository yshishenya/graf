"""Public meeting projections: explicit link authority, never an owner's session."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.cabinet.access import (
    AccessDecision,
    hash_share_token,
    lock_shareable_meeting,
)
from twobrain_rec_server.cabinet.queries import (
    _latest_media_revision,
    shared_meeting_display_metadata,
)
from twobrain_rec_server.cabinet.speakers import speaker_names_for_result
from twobrain_rec_server.cabinet.view_models import transcript_state
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    MeetingShareGrant,
    MeetingSpeakerName,
    TranscriptSegment,
)
from twobrain_rec_server.processing.results import effective_processing_result_query

TOKEN = re.compile(r"[A-Za-z0-9_-]{32,128}\Z")
CONTINUATION_COOKIE = "graf_shared_meeting_continue"


@dataclass(frozen=True, slots=True)
class PublicShareProof:
    workspace_id: UUID
    meeting_id: UUID
    grant_id: UUID
    token_hash: str
    version: int


def unavailable():
    return ProblemDetail(status=404, code="share_not_found", title="Share not found")


async def resolve_public_share(db, *, settings, workspace_id, token):
    if (
        db is None
        or not settings.share_public_links_enabled
        or not settings.share_public_links_abuse_gate_approved
        or not TOKEN.fullmatch(token)
    ):
        raise unavailable()
    token_hash = hash_share_token(token)
    grant = await db.scalar(
        select(MeetingShareGrant).where(
            MeetingShareGrant.workspace_id == workspace_id,
            MeetingShareGrant.audience_type == "link",
            MeetingShareGrant.status == "active",
            MeetingShareGrant.share_token_hash == token_hash,
        )
    )
    if grant is None:
        raise unavailable()
    try:
        meeting = await lock_shareable_meeting(
            db, workspace_id=workspace_id, meeting_id=grant.meeting_id
        )
    except ProblemDetail:
        raise unavailable() from None
    proof = PublicShareProof(
        workspace_id, meeting.id, grant.id, token_hash, grant.publication_version
    )
    grant = await validate_public_proof(db, proof=proof)
    return meeting, grant, proof


async def validate_public_proof(db, *, proof, require_full=False):
    grant = await db.scalar(
        select(MeetingShareGrant)
        .where(
            MeetingShareGrant.id == proof.grant_id,
            MeetingShareGrant.workspace_id == proof.workspace_id,
            MeetingShareGrant.meeting_id == proof.meeting_id,
            MeetingShareGrant.audience_type == "link",
            MeetingShareGrant.status == "active",
            MeetingShareGrant.share_token_hash == proof.token_hash,
            MeetingShareGrant.publication_version == proof.version,
            MeetingShareGrant.expires_at.is_(None)
            | (MeetingShareGrant.expires_at > datetime.now(UTC)),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        grant is None
        or grant.content_scope not in ("summary_only", "full_meeting")
        or (require_full and grant.content_scope != "full_meeting")
    ):
        raise unavailable()
    return grant


def public_access():
    return AccessDecision(
        state="shared",
        label="По ссылке",
        reason=None,
        can_view=True,
        can_share=False,
        can_manage_team_visibility=False,
        can_download=False,
        can_export=False,
        content_scope="full_meeting",
        can_view_full_meeting=True,
    )


async def current_media(db, *, meeting):
    revision = await _latest_media_revision(
        db, workspace_id=meeting.workspace_id, meeting_id=meeting.id
    )
    result = await db.scalar(
        effective_processing_result_query(
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            media_revision_id=revision.id if revision else None,
        )
    )
    version = sha256(
        f"{revision.id if revision else 'absent'}:{result.id if result else 'absent'}".encode()
    ).hexdigest()[:24]
    return result, version


async def full_projection(db, *, meeting, summary, outcome_set=None, outcome_items=()):
    from twobrain_rec_server.cabinet.egress import review_playback_state

    result, version = await current_media(db, meeting=meeting)
    playback = await review_playback_state(db, meeting=meeting, access=public_access())
    turns = []
    sources = {}
    if result is not None:
        common = {
            "workspace_id": meeting.workspace_id,
            "meeting_id": meeting.id,
            "processing_result_id": result.id,
        }
        segments = (await db.scalars(select(TranscriptSegment).filter_by(**common))).all()
        diarization = (await db.scalars(select(DiarizationSegment).filter_by(**common))).all()
        if outcome_set is not None and outcome_set.processing_result_id == result.id:
            sources = {
                str(segment.id): max(0, int(segment.start_seconds * 1000)) for segment in segments
            }
        names = speaker_names_for_result(
            (
                await db.scalars(
                    select(MeetingSpeakerName).where(
                        MeetingSpeakerName.workspace_id == meeting.workspace_id,
                        MeetingSpeakerName.meeting_id == meeting.id,
                    )
                )
            ).all(),
            result_imported_at=result.imported_at,
        )
        transcript = transcript_state(
            speaker_names=names,
            language=result.language,
            transcript_segments=segments,
            diarization_segments=diarization,
            status="ready",
            playback_available=playback.can_play,
            playback_duration_seconds=meeting.duration_seconds,
        )
        # Local row order is sufficient; no provider/result/storage identifiers cross this boundary.
        turns = [
            {
                "speaker": t.speaker_label,
                "text": t.text,
                "start_ms": int(t.start_seconds * 1000),
                "end_ms": int(t.end_seconds * 1000),
                "time": t.timestamp_label,
            }
            for t in transcript.speaker_turns
        ]

    def safe_sources(refs):
        values = []
        for ref in refs if isinstance(refs, list) else []:
            if not isinstance(ref, dict):
                continue
            start = sources.get(str(ref.get("transcript_segment_id")))
            if start is not None and start <= 86400000:
                values.append(
                    {"start_ms": start, "time": f"{start // 60000}:{start // 1000 % 60:02d}"}
                )
        return values[:10]

    sections = [
        {
            "category": item.category,
            "text": item.text or "",
            "sources": safe_sources(item.source_refs_json),
        }
        for item in outcome_items
    ]
    protocol = summary["protocol"]
    if protocol and outcome_set is not None and sources:

        def attach(safe, original):
            if isinstance(safe, dict) and isinstance(original, dict):
                for key, value in list(safe.items()):
                    attach(value, original.get(key))
                if "text" in safe or "task" in safe:
                    safe["sources"] = safe_sources(original.get("source_refs"))
            elif isinstance(safe, list) and isinstance(original, list):
                for row, origin in zip(safe, original, strict=False):
                    attach(row, origin)

        attach(protocol, outcome_set.protocol_json)
    label, occurred, _ = await shared_meeting_display_metadata(db, meeting=meeting)
    return {
        "meeting_label": label,
        "occurred_at": occurred,
        "duration_seconds": max(0, meeting.duration_seconds or 0),
        "summary_sections": sections or summary["summary_sections"],
        "protocol": protocol,
        "transcript": turns,
        "media_version": version,
        "playback_available": playback.can_play,
    }


def share_fragment(tab="outcomes", position_ms=None):
    if tab not in ("outcomes", "recording"):
        raise ValueError("invalid share tab")
    if position_ms is not None and (
        tab != "recording" or not isinstance(position_ms, int) or not 0 <= position_ms <= 86400000
    ):
        raise ValueError("invalid share position")
    return "#" + tab + (f"?position_ms={position_ms}" if position_ms is not None else "")


async def reader_is_signed_in(request):
    """Presentation only: an expired browser session cannot disable a valid public link."""
    from twobrain_rec_server.auth.dependencies import (
        AUTH_SESSION_COOKIE_NAME,
        DESKTOP_CALENDAR_AUTH_COOKIE_NAME,
        get_optional_principal,
    )

    try:
        return (
            await get_optional_principal(
                request,
                authorization=request.headers.get("Authorization"),
                x_auth_session=request.headers.get("X-Auth-Session"),
                auth_session_cookie=request.cookies.get(AUTH_SESSION_COOKIE_NAME),
                x_user_id=request.headers.get("X-User-Id"),
                x_organization_id=request.headers.get("X-Organization-Id"),
                x_workspace_id=request.headers.get("X-Workspace-Id"),
                desktop_calendar_auth_cookie=request.cookies.get(DESKTOP_CALENDAR_AUTH_COOKIE_NAME),
            )
            is not None
        )
    except ProblemDetail as error:
        if error.status not in (400, 401, 403):
            raise
        return False
