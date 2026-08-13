from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import BillingLaunchGate

MANDATORY_BILLING_LAUNCH_GATES = frozenset(
    {
        "product",
        "unit_economics",
        "finance_accounting",
        "legal",
        "security_privacy",
        "qa_accessibility",
        "infrastructure",
        "provider_canary",
        "global_rollout",
    }
)


class BillingLaunchBlocked(RuntimeError):
    pass


def shop_id_hash(shop_id: str) -> str:
    value = shop_id.strip()
    if not value:
        raise BillingLaunchBlocked("billing shop identity is unavailable")
    return sha256(value.encode("utf-8")).hexdigest()


def provider_environment(environment: object) -> str:
    """Return the explicitly selected YooKassa environment.

    Test and production shops may share ``api.yookassa.ru``. Callers must pass
    the server-owned environment setting instead of deriving it from a URL.
    """
    value = str(environment).strip().lower()
    if value not in {"test", "production"}:
        raise ValueError("provider environment is invalid")
    return value


def _has_four_eyes_values(values: object) -> bool:
    """Validate the approved correction authority without storing money actions."""
    if not isinstance(values, dict):
        return False
    for scope in ("provider_correction", "off_provider_correction"):
        policy = values.get(scope)
        if not isinstance(policy, dict):
            return False
        threshold = policy.get("threshold_minor")
        approver_role = policy.get("approver_role")
        executor_role = policy.get("executor_role")
        if (
            isinstance(threshold, bool)
            or not isinstance(threshold, int)
            or threshold < 0
            or not isinstance(approver_role, str)
            or not approver_role.strip()
            or not isinstance(executor_role, str)
            or not executor_role.strip()
            or approver_role.strip().casefold() == executor_role.strip().casefold()
        ):
            return False
    return True


async def require_current_billing_launch_gates(
    db: AsyncSession,
    *,
    environment: str,
    shop_id: str,
    deployment_sha: str | None,
    now: datetime | None = None,
) -> None:
    """Require one current, approved, four-eyes row for every mandatory gate."""
    sha = (deployment_sha or "").strip().lower()
    if len(sha) != 40 or any(char not in "0123456789abcdef" for char in sha):
        raise BillingLaunchBlocked("billing deployment identity is unavailable")
    current = (now or datetime.now(UTC)).astimezone(UTC)
    rows = list(
        await db.scalars(
            select(BillingLaunchGate).where(
                BillingLaunchGate.environment == environment,
                BillingLaunchGate.shop_id_hash == shop_id_hash(shop_id),
                BillingLaunchGate.deployment_sha == sha,
                BillingLaunchGate.gate_key.in_(MANDATORY_BILLING_LAUNCH_GATES),
            )
        )
    )
    current_by_key: dict[str, BillingLaunchGate] = {}
    for row in rows:
        previous = current_by_key.get(row.gate_key)
        if previous is None or row.version > previous.version:
            current_by_key[row.gate_key] = row
    if set(current_by_key) != MANDATORY_BILLING_LAUNCH_GATES:
        raise BillingLaunchBlocked("billing launch approvals are incomplete")
    for row in current_by_key.values():
        if (
            row.status != "approved"
            or row.approved_at > current
            or row.valid_until <= current
            or row.revoked_at is not None
            or not row.approver_ref.strip()
            or not row.executor_ref.strip()
            or row.approver_ref.strip().casefold() == row.executor_ref.strip().casefold()
            or not row.evidence_ref.strip()
            or not row.owner_role.strip()
            or not _has_four_eyes_values(row.values_json)
        ):
            raise BillingLaunchBlocked("billing launch approval is invalid")
