from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.sql import Select


class BillingAuthorizationError(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class BillingActor:
    user_id: UUID
    workspace_id: UUID
    role: str

    @property
    def may_manage_billing(self) -> bool:
        return self.role == "owner"


def require_billing_owner(actor: BillingActor) -> None:
    if actor.role != "owner":
        raise BillingAuthorizationError("billing owner is required")


def require_authority_version(*, expected: int, actual: int) -> None:
    if expected != actual:
        raise BillingAuthorizationError("billing authority changed; reload and confirm again")


def lock_billing_row(statement: Select[tuple[object]]) -> Select[tuple[object]]:
    """Serialize a sensitive billing mutation in its surrounding transaction."""
    return statement.with_for_update(nowait=False, skip_locked=False)


def safe_audit_metadata(values: dict[str, object]) -> dict[str, str]:
    blocked = (
        "token",
        "secret",
        "payload",
        "card",
        "email",
        "meeting",
        "provider",
        "object_id",
    )
    return {
        str(key): str(value)[:160]
        for key, value in values.items()
        if not any(part in str(key).lower() for part in blocked)
    }
