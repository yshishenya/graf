from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.db.models import (
    AdminAuditEvent,
    Meeting,
    Workspace,
    WorkspaceInvitation,
    WorkspaceMembership,
    WorkspaceUsageDaily,
)


@dataclass(frozen=True, slots=True)
class AdminWorkspaceContext:
    workspace_id: UUID
    workspace_name: str
    actor_user_id: UUID
    actor_role: str


async def load_admin_workspace_context(
    db: AsyncSession,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
) -> AdminWorkspaceContext:
    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == tenant_scope.workspace_id,
            WorkspaceMembership.user_id == principal.user_id,
            WorkspaceMembership.status == "active",
        )
    )
    if membership is None or membership.role not in {"owner", "admin"}:
        raise ProblemDetail(status=403, code="admin_forbidden", title="Admin access is restricted")
    workspace = await db.get(Workspace, tenant_scope.workspace_id)
    return AdminWorkspaceContext(
        workspace_id=tenant_scope.workspace_id,
        workspace_name=workspace.name if workspace is not None else "Рабочая область",
        actor_user_id=principal.user_id,
        actor_role=membership.role,
    )


async def get_admin_overview_payload(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
) -> dict[str, object]:
    return {
        "workspace_id": str(context.workspace_id),
        "actor": {"user_id": str(context.actor_user_id), "role": context.actor_role},
        "user_counts": await _user_counts(db, context.workspace_id),
        "usage_summary": await _usage_summary(db, context.workspace_id),
        "file_summary": await _file_summary(db, context.workspace_id),
        "metrics_summary": {"families": [], "freshness": "unavailable"},
        "recent_audit": await _recent_admin_audit(db, context.workspace_id),
    }


async def _user_counts(db: AsyncSession, workspace_id: UUID) -> dict[str, int]:
    counts = {"active": 0, "pending": 0, "inactive": 0, "blocked": 0, "revoked": 0}
    rows = (
        await db.execute(
            select(WorkspaceMembership.status, func.count())
            .where(WorkspaceMembership.workspace_id == workspace_id)
            .group_by(WorkspaceMembership.status)
        )
    ).all()
    for status, count in rows:
        if status in counts:
            counts[status] = int(count)
    counts["pending"] = int(
        await db.scalar(
            select(func.count())
            .select_from(WorkspaceInvitation)
            .where(
                WorkspaceInvitation.workspace_id == workspace_id,
                WorkspaceInvitation.status == "pending",
            )
        )
        or 0
    )
    return counts


async def _usage_summary(db: AsyncSession, workspace_id: UUID) -> dict[str, object]:
    rows = (
        (
            await db.execute(
                select(WorkspaceUsageDaily).where(WorkspaceUsageDaily.workspace_id == workspace_id)
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return {
            "recording_minutes": 0,
            "storage_bytes": 0,
            "processing_jobs": 0,
            "quota_risk": "not_configured",
            "freshness": "unknown",
        }
    freshness = "fresh" if all(row.freshness_state == "fresh" for row in rows) else "incomplete"
    return {
        "recording_minutes": sum(row.recording_minutes for row in rows),
        "storage_bytes": sum(row.storage_bytes for row in rows),
        "processing_jobs": sum(row.processing_jobs for row in rows),
        "quota_risk": "not_configured",
        "freshness": freshness,
    }


async def _file_summary(db: AsyncSession, workspace_id: UUID) -> dict[str, int]:
    rows = (
        await db.execute(
            select(Meeting.deletion_state, Meeting.processing_status, func.count())
            .where(Meeting.workspace_id == workspace_id)
            .group_by(Meeting.deletion_state, Meeting.processing_status)
        )
    ).all()
    summary = {"server_known_meetings": 0, "deleting": 0, "problem": 0}
    for deletion_state, processing_status, count in rows:
        value = int(count)
        summary["server_known_meetings"] += value
        if deletion_state in {"deleting", "deleted"}:
            summary["deleting"] += value
        if processing_status in {"failed_terminal", "blocked"}:
            summary["problem"] += value
    return summary


async def _recent_admin_audit(db: AsyncSession, workspace_id: UUID) -> list[dict[str, object]]:
    rows = (
        (
            await db.execute(
                select(AdminAuditEvent)
                .where(AdminAuditEvent.workspace_id == workspace_id)
                .order_by(AdminAuditEvent.created_at.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "event_id": str(row.id),
            "action": row.action,
            "target_kind": row.target_kind,
            "outcome": row.outcome,
            "created_at": row.created_at.isoformat() if row.created_at is not None else None,
        }
        for row in rows
    ]
