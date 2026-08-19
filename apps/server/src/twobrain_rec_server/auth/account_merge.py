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

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.audit import write_auth_audit_event
from twobrain_rec_server.db.models import (
    AccountClosureRequest,
    AccountMergeIntent,
    AccountMergeJournal,
    AuthSession,
    AuthSessionDeviceBinding,
    CalendarSource,
    ExternalIdentity,
    MediaRevision,
    Meeting,
    MeetingDeletionRequest,
    ProcessingPlaceholder,
    ProcessingWorkflow,
    RegisteredDevice,
    TrackArtifact,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.tenant_context import (
    AccountMergeTenantContext,
    apply_tenant_context,
)

MERGE_POLICY_VERSION = 1
MERGE_INTENT_TTL_SECONDS = 15 * 60
ACTIVE_INTENT_STATES = ("initiated", "awaiting_proof", "preview_ready", "confirmed")
TERMINAL_INTENT_STATES = ("completed", "cancelled", "expired", "rejected", "blocked", "failed")


class AccountMergeError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


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

    source_meeting_ids = tuple(
        await db.scalars(
            select(Meeting.id)
            .where(Meeting.created_by_user_id == source_user_id)
            .order_by(Meeting.id)
        )
    )
    source_meetings = list(
        await db.scalars(
            select(Meeting).where(Meeting.created_by_user_id == source_user_id).order_by(Meeting.id)
        )
    )
    counts = MergeEntityCounts(
        meetings=len(source_meetings),
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
    memberships = list(
        await db.scalars(
            select(WorkspaceMembership).where(
                WorkspaceMembership.user_id.in_((survivor_user_id, source_user_id)),
                WorkspaceMembership.status == "active",
            )
        )
    )
    roles: dict[UUID, set[str]] = {}
    for membership in memberships:
        roles.setdefault(membership.workspace_id, set()).add(membership.role)
    if any(len(values) > 1 for values in roles.values()):
        blockers.add("workspace_role_conflict")

    source_owned_workspaces = set(
        await db.scalars(select(Workspace.id).where(Workspace.owner_user_id == source_user_id))
    )
    survivor_owned_workspaces = set(
        await db.scalars(select(Workspace.id).where(Workspace.owner_user_id == survivor_user_id))
    )
    personal_source = set(
        await db.scalars(
            select(Workspace.id).where(
                Workspace.id.in_(source_owned_workspaces), Workspace.kind == "personal"
            )
        )
    )
    personal_survivor = set(
        await db.scalars(
            select(Workspace.id).where(
                Workspace.id.in_(survivor_owned_workspaces), Workspace.kind == "personal"
            )
        )
    )
    if personal_source and personal_survivor:
        blockers.add("workspace_ownership_conflict")

    survivor_meeting_keys = {
        (workspace_id_value, local_recording_id)
        for workspace_id_value, local_recording_id in await db.execute(
            select(Meeting.workspace_id, Meeting.local_recording_id).where(
                Meeting.created_by_user_id == survivor_user_id
            )
        )
    }
    if any(
        (meeting.workspace_id, meeting.local_recording_id) in survivor_meeting_keys
        for meeting in source_meetings
    ):
        blockers.add("meeting_owner_conflict")

    if source_owned_workspaces:
        active_calendar = await db.scalar(
            select(CalendarSource.id)
            .where(
                CalendarSource.owner_user_id == source_user_id,
                CalendarSource.connection_state == "active",
            )
            .limit(1)
        )
        if active_calendar is not None:
            blockers.add("calendar_ownership_conflict")
        active_billing = await db.scalar(
            select(WorkspaceSubscription.workspace_id)
            .where(
                WorkspaceSubscription.workspace_id.in_(source_owned_workspaces),
                WorkspaceSubscription.state != "free",
            )
            .limit(1)
        )
        if active_billing is not None:
            blockers.add("billing_conflict")

    closing = await db.scalar(
        select(AccountClosureRequest.id)
        .where(
            AccountClosureRequest.requested_by_user_id.in_((survivor_user_id, source_user_id)),
            AccountClosureRequest.state.in_(("scheduled", "finalizing")),
        )
        .limit(1)
    )
    deletion = (
        await db.scalar(
            select(MeetingDeletionRequest.id)
            .where(
                MeetingDeletionRequest.meeting_id.in_(source_meeting_ids),
                MeetingDeletionRequest.state.in_(("requested", "accepted", "processing")),
            )
            .limit(1)
        )
        if source_meeting_ids
        else None
    )
    if closing is not None or deletion is not None:
        blockers.add("deletion_state_conflict")

    return MergePreview(
        survivor_user_id=survivor_user_id,
        source_user_id=source_user_id,
        counts=counts,
        blocker_codes=tuple(sorted(blockers)),
    )


async def create_merge_intent(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    survivor_user_id: UUID,
    source_user_id: UUID,
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
    if existing is not None:
        await apply_tenant_context(
            db,
            AccountMergeTenantContext(
                intent_id=existing.id,
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
        existing.preview_fingerprint = preview.fingerprint
        existing.status = "blocked" if preview.blocker_codes else "preview_ready"
        existing.blocker_code = preview.blocker_codes[0] if preview.blocker_codes else None
        existing.email_proof_state = email_proof_state
        existing.oauth_proof_state = oauth_proof_state
        return existing, preview
    preview = await _merge_preview_from_db(
        db,
        workspace_id=workspace_id,
        survivor_user_id=survivor_user_id,
        source_user_id=source_user_id,
    )
    intent = AccountMergeIntent(
        workspace_id=workspace_id,
        survivor_user_id=survivor_user_id,
        source_user_id=source_user_id,
        email_proof_state=email_proof_state,
        oauth_proof_state=oauth_proof_state,
        preview_fingerprint=preview.fingerprint,
        policy_version=preview.policy_version,
        status="blocked" if preview.blocker_codes else "preview_ready",
        blocker_code=preview.blocker_codes[0] if preview.blocker_codes else None,
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
    db.add(intent)
    await db.flush()
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
    return intent, preview


async def preview_merge_intent(db: AsyncSession, *, intent_id: UUID) -> MergePreview:
    intent = await db.get(AccountMergeIntent, intent_id)
    if intent is None:
        raise AccountMergeError("merge_intent_not_found")
    await apply_tenant_context(
        db,
        AccountMergeTenantContext(
            intent_id=intent.id,
            workspace_id=intent.workspace_id,
            survivor_user_id=intent.survivor_user_id,
            source_user_id=intent.source_user_id,
        ),
    )
    if intent.status in TERMINAL_INTENT_STATES and intent.status not in {"completed", "blocked"}:
        raise AccountMergeError(intent.error_code or intent.status)
    if _aware(intent.expires_at) <= datetime.now(UTC) and intent.status != "completed":
        intent.status = "expired"
        intent.error_code = "merge_intent_expired"
        raise AccountMergeError("merge_intent_expired")
    return await _merge_preview_from_db(
        db,
        workspace_id=intent.workspace_id,
        survivor_user_id=intent.survivor_user_id,
        source_user_id=intent.source_user_id,
    )


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
    await apply_tenant_context(
        db,
        AccountMergeTenantContext(
            intent_id=intent.id,
            workspace_id=intent.workspace_id,
            survivor_user_id=intent.survivor_user_id,
            source_user_id=intent.source_user_id,
        ),
    )
    if intent.status == "completed":
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
        return AccountMergeResult(
            intent.id,
            "expired",
            intent.survivor_user_id,
            intent.source_user_id,
            MergeEntityCounts(),
        )
    if intent.email_proof_state != "verified" or intent.oauth_proof_state != "verified":
        intent.status = "rejected"
        intent.error_code = "proof_required"
        raise AccountMergeError("proof_required")
    key_hash = sha256(idempotency_key.encode("utf-8")).hexdigest()
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

    preview = await _merge_preview_from_db(
        db,
        workspace_id=intent.workspace_id,
        survivor_user_id=intent.survivor_user_id,
        source_user_id=intent.source_user_id,
    )
    ensure_preview_confirmable(preview, fingerprint=preview_fingerprint)
    if intent.preview_fingerprint != preview.fingerprint:
        raise AccountMergeError("merge_preview_stale")

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
    for identity in source_identities:
        duplicate = survivor_identities.get((identity.provider, identity.provider_subject))
        if duplicate is not None and duplicate.id != identity.id:
            identity.is_active = False
            identity.is_verified = False
        else:
            identity.user_id = intent.survivor_user_id

    source_memberships = list(
        await db.scalars(
            select(WorkspaceMembership)
            .where(WorkspaceMembership.user_id == intent.source_user_id)
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
            await db.execute(
                delete(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == membership.workspace_id,
                    WorkspaceMembership.user_id == intent.source_user_id,
                )
            )

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
        RegisteredDevice.__table__.update()
        .where(RegisteredDevice.user_id.in_(user_ids))
        .values(status="revoked", registration_state="revoked", revoked_by=intent.survivor_user_id)
    )
    sessions = list(
        await db.scalars(
            select(AuthSession).where(AuthSession.user_id.in_(user_ids)).with_for_update()
        )
    )
    for session in sessions:
        session.status = "revoked"
    if sessions:
        await db.execute(
            AuthSessionDeviceBinding.__table__.update()
            .where(
                AuthSessionDeviceBinding.auth_session_id.in_([session.id for session in sessions])
            )
            .values(device_state="blocked", revocation_reason="account_merge")
        )

    source = next(user for user in locked_users if user.id == intent.source_user_id)
    source.status = "merged"
    source.merged_into_user_id = intent.survivor_user_id
    source.merged_at = now
    intent.status = "completed"
    intent.confirmed_at = now
    intent.completed_at = now
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
