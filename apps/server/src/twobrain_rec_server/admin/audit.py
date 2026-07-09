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
    UserIdentity,
    WorkspaceMembership,
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

SOURCE_LABELS = {
    "admin_audit_events": "Админские действия",
    "auth_audit_events": "Авторизация",
    "meeting_egress_audit_events": "Доступ к файлам встречи",
    "meeting_lifecycle_audit_events": "Жизненный цикл встречи",
}

ACTION_LABELS = {
    "membership_updated": "Изменение роли или статуса пользователя",
    "quota_viewed": "Просмотр квоты",
    "provider_callback_success": "Успешная авторизация через провайдера",
    "deletion_requested": "Запрос удаления встречи",
}

OUTCOME_LABELS = {
    "accepted": "Принято",
    "allowed": "Разрешено",
    "blocked": "Заблокировано",
    "completed": "Выполнено",
    "denied": "Запрещено",
    "failed": "Ошибка",
    "success": "Успешно",
}


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
    user_lookup = await _load_audit_user_lookup(
        db,
        context=context,
        user_ids=_collect_user_ids(
            admin_events=admin_events,
            auth_events=auth_events,
            egress_events=egress_events,
            lifecycle_events=lifecycle_events,
        ),
    )
    entries = [
        _entry(
            event_id=str(event.id),
            source="admin_audit_events",
            actor_user_id=event.actor_user_id,
            actor_role=event.actor_role,
            action=event.action,
            object_kind=event.target_kind,
            object_id=event.target_id,
            outcome=event.outcome,
            reason_code=event.reason_code,
            created_at=event.created_at,
            metadata_safe_summary=event.reason_code or event.outcome,
            drill_down_path=_admin_drill_down_path(event.target_kind, event.target_id),
            user_lookup=user_lookup,
        )
        for event in admin_events
    ]
    entries.extend(
        _entry(
            event_id=str(event.id),
            source="auth_audit_events",
            actor_user_id=event.actor_user_id or event.user_id,
            actor_role=None,
            action=event.event_type,
            object_kind="auth",
            object_id=event.provider,
            outcome=event.outcome,
            reason_code=None,
            created_at=event.created_at,
            metadata_safe_summary=event.outcome,
            drill_down_path=f"/admin/users/{event.user_id}" if event.user_id else "/admin/users",
            user_lookup=user_lookup,
        )
        for event in auth_events
    )
    entries.extend(
        _entry(
            event_id=str(event.id),
            source="meeting_egress_audit_events",
            actor_user_id=event.actor_user_id,
            actor_role=None,
            action=event.event_type,
            object_kind="meeting",
            object_id=str(event.meeting_id) if event.meeting_id else None,
            outcome=event.outcome,
            reason_code=event.policy_reason,
            created_at=event.created_at,
            metadata_safe_summary=event.policy_reason or event.outcome,
            drill_down_path=f"/admin/files/{event.meeting_id}" if event.meeting_id else "/admin/files",
            user_lookup=user_lookup,
        )
        for event in egress_events
    )
    entries.extend(
        _entry(
            event_id=str(event.id),
            source="meeting_lifecycle_audit_events",
            actor_user_id=event.actor_user_id,
            actor_role=None,
            action=event.event_type,
            object_kind="meeting",
            object_id=str(event.meeting_id) if event.meeting_id else None,
            outcome=event.outcome,
            reason_code=event.safe_reason,
            created_at=event.created_at,
            metadata_safe_summary=event.safe_reason or event.outcome,
            drill_down_path=f"/admin/files/{event.meeting_id}" if event.meeting_id else "/admin/files",
            user_lookup=user_lookup,
        )
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


async def _load_audit_user_lookup(
    db: AsyncSession, *, context: AdminWorkspaceContext, user_ids: set[UUID]
) -> dict[UUID, dict[str, object]]:
    if not user_ids:
        return {}
    rows = (
        await db.execute(
            select(WorkspaceMembership, UserIdentity)
            .join(UserIdentity, UserIdentity.id == WorkspaceMembership.user_id)
            .where(
                WorkspaceMembership.workspace_id == context.workspace_id,
                WorkspaceMembership.user_id.in_(user_ids),
            )
        )
    ).all()
    return {
        membership.user_id: {
            "display_name": user.display_name,
            "role": membership.role,
            "status": membership.status,
        }
        for membership, user in rows
    }


def _collect_user_ids(
    *,
    admin_events: list[AdminAuditEvent],
    auth_events: list[AuthAuditEvent],
    egress_events: list[MeetingEgressAuditEvent],
    lifecycle_events: list[MeetingLifecycleAuditEvent],
) -> set[UUID]:
    user_ids: set[UUID] = set()
    for event in admin_events:
        if event.actor_user_id:
            user_ids.add(event.actor_user_id)
        if event.target_kind == "user" and event.target_id:
            user_id = _uuid_or_none(event.target_id)
            if user_id:
                user_ids.add(user_id)
    for event in auth_events:
        if event.actor_user_id:
            user_ids.add(event.actor_user_id)
        if event.user_id:
            user_ids.add(event.user_id)
    for event in egress_events:
        if event.actor_user_id:
            user_ids.add(event.actor_user_id)
    for event in lifecycle_events:
        if event.actor_user_id:
            user_ids.add(event.actor_user_id)
    return user_ids


def _entry(
    *,
    event_id: str,
    source: str,
    actor_user_id: UUID | None,
    actor_role: str | None,
    action: str,
    object_kind: str,
    object_id: str | None,
    outcome: str,
    reason_code: str | None,
    created_at: datetime | None,
    metadata_safe_summary: str | None,
    drill_down_path: str,
    user_lookup: dict[UUID, dict[str, object]],
) -> dict[str, object]:
    actor = _actor_model(actor_user_id, actor_role=actor_role, user_lookup=user_lookup)
    target = _target_model(object_kind, object_id)
    summary_parts = [ACTION_LABELS.get(action, _humanize_token(action)), target["label"]]
    if reason_code:
        summary_parts.append(f"причина: {reason_code}")
    return {
        "event_id": event_id,
        "source": source,
        "source_label": SOURCE_LABELS.get(source, source),
        "actor_user_id": str(actor_user_id) if actor_user_id else None,
        "actor_label": actor["label"],
        "actor_role": actor["role"],
        "actor_href": actor["href"],
        "action": action,
        "action_label": ACTION_LABELS.get(action, _humanize_token(action)),
        "object_kind": object_kind,
        "object_id": object_id,
        "object_label": target["label"],
        "object_href": target["href"],
        "outcome": outcome,
        "outcome_label": OUTCOME_LABELS.get(outcome, _humanize_token(outcome)),
        "reason_code": reason_code,
        "created_at": created_at.isoformat() if created_at else None,
        "created_at_label": created_at.strftime("%Y-%m-%d %H:%M:%S %Z") if created_at else "нет времени",
        "metadata_safe_summary": metadata_safe_summary,
        "summary": " · ".join(part for part in summary_parts if part),
        "drill_down_path": drill_down_path,
        "drill_down_label": _drill_down_label(drill_down_path),
    }


def _actor_model(
    actor_user_id: UUID | None,
    *,
    actor_role: str | None,
    user_lookup: dict[UUID, dict[str, object]],
) -> dict[str, object | None]:
    if actor_user_id is None:
        return {"label": "Система или неизвестный пользователь", "role": actor_role, "href": None}
    user = user_lookup.get(actor_user_id, {})
    display_name = user.get("display_name")
    role = actor_role or user.get("role")
    label = str(display_name) if display_name else f"Пользователь {_short_id(str(actor_user_id))}"
    if role:
        label = f"{label} · {role}"
    return {"label": label, "role": role, "href": f"/admin/users/{actor_user_id}"}


def _target_model(object_kind: str, object_id: str | None) -> dict[str, str | None]:
    if object_kind == "meeting":
        return {
            "label": f"Встреча {_short_id(object_id)}" if object_id else "Встреча без ID",
            "href": f"/admin/files/{object_id}" if object_id else "/admin/files",
        }
    if object_kind == "user":
        return {
            "label": f"Пользователь {_short_id(object_id)}" if object_id else "Пользователь",
            "href": f"/admin/users/{object_id}" if object_id else "/admin/users",
        }
    if object_kind == "auth":
        return {
            "label": f"Авторизация: {object_id}" if object_id else "Авторизация",
            "href": None,
        }
    if object_kind == "quota":
        return {"label": "Квота рабочей области", "href": "/admin/balance"}
    label = _humanize_token(object_kind)
    if object_id:
        label = f"{label}: {_short_id(object_id)}"
    return {"label": label, "href": None}


def _admin_drill_down_path(object_kind: str, object_id: str | None) -> str:
    if object_kind == "user" and object_id:
        return f"/admin/users/{object_id}"
    if object_kind == "meeting" and object_id:
        return f"/admin/files/{object_id}"
    if object_kind == "quota":
        return "/admin/balance"
    return "/admin/audit"


def _drill_down_label(path: str) -> str:
    if path.startswith("/admin/users/"):
        return "Открыть пользователя"
    if path.startswith("/admin/files/"):
        return "Открыть встречу"
    if path == "/admin/users":
        return "Открыть пользователей"
    if path == "/admin/files":
        return "Открыть файлы"
    if path == "/admin/balance":
        return "Открыть баланс"
    return "Открыть аудит"


def _humanize_token(value: str | None) -> str:
    if not value:
        return "нет значения"
    return value.replace("_", " ")


def _short_id(value: str | None) -> str:
    if not value:
        return "без ID"
    return value[:8]


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
