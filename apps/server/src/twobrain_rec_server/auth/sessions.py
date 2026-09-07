from __future__ import annotations

import hashlib
import secrets
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import (
    AuthCallbackState,
    AuthSession,
    AuthSessionDeviceBinding,
    RegisteredDevice,
)

SESSION_TOKEN_TTL_SECONDS = 86_400
CALLBACK_STATE_TTL_SECONDS = 900


def issue_session_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def fingerprint_identity(subject: str, provider: str, workspace_id: UUID) -> str:
    if provider == "email":
        return hash_token(f"email:{subject}:{workspace_id}")
    if provider == "email_magic_link":
        return hash_token(f"magic:{subject}:{workspace_id}")
    return hash_token(f"{workspace_id}|{provider}|{subject}")


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
    expires_at: datetime | None = None,
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
        expires_at=expires_at or session_expiry(now, ttl_seconds=ttl_seconds),
        status="active",
        claims_fingerprint=claims_fingerprint,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return IssuedAuthSession(
        id=session.id, token=raw_token, token_hash=token_hash, expires_at=session.expires_at
    )


def client_metadata(user_agent: str | None, *, browser_only: bool = False) -> tuple[str, str]:
    """Bounded display hints; never an authentication or device trust signal."""
    import re

    agent = (user_agent or '')[:2048]
    desktop = re.search(r'(?:^|\s)GRAFDesktop/(unknown|[0-9]+(?:\.[0-9]+){1,4})(?=\s|$)', agent)
    if desktop and not browser_only and len(desktop[1]) <= 40:
        return 'macos', desktop[1]
    family = next((name for token, name in (
        ('Edg/', 'edge'), ('EdgiOS/', 'edge'), ('EdgA/', 'edge'),
        ('Firefox/', 'firefox'), ('FxiOS/', 'firefox'), ('Chrome/', 'chrome'),
        ('CriOS/', 'chrome'), ('Safari/', 'safari'),
    ) if token in agent), 'unknown')
    operating_system = next((name for token, name in (
        ('iPhone', 'ios'), ('iPad', 'ios'), ('Android', 'android'),
        ('Macintosh', 'macos'), ('Mac OS X', 'macos'), ('Windows', 'windows'),
        ('Linux', 'linux'),
    ) if token in agent), 'unknown')
    return 'web', f'browser:{family}:{operating_system}'


async def create_login_device(
    db: AsyncSession, *, user_id: UUID, workspace_id: UUID,
    user_agent: str | None = None, metadata: tuple[str, str | None] | None = None,
    browser_only: bool = False, now: datetime | None = None,
) -> RegisteredDevice:
    platform, version = metadata or client_metadata(user_agent, browser_only=browser_only)
    device = RegisteredDevice(
        user_id=user_id, workspace_id=workspace_id, device_public_id=f'login:{uuid4()}',
        platform=platform, client_version=version, status='active',
        registration_state='approved', trusted_by=user_id, last_seen_at=now or datetime.now(UTC),
    )
    db.add(device)
    await db.flush()
    return device


def session_device_access(
    session: AuthSession, devices_by_id: dict[UUID, RegisteredDevice],
    bindings: Iterable[AuthSessionDeviceBinding],
) -> tuple[bool, RegisteredDevice | None]:
    """Resolve a bound client, or a legitimate API bootstrap without any binding."""
    links = list(bindings)
    if session.device_id is None and not links:
        return True, None
    device_ids = {link.registered_device_id for link in links}
    if len(device_ids) != 1 or (
        session.device_id is not None and device_ids != {session.device_id}
    ):
        return False, None
    device = devices_by_id.get(next(iter(device_ids)))
    if device is None or (
        device.user_id != session.user_id or device.workspace_id != session.workspace_id
        or device.status != 'active' or device.registration_state != 'approved'
        or any(link.auth_session_id != session.id or link.device_state != 'trusted' for link in links)
    ):
        return False, None
    return True, device


async def revoke_auth_sessions(db: AsyncSession, sessions: Iterable[AuthSession]) -> int:
    rows = list(sessions)
    ids = [session.id for session in rows]
    if not ids:
        return 0
    # Match the activity writer's session-before-binding lock order.
    ids = list(await db.scalars(select(AuthSession.id).where(
        AuthSession.id.in_(ids)).order_by(AuthSession.id).with_for_update()))
    links = await db.scalars(select(AuthSessionDeviceBinding).where(
        AuthSessionDeviceBinding.auth_session_id.in_(ids)).with_for_update())
    for link in links:
        link.device_state = 'blocked'
        link.revocation_reason = 'session_revoked'
    changed = list(await db.scalars(update(AuthSession).where(
        AuthSession.id.in_(ids), AuthSession.status == 'active',
    ).values(status='revoked').returning(AuthSession.id)))
    await db.flush()
    return len(changed)


async def revoke_registered_devices(
    db: AsyncSession, devices: Iterable[RegisteredDevice], *, actor_user_id: UUID,
) -> tuple[int, int]:
    rows = list(devices)
    ids = [device.id for device in rows]
    if not ids:
        return 0, 0
    linked_sessions = select(AuthSessionDeviceBinding.auth_session_id).where(
        AuthSessionDeviceBinding.registered_device_id.in_(ids))
    sessions = list(await db.scalars(select(AuthSession).where(
        or_(AuthSession.device_id.in_(ids), AuthSession.id.in_(linked_sessions)),
        or_(*(and_(AuthSession.user_id == device.user_id,
                   AuthSession.workspace_id == device.workspace_id) for device in rows)),
    ).order_by(AuthSession.id).with_for_update()))
    count = await revoke_auth_sessions(db, sessions)
    for device in rows:
        device.status = 'revoked'
        device.registration_state = 'revoked'
        device.revoked_by = actor_user_id
    await db.flush()
    return len(rows), count


async def resolve_session_device(
    db: AsyncSession, session: AuthSession,
) -> tuple[bool, RegisteredDevice | None]:
    links = list(await db.scalars(select(AuthSessionDeviceBinding).where(
        AuthSessionDeviceBinding.auth_session_id == session.id)))
    ids = {link.registered_device_id for link in links}
    if session.device_id is not None:
        ids.add(session.device_id)
    devices = list(await db.scalars(select(RegisteredDevice).where(RegisteredDevice.id.in_(ids)))) if ids else []
    return session_device_access(session, {device.id: device for device in devices}, links)


async def record_session_activity(
    db: AsyncSession, session: AuthSession, device: RegisteredDevice | None,
    *, now: datetime | None = None,
) -> None:
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(seconds=300)
    touched = await db.scalar(update(AuthSession).where(
        AuthSession.id == session.id, AuthSession.status == 'active',
        AuthSession.expires_at > now,
        or_(AuthSession.last_seen_at.is_(None), AuthSession.last_seen_at <= cutoff),
    ).values(last_seen_at=now).returning(AuthSession.id).execution_options(synchronize_session=False))
    if touched is not None and device is not None:
        await db.execute(update(RegisteredDevice).where(
            RegisteredDevice.id == device.id, RegisteredDevice.status == 'active',
        ).values(last_seen_at=now).execution_options(synchronize_session=False))
        await db.execute(update(AuthSessionDeviceBinding).where(
            AuthSessionDeviceBinding.auth_session_id == session.id,
            AuthSessionDeviceBinding.registered_device_id == device.id,
            AuthSessionDeviceBinding.device_state == 'trusted',
        ).values(last_heartbeat_at=now).execution_options(synchronize_session=False))
