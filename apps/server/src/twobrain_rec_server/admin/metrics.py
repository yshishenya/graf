from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.admin.queries import AdminWorkspaceContext
from twobrain_rec_server.db.models import (
    AdminAuditEvent,
    AuthAuditEvent,
    Meeting,
    MeetingEgressAuditEvent,
    MeetingLifecycleAuditEvent,
    WorkspaceMembership,
    WorkspaceUsageDaily,
)

METRIC_FAMILIES = ("adoption", "usage", "funnel", "reliability", "governance")

FAMILY_LABELS = {
    "adoption": "Принятие продукта",
    "usage": "Использование",
    "funnel": "Воронка встреч",
    "reliability": "Надежность",
    "governance": "Контроль и аудит",
}


def metric_families() -> list[str]:
    return list(METRIC_FAMILIES)


async def get_admin_metrics(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    family: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, object]:
    active_users = int(
        await db.scalar(
            select(func.count())
            .select_from(WorkspaceMembership)
            .where(
                WorkspaceMembership.workspace_id == context.workspace_id,
                WorkspaceMembership.status == "active",
            )
        )
        or 0
    )
    usage_stmt = select(WorkspaceUsageDaily).where(
        WorkspaceUsageDaily.workspace_id == context.workspace_id
    )
    if date_from is not None:
        usage_stmt = usage_stmt.where(WorkspaceUsageDaily.usage_date >= date_from)
    if date_to is not None:
        usage_stmt = usage_stmt.where(WorkspaceUsageDaily.usage_date <= date_to)
    usage_rows = (await db.execute(usage_stmt)).scalars().all()
    recording_minutes = sum(row.recording_minutes for row in usage_rows)
    usage_window = _usage_date_window(usage_rows, date_from=date_from, date_to=date_to)
    usage_freshness = _usage_freshness(usage_rows)
    meetings_total = int(
        await db.scalar(
            select(func.count())
            .select_from(Meeting)
            .where(Meeting.workspace_id == context.workspace_id)
        )
        or 0
    )
    problem_meetings = int(
        await db.scalar(
            select(func.count())
            .select_from(Meeting)
            .where(
                Meeting.workspace_id == context.workspace_id,
                Meeting.processing_status.in_(("failed_terminal", "blocked")),
            )
        )
        or 0
    )
    audit_breakdown = {
        "Админские действия": await _count_audit_rows(
            db, AdminAuditEvent, context=context, date_from=date_from, date_to=date_to
        ),
        "Авторизация": await _count_audit_rows(
            db, AuthAuditEvent, context=context, date_from=date_from, date_to=date_to
        ),
        "Доступ к файлам встречи": await _count_audit_rows(
            db, MeetingEgressAuditEvent, context=context, date_from=date_from, date_to=date_to
        ),
        "Жизненный цикл встречи": await _count_audit_rows(
            db, MeetingLifecycleAuditEvent, context=context, date_from=date_from, date_to=date_to
        ),
    }
    audit_events = sum(audit_breakdown.values())
    cards = [
        _card(
            "active_users",
            "adoption",
            "Активные пользователи",
            "Сколько людей сейчас может пользоваться этой рабочей областью.",
            "активные записи workspace_memberships",
            "identity",
            active_users,
            "/admin/users",
            date_window=usage_window,
            question="Кто реально имеет доступ к продукту?",
            drill_down_label="Открыть пользователей",
            value_unit="пользователей",
        ),
        _card(
            "recording_minutes",
            "usage",
            "Минуты записи",
            "Сколько минут записи накоплено по проверенным дневным rollup-строкам.",
            "дни из workspace_usage_daily",
            "usage_rollup",
            recording_minutes,
            "/admin/balance",
            date_window=usage_window,
            freshness=usage_freshness,
            question="Сколько продуктом пользовались в выбранном окне?",
            drill_down_label="Открыть баланс",
            value_unit="минут",
        ),
        _card(
            "server_known_meetings",
            "funnel",
            "Серверные встречи",
            "Сколько встреч уже известно серверу и попало в хранилище метаданных.",
            "meetings",
            "meeting_store",
            meetings_total,
            "/admin/files",
            date_window=usage_window,
            question="Сколько встреч дошло до серверной части продукта?",
            drill_down_label="Открыть файлы",
            value_unit="встреч",
        ),
        _card(
            "problem_meetings",
            "reliability",
            "Проблемные встречи",
            "Сколько встреч остановилось в terminal/blocked processing-состоянии.",
            "meetings",
            "meeting_store",
            problem_meetings,
            "/admin/files",
            date_window=usage_window,
            question="Где нужно смотреть сбои обработки?",
            drill_down_label="Открыть проблемные файлы",
            value_unit="встреч",
        ),
        _card(
            "admin_audit_events",
            "governance",
            "События аудита",
            "Сколько metadata-only событий контроля есть по админке, авторизации и файлам.",
            "audit events",
            "audit_journal",
            audit_events,
            "/admin/audit",
            date_window=usage_window,
            question="Кто что сделал и где это проверить?",
            drill_down_label="Открыть журнал аудита",
            value_unit="событий",
            breakdown=[
                {"label": label, "value": value} for label, value in audit_breakdown.items()
            ],
        ),
    ]
    if family:
        cards = [card for card in cards if card["family"] == family]
    return {
        "metrics": cards,
        "family_options": [
            {"value": value, "label": FAMILY_LABELS[value]} for value in METRIC_FAMILIES
        ],
    }


def _card(
    metric_id: str,
    family: str,
    label: str,
    definition: str,
    denominator: str,
    source_category: str,
    value: int,
    drill_down_path: str,
    date_window: dict[str, str | None],
    freshness: str = "source_backed",
    question: str | None = None,
    drill_down_label: str = "Открыть",
    value_unit: str | None = None,
    breakdown: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "metric_id": metric_id,
        "family": family,
        "family_label": FAMILY_LABELS.get(family, family),
        "label": label,
        "definition": definition,
        "question": question,
        "denominator": denominator,
        "source_category": source_category,
        "date_window": date_window,
        "freshness": freshness,
        "value": value,
        "value_label": f"{value} {value_unit}" if value_unit else str(value),
        "drill_down_path": drill_down_path,
        "drill_down_label": drill_down_label,
        "breakdown": breakdown or [],
    }


def _usage_date_window(
    rows: list[WorkspaceUsageDaily],
    *,
    date_from: date | None,
    date_to: date | None,
) -> dict[str, str | None]:
    row_dates = sorted(row.usage_date for row in rows)
    return {
        "from": (date_from or (row_dates[0] if row_dates else None)).isoformat()
        if (date_from or row_dates)
        else None,
        "to": (date_to or (row_dates[-1] if row_dates else None)).isoformat()
        if (date_to or row_dates)
        else None,
    }


def _usage_freshness(rows: list[WorkspaceUsageDaily]) -> str:
    if not rows:
        return "unavailable"
    if all(row.freshness_state == "fresh" for row in rows):
        return "fresh"
    return "incomplete"


async def _count_audit_rows(
    db: AsyncSession,
    model,
    *,
    context: AdminWorkspaceContext,
    date_from: date | None,
    date_to: date | None,
) -> int:
    stmt = select(func.count()).select_from(model).where(model.workspace_id == context.workspace_id)
    if date_from is not None:
        stmt = stmt.where(func.date(model.created_at) >= date_from)
    if date_to is not None:
        stmt = stmt.where(func.date(model.created_at) <= date_to)
    return int(await db.scalar(stmt) or 0)
