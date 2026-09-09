"""Plain-text discussions sharing the meeting fence and the existing ACL."""

import hashlib
import json
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import case, delete, func, or_, select, text, tuple_
from sqlalchemy.orm import aliased

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.cabinet.access import decide_meeting_access
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    MeetingComment,
    MeetingCommentMention,
    MeetingCommentReaction,
    MeetingShareGrant,
    ProcessingResult,
    TranscriptSegment,
    UserIdentity,
    WorkspaceMembership,
)
from twobrain_rec_server.db.models.notifications import ServerNotification

EMOJI_OPTIONS = ["👍", "👎", "❤️", "🎉", "😄", "😕", "👀", "✅", "🙏", "🚀"]


def problem(status, code):
    raise ProblemDetail(
        status=status,
        code=code,
        title={
            403: "Недостаточно прав",
            404: "Обсуждение недоступно",
            409: "Данные изменились. Обновите обсуждение",
            422: "Проверьте введённые данные",
        }.get(status, "Обсуждение недоступно"),
    )


class MentionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID
    start: int = Field(ge=0, strict=True)
    end: int = Field(gt=0, strict=True)


class CommentText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str = Field(min_length=1, max_length=10000)
    mentions: list[MentionInput] = Field(default_factory=list, max_length=20)

    @field_validator("body")
    @classmethod
    def nonempty(cls, value):
        if not value.strip() or any(ord(c) < 32 and c not in "\n\r\t" for c in value):
            raise ValueError("invalid comment")
        return value


class CreateComment(CommentText):
    request_id: UUID
    media_revision_id: UUID
    start_ms: int = Field(ge=0, strict=True)
    end_ms: int | None = Field(default=None, ge=0, strict=True)
    processing_result_id: UUID | None = None
    source_segment_id: UUID | None = None


class ReplyComment(CommentText):
    request_id: UUID


class EditComment(CommentText):
    expected_version: int = Field(ge=1, strict=True)


class VersionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1, strict=True)


class ResolutionInput(VersionInput):
    resolved: bool = Field(strict=True)


class ReactionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    emoji: str
    selected: bool = Field(strict=True)

    @field_validator("emoji")
    @classmethod
    def supported(cls, value):
        if value not in EMOJI_OPTIONS:
            raise ValueError("unsupported emoji")
        return value


def capabilities(decision):
    return dict(
        can_comment=decision.can_comment,
        can_edit=decision.can_edit,
        can_manage_roles=decision.state == "owner" or decision.can_edit,
        emoji_options=EMOJI_OPTIONS,
    )


async def current_media(db, meeting):
    from twobrain_rec_server.processing.store import latest_media_revision_for_meeting

    media = await latest_media_revision_for_meeting(
        db, workspace_id=meeting.workspace_id, meeting_id=meeting.id
    )
    if media is None:
        problem(409, "comment_media_unavailable")
    return media


async def find_comment(db, meeting, identifier):
    row = await db.scalar(
        select(MeetingComment).where(
            MeetingComment.id == identifier,
            MeetingComment.meeting_id == meeting.id,
            MeetingComment.workspace_id == meeting.workspace_id,
        )
    )
    if row is None:
        problem(404, "comment_not_found")
    media = await current_media(db, meeting)
    if row.media_revision_id != media.id:
        problem(409, "comment_media_revision_stale")
    return row


def require_write(decision):
    if not decision.can_comment:
        problem(403, "comment_write_forbidden")


def require_version(row, expected):
    if row.version != expected:
        problem(409, "comment_version_stale")


async def external_recipient_identity(db, meeting, user_id):
    if db.bind.dialect.name != "postgresql":
        return None
    return await db.scalar(
        text("SELECT rec_comment_recipient_identity(:meeting, :user)"),
        dict(meeting=meeting.id, user=user_id),
    )


async def eligible_user(db, meeting, user_id):
    from twobrain_rec_server.cabinet.access import (
        ShareRecipientAccessProof,
        invitation_address_hashes,
    )

    user = await db.get(UserIdentity, user_id)
    proof = None
    if user is None:
        identity = await external_recipient_identity(db, meeting, user_id)
        if not identity:
            return False
        proof = ShareRecipientAccessProof(
            user_is_active=True,
            workspace_membership_is_active=identity["workspace_membership_is_active"],
            verified_address_hashes=frozenset(
                value
                for email in identity["verified_emails"]
                for value in invitation_address_hashes(email)
            ),
        )
    elif user.status != "active":
        return False
    decision = await decide_meeting_access(
        db,
        meeting,
        workspace_id=meeting.workspace_id,
        viewer_user_id=user_id,
        recipient_proof=proof,
    )
    return decision.can_view_full_meeting and decision.can_view


async def validate_mentions(db, meeting, payload):
    end = 0
    seen = set()
    for mention in sorted(payload.mentions, key=lambda m: m.start):
        if (
            mention.user_id in seen
            or mention.start < end
            or mention.end <= mention.start
            or mention.end > len(payload.body)
            or not payload.body[mention.start : mention.end].startswith("@")
        ):
            problem(422, "comment_mention_invalid")
        if not await eligible_user(db, meeting, mention.user_id):
            problem(422, "comment_mention_unavailable")
        end = mention.end
        seen.add(mention.user_id)


async def sync_mentions(db, meeting, row, mentions):
    existing = {
        m.user_id: m
        for m in await db.scalars(
            select(MeetingCommentMention).where(MeetingCommentMention.comment_id == row.id)
        )
    }
    wanted = {m.user_id: m for m in mentions}
    now = datetime.now(UTC)
    for user_id, old in existing.items():
        if user_id not in wanted:
            # Expire before removing the proof row: producer RLS uses that row.
            notice = await db.scalar(
                select(ServerNotification).where(
                    ServerNotification.family == "comment",
                    ServerNotification.source_id == row.id,
                    ServerNotification.recipient_id == user_id,
                )
            )
            if notice:
                notice.expires_at = now
                await db.flush()
            await db.delete(old)
    for user_id, item in wanted.items():
        if user_id in existing:
            existing[user_id].start = item.start
            existing[user_id].end = item.end
        else:
            db.add(
                MeetingCommentMention(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    comment_id=row.id,
                    user_id=user_id,
                    start=item.start,
                    end=item.end,
                )
            )
    await db.flush()
    for user_id in wanted:
        if user_id == row.author_user_id or user_id in existing:
            continue
        notice = await db.scalar(
            select(ServerNotification)
            .where(
                ServerNotification.family == "comment",
                ServerNotification.source_id == row.id,
                ServerNotification.recipient_id == user_id,
            )
            .with_for_update()
        )
        if notice is None:
            notice = ServerNotification(
                recipient_id=user_id,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                family="comment",
                source_id=row.id,
                source_revision=str(row.version),
                kind="mentioned",
                revision=1,
                read_revision=0,
                requires_action=False,
                created_at=now,
                updated_at=now,
            )
            db.add(notice)
        else:
            notice.revision += 1
            notice.source_revision = str(row.version)
            notice.updated_at = now
        from datetime import timedelta

        notice.expires_at = now + timedelta(days=30)
    await db.flush()


async def create_comment(db, meeting, decision, user_id, payload, parent=None):
    require_write(decision)
    media = await current_media(db, meeting)
    if parent is not None and parent.parent_id is not None:
        problem(422, "comment_reply_depth")
    if parent is None:
        if payload.media_revision_id != media.id:
            problem(409, "comment_media_revision_stale")
        if (
            payload.start_ms
            > (
                media.duration_seconds
                if media.duration_seconds is not None
                else meeting.duration_seconds
            )
            * 1000
            or payload.end_ms is not None
            and not payload.start_ms
            <= payload.end_ms
            <= (
                media.duration_seconds
                if media.duration_seconds is not None
                else meeting.duration_seconds
            )
            * 1000
        ):
            problem(422, "comment_range_invalid")
        if payload.processing_result_id:
            result = await db.scalar(
                select(ProcessingResult).where(
                    ProcessingResult.id == payload.processing_result_id,
                    ProcessingResult.workspace_id == meeting.workspace_id,
                    ProcessingResult.meeting_id == meeting.id,
                    ProcessingResult.media_revision_id == media.id,
                    ProcessingResult.status == "imported",
                )
            )
            if result is None:
                problem(422, "comment_source_invalid")
        if payload.source_segment_id:
            segment = None
            for source_model in (TranscriptSegment, DiarizationSegment):
                segment = await db.scalar(
                    select(source_model.id).where(
                        source_model.id == payload.source_segment_id,
                        source_model.workspace_id == meeting.workspace_id,
                        source_model.meeting_id == meeting.id,
                        source_model.processing_result_id == payload.processing_result_id,
                    )
                )
                if segment is not None:
                    break
            if segment is None:
                problem(422, "comment_source_invalid")
    await validate_mentions(db, meeting, payload)
    digest = hashlib.sha256(
        json.dumps(
            dict(
                payload=payload.model_dump(mode="json"), parent=str(parent.id) if parent else None
            ),
            sort_keys=True,
        ).encode()
    ).hexdigest()
    prior = await db.scalar(
        select(MeetingComment).where(
            MeetingComment.author_user_id == user_id,
            MeetingComment.meeting_id == meeting.id,
            MeetingComment.request_id == payload.request_id,
        )
    )
    if prior:
        if prior.request_hash != digest:
            problem(409, "comment_request_conflict")
        return prior
    row = MeetingComment(
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        author_user_id=user_id,
        media_revision_id=media.id,
        processing_result_id=parent.processing_result_id
        if parent
        else payload.processing_result_id,
        source_segment_id=parent.source_segment_id if parent else payload.source_segment_id,
        parent_id=parent.id if parent else None,
        start_ms=parent.start_ms if parent else payload.start_ms,
        end_ms=parent.end_ms if parent else payload.end_ms,
        body=payload.body,
        request_id=payload.request_id,
        request_hash=digest,
        version=1,
        resolved=False,
    )
    db.add(row)
    await db.flush()
    await sync_mentions(db, meeting, row, payload.mentions)
    return row


async def edit_comment(db, meeting, decision, user_id, row, payload):
    require_write(decision)
    if row.author_user_id != user_id:
        problem(403, "comment_author_required")
    require_version(row, payload.expected_version)
    await validate_mentions(db, meeting, payload)
    row.body = payload.body
    row.version += 1
    row.edited_at = datetime.now(UTC)
    await sync_mentions(db, meeting, row, payload.mentions)
    return row


async def delete_comment(db, meeting, decision, user_id, row, expected):
    require_write(decision)
    if row.author_user_id != user_id and not decision.can_edit:
        problem(403, "comment_author_required")
    require_version(row, expected)
    ids = select(MeetingComment.id).where(
        or_(MeetingComment.id == row.id, MeetingComment.parent_id == row.id)
    )
    await db.execute(
        delete(ServerNotification).where(
            ServerNotification.family == "comment", ServerNotification.source_id.in_(ids)
        )
    )
    await db.execute(delete(MeetingComment).where(MeetingComment.id.in_(ids)))


async def resolve_comment(db, decision, user_id, row, payload):
    require_write(decision)
    if row.parent_id is not None:
        problem(422, "comment_root_required")
    if row.author_user_id != user_id and not decision.can_edit:
        problem(403, "comment_author_required")
    require_version(row, payload.expected_version)
    if row.resolved != payload.resolved:
        row.resolved = payload.resolved
        row.resolved_by = user_id if row.resolved else None
        row.resolved_at = datetime.now(UTC) if row.resolved else None
        row.version += 1
    return row


async def react(db, decision, user_id, row, payload):
    require_write(decision)
    old = await db.scalar(
        select(MeetingCommentReaction).where(
            MeetingCommentReaction.comment_id == row.id,
            MeetingCommentReaction.user_id == user_id,
            MeetingCommentReaction.emoji == payload.emoji,
        )
    )
    if old is None and payload.selected:
        db.add(
            MeetingCommentReaction(
                workspace_id=row.workspace_id,
                meeting_id=row.meeting_id,
                comment_id=row.id,
                user_id=user_id,
                emoji=payload.emoji,
            )
        )
    elif old and not payload.selected:
        await db.delete(old)
    await db.flush()
    return row


@asynccontextmanager
async def comment_reader_context(db, meeting, decision, user_id):
    """Carry the request dependency's already-validated ACL into label reads."""
    if not decision.can_view or not decision.can_view_full_meeting:
        problem(404, "meeting_not_found")
    previous = db.info.get("comment_reader_access")
    db.info["comment_reader_access"] = (meeting.id, user_id)
    try:
        yield
    finally:
        if previous is None:
            db.info.pop("comment_reader_access", None)
        else:
            db.info["comment_reader_access"] = previous


def _comment_cursor(row):
    return f"{row.created_at.isoformat()}|{row.id}"


def _comment_view(row, decision, user_id, labels, mentions, reactions):
    return dict(
        id=str(row.id),
        parent_id=str(row.parent_id) if row.parent_id else None,
        author_user_id=str(row.author_user_id),
        author_label=labels.get(row.author_user_id) or "Участник",
        media_revision_id=str(row.media_revision_id),
        processing_result_id=str(row.processing_result_id) if row.processing_result_id else None,
        source_segment_id=str(row.source_segment_id) if row.source_segment_id else None,
        start_ms=row.start_ms,
        end_ms=row.end_ms,
        body=row.body,
        version=row.version,
        resolved=row.resolved,
        created_at=row.created_at.isoformat(),
        edited_at=row.edited_at.isoformat() if row.edited_at else None,
        mentions=mentions.get(row.id, []),
        reactions=reactions.get(row.id, []),
        can_edit=decision.can_comment and row.author_user_id == user_id,
        can_delete=decision.can_comment and (row.author_user_id == user_id or decision.can_edit),
        can_resolve=decision.can_comment
        and row.parent_id is None
        and (row.author_user_id == user_id or decision.can_edit),
    )


async def _comment_views(db, rows, decision, user_id, *, with_replies=False):
    if not rows:
        return []
    replies = defaultdict(list)
    if with_replies:
        ranked = (
            select(
                MeetingComment,
                func.row_number()
                .over(
                    partition_by=MeetingComment.parent_id,
                    order_by=(MeetingComment.created_at, MeetingComment.id),
                )
                .label("reply_number"),
            )
            .where(
                MeetingComment.workspace_id == rows[0].workspace_id,
                MeetingComment.meeting_id == rows[0].meeting_id,
                MeetingComment.media_revision_id == rows[0].media_revision_id,
                MeetingComment.parent_id.in_([row.id for row in rows]),
            )
            .subquery()
        )
        reply = aliased(MeetingComment, ranked)
        for row in await db.scalars(
            select(reply)
            .where(ranked.c.reply_number <= 51)
            .order_by(reply.parent_id, reply.created_at, reply.id)
        ):
            replies[row.parent_id].append(row)
    visible = [*rows, *(row for group in replies.values() for row in group[:50])]
    identifiers = [row.id for row in visible]
    authors = {row.author_user_id for row in visible}
    if db.bind.dialect.name == "postgresql":
        meeting_id = rows[0].meeting_id
        # Only the request dependency that performed the real ACL check may
        # supply this proof. Ordinary workspace readers are authorized in SQL.
        marked = (
            decision.role is None
            and decision.state != "owner"
            and db.info.get("comment_reader_access") == (meeting_id, user_id)
            and db.info.get("tenant_context", {}).get("app.user_id") == str(user_id)
            and db.info.get("tenant_context", {}).get("app.workspace_id")
            == str(rows[0].workspace_id)
        )
        marker_sql = text(
            "SELECT set_config('app.comment_reader_meeting_id', :meeting, true), "
            "set_config('app.comment_reader_user_id', :user, true)"
        )
        if marked:
            await db.execute(marker_sql, dict(meeting=str(meeting_id), user=str(user_id)))
        try:
            labels = dict(
                (
                    await db.execute(
                        text(
                            "SELECT user_id, display_label FROM rec_comment_author_labels(:meeting, CAST(:users AS uuid[]))"
                        ),
                        dict(meeting=meeting_id, users=list(authors)),
                    )
                ).all()
            )
        finally:
            if marked:
                await db.execute(marker_sql, dict(meeting="", user=""))
    else:
        labels = dict(
            (
                await db.execute(
                    select(UserIdentity.id, UserIdentity.display_name).where(
                        UserIdentity.id.in_(authors)
                    )
                )
            ).all()
        )
    mentions = defaultdict(list)
    for mention in await db.scalars(
        select(MeetingCommentMention)
        .where(MeetingCommentMention.comment_id.in_(identifiers))
        .order_by(MeetingCommentMention.start, MeetingCommentMention.id)
    ):
        mentions[mention.comment_id].append(
            dict(user_id=str(mention.user_id), start=mention.start, end=mention.end)
        )
    reactions = defaultdict(list)
    for comment, emoji, count, selected in await db.execute(
        select(
            MeetingCommentReaction.comment_id,
            MeetingCommentReaction.emoji,
            func.count(),
            func.max(case((MeetingCommentReaction.user_id == user_id, 1), else_=0)),
        )
        .where(MeetingCommentReaction.comment_id.in_(identifiers))
        .group_by(MeetingCommentReaction.comment_id, MeetingCommentReaction.emoji)
        .order_by(MeetingCommentReaction.emoji)
    ):
        reactions[comment].append(dict(emoji=emoji, count=count, selected=bool(selected)))
    items = []
    for row in rows:
        item = _comment_view(row, decision, user_id, labels, mentions, reactions)
        if with_replies:
            children = replies[row.id]
            item.update(
                replies=[
                    _comment_view(child, decision, user_id, labels, mentions, reactions)
                    for child in children[:50]
                ],
                next_reply_cursor=_comment_cursor(children[49]) if len(children) > 50 else None,
            )
        items.append(item)
    return items


async def comment_view(db, row, decision, user_id, *, with_replies=False):
    return (await _comment_views(db, [row], decision, user_id, with_replies=with_replies))[0]


async def list_comments(
    db,
    meeting_id,
    media_id,
    decision,
    user_id,
    *,
    parent_id=None,
    status="open",
    author_id=None,
    source_segment_ids=None,
    limit=50,
    cursor=None,
):
    query = select(MeetingComment).where(
        MeetingComment.meeting_id == meeting_id,
        MeetingComment.media_revision_id == media_id,
        MeetingComment.parent_id == parent_id,
    )
    if parent_id is None and status != "all":
        query = query.where(MeetingComment.resolved == (status == "resolved"))
    if source_segment_ids:
        query = query.where(MeetingComment.source_segment_id.in_(source_segment_ids))
    if author_id:
        query = query.where(MeetingComment.author_user_id == author_id)
    if cursor:
        try:
            date, identifier = cursor.split("|")
            marker = (datetime.fromisoformat(date), UUID(identifier))
            if marker[0].tzinfo is None:
                raise ValueError()
        except (ValueError, TypeError):
            problem(422, "comment_cursor_invalid")
        query = query.where(tuple_(MeetingComment.created_at, MeetingComment.id) > marker)
    rows = list(
        await db.scalars(
            query.order_by(MeetingComment.created_at, MeetingComment.id).limit(limit + 1)
        )
    )
    more = len(rows) > limit
    rows = rows[:limit]
    counts = []
    if parent_id is None:
        counts = list(
            await db.execute(
                select(MeetingComment.source_segment_id, func.count())
                .where(
                    MeetingComment.meeting_id == meeting_id,
                    MeetingComment.media_revision_id == media_id,
                    MeetingComment.parent_id.is_(None),
                )
                .group_by(MeetingComment.source_segment_id)
            )
        )
    return dict(
        total_count=sum(count for _, count in counts),
        source_counts=[
            dict(source_segment_id=str(source), count=count)
            for source, count in counts
            if source is not None
        ],
        items=await _comment_views(db, rows, decision, user_id, with_replies=parent_id is None),
        next_cursor=_comment_cursor(rows[-1]) if more else None,
        capabilities=capabilities(decision),
        media_revision_id=str(media_id),
    )


async def mention_candidates(db, meeting, q):
    users = await db.scalars(
        select(UserIdentity)
        .where(
            UserIdentity.status == "active",
            UserIdentity.display_name.ilike(
                "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%",
                escape="\\",
            ),
            or_(
                UserIdentity.id == meeting.created_by_user_id,
                UserIdentity.id.in_(
                    select(WorkspaceMembership.user_id).where(
                        WorkspaceMembership.workspace_id == meeting.workspace_id,
                        WorkspaceMembership.status == "active",
                    )
                ),
                UserIdentity.id.in_(
                    select(MeetingShareGrant.grantee_user_id).where(
                        MeetingShareGrant.meeting_id == meeting.id,
                        MeetingShareGrant.workspace_id == meeting.workspace_id,
                        MeetingShareGrant.status == "active",
                    )
                ),
            ),
        )
        .order_by(UserIdentity.display_name)
        .limit(100)
    )
    items = []
    for user in users:
        if await eligible_user(db, meeting, user.id):
            items.append(dict(user_id=str(user.id), display_label=user.display_name or "Участник"))
        if len(items) == 20:
            break
    # Explicit external grantees may be hidden by organization RLS; only the
    # bounded projection above may provide their label and address proof.
    if len(items) < 20:
        existing = {item["user_id"] for item in items}
        external_ids = await db.scalars(
            select(MeetingShareGrant.audience_id)
            .where(
                MeetingShareGrant.meeting_id == meeting.id,
                MeetingShareGrant.workspace_id == meeting.workspace_id,
                MeetingShareGrant.audience_type == "user",
                MeetingShareGrant.status == "active",
                MeetingShareGrant.content_scope == "full_meeting",
            )
            .limit(100)
        )
        candidate_ids = list(external_ids)
        candidate_ids.extend(
            await db.scalars(
                select(WorkspaceMembership.user_id)
                .where(
                    WorkspaceMembership.workspace_id == meeting.workspace_id,
                    WorkspaceMembership.status == "active",
                )
                .limit(100)
            )
        )
        candidate_ids.append(meeting.created_by_user_id)
        for user_id in dict.fromkeys(candidate_ids):
            if str(user_id) in existing:
                continue
            identity = await external_recipient_identity(db, meeting, user_id)
            label = (identity or {}).get("display_label") or "Участник"
            if (
                identity
                and q.casefold() in label.casefold()
                and await eligible_user(db, meeting, user_id)
            ):
                items.append(dict(user_id=str(user_id), display_label=label))
            if len(items) == 20:
                break
    return dict(items=items)


async def merge_comment_identity(db, source_user_id, survivor_user_id):
    """Called only inside the existing proof-bound account merge transaction."""
    from uuid import uuid4

    from sqlalchemy import update

    for row in await db.scalars(
        select(MeetingComment)
        .where(MeetingComment.author_user_id == source_user_id)
        .with_for_update()
    ):
        collision = await db.scalar(
            select(MeetingComment.id).where(
                MeetingComment.author_user_id == survivor_user_id,
                MeetingComment.meeting_id == row.meeting_id,
                MeetingComment.request_id == row.request_id,
            )
        )
        if collision:
            row.request_id = uuid4()
        row.author_user_id = survivor_user_id
    await db.execute(
        update(MeetingComment)
        .where(MeetingComment.resolved_by == source_user_id)
        .values(resolved_by=survivor_user_id)
    )
    for model in (MeetingCommentMention, MeetingCommentReaction):
        for row in await db.scalars(
            select(model).where(model.user_id == source_user_id).with_for_update()
        ):
            clauses = [model.comment_id == row.comment_id, model.user_id == survivor_user_id]
            if model is MeetingCommentReaction:
                clauses.append(model.emoji == row.emoji)
            duplicate = await db.scalar(select(model.id).where(*clauses))
            if duplicate:
                await db.delete(row)
            else:
                row.user_id = survivor_user_id
    for row in await db.scalars(
        select(ServerNotification)
        .where(
            ServerNotification.family == "comment",
            ServerNotification.recipient_id == source_user_id,
        )
        .with_for_update()
    ):
        duplicate = await db.scalar(
            select(ServerNotification)
            .where(
                ServerNotification.family == "comment",
                ServerNotification.recipient_id == survivor_user_id,
                ServerNotification.workspace_id == row.workspace_id,
                ServerNotification.source_id == row.source_id,
            )
            .with_for_update()
        )
        if duplicate:
            unseen = (
                row.read_revision < row.revision or duplicate.read_revision < duplicate.revision
            )
            duplicate.revision = max(row.revision, duplicate.revision)
            duplicate.read_revision = duplicate.revision - 1 if unseen else duplicate.revision
            await db.delete(row)
        else:
            row.recipient_id = survivor_user_id
    await db.flush()
