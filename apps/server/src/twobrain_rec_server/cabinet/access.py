from __future__ import annotations

import hmac
import json
import math
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    MeetingAccessState,
    ShareGrantView,
    SharePanelState,
    ShareRecipientFreshness,
    ShareRecipientSource,
    ShareRecipientType,
)
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.db.models import (
    CalendarEventSnapshot,
    CalendarParticipant,
    CalendarSource,
    ExternalIdentity,
    Meeting,
    MeetingShareGrant,
    MeetingShareInvitation,
    MeetingShareRateLimitBucket,
    RecordingCalendarContextLink,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.db.tenant_context import TenantDatabaseContext, apply_tenant_context
from twobrain_rec_server.domain.statuses import DeletionState
from twobrain_rec_server.processing.audit import safe_denied_access_metadata

TEAM_VISIBLE_VALUES = {"team", "team_visible", "workspace", "workspace_visible"}
PRIVILEGED_ROLES = {"owner", "admin"}
ACTIVE_INVITATION_STATES = {"pending", "sending", "sent"}
REVOCABLE_INVITATION_STATES = (*ACTIVE_INVITATION_STATES, "outcome_unknown")
ACTIVE_CALENDAR_CONTEXT_STATES = {"matched_auto", "matched_user", "legacy_linked"}
SHAREABLE_CALENDAR_CANDIDATE_CLASSES = {
    "organizer",
    "internal_attendee",
    "optional_attendee",
    "required_attendee",
}
MAX_SHARE_INVITATION_TTL_SECONDS = 7 * 24 * 60 * 60
SHARE_INVITATION_CONTINUATION_TTL_SECONDS = 15 * 60
SHARE_RATE_LIMITS: dict[str, tuple[int, int]] = {
    "recipient_search": (30, 60),
    "grant": (20, 60 * 60),
    "rotate": (20, 60 * 60),
    "invitation": (10, 60 * 60),
    "accept": (10, 60 * 60),
    "resolve": (60, 60),
    "revoke": (30, 60 * 60),
}
_EMAIL_LOCAL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$")


@dataclass(frozen=True, slots=True)
class GrantCapabilities:
    can_view_summary: bool
    can_view_full_meeting: bool
    can_download: bool
    can_export: bool


@dataclass(frozen=True, slots=True)
class ShareRecipientCandidate:
    user_id: UUID
    display_label: str
    source: ShareRecipientSource
    freshness: ShareRecipientFreshness = "current"
    recipient_type: ShareRecipientType = "workspace_member"


@dataclass(frozen=True, slots=True)
class ShareInvitationPreview:
    """Metadata safe to show before the recipient accepts an invitation."""

    meeting_title: str
    occurred_at: datetime
    duration_seconds: int
    expires_at: datetime
    content_scope: str = "summary_only"


@dataclass(frozen=True, slots=True)
class ShareRecipientAccessProof:
    user_is_active: bool
    workspace_membership_is_active: bool
    verified_address_hashes: frozenset[str] = frozenset()


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
    if len(normalized) > 254 or normalized.count("@") != 1:
        raise ProblemDetail(status=422, code="invalid_invitation", title="Invitation is invalid")
    local, domain = normalized.split("@", maxsplit=1)
    if (
        not 1 <= len(local) <= 64
        or not _EMAIL_LOCAL_RE.fullmatch(local)
        or local.startswith(".")
        or local.endswith(".")
        or ".." in local
    ):
        raise ProblemDetail(status=422, code="invalid_invitation", title="Invitation is invalid")
    try:
        ascii_domain = domain.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ProblemDetail(
            status=422, code="invalid_invitation", title="Invitation is invalid"
        ) from exc
    labels = ascii_domain.split(".")
    if (
        len(ascii_domain) > 253
        or len(labels) < 2
        or any(
            not label
            or len(label) > 63
            or label.startswith("-")
            or label.endswith("-")
            or not re.fullmatch(r"[a-z0-9-]+", label)
            for label in labels
        )
    ):
        raise ProblemDetail(status=422, code="invalid_invitation", title="Invitation is invalid")
    return normalized


def mask_invitation_address(address: str) -> str:
    normalized = normalize_invitation_address(address)
    local, domain = normalized.split("@", maxsplit=1)
    masked_local = f"{local[0]}*" if len(local) <= 2 else f"{local[0]}***{local[-1]}"
    return f"{masked_local}@{domain}"


def invitation_address_hashes(address: str) -> frozenset[str]:
    """Return the keyed identity digest and the legacy digest during migration."""
    normalized = normalize_invitation_address(address)
    from twobrain_rec_server.config import get_settings

    secret = get_settings().share_identity_hash_secret.encode("utf-8")
    keyed = hmac.new(secret, normalized.encode("utf-8"), sha256).hexdigest()
    return frozenset({f"hmac-sha256:{keyed}", sha256(normalized.encode("utf-8")).hexdigest()})


def hash_invitation_address(address: str) -> str:
    return next(
        value for value in invitation_address_hashes(address) if value.startswith("hmac-sha256:")
    )


async def enforce_share_rate_limit(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
    device_id: UUID,
    action_key: str,
    now: datetime | None = None,
) -> None:
    """Serialize a bounded actor/device bucket in a committed transaction."""
    sessionmaker = db.info.get("share_rate_limit_sessionmaker")
    if sessionmaker is not None:
        async with sessionmaker() as rate_db:
            await apply_tenant_context(
                rate_db,
                TenantDatabaseContext(
                    organization_id=UUID(int=0),
                    workspace_id=workspace_id,
                    user_id=user_id,
                    device_id=device_id,
                    context_kind="request",
                ),
            )
            try:
                await _enforce_share_rate_limit_in_session(
                    rate_db,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    device_id=device_id,
                    action_key=action_key,
                    now=now,
                )
            except ProblemDetail as exc:
                if exc.status == 429:
                    await rate_db.commit()
                raise
            await rate_db.commit()
        return
    await _enforce_share_rate_limit_in_session(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        device_id=device_id,
        action_key=action_key,
        now=now,
    )


async def _enforce_share_rate_limit_in_session(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
    device_id: UUID,
    action_key: str,
    now: datetime | None = None,
) -> None:
    """Update one rate-limit bucket; the caller owns the transaction boundary."""
    limit, window_seconds = SHARE_RATE_LIMITS[action_key]
    now = now or datetime.now(UTC)
    await db.execute(
        pg_insert(MeetingShareRateLimitBucket)
        .values(
            workspace_id=workspace_id,
            user_id=user_id,
            device_id=device_id,
            action_key=action_key,
            window_started_at=now,
            attempt_count=0,
        )
        .on_conflict_do_nothing(
            index_elements=["workspace_id", "user_id", "device_id", "action_key"]
        )
    )
    bucket = await db.scalar(
        select(MeetingShareRateLimitBucket)
        .where(
            MeetingShareRateLimitBucket.workspace_id == workspace_id,
            MeetingShareRateLimitBucket.user_id == user_id,
            MeetingShareRateLimitBucket.device_id == device_id,
            MeetingShareRateLimitBucket.action_key == action_key,
        )
        .with_for_update()
    )
    if bucket is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    window_started_at = bucket.window_started_at
    if window_started_at.tzinfo is None:
        window_started_at = window_started_at.replace(tzinfo=UTC)
    if now - window_started_at >= timedelta(seconds=window_seconds):
        bucket.window_started_at = now
        bucket.attempt_count = 0
        bucket.blocked_until = None
    blocked_until = bucket.blocked_until
    if blocked_until is not None and blocked_until.tzinfo is None:
        blocked_until = blocked_until.replace(tzinfo=UTC)
    if blocked_until is not None and blocked_until > now:
        retry_after = max(1, math.ceil((blocked_until - now).total_seconds()))
        raise ProblemDetail(
            status=429,
            code="share_rate_limited",
            title="Share requests are temporarily limited",
            detail="Try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    if bucket.attempt_count >= limit:
        blocked_until = now + timedelta(seconds=window_seconds)
        bucket.blocked_until = blocked_until
        retry_after = max(1, math.ceil((blocked_until - now).total_seconds()))
        await db.flush()
        raise ProblemDetail(
            status=429,
            code="share_rate_limited",
            title="Share requests are temporarily limited",
            detail="Try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    bucket.attempt_count += 1
    bucket.last_attempt_at = now
    await db.flush()


def escape_share_search_query(query: str, *, max_length: int = 80) -> str:
    """Normalize a recipient query without allowing LIKE wildcards to widen it."""
    normalized = " ".join(query.strip().split())[:max_length]
    return normalized.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def bounded_share_invitation_expiry(
    *,
    now: datetime,
    ttl_seconds: int,
) -> datetime:
    if ttl_seconds <= 0:
        raise ProblemDetail(
            status=422,
            code="invalid_invitation_ttl",
            title="Invitation expiry is invalid",
        )
    return now + timedelta(seconds=min(ttl_seconds, MAX_SHARE_INVITATION_TTL_SECONDS))


def _query_matches(value: str | None, query: str) -> bool:
    return bool(value and query.casefold() in value.casefold())


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
    if (
        meeting is None
        or meeting.deleted_at is not None
        or (meeting.deletion_state or DeletionState.NONE.value) != DeletionState.NONE.value
    ):
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


def denied_access_state(
    reason: str = "Access is unavailable for this viewer.",
) -> MeetingAccessState:
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
    recipient_proof: ShareRecipientAccessProof | None = None,
) -> AccessDecision:
    if meeting.workspace_id != workspace_id:
        return _denied_decision()
    if (
        meeting.deleted_at is not None
        or (meeting.deletion_state or DeletionState.NONE.value) != DeletionState.NONE.value
    ):
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
        select(WorkspaceMembership)
        .where(
            and_(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == viewer_user_id,
                WorkspaceMembership.status == "active",
            )
        )
        .execution_options(populate_existing=True)
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
        if capabilities.can_view_summary and await _share_grant_recipient_is_valid(
            db,
            grant=grant,
            viewer_user_id=viewer_user_id,
            recipient_proof=recipient_proof,
        ):
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
    now = datetime.now(UTC)
    return await db.scalar(
        select(MeetingShareGrant)
        .where(
            MeetingShareGrant.workspace_id == workspace_id,
            MeetingShareGrant.meeting_id == meeting_id,
            MeetingShareGrant.grantee_user_id == grantee_user_id,
            MeetingShareGrant.audience_type == "user",
            MeetingShareGrant.status == "active",
            MeetingShareGrant.expires_at.is_(None) | (MeetingShareGrant.expires_at > now),
        )
        .execution_options(populate_existing=True)
    )


async def recipient_share_access_proof(
    sessionmaker,
    *,
    recipient_scope: TenantScope,
    owner_workspace_id: UUID,
) -> ShareRecipientAccessProof:
    """Build recipient proof under trusted recipient and source-workspace contexts."""
    async with sessionmaker() as session:
        await apply_tenant_context(
            session,
            TenantDatabaseContext(
                organization_id=recipient_scope.organization_id,
                workspace_id=recipient_scope.workspace_id,
                user_id=recipient_scope.user_id,
                device_id=recipient_scope.device_id,
                auth_session_id=recipient_scope.auth_session_id,
            ),
        )
        user = await session.scalar(
            select(UserIdentity).where(
                UserIdentity.id == recipient_scope.user_id,
                UserIdentity.status == "active",
            )
        )
        emails = (
            await session.scalars(
                select(ExternalIdentity.email).where(
                    ExternalIdentity.user_id == recipient_scope.user_id,
                    ExternalIdentity.is_verified.is_(True),
                    ExternalIdentity.email.is_not(None),
                )
            )
        ).all()
    async with sessionmaker() as session:
        await apply_tenant_context(
            session,
            TenantDatabaseContext(
                organization_id=recipient_scope.organization_id,
                workspace_id=owner_workspace_id,
                user_id=recipient_scope.user_id,
                device_id=recipient_scope.device_id,
                auth_session_id=recipient_scope.auth_session_id,
            ),
        )
        membership = await session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == owner_workspace_id,
                WorkspaceMembership.user_id == recipient_scope.user_id,
                WorkspaceMembership.status == "active",
            )
        )
    return ShareRecipientAccessProof(
        user_is_active=user is not None,
        workspace_membership_is_active=membership is not None,
        verified_address_hashes=frozenset(
            digest
            for email in emails
            if email
            for digest in invitation_address_hashes(normalize_invitation_address(email))
        ),
    )


async def _share_grant_recipient_is_valid(
    db: AsyncSession,
    *,
    grant: MeetingShareGrant,
    viewer_user_id: UUID,
    recipient_proof: ShareRecipientAccessProof | None = None,
) -> bool:
    """Recheck the recipient boundary at every access decision."""
    if recipient_proof is not None and not recipient_proof.user_is_active:
        return False
    if recipient_proof is None:
        user = await db.get(UserIdentity, viewer_user_id)
        if user is None or user.status != "active":
            return False
    metadata = grant.metadata_json if isinstance(grant.metadata_json, dict) else {}
    if metadata.get("source") == "accepted_external_invitation":
        expected_hash = metadata.get("recipient_address_hash")
        if not isinstance(expected_hash, str) or not expected_hash:
            return False
        if recipient_proof is not None:
            return expected_hash in recipient_proof.verified_address_hashes
        verified_emails = (
            await db.scalars(
                select(ExternalIdentity.email).where(
                    ExternalIdentity.user_id == viewer_user_id,
                    ExternalIdentity.is_verified.is_(True),
                    ExternalIdentity.email.is_not(None),
                )
            )
        ).all()
        return any(
            expected_hash in invitation_address_hashes(email) for email in verified_emails if email
        )
    if recipient_proof is not None:
        return recipient_proof.workspace_membership_is_active
    return (
        await db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == grant.workspace_id,
                WorkspaceMembership.user_id == viewer_user_id,
                WorkspaceMembership.status == "active",
            )
        )
    ) is not None


async def active_share_grants(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> list[MeetingShareGrant]:
    now = datetime.now(UTC)
    return (
        await db.scalars(
            select(MeetingShareGrant)
            .where(
                MeetingShareGrant.workspace_id == workspace_id,
                MeetingShareGrant.meeting_id == meeting_id,
                MeetingShareGrant.status == "active",
                (MeetingShareGrant.expires_at.is_(None) | (MeetingShareGrant.expires_at > now)),
            )
            .order_by(MeetingShareGrant.created_at.asc())
        )
    ).all()


async def share_panel_state(
    db: AsyncSession,
    meeting: Meeting,
    decision: AccessDecision,
    *,
    external_invitations_enabled: bool = False,
    invitation_encryption_key: bytes | None = None,
) -> SharePanelState:
    grants = (
        await active_share_grants(db, workspace_id=meeting.workspace_id, meeting_id=meeting.id)
        if decision.can_share
        else []
    )
    invitations = (
        (
            await db.scalars(
                select(MeetingShareInvitation)
                .where(
                    MeetingShareInvitation.workspace_id == meeting.workspace_id,
                    MeetingShareInvitation.meeting_id == meeting.id,
                    MeetingShareInvitation.status.in_(
                        (*ACTIVE_INVITATION_STATES, "outcome_unknown")
                    ),
                )
                .order_by(MeetingShareInvitation.created_at.asc())
            )
        ).all()
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
                audience_type=grant.audience_type,
                content_scope=grant.content_scope,
                expires_at=grant.expires_at,
            )
        )

    team_visibility = (
        "enabled" if (meeting.visibility or "").lower() in TEAM_VISIBLE_VALUES else "disabled"
    )
    calendar_context = await db.scalar(
        select(RecordingCalendarContextLink.id).where(
            RecordingCalendarContextLink.workspace_id == meeting.workspace_id,
            RecordingCalendarContextLink.meeting_id == meeting.id,
            RecordingCalendarContextLink.context_state.in_(ACTIVE_CALENDAR_CONTEXT_STATES),
            RecordingCalendarContextLink.calendar_event_snapshot_id.is_not(None),
        )
    )
    capability_state = "available" if decision.can_share else "auth_required"
    capability_reason = (
        None
        if decision.can_share
        else "Для управления доступом войдите в аккаунт с правом владельца."
    )
    invitation_views = []
    for invitation in invitations:
        display_label = f"Приглашение · {str(invitation.id)[:8]}"
        sealed_address = (
            invitation.encrypted_recipient_address or invitation.encrypted_delivery_address
        )
        if invitation_encryption_key and sealed_address:
            try:
                address, _ = open_invitation_delivery(
                    sealed_address,
                    key=invitation_encryption_key,
                )
                display_label = mask_invitation_address(address)
            except ProblemDetail:
                pass
        invitation_views.append(
            {
                "invitation_id": invitation.id,
                "status": invitation.status,
                "created_at": invitation.created_at,
                "expires_at": invitation.expires_at,
                "content_scope": invitation.content_scope,
                "display_label": display_label,
            }
        )
    return SharePanelState(
        team_visibility=team_visibility,
        active_grants=grant_views,
        copy_link_state="available" if decision.can_share else "auth_required",
        public_link_state="disabled_by_default",
        capability_state=capability_state,
        capability_reason=capability_reason,
        external_invitation_state=("available" if external_invitations_enabled else "disabled"),
        active_invitations=invitation_views,
        recipient_sources=["workspace", "calendar"] if calendar_context else ["workspace"],
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

    meeting = await lock_shareable_meeting(db, workspace_id=workspace_id, meeting_id=meeting.id)
    decision = await decide_meeting_access(
        db, meeting, workspace_id=workspace_id, viewer_user_id=actor_user_id
    )
    if not decision.can_share:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    if audience_type == "user" and audience_id is not None:
        await enforce_share_rate_limit(
            db,
            workspace_id=workspace_id,
            user_id=actor_user_id,
            device_id=device_id,
            action_key="grant",
        )
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
            raise ProblemDetail(status=404, code="grantee_not_found", title="Grantee not found")
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
            if existing.expires_at is None or existing.expires_at > datetime.now(UTC):
                raise ProblemDetail(
                    status=409,
                    code="grantee_already_has_access",
                    title="Grantee already has access",
                )
            # Reuse the durable row after expiry; the partial unique index still
            # treats an expired row as active until its status changes.
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
                policy_reason="expired_user_grant_reactivated",
                metadata={"share_grant_id": str(existing.id)},
            )
            await db.flush()
            return existing, raw_token
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
        raise ProblemDetail(
            status=422, code="invalid_share_audience", title="Share audience is invalid"
        )
    if audience_type == "link" and expires_at is None:
        raise ProblemDetail(status=422, code="share_expiry_required", title="Share expiry required")
    if audience_type == "link" and content_scope != "summary_only":
        raise ProblemDetail(
            status=422,
            code="public_share_scope_invalid",
            title="Public links can share summaries only",
        )
    if audience_type != "user":
        await enforce_share_rate_limit(
            db,
            workspace_id=workspace_id,
            user_id=actor_user_id,
            device_id=device_id,
            action_key="grant",
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

    meeting = await lock_shareable_meeting(db, workspace_id=workspace_id, meeting_id=meeting.id)
    decision = await decide_meeting_access(
        db, meeting, workspace_id=workspace_id, viewer_user_id=actor_user_id
    )
    if not decision.can_share:
        raise ProblemDetail(status=404, code="share_not_found", title="Share not found")
    await enforce_share_rate_limit(
        db,
        workspace_id=workspace_id,
        user_id=actor_user_id,
        device_id=device_id,
        action_key="rotate",
    )
    now = datetime.now(UTC)
    grant = await db.scalar(
        select(MeetingShareGrant).where(
            MeetingShareGrant.workspace_id == workspace_id,
            MeetingShareGrant.meeting_id == meeting.id,
            MeetingShareGrant.id == grant_id,
            MeetingShareGrant.audience_type.in_(("link", "user")),
            MeetingShareGrant.status == "active",
            MeetingShareGrant.expires_at.is_(None) | (MeetingShareGrant.expires_at > now),
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
        event_type=("share_link_rotated" if grant.audience_type == "link" else "share_updated"),
        outcome="allowed",
        policy_reason=(
            "active_link_token_rotated"
            if grant.audience_type == "link"
            else "active_user_grant_token_rotated"
        ),
        metadata={"share_grant_id": str(grant.id)},
    )
    await db.flush()
    return grant, raw_token


async def search_share_recipients(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID | None = None,
    viewer_user_id: UUID | None = None,
    device_id: UUID | None = None,
    query: str,
    limit: int = 20,
) -> list[ShareRecipientCandidate]:
    normalized_query = " ".join(query.strip().split())[:80]
    if meeting_id is None or len(normalized_query) == 1:
        return []
    if viewer_user_id is not None and device_id is not None:
        await enforce_share_rate_limit(
            db,
            workspace_id=workspace_id,
            user_id=viewer_user_id,
            device_id=device_id,
            action_key="recipient_search",
        )

    # The meeting lock/access decision is performed by the API route. This
    # second boundary keeps the helper safe when called from another service
    # path: a missing meeting context never degrades to workspace-wide search.
    link = await db.scalar(
        select(RecordingCalendarContextLink)
        .join(Meeting, Meeting.id == RecordingCalendarContextLink.meeting_id)
        .join(
            CalendarEventSnapshot,
            CalendarEventSnapshot.id == RecordingCalendarContextLink.calendar_event_snapshot_id,
        )
        .join(CalendarSource, CalendarSource.id == CalendarEventSnapshot.calendar_source_id)
        .where(
            RecordingCalendarContextLink.workspace_id == workspace_id,
            RecordingCalendarContextLink.meeting_id == meeting_id,
            RecordingCalendarContextLink.context_state.in_(ACTIVE_CALENDAR_CONTEXT_STATES),
            RecordingCalendarContextLink.calendar_event_snapshot_id.is_not(None),
            CalendarSource.workspace_id == workspace_id,
            CalendarSource.owner_user_id == Meeting.created_by_user_id,
            CalendarSource.connection_state == "active",
        )
        .order_by(RecordingCalendarContextLink.updated_at.desc())
    )

    escaped_query = escape_share_search_query(normalized_query)
    pattern = f"%{escaped_query}%"
    workspace_users = (
        await db.scalars(
            select(UserIdentity)
            .join(WorkspaceMembership, WorkspaceMembership.user_id == UserIdentity.id)
            .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
            .outerjoin(
                ExternalIdentity,
                and_(
                    ExternalIdentity.user_id == UserIdentity.id,
                    ExternalIdentity.is_verified.is_(True),
                ),
            )
            .where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.status == "active",
                UserIdentity.status == "active",
                UserIdentity.organization_id == Workspace.organization_id,
                or_(
                    UserIdentity.display_name.ilike(pattern, escape="\\"),
                    ExternalIdentity.email.ilike(pattern, escape="\\"),
                ),
                *((UserIdentity.id != viewer_user_id,) if viewer_user_id is not None else ()),
            )
            .distinct()
            .order_by(UserIdentity.display_name.asc())
            .limit(min(limit, 20))
        )
    ).all()
    candidates: dict[UUID, ShareRecipientCandidate] = {
        user.id: ShareRecipientCandidate(
            user_id=user.id,
            display_label=_safe_display_name(user),
            source="workspace",
        )
        for user in workspace_users
    }

    if link is None or link.calendar_event_snapshot_id is None:
        return sorted(candidates.values(), key=lambda item: item.display_label.casefold())[:limit]

    participants = (
        await db.scalars(
            select(CalendarParticipant)
            .where(
                CalendarParticipant.workspace_id == workspace_id,
                CalendarParticipant.calendar_event_snapshot_id == link.calendar_event_snapshot_id,
                CalendarParticipant.recipient_candidate_class.in_(
                    SHAREABLE_CALENDAR_CANDIDATE_CLASSES
                ),
                CalendarParticipant.email.is_not(None),
            )
            .limit(100)
        )
    ).all()
    participant_emails = {
        participant.email.strip().lower()
        for participant in participants
        if participant.email
        and (
            not normalized_query
            or _query_matches(participant.display_name, normalized_query)
            or _query_matches(participant.email, normalized_query)
        )
    }
    if not participant_emails:
        return sorted(candidates.values(), key=lambda item: item.display_label.casefold())[:limit]

    calendar_users = (
        await db.execute(
            select(UserIdentity, ExternalIdentity.email)
            .join(WorkspaceMembership, WorkspaceMembership.user_id == UserIdentity.id)
            .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
            .join(
                ExternalIdentity,
                and_(
                    ExternalIdentity.user_id == UserIdentity.id,
                    ExternalIdentity.is_verified.is_(True),
                ),
            )
            .where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.status == "active",
                UserIdentity.status == "active",
                UserIdentity.organization_id == Workspace.organization_id,
                func.lower(ExternalIdentity.email).in_(participant_emails),
                *((UserIdentity.id != viewer_user_id,) if viewer_user_id is not None else ()),
            )
            .distinct()
        )
    ).all()
    freshness = "current"
    if link.updated_at is not None:
        link_updated_at = (
            link.updated_at.replace(tzinfo=UTC)
            if link.updated_at.tzinfo is None
            else link.updated_at.astimezone(UTC)
        )
        if datetime.now(UTC) - link_updated_at > timedelta(days=7):
            freshness = "stale"
    for user, _email in calendar_users:
        current = candidates.get(user.id)
        candidates[user.id] = ShareRecipientCandidate(
            user_id=user.id,
            display_label=_safe_display_name(user),
            source=("workspace_calendar" if current is not None else "calendar"),
            freshness=freshness,
        )
    return sorted(candidates.values(), key=lambda item: item.display_label.casefold())[:limit]


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

    meeting = await lock_shareable_meeting(db, workspace_id=workspace_id, meeting_id=meeting.id)
    decision = await decide_meeting_access(
        db, meeting, workspace_id=workspace_id, viewer_user_id=actor_user_id
    )
    if not decision.can_share:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    await enforce_share_rate_limit(
        db,
        workspace_id=workspace_id,
        user_id=actor_user_id,
        device_id=device_id,
        action_key="invitation",
    )
    if content_scope == "summary_only" and (can_download or can_export):
        raise ProblemDetail(
            status=422,
            code="external_share_scope_invalid",
            title="Summary invitations cannot include recording artifacts",
        )
    if content_scope == "full_meeting" and (not can_download or not can_export):
        raise ProblemDetail(
            status=422,
            code="external_share_scope_invalid",
            title="Recording invitations must include download and export access",
        )
    if content_scope not in {"summary_only", "full_meeting"}:
        raise ProblemDetail(
            status=422,
            code="external_share_scope_invalid",
            title="External invitation scope is invalid",
        )
    normalized = normalize_invitation_address(address)
    address_hash = hash_invitation_address(normalized)
    address_hashes = invitation_address_hashes(normalized)
    now = datetime.now(UTC)
    expired = (
        await db.scalars(
            select(MeetingShareInvitation)
            .where(
                MeetingShareInvitation.workspace_id == workspace_id,
                MeetingShareInvitation.meeting_id == meeting.id,
                MeetingShareInvitation.normalized_address_hash.in_(address_hashes),
                MeetingShareInvitation.status.in_(ACTIVE_INVITATION_STATES),
                MeetingShareInvitation.expires_at <= now,
            )
            .with_for_update()
        )
    ).all()
    for invitation in expired:
        invitation.status = "expired"
        invitation.encrypted_delivery_address = ""
        invitation.encrypted_recipient_address = None
    uncertain = await db.scalar(
        select(MeetingShareInvitation).where(
            MeetingShareInvitation.workspace_id == workspace_id,
            MeetingShareInvitation.meeting_id == meeting.id,
            MeetingShareInvitation.normalized_address_hash.in_(address_hashes),
            MeetingShareInvitation.status == "outcome_unknown",
            MeetingShareInvitation.expires_at > now,
        )
    )
    if uncertain is not None:
        raise ProblemDetail(
            status=409,
            code="postal_delivery_outcome_unknown",
            title="Invitation delivery outcome is unknown",
        )
    existing = await db.scalar(
        select(MeetingShareInvitation).where(
            MeetingShareInvitation.workspace_id == workspace_id,
            MeetingShareInvitation.meeting_id == meeting.id,
            MeetingShareInvitation.normalized_address_hash.in_(address_hashes),
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
        encrypted_recipient_address=seal_invitation_delivery(
            address=normalized,
            raw_token=raw_token,
            key=encryption_key,
        ),
        content_scope=content_scope,
        can_download=can_download,
        can_export=can_export,
        token_hash=hash_share_token(raw_token),
        status="pending",
        expires_at=bounded_share_invitation_expiry(now=now, ttl_seconds=ttl_seconds),
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


async def share_invitation_recipient_address(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    raw_token: str,
    encryption_key: bytes,
) -> str | None:
    """Recover the invited address only for the matching active magic link."""
    invitation = await db.scalar(
        select(MeetingShareInvitation).where(
            MeetingShareInvitation.workspace_id == workspace_id,
            MeetingShareInvitation.token_hash == hash_share_token(raw_token),
            MeetingShareInvitation.status.in_(ACTIVE_INVITATION_STATES),
            MeetingShareInvitation.expires_at > datetime.now(UTC),
        )
    )
    if invitation is None:
        return None
    sealed = invitation.encrypted_recipient_address or invitation.encrypted_delivery_address
    if not sealed:
        return None
    try:
        address, stored_token = open_invitation_delivery(sealed, key=encryption_key)
    except ProblemDetail:
        return None
    if not hmac.compare_digest(hash_share_token(stored_token), invitation.token_hash):
        return None
    if invitation.normalized_address_hash not in invitation_address_hashes(address):
        return None
    return address


async def create_share_invitation_continuation(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    raw_token: str,
    encryption_key: bytes,
) -> str | None:
    """Persist a one-time opaque login continuation without putting the bearer in `next`."""
    now = datetime.now(UTC)
    invitation = await db.scalar(
        select(MeetingShareInvitation)
        .where(
            MeetingShareInvitation.workspace_id == workspace_id,
            MeetingShareInvitation.token_hash == hash_share_token(raw_token),
            MeetingShareInvitation.status.in_(ACTIVE_INVITATION_STATES),
            MeetingShareInvitation.expires_at > now,
        )
        .with_for_update()
    )
    if invitation is None:
        return None
    if (
        invitation.continuation_nonce
        and invitation.continuation_token_ciphertext
        and invitation.continuation_used_at is None
        and invitation.continuation_expires_at is not None
        and invitation.continuation_expires_at > now
    ):
        # Reuse an active exchange when the same invite is opened in multiple
        # tabs; the nonce remains one-time and the first tab stays valid.
        return invitation.continuation_nonce
    nonce = secrets.token_urlsafe(24)
    invitation.continuation_nonce = nonce
    invitation.continuation_token_ciphertext = seal_invitation_delivery(
        address="continuation@graf.invalid",
        raw_token=raw_token,
        key=encryption_key,
    )
    invitation.continuation_expires_at = min(
        invitation.expires_at,
        now + timedelta(seconds=SHARE_INVITATION_CONTINUATION_TTL_SECONDS),
    )
    invitation.continuation_used_at = None
    await db.flush()
    return nonce


async def share_invitation_continuation_matches(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    nonce: str,
    address: str | None = None,
) -> bool:
    """Check an active invitation continuation without consuming it."""
    now = datetime.now(UTC)
    statement = select(MeetingShareInvitation.id).where(
        MeetingShareInvitation.workspace_id == workspace_id,
        MeetingShareInvitation.continuation_nonce == nonce,
        MeetingShareInvitation.status.in_(ACTIVE_INVITATION_STATES),
        MeetingShareInvitation.continuation_used_at.is_(None),
        MeetingShareInvitation.continuation_expires_at > now,
        MeetingShareInvitation.expires_at > now,
    )
    if address is not None:
        statement = statement.where(
            MeetingShareInvitation.normalized_address_hash.in_(invitation_address_hashes(address))
        )
    return await db.scalar(statement) is not None


async def consume_share_invitation_continuation(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    nonce: str,
    encryption_key: bytes,
) -> str | None:
    now = datetime.now(UTC)
    invitation = await db.scalar(
        select(MeetingShareInvitation).where(
            MeetingShareInvitation.workspace_id == workspace_id,
            MeetingShareInvitation.continuation_nonce == nonce,
            MeetingShareInvitation.status.in_(ACTIVE_INVITATION_STATES),
            MeetingShareInvitation.continuation_used_at.is_(None),
            MeetingShareInvitation.continuation_expires_at > now,
            MeetingShareInvitation.expires_at > now,
        )
    )
    if invitation is None:
        return None
    # Keep the same meeting -> invitation lock order as revoke/create/accept.
    # The first lookup is only a candidate read; the locked re-read below is
    # the authority after the meeting mutation lock is held.
    await lock_shareable_meeting(
        db,
        workspace_id=workspace_id,
        meeting_id=invitation.meeting_id,
    )
    invitation = await db.scalar(
        select(MeetingShareInvitation)
        .where(
            MeetingShareInvitation.id == invitation.id,
            MeetingShareInvitation.workspace_id == workspace_id,
            MeetingShareInvitation.continuation_nonce == nonce,
            MeetingShareInvitation.status.in_(ACTIVE_INVITATION_STATES),
            MeetingShareInvitation.continuation_used_at.is_(None),
            MeetingShareInvitation.continuation_expires_at > now,
            MeetingShareInvitation.expires_at > now,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if invitation is None or not invitation.continuation_token_ciphertext:
        return None
    try:
        marker, raw_token = open_invitation_delivery(
            invitation.continuation_token_ciphertext,
            key=encryption_key,
        )
    except ProblemDetail:
        return None
    if marker != "continuation@graf.invalid":
        return None

    # Keep the row locked and let identity validation finish before consuming
    # the exchange. A wrong logged-in account must be able to retry with the
    # correct verified address.
    await db.flush()
    return raw_token


async def finalize_share_invitation_continuation(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    nonce: str,
) -> bool:
    now = datetime.now(UTC)
    invitation = await db.scalar(
        select(MeetingShareInvitation)
        .where(
            MeetingShareInvitation.workspace_id == workspace_id,
            MeetingShareInvitation.continuation_nonce == nonce,
            MeetingShareInvitation.continuation_used_at.is_(None),
            MeetingShareInvitation.status.in_((*ACTIVE_INVITATION_STATES, "accepted")),
        )
        .with_for_update()
    )
    if invitation is None:
        return False
    invitation.continuation_used_at = now
    invitation.continuation_nonce = None
    invitation.continuation_token_ciphertext = None
    invitation.continuation_expires_at = None
    await db.flush()
    return True


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

    meeting = await lock_shareable_meeting(db, workspace_id=workspace_id, meeting_id=meeting.id)
    decision = await decide_meeting_access(
        db, meeting, workspace_id=workspace_id, viewer_user_id=actor_user_id
    )
    if not decision.can_share:
        raise ProblemDetail(status=404, code="invitation_not_found", title="Invitation not found")
    await enforce_share_rate_limit(
        db,
        workspace_id=workspace_id,
        user_id=actor_user_id,
        device_id=device_id,
        action_key="revoke",
    )
    invitation = await db.scalar(
        select(MeetingShareInvitation).where(
            MeetingShareInvitation.workspace_id == workspace_id,
            MeetingShareInvitation.meeting_id == meeting.id,
            MeetingShareInvitation.id == invitation_id,
            MeetingShareInvitation.status.in_(REVOCABLE_INVITATION_STATES),
        )
    )
    if invitation is None:
        raise ProblemDetail(status=404, code="invitation_not_found", title="Invitation not found")
    invitation.status = "revoked"
    invitation.revoked_at = datetime.now(UTC)
    invitation.encrypted_delivery_address = ""
    invitation.encrypted_recipient_address = None
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
    encryption_key: bytes,
    recipient_user_active: bool | None = None,
) -> tuple[MeetingShareGrant, str] | None:
    from twobrain_rec_server.cabinet.egress import record_egress_audit_event

    await enforce_share_rate_limit(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        device_id=device_id,
        action_key="accept",
    )
    if recipient_user_active is False:
        return None
    if recipient_user_active is None:
        user = await db.scalar(
            select(UserIdentity).where(
                UserIdentity.id == user_id,
                UserIdentity.status == "active",
            )
        )
        if user is None:
            return None
    token_hash = hash_share_token(raw_token)
    invitation = await db.scalar(
        select(MeetingShareInvitation).where(
            MeetingShareInvitation.workspace_id == workspace_id,
            MeetingShareInvitation.token_hash == token_hash,
            MeetingShareInvitation.status.in_(ACTIVE_INVITATION_STATES),
        )
    )
    replay = False
    if invitation is None:
        invitation = await db.scalar(
            select(MeetingShareInvitation).where(
                MeetingShareInvitation.workspace_id == workspace_id,
                MeetingShareInvitation.token_hash == token_hash,
                MeetingShareInvitation.status == "accepted",
                MeetingShareInvitation.resolved_user_id == user_id,
            )
        )
        replay = invitation is not None
    if invitation is None:
        return None
    await lock_shareable_meeting(db, workspace_id=workspace_id, meeting_id=invitation.meeting_id)
    invitation = await db.scalar(
        select(MeetingShareInvitation)
        .where(
            MeetingShareInvitation.id == invitation.id,
            MeetingShareInvitation.workspace_id == workspace_id,
            MeetingShareInvitation.token_hash == token_hash,
            MeetingShareInvitation.status.in_((*ACTIVE_INVITATION_STATES, "accepted")),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if invitation is None:
        return None
    if invitation.status == "accepted":
        if invitation.resolved_user_id != user_id:
            return None
        replay = True
    elif replay:
        return None
    if invitation.expires_at <= datetime.now(UTC):
        if not replay:
            invitation.status = "expired"
            invitation.encrypted_delivery_address = ""
            invitation.encrypted_recipient_address = None
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
    if replay:
        if (
            grant is None
            or (grant.expires_at is not None and grant.expires_at <= datetime.now(UTC))
            or not invitation.grant_token_ciphertext
        ):
            return None
        try:
            marker, grant_raw_token = open_invitation_delivery(
                invitation.grant_token_ciphertext,
                key=encryption_key,
            )
        except ProblemDetail:
            return None
        if (
            marker != "grant-token@graf.invalid"
            or hash_share_token(grant_raw_token) != grant.share_token_hash
        ):
            return None
        return grant, grant_raw_token
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
    else:
        metadata = grant.metadata_json if isinstance(grant.metadata_json, dict) else {}
        if (
            metadata.get("source") != "accepted_external_invitation"
            or metadata.get("recipient_address_hash") != invitation.normalized_address_hash
        ):
            # Never downgrade or rebind an existing internal grant as a side
            # effect of accepting an external invitation.
            return None
    grant.content_scope = invitation.content_scope
    grant.can_download = invitation.can_download
    grant.can_export = invitation.can_export
    if grant.expires_at is None or grant.expires_at > invitation.expires_at:
        grant.expires_at = invitation.expires_at
    # The email bearer is an exchange credential, never the long-lived recipient
    # grant credential returned to the authenticated user.
    grant_raw_token = secrets.token_urlsafe(32)
    grant.share_token_hash = hash_share_token(grant_raw_token)
    grant.metadata_json = {
        "source": "accepted_external_invitation",
        "recipient_address_hash": invitation.normalized_address_hash,
    }
    invitation.status = "accepted"
    invitation.accepted_at = datetime.now(UTC)
    invitation.resolved_user_id = user_id
    invitation.encrypted_delivery_address = ""
    invitation.encrypted_recipient_address = None
    invitation.grant_token_ciphertext = seal_invitation_delivery(
        address="grant-token@graf.invalid",
        raw_token=grant_raw_token,
        key=encryption_key,
    )
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
    return grant, grant_raw_token


async def share_invitation_preview(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    raw_token: str,
) -> ShareInvitationPreview | None:
    """Return only meeting metadata for an unexpired, unconsumed invitation."""
    row = await db.execute(
        select(Meeting, MeetingShareInvitation.expires_at, MeetingShareInvitation.content_scope)
        .join(MeetingShareInvitation, MeetingShareInvitation.meeting_id == Meeting.id)
        .where(
            Meeting.workspace_id == workspace_id,
            MeetingShareInvitation.workspace_id == workspace_id,
            MeetingShareInvitation.token_hash == hash_share_token(raw_token),
            MeetingShareInvitation.status.in_(ACTIVE_INVITATION_STATES),
            MeetingShareInvitation.expires_at > datetime.now(UTC),
            Meeting.deletion_state == DeletionState.NONE.value,
        )
    )
    result = row.one_or_none()
    if result is None:
        return None
    meeting, expires_at, content_scope = result
    return ShareInvitationPreview(
        meeting_title=(meeting.title or "Встреча")[:160],
        occurred_at=meeting.started_at or meeting.created_at,
        duration_seconds=max(0, meeting.duration_seconds),
        expires_at=expires_at,
        content_scope=content_scope,
    )


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

    meeting = await lock_shareable_meeting(db, workspace_id=workspace_id, meeting_id=meeting.id)
    decision = await decide_meeting_access(
        db,
        meeting,
        workspace_id=workspace_id,
        viewer_user_id=actor_user_id,
    )
    if not decision.can_share:
        raise ProblemDetail(status=403, code="share_forbidden", title="Share is not available")
    await enforce_share_rate_limit(
        db,
        workspace_id=workspace_id,
        user_id=actor_user_id,
        device_id=device_id,
        action_key="revoke",
    )

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
    recipient_proof: ShareRecipientAccessProof | None = None,
) -> Meeting | None:
    from twobrain_rec_server.cabinet.egress import record_egress_audit_event

    await enforce_share_rate_limit(
        db,
        workspace_id=workspace_id,
        user_id=viewer_user_id,
        device_id=device_id,
        action_key="resolve",
    )
    token_hash = hash_share_token(share_token)
    now = datetime.now(UTC)
    grant = await db.scalar(
        select(MeetingShareGrant).where(
            MeetingShareGrant.workspace_id == workspace_id,
            MeetingShareGrant.share_token_hash == token_hash,
            MeetingShareGrant.grantee_user_id == viewer_user_id,
            MeetingShareGrant.audience_type == "user",
            MeetingShareGrant.status == "active",
            MeetingShareGrant.expires_at.is_(None) | (MeetingShareGrant.expires_at > now),
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
        recipient_proof=recipient_proof,
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
        audience_type=grant.audience_type,  # type: ignore[arg-type]
        content_scope=grant.content_scope,  # type: ignore[arg-type]
        expires_at=grant.expires_at,
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
