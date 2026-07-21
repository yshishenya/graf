from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import MeetingAccessState, ShareGrantView, SharePanelState
from twobrain_rec_server.db.models import (
    Meeting,
    MeetingShareGrant,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.domain.statuses import DeletionState

TEAM_VISIBLE_VALUES = {"team", "team_visible", "workspace", "workspace_visible"}
PRIVILEGED_ROLES = {"owner", "admin"}


@dataclass(frozen=True, slots=True)
class AccessDecision:
    state: str
    label: str
    reason: str | None
    can_view: bool
    can_share: bool
    can_manage_team_visibility: bool
    can_download: bool
    can_export: bool
    role: str | None = None

    def to_schema(self) -> MeetingAccessState:
        return MeetingAccessState(
            state=self.state,  # type: ignore[arg-type]
            label=self.label,
            reason=self.reason,
            can_view=self.can_view,
            can_share=self.can_share,
            can_manage_team_visibility=self.can_manage_team_visibility,
            can_download=self.can_download,
            can_export=self.can_export,
        )


def owner_access_state() -> MeetingAccessState:
    return AccessDecision(
        state="owner",
        label="Owner",
        reason="You own this meeting.",
        can_view=True,
        can_share=True,
        can_manage_team_visibility=True,
        can_download=True,
        can_export=True,
        role="owner",
    ).to_schema()


def denied_access_state(reason: str = "Access is unavailable for this viewer.") -> MeetingAccessState:
    return AccessDecision(
        state="denied",
        label="Not available",
        reason=reason,
        can_view=False,
        can_share=False,
        can_manage_team_visibility=False,
        can_download=False,
        can_export=False,
    ).to_schema()


async def decide_meeting_access(
    db: AsyncSession,
    meeting: Meeting,
    *,
    workspace_id: UUID,
    viewer_user_id: UUID,
) -> AccessDecision:
    if meeting.workspace_id != workspace_id:
        return _denied_decision()
    if (meeting.deletion_state or DeletionState.NONE.value) != DeletionState.NONE.value:
        return AccessDecision(
            state="deleted",
            label="Deleted",
            reason="Meeting deletion is in progress.",
            can_view=False,
            can_share=False,
            can_manage_team_visibility=False,
            can_download=False,
            can_export=False,
        )

    membership = await db.scalar(
        select(WorkspaceMembership).where(
            and_(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == viewer_user_id,
                WorkspaceMembership.status == "active",
            )
        ).execution_options(populate_existing=True)
    )
    role = membership.role if membership is not None else None
    privileged = role in PRIVILEGED_ROLES

    if meeting.created_by_user_id == viewer_user_id:
        return AccessDecision(
            state="owner",
            label="Owner",
            reason="You own this meeting.",
            can_view=True,
            can_share=True,
            can_manage_team_visibility=True,
            can_download=True,
            can_export=True,
            role=role,
        )

    if membership is not None and (meeting.visibility or "").lower() in TEAM_VISIBLE_VALUES:
        return AccessDecision(
            state="team",
            label="Team",
            reason="Visible to active workspace members.",
            can_view=True,
            can_share=privileged,
            can_manage_team_visibility=privileged,
            can_download=True,
            can_export=True,
            role=role,
        )

    grant = await active_user_grant(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting.id,
        grantee_user_id=viewer_user_id,
    )
    if grant is not None:
        return AccessDecision(
            state="shared",
            label="Shared",
            reason="Access was granted with a login-required share.",
            can_view=True,
            can_share=privileged,
            can_manage_team_visibility=privileged,
            can_download=True,
            can_export=True,
            role=role,
        )

    return _denied_decision(role=role)


async def active_user_grant(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    grantee_user_id: UUID,
) -> MeetingShareGrant | None:
    return await db.scalar(
        select(MeetingShareGrant).where(
            MeetingShareGrant.workspace_id == workspace_id,
            MeetingShareGrant.meeting_id == meeting_id,
            MeetingShareGrant.grantee_user_id == grantee_user_id,
            MeetingShareGrant.grant_type == "user",
            MeetingShareGrant.status == "active",
        ).execution_options(populate_existing=True)
    )


async def active_share_grants(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> list[MeetingShareGrant]:
    return (
        await db.scalars(
            select(MeetingShareGrant)
            .where(
                MeetingShareGrant.workspace_id == workspace_id,
                MeetingShareGrant.meeting_id == meeting_id,
                MeetingShareGrant.status == "active",
            )
            .order_by(MeetingShareGrant.created_at.asc())
        )
    ).all()


async def share_panel_state(
    db: AsyncSession,
    meeting: Meeting,
    decision: AccessDecision,
) -> SharePanelState:
    grants = await active_share_grants(db, workspace_id=meeting.workspace_id, meeting_id=meeting.id)
    grant_views: list[ShareGrantView] = []
    for grant in grants:
        if grant.grantee_user_id is None:
            continue
        user = await db.get(UserIdentity, grant.grantee_user_id)
        display = _safe_display_name(user)
        grant_views.append(
            ShareGrantView(
                grant_id=grant.id,
                display_name=display,
                role_label="Can view",
                status="active",
                created_at=grant.created_at,
            )
        )

    team_visibility = "enabled" if (meeting.visibility or "").lower() in TEAM_VISIBLE_VALUES else "disabled"
    return SharePanelState(
        team_visibility=team_visibility,
        active_grants=grant_views,
        copy_link_state="available" if decision.can_share else "auth_required",
        public_link_state="disabled_by_default",
    )


async def create_share_grant(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting: Meeting,
    actor_user_id: UUID,
    device_id: UUID,
    grantee_user_id: UUID,
) -> tuple[MeetingShareGrant, str]:
    from twobrain_rec_server.cabinet.egress import record_egress_audit_event

    decision = await decide_meeting_access(
        db,
        meeting,
        workspace_id=workspace_id,
        viewer_user_id=actor_user_id,
    )
    if not decision.can_share:
        raise ProblemDetail(status=403, code="share_forbidden", title="Share is not available")

    workspace = await db.get(Workspace, workspace_id)
    grantee = await db.get(UserIdentity, grantee_user_id)
    grantee_membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == grantee_user_id,
            WorkspaceMembership.status == "active",
        )
    )
    if (
        grantee is None
        or workspace is None
        or grantee.status != "active"
        or grantee.organization_id != workspace.organization_id
        or grantee_membership is None
    ):
        raise ProblemDetail(status=404, code="grantee_not_found", title="Grantee not found")

    existing_decision = await decide_meeting_access(
        db,
        meeting,
        workspace_id=workspace_id,
        viewer_user_id=grantee_user_id,
    )
    if existing_decision.can_view:
        raise ProblemDetail(status=409, code="grantee_already_has_access", title="Grantee already has access")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_share_token(raw_token)
    grant = MeetingShareGrant(
        id=uuid4(),
        workspace_id=workspace_id,
        meeting_id=meeting.id,
        grant_type="user",
        grantee_user_id=grantee_user_id,
        share_token_hash=token_hash,
        created_by_user_id=actor_user_id,
        created_at=datetime.now(UTC),
        status="active",
        metadata_json={"source": "meeting_share_panel"},
    )
    await record_egress_audit_event(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting.id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type="share_granted",
        outcome="allowed",
        policy_reason="login_required_user_grant",
        metadata={"share_grant_id": str(grant.id)},
    )
    db.add(grant)
    await db.flush()
    return grant, raw_token


async def revoke_share_grant(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting: Meeting,
    actor_user_id: UUID,
    device_id: UUID,
    grant_id: UUID,
) -> None:
    from twobrain_rec_server.cabinet.egress import record_egress_audit_event

    decision = await decide_meeting_access(
        db,
        meeting,
        workspace_id=workspace_id,
        viewer_user_id=actor_user_id,
    )
    if not decision.can_share:
        raise ProblemDetail(status=403, code="share_forbidden", title="Share is not available")

    grant = await db.scalar(
        select(MeetingShareGrant).where(
            MeetingShareGrant.workspace_id == workspace_id,
            MeetingShareGrant.meeting_id == meeting.id,
            MeetingShareGrant.id == grant_id,
            MeetingShareGrant.status == "active",
        )
    )
    if grant is None:
        raise ProblemDetail(status=404, code="share_grant_not_found", title="Share grant not found")

    await record_egress_audit_event(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting.id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type="share_revoked",
        outcome="allowed",
        policy_reason="login_required_grant_revoked",
        metadata={"share_grant_id": str(grant.id)},
    )
    grant.status = "revoked"
    grant.revoked_by_user_id = actor_user_id
    grant.revoked_at = datetime.now(UTC)
    await db.flush()


async def resolve_share_token(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    viewer_user_id: UUID,
    device_id: UUID,
    share_token: str,
) -> Meeting | None:
    from twobrain_rec_server.cabinet.egress import record_egress_audit_event

    token_hash = hash_share_token(share_token)
    grant = await db.scalar(
        select(MeetingShareGrant).where(
            MeetingShareGrant.workspace_id == workspace_id,
            MeetingShareGrant.share_token_hash == token_hash,
            MeetingShareGrant.grantee_user_id == viewer_user_id,
            MeetingShareGrant.status == "active",
        )
    )
    if grant is None:
        return None
    meeting = await db.get(Meeting, grant.meeting_id)
    if meeting is None or meeting.workspace_id != workspace_id:
        return None
    decision = await decide_meeting_access(
        db,
        meeting,
        workspace_id=workspace_id,
        viewer_user_id=viewer_user_id,
    )
    if not decision.can_view:
        return None
    await record_egress_audit_event(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting.id,
        actor_user_id=viewer_user_id,
        device_id=device_id,
        event_type="share_link_opened",
        outcome="allowed",
        policy_reason="login_required_link_opened",
        metadata={"share_grant_id": str(grant.id), "viewer_access_state": decision.state},
    )
    return meeting


def grant_view(grant: MeetingShareGrant, *, display_name: str) -> ShareGrantView:
    return ShareGrantView(
        grant_id=grant.id,
        display_name=display_name,
        role_label="Can view",
        status=grant.status,  # type: ignore[arg-type]
        created_at=grant.created_at,
    )


def hash_share_token(raw_token: str) -> str:
    return sha256(raw_token.encode("utf-8")).hexdigest()


def _safe_display_name(user: UserIdentity | None) -> str:
    if user is None:
        return "Authenticated user"
    display = (user.display_name or user.external_subject or "Authenticated user").strip()
    safe = "".join(char for char in display if char >= " " and char != "\x7f")
    return safe[:120] or "Authenticated user"


def _denied_decision(role: str | None = None) -> AccessDecision:
    return AccessDecision(
        state="denied",
        label="Not available",
        reason="Access is unavailable for this viewer.",
        can_view=False,
        can_share=False,
        can_manage_team_visibility=False,
        can_download=False,
        can_export=False,
        role=role,
    )
