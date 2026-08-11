from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from uuid import UUID


class ProviderEventError(ValueError):
    pass


def validate_provider_identifier(value: object) -> str:
    """Return a provider id safe to use as one API path segment."""
    if not isinstance(value, str) or not 1 <= len(value) <= 160:
        raise ValueError("provider identifier is invalid")
    if value != value.strip() or not all(
        char.isascii() and (char.isalnum() or char in "-_.") for char in value
    ):
        raise ValueError("provider identifier is invalid")
    return value


def validate_webhook_secret(*, supplied: str | None, expected: str | None) -> None:
    if not supplied or not expected or not hmac.compare_digest(supplied.strip(), expected.strip()):
        raise ProviderEventError("provider webhook authentication failed")


def redacted_event_metadata(event: ProviderEvent) -> dict[str, str]:
    metadata = {
        "provider_event_id": event.event_id,
        "event_type": event.event_type,
        "object_id": event.object_id,
        "occurred_at": event.occurred_at.isoformat(),
        "payload_hash": event.payload_hash,
    }
    if event.workspace_id is not None:
        metadata["workspace_id"] = str(event.workspace_id)
    return metadata


@dataclass(frozen=True, slots=True)
class ProviderEvent:
    event_id: str
    event_type: str
    object_id: str
    occurred_at: datetime
    payload_hash: str
    workspace_id: UUID | None = None


def parse_provider_event(payload: dict[str, Any]) -> ProviderEvent:
    try:
        event_id = validate_provider_identifier(payload["id"])
        event_type = str(payload["event"]).strip()
        object_id = validate_provider_identifier(payload["object"]["id"])
        occurred_at = datetime.fromisoformat(str(payload["object"].get("created_at", "")).replace("Z", "+00:00"))
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ProviderEventError("malformed provider event") from exc
    if not event_id or not event_type:
        raise ProviderEventError("provider event identifiers are required")
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)
    workspace_id: UUID | None = None
    metadata = payload["object"].get("metadata", {})
    if isinstance(metadata, dict) and metadata.get("workspace_id"):
        try:
            workspace_id = UUID(str(metadata["workspace_id"]))
        except (ValueError, TypeError):
            raise ProviderEventError("provider workspace metadata is malformed") from None
    provider_object = payload["object"]
    raw_amount = provider_object.get("amount")
    safe_amount = {
        field: str(raw_amount[field])[:64]
        for field in ("value", "currency")
        if isinstance(raw_amount, dict) and isinstance(raw_amount.get(field), (str, int, float))
    }
    safe_payload = {
        "id": event_id,
        "event": event_type,
        "object_id": object_id,
        "workspace_id": str(workspace_id) if workspace_id else "",
        # Include only bounded, non-content fields in the replay fingerprint.
        # The raw provider body is never persisted or logged.
        "created_at": occurred_at.isoformat(),
        "status": str(provider_object.get("status", "")),
        "amount": safe_amount,
    }
    digest = sha256(repr(sorted(safe_payload.items())).encode()).hexdigest()
    return ProviderEvent(event_id, event_type, object_id, occurred_at, digest, workspace_id)


class WebhookInbox:
    """Small deterministic inbox primitive; persistence is supplied by the DB layer."""

    def __init__(self) -> None:
        self._events: dict[str, ProviderEvent] = {}

    def accept(self, event: ProviderEvent) -> str:
        previous = self._events.get(event.event_id)
        if previous is not None:
            return "duplicate" if previous.payload_hash == event.payload_hash else "replay_conflict"
        self._events[event.event_id] = event
        return "accepted"

    def seen(self, event_id: str) -> bool:
        return event_id in self._events
