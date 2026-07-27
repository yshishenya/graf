from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, distinct, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import (
    ExternalIdentity,
    WorkspaceMembership,
    WorkspaceProviderLinkState,
)


@dataclass(frozen=True)
class LinkResult:
    status: str
    user_id: UUID
    provider: str
    linked_identity_id: UUID
    message: str


class LinkError(ValueError):
    """Structured link operation error."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


def _is_external_identity_unique_conflict(exc: IntegrityError) -> bool:
    message = str(exc.orig).lower()
    return (
        "external_identities.provider" in message
        and "external_identities.provider_subject" in message
    ) or any(
        constraint in message
        for constraint in (
            "external_identities_provider_provider_subject_key",
            "uq_external_identities_provider",
        )
    )


async def _find_existing_identity(
    db: AsyncSession,
    *,
    provider: str,
    provider_subject: str,
) -> ExternalIdentity | None:
    return await db.scalar(
        select(ExternalIdentity).where(
            and_(
                ExternalIdentity.provider == provider,
                ExternalIdentity.provider_subject == provider_subject,
            )
        )
    )


async def _find_workspace_candidates(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    exclude_user_id: UUID,
    email: str | None,
    phone: str | None,
) -> list[UUID]:
    conditions = [WorkspaceMembership.workspace_id == workspace_id]
    if email and phone:
        conditions.append(
            or_(
                and_(ExternalIdentity.email.is_not(None), ExternalIdentity.email == email),
                and_(ExternalIdentity.phone.is_not(None), ExternalIdentity.phone == phone),
            )
        )
    elif email:
        conditions.append(ExternalIdentity.email == email)
    elif phone:
        conditions.append(ExternalIdentity.phone == phone)
    else:
        return []

    rows = await db.execute(
        select(distinct(ExternalIdentity.user_id))
        .join(WorkspaceMembership, WorkspaceMembership.user_id == ExternalIdentity.user_id)
        .where(
            *conditions,
            ExternalIdentity.user_id != exclude_user_id,
        )
    )
    return list(rows.scalars().all())


async def _anchor_identity_for_user(db: AsyncSession, user_id: UUID) -> UUID | None:
    return await db.scalar(
        select(ExternalIdentity.id)
        .where(ExternalIdentity.user_id == user_id)
        .order_by(ExternalIdentity.created_at.asc())
        .limit(1)
    )


async def _membership_or_error(db: AsyncSession, user_id: UUID, workspace_id: UUID) -> None:
    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
    )
    if membership is None:
        raise LinkError("link_not_authorized", "user is not a member of workspace")


async def link_provider_identity(
    db: AsyncSession,
    *,
    user_id: UUID,
    provider: str,
    provider_subject: str,
    expected_workspace_id: UUID,
    display_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> LinkResult:
    provider = provider.strip().lower()
    await _membership_or_error(db, user_id, expected_workspace_id)

    existing_identity = await _find_existing_identity(
        db,
        provider=provider,
        provider_subject=provider_subject,
    )
    if existing_identity is not None:
        if existing_identity.user_id == user_id:
            return LinkResult(
                status="confirmed",
                user_id=user_id,
                provider=provider,
                linked_identity_id=existing_identity.id,
                message="identity already linked",
            )
        raise LinkError("link_conflict", "provider identity already linked to another user")

    candidate_user_ids = await _find_workspace_candidates(
        db,
        workspace_id=expected_workspace_id,
        exclude_user_id=user_id,
        email=(email or "").strip() or None,
        phone=(phone or "").strip() or None,
    )
    if len(candidate_user_ids) == 1:
        target_user_id = candidate_user_ids[0]
        target_identity = await db.scalar(
            select(ExternalIdentity.id)
            .where(ExternalIdentity.user_id == target_user_id)
            .order_by(ExternalIdentity.created_at.asc())
            .limit(1)
        )
        if target_identity is None:
            raise LinkError("link_rejected", "candidate identity lookup failed")

        source_identity_id = await _anchor_identity_for_user(db, user_id)
        if source_identity_id is None:
            raise LinkError("link_rejected", "initiating anchor identity missing")

        db.add(
            WorkspaceProviderLinkState(
                workspace_id=expected_workspace_id,
                initiating_user_id=user_id,
                source_provider_identity_id=source_identity_id,
                target_provider_identity_id=target_identity,
                candidate_identity_subject=provider_subject,
                candidate_email=email,
                candidate_phone=phone,
                status="requires_confirmation",
                resolution="pending",
                expires_at=datetime.now(UTC) + timedelta(hours=12),
            )
        )
        return LinkResult(
            status="requires_confirmation",
            user_id=user_id,
            provider=provider,
            linked_identity_id=target_identity,
            message="link requires confirmation",
        )
    if len(candidate_user_ids) > 1:
        raise LinkError("link_conflict", "multiple candidate users found")

    try:
        async with db.begin_nested():
            record = ExternalIdentity(
                user_id=user_id,
                provider=provider,
                provider_subject=provider_subject,
                provider_username=None,
                email=email,
                phone=phone,
                display_name=display_name,
                is_verified=True,
                last_seen_at=datetime.now(UTC),
                meta={"expected_workspace_id": str(expected_workspace_id)},
            )
            db.add(record)
            await db.flush()
    except IntegrityError as exc:
        if _is_external_identity_unique_conflict(exc):
            raise LinkError("link_conflict", "provider identity already linked to another user") from exc
        raise
    return LinkResult(
        status="confirmed",
        user_id=user_id,
        provider=provider,
        linked_identity_id=record.id,
        message="identity linked",
    )
