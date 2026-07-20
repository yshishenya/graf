from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import AuthAuditEvent

SENSITIVE_METADATA_KEYS = frozenset(
    {
        "authorization_code",
        "code",
        "device_public_id",
        "provider_code",
        "state",
        "state_nonce",
    }
)

DENIED_AUTH_ACCESS_METADATA_KEYS = frozenset(
    {
        "route_name",
        "outcome",
        "reason_code",
        "workspace_id",
        "organization_id",
        "user_id",
        "device_id",
        "provider",
        "context_kind",
        "request_id",
    }
)

ONBOARDING_AUDIT_METADATA_KEYS = frozenset(
    {"offer_id", "invitation_id", "workspace_kind", "status", "action"}
)


@dataclass(frozen=True, slots=True)
class AuthAuditEventRecord:
    workspace_id: UUID
    event_type: str
    actor_user_id: UUID | None = None
    actor_ip: str | None = None
    user_id: UUID | None = None
    provider: str | None = None
    outcome: str = "success"
    metadata: dict[str, object] | None = None


def _hash_value(value: str | None) -> str | None:
    if not value:
        return None
    return sha256(value.encode("utf-8")).hexdigest()


def sanitize_audit_metadata(metadata: Mapping[str, object] | None) -> dict[str, object]:
    if not metadata:
        return {}
    sanitized: dict[str, object] = {}
    for key, value in metadata.items():
        if key in SENSITIVE_METADATA_KEYS:
            sanitized[f"{key}_sha256"] = _hash_value(str(value)) if value is not None else None
        else:
            sanitized[key] = value
    return sanitized


def denied_auth_access_metadata(**values: object) -> dict[str, object]:
    return {
        key: value
        for key, value in values.items()
        if key in DENIED_AUTH_ACCESS_METADATA_KEYS and value is not None
    }


async def write_auth_audit_event(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_type: str,
    actor_user_id: UUID | None = None,
    actor_ip: str | None = None,
    user_id: UUID | None = None,
    provider: str | None = None,
    outcome: str = "success",
    metadata: dict[str, object] | None = None,
    request_id: str | None = None,
) -> AuthAuditEvent:
    payload = sanitize_audit_metadata(metadata)
    event = AuthAuditEvent(
        workspace_id=workspace_id,
        user_id=user_id,
        event_type=event_type,
        provider=provider,
        actor_user_id=actor_user_id,
        actor_ip_hash=_hash_value(actor_ip),
        request_id=request_id,
        outcome=outcome,
        metadata_json=payload,
    )
    db.add(event)
    return event


async def write_onboarding_audit_event(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
    event_type: str,
    metadata: Mapping[str, object] | None = None,
) -> AuthAuditEvent:
    """Persist only opaque onboarding state; never identity-match inputs."""

    safe_metadata = {
        key: value
        for key, value in (metadata or {}).items()
        if key in ONBOARDING_AUDIT_METADATA_KEYS
    }
    return await write_auth_audit_event(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        actor_user_id=user_id,
        event_type=event_type,
        metadata=safe_metadata,
    )
