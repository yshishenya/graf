"""Proof-bound, transactional account linking and merge operations.

The module intentionally keeps the merge policy explicit.  Unknown user-owned
references are left pointing at the archived source account; only references
whose semantics are safe and covered by the policy are reassigned.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from twobrain_rec_server.auth.audit import write_auth_audit_event
from twobrain_rec_server.billing.fair_use import fair_use_restricted_for_lineage
from twobrain_rec_server.billing.operations import CHECKOUT_BLOCKING_STATES
from twobrain_rec_server.billing.webhook_reconciliation import RECONCILABLE_WEBHOOK_STATES
from twobrain_rec_server.db.models import (
    AccountClosureRequest,
    AccountMergeIntent,
    AccountMergeJournal,
    AuthCallbackState,
    AuthSession,
    AuthSessionDeviceBinding,
    BillingEntitlementGrant,
    BillingNotificationPreference,
    BillingOperation,
    BillingPaymentMethod,
    BillingWebhookEvent,
    CalendarSettingsPreference,
    CalendarSource,
    ExportPackage,
    ExternalIdentity,
    FairUseReviewRecord,
    MediaRevision,
    Meeting,
    MeetingDeletionRequest,
    MeetingShareGrant,
    ProcessingPlaceholder,
    ProcessingWorkflow,
    ReferralAttribution,
    ReferralLink,
    RegisteredDevice,
    SummaryTemplate,
    TrackArtifact,
    UploadSession,
    UserIdentity,
    Workspace,
    WorkspaceJoinOffer,
    WorkspaceMembership,
    WorkspaceProviderLinkState,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.tenant_context import (
    AccountMergeTenantContext,
    apply_tenant_context,
)

MERGE_POLICY_VERSION = 2
MERGE_INTENT_TTL_SECONDS = 15 * 60
ACTIVE_INTENT_STATES = ("initiated", "awaiting_proof", "preview_ready", "confirmed")
TERMINAL_INTENT_STATES = ("completed", "cancelled", "expired", "rejected", "blocked", "failed")


class AccountMergeError(ValueError):
    def __init__(self, code: str, *, durable: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.durable = durable


@dataclass(frozen=True, slots=True)
class MergeEntityCounts:
    meetings: int = 0
    recordings: int = 0
    artifacts: int = 0
    processing: int = 0

    def as_json(self) -> dict[str, int]:
        return {
            "meetings": self.meetings,
            "recordings": self.recordings,
            "artifacts": self.artifacts,
            "processing": self.processing,
        }


@dataclass(frozen=True, slots=True)
class MergePreview:
    survivor_user_id: UUID
    source_user_id: UUID
    counts: MergeEntityCounts
    blocker_codes: tuple[str, ...]
    survivor_provider_ids: tuple[str, ...] = ()
    source_provider_ids: tuple[str, ...] = ()
    workspace_count_after: int = 0
    state_tokens: tuple[str, ...] = ()
    policy_version: int = MERGE_POLICY_VERSION

    @property
    def fingerprint(self) -> str:
        payload = ":".join(
            (
                str(self.policy_version),
                str(self.survivor_user_id),
                str(self.source_user_id),
                str(self.counts.meetings),
                str(self.counts.recordings),
                str(self.counts.artifacts),
                str(self.counts.processing),
                ",".join(self.blocker_codes),
                ",".join(self.survivor_provider_ids),
                ",".join(self.source_provider_ids),
                str(self.workspace_count_after),
                *self.state_tokens,
            )
        )
        return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AccountMergeResult:
    intent_id: UUID
    status: str
    survivor_user_id: UUID
    source_user_id: UUID
    counts: MergeEntityCounts
    blocker_codes: tuple[str, ...] = ()


def build_merge_preview(
    *,
    survivor_user_id: UUID,
    source_user_id: UUID,
    counts: MergeEntityCounts | None = None,
    role_conflict: bool = False,
    billing_conflict: bool = False,
    calendar_conflict: bool = False,
    deletion_conflict: bool = False,
) -> MergePreview:
    if survivor_user_id == source_user_id:
        raise AccountMergeError("merge_same_account")
    blockers = [
        code
        for code, present in (
            ("workspace_role_conflict", role_conflict),
            ("billing_conflict", billing_conflict),
            ("calendar_ownership_conflict", calendar_conflict),
            ("deletion_state_conflict", deletion_conflict),
        )
        if present
    ]
    return MergePreview(
        survivor_user_id=survivor_user_id,
        source_user_id=source_user_id,
        counts=counts or MergeEntityCounts(),
        blocker_codes=tuple(blockers),
    )


def ensure_preview_confirmable(preview: MergePreview, *, fingerprint: str) -> None:
    if preview.blocker_codes:
        raise AccountMergeError(preview.blocker_codes[0])
    if preview.fingerprint != fingerprint:
        raise AccountMergeError("merge_preview_stale")


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _state_digest(prefix: str, rows) -> str:
    normalized = sorted(
        "\x1f".join("" if value is None else str(value) for value in row) for row in rows
    )
    digest = sha256("\x1e".join(normalized).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


async def _count_for_meetings(
    db: AsyncSession,
    model: type,
    meeting_ids,
    column,
) -> int:
    if not meeting_ids:
        return 0
    return int(
        await db.scalar(select(func.count()).select_from(model).where(column.in_(meeting_ids))) or 0
    )


async def _lock_merge_domain_rows(
    db: AsyncSession,
    *,
    survivor_user_id: UUID,
    source_user_id: UUID,
) -> list[Workspace]:
    """Lock every mutable row that can change merge eligibility or access."""
    user_ids = (survivor_user_id, source_user_id)
    memberships = list(
        await db.scalars(
            select(WorkspaceMembership)
            .where(WorkspaceMembership.user_id.in_(user_ids))
            .order_by(WorkspaceMembership.workspace_id, WorkspaceMembership.user_id)
            .with_for_update()
        )
    )
    owned_workspaces = list(
        await db.scalars(
            select(Workspace)
            .where(Workspace.owner_user_id.in_(user_ids))
            .order_by(Workspace.id)
            .with_for_update()
        )
    )
    workspace_ids = {
        *(membership.workspace_id for membership in memberships),
        *(workspace.id for workspace in owned_workspaces),
    }
    if workspace_ids:
        await db.execute(
            select(Workspace.id)
            .where(Workspace.id.in_(workspace_ids))
            .order_by(Workspace.id)
            .with_for_update()
        )

    meetings = list(
        await db.scalars(
            select(Meeting)
            .where(Meeting.created_by_user_id.in_(user_ids))
            .order_by(Meeting.id)
            .with_for_update()
        )
    )
    source_meeting_ids = {
        meeting.id for meeting in meetings if meeting.created_by_user_id == source_user_id
    }
    source_workspace_ids = {
        workspace.id for workspace in owned_workspaces if workspace.owner_user_id == source_user_id
    }

    statements = [
        select(ExternalIdentity.id)
        .where(ExternalIdentity.user_id.in_(user_ids))
        .order_by(ExternalIdentity.id),
        select(AccountClosureRequest.id)
        .where(AccountClosureRequest.requested_by_user_id.in_(user_ids))
        .order_by(AccountClosureRequest.id),
        select(CalendarSource.id)
        .where(CalendarSource.owner_user_id.in_(user_ids))
        .order_by(CalendarSource.id),
        select(CalendarSettingsPreference.id)
        .where(CalendarSettingsPreference.owner_user_id.in_(user_ids))
        .order_by(CalendarSettingsPreference.id),
        select(WorkspaceJoinOffer.id)
        .where(WorkspaceJoinOffer.user_id.in_(user_ids))
        .order_by(WorkspaceJoinOffer.id),
        select(MeetingShareGrant.id)
        .where(MeetingShareGrant.grantee_user_id.in_(user_ids))
        .order_by(MeetingShareGrant.id),
        select(BillingNotificationPreference.user_id)
        .where(BillingNotificationPreference.user_id.in_(user_ids))
        .order_by(BillingNotificationPreference.user_id),
        select(SummaryTemplate.id)
        .where(SummaryTemplate.owner_user_id.in_(user_ids))
        .order_by(SummaryTemplate.id),
        select(UploadSession.id)
        .where(UploadSession.created_by_user_id.in_(user_ids))
        .order_by(UploadSession.id),
        select(ExportPackage.id)
        .where(ExportPackage.requested_by_user_id.in_(user_ids))
        .order_by(ExportPackage.id),
        select(RegisteredDevice.id)
        .where(RegisteredDevice.user_id.in_(user_ids))
        .order_by(RegisteredDevice.id),
        select(AuthSession.id).where(AuthSession.user_id.in_(user_ids)).order_by(AuthSession.id),
        select(FairUseReviewRecord.id)
        .where(
            or_(
                FairUseReviewRecord.subject_user_id.in_(user_ids),
                FairUseReviewRecord.workspace_id.in_(source_workspace_ids),
            )
        )
        .order_by(FairUseReviewRecord.id),
    ]
    if source_meeting_ids:
        statements.extend(
            (
                select(MediaRevision.id)
                .where(MediaRevision.meeting_id.in_(source_meeting_ids))
                .order_by(MediaRevision.id),
                select(TrackArtifact.id)
                .where(TrackArtifact.meeting_id.in_(source_meeting_ids))
                .order_by(TrackArtifact.id),
                select(ProcessingPlaceholder.id)
                .where(ProcessingPlaceholder.meeting_id.in_(source_meeting_ids))
                .order_by(ProcessingPlaceholder.id),
                select(ProcessingWorkflow.id)
                .where(ProcessingWorkflow.meeting_id.in_(source_meeting_ids))
                .order_by(ProcessingWorkflow.id),
                select(MeetingDeletionRequest.id)
                .where(
                    or_(
                        MeetingDeletionRequest.meeting_id.in_(source_meeting_ids),
                        MeetingDeletionRequest.requested_by_user_id == source_user_id,
                    )
                )
                .order_by(MeetingDeletionRequest.id),
            )
        )
    else:
        statements.append(
            select(MeetingDeletionRequest.id)
            .where(MeetingDeletionRequest.requested_by_user_id == source_user_id)
            .order_by(MeetingDeletionRequest.id)
        )
    if source_workspace_ids:
        statements.extend(
            (
                select(WorkspaceSubscription.workspace_id)
                .where(
                    or_(
                        WorkspaceSubscription.workspace_id.in_(source_workspace_ids),
                        WorkspaceSubscription.billing_owner_id == source_user_id,
                    )
                )
                .order_by(WorkspaceSubscription.workspace_id),
                select(BillingEntitlementGrant.id)
                .where(BillingEntitlementGrant.workspace_id.in_(source_workspace_ids))
                .order_by(BillingEntitlementGrant.id),
                select(BillingPaymentMethod.id)
                .where(
                    or_(
                        BillingPaymentMethod.workspace_id.in_(source_workspace_ids),
                        BillingPaymentMethod.owner_user_id == source_user_id,
                    )
                )
                .order_by(BillingPaymentMethod.id),
                select(BillingOperation.id)
                .where(BillingOperation.workspace_id.in_(source_workspace_ids))
                .order_by(BillingOperation.id),
                select(BillingWebhookEvent.id)
                .where(BillingWebhookEvent.workspace_id.in_(source_workspace_ids))
                .order_by(BillingWebhookEvent.id),
            )
        )
    statements.extend(
        (
            select(ReferralLink.id)
            .where(
                or_(
                    ReferralLink.inviter_user_id == source_user_id,
                    ReferralLink.workspace_id.in_(source_workspace_ids),
                )
            )
            .order_by(ReferralLink.id),
            select(ReferralAttribution.id)
            .where(
                or_(
                    ReferralAttribution.inviter_user_id == source_user_id,
                    ReferralAttribution.invitee_user_id == source_user_id,
                    ReferralAttribution.workspace_id.in_(source_workspace_ids),
                )
            )
            .order_by(ReferralAttribution.id),
        )
    )
    session_ids = tuple(
        await db.scalars(select(AuthSession.id).where(AuthSession.user_id.in_(user_ids)))
    )
    if session_ids:
        statements.append(
            select(AuthSessionDeviceBinding.id)
            .where(AuthSessionDeviceBinding.auth_session_id.in_(session_ids))
            .order_by(AuthSessionDeviceBinding.id)
        )
    for statement in statements:
        await db.execute(statement.with_for_update())
    return owned_workspaces


async def _merge_preview_from_db(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    survivor_user_id: UUID,
    source_user_id: UUID,
) -> MergePreview:
    if survivor_user_id == source_user_id:
        raise AccountMergeError("merge_same_account")
    users = list(
        await db.scalars(
            select(UserIdentity)
            .where(UserIdentity.id.in_((survivor_user_id, source_user_id)))
            .order_by(UserIdentity.id)
        )
    )
    by_id = {user.id: user for user in users}
    survivor = by_id.get(survivor_user_id)
    source = by_id.get(source_user_id)
    if survivor is None or survivor.status != "active":
        raise AccountMergeError("survivor_account_inactive")
    if source is None or source.status != "active":
        raise AccountMergeError("source_account_inactive")
    if survivor.organization_id != source.organization_id:
        raise AccountMergeError("account_organization_conflict")
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None or workspace.organization_id != survivor.organization_id:
        raise AccountMergeError("workspace_scope_denied")

    meeting_state_rows = list(
        await db.execute(
            select(
                Meeting.id,
                Meeting.workspace_id,
                Meeting.created_by_user_id,
                Meeting.local_recording_id,
                Meeting.status,
            )
            .where(Meeting.created_by_user_id.in_((survivor_user_id, source_user_id)))
            .order_by(Meeting.id)
        )
    )
    source_meeting_rows = [
        row for row in meeting_state_rows if row.created_by_user_id == source_user_id
    ]
    source_meeting_ids = tuple(row.id for row in source_meeting_rows)
    counts = MergeEntityCounts(
        meetings=len(source_meeting_rows),
        recordings=await _count_for_meetings(
            db, MediaRevision, source_meeting_ids, MediaRevision.meeting_id
        ),
        artifacts=await _count_for_meetings(
            db, TrackArtifact, source_meeting_ids, TrackArtifact.meeting_id
        ),
        processing=(
            await _count_for_meetings(
                db, ProcessingPlaceholder, source_meeting_ids, ProcessingPlaceholder.meeting_id
            )
            + await _count_for_meetings(
                db, ProcessingWorkflow, source_meeting_ids, ProcessingWorkflow.meeting_id
            )
        ),
    )

    blockers: set[str] = set()
    all_memberships = list(
        await db.scalars(
            select(WorkspaceMembership).where(
                WorkspaceMembership.user_id.in_((survivor_user_id, source_user_id)),
            )
        )
    )
    memberships = [membership for membership in all_memberships if membership.status == "active"]
    roles: dict[UUID, set[str]] = {}
    for membership in memberships:
        roles.setdefault(membership.workspace_id, set()).add(membership.role)
    if any(len(values) > 1 for values in roles.values()):
        blockers.add("workspace_role_conflict")

    workspace_rows = list(
        await db.execute(
            select(Workspace.id, Workspace.kind, Workspace.owner_user_id, Workspace.name)
            .where(
                or_(
                    Workspace.owner_user_id.in_((survivor_user_id, source_user_id)),
                    Workspace.id.in_(membership.workspace_id for membership in memberships),
                )
            )
            .order_by(Workspace.id)
        )
    )
    source_owned_workspaces = {
        workspace_id_value
        for workspace_id_value, _kind, owner_user_id, _name in workspace_rows
        if owner_user_id == source_user_id
    }
    survivor_owned_workspaces = {
        workspace_id_value
        for workspace_id_value, _kind, owner_user_id, _name in workspace_rows
        if owner_user_id == survivor_user_id
    }
    personal_source = {
        workspace_id_value
        for workspace_id_value, kind, owner_user_id, _name in workspace_rows
        if owner_user_id == source_user_id and kind == "personal"
    }
    personal_survivor = {
        workspace_id_value
        for workspace_id_value, kind, owner_user_id, _name in workspace_rows
        if owner_user_id == survivor_user_id and kind == "personal"
    }
    active_owner_memberships = {
        (membership.workspace_id, membership.user_id)
        for membership in memberships
        if membership.role == "owner"
    }
    owned_workspace_pairs = {
        *((workspace_id_value, source_user_id) for workspace_id_value in source_owned_workspaces),
        *(
            (workspace_id_value, survivor_user_id)
            for workspace_id_value in survivor_owned_workspaces
        ),
    }
    missing_owner_membership = not owned_workspace_pairs <= active_owner_memberships
    if len(personal_source) > 1 or len(personal_survivor) > 1 or missing_owner_membership:
        blockers.add("workspace_ownership_conflict")

    identity_rows = list(
        await db.execute(
            select(
                ExternalIdentity.id,
                ExternalIdentity.user_id,
                ExternalIdentity.provider,
                ExternalIdentity.is_active,
                ExternalIdentity.is_verified,
            )
            .where(
                ExternalIdentity.user_id.in_((survivor_user_id, source_user_id)),
            )
            .order_by(ExternalIdentity.id)
        )
    )
    providers_by_user = {survivor_user_id: set(), source_user_id: set()}
    for _id, user_id, provider, is_active, is_verified in identity_rows:
        if is_active and is_verified:
            providers_by_user[user_id].add(provider)
    survivor_provider_ids = tuple(sorted(providers_by_user[survivor_user_id]))
    source_provider_ids = tuple(sorted(providers_by_user[source_user_id]))
    state_tokens = [
        _state_digest(
            "identity",
            (
                (identity_id, user_id, provider, is_active, is_verified)
                for identity_id, user_id, provider, is_active, is_verified in identity_rows
            ),
        ),
        _state_digest(
            "membership",
            (
                (
                    membership.workspace_id,
                    membership.user_id,
                    membership.role,
                    membership.status,
                )
                for membership in all_memberships
            ),
        ),
        _state_digest("workspace", workspace_rows),
    ]

    state_tokens.append(_state_digest("meeting", meeting_state_rows))
    survivor_meeting_keys = {
        (workspace_id_value, local_recording_id)
        for _id, workspace_id_value, created_by_user_id, local_recording_id, _status in meeting_state_rows
        if created_by_user_id == survivor_user_id
    }
    if any(
        (meeting.workspace_id, meeting.local_recording_id) in survivor_meeting_keys
        for meeting in source_meeting_rows
    ):
        blockers.add("meeting_owner_conflict")

    now = datetime.now(UTC)
    calendar_rows = list(
        await db.execute(
            select(
                CalendarSource.id,
                CalendarSource.workspace_id,
                CalendarSource.owner_user_id,
                CalendarSource.connection_state,
            )
            .where(CalendarSource.owner_user_id == source_user_id)
            .order_by(CalendarSource.id)
        )
    )
    state_tokens.append(_state_digest("calendar", calendar_rows))
    if any(connection_state == "active" for *_prefix, connection_state in calendar_rows):
        blockers.add("calendar_ownership_conflict")

    subscription_rows = list(
        await db.execute(
            select(
                WorkspaceSubscription.workspace_id,
                WorkspaceSubscription.billing_owner_id,
                WorkspaceSubscription.state,
                WorkspaceSubscription.plan_code,
                WorkspaceSubscription.cycle,
                WorkspaceSubscription.recurring_allowed,
                WorkspaceSubscription.paid_through,
                WorkspaceSubscription.trial_ends_at,
                WorkspaceSubscription.billing_anchor,
            )
            .where(
                or_(
                    WorkspaceSubscription.workspace_id.in_(source_owned_workspaces),
                    WorkspaceSubscription.billing_owner_id == source_user_id,
                )
            )
            .order_by(WorkspaceSubscription.workspace_id)
        )
    )
    entitlement_rows = list(
        await db.execute(
            select(
                BillingEntitlementGrant.id,
                BillingEntitlementGrant.workspace_id,
                BillingEntitlementGrant.ends_at,
            )
            .where(BillingEntitlementGrant.workspace_id.in_(source_owned_workspaces))
            .order_by(BillingEntitlementGrant.id)
        )
    )
    payment_method_rows = list(
        await db.execute(
            select(
                BillingPaymentMethod.id,
                BillingPaymentMethod.workspace_id,
                BillingPaymentMethod.owner_user_id,
                BillingPaymentMethod.state,
                BillingPaymentMethod.is_default,
            )
            .where(
                or_(
                    BillingPaymentMethod.workspace_id.in_(source_owned_workspaces),
                    BillingPaymentMethod.owner_user_id == source_user_id,
                )
            )
            .order_by(BillingPaymentMethod.id)
        )
    )
    operation_rows = list(
        await db.execute(
            select(BillingOperation.id, BillingOperation.workspace_id, BillingOperation.state)
            .where(BillingOperation.workspace_id.in_(source_owned_workspaces))
            .order_by(BillingOperation.id)
        )
    )
    webhook_rows = list(
        await db.execute(
            select(
                BillingWebhookEvent.id,
                BillingWebhookEvent.workspace_id,
                BillingWebhookEvent.state,
            )
            .where(BillingWebhookEvent.workspace_id.in_(source_owned_workspaces))
            .order_by(BillingWebhookEvent.id)
        )
    )
    state_tokens.append(
        _state_digest(
            "billing",
            (
                *subscription_rows,
                *entitlement_rows,
                *payment_method_rows,
                *operation_rows,
                *webhook_rows,
            ),
        )
    )
    active_subscription = any(
        state != "free"
        or plan_code != "free"
        or cycle != "none"
        or recurring_allowed
        or (paid_through is not None and _aware(paid_through) > now)
        or (trial_ends_at is not None and _aware(trial_ends_at) > now)
        or billing_anchor is not None
        for (
            _workspace_id,
            _billing_owner_id,
            state,
            plan_code,
            cycle,
            recurring_allowed,
            paid_through,
            trial_ends_at,
            billing_anchor,
        ) in subscription_rows
    )
    if (
        active_subscription
        or any(_aware(ends_at) > now for _id, _workspace_id, ends_at in entitlement_rows)
        or any(state == "active" for *_prefix, state, _is_default in payment_method_rows)
        or any(state in CHECKOUT_BLOCKING_STATES for _id, _workspace_id, state in operation_rows)
        or any(state in RECONCILABLE_WEBHOOK_STATES for _id, _workspace_id, state in webhook_rows)
    ):
        blockers.add("billing_conflict")

    fair_use_rows = list(
        await db.execute(
            select(
                FairUseReviewRecord.id,
                FairUseReviewRecord.workspace_id,
                FairUseReviewRecord.subject_user_id,
                FairUseReviewRecord.capability,
                FairUseReviewRecord.state,
            )
            .where(
                or_(
                    FairUseReviewRecord.subject_user_id == source_user_id,
                    FairUseReviewRecord.workspace_id.in_(source_owned_workspaces),
                )
            )
            .order_by(FairUseReviewRecord.id)
        )
    )
    state_tokens.append(_state_digest("fair-use", fair_use_rows))
    if await fair_use_restricted_for_lineage(
        db,
        user_id=source_user_id,
        include_confirmed=False,
    ):
        blockers.add("fair_use_conflict")

    referral_link_rows = list(
        await db.execute(
            select(
                ReferralLink.id,
                ReferralLink.workspace_id,
                ReferralLink.inviter_user_id,
                ReferralLink.state,
            )
            .where(
                or_(
                    ReferralLink.inviter_user_id == source_user_id,
                    ReferralLink.workspace_id.in_(source_owned_workspaces),
                )
            )
            .order_by(ReferralLink.id)
        )
    )
    referral_attribution_rows = list(
        await db.execute(
            select(
                ReferralAttribution.id,
                ReferralAttribution.workspace_id,
                ReferralAttribution.inviter_user_id,
                ReferralAttribution.invitee_user_id,
                ReferralAttribution.state,
            )
            .where(
                or_(
                    ReferralAttribution.inviter_user_id == source_user_id,
                    ReferralAttribution.invitee_user_id == source_user_id,
                    ReferralAttribution.workspace_id.in_(source_owned_workspaces),
                )
            )
            .order_by(ReferralAttribution.id)
        )
    )
    state_tokens.append(
        _state_digest("referral", (*referral_link_rows, *referral_attribution_rows))
    )
    nonterminal_referral_states = {
        "issued",
        "bound",
        "registered",
        "attributed",
        "pending_maturity",
        "available",
    }
    if any(state == "active" for *_prefix, state in referral_link_rows) or any(
        state in nonterminal_referral_states for *_prefix, state in referral_attribution_rows
    ):
        blockers.add("referral_conflict")

    closure_rows = list(
        await db.execute(
            select(
                AccountClosureRequest.id,
                AccountClosureRequest.requested_by_user_id,
                AccountClosureRequest.state,
            )
            .where(
                AccountClosureRequest.requested_by_user_id.in_((survivor_user_id, source_user_id))
            )
            .order_by(AccountClosureRequest.id)
        )
    )
    deletion_rows = list(
        await db.execute(
            select(
                MeetingDeletionRequest.id,
                MeetingDeletionRequest.meeting_id,
                MeetingDeletionRequest.requested_by_user_id,
                MeetingDeletionRequest.state,
            )
            .where(
                or_(
                    MeetingDeletionRequest.meeting_id.in_(source_meeting_ids),
                    MeetingDeletionRequest.requested_by_user_id == source_user_id,
                )
            )
            .order_by(MeetingDeletionRequest.id)
        )
    )
    state_tokens.append(_state_digest("deletion", (*closure_rows, *deletion_rows)))
    if any(state in {"scheduled", "finalizing"} for *_prefix, state in closure_rows) or any(
        state in {"requested", "accepted", "processing"} for *_prefix, state in deletion_rows
    ):
        blockers.add("deletion_state_conflict")

    template_rows = list(
        await db.execute(
            select(
                SummaryTemplate.id,
                SummaryTemplate.workspace_id,
                SummaryTemplate.owner_user_id,
                SummaryTemplate.template_key,
                SummaryTemplate.version,
                SummaryTemplate.status,
            )
            .where(SummaryTemplate.owner_user_id.in_((survivor_user_id, source_user_id)))
            .order_by(SummaryTemplate.id)
        )
    )
    survivor_template_keys = {
        (workspace_id_value, template_key, version)
        for _id, workspace_id_value, owner_user_id, template_key, version, _status in template_rows
        if owner_user_id == survivor_user_id
    }
    if any(
        (workspace_id_value, template_key, version) in survivor_template_keys
        for _id, workspace_id_value, owner_user_id, template_key, version, status in template_rows
        if owner_user_id == source_user_id and status == "active"
    ):
        blockers.add("settings_conflict")

    upload_rows = list(
        await db.execute(
            select(
                UploadSession.id,
                UploadSession.workspace_id,
                UploadSession.meeting_id,
                UploadSession.created_by_user_id,
                UploadSession.status,
                UploadSession.processing_status,
            )
            .where(UploadSession.created_by_user_id == source_user_id)
            .order_by(UploadSession.id)
        )
    )
    export_rows = list(
        await db.execute(
            select(
                ExportPackage.id,
                ExportPackage.workspace_id,
                ExportPackage.meeting_id,
                ExportPackage.requested_by_user_id,
                ExportPackage.status,
            )
            .where(ExportPackage.requested_by_user_id == source_user_id)
            .order_by(ExportPackage.id)
        )
    )
    if any(
        status in {"pending", "uploading", "retrying", "finalizing"}
        for *_prefix, status, _processing_status in upload_rows
    ):
        blockers.add("upload_in_progress")
    if any(status == "requested" for *_prefix, status in export_rows):
        blockers.add("export_in_progress")

    preference_rows = list(
        await db.execute(
            select(
                BillingNotificationPreference.user_id,
                BillingNotificationPreference.optional_email_enabled,
                BillingNotificationPreference.optional_in_app_enabled,
            ).where(BillingNotificationPreference.user_id.in_((survivor_user_id, source_user_id)))
        )
    )
    calendar_preference_rows = list(
        await db.execute(
            select(
                CalendarSettingsPreference.id,
                CalendarSettingsPreference.workspace_id,
                CalendarSettingsPreference.owner_user_id,
                CalendarSettingsPreference.join_prompt_enabled,
                CalendarSettingsPreference.record_prompt_enabled,
                CalendarSettingsPreference.show_upcoming_time,
                CalendarSettingsPreference.show_upcoming_title,
                CalendarSettingsPreference.include_events_without_participants,
                CalendarSettingsPreference.include_events_without_link_or_location,
                CalendarSettingsPreference.include_all_day_events,
                CalendarSettingsPreference.include_private_free_busy_prompt_candidates,
            )
            .where(CalendarSettingsPreference.owner_user_id.in_((survivor_user_id, source_user_id)))
            .order_by(CalendarSettingsPreference.id)
        )
    )
    offer_rows = list(
        await db.execute(
            select(
                WorkspaceJoinOffer.id,
                WorkspaceJoinOffer.workspace_id,
                WorkspaceJoinOffer.user_id,
                WorkspaceJoinOffer.invitation_id,
                WorkspaceJoinOffer.invited_role,
                WorkspaceJoinOffer.status,
                WorkspaceJoinOffer.expires_at,
            )
            .where(WorkspaceJoinOffer.user_id.in_((survivor_user_id, source_user_id)))
            .order_by(WorkspaceJoinOffer.id)
        )
    )
    grant_rows = list(
        await db.execute(
            select(
                MeetingShareGrant.id,
                MeetingShareGrant.workspace_id,
                MeetingShareGrant.meeting_id,
                MeetingShareGrant.grantee_user_id,
                MeetingShareGrant.audience_id,
                MeetingShareGrant.status,
                MeetingShareGrant.expires_at,
            )
            .where(MeetingShareGrant.grantee_user_id.in_((survivor_user_id, source_user_id)))
            .order_by(MeetingShareGrant.id)
        )
    )
    state_tokens.extend(
        (
            _state_digest("template", template_rows),
            _state_digest("upload", upload_rows),
            _state_digest("export", export_rows),
            _state_digest("preference", (*preference_rows, *calendar_preference_rows)),
            _state_digest("offer", offer_rows),
            _state_digest("grant", grant_rows),
        )
    )

    return MergePreview(
        survivor_user_id=survivor_user_id,
        source_user_id=source_user_id,
        counts=counts,
        blocker_codes=tuple(sorted(blockers)),
        survivor_provider_ids=survivor_provider_ids,
        source_provider_ids=source_provider_ids,
        workspace_count_after=len(workspace_rows),
        state_tokens=tuple(state_tokens),
    )


async def create_merge_intent(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    survivor_user_id: UUID,
    source_user_id: UUID,
    initiating_auth_session_id: UUID,
    source_external_identity_id: UUID,
    proof_callback_state_id: UUID,
    provider_link_state_id: UUID | None = None,
    email_proof_state: str = "missing",
    oauth_proof_state: str = "missing",
    now: datetime | None = None,
    ttl_seconds: int = MERGE_INTENT_TTL_SECONDS,
    actor_user_id: UUID | None = None,
) -> tuple[AccountMergeIntent, MergePreview]:
    now = now or datetime.now(UTC)
    existing = await db.scalar(
        select(AccountMergeIntent)
        .where(
            AccountMergeIntent.survivor_user_id == survivor_user_id,
            AccountMergeIntent.source_user_id == source_user_id,
            AccountMergeIntent.status.in_(ACTIVE_INTENT_STATES),
        )
        .with_for_update()
    )
    if existing is not None and _aware(existing.expires_at) <= now:
        existing.status = "expired"
        existing.error_code = "merge_intent_expired"
        await db.flush()
        existing = None
    intent = existing
    if intent is None:
        preview = await _merge_preview_from_db(
            db,
            workspace_id=workspace_id,
            survivor_user_id=survivor_user_id,
            source_user_id=source_user_id,
        )
        candidate = AccountMergeIntent(
            workspace_id=workspace_id,
            survivor_user_id=survivor_user_id,
            source_user_id=source_user_id,
            initiating_auth_session_id=initiating_auth_session_id,
            source_external_identity_id=source_external_identity_id,
            proof_callback_state_id=proof_callback_state_id,
            provider_link_state_id=provider_link_state_id,
            email_proof_state=email_proof_state,
            oauth_proof_state=oauth_proof_state,
            preview_fingerprint=preview.fingerprint,
            policy_version=preview.policy_version,
            status="blocked" if preview.blocker_codes else "preview_ready",
            blocker_code=preview.blocker_codes[0] if preview.blocker_codes else None,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        try:
            async with db.begin_nested():
                db.add(candidate)
                await db.flush()
            intent = candidate
        except IntegrityError:
            intent = await db.scalar(
                select(AccountMergeIntent)
                .where(
                    AccountMergeIntent.survivor_user_id == survivor_user_id,
                    AccountMergeIntent.source_user_id == source_user_id,
                    AccountMergeIntent.status.in_(ACTIVE_INTENT_STATES),
                )
                .with_for_update()
            )
            if intent is None:
                raise
    if any(
        value is None
        for value in (
            intent.initiating_auth_session_id,
            intent.source_external_identity_id,
            intent.proof_callback_state_id,
        )
    ):
        intent.status = "rejected"
        intent.error_code = "proof_required"
        raise AccountMergeError("proof_required")
    if (
        intent.initiating_auth_session_id != initiating_auth_session_id
        or intent.source_external_identity_id != source_external_identity_id
        or intent.proof_callback_state_id != proof_callback_state_id
        or intent.provider_link_state_id != provider_link_state_id
    ):
        raise AccountMergeError("account_state_changed")
    await apply_tenant_context(
        db,
        AccountMergeTenantContext(
            intent_id=intent.id,
            workspace_id=workspace_id,
            survivor_user_id=survivor_user_id,
            source_user_id=source_user_id,
        ),
    )
    preview = await _merge_preview_from_db(
        db,
        workspace_id=workspace_id,
        survivor_user_id=survivor_user_id,
        source_user_id=source_user_id,
    )
    intent.preview_fingerprint = preview.fingerprint
    intent.status = "blocked" if preview.blocker_codes else "preview_ready"
    intent.blocker_code = preview.blocker_codes[0] if preview.blocker_codes else None
    intent.email_proof_state = email_proof_state
    intent.oauth_proof_state = oauth_proof_state
    await write_auth_audit_event(
        db,
        workspace_id=workspace_id,
        event_type="account_merge_preview_prepared",
        actor_user_id=actor_user_id,
        user_id=survivor_user_id,
        metadata={"intent_id_sha256": sha256(str(intent.id).encode("utf-8")).hexdigest()},
    )
    return intent, preview


async def preview_merge_intent(db: AsyncSession, *, intent_id: UUID) -> MergePreview:
    intent = await db.get(AccountMergeIntent, intent_id)
    if intent is None:
        raise AccountMergeError("merge_intent_not_found")
    if intent.status in TERMINAL_INTENT_STATES and intent.status not in {"completed", "blocked"}:
        raise AccountMergeError(intent.error_code or intent.status)
    if _aware(intent.expires_at) <= datetime.now(UTC) and intent.status != "completed":
        intent.status = "expired"
        intent.error_code = "merge_intent_expired"
        await db.flush()
        raise AccountMergeError("merge_intent_expired", durable=True)
    await apply_tenant_context(
        db,
        AccountMergeTenantContext(
            intent_id=intent.id,
            workspace_id=intent.workspace_id,
            survivor_user_id=intent.survivor_user_id,
            source_user_id=intent.source_user_id,
        ),
    )
    preview = await _merge_preview_from_db(
        db,
        workspace_id=intent.workspace_id,
        survivor_user_id=intent.survivor_user_id,
        source_user_id=intent.source_user_id,
    )
    if intent.status == "blocked" and not preview.blocker_codes:
        raise AccountMergeError("merge_blocked")
    return preview


async def confirm_merge_intent(
    db: AsyncSession,
    *,
    intent_id: UUID,
    preview_fingerprint: str,
    idempotency_key: str,
    now: datetime | None = None,
) -> AccountMergeResult:
    now = now or datetime.now(UTC)
    intent = await db.scalar(
        select(AccountMergeIntent).where(AccountMergeIntent.id == intent_id).with_for_update()
    )
    if intent is None:
        raise AccountMergeError("merge_intent_not_found")
    key_hash = sha256(idempotency_key.encode("utf-8")).hexdigest()
    if intent.status == "completed":
        if intent.idempotency_key_hash != key_hash:
            raise AccountMergeError("merge_idempotency_conflict")
        journal = await db.scalar(
            select(AccountMergeJournal).where(AccountMergeJournal.merge_intent_id == intent.id)
        )
        if journal is None:
            raise AccountMergeError("merge_journal_missing")
        counts = MergeEntityCounts(
            **{key: int(value) for key, value in journal.counts_json.items()}
        )
        return AccountMergeResult(
            intent.id, "completed", intent.survivor_user_id, intent.source_user_id, counts
        )
    if intent.status in TERMINAL_INTENT_STATES:
        raise AccountMergeError(intent.error_code or intent.status)
    if _aware(intent.expires_at) <= _aware(now):
        intent.status = "expired"
        intent.error_code = "merge_intent_expired"
        await db.flush()
        raise AccountMergeError("merge_intent_expired", durable=True)
    if intent.email_proof_state != "verified" or intent.oauth_proof_state != "verified":
        intent.status = "rejected"
        intent.error_code = "proof_required"
        await db.flush()
        raise AccountMergeError("proof_required", durable=True)
    if any(
        value is None
        for value in (
            intent.initiating_auth_session_id,
            intent.source_external_identity_id,
            intent.proof_callback_state_id,
        )
    ):
        raise AccountMergeError("proof_required")
    await apply_tenant_context(
        db,
        AccountMergeTenantContext(
            intent_id=intent.id,
            workspace_id=intent.workspace_id,
            survivor_user_id=intent.survivor_user_id,
            source_user_id=intent.source_user_id,
        ),
    )
    proof_session = await db.scalar(
        select(AuthSession)
        .where(AuthSession.id == intent.initiating_auth_session_id)
        .with_for_update()
    )
    proof_identity = await db.scalar(
        select(ExternalIdentity)
        .where(ExternalIdentity.id == intent.source_external_identity_id)
        .with_for_update()
    )
    proof_callback = await db.scalar(
        select(AuthCallbackState)
        .where(AuthCallbackState.id == intent.proof_callback_state_id)
        .with_for_update()
    )
    proof_link = (
        await db.scalar(
            select(WorkspaceProviderLinkState)
            .where(WorkspaceProviderLinkState.id == intent.provider_link_state_id)
            .with_for_update()
        )
        if intent.provider_link_state_id is not None
        else None
    )
    if (
        proof_session is None
        or proof_session.user_id != intent.survivor_user_id
        or proof_session.workspace_id != intent.workspace_id
        or proof_session.status != "active"
        or _aware(proof_session.expires_at) <= _aware(now)
        or proof_identity is None
        or proof_identity.user_id != intent.source_user_id
        or not proof_identity.is_active
        or not proof_identity.is_verified
        or proof_callback is None
        or proof_callback.workspace_id != intent.workspace_id
        or proof_callback.result != "completed"
        or proof_callback.used_at is None
        or (
            intent.provider_link_state_id is not None
            and (
                proof_link is None
                or proof_link.initiating_auth_session_id != proof_session.id
                or proof_link.callback_state_id != proof_callback.id
                or proof_link.status != "confirmed"
            )
        )
    ):
        raise AccountMergeError("proof_required")
    if intent.idempotency_key_hash not in (None, key_hash):
        raise AccountMergeError("merge_idempotency_conflict")
    intent.idempotency_key_hash = key_hash

    # Lock both account roots before reading the preview. User-owned rows moved
    # below reference these roots, so concurrent inserts/updates wait for this
    # transaction instead of changing the preview between check and use.
    user_ids = sorted((intent.survivor_user_id, intent.source_user_id), key=str)
    locked_users = list(
        await db.scalars(
            select(UserIdentity)
            .where(UserIdentity.id.in_(user_ids))
            .order_by(UserIdentity.id)
            .with_for_update()
        )
    )
    if len(locked_users) != 2 or any(user.status != "active" for user in locked_users):
        raise AccountMergeError("account_state_changed")

    locked_workspaces = await _lock_merge_domain_rows(
        db,
        survivor_user_id=intent.survivor_user_id,
        source_user_id=intent.source_user_id,
    )

    preview = await _merge_preview_from_db(
        db,
        workspace_id=intent.workspace_id,
        survivor_user_id=intent.survivor_user_id,
        source_user_id=intent.source_user_id,
    )
    ensure_preview_confirmable(preview, fingerprint=preview_fingerprint)
    if intent.preview_fingerprint != preview.fingerprint:
        raise AccountMergeError("merge_preview_stale")

    source_personal = [
        workspace
        for workspace in locked_workspaces
        if workspace.owner_user_id == intent.source_user_id and workspace.kind == "personal"
    ]
    survivor_personal = [
        workspace
        for workspace in locked_workspaces
        if workspace.owner_user_id == intent.survivor_user_id and workspace.kind == "personal"
    ]
    if len(source_personal) > 1 or len(survivor_personal) > 1:
        raise AccountMergeError("workspace_ownership_conflict")
    if source_personal and survivor_personal:
        preserved = source_personal[0]
        preserved.kind = "linked"
        if preserved.name == "Моё пространство":
            preserved.name = "Пространство из другого профиля"
        await db.flush()

    source_identities = list(
        await db.scalars(
            select(ExternalIdentity)
            .where(
                ExternalIdentity.user_id == intent.source_user_id,
                ExternalIdentity.is_active.is_(True),
            )
            .with_for_update()
        )
    )
    survivor_identities = {
        (identity.provider, identity.provider_subject): identity
        for identity in await db.scalars(
            select(ExternalIdentity)
            .where(ExternalIdentity.user_id == intent.survivor_user_id)
            .with_for_update()
        )
    }
    proof_identity_duplicate = survivor_identities.get(
        (proof_identity.provider, proof_identity.provider_subject)
    )
    deactivate_proof_identity = (
        proof_identity_duplicate is not None and proof_identity_duplicate.id != proof_identity.id
    )
    for identity in source_identities:
        if identity.id == proof_identity.id:
            continue
        duplicate = survivor_identities.get((identity.provider, identity.provider_subject))
        if duplicate is not None and duplicate.id != identity.id:
            identity.is_active = False
            identity.is_verified = False
        else:
            identity.user_id = intent.survivor_user_id

    source_memberships = list(
        await db.scalars(
            select(WorkspaceMembership)
            .where(
                WorkspaceMembership.user_id == intent.source_user_id,
                WorkspaceMembership.status == "active",
            )
            .with_for_update()
        )
    )
    for membership in source_memberships:
        existing = await db.get(
            WorkspaceMembership,
            {"workspace_id": membership.workspace_id, "user_id": intent.survivor_user_id},
            with_for_update=True,
        )
        if existing is None:
            membership.user_id = intent.survivor_user_id
        else:
            if existing.status == "active" and existing.role != membership.role:
                raise AccountMergeError("workspace_role_conflict")
            if existing.status != "active":
                existing.status = "active"
                existing.role = membership.role
            await db.execute(
                delete(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == membership.workspace_id,
                    WorkspaceMembership.user_id == intent.source_user_id,
                )
            )

    source_offers = list(
        await db.scalars(
            select(WorkspaceJoinOffer)
            .where(
                WorkspaceJoinOffer.user_id == intent.source_user_id,
                WorkspaceJoinOffer.status == "offered",
                WorkspaceJoinOffer.expires_at > now,
            )
            .with_for_update()
        )
    )
    for offer in source_offers:
        existing = await db.scalar(
            select(WorkspaceJoinOffer)
            .where(
                WorkspaceJoinOffer.user_id == intent.survivor_user_id,
                WorkspaceJoinOffer.invitation_id == offer.invitation_id,
            )
            .with_for_update()
        )
        if existing is None:
            offer.user_id = intent.survivor_user_id
        else:
            if (
                existing.status == "offered"
                and _aware(existing.expires_at) > _aware(now)
                and existing.invited_role != offer.invited_role
            ):
                raise AccountMergeError("workspace_role_conflict")
            if existing.status != "offered" or _aware(existing.expires_at) <= _aware(now):
                existing.status = "offered"
                existing.workspace_id = offer.workspace_id
                existing.workspace_name = offer.workspace_name
                existing.invited_role = offer.invited_role
                existing.expires_at = offer.expires_at
            offer.status = "rejected"

    source_share_grants = list(
        await db.scalars(
            select(MeetingShareGrant)
            .where(
                MeetingShareGrant.grantee_user_id == intent.source_user_id,
                MeetingShareGrant.audience_type == "user",
                MeetingShareGrant.status == "active",
                or_(MeetingShareGrant.expires_at.is_(None), MeetingShareGrant.expires_at > now),
            )
            .with_for_update()
        )
    )
    for grant in source_share_grants:
        existing = await db.scalar(
            select(MeetingShareGrant)
            .where(
                MeetingShareGrant.workspace_id == grant.workspace_id,
                MeetingShareGrant.meeting_id == grant.meeting_id,
                MeetingShareGrant.audience_type == "user",
                MeetingShareGrant.audience_id == intent.survivor_user_id,
                MeetingShareGrant.status == "active",
            )
            .with_for_update()
        )
        if existing is None:
            grant.grantee_user_id = intent.survivor_user_id
            grant.audience_id = intent.survivor_user_id
        else:
            if existing.expires_at is not None and _aware(existing.expires_at) <= _aware(now):
                existing.status = "revoked"
                existing.revoked_at = now
                existing.revoked_by_user_id = intent.survivor_user_id
                await db.flush()
                grant.grantee_user_id = intent.survivor_user_id
                grant.audience_id = intent.survivor_user_id
            else:
                grant.status = "revoked"
                grant.revoked_at = now
                grant.revoked_by_user_id = intent.survivor_user_id

    source_notification_preference = await db.get(
        BillingNotificationPreference,
        intent.source_user_id,
        with_for_update=True,
    )
    survivor_notification_preference = await db.get(
        BillingNotificationPreference,
        intent.survivor_user_id,
        with_for_update=True,
    )
    if source_notification_preference is not None:
        if survivor_notification_preference is None:
            source_notification_preference.user_id = intent.survivor_user_id
        else:
            survivor_notification_preference.optional_email_enabled = (
                survivor_notification_preference.optional_email_enabled
                and source_notification_preference.optional_email_enabled
            )
            survivor_notification_preference.optional_in_app_enabled = (
                survivor_notification_preference.optional_in_app_enabled
                and source_notification_preference.optional_in_app_enabled
            )
            await db.delete(source_notification_preference)

    source_calendar_preferences = list(
        await db.scalars(
            select(CalendarSettingsPreference)
            .where(CalendarSettingsPreference.owner_user_id == intent.source_user_id)
            .with_for_update()
        )
    )
    for preference in source_calendar_preferences:
        existing = await db.scalar(
            select(CalendarSettingsPreference)
            .where(
                CalendarSettingsPreference.workspace_id == preference.workspace_id,
                CalendarSettingsPreference.owner_user_id == intent.survivor_user_id,
            )
            .with_for_update()
        )
        if existing is None:
            preference.owner_user_id = intent.survivor_user_id
        else:
            await db.delete(preference)

    source_templates = list(
        await db.scalars(
            select(SummaryTemplate)
            .where(
                SummaryTemplate.owner_user_id == intent.source_user_id,
                SummaryTemplate.status == "active",
            )
            .with_for_update()
        )
    )
    for template in source_templates:
        collision = await db.scalar(
            select(SummaryTemplate.id)
            .where(
                SummaryTemplate.workspace_id == template.workspace_id,
                SummaryTemplate.owner_user_id == intent.survivor_user_id,
                SummaryTemplate.template_key == template.template_key,
                SummaryTemplate.version == template.version,
            )
            .with_for_update()
        )
        if collision is not None:
            raise AccountMergeError("settings_conflict")
        template.owner_user_id = intent.survivor_user_id

    await db.execute(
        Meeting.__table__.update()
        .where(Meeting.created_by_user_id == intent.source_user_id)
        .values(created_by_user_id=intent.survivor_user_id)
    )
    await db.execute(
        Workspace.__table__.update()
        .where(Workspace.owner_user_id == intent.source_user_id)
        .values(owner_user_id=intent.survivor_user_id)
    )
    await db.execute(
        WorkspaceSubscription.__table__.update()
        .where(WorkspaceSubscription.billing_owner_id == intent.source_user_id)
        .values(billing_owner_id=intent.survivor_user_id)
    )
    await db.execute(
        RegisteredDevice.__table__.update()
        .where(
            RegisteredDevice.user_id.in_(user_ids),
            or_(
                RegisteredDevice.status != "revoked",
                RegisteredDevice.registration_state != "revoked",
            ),
        )
        .values(status="revoked", registration_state="revoked", revoked_by=intent.survivor_user_id)
    )
    sessions = list(
        await db.scalars(
            select(AuthSession)
            .where(AuthSession.user_id.in_(user_ids), AuthSession.status == "active")
            .with_for_update()
        )
    )
    for session in sessions:
        if session.id != proof_session.id:
            session.status = "revoked"
    if sessions:
        await db.execute(
            AuthSessionDeviceBinding.__table__.update()
            .where(
                AuthSessionDeviceBinding.auth_session_id.in_([session.id for session in sessions])
            )
            .values(device_state="blocked", revocation_reason="account_merge")
        )

    journal = AccountMergeJournal(
        merge_intent_id=intent.id,
        workspace_id=intent.workspace_id,
        survivor_user_id=intent.survivor_user_id,
        source_user_id=intent.source_user_id,
        policy_version=preview.policy_version,
        preview_fingerprint=preview.fingerprint,
        status="completed",
        counts_json=preview.counts.as_json(),
        blocker_codes_json=[],
    )
    db.add(journal)
    await write_auth_audit_event(
        db,
        workspace_id=intent.workspace_id,
        event_type="account_merge_completed",
        actor_user_id=intent.survivor_user_id,
        user_id=intent.survivor_user_id,
        outcome="success",
        metadata={
            "merge_intent_id_sha256": sha256(str(intent.id).encode("utf-8")).hexdigest(),
            "source_user_id_sha256": sha256(str(intent.source_user_id).encode("utf-8")).hexdigest(),
            "policy_version": preview.policy_version,
            "meeting_count": preview.counts.meetings,
        },
    )
    await db.flush()
    finalized = (
        await db.execute(
            text(
                """
                with finalized_identity as (
                    update external_identities
                    set user_id = :proof_identity_user_id,
                        is_active = :proof_identity_active,
                        is_verified = :proof_identity_verified
                    where id = :proof_identity_id
                    returning id
                ), revoked_session as (
                    update auth_sessions
                    set status = 'revoked'
                    where id = :proof_session_id and status = 'active'
                    returning id
                ), merged_source as (
                    update user_identities
                    set status = 'merged',
                        merged_into_user_id = :survivor_user_id,
                        merged_at = :completed_at
                    where id = :source_user_id and status = 'active'
                    returning id
                ), completed_intent as (
                    update account_merge_intents
                    set status = 'completed',
                        confirmed_at = :completed_at,
                        completed_at = :completed_at
                    where id = :intent_id and status = 'preview_ready'
                    returning id
                )
                select
                    (select count(*) from finalized_identity),
                    (select count(*) from revoked_session),
                    (select count(*) from merged_source),
                    (select count(*) from completed_intent)
                """
            ),
            {
                "proof_identity_user_id": (
                    intent.source_user_id if deactivate_proof_identity else intent.survivor_user_id
                ),
                "proof_identity_active": not deactivate_proof_identity,
                "proof_identity_verified": not deactivate_proof_identity,
                "proof_identity_id": proof_identity.id,
                "proof_session_id": proof_session.id,
                "survivor_user_id": intent.survivor_user_id,
                "source_user_id": intent.source_user_id,
                "completed_at": now,
                "intent_id": intent.id,
            },
        )
    ).one()
    if finalized != (1, 1, 1, 1):
        raise AccountMergeError("account_state_changed")
    set_committed_value(
        proof_identity,
        "user_id",
        intent.source_user_id if deactivate_proof_identity else intent.survivor_user_id,
    )
    set_committed_value(proof_identity, "is_active", not deactivate_proof_identity)
    set_committed_value(proof_identity, "is_verified", not deactivate_proof_identity)
    set_committed_value(proof_session, "status", "revoked")
    source = next(user for user in locked_users if user.id == intent.source_user_id)
    set_committed_value(source, "status", "merged")
    set_committed_value(source, "merged_into_user_id", intent.survivor_user_id)
    set_committed_value(source, "merged_at", now)
    set_committed_value(intent, "status", "completed")
    set_committed_value(intent, "confirmed_at", now)
    set_committed_value(intent, "completed_at", now)
    return AccountMergeResult(
        intent.id, "completed", intent.survivor_user_id, intent.source_user_id, preview.counts
    )


async def cancel_merge_intent(db: AsyncSession, *, intent_id: UUID, actor_user_id: UUID) -> None:
    intent = await db.scalar(
        select(AccountMergeIntent).where(AccountMergeIntent.id == intent_id).with_for_update()
    )
    if intent is None:
        raise AccountMergeError("merge_intent_not_found")
    if intent.survivor_user_id != actor_user_id:
        raise AccountMergeError("workspace_scope_denied")
    if intent.status == "completed":
        raise AccountMergeError("merge_already_completed")
    if intent.status in TERMINAL_INTENT_STATES:
        return
    intent.status = "cancelled"
    intent.error_code = "merge_cancelled"
    await write_auth_audit_event(
        db,
        workspace_id=intent.workspace_id,
        event_type="account_merge_cancelled",
        actor_user_id=actor_user_id,
        outcome="success",
        metadata={"merge_intent_id_sha256": sha256(str(intent.id).encode("utf-8")).hexdigest()},
    )
