from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import DesktopStorageStatusResponse
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.billing.catalog import (
    FREE_STORAGE_BYTES,
    classify_storage_threshold,
)
from twobrain_rec_server.billing.entitlements import effective_plan_code
from twobrain_rec_server.billing.purchases import effective_paid_storage
from twobrain_rec_server.billing.storage import (
    _active_reserved_bytes,
    project_active_playback_storage,
)
from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.db.models import (
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)

_VALID_PLAN_CODES = frozenset({"free", "trial", "personal"})
_BILLING_STORAGE_PATH = "/billing/storage"


def _retention_state(settings: Settings) -> tuple[int | None, int | None, str]:
    meeting_days = settings.retention_meeting_delete_after_days
    source_days = settings.retention_source_audio_days
    if meeting_days is None:
        return meeting_days, source_days, "not_configured"
    if (
        settings.retention_backup_expiry_days is None
        or settings.retention_local_buffer_expiry_days is None
    ):
        return meeting_days, source_days, "unsafe"
    return meeting_days, source_days, "active"


def _base_response(
    *,
    settings: Settings,
    billing_role: str,
    access_mode: str,
    plan_code: str,
) -> DesktopStorageStatusResponse:
    meeting_days, source_days, retention_state = _retention_state(settings)
    return DesktopStorageStatusResponse(
        billing_role=billing_role,  # type: ignore[arg-type]
        access_mode=access_mode,  # type: ignore[arg-type]
        plan_code=plan_code,
        meeting_retention_days=meeting_days,
        source_audio_retention_days=source_days,
        retention_policy_state=retention_state,  # type: ignore[arg-type]
        observed_at=datetime.now(UTC),
    )


def _member_profile(settings: Settings, *, plan_code: str = "free") -> DesktopStorageStatusResponse:
    """Unknown/member profile: read-only, hidden amounts, no false action."""

    return _base_response(
        settings=settings,
        billing_role="member",
        access_mode="read_only",
        plan_code=plan_code,
    )


async def _resolve_billing_role(
    db: AsyncSession,
    *,
    tenant_scope: TenantScope,
) -> tuple[str, Workspace | None]:
    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == tenant_scope.workspace_id,
            WorkspaceMembership.user_id == tenant_scope.user_id,
            WorkspaceMembership.status == "active",
        )
    )
    if membership is None:
        return "member", None
    workspace = await db.get(Workspace, tenant_scope.workspace_id)
    if membership.role == "owner":
        if (
            workspace is not None
            and workspace.kind == "personal"
            and workspace.owner_user_id == tenant_scope.user_id
        ):
            return "owner", workspace
        if workspace is not None and workspace.kind == "personal":
            # A personal workspace owner marker that disagrees with the
            # membership is not a management right.
            return "member", workspace
        return "admin", workspace
    if membership.role == "admin":
        return "admin", workspace
    return "member", workspace


async def desktop_storage_status(
    db: AsyncSession | None,
    *,
    tenant_scope: TenantScope,
    settings: Settings | None = None,
) -> DesktopStorageStatusResponse:
    """Tenant-scoped, fail-closed storage projection for the desktop client."""

    if db is None:
        raise ProblemDetail(
            status=503,
            code="cabinet_store_unavailable",
            title="Storage status is unavailable",
            headers={"Cache-Control": "no-store"},
        )
    resolved_settings = settings or get_settings()
    try:
        billing_role, _workspace = await _resolve_billing_role(db, tenant_scope=tenant_scope)
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == tenant_scope.workspace_id
            )
        )
    except Exception:
        # A dependency failure after a valid session must stay an explicit
        # unknown instead of a 5xx response.
        return _member_profile(resolved_settings)
    if billing_role not in {"owner", "admin"}:
        billing_role = "member"

    if billing_role == "member":
        member_plan = subscription.plan_code if subscription is not None else "free"
        if member_plan in _VALID_PLAN_CODES:
            member_plan = effective_plan_code(
                plan_code=member_plan,  # type: ignore[arg-type]
                state=subscription.state if subscription is not None else "free",
                now=datetime.now(UTC),
                paid_through=subscription.paid_through if subscription is not None else None,
                trial_ends_at=subscription.trial_ends_at if subscription is not None else None,
            )
        else:
            member_plan = "free"
        return _member_profile(resolved_settings, plan_code=member_plan)

    now = datetime.now(UTC)
    raw_plan_code = subscription.plan_code if subscription is not None else "free"
    plan_known = raw_plan_code in _VALID_PLAN_CODES
    if plan_known:
        plan_code = effective_plan_code(
            plan_code=raw_plan_code,  # type: ignore[arg-type]
            state=subscription.state if subscription is not None else "free",
            now=now,
            paid_through=subscription.paid_through if subscription is not None else None,
            trial_ends_at=subscription.trial_ends_at if subscription is not None else None,
        )
    else:
        plan_code = "free"
    payer_matches = (
        subscription is None
        or subscription.billing_owner_id is None
        or subscription.billing_owner_id == tenant_scope.user_id
    )
    can_manage = billing_role == "owner" and payer_matches and plan_known
    access_mode = "manage" if can_manage else "read_only"
    if not plan_known:
        return _base_response(
            settings=resolved_settings,
            billing_role=billing_role,
            access_mode="read_only",
            plan_code=plan_code,
        )

    try:
        capacity = (
            await effective_paid_storage(db, subscription=subscription, now=now)
            if subscription is not None and plan_code in {"trial", "personal"}
            else FREE_STORAGE_BYTES
        )
        reserved = await _active_reserved_bytes(
            db,
            workspace_id=tenant_scope.workspace_id,
            now=now,
        )
        projection = await project_active_playback_storage(
            db,
            workspace_id=tenant_scope.workspace_id,
            capacity_bytes=capacity,
            reserved_bytes=reserved,
        )
    except Exception:
        return _base_response(
            settings=resolved_settings,
            billing_role=billing_role,
            access_mode=access_mode,
            plan_code=plan_code,
        )

    threshold = classify_storage_threshold(
        used_bytes=projection.used_bytes,
        capacity_bytes=projection.capacity_bytes,
    )
    action = "none"
    action_path = None
    if threshold != "normal":
        action = "open_billing_storage" if can_manage else "contact_owner"
        if can_manage:
            action_path = _BILLING_STORAGE_PATH
    return DesktopStorageStatusResponse(
        billing_role=billing_role,  # type: ignore[arg-type]
        access_mode=access_mode,  # type: ignore[arg-type]
        plan_code=plan_code,
        used_bytes=projection.used_bytes,
        reserved_bytes=projection.reserved_bytes,
        capacity_bytes=projection.capacity_bytes,
        available_bytes=projection.available_bytes,
        threshold=threshold,
        action=action,  # type: ignore[arg-type]
        action_path=action_path,
        meeting_retention_days=resolved_settings.retention_meeting_delete_after_days,
        source_audio_retention_days=resolved_settings.retention_source_audio_days,
        retention_policy_state=_retention_state(resolved_settings)[2],  # type: ignore[arg-type]
        observed_at=now,
    )
