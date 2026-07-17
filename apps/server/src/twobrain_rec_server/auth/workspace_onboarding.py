from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import Workspace, WorkspaceJoinOffer, WorkspaceMembership

JOIN_OFFER_TRANSITIONS = {
    "offered": frozenset(("accepted", "rejected", "expired", "revoked")),
    "accepted": frozenset(),
    "rejected": frozenset(),
    "expired": frozenset(),
    "revoked": frozenset(),
}


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
            status="offered",
            expires_at=expires_at,
        )
        db.add(offer)
        await db.flush()
    return offer


async def list_active_workspaces(db: AsyncSession, *, user_id: UUID) -> list[Workspace]:
    return list(
        await db.scalars(
            select(Workspace)
            .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
            .where(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.status == "active",
            )
            .order_by(Workspace.kind.desc(), Workspace.name, Workspace.id)
        )
    )


def join_offer_is_actionable(offer: WorkspaceJoinOffer, *, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    expires_at = offer.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return offer.status == "offered" and expires_at > now
