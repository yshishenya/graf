from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from twobrain_rec_server.billing.catalog import PERSONAL_STORAGE_BYTES


@dataclass(frozen=True, slots=True)
class BillingIdentity:
    user_id: UUID
    workspace_id: UUID
    email: str


def billing_identity(*, seed: int = 1) -> BillingIdentity:
    value = f"{seed:032x}"[-32:]
    return BillingIdentity(
        user_id=UUID(value),
        workspace_id=uuid4(),
        email=f"billing-{seed}@example.test",
    )


def billing_now() -> datetime:
    return datetime(2026, 1, 15, 9, 0, tzinfo=UTC)


def billing_workspace_defaults() -> dict[str, object]:
    return {"plan_code": "free", "capacity_bytes": PERSONAL_STORAGE_BYTES // 8}
