from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.admin.queries import AdminWorkspaceContext
from twobrain_rec_server.db.models import (
    AdminAuditEvent,
    AuthAuditEvent,
    MeetingEgressAuditEvent,
    MeetingLifecycleAuditEvent,
)

FORBIDDEN_METADATA_MARKERS = (
    "storage_object_key",
    "signed_url",
    "x-amz",
    "/users/",
    "session_token",
    "password",
    "secret",
    "token",
    "transcript_text",
    "raw_audio",
)

SAFE_METADATA_KEYS = frozenset(
    {
        "action",
        "actor_role",
        "artifact_class",
        "date_from",
        "date_to",
        "freshness_state",
        "group_by",
        "limit",
        "object_kind",
        "outcome",
        "reason_code",
        "role",
        "source",
        "status",
        "target_kind",
    }
)


def assert_metadata_safe(metadata: Mapping[str, Any]) -> None:
    body = str(metadata).lower()
    if any(marker in body for marker in FORBIDDEN_METADATA_MARKERS):
        raise ValueError("Admin audit metadata contains private content or secret markers")


def sanitize_audit_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    safe = {
        key: value
        for key, value in metadata.items()
        if key in SAFE_METADATA_KEYS and _is_safe_scalar(value)
    }
    assert_metadata_safe(safe)
    return safe


async def write_admin_audit_event(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    actor_user_id: UUID | None,
    actor_role: str | None,
    action: str,
    target_kind: str,
    outcome: str,
    target_id: str | None = None,
    reason_code: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> AdminAuditEvent:
    safe_metadata = sanitize_audit_metadata(metadata)
    event = AdminAuditEvent(
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action=action,
        target_kind=target_kind,
        target_id=target_id,
        outcome=outcome,
        reason_code=reason_code,
        metadata_json=safe_metadata,
    )
    db.add(event)
    await db.flush()
    return event


def _is_safe_scalar(value: Any) -> bool:
    if value is None or isinstance(value, bool | int | float):
        return True
    return isinstance(value, str) and len(value) <= 240


async def read_admin_audit_journal(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    date_from: date | None = None,
    date_to: date | None = None,
    user_id: UUID | None = None,
    action: str | None = None,
    object_kind: str | None = None,
    object_id: str | None = None,
    outcome: str | None = None,
    limit: int = 50,
) -> dict[str, object]:
    admin_events = await _admin_events(
        db,
        context=context,
        date_from=date_from,
        date_to=date_to,
        user_id=user_id,
        action=action,
        object_kind=object_kind,
        object_id=object_id,
        outcome=outcome,
        limit=limit,
    )
    auth_events = await _auth_events(
        db,
        context=context,
        date_from=date_from,
        date_to=date_to,
        user_id=user_id,
        action=action,
        object_kind=object_kind,
        object_id=object_id,
        outcome=outcome,
        limit=limit,
    )
    egress_events = await _egress_events(
        db,
        context=context,
        date_from=date_from,
        date_to=date_to,
        user_id=user_id,
        action=action,
        object_kind=object_kind,
        object_id=object_id,
        outcome=outcome,
        limit=limit,
    )
    lifecycle_events = await _lifecycle_events(
        db,
        context=context,
        date_from=date_from,
        date_to=date_to,
        user_id=user_id,
        action=action,
        object_kind=object_kind,
        object_id=object_id,
        outcome=outcome,
        limit=limit,
    )
    entries = [
        {
            "event_id": str(event.id),
            "source": "admin_audit_events",
            "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
            "action": event.action,
            "object_kind": event.target_kind,
            "object_id": event.target_id,
            "outcome": event.outcome,
            "reason_code": event.reason_code,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "metadata_safe_summary": event.reason_code or event.outcome,
            "drill_down_path": "/admin/audit",
        }
        for event in admin_events
    ]
    entries.extend(
        {
            "event_id": str(event.id),
            "source": "auth_audit_events",
            "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
            "action": event.event_type,
            "object_kind": "auth",
            "object_id": event.provider,
            "outcome": event.outcome,
            "reason_code": None,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "metadata_safe_summary": event.outcome,
            "drill_down_path": "/admin/users",
        }
        for event in auth_events
    )
    entries.extend(
        {
            "event_id": str(event.id),
            "source": "meeting_egress_audit_events",
            "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
            "action": event.event_type,
            "object_kind": "meeting",
            "object_id": str(event.meeting_id) if event.meeting_id else None,
            "outcome": event.outcome,
            "reason_code": event.policy_reason,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "metadata_safe_summary": event.policy_reason or event.outcome,
            "drill_down_path": f"/admin/files/{event.meeting_id}"
            if event.meeting_id
            else "/admin/files",
        }
        for event in egress_events
    )
    entries.extend(
        {
            "event_id": str(event.id),
            "source": "meeting_lifecycle_audit_events",
            "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
            "action": event.event_type,
            "object_kind": "meeting",
            "object_id": str(event.meeting_id) if event.meeting_id else None,
            "outcome": event.outcome,
            "reason_code": event.safe_reason,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "metadata_safe_summary": event.safe_reason or event.outcome,
            "drill_down_path": f"/admin/files/{event.meeting_id}"
            if event.meeting_id
            else "/admin/files",
        }
        for event in lifecycle_events
    )
    entries.sort(key=lambda item: str(item["created_at"] or ""), reverse=True)
    return {
        "entries": entries[:limit],
        "freshness": "source_backed",
        "filters": {
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "user_id": str(user_id) if user_id else None,
            "action": action,
            "object_kind": object_kind,
            "object_id": object_id,
            "outcome": outcome,
        },
    }


async def _admin_events(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    date_from: date | None,
    date_to: date | None,
    user_id: UUID | None,
    action: str | None,
    object_kind: str | None,
    object_id: str | None,
    outcome: str | None,
    limit: int,
) -> list[AdminAuditEvent]:
    stmt = select(AdminAuditEvent).where(AdminAuditEvent.workspace_id == context.workspace_id)
    stmt = _with_date_filters(stmt, AdminAuditEvent.created_at, date_from=date_from, date_to=date_to)
    if user_id:
        stmt = stmt.where(AdminAuditEvent.actor_user_id == user_id)
    if action:
        stmt = stmt.where(AdminAuditEvent.action == action)
    if object_kind:
        stmt = stmt.where(AdminAuditEvent.target_kind == object_kind)
    if object_id:
        stmt = stmt.where(AdminAuditEvent.target_id == object_id)
    if outcome:
        stmt = stmt.where(AdminAuditEvent.outcome == outcome)
    return (await db.execute(stmt.order_by(AdminAuditEvent.created_at.desc()).limit(limit))).scalars().all()


async def _auth_events(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    date_from: date | None,
    date_to: date | None,
    user_id: UUID | None,
    action: str | None,
    object_kind: str | None,
    object_id: str | None,
    outcome: str | None,
    limit: int,
) -> list[AuthAuditEvent]:
    if object_kind and object_kind != "auth":
        return []
    stmt = select(AuthAuditEvent).where(AuthAuditEvent.workspace_id == context.workspace_id)
    stmt = _with_date_filters(stmt, AuthAuditEvent.created_at, date_from=date_from, date_to=date_to)
    if user_id:
        stmt = stmt.where(or_(AuthAuditEvent.actor_user_id == user_id, AuthAuditEvent.user_id == user_id))
    if action:
        stmt = stmt.where(AuthAuditEvent.event_type == action)
    if object_id:
        stmt = stmt.where(AuthAuditEvent.provider == object_id)
    if outcome:
        stmt = stmt.where(AuthAuditEvent.outcome == outcome)
    return (await db.execute(stmt.order_by(AuthAuditEvent.created_at.desc()).limit(limit))).scalars().all()


async def _egress_events(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    date_from: date | None,
    date_to: date | None,
    user_id: UUID | None,
    action: str | None,
    object_kind: str | None,
    object_id: str | None,
    outcome: str | None,
    limit: int,
) -> list[MeetingEgressAuditEvent]:
    if object_kind and object_kind != "meeting":
        return []
    stmt = select(MeetingEgressAuditEvent).where(
        MeetingEgressAuditEvent.workspace_id == context.workspace_id
    )
    stmt = _with_date_filters(
        stmt, MeetingEgressAuditEvent.created_at, date_from=date_from, date_to=date_to
    )
    if user_id:
        stmt = stmt.where(MeetingEgressAuditEvent.actor_user_id == user_id)
    if action:
        stmt = stmt.where(MeetingEgressAuditEvent.event_type == action)
    if object_id:
        meeting_id = _uuid_or_none(object_id)
        if meeting_id is None:
            return []
        stmt = stmt.where(MeetingEgressAuditEvent.meeting_id == meeting_id)
    if outcome:
        stmt = stmt.where(MeetingEgressAuditEvent.outcome == outcome)
    return (
        await db.execute(stmt.order_by(MeetingEgressAuditEvent.created_at.desc()).limit(limit))
    ).scalars().all()


async def _lifecycle_events(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    date_from: date | None,
    date_to: date | None,
    user_id: UUID | None,
    action: str | None,
    object_kind: str | None,
    object_id: str | None,
    outcome: str | None,
    limit: int,
) -> list[MeetingLifecycleAuditEvent]:
    if object_kind and object_kind != "meeting":
        return []
    stmt = select(MeetingLifecycleAuditEvent).where(
        MeetingLifecycleAuditEvent.workspace_id == context.workspace_id
    )
    stmt = _with_date_filters(
        stmt, MeetingLifecycleAuditEvent.created_at, date_from=date_from, date_to=date_to
    )
    if user_id:
        stmt = stmt.where(MeetingLifecycleAuditEvent.actor_user_id == user_id)
    if action:
        stmt = stmt.where(MeetingLifecycleAuditEvent.event_type == action)
    if object_id:
        meeting_id = _uuid_or_none(object_id)
        if meeting_id is None:
            return []
        stmt = stmt.where(MeetingLifecycleAuditEvent.meeting_id == meeting_id)
    if outcome:
        stmt = stmt.where(MeetingLifecycleAuditEvent.outcome == outcome)
    return (
        await db.execute(stmt.order_by(MeetingLifecycleAuditEvent.created_at.desc()).limit(limit))
    ).scalars().all()


def _with_date_filters(stmt, created_at, *, date_from: date | None, date_to: date | None):
    if date_from:
        stmt = stmt.where(created_at >= datetime.combine(date_from, time.min, tzinfo=UTC))
    if date_to:
        exclusive_end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)
        stmt = stmt.where(created_at < exclusive_end)
    return stmt


def _uuid_or_none(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None
