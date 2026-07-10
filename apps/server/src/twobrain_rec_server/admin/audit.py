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
    CalendarAuditEvent,
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
    "calendar_audit_events": "Календарь",
    "meeting_egress_audit_events": "Доступ к файлам встречи",
    "meeting_lifecycle_audit_events": "Жизненный цикл встречи",
}

ACTION_LABELS = {
    "add_diagnostic_only_draft": "Добавление диагностического кандидата ВКС",
    "browser_logout": "Выход из браузерной сессии",
    "calendar_connect_result": "Подключение календаря завершено",
    "calendar_connect_start": "Подключение календаря начато",
    "calendar_context_deletion_accounted": "Календарный контекст учтен при удалении",
    "calendar_disconnect_confirmed": "Отключение календаря подтверждено",
    "calendar_disconnect_result": "Отключение календаря завершено",
    "calendar_manual_sync_requested": "Ручная синхронизация календаря запрошена",
    "calendar_manual_sync_result": "Ручная синхронизация календаря завершена",
    "deletion_requested": "Запрос удаления встречи",
    "device_registered": "Устройство зарегистрировано",
    "device_revoked": "Устройство отозвано",
    "download_completed": "Скачивание завершено",
    "download_denied": "Скачивание запрещено",
    "download_requested": "Запрос скачивания",
    "email_auth_completed": "Вход по email завершен",
    "email_auth_started": "Вход по email начат",
    "export_completed": "Экспорт завершен",
    "export_denied": "Экспорт запрещен",
    "export_requested": "Запрос экспорта",
    "file_review_accessed": "Проверка доступа к файлу встречи",
    "invite_completed": "Приглашение принято",
    "invite_created": "Приглашение создано",
    "invite_revoked": "Приглашение отозвано",
    "local_purge_acknowledged": "Локальное удаление подтверждено",
    "mark_non_target": "Кандидат ВКС помечен как нецелевой",
    "merge_existing_target": "Кандидат ВКС привязан к существующей встрече",
    "membership_updated": "Изменение роли или статуса пользователя",
    "playback_completed": "Воспроизведение завершено",
    "playback_denied": "Воспроизведение запрещено",
    "playback_requested": "Запрос воспроизведения",
    "provider_auth_started": "Авторизация через провайдера начата",
    "provider_callback_failed": "Авторизация через провайдера не прошла",
    "provider_link_confirmed": "Связь с провайдером подтверждена",
    "provider_link_conflict": "Конфликт связи с провайдером",
    "provider_link_rejected": "Связь с провайдером отклонена",
    "provider_link_requested": "Связь с провайдером запрошена",
    "quota_viewed": "Просмотр квоты",
    "publish_registry_version": "Версия ВКС-реестра опубликована",
    "provider_callback_success": "Успешная авторизация через провайдера",
    "retention_evaluated": "Проверка retention-политики",
    "retention_policy_blocked": "Retention-политика заблокировала удаление",
    "share_granted": "Доступ к встрече выдан",
    "share_link_opened": "Ссылка доступа к встрече открыта",
    "share_revoked": "Доступ к встрече отозван",
    "workspace_auth_policy_updated": "Политика входа рабочей области обновлена",
}

OBJECT_KIND_LABELS = {
    "auth": "Авторизация",
    "calendar": "Календарь",
    "calendar_event": "Календарное событие",
    "calendar_source": "Календарный источник",
    "invitation": "Приглашение",
    "meeting": "Встреча",
    "meeting_detection_candidate": "Кандидат ВКС",
    "meeting_detection_registry_version": "Версия ВКС-реестра",
    "quota": "Квота",
    "user": "Пользователь",
}

OUTCOME_LABELS = {
    "accepted": "Принято",
    "allowed": "Разрешено",
    "blocked": "Заблокировано",
    "already_running": "Уже выполняется",
    "cancelled": "Отменено",
    "completed": "Выполнено",
    "denied": "Запрещено",
    "failed": "Ошибка",
    "failure": "Ошибка",
    "no_readable_calendars": "Нет доступных календарей",
    "partial": "Частично выполнено",
    "pending": "Ожидает",
    "pilot_blocked": "Пилот заблокирован",
    "reconnect_required": "Нужно переподключить",
    "skipped": "Пропущено",
    "success": "Успешно",
    "unavailable": "Недоступно",
}

CALENDAR_OBJECT_KINDS = {"calendar", "calendar_event", "calendar_source", "meeting"}


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
    calendar_events = await _calendar_events(
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
            calendar_events=calendar_events,
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
    entries.extend(
        _entry(
            event_id=str(event.id),
            source="calendar_audit_events",
            actor_user_id=event.actor_user_id,
            actor_role=None,
            action=event.event_type,
            object_kind=_calendar_object_kind(event),
            object_id=_calendar_object_id(event),
            outcome=event.outcome,
            reason_code=event.safe_reason_code,
            created_at=event.created_at,
            metadata_safe_summary=event.safe_reason_code or event.outcome,
            drill_down_path=_calendar_drill_down_path(event),
            user_lookup=user_lookup,
        )
        for event in calendar_events
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
        "filter_options": audit_filter_options(),
    }


def audit_filter_options() -> dict[str, list[dict[str, str]]]:
    return {
        "actions": _label_options(ACTION_LABELS),
        "object_kinds": _label_options(OBJECT_KIND_LABELS),
        "outcomes": _label_options(OUTCOME_LABELS),
    }


def _label_options(labels: Mapping[str, str]) -> list[dict[str, str]]:
    return [{"value": value, "label": label} for value, label in labels.items()]


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
    calendar_events: list[CalendarAuditEvent],
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
    for event in calendar_events:
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
    action_label = ACTION_LABELS.get(action, _humanize_token(action))
    object_kind_label = OBJECT_KIND_LABELS.get(object_kind, _humanize_token(object_kind))
    summary_parts = [action_label, target["label"]]
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
        "action_label": action_label,
        "object_kind": object_kind,
        "object_kind_label": object_kind_label,
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
    if object_kind == "calendar_source":
        return {
            "label": f"Календарный источник {_short_id(object_id)}" if object_id else "Календарный источник",
            "href": None,
        }
    if object_kind == "calendar_event":
        return {
            "label": f"Календарное событие {_short_id(object_id)}" if object_id else "Календарное событие",
            "href": None,
        }
    if object_kind == "calendar":
        return {"label": "Календарь", "href": None}
    if object_kind == "quota":
        return {"label": "Квота рабочей области", "href": "/admin/balance"}
    label = OBJECT_KIND_LABELS.get(object_kind, _humanize_token(object_kind))
    if object_id:
        label = f"{label}: {_short_id(object_id)}"
    return {"label": label, "href": None}


def _calendar_object_kind(event: CalendarAuditEvent) -> str:
    if event.calendar_source_id:
        return "calendar_source"
    if event.calendar_event_snapshot_id:
        return "calendar_event"
    if event.meeting_id:
        return "meeting"
    return "calendar"


def _calendar_object_id(event: CalendarAuditEvent) -> str | None:
    if event.calendar_source_id:
        return str(event.calendar_source_id)
    if event.calendar_event_snapshot_id:
        return str(event.calendar_event_snapshot_id)
    if event.meeting_id:
        return str(event.meeting_id)
    return None


def _admin_drill_down_path(object_kind: str, object_id: str | None) -> str:
    if object_kind == "user" and object_id:
        return f"/admin/users/{object_id}"
    if object_kind == "meeting" and object_id:
        return f"/admin/files/{object_id}"
    if object_kind == "quota":
        return "/admin/balance"
    return "/admin/audit"


def _calendar_drill_down_path(event: CalendarAuditEvent) -> str:
    if event.meeting_id:
        return f"/admin/files/{event.meeting_id}"
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


async def _calendar_events(
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
) -> list[CalendarAuditEvent]:
    if object_kind and object_kind not in CALENDAR_OBJECT_KINDS:
        return []
    stmt = select(CalendarAuditEvent).where(CalendarAuditEvent.workspace_id == context.workspace_id)
    stmt = _with_date_filters(stmt, CalendarAuditEvent.created_at, date_from=date_from, date_to=date_to)
    if user_id:
        stmt = stmt.where(CalendarAuditEvent.actor_user_id == user_id)
    if action:
        stmt = stmt.where(CalendarAuditEvent.event_type == action)
    if object_kind == "calendar_source":
        stmt = stmt.where(CalendarAuditEvent.calendar_source_id.is_not(None))
    elif object_kind == "calendar_event":
        stmt = stmt.where(CalendarAuditEvent.calendar_event_snapshot_id.is_not(None))
    elif object_kind == "meeting":
        stmt = stmt.where(CalendarAuditEvent.meeting_id.is_not(None))
    elif object_kind == "calendar":
        stmt = stmt.where(
            CalendarAuditEvent.calendar_source_id.is_(None),
            CalendarAuditEvent.calendar_event_snapshot_id.is_(None),
            CalendarAuditEvent.meeting_id.is_(None),
        )
    if object_id:
        object_uuid = _uuid_or_none(object_id)
        if object_uuid is None:
            return []
        if object_kind == "calendar_source":
            stmt = stmt.where(CalendarAuditEvent.calendar_source_id == object_uuid)
        elif object_kind == "calendar_event":
            stmt = stmt.where(CalendarAuditEvent.calendar_event_snapshot_id == object_uuid)
        elif object_kind == "meeting":
            stmt = stmt.where(CalendarAuditEvent.meeting_id == object_uuid)
        elif object_kind == "calendar":
            return []
        else:
            stmt = stmt.where(
                or_(
                    CalendarAuditEvent.calendar_source_id == object_uuid,
                    CalendarAuditEvent.calendar_event_snapshot_id == object_uuid,
                    CalendarAuditEvent.meeting_id == object_uuid,
                )
            )
    if outcome:
        stmt = stmt.where(CalendarAuditEvent.outcome == outcome)
    return (
        await db.execute(stmt.order_by(CalendarAuditEvent.created_at.desc()).limit(limit))
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
