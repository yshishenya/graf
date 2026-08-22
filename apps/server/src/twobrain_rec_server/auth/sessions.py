from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import AuthCallbackState, AuthSession

SESSION_TOKEN_TTL_SECONDS = 86_400
CALLBACK_STATE_TTL_SECONDS = 900


def issue_session_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_session_token(token: str) -> str:
    return hash_token(token)


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def is_session_token_valid(session: AuthSession, at: datetime) -> bool:
    return session.status == "active" and _as_aware_utc(session.expires_at) > at


def issue_callback_nonce() -> str:
    return secrets.token_urlsafe(24)


def callback_expiry(
    now: datetime | None = None,
    *,
    ttl_seconds: int | None = None,
) -> datetime:
    resolved_ttl = ttl_seconds if ttl_seconds is not None else CALLBACK_STATE_TTL_SECONDS
    return (now or datetime.now(UTC)) + timedelta(seconds=resolved_ttl)


@dataclass(frozen=True, slots=True)
class CreatedCallbackState:
    id: UUID
    state_nonce: str
    expected_state: str
    expires_at: datetime


def create_callback_state(
    db: AsyncSession,
    *,
    provider: str,
    workspace_id: UUID,
    requested_redirect: str | None,
    browser_state_nonce: str | None = None,
    ttl_seconds: int | None = None,
    now: datetime | None = None,
) -> CreatedCallbackState:
    state_nonce = issue_callback_nonce()
    expected_state = (
        hash_token(browser_state_nonce) if browser_state_nonce is not None else state_nonce
    )
    created = AuthCallbackState(
        id=uuid4(),
        provider=provider,
        state_nonce=state_nonce,
        workspace_id=workspace_id,
        requested_redirect=requested_redirect,
        expected_state=expected_state,
        expires_at=callback_expiry(now, ttl_seconds=ttl_seconds),
        result="pending",
        error_code=None,
    )
    db.add(created)
    return CreatedCallbackState(
        id=created.id,
        state_nonce=state_nonce,
        expected_state=expected_state,
        expires_at=created.expires_at,
    )


async def consume_callback_state(
    db: AsyncSession,
    *,
    provider: str,
    state_nonce: str,
    browser_state_nonce: str | None = None,
    now: datetime | None = None,
) -> AuthCallbackState:
    now = now or datetime.now(UTC)
    now = _as_aware_utc(now)
    state = await db.scalar(
        select(AuthCallbackState)
        .where(
            AuthCallbackState.provider == provider,
            AuthCallbackState.state_nonce == state_nonce,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if state is None:
        raise ValueError("callback state not found")
    if state.result != "pending":
        raise ValueError("callback state already consumed")
    if _as_aware_utc(state.expires_at) <= now:
        state.used_at = now
        state.result = "expired"
        raise ValueError("callback state expired")
    if state.expected_state != state_nonce and (
        browser_state_nonce is None or hash_token(browser_state_nonce) != state.expected_state
    ):
        raise ValueError("callback state browser binding invalid")
    state.used_at = now
    state.result = "completed"
    db.add(state)
    return state


def session_expiry(
    now: datetime | None = None,
    *,
    ttl_seconds: int | None = None,
) -> datetime:
    resolved_ttl = ttl_seconds if ttl_seconds is not None else SESSION_TOKEN_TTL_SECONDS
    return (now or datetime.now(UTC)) + timedelta(seconds=resolved_ttl)


@dataclass(frozen=True, slots=True)
class IssuedAuthSession:
    id: UUID
    token: str
    token_hash: str
    expires_at: datetime


async def issue_auth_session(
    db: AsyncSession,
    *,
    user_id: UUID,
    workspace_id: UUID,
    provider: str,
    device_id: UUID | None = None,
    claims_fingerprint: str | None = None,
    ttl_seconds: int | None = None,
    now: datetime | None = None,
) -> IssuedAuthSession:
    now = now or datetime.now(UTC)
    raw_token = issue_session_token()
    token_hash = hash_token(raw_token)
    session = AuthSession(
        user_id=user_id,
        workspace_id=workspace_id,
        device_id=device_id,
        provider=provider,
        session_token_hash=token_hash,
        issued_at=now,
        last_seen_at=now,
        expires_at=session_expiry(now, ttl_seconds=ttl_seconds),
        status="active",
        claims_fingerprint=claims_fingerprint,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return IssuedAuthSession(
        id=session.id, token=raw_token, token_hash=token_hash, expires_at=session.expires_at
    )
