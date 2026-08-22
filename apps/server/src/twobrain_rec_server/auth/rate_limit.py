from __future__ import annotations

import hashlib
import hmac
import math
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.sessions import hash_token
from twobrain_rec_server.db.models import AuthRateLimitBucket
from twobrain_rec_server.db.tenant_context import WorkspaceAuthContext, apply_tenant_context

AUTH_RATE_LIMITS: dict[str, tuple[int, int]] = {
    "email_code_start_address": (3, 15 * 60),
    "email_code_start_ip": (20, 15 * 60),
    "email_code_start_invitation": (5, 15 * 60),
    "email_code_verify_address": (10, 15 * 60),
    "email_code_verify_ip": (40, 15 * 60),
    "email_code_verify_state": (10, 15 * 60),
    "provider_start_ip": (20, 15 * 60),
    "provider_start_provider": (100, 15 * 60),
    "provider_callback_ip": (60, 15 * 60),
    "provider_callback_state": (5, 15 * 60),
    "provider_callback_provider": (300, 15 * 60),
    "billing_checkout_start": (5, 15 * 60),
    "billing_status_refresh": (30, 15 * 60),
    "billing_promo_action": (20, 15 * 60),
    "billing_referral_issue": (5, 60 * 60),
}


async def enforce_auth_rate_limits(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    scopes: Iterable[tuple[str, str]],
    sessionmaker=None,
    scope_secret: str | None = None,
    now: datetime | None = None,
) -> int | None:
    """Consume hashed auth buckets in a committed, narrow auth context."""
    if sessionmaker is not None:
        async with sessionmaker() as rate_db:
            await apply_tenant_context(
                rate_db,
                WorkspaceAuthContext(workspace_id=workspace_id),
            )
            retry_after = await _enforce_auth_rate_limits_in_session(
                rate_db,
                workspace_id=workspace_id,
                scopes=scopes,
                scope_secret=scope_secret,
                now=now,
            )
            await rate_db.commit()
            return retry_after
    await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=workspace_id))
    return await _enforce_auth_rate_limits_in_session(
        db,
        workspace_id=workspace_id,
        scopes=scopes,
        scope_secret=scope_secret,
        now=now,
    )


async def _enforce_auth_rate_limits_in_session(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    scopes: Iterable[tuple[str, str]],
    scope_secret: str | None = None,
    now: datetime | None = None,
) -> int | None:
    resolved_now = now or datetime.now(UTC)
    retry_after: int | None = None
    ordered_scopes = sorted(scopes, key=lambda scope: not scope[0].endswith("_ip"))
    for action_key, raw_scope in ordered_scopes:
        if not raw_scope or action_key not in AUTH_RATE_LIMITS:
            continue
        limit, window_seconds = AUTH_RATE_LIMITS[action_key]
        scope_material = f"{action_key}:{raw_scope}".encode()
        scope_hash = (
            hmac.new(scope_secret.encode("utf-8"), scope_material, hashlib.sha256).hexdigest()
            if scope_secret
            else hash_token(scope_material.decode("utf-8"))
        )
        await db.execute(
            pg_insert(AuthRateLimitBucket)
            .values(
                workspace_id=workspace_id,
                scope_hash=scope_hash,
                action_key=action_key,
                window_started_at=resolved_now,
                attempt_count=0,
            )
            .on_conflict_do_nothing(
                index_elements=["workspace_id", "scope_hash", "action_key"]
            )
        )
        bucket = await db.scalar(
            select(AuthRateLimitBucket)
            .where(
                AuthRateLimitBucket.workspace_id == workspace_id,
                AuthRateLimitBucket.scope_hash == scope_hash,
                AuthRateLimitBucket.action_key == action_key,
            )
            .with_for_update()
        )
        if bucket is None:
            raise RuntimeError("auth rate limit bucket could not be created")
        window_started_at = bucket.window_started_at
        if window_started_at.tzinfo is None:
            window_started_at = window_started_at.replace(tzinfo=UTC)
        if resolved_now - window_started_at >= timedelta(seconds=window_seconds):
            bucket.window_started_at = resolved_now
            bucket.attempt_count = 0
            bucket.blocked_until = None
        blocked_until = bucket.blocked_until
        if blocked_until is not None and blocked_until.tzinfo is None:
            blocked_until = blocked_until.replace(tzinfo=UTC)
        if blocked_until is not None and blocked_until > resolved_now:
            retry_after = max(
                retry_after or 0,
                max(1, math.ceil((blocked_until - resolved_now).total_seconds())),
            )
            break
        if bucket.attempt_count >= limit:
            bucket.blocked_until = resolved_now + timedelta(seconds=window_seconds)
            retry_after = max(retry_after or 0, window_seconds)
            break
        bucket.attempt_count += 1
        bucket.last_attempt_at = resolved_now
    await db.flush()
    return retry_after
