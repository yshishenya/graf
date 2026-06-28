from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.admin.queries import AdminWorkspaceContext
from twobrain_rec_server.db.models import UserUsageDaily, WorkspaceQuotaPolicy, WorkspaceUsageDaily


def quota_risk_state(*, used: int, limit: int | None) -> str:
    if limit is None or limit <= 0:
        return "not_configured"
    if used >= limit:
        return "exceeded"
    if used >= int(limit * 0.8):
        return "near_limit"
    return "ok"


def summarize_usage_rows(rows: list[Mapping[str, Any]]) -> dict[str, object]:
    freshness_states = {str(row.get("freshness_state") or "unknown") for row in rows}
    usage_dates = sorted(row.get("usage_date") for row in rows if row.get("usage_date") is not None)
    if not rows:
        freshness = "unknown"
    elif freshness_states == {"fresh"}:
        freshness = "fresh"
    else:
        freshness = "incomplete"
    return {
        "recording_minutes": sum(int(row.get("recording_minutes") or 0) for row in rows),
        "storage_bytes": sum(int(row.get("storage_bytes") or 0) for row in rows),
        "processing_jobs": sum(int(row.get("processing_jobs") or 0) for row in rows),
        "freshness": freshness,
        "date_window": {
            "from": usage_dates[0].isoformat() if usage_dates else None,
            "to": usage_dates[-1].isoformat() if usage_dates else None,
        },
    }


async def get_usage_summary(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 10,
) -> dict[str, object]:
    workspace_stmt = select(WorkspaceUsageDaily).where(
        WorkspaceUsageDaily.workspace_id == context.workspace_id
    )
    user_stmt = select(UserUsageDaily).where(UserUsageDaily.workspace_id == context.workspace_id)
    if date_from is not None:
        workspace_stmt = workspace_stmt.where(WorkspaceUsageDaily.usage_date >= date_from)
        user_stmt = user_stmt.where(UserUsageDaily.usage_date >= date_from)
    if date_to is not None:
        workspace_stmt = workspace_stmt.where(WorkspaceUsageDaily.usage_date <= date_to)
        user_stmt = user_stmt.where(UserUsageDaily.usage_date <= date_to)
    workspace_rows = (await db.execute(workspace_stmt)).scalars().all()
    user_rows = (await db.execute(user_stmt)).scalars().all()
    policy = await load_quota_policy(db, context=context)
    totals = summarize_usage_rows(
        [
            {
                "usage_date": row.usage_date,
                "recording_minutes": row.recording_minutes,
                "storage_bytes": row.storage_bytes,
                "processing_jobs": row.processing_jobs,
                "freshness_state": row.freshness_state,
            }
            for row in workspace_rows
        ]
    )
    if not totals["date_window"]["from"] and (date_from or date_to):
        totals["date_window"] = {
            "from": date_from.isoformat() if date_from else None,
            "to": date_to.isoformat() if date_to else None,
        }
    top_consumers = _summarize_user_usage_rows(user_rows, limit=limit)
    return {
        "totals": totals,
        "quota_risk": {
            "recording_minutes": quota_risk_state(
                used=int(totals["recording_minutes"]),
                limit=policy.get("recording_minutes_limit"),
            ),
            "storage_bytes": quota_risk_state(
                used=int(totals["storage_bytes"]),
                limit=policy.get("storage_bytes_limit"),
            ),
            "processing_jobs": quota_risk_state(
                used=int(totals["processing_jobs"]),
                limit=policy.get("processing_jobs_limit"),
            ),
        },
        "top_consumers": top_consumers,
        "policy": policy,
    }


async def load_quota_policy(db: AsyncSession, *, context: AdminWorkspaceContext) -> dict[str, Any]:
    policy = await db.scalar(
        select(WorkspaceQuotaPolicy).where(
            WorkspaceQuotaPolicy.workspace_id == context.workspace_id
        )
    )
    if policy is None:
        return {
            "status": "not_configured",
            "recording_minutes_limit": None,
            "storage_bytes_limit": None,
            "processing_jobs_limit": None,
            "policy_source": "not_configured",
        }
    return {
        "status": policy.status,
        "recording_minutes_limit": policy.recording_minutes_limit,
        "storage_bytes_limit": policy.storage_bytes_limit,
        "processing_jobs_limit": policy.processing_jobs_limit,
        "policy_source": policy.policy_source,
        "effective_from": policy.effective_from.isoformat() if policy.effective_from else None,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
    }


def _summarize_user_usage_rows(
    rows: list[UserUsageDaily], *, limit: int
) -> list[dict[str, object]]:
    by_user: dict[Any, dict[str, object]] = {}
    for row in rows:
        current = by_user.setdefault(
            row.user_id,
            {
                "user_id": str(row.user_id),
                "recording_minutes": 0,
                "storage_bytes": 0,
                "processing_jobs": 0,
                "file_count": 0,
                "freshness": "fresh",
            },
        )
        current["recording_minutes"] = int(current["recording_minutes"]) + row.recording_minutes
        current["storage_bytes"] = int(current["storage_bytes"]) + row.storage_bytes
        current["processing_jobs"] = int(current["processing_jobs"]) + row.processing_jobs
        current["file_count"] = int(current["file_count"]) + row.file_count
        if row.freshness_state != "fresh":
            current["freshness"] = row.freshness_state
    return sorted(by_user.values(), key=lambda item: int(item["recording_minutes"]), reverse=True)[
        :limit
    ]
