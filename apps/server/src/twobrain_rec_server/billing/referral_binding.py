from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.referrals import (
    REFERRAL_TOKEN_MAX_AGE_DAYS,
    referral_token_hash,
    validate_referral_token,
)
from twobrain_rec_server.db.models import ReferralAttribution, ReferralLink
from twobrain_rec_server.db.tenant_context import (
    AuthReferralLookupContext,
    AuthReferralUserLookupContext,
    WorkspaceAuthContext,
    apply_tenant_context,
)


async def bind_referral_attribution(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
    token: str | None,
    now: datetime,
) -> bool:
    """Atomically bind one new invitee to a stable referral link."""
    if not token:
        return False
    try:
        token_hash = referral_token_hash(validate_referral_token(token))
    except ValueError:
        return False
    await apply_tenant_context(
        db,
        AuthReferralLookupContext(
            workspace_id=workspace_id,
            user_id=user_id,
            token_hash=token_hash,
        ),
    )
    try:
        link = await db.scalar(
            select(ReferralLink)
            .where(ReferralLink.token_hash == token_hash, ReferralLink.state == "active")
            .with_for_update()
        )
        if link is None or link.inviter_user_id == user_id:
            return False
        if link.expires_at is not None and now.astimezone(UTC) >= link.expires_at.astimezone(UTC):
            return False
        await apply_tenant_context(db, AuthReferralUserLookupContext(user_id=user_id))
        existing = await db.scalar(
            select(ReferralAttribution.id).where(ReferralAttribution.invitee_user_id == user_id)
        )
        if existing is not None:
            return False
        await apply_tenant_context(
            db,
            AuthReferralLookupContext(
                workspace_id=workspace_id,
                user_id=user_id,
                token_hash=token_hash,
                referral_link_id=link.id,
            ),
        )
        attribution = await db.scalar(
            select(ReferralAttribution)
            .where(
                ReferralAttribution.referral_link_id == link.id,
                ReferralAttribution.invitee_user_id.is_(None),
                ReferralAttribution.state == "issued",
            )
            .with_for_update()
        )
        if attribution is not None:
            first_touched_at = attribution.first_touched_at
            if first_touched_at is not None:
                touched = first_touched_at.astimezone(UTC)
                if now.astimezone(UTC) - touched > timedelta(days=REFERRAL_TOKEN_MAX_AGE_DAYS):
                    return False
            attribution.invitee_user_id = user_id
            attribution.first_touched_at = attribution.first_touched_at or now
            attribution.bound_at = now
            attribution.state = "registered"
            return True
        try:
            async with db.begin_nested():
                db.add(
                    ReferralAttribution(
                        workspace_id=link.workspace_id,
                        inviter_user_id=link.inviter_user_id,
                        invitee_user_id=user_id,
                        referral_link_id=link.id,
                        token_hash=link.token_hash,
                        campaign_version=link.campaign_version,
                        first_touched_at=now,
                        bound_at=now,
                        state="registered",
                    )
                )
                await db.flush()
        except IntegrityError:
            return False
        return True
    finally:
        await apply_tenant_context(
            db,
            WorkspaceAuthContext(
                workspace_id=workspace_id,
                user_id=user_id,
                context_kind="auth_bootstrap",
            ),
        )
