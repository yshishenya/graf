from __future__ import annotations

from datetime import datetime
from urllib.parse import urlencode
from uuid import UUID

from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.cabinet.view_models import CALENDAR_PROVIDER_UI
from twobrain_rec_server.calendar.audit import write_calendar_audit_event


def calendar_settings_redirect(
    request: Request,
    *,
    connect_result: str | None = None,
    policy_limited: str | None = None,
    selection_result: str | None = None,
    preferences_result: str | None = None,
    sync_result: str | None = None,
    disconnect_result: str | None = None,
) -> RedirectResponse:
    embedded = request.url.path.startswith("/desktop/")
    params = {}
    if connect_result:
        params["connect_result"] = connect_result
    if policy_limited:
        params["policy_limited"] = policy_limited
    if selection_result:
        params["selection_result"] = selection_result
    if preferences_result:
        params["preferences_result"] = preferences_result
    if sync_result:
        params["sync_result"] = sync_result
    if disconnect_result:
        params["disconnect_result"] = disconnect_result
    suffix = f"?{urlencode(params)}" if params else ""
    path = "/desktop/settings/integrations/calendar" if embedded else "/settings/integrations/calendar"
    return RedirectResponse(f"{path}{suffix}", status_code=303)


def safe_calendar_provider_result(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"success", "cancelled", "denied", "failed", "no_readable_calendars"}:
        return normalized
    return "failed"


def calendar_provider_method_category(provider_family: str) -> str:
    provider_copy = CALENDAR_PROVIDER_UI.get(provider_family)
    if provider_copy is None:
        return "unknown"
    return provider_copy[1]


def calendar_form_checkbox(form: object, key: str) -> bool:
    value = form.get(key) if hasattr(form, "get") else None
    return value is not None and str(value).strip().lower() not in {"", "0", "false", "off"}


def calendar_manual_sync_result(source, *, requested_at: datetime | None = None) -> str:
    if source.connection_state == "disconnected" or source.disconnected_at is not None:
        return "unavailable"
    if source.connection_state in {"disabled", "disabled_by_policy"}:
        return "unavailable"
    if source.connection_state in {"needs_action", "error"} or source.sync_state == "credential_failed":
        return "reconnect_required"
    if source.sync_state in {"queued", "syncing"}:
        if (
            requested_at is not None
            and source.last_sync_started_at is not None
            and source.last_sync_started_at >= requested_at
        ):
            return "accepted"
        return "already_running"
    if source.sync_state in {"failed", "failed_closed", "provider_unavailable", "rate_limited"}:
        return "failed"
    return "accepted"


def calendar_disconnect_result(result: dict[str, object]) -> str:
    if result.get("connection_state") != "disconnected":
        return "failed"
    if result.get("credentials_purged") is not True or result.get("unmatched_future_cache_purged") is not True:
        return "partial"
    return "success"


async def record_calendar_connect_start(
    db: AsyncSession,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
    provider_family: str,
    method_category: str,
) -> None:
    await write_calendar_audit_event(
        db,
        workspace_id=tenant_scope.workspace_id,
        actor_user_id=principal.user_id,
        device_id=tenant_scope.device_id,
        event_type="calendar_connect_start",
        outcome="accepted",
        metadata={"provider_family": provider_family, "method_category": method_category},
    )


async def record_calendar_connect_result(
    db: AsyncSession,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
    provider_family: str,
    method_category: str,
    outcome: str,
    safe_reason_code: str | None = None,
    source_id: UUID | None = None,
) -> None:
    await write_calendar_audit_event(
        db,
        workspace_id=tenant_scope.workspace_id,
        actor_user_id=principal.user_id,
        device_id=tenant_scope.device_id,
        calendar_source_id=source_id,
        event_type="calendar_connect_result",
        outcome=outcome,
        safe_reason_code=safe_reason_code,
        metadata={
            "provider_family": provider_family,
            "method_category": method_category,
            "result_category": safe_reason_code or outcome,
        },
    )


async def record_calendar_source_event(
    db: AsyncSession,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
    source_id: UUID,
    event_type: str,
    outcome: str,
    safe_reason_code: str | None = None,
) -> None:
    await write_calendar_audit_event(
        db,
        workspace_id=tenant_scope.workspace_id,
        actor_user_id=principal.user_id,
        device_id=tenant_scope.device_id,
        calendar_source_id=source_id,
        event_type=event_type,
        outcome=outcome,
        safe_reason_code=safe_reason_code,
        metadata={"result_category": safe_reason_code or outcome},
    )
