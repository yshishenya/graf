from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.admin.queries import AdminWorkspaceContext
from twobrain_rec_server.db.models import (
    AdminAuditEvent,
    Meeting,
    WorkspaceMembership,
    WorkspaceUsageDaily,
)

METRIC_FAMILIES = ("adoption", "usage", "funnel", "reliability", "governance")


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
    audit_events = int(
        await db.scalar(
            select(func.count())
            .select_from(AdminAuditEvent)
            .where(AdminAuditEvent.workspace_id == context.workspace_id)
        )
        or 0
    )
    cards = [
        _card(
            "active_users",
            "adoption",
            "Активные пользователи",
            "Активные memberships",
            "workspace members",
            "identity",
            active_users,
            "/admin/users",
            date_window=usage_window,
        ),
        _card(
            "recording_minutes",
            "usage",
            "Минуты записи",
            "Сумма source-backed usage rollups",
            "workspace usage days",
            "usage_rollup",
            recording_minutes,
            "/admin/balance",
            date_window=usage_window,
            freshness=usage_freshness,
        ),
        _card(
            "server_known_meetings",
            "funnel",
            "Серверные встречи",
            "Встречи, принятые сервером",
            "meetings",
            "meeting_store",
            meetings_total,
            "/admin/files",
            date_window=usage_window,
        ),
        _card(
            "problem_meetings",
            "reliability",
            "Проблемные встречи",
            "Встречи с terminal/blocked processing",
            "meetings",
            "meeting_store",
            problem_meetings,
            "/admin/files",
            date_window=usage_window,
        ),
        _card(
            "admin_audit_events",
            "governance",
            "События аудита",
            "Metadata-only admin audit events",
            "admin audit events",
            "audit_journal",
            audit_events,
            "/admin/audit",
            date_window=usage_window,
        ),
    ]
    if family:
        cards = [card for card in cards if card["family"] == family]
    return {"metrics": cards}


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
) -> dict[str, object]:
    return {
        "metric_id": metric_id,
        "family": family,
        "label": label,
        "definition": definition,
        "denominator": denominator,
        "source_category": source_category,
        "date_window": date_window,
        "freshness": freshness,
        "value": value,
        "drill_down_path": drill_down_path,
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
