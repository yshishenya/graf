from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession
from sqlalchemy.orm import Session, SessionTransaction

from twobrain_rec_server.auth.context import TenantScope

ALLOWED_MAINTENANCE_OPERATIONS = frozenset(
    {
        "migration_verification",
        "production_smoke_setup",
        "production_smoke_cleanup",
        "backup_restore_rehearsal",
        "operator_diagnostics",
        "provider_link_cleanup",
        "playback_normalization_inventory",
        "playback_normalization_dispatch",
        "prompt_optimization",
        "outcome_dispatch_reconciliation",
        "deletion_purge_reconciliation",
        "processing_legacy_lineage_reconciliation",
        "outcome_initial_baseline_reconciliation",
        "billing_reconciliation",
        "billing_notification_reconciliation",
    }
)

type TenantRequestContextKind = Literal["request", "worker"]
type WorkspaceAuthContextKind = Literal["auth_public", "auth_bootstrap"]
type AuthSessionLookupContextKind = Literal["auth_session_lookup"]
type AuthCallbackLookupContextKind = Literal["auth_callback_lookup"]
type AuthReferralLookupContextKind = Literal["auth_referral_lookup"]
type AuthReferralUserLookupContextKind = Literal["auth_referral_user_lookup"]
type ReferralLandingLookupContextKind = Literal["referral_landing_lookup"]
type ShareInvitationLookupContextKind = Literal["share_invitation_lookup"]
type SharedWithMeLookupContextKind = Literal["shared_with_me_lookup"]
type MaintenanceContextKind = Literal["maintenance"]

ALLOWED_TENANT_CONTEXT_KINDS = frozenset(("request", "worker"))
ALLOWED_WORKSPACE_AUTH_CONTEXT_KINDS = frozenset(("auth_public", "auth_bootstrap"))


@event.listens_for(Session, "after_begin")
def _restore_transaction_local_context(
    session: Session,
    _transaction: SessionTransaction,
    connection: Connection,
) -> None:
    """Replay validated tenant settings whenever a session opens a new transaction.

    PostgreSQL RLS context intentionally uses transaction-local GUCs so pooled
    connections cannot leak one tenant into another. AsyncSession keeps
    ``session.info`` across commit and rollback, however, so a reused request or
    worker session must replay that same validated context on its next
    transaction before any protected statement runs.
    """

    settings = session.info.get("tenant_context")
    if not isinstance(settings, dict) or connection.dialect.name != "postgresql":
        return
    for name, value in settings.items():
        connection.execute(
            text("select set_config(:setting_name, :setting_value, true)"),
            {"setting_name": name, "setting_value": value},
        )


def _require_context_kind(value: str, allowed: frozenset[str], label: str) -> None:
    if value not in allowed:
        expected = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported {label}: {value}; expected one of {expected}")


def require_database_context(
    session: AsyncSession,
    *,
    allowed_context_kinds: frozenset[str],
    workspace_id: UUID | None = None,
    maintenance_operation: str | None = None,
) -> None:
    """Fail before a protected query when production context is absent or too broad."""

    settings = session.info.get("tenant_context")
    if not isinstance(settings, dict):
        if session.get_bind().dialect.name == "postgresql":
            raise RuntimeError("database tenant context is required")
        return
    context_kind = settings.get("app.context_kind")
    if context_kind not in allowed_context_kinds:
        raise RuntimeError("database tenant context kind is not allowed")
    if maintenance_operation is not None and (
        context_kind != "maintenance"
        or settings.get("app.maintenance_operation") != maintenance_operation
        or settings.get("app.maintenance_feature_area") != "playback_normalization"
    ):
        raise RuntimeError("database maintenance context is not exact")
    if (
        workspace_id is not None
        and context_kind in ALLOWED_TENANT_CONTEXT_KINDS
        and settings.get("app.workspace_id") != str(workspace_id)
    ):
        raise RuntimeError("database tenant workspace does not match")


@dataclass(frozen=True, slots=True)
class TenantDatabaseContext:
    organization_id: UUID
    workspace_id: UUID
    user_id: UUID
    device_id: UUID | None = None
    auth_session_id: UUID | None = None
    upload_session_id: UUID | None = None
    context_kind: TenantRequestContextKind = "request"
    session_token_hash: str | None = None

    def __post_init__(self) -> None:
        _require_context_kind(self.context_kind, ALLOWED_TENANT_CONTEXT_KINDS, "context_kind")


@dataclass(frozen=True, slots=True)
class MaintenanceTenantContext:
    operation_name: str
    actor_id: str
    reason_category: str
    feature_area: str
    context_kind: MaintenanceContextKind = "maintenance"

    def __post_init__(self) -> None:
        if self.operation_name not in ALLOWED_MAINTENANCE_OPERATIONS:
            raise ValueError(f"Unsupported maintenance operation: {self.operation_name}")
        if self.context_kind != "maintenance":
            raise ValueError(f"Unsupported maintenance context_kind: {self.context_kind}")
        for field_name in ("actor_id", "reason_category", "feature_area"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} is required for maintenance context")


@dataclass(frozen=True, slots=True)
class AuthSessionLookupContext:
    session_token_hash: str
    context_kind: AuthSessionLookupContextKind = "auth_session_lookup"

    def __post_init__(self) -> None:
        if self.context_kind != "auth_session_lookup":
            raise ValueError(f"Unsupported auth_session_lookup context_kind: {self.context_kind}")


@dataclass(frozen=True, slots=True)
class WorkspaceAuthContext:
    workspace_id: UUID
    organization_id: UUID | None = None
    user_id: UUID | None = None
    context_kind: WorkspaceAuthContextKind = "auth_public"

    def __post_init__(self) -> None:
        _require_context_kind(
            self.context_kind,
            ALLOWED_WORKSPACE_AUTH_CONTEXT_KINDS,
            "workspace auth context_kind",
        )


@dataclass(frozen=True, slots=True)
class AuthCallbackLookupContext:
    state_nonce: str
    context_kind: AuthCallbackLookupContextKind = "auth_callback_lookup"

    def __post_init__(self) -> None:
        if self.context_kind != "auth_callback_lookup":
            raise ValueError(f"Unsupported auth_callback_lookup context_kind: {self.context_kind}")


@dataclass(frozen=True, slots=True)
class AuthReferralLookupContext:
    """Single-token signup lookup; never grants general cross-workspace reads."""

    workspace_id: UUID
    user_id: UUID
    token_hash: str
    referral_link_id: UUID | None = None
    context_kind: AuthReferralLookupContextKind = "auth_referral_lookup"

    def __post_init__(self) -> None:
        if self.context_kind != "auth_referral_lookup":
            raise ValueError(f"Unsupported auth_referral_lookup context_kind: {self.context_kind}")
        if len(self.token_hash) != 64 or any(char not in "0123456789abcdef" for char in self.token_hash):
            raise ValueError("referral token hash must be lowercase hex")


@dataclass(frozen=True, slots=True)
class AuthReferralUserLookupContext:
    """Read only the current invitee's own bound attribution cross-workspace."""

    user_id: UUID
    context_kind: AuthReferralUserLookupContextKind = "auth_referral_user_lookup"

    def __post_init__(self) -> None:
        if self.context_kind != "auth_referral_user_lookup":
            raise ValueError(f"Unsupported auth_referral_user_lookup context_kind: {self.context_kind}")


@dataclass(frozen=True, slots=True)
class ReferralLandingLookupContext:
    """Anonymous lookup constrained to one hashed, active referral token."""

    token_hash: str
    context_kind: ReferralLandingLookupContextKind = "referral_landing_lookup"

    def __post_init__(self) -> None:
        if self.context_kind != "referral_landing_lookup":
            raise ValueError(f"Unsupported referral_landing_lookup context_kind: {self.context_kind}")
        if len(self.token_hash) != 64 or any(char not in "0123456789abcdef" for char in self.token_hash):
            raise ValueError("referral token hash must be lowercase hex")


@dataclass(frozen=True, slots=True)
class ShareInvitationLookupContext:
    workspace_id: UUID
    continuation_nonce: str
    context_kind: ShareInvitationLookupContextKind = "share_invitation_lookup"

    def __post_init__(self) -> None:
        if self.context_kind != "share_invitation_lookup":
            raise ValueError(
                f"Unsupported share_invitation_lookup context_kind: {self.context_kind}"
            )


@dataclass(frozen=True, slots=True)
class SharedWithMeLookupContext:
    """Select only the current user's active direct share grants."""

    user_id: UUID
    context_kind: SharedWithMeLookupContextKind = "shared_with_me_lookup"

    def __post_init__(self) -> None:
        if self.context_kind != "shared_with_me_lookup":
            raise ValueError(
                f"Unsupported shared_with_me_lookup context_kind: {self.context_kind}"
            )


def tenant_context_from_scope(
    scope: TenantScope,
    *,
    context_kind: TenantRequestContextKind = "request",
    session_token_hash: str | None = None,
) -> TenantDatabaseContext:
    return TenantDatabaseContext(
        organization_id=scope.organization_id,
        workspace_id=scope.workspace_id,
        user_id=scope.user_id,
        device_id=scope.device_id,
        auth_session_id=scope.auth_session_id,
        upload_session_id=scope.upload_session_id,
        context_kind=context_kind,
        session_token_hash=session_token_hash,
    )


def tenant_context_settings(context: TenantDatabaseContext) -> dict[str, str]:
    settings = {
        "app.organization_id": str(context.organization_id),
        "app.workspace_id": str(context.workspace_id),
        "app.user_id": str(context.user_id),
        "app.context_kind": context.context_kind,
    }
    if context.device_id is not None:
        settings["app.device_id"] = str(context.device_id)
    if context.auth_session_id is not None:
        settings["app.auth_session_id"] = str(context.auth_session_id)
    if context.upload_session_id is not None:
        settings["app.upload_session_id"] = str(context.upload_session_id)
    if context.session_token_hash is not None:
        settings["app.auth_session_token_hash"] = context.session_token_hash
    return settings


def maintenance_context_settings(context: MaintenanceTenantContext) -> dict[str, str]:
    return {
        "app.context_kind": context.context_kind,
        "app.maintenance_operation": context.operation_name,
        "app.maintenance_actor": context.actor_id,
        "app.maintenance_reason": context.reason_category,
        "app.maintenance_feature_area": context.feature_area,
    }


def auth_session_lookup_settings(context: AuthSessionLookupContext) -> dict[str, str]:
    return {
        "app.context_kind": context.context_kind,
        "app.auth_session_token_hash": context.session_token_hash,
    }


def workspace_auth_context_settings(context: WorkspaceAuthContext) -> dict[str, str]:
    settings = {
        "app.context_kind": context.context_kind,
        "app.workspace_id": str(context.workspace_id),
    }
    if context.organization_id is not None:
        settings["app.organization_id"] = str(context.organization_id)
    if context.user_id is not None:
        settings["app.user_id"] = str(context.user_id)
    return settings


def auth_callback_lookup_settings(context: AuthCallbackLookupContext) -> dict[str, str]:
    return {
        "app.context_kind": context.context_kind,
        "app.auth_callback_state_nonce": context.state_nonce,
    }


def auth_referral_lookup_settings(context: AuthReferralLookupContext) -> dict[str, str]:
    settings = {
        "app.context_kind": context.context_kind,
        "app.workspace_id": str(context.workspace_id),
        "app.user_id": str(context.user_id),
        "app.referral_token_hash": context.token_hash,
    }
    if context.referral_link_id is not None:
        settings["app.referral_link_id"] = str(context.referral_link_id)
    return settings


def auth_referral_user_lookup_settings(context: AuthReferralUserLookupContext) -> dict[str, str]:
    return {
        "app.context_kind": context.context_kind,
        "app.user_id": str(context.user_id),
    }


def referral_landing_lookup_settings(context: ReferralLandingLookupContext) -> dict[str, str]:
    return {
        "app.context_kind": context.context_kind,
        "app.referral_token_hash": context.token_hash,
    }


def share_invitation_lookup_settings(
    context: ShareInvitationLookupContext,
) -> dict[str, str]:
    return {
        "app.context_kind": context.context_kind,
        "app.workspace_id": str(context.workspace_id),
        "app.share_invitation_continuation_nonce": context.continuation_nonce,
    }


def shared_with_me_lookup_settings(context: SharedWithMeLookupContext) -> dict[str, str]:
    return {
        "app.context_kind": context.context_kind,
        "app.user_id": str(context.user_id),
    }


async def apply_tenant_context(
    session: AsyncSession,
    context: (
        TenantDatabaseContext
        | MaintenanceTenantContext
        | AuthSessionLookupContext
        | WorkspaceAuthContext
        | AuthCallbackLookupContext
        | AuthReferralLookupContext
        | AuthReferralUserLookupContext
        | ReferralLandingLookupContext
        | ShareInvitationLookupContext
        | SharedWithMeLookupContext
    ),
) -> None:
    if isinstance(context, TenantDatabaseContext):
        settings = tenant_context_settings(context)
    elif isinstance(context, MaintenanceTenantContext):
        settings = maintenance_context_settings(context)
    elif isinstance(context, AuthSessionLookupContext):
        settings = auth_session_lookup_settings(context)
    elif isinstance(context, WorkspaceAuthContext):
        settings = workspace_auth_context_settings(context)
    elif isinstance(context, AuthCallbackLookupContext):
        settings = auth_callback_lookup_settings(context)
    elif isinstance(context, AuthReferralLookupContext):
        settings = auth_referral_lookup_settings(context)
    elif isinstance(context, AuthReferralUserLookupContext):
        settings = auth_referral_user_lookup_settings(context)
    elif isinstance(context, ReferralLandingLookupContext):
        settings = referral_landing_lookup_settings(context)
    elif isinstance(context, ShareInvitationLookupContext):
        settings = share_invitation_lookup_settings(context)
    else:
        settings = shared_with_me_lookup_settings(context)
    session.info["tenant_context"] = settings
    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for name, value in settings.items():
        await session.execute(
            text("select set_config(:setting_name, :setting_value, true)"),
            {"setting_name": name, "setting_value": value},
        )


async def apply_tenant_context_to_connection(
    connection: AsyncConnection,
    context: (
        TenantDatabaseContext
        | MaintenanceTenantContext
        | AuthSessionLookupContext
        | WorkspaceAuthContext
        | AuthCallbackLookupContext
        | AuthReferralLookupContext
        | AuthReferralUserLookupContext
        | ReferralLandingLookupContext
        | ShareInvitationLookupContext
        | SharedWithMeLookupContext
    ),
) -> None:
    if isinstance(context, TenantDatabaseContext):
        settings = tenant_context_settings(context)
    elif isinstance(context, MaintenanceTenantContext):
        settings = maintenance_context_settings(context)
    elif isinstance(context, AuthSessionLookupContext):
        settings = auth_session_lookup_settings(context)
    elif isinstance(context, WorkspaceAuthContext):
        settings = workspace_auth_context_settings(context)
    elif isinstance(context, AuthCallbackLookupContext):
        settings = auth_callback_lookup_settings(context)
    elif isinstance(context, AuthReferralLookupContext):
        settings = auth_referral_lookup_settings(context)
    elif isinstance(context, AuthReferralUserLookupContext):
        settings = auth_referral_user_lookup_settings(context)
    elif isinstance(context, ReferralLandingLookupContext):
        settings = referral_landing_lookup_settings(context)
    elif isinstance(context, ShareInvitationLookupContext):
        settings = share_invitation_lookup_settings(context)
    else:
        settings = shared_with_me_lookup_settings(context)
    connection.info["tenant_context"] = settings
    if connection.dialect.name != "postgresql":
        return
    for name, value in settings.items():
        await connection.execute(
            text("select set_config(:setting_name, :setting_value, true)"),
            {"setting_name": name, "setting_value": value},
        )


async def apply_tenant_scope(
    session: AsyncSession,
    scope: TenantScope,
    *,
    context_kind: TenantRequestContextKind = "request",
) -> None:
    await apply_tenant_context(session, tenant_context_from_scope(scope, context_kind=context_kind))


async def rehydrate_tenant_context(session: AsyncSession) -> None:
    """Reapply the exact worker/request settings after a transaction boundary."""

    settings = session.info.get("tenant_context")
    if not settings or session.get_bind().dialect.name != "postgresql":
        return
    for name, value in settings.items():
        await session.execute(
            text("select set_config(:setting_name, :setting_value, true)"),
            {"setting_name": name, "setting_value": value},
        )
