from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import MeetingAccessState, ShareGrantView, SharePanelState
from twobrain_rec_server.db.models import (
    Meeting,
    MeetingShareGrant,
    MeetingShareInvitation,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.domain.statuses import DeletionState
from twobrain_rec_server.processing.audit import safe_denied_access_metadata

TEAM_VISIBLE_VALUES = {"team", "team_visible", "workspace", "workspace_visible"}
PRIVILEGED_ROLES = {"owner", "admin"}
ACTIVE_INVITATION_STATES = {"pending", "sending", "sent"}


@dataclass(frozen=True, slots=True)
class GrantCapabilities:
    can_view_summary: bool
    can_view_full_meeting: bool
    can_download: bool
    can_export: bool


def effective_grant_capabilities(
    *,
    content_scope: str,
    can_download: bool,
    can_export: bool,
    expires_at: datetime | None,
    now: datetime | None = None,
) -> GrantCapabilities:
    now = now or datetime.now(UTC)
    if expires_at is not None and expires_at <= now:
        return GrantCapabilities(False, False, False, False)
    full = content_scope == "full_meeting"
    return GrantCapabilities(True, full, bool(can_download), bool(can_export))


def narrow_summary_projection(
    *,
    meeting_label: str,
    occurred_at: datetime,
    duration_seconds: int,
    summary_sections: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "meeting_label": meeting_label[:160],
        "occurred_at": occurred_at,
        "duration_seconds": max(0, duration_seconds),
        "summary_sections": summary_sections,
    }


def normalize_invitation_address(address: str) -> str:
    normalized = address.strip().lower()
    local, separator, domain = normalized.rpartition("@")
    if not separator or not local or "." not in domain or domain.startswith("."):
        raise ProblemDetail(status=422, code="invalid_invitation", title="Invitation is invalid")
    return normalized


def seal_invitation_delivery(*, address: str, raw_token: str, key: bytes) -> str:
    payload = json.dumps(
        {"address": normalize_invitation_address(address), "token": raw_token},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    try:
        return Fernet(key).encrypt(payload.encode("utf-8")).decode("ascii")
    except (TypeError, ValueError) as exc:
        raise ProblemDetail(
            status=503,
            code="invitation_delivery_unavailable",
            title="Invitation delivery unavailable",
        ) from exc


def open_invitation_delivery(sealed: str, *, key: bytes) -> tuple[str, str]:
    try:
        payload = json.loads(Fernet(key).decrypt(sealed.encode("ascii")).decode("utf-8"))
        address = normalize_invitation_address(str(payload["address"]))
        raw_token = str(payload["token"])
    except (InvalidToken, ValueError, TypeError, KeyError) as exc:
        raise ProblemDetail(
            status=503,
            code="invitation_delivery_unavailable",
            title="Invitation delivery unavailable",
        ) from exc
    return address, raw_token


def denied_access_audit_metadata(**values: object) -> dict[str, object]:
    return safe_denied_access_metadata(**values)


async def lock_shareable_meeting(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> Meeting:
    """Serialize sharing mutations with deletion and reject deletion-first races."""
    meeting = await db.scalar(
        select(Meeting)
        .where(Meeting.workspace_id == workspace_id, Meeting.id == meeting_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if meeting is None or (
        meeting.deletion_state or DeletionState.NONE.value
    ) != DeletionState.NONE.value:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return meeting


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
    content_scope: str = "full_meeting"
    can_view_full_meeting: bool = True

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
            content_scope=self.content_scope,
            can_view_full_meeting=self.can_view_full_meeting,
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
        content_scope="summary_only",
        can_view_full_meeting=False,
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
            content_scope="summary_only",
            can_view_full_meeting=False,
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
        capabilities = effective_grant_capabilities(
            content_scope=grant.content_scope,
            can_download=grant.can_download,
            can_export=grant.can_export,
            expires_at=grant.expires_at,
        )
        if capabilities.can_view_summary:
            return _grant_access_decision(
                grant=grant,
                capabilities=capabilities,
                privileged=privileged,
                role=role,
                reason="Access was granted with a login-required share.",
            )

    if membership is not None:
        workspace_grant = await db.scalar(
            select(MeetingShareGrant).where(
                MeetingShareGrant.workspace_id == workspace_id,
                MeetingShareGrant.meeting_id == meeting.id,
                MeetingShareGrant.audience_type == "workspace",
                MeetingShareGrant.audience_id == workspace_id,
                MeetingShareGrant.status == "active",
            )
        )
        if workspace_grant is not None:
            capabilities = effective_grant_capabilities(
                content_scope=workspace_grant.content_scope,
                can_download=workspace_grant.can_download,
                can_export=workspace_grant.can_export,
                expires_at=workspace_grant.expires_at,
            )
            if capabilities.can_view_summary:
                return _grant_access_decision(
                    grant=workspace_grant,
                    capabilities=capabilities,
                    privileged=privileged,
                    role=role,
                    reason="Access was granted to active workspace members.",
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
            MeetingShareGrant.audience_type == "user",
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
    grants = (
        await active_share_grants(db, workspace_id=meeting.workspace_id, meeting_id=meeting.id)
        if decision.can_share
        else []
    )
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


async def create_scoped_share_grant(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting: Meeting,
    actor_user_id: UUID,
    device_id: UUID,
    audience_type: str,
    audience_id: UUID | None,
    content_scope: str,
    can_download: bool,
    can_export: bool,
    expires_at: datetime | None,
    broader_audience_enabled: bool = False,
) -> tuple[MeetingShareGrant, str]:
    from twobrain_rec_server.cabinet.egress import record_egress_audit_event

    meeting = await lock_shareable_meeting(
        db, workspace_id=workspace_id, meeting_id=meeting.id
    )
    decision = await decide_meeting_access(
        db, meeting, workspace_id=workspace_id, viewer_user_id=actor_user_id
    )
    if not decision.can_share:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    if audience_type == "user" and audience_id is not None:
        existing = await db.scalar(
            select(MeetingShareGrant)
            .where(
                MeetingShareGrant.workspace_id == workspace_id,
                MeetingShareGrant.meeting_id == meeting.id,
                MeetingShareGrant.audience_type == "user",
                MeetingShareGrant.audience_id == audience_id,
                MeetingShareGrant.status == "active",
            )
            .with_for_update()
        )
        if existing is not None:
            raw_token = secrets.token_urlsafe(32)
            existing.share_token_hash = hash_share_token(raw_token)
            existing.content_scope = content_scope
            existing.can_download = can_download
            existing.can_export = can_export
            existing.expires_at = expires_at
            existing.rotated_at = datetime.now(UTC)
            await record_egress_audit_event(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting.id,
                actor_user_id=actor_user_id,
                device_id=device_id,
                event_type="share_updated",
                outcome="allowed",
                policy_reason="existing_user_grant_updated",
                metadata={"share_grant_id": str(existing.id)},
            )
            await db.flush()
            return existing, raw_token
        workspace = await db.get(Workspace, workspace_id)
        grantee = await db.get(UserIdentity, audience_id)
        membership = await db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == audience_id,
                WorkspaceMembership.status == "active",
            )
        )
        if (
            workspace is None
            or grantee is None
            or grantee.status != "active"
            or grantee.organization_id != workspace.organization_id
            or membership is None
        ):
            raise ProblemDetail(
                status=404, code="grantee_not_found", title="Grantee not found"
            )
        existing_decision = await decide_meeting_access(
            db,
            meeting,
            workspace_id=workspace_id,
            viewer_user_id=audience_id,
        )
        if existing_decision.can_view:
            raise ProblemDetail(
                status=409,
                code="grantee_already_has_access",
                title="Grantee already has access",
            )
    elif audience_type not in {"workspace", "team", "link"} or not broader_audience_enabled:
        raise ProblemDetail(status=403, code="share_policy_blocked", title="Share is not available")
    if audience_type == "team":
        # Feature 121 has no canonical team entity/membership boundary yet. Keep the
        # policy switch fail-closed instead of returning a grant that nobody can use.
        raise ProblemDetail(
            status=409,
            code="share_team_audience_unavailable",
            title="Team sharing is not available",
        )
    if audience_type == "workspace" and audience_id != workspace_id:
        raise ProblemDetail(status=422, code="invalid_share_audience", title="Share audience is invalid")
    if audience_type == "link" and expires_at is None:
        raise ProblemDetail(status=422, code="share_expiry_required", title="Share expiry required")
    if audience_type == "link" and content_scope != "summary_only":
        raise ProblemDetail(
            status=422,
            code="public_share_scope_invalid",
            title="Public links can share summaries only",
        )
    raw_token = secrets.token_urlsafe(32)
    existing = await db.scalar(
        select(MeetingShareGrant)
        .where(
            MeetingShareGrant.workspace_id == workspace_id,
            MeetingShareGrant.meeting_id == meeting.id,
            MeetingShareGrant.audience_type == audience_type,
            MeetingShareGrant.audience_id == audience_id,
            MeetingShareGrant.status == "active",
        )
        .with_for_update()
    )
    if existing is not None:
        existing.share_token_hash = hash_share_token(raw_token)
        existing.content_scope = content_scope
        existing.can_download = can_download
        existing.can_export = can_export
        existing.expires_at = expires_at
        existing.rotated_at = datetime.now(UTC)
        await record_egress_audit_event(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting.id,
            actor_user_id=actor_user_id,
            device_id=device_id,
            event_type="share_updated",
            outcome="allowed",
            policy_reason=f"existing_{audience_type}_grant_updated",
            metadata={"share_grant_id": str(existing.id)},
        )
        await db.flush()
        return existing, raw_token
    grant = MeetingShareGrant(
        id=uuid4(),
        workspace_id=workspace_id,
        meeting_id=meeting.id,
        grant_type=audience_type,
        grantee_user_id=audience_id if audience_type == "user" else None,
        audience_type=audience_type,
        audience_id=audience_id,
        share_token_hash=hash_share_token(raw_token),
        content_scope=content_scope,
        can_download=can_download,
        can_export=can_export,
        expires_at=expires_at,
        created_by_user_id=actor_user_id,
        status="active",
        metadata_json={"source": "recording_share_dialog"},
        created_at=datetime.now(UTC),
    )
    db.add(grant)
    await record_egress_audit_event(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting.id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type="share_granted",
        outcome="allowed",
        policy_reason=f"{audience_type}_grant_created",
        metadata={"share_grant_id": str(grant.id)},
    )
    await db.flush()
    return grant, raw_token


async def rotate_share_link(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting: Meeting,
    actor_user_id: UUID,
    device_id: UUID,
    grant_id: UUID,
) -> tuple[MeetingShareGrant, str]:
    from twobrain_rec_server.cabinet.egress import record_egress_audit_event

    meeting = await lock_shareable_meeting(
        db, workspace_id=workspace_id, meeting_id=meeting.id
    )
    decision = await decide_meeting_access(
        db, meeting, workspace_id=workspace_id, viewer_user_id=actor_user_id
    )
    if not decision.can_share:
        raise ProblemDetail(status=404, code="share_not_found", title="Share not found")
    grant = await db.scalar(
        select(MeetingShareGrant).where(
            MeetingShareGrant.workspace_id == workspace_id,
            MeetingShareGrant.meeting_id == meeting.id,
            MeetingShareGrant.id == grant_id,
            MeetingShareGrant.audience_type == "link",
            MeetingShareGrant.status == "active",
        )
    )
    if grant is None:
        raise ProblemDetail(status=404, code="share_not_found", title="Share not found")
    raw_token = secrets.token_urlsafe(32)
    grant.share_token_hash = hash_share_token(raw_token)
    grant.rotated_at = datetime.now(UTC)
    await record_egress_audit_event(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting.id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type="share_link_rotated",
        outcome="allowed",
        policy_reason="active_link_token_rotated",
        metadata={"share_grant_id": str(grant.id)},
    )
    await db.flush()
    return grant, raw_token


async def search_share_recipients(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    query: str,
    limit: int = 20,
) -> list[tuple[UUID, str]]:
    query = query.strip()
    if len(query) < 2:
        return []
    users = (
        await db.scalars(
            select(UserIdentity)
            .join(WorkspaceMembership, WorkspaceMembership.user_id == UserIdentity.id)
            .where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.status == "active",
                UserIdentity.status == "active",
                UserIdentity.display_name.ilike(f"%{query[:80]}%"),
            )
            .order_by(UserIdentity.display_name.asc())
            .limit(min(limit, 20))
        )
    ).all()
    return [(user.id, _safe_display_name(user)) for user in users]


async def create_share_invitation(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting: Meeting,
    actor_user_id: UUID,
    device_id: UUID,
    address: str,
    content_scope: str,
    can_download: bool,
    can_export: bool,
    encryption_key: bytes,
    ttl_seconds: int,
) -> MeetingShareInvitation:
    from twobrain_rec_server.cabinet.egress import record_egress_audit_event

    meeting = await lock_shareable_meeting(
        db, workspace_id=workspace_id, meeting_id=meeting.id
    )
    decision = await decide_meeting_access(
        db, meeting, workspace_id=workspace_id, viewer_user_id=actor_user_id
    )
    if not decision.can_share:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    normalized = normalize_invitation_address(address)
    address_hash = hash_share_token(normalized)
    now = datetime.now(UTC)
    expired = (
        await db.scalars(
            select(MeetingShareInvitation)
            .where(
                MeetingShareInvitation.workspace_id == workspace_id,
                MeetingShareInvitation.meeting_id == meeting.id,
                MeetingShareInvitation.normalized_address_hash == address_hash,
                MeetingShareInvitation.status.in_(ACTIVE_INVITATION_STATES),
                MeetingShareInvitation.expires_at <= now,
            )
            .with_for_update()
        )
    ).all()
    for invitation in expired:
        invitation.status = "expired"
        invitation.encrypted_delivery_address = ""
    existing = await db.scalar(
        select(MeetingShareInvitation).where(
            MeetingShareInvitation.workspace_id == workspace_id,
            MeetingShareInvitation.meeting_id == meeting.id,
            MeetingShareInvitation.normalized_address_hash == address_hash,
            MeetingShareInvitation.status.in_(ACTIVE_INVITATION_STATES),
            MeetingShareInvitation.expires_at > now,
        )
    )
    if existing is not None:
        return existing
    raw_token = secrets.token_urlsafe(32)
    invitation = MeetingShareInvitation(
        id=uuid4(),
        workspace_id=workspace_id,
        meeting_id=meeting.id,
        invited_by_user_id=actor_user_id,
        normalized_address_hash=address_hash,
        encrypted_delivery_address=seal_invitation_delivery(
            address=normalized,
            raw_token=raw_token,
            key=encryption_key,
        ),
        content_scope=content_scope,
        can_download=can_download,
        can_export=can_export,
        token_hash=hash_share_token(raw_token),
        status="pending",
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
    db.add(invitation)
    await record_egress_audit_event(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting.id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type="share_invitation_requested",
        outcome="allowed",
        policy_reason="external_invitation_requested",
    )
    await db.flush()
    return invitation


async def revoke_share_invitation(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting: Meeting,
    actor_user_id: UUID,
    device_id: UUID,
    invitation_id: UUID,
) -> None:
    from twobrain_rec_server.cabinet.egress import record_egress_audit_event

    meeting = await lock_shareable_meeting(
        db, workspace_id=workspace_id, meeting_id=meeting.id
    )
    decision = await decide_meeting_access(
        db, meeting, workspace_id=workspace_id, viewer_user_id=actor_user_id
    )
    if not decision.can_share:
        raise ProblemDetail(status=404, code="invitation_not_found", title="Invitation not found")
    invitation = await db.scalar(
        select(MeetingShareInvitation).where(
            MeetingShareInvitation.workspace_id == workspace_id,
            MeetingShareInvitation.meeting_id == meeting.id,
            MeetingShareInvitation.id == invitation_id,
            MeetingShareInvitation.status.in_(ACTIVE_INVITATION_STATES),
        )
    )
    if invitation is None:
        raise ProblemDetail(status=404, code="invitation_not_found", title="Invitation not found")
    invitation.status = "revoked"
    invitation.revoked_at = datetime.now(UTC)
    invitation.encrypted_delivery_address = ""
    await record_egress_audit_event(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting.id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type="share_invitation_revoked",
        outcome="allowed",
        policy_reason="external_invitation_revoked",
    )
    await db.flush()


async def accept_share_invitation(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
    device_id: UUID,
    raw_token: str,
    verified_address_hashes: set[str],
) -> MeetingShareGrant | None:
    from twobrain_rec_server.cabinet.egress import record_egress_audit_event

    invitation = await db.scalar(
        select(MeetingShareInvitation)
        .where(
            MeetingShareInvitation.workspace_id == workspace_id,
            MeetingShareInvitation.token_hash == hash_share_token(raw_token),
            MeetingShareInvitation.status.in_(ACTIVE_INVITATION_STATES),
        )
    )
    if invitation is None:
        return None
    await lock_shareable_meeting(
        db, workspace_id=workspace_id, meeting_id=invitation.meeting_id
    )
    invitation = await db.scalar(
        select(MeetingShareInvitation)
        .where(
            MeetingShareInvitation.id == invitation.id,
            MeetingShareInvitation.workspace_id == workspace_id,
            MeetingShareInvitation.token_hash == hash_share_token(raw_token),
            MeetingShareInvitation.status.in_(ACTIVE_INVITATION_STATES),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if invitation is None:
        return None
    if invitation.expires_at <= datetime.now(UTC):
        invitation.status = "expired"
        invitation.encrypted_delivery_address = ""
        return None
    if invitation.normalized_address_hash not in verified_address_hashes:
        return None
    grant = await db.scalar(
        select(MeetingShareGrant)
        .where(
            MeetingShareGrant.workspace_id == workspace_id,
            MeetingShareGrant.meeting_id == invitation.meeting_id,
            MeetingShareGrant.audience_type == "user",
            MeetingShareGrant.audience_id == user_id,
            MeetingShareGrant.status == "active",
        )
        .with_for_update()
    )
    if grant is None:
        grant = MeetingShareGrant(
            id=uuid4(),
            workspace_id=workspace_id,
            meeting_id=invitation.meeting_id,
            grant_type="user",
            grantee_user_id=user_id,
            audience_type="user",
            audience_id=user_id,
            created_by_user_id=invitation.invited_by_user_id,
            status="active",
        )
        db.add(grant)
    grant.content_scope = invitation.content_scope
    grant.can_download = invitation.can_download
    grant.can_export = invitation.can_export
    grant.share_token_hash = invitation.token_hash
    grant.metadata_json = {"source": "accepted_external_invitation"}
    invitation.status = "accepted"
    invitation.accepted_at = datetime.now(UTC)
    invitation.resolved_user_id = user_id
    invitation.encrypted_delivery_address = ""
    await record_egress_audit_event(
        db,
        workspace_id=workspace_id,
        meeting_id=invitation.meeting_id,
        actor_user_id=user_id,
        device_id=device_id,
        event_type="share_invitation_accepted",
        outcome="allowed",
        policy_reason="verified_invitation_address_matched",
        metadata={"share_grant_id": str(grant.id)},
    )
    await db.flush()
    return grant


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

    meeting = await lock_shareable_meeting(
        db, workspace_id=workspace_id, meeting_id=meeting.id
    )
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
    try:
        meeting = await lock_shareable_meeting(
            db, workspace_id=workspace_id, meeting_id=grant.meeting_id
        )
    except ProblemDetail:
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


def _grant_access_decision(
    *,
    grant: MeetingShareGrant,
    capabilities: GrantCapabilities,
    privileged: bool,
    role: str | None,
    reason: str,
) -> AccessDecision:
    return AccessDecision(
        state="shared",
        label="Shared",
        reason=reason,
        can_view=True,
        can_share=privileged,
        can_manage_team_visibility=privileged,
        can_download=capabilities.can_download,
        can_export=capabilities.can_export,
        role=role,
        content_scope=grant.content_scope,
        can_view_full_meeting=capabilities.can_view_full_meeting,
    )


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
        content_scope="summary_only",
        can_view_full_meeting=False,
    )
