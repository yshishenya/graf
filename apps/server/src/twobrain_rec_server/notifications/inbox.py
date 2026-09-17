"""One card per domain object, updated in the domain owner's transaction."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import Meeting
from twobrain_rec_server.db.models.notifications import ServerNotification

COPY = {
    'transcript_ready': ('Расшифровка готова', 'Откройте встречу, чтобы прочитать расшифровку.'),
    'result_ready': ('Итоги готовы', 'Результат доступен в карточке встречи.'),
    'summary_failed': ('Не удалось подготовить итоги', 'Расшифровка доступна. Откройте встречу для восстановления.'),
    'processing_failed': ('Не удалось обработать запись', 'Откройте встречу, чтобы проверить запись и доступные действия.'),
    'no_speech': ('Речь не распознана', 'Проверьте звук записи или загрузите другой файл.'),
    'mentioned': ('Вас упомянули в обсуждении', 'Откройте встречу, чтобы прочитать комментарий.'),
    'shared': ('С вами поделились встречей', 'Откройте встречу, чтобы посмотреть доступный результат.'),
}
ACTION_KINDS = frozenset({'summary_failed', 'processing_failed', 'no_speech'})


def apply_event(row: ServerNotification, *, kind: str, source_revision: str, now: datetime) -> None:
    if kind not in COPY:
        raise ValueError('unsupported notification event')
    # A retry with the same visible outcome never renews attention or retention.
    if row.kind == kind:
        return
    was_action = bool(row.requires_action)
    row.kind = kind
    row.source_revision = source_revision
    row.revision = (row.revision or 0) + 1
    row.updated_at = now
    row.requires_action = kind in ACTION_KINDS
    row.resolved_at = now if was_action and not row.requires_action else None
    row.expires_at = None if row.requires_action else now + timedelta(days=30)


def acknowledge_revision(row: ServerNotification, revision: int) -> None:
    if isinstance(revision, bool) or revision < 1 or revision > row.revision:
        raise ValueError('invalid shown revision')
    row.read_revision = max(row.read_revision or 0, revision)


async def record_event(db: AsyncSession, *, meeting: Meeting, kind: str, source_revision: str,
                       recipient_id: UUID | None = None, share_id: UUID | None = None) -> None:
    """Caller holds the meeting fence and owns commit, including deletion/source checks."""
    if kind not in COPY:
        raise ValueError('unsupported notification event')
    if (kind == 'shared') != (share_id is not None) or (share_id is not None and recipient_id is None):
        raise ValueError('notification source does not match event family')
    if meeting.deleted_at or meeting.deletion_state not in {None, 'none'}:
        return
    recipient = recipient_id or meeting.created_by_user_id
    family = 'share' if share_id else 'result'
    source_id = share_id or meeting.id
    row = await db.scalar(select(ServerNotification).where(
        ServerNotification.recipient_id == recipient,
        ServerNotification.workspace_id == meeting.workspace_id,
        ServerNotification.family == family,
        ServerNotification.source_id == source_id,
    ).with_for_update())
    now = datetime.now(UTC)
    if row is None:
        row = ServerNotification(recipient_id=recipient, workspace_id=meeting.workspace_id,
                                 meeting_id=meeting.id, family=family, source_id=source_id,
                                 kind='', revision=0, read_revision=0, requires_action=False,
                                 created_at=now)
        db.add(row)
    apply_event(row, kind=kind, source_revision=source_revision, now=now)
    await db.flush()


def encode_cursor(marker: tuple[datetime, UUID], *, binding: str, secret: str, now: datetime) -> str:
    payload = json.dumps([marker[0].isoformat(), str(marker[1]), binding, int(now.timestamp())], separators=(',', ':')).encode()
    data = base64.urlsafe_b64encode(payload).decode().rstrip('=')
    signature = hmac.new(secret.encode(), b'graf-inbox-v1:'+data.encode(), hashlib.sha256).hexdigest()
    return data+'.'+signature


def decode_cursor(cursor: str, *, binding: str, secret: str, now: datetime) -> tuple[datetime, UUID]:
    try:
        if len(cursor) > 2048:
            raise ValueError('cursor too long')
        data, signature = cursor.rsplit('.', 1)
        expected = hmac.new(secret.encode(), b'graf-inbox-v1:'+data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError('invalid signature')
        timestamp, identifier, bound, issued = json.loads(base64.urlsafe_b64decode(data+'='*(-len(data)%4)))
        if bound != binding or not 0 <= now.timestamp()-issued <= 3600:
            raise ValueError('stale or foreign cursor')
        parsed = datetime.fromisoformat(timestamp)
        if parsed.tzinfo is None:
            raise ValueError('invalid date')
        return parsed, UUID(identifier)
    except (TypeError, ValueError, KeyError) as exc:
        raise ValueError('invalid cursor') from exc


async def authorized_card(db, row, *, tenant_scope, sessionmaker):
    """Revalidate the object; an inbox row itself never grants meeting access."""
    from twobrain_rec_server.cabinet.access import (
        decide_meeting_access,
        recipient_share_access_proof,
    )
    from twobrain_rec_server.db.models import MeetingShareGrant
    from twobrain_rec_server.db.tenant_context import TenantDatabaseContext, apply_tenant_context

    if row.recipient_id != tenant_scope.user_id:
        return None
    if row.family == 'comment':
        from twobrain_rec_server.db.models import (
            MeetingComment,
            MeetingCommentMention,
        )
        proof = await recipient_share_access_proof(sessionmaker, recipient_scope=tenant_scope, owner_workspace_id=row.workspace_id)
        if not proof.user_is_active:
            return None
        async with sessionmaker() as source_db:
            await apply_tenant_context(source_db, TenantDatabaseContext(
                organization_id=UUID(int=0), workspace_id=row.workspace_id, user_id=UUID(int=0)))
            meeting = await source_db.get(Meeting, row.meeting_id)
            comment = await source_db.get(MeetingComment, row.source_id)
            mention = await source_db.scalar(select(MeetingCommentMention.id).where(
                MeetingCommentMention.comment_id == row.source_id, MeetingCommentMention.user_id == tenant_scope.user_id,
                MeetingCommentMention.meeting_id == row.meeting_id, MeetingCommentMention.workspace_id == row.workspace_id))
            if meeting is None or comment is None or mention is None:
                return None
            decision = await decide_meeting_access(source_db, meeting, workspace_id=row.workspace_id,
                viewer_user_id=tenant_scope.user_id, recipient_proof=proof)
            from twobrain_rec_server.processing.store import latest_media_revision_for_meeting
            media = await latest_media_revision_for_meeting(source_db, workspace_id=row.workspace_id, meeting_id=meeting.id)
            if not decision.can_view or not decision.can_view_full_meeting or media is None or comment.media_revision_id != media.id:
                return None
        path = (f'/meetings/{meeting.id}?comment_id={comment.id}' if row.workspace_id == tenant_scope.workspace_id
                else f'/shared-meetings/{meeting.id}?workspace_id={row.workspace_id}&comment_id={comment.id}')
    elif row.family == 'result':
        if row.workspace_id != tenant_scope.workspace_id:
            return None
        meeting = await db.get(Meeting, row.meeting_id)
        if meeting is None or meeting.created_by_user_id != tenant_scope.user_id:
            return None
        path = f'/meetings/{meeting.id}'
    else:
        proof = await recipient_share_access_proof(sessionmaker, recipient_scope=tenant_scope, owner_workspace_id=row.workspace_id)
        if not proof.user_is_active:
            return None
        async with sessionmaker() as source_db:
            await apply_tenant_context(source_db, TenantDatabaseContext(
                organization_id=UUID(int=0), workspace_id=row.workspace_id, user_id=UUID(int=0)))
            meeting = await source_db.get(Meeting, row.meeting_id)
            grant = await source_db.get(MeetingShareGrant, row.source_id)
            if (meeting is None or grant is None or grant.status != 'active'
                    or grant.grantee_user_id != tenant_scope.user_id
                    or grant.meeting_id != row.meeting_id or grant.workspace_id != row.workspace_id
                    or (grant.expires_at and grant.expires_at <= datetime.now(UTC))):
                return None
            decision = await decide_meeting_access(source_db, meeting, workspace_id=row.workspace_id,
                viewer_user_id=tenant_scope.user_id, recipient_proof=proof)
            if not decision.can_view:
                return None
        path = f'/shared-meetings/{meeting.id}?workspace_id={row.workspace_id}'
    if meeting.deleted_at or meeting.deletion_state not in {None, 'none'}:
        return None
    title, body = COPY[row.kind]
    return dict(id=str(row.id), revision=row.revision, title=title, body=body,
                meeting_title=meeting.title or 'Встреча', href=path,
                requires_action=row.requires_action, unseen=row.read_revision < row.revision,
                personal=row.family in {'share', 'comment'}, created_at=row.created_at.isoformat(),
                updated_at=row.updated_at.isoformat(), resolved=row.resolved_at is not None)


async def purge_expired(db: AsyncSession, *, limit: int = 1000) -> None:
    from sqlalchemy import delete
    expired = select(ServerNotification.id).where(
        ServerNotification.expires_at <= datetime.now(UTC),
        ServerNotification.requires_action.is_(False),
    ).limit(limit)
    await db.execute(delete(ServerNotification).where(ServerNotification.id.in_(expired)))
    await db.commit()
