from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.audit import write_onboarding_audit_event
from twobrain_rec_server.auth.sessions import IssuedAuthSession, issue_auth_session
from twobrain_rec_server.db.models import (
    AuthSession,
    AuthSessionDeviceBinding,
    RegisteredDevice,
    Workspace,
    WorkspaceInvitation,
    WorkspaceJoinOffer,
    WorkspaceMembership,
)
from twobrain_rec_server.db.tenant_context import (
    TenantDatabaseContext,
    WorkspaceAuthContext,
    apply_tenant_context,
)

JOIN_OFFER_TRANSITIONS = {
    "offered": frozenset(("accepted", "rejected", "expired", "revoked")),
    "accepted": frozenset(),
    "rejected": frozenset(),
    "expired": frozenset(),
    "revoked": frozenset(),
}


@dataclass(frozen=True, slots=True)
class WorkspaceJoinOfferView:
    id: UUID
    workspace_name: str
    invited_role: str
    expires_at: datetime

    @property
    def invited_role_label(self) -> str:
        return {
            "owner": "Владелец",
            "admin": "Администратор",
            "member": "Участник",
        }.get(self.invited_role, "Участник")


@dataclass(frozen=True, slots=True)
class WorkspaceAccessView:
    id: UUID
    name: str
    kind: str
    role: str
    active: bool


@dataclass(frozen=True, slots=True)
class ActivatedWorkspaceSession:
    workspace: WorkspaceAccessView
    issued_session: IssuedAuthSession


def can_transition_join_offer(current: str, target: str) -> bool:
    return target in JOIN_OFFER_TRANSITIONS.get(current, frozenset())


async def ensure_personal_workspace(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
) -> Workspace:
    """Create or reuse a user's private workspace without touching corporate access."""

    workspace = await db.scalar(
        select(Workspace).where(
            Workspace.organization_id == organization_id,
            Workspace.owner_user_id == user_id,
            Workspace.kind == "personal",
        )
    )
    if workspace is None:
        workspace = Workspace(
            organization_id=organization_id,
            owner_user_id=user_id,
            kind="personal",
            slug=f"personal-{user_id.hex}",
            name="Личное пространство",
        )
        db.add(workspace)
        await db.flush()

    membership = await db.get(
        WorkspaceMembership,
        {"workspace_id": workspace.id, "user_id": user_id},
    )
    if membership is None:
        db.add(
            WorkspaceMembership(
                workspace_id=workspace.id,
                user_id=user_id,
                role="owner",
                status="active",
            )
        )
        await db.flush()
    elif membership.status != "active":
        membership.status = "active"
        membership.role = "owner"

    return workspace


async def create_or_reuse_join_offer(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
    invitation_id: UUID,
    workspace_name: str,
    invited_role: str,
    expires_at: datetime,
) -> WorkspaceJoinOffer:
    offer = await db.scalar(
        select(WorkspaceJoinOffer).where(
            WorkspaceJoinOffer.user_id == user_id,
            WorkspaceJoinOffer.invitation_id == invitation_id,
        )
    )
    if offer is None:
        offer = WorkspaceJoinOffer(
            workspace_id=workspace_id,
            user_id=user_id,
            invitation_id=invitation_id,
            workspace_name=workspace_name,
            invited_role=invited_role,
            status="offered",
            expires_at=expires_at,
        )
        db.add(offer)
        await db.flush()
    return offer


async def list_active_workspaces(
    db: AsyncSession,
    *,
    organization_id: UUID,
    current_workspace_id: UUID,
    user_id: UUID,
) -> tuple[WorkspaceAccessView, ...]:
    """List only server-verified active spaces for the current user.

    `auth_bootstrap` is a bounded server context: it can read this user's
    memberships in the current organization, but it cannot create or change a
    cross-workspace membership.  The matching RLS policy is introduced with
    the active-space migration.
    """

    await apply_tenant_context(
        db,
        WorkspaceAuthContext(
            workspace_id=current_workspace_id,
            organization_id=organization_id,
            user_id=user_id,
            context_kind="auth_bootstrap",
        ),
    )
    rows = (
        await db.execute(
            select(Workspace, WorkspaceMembership)
            .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
            .where(
                Workspace.organization_id == organization_id,
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.status == "active",
            )
            .order_by(Workspace.kind.desc(), Workspace.name, Workspace.id)
        )
    ).all()
    return tuple(
        WorkspaceAccessView(
            id=workspace.id,
            name=workspace.name,
            kind=workspace.kind,
            role=membership.role,
            active=workspace.id == current_workspace_id,
        )
        for workspace, membership in rows
    )


async def activate_workspace_session(
    db: AsyncSession,
    *,
    organization_id: UUID,
    current_workspace_id: UUID,
    user_id: UUID,
    current_session_id: UUID,
    target_workspace_id: UUID,
) -> ActivatedWorkspaceSession:
    """Replace a browser session only after verifying its target membership.

    The prior session is invalidated before the tenant context changes.  A
    failed transaction rolls that change back, so a request cannot be left
    without both its old and replacement session.  Existing recordings and
    upload sessions retain their original workspace IDs.
    """

    current_session = await db.get(AuthSession, current_session_id)
    if (
        current_session is None
        or current_session.user_id != user_id
        or current_session.workspace_id != current_workspace_id
        or current_session.status != "active"
    ):
        raise ProblemDetail(status=401, code="auth_session_invalid", title="Auth session is invalid")

    spaces = await list_active_workspaces(
        db,
        organization_id=organization_id,
        current_workspace_id=current_workspace_id,
        user_id=user_id,
    )
    target = next((space for space in spaces if space.id == target_workspace_id), None)
    if target is None:
        raise ProblemDetail(
            status=404,
            code="workspace_activation_unavailable",
            title="Workspace activation unavailable",
        )
    if target.id == current_workspace_id:
        issued = IssuedAuthSession(
            id=current_session.id,
            token="",
            token_hash=current_session.session_token_hash,
            expires_at=current_session.expires_at,
        )
        return ActivatedWorkspaceSession(workspace=target, issued_session=issued)

    await apply_tenant_context(
        db,
        TenantDatabaseContext(
            organization_id=organization_id,
            workspace_id=current_workspace_id,
            user_id=user_id,
            auth_session_id=current_session_id,
        ),
    )
    current_session.status = "replaced"
    await db.flush()
    await apply_tenant_context(
        db,
        TenantDatabaseContext(
            organization_id=organization_id,
            workspace_id=target.id,
            user_id=user_id,
        ),
    )
    device = await _ensure_browser_workspace_device(
        db,
        workspace_id=target.id,
        user_id=user_id,
    )
    issued = await issue_auth_session(
        db,
        user_id=user_id,
        workspace_id=target.id,
        device_id=device.id,
        provider=current_session.provider,
        claims_fingerprint=current_session.claims_fingerprint,
    )
    db.add(
        AuthSessionDeviceBinding(
            auth_session_id=issued.id,
            registered_device_id=device.id,
            device_state="trusted",
            last_heartbeat_at=datetime.now(UTC),
        )
    )
    await write_onboarding_audit_event(
        db,
        workspace_id=target.id,
        user_id=user_id,
        event_type="workspace_session_activated",
        metadata={"workspace_kind": target.kind},
    )
    return ActivatedWorkspaceSession(workspace=target, issued_session=issued)


async def _ensure_browser_workspace_device(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
) -> RegisteredDevice:
    device_public_id = f"browser-login:{user_id}"
    device = await db.scalar(
        select(RegisteredDevice).where(
            RegisteredDevice.workspace_id == workspace_id,
            RegisteredDevice.user_id == user_id,
            RegisteredDevice.device_public_id == device_public_id,
        )
    )
    if device is None:
        device = RegisteredDevice(
            workspace_id=workspace_id,
            user_id=user_id,
            device_public_id=device_public_id,
            platform="web",
            client_version="browser-login",
            status="active",
            registration_state="approved",
            trusted_by=user_id,
            last_seen_at=datetime.now(UTC),
        )
        db.add(device)
        await db.flush()
        return device
    if device.status != "active" or device.registration_state != "approved":
        raise ProblemDetail(
            status=403,
            code="workspace_activation_device_unavailable",
            title="Workspace activation device unavailable",
        )
    device.platform = "web"
    device.client_version = "browser-login"
    device.last_seen_at = datetime.now(UTC)
    return device


async def list_workspace_join_offers(
    db: AsyncSession,
    *,
    organization_id: UUID,
    current_workspace_id: UUID,
    user_id: UUID,
) -> tuple[WorkspaceJoinOfferView, ...]:
    """Return only the current user's still-actionable offer labels."""
    await apply_tenant_context(
        db,
        TenantDatabaseContext(
            organization_id=organization_id,
            workspace_id=current_workspace_id,
            user_id=user_id,
        ),
    )
    offers = list(
        await db.scalars(
            select(WorkspaceJoinOffer)
            .where(
                WorkspaceJoinOffer.user_id == user_id,
                WorkspaceJoinOffer.status == "offered",
            )
            .order_by(WorkspaceJoinOffer.workspace_name, WorkspaceJoinOffer.id)
        )
    )
    views: list[WorkspaceJoinOfferView] = []
    for offer in offers:
        if not join_offer_is_actionable(offer):
            offer.status = "expired"
            continue
        views.append(
            WorkspaceJoinOfferView(
                id=offer.id,
                workspace_name=offer.workspace_name,
                invited_role=offer.invited_role,
                expires_at=offer.expires_at,
            )
        )
    return tuple(views)


async def decide_workspace_join_offer(
    db: AsyncSession,
    *,
    organization_id: UUID,
    current_workspace_id: UUID,
    user_id: UUID,
    offer_id: UUID,
    action: str,
) -> tuple[WorkspaceJoinOffer, bool]:
    """Accept or reject an offer without trusting any client tenancy input."""
    if action not in {"accept", "reject"}:
        raise ValueError("unsupported workspace join offer action")
    await apply_tenant_context(
        db,
        TenantDatabaseContext(
            organization_id=organization_id,
            workspace_id=current_workspace_id,
            user_id=user_id,
        ),
    )
    offer = await db.scalar(
        select(WorkspaceJoinOffer).where(
            WorkspaceJoinOffer.id == offer_id,
            WorkspaceJoinOffer.user_id == user_id,
        )
    )
    if offer is None:
        raise ProblemDetail(status=404, code="workspace_join_offer_not_found", title="Join offer not found")
    expected_status = "accepted" if action == "accept" else "rejected"
    if offer.status == expected_status:
        return offer, True
    if offer.status == "expired" or not join_offer_is_actionable(offer):
        offer.status = "expired"
        raise ProblemDetail(status=409, code="workspace_join_offer_unavailable", title="Join offer unavailable")
    if offer.status != "offered":
        raise ProblemDetail(status=409, code="workspace_join_offer_unavailable", title="Join offer unavailable")
    if action == "reject":
        offer.status = "rejected"
        await apply_tenant_context(
            db,
            WorkspaceAuthContext(
                workspace_id=offer.workspace_id,
                organization_id=organization_id,
                user_id=user_id,
                context_kind="auth_bootstrap",
            ),
        )
        await write_onboarding_audit_event(
            db,
            workspace_id=offer.workspace_id,
            user_id=user_id,
            event_type="workspace_join_offer_rejected",
            metadata={"offer_id": str(offer.id), "action": action, "status": offer.status},
        )
        return offer, False

    await apply_tenant_context(
        db,
        WorkspaceAuthContext(
            workspace_id=offer.workspace_id,
            organization_id=organization_id,
            user_id=user_id,
            context_kind="auth_bootstrap",
        ),
    )
    invitation = await db.get(WorkspaceInvitation, offer.invitation_id)
    if invitation is None or invitation.workspace_id != offer.workspace_id:
        await _mark_join_offer_unavailable(
            db,
            offer,
            organization_id=organization_id,
            current_workspace_id=current_workspace_id,
            user_id=user_id,
            status="revoked",
        )
    if invitation.status != "pending":
        await _mark_join_offer_unavailable(
            db,
            offer,
            organization_id=organization_id,
            current_workspace_id=current_workspace_id,
            user_id=user_id,
            status="expired" if invitation.status == "expired" else "revoked",
        )
    expires_at = invitation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        invitation.status = "expired"
        await _mark_join_offer_unavailable(
            db,
            offer,
            organization_id=organization_id,
            current_workspace_id=current_workspace_id,
            user_id=user_id,
            status="expired",
        )
    membership = await db.get(
        WorkspaceMembership,
        {"workspace_id": offer.workspace_id, "user_id": user_id},
    )
    if membership is None:
        membership = WorkspaceMembership(
            workspace_id=offer.workspace_id,
            user_id=user_id,
            role=invitation.invited_role,
            status="active",
        )
        db.add(membership)
    elif membership.status != "active":
        membership.status = "active"
        membership.role = invitation.invited_role
    invitation.status = "completed"
    invitation.completed_by_user_id = user_id
    invitation.completed_membership_id = f"{offer.workspace_id}:{user_id}"
    invitation.completed_at = datetime.now(UTC)
    await write_onboarding_audit_event(
        db,
        workspace_id=offer.workspace_id,
        user_id=user_id,
        event_type="workspace_join_offer_accepted",
        metadata={"offer_id": str(offer.id), "invitation_id": str(invitation.id), "action": action},
    )
    await apply_tenant_context(
        db,
        TenantDatabaseContext(
            organization_id=organization_id,
            workspace_id=offer.workspace_id,
            user_id=user_id,
        ),
    )
    offer.status = "accepted"
    return offer, False


async def _mark_join_offer_unavailable(
    db: AsyncSession,
    offer: WorkspaceJoinOffer,
    *,
    organization_id: UUID,
    current_workspace_id: UUID,
    user_id: UUID,
    status: str,
) -> None:
    await apply_tenant_context(
        db,
        TenantDatabaseContext(
            organization_id=organization_id,
            workspace_id=current_workspace_id,
            user_id=user_id,
        ),
    )
    offer.status = status
    raise ProblemDetail(status=409, code="workspace_join_offer_unavailable", title="Join offer unavailable")


def join_offer_is_actionable(offer: WorkspaceJoinOffer, *, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    expires_at = offer.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return offer.status == "offered" and expires_at > now
