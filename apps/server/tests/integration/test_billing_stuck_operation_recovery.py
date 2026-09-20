"""PostgreSQL proof that a lost create-payment response cannot block payment forever.

The unit suite owns the counter contract against a fake session; the SQL
conditions that decide which operation is abandoned are proven here against a
real database. ``_blocking_payment_operation_query`` is the exact query the
checkout route runs before it allows another money mutation, so an empty result
is what lets a person start a new payment.

Scenario under test: the provider created a payment but the response never
reached the server, so ``provider_id`` was never stored and no confirmation link
was ever shown. The operation stays in a blocking state and the person can
neither finish the payment nor start a new one.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select

from tests.fakes.auth_contexts import ORG_ID
from twobrain_rec_server.billing.maintenance import (
    STUCK_OPERATION_MAX_AGE,
    reconcile_billing_maintenance,
)
from twobrain_rec_server.billing.operations import CHECKOUT_BLOCKING_STATES
from twobrain_rec_server.cabinet.web_routes.billing import (
    _blocking_payment_operation_query,
    _initial_checkout_can_continue,
)
from twobrain_rec_server.db.models import (
    BillingAuditEvent,
    BillingInvoice,
    BillingOperation,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    TenantDatabaseContext,
    apply_tenant_context,
)

CHECKOUT_AMOUNT_MINOR = 79_000
PROVIDER_KEY_WINDOW = timedelta(hours=24)
ABANDONED_AUDIT_ACTION = "billing.abandoned_operation_canceled"
STUCK_AUDIT_ACTION = "billing.maintenance_stuck_operation"


def _maintenance_context() -> MaintenanceTenantContext:
    """Return the context the billing reconciliation worker runs under."""
    return MaintenanceTenantContext(
        operation_name="billing_reconciliation",
        actor_id="integration-stuck-operation-recovery",
        reason_category="billing_maintenance",
        feature_area="billing",
    )


def _request_context(workspace_id: UUID, user_id: UUID) -> TenantDatabaseContext:
    """Return the workspace-scoped context a cabinet request runs under."""
    return TenantDatabaseContext(
        organization_id=ORG_ID,
        workspace_id=workspace_id,
        user_id=user_id,
        context_kind="request",
    )


async def _seed_workspace(db) -> tuple[UUID, UUID]:
    """Create one isolated personal workspace so tests never share identifiers."""
    suffix = uuid4().hex
    user_id = uuid4()
    workspace_id = uuid4()
    db.add(
        UserIdentity(
            id=user_id,
            organization_id=ORG_ID,
            external_subject=f"stuck-operation-{suffix}",
            display_name="Stuck Operation Owner",
        )
    )
    db.add(
        Workspace(
            id=workspace_id,
            organization_id=ORG_ID,
            slug=f"stuck-operation-{suffix}",
            name="Stuck Operation Workspace",
            kind="personal",
            owner_user_id=user_id,
        )
    )
    await db.flush()
    db.add(
        WorkspaceMembership(
            workspace_id=workspace_id,
            user_id=user_id,
            role="owner",
            status="active",
        )
    )
    db.add(WorkspaceSubscription(workspace_id=workspace_id, state="free", plan_code="free"))
    await db.flush()
    return workspace_id, user_id


async def _seed_initial_checkout(
    db,
    *,
    workspace_id: UUID,
    state: str,
    provider_id: str | None,
    key_expires_at: datetime,
    created_at: datetime,
    updated_at: datetime,
    invoice_status: str = "pending",
    kind: str = "initial_checkout",
) -> tuple[UUID, UUID]:
    """Persist one billing operation together with its invoice."""
    suffix = uuid4().hex
    operation_id = uuid4()
    invoice_id = uuid4()
    db.add(
        BillingOperation(
            id=operation_id,
            workspace_id=workspace_id,
            kind=kind,
            idempotency_key=f"stuck-operation-{suffix}",
            provider_id=provider_id,
            state=state,
            provider_key_expires_at=key_expires_at,
            request_snapshot={
                "plan_code": "personal",
                "cycle": "year",
                "offer_consent": True,
                "recurring_consent": True,
                "payable_amount_minor": CHECKOUT_AMOUNT_MINOR,
            },
            created_at=created_at,
            updated_at=updated_at,
        )
    )
    await db.flush()
    db.add(
        BillingInvoice(
            id=invoice_id,
            workspace_id=workspace_id,
            operation_id=operation_id,
            safe_number=f"INV-STUCK{suffix[:16].upper()}",
            amount_minor=CHECKOUT_AMOUNT_MINOR,
            currency="RUB",
            status=invoice_status,
            plan_snapshot={},
        )
    )
    await db.flush()
    return operation_id, invoice_id


async def _blocking_operation_ids(db, workspace_id: UUID) -> list[UUID]:
    """Run the production blocking query exactly as the checkout route does."""
    rows = await db.scalars(_blocking_payment_operation_query(workspace_id))
    return [operation.id for operation in rows]


async def _operation_state(db, operation_id: UUID) -> str:
    state = await db.scalar(select(BillingOperation.state).where(BillingOperation.id == operation_id))
    assert state is not None, "seeded operation disappeared instead of being classified"
    return state


async def _audit_actions(db, workspace_id: UUID) -> list[str]:
    rows = await db.scalars(
        select(BillingAuditEvent.action).where(BillingAuditEvent.workspace_id == workspace_id)
    )
    return list(rows)


async def _run_maintenance(sessionmaker, *, now: datetime) -> dict[str, int]:
    """Run one real maintenance pass and commit it like the worker activity does."""
    async with sessionmaker() as db:
        await apply_tenant_context(db, _maintenance_context())
        counters = await reconcile_billing_maintenance(db, now=now)
        await db.commit()
    return counters


def test_expired_key_without_provider_id_is_canceled_and_stops_blocking(client) -> None:
    """A payment we never got an id for, past its key window, must stop blocking."""
    now = datetime.now(UTC).replace(microsecond=0)

    async def exercise() -> dict[str, object]:
        sessionmaker = client.app_state["sessionmaker"]
        async with sessionmaker() as db:
            await apply_tenant_context(db, _maintenance_context())
            workspace_id, user_id = await _seed_workspace(db)
            operation_id, invoice_id = await _seed_initial_checkout(
                db,
                workspace_id=workspace_id,
                state="scheduled",
                provider_id=None,
                # The real timeline: created 25 hours ago, key window already over.
                created_at=now - timedelta(hours=25),
                updated_at=now - timedelta(hours=25),
                key_expires_at=now - timedelta(hours=1),
            )
            await db.commit()

        # Precondition: the reported scenario reproduces - the person is blocked
        # and has no confirmation link to finish the lost payment.
        async with sessionmaker() as db:
            await apply_tenant_context(db, _request_context(workspace_id, user_id))
            blocked_before = await _blocking_operation_ids(db, workspace_id)
            snapshot = dict(
                await db.scalar(
                    select(BillingOperation.request_snapshot).where(
                        BillingOperation.id == operation_id
                    )
                )
                or {}
            )

        counters = await _run_maintenance(sessionmaker, now=now)

        async with sessionmaker() as db:
            await apply_tenant_context(db, _request_context(workspace_id, user_id))
            state = await _operation_state(db, operation_id)
            invoice_status = await db.scalar(
                select(BillingInvoice.status).where(BillingInvoice.id == invoice_id)
            )
            blocking_after = await _blocking_operation_ids(db, workspace_id)
            audit_actions = await _audit_actions(db, workspace_id)

        return {
            "operation_id": operation_id,
            "blocked_before": blocked_before,
            "snapshot": snapshot,
            "counters": counters,
            "state": state,
            "invoice_status": invoice_status,
            "blocking_after": blocking_after,
            "audit_actions": audit_actions,
        }

    evidence = asyncio.run(exercise())

    assert "scheduled" in CHECKOUT_BLOCKING_STATES
    assert evidence["blocked_before"] == [evidence["operation_id"]]
    assert "confirmation_url" not in evidence["snapshot"]
    assert evidence["state"] == "canceled"
    assert evidence["invoice_status"] == "canceled"
    assert evidence["blocking_after"] == []
    assert ABANDONED_AUDIT_ACTION in evidence["audit_actions"]
    assert evidence["counters"]["abandoned_operations"] == 1
    assert evidence["counters"]["stuck_operations"] == 0


def test_live_key_without_provider_id_is_not_canceled_and_keeps_blocking(client) -> None:
    """A payment the person can still finish must not be canceled underneath them.

    This is a preservation guard: it must hold for any maintenance pass, so it
    asserts the outcome rather than the new abandoned-operations counter.
    """
    now = datetime.now(UTC).replace(microsecond=0)

    async def exercise() -> dict[str, object]:
        sessionmaker = client.app_state["sessionmaker"]
        async with sessionmaker() as db:
            await apply_tenant_context(db, _maintenance_context())
            workspace_id, user_id = await _seed_workspace(db)
            operation_id, invoice_id = await _seed_initial_checkout(
                db,
                workspace_id=workspace_id,
                state="scheduled",
                provider_id=None,
                # A checkout started one minute ago: the key window has just opened.
                created_at=now - timedelta(minutes=1),
                updated_at=now - timedelta(minutes=1),
                key_expires_at=now + PROVIDER_KEY_WINDOW - timedelta(minutes=1),
            )
            await db.commit()

        counters = await _run_maintenance(sessionmaker, now=now)

        async with sessionmaker() as db:
            await apply_tenant_context(db, _request_context(workspace_id, user_id))
            operation = await db.scalar(
                select(BillingOperation).where(BillingOperation.id == operation_id)
            )
            assert operation is not None
            state = operation.state
            can_continue = _initial_checkout_can_continue(operation, now=now)
            invoice_status = await db.scalar(
                select(BillingInvoice.status).where(BillingInvoice.id == invoice_id)
            )
            blocking_after = await _blocking_operation_ids(db, workspace_id)

        return {
            "counters": counters,
            "state": state,
            "can_continue": can_continue,
            "invoice_status": invoice_status,
            "blocking_after": blocking_after,
        }

    evidence = asyncio.run(exercise())

    assert evidence["state"] == "scheduled"
    assert evidence["invoice_status"] == "pending"
    # Still blocking is correct here: the person can finish this very payment, so
    # a second one must wait instead of charging twice.
    assert len(evidence["blocking_after"]) == 1
    assert evidence["can_continue"] is True
    assert evidence["counters"]["stuck_operations"] == 0


def test_stale_operation_with_provider_id_is_still_marked_unknown(client) -> None:
    """The 30-minute stale classification keeps working for operations we can poll.

    This is a preservation guard for the behaviour that existed before the
    abandoned-operations pass, including its refusal to cancel such a payment.
    """
    now = datetime.now(UTC).replace(microsecond=0)

    async def exercise() -> dict[str, object]:
        sessionmaker = client.app_state["sessionmaker"]
        async with sessionmaker() as db:
            await apply_tenant_context(db, _maintenance_context())
            workspace_id, user_id = await _seed_workspace(db)
            operation_id, invoice_id = await _seed_initial_checkout(
                db,
                workspace_id=workspace_id,
                state="provider_pending",
                provider_id=f"pay-{uuid4().hex}",
                created_at=now - timedelta(hours=2),
                updated_at=now - timedelta(minutes=45),
                key_expires_at=now + timedelta(hours=22),
            )
            await db.commit()

        counters = await _run_maintenance(sessionmaker, now=now)

        async with sessionmaker() as db:
            await apply_tenant_context(db, _request_context(workspace_id, user_id))
            state = await _operation_state(db, operation_id)
            invoice_status = await db.scalar(
                select(BillingInvoice.status).where(BillingInvoice.id == invoice_id)
            )
            blocking_after = await _blocking_operation_ids(db, workspace_id)
            audit_actions = await _audit_actions(db, workspace_id)

        return {
            "counters": counters,
            "state": state,
            "invoice_status": invoice_status,
            "blocking_after": blocking_after,
            "audit_actions": audit_actions,
        }

    evidence = asyncio.run(exercise())

    # A stored provider id proves the provider created the payment, so the local
    # 30-minute classification must still fire and wait for provider truth. The
    # payment itself stays alive: only its local state becomes unknown.
    assert evidence["state"] == "unknown"
    assert evidence["invoice_status"] == "pending"
    assert len(evidence["blocking_after"]) == 1
    assert STUCK_AUDIT_ACTION in evidence["audit_actions"]
    assert evidence["counters"]["stuck_operations"] == 1


def test_expired_provider_id_operation_becomes_non_blocking_but_remains_reconcilable(client) -> None:
    """Known provider ids may stop blocking after bounded observation, never after a blind cancellation."""
    now = datetime.now(UTC).replace(microsecond=0)

    async def exercise() -> dict[str, object]:
        sessionmaker = client.app_state["sessionmaker"]
        async with sessionmaker() as db:
            await apply_tenant_context(db, _maintenance_context())
            workspace_id, user_id = await _seed_workspace(db)
            operation_id, invoice_id = await _seed_initial_checkout(
                db,
                workspace_id=workspace_id,
                state="unknown",
                provider_id=f"pay-{uuid4().hex}",
                created_at=now - timedelta(hours=30),
                updated_at=now - timedelta(hours=2),
                key_expires_at=now - timedelta(hours=1),
            )
            await db.commit()
        counters = await _run_maintenance(sessionmaker, now=now)
        async with sessionmaker() as db:
            await apply_tenant_context(db, _request_context(workspace_id, user_id))
            operation = await db.scalar(select(BillingOperation).where(BillingOperation.id == operation_id))
            invoice_status = await db.scalar(select(BillingInvoice.status).where(BillingInvoice.id == invoice_id))
            blocking_after = await _blocking_operation_ids(db, workspace_id)
        return {
            "operation": operation,
            "invoice_status": invoice_status,
            "blocking_after": blocking_after,
            "counters": counters,
        }

    evidence = asyncio.run(exercise())
    operation = evidence["operation"]
    assert operation.state == "observation_expired"
    assert operation.provider_id is not None
    assert evidence["invoice_status"] == "unknown"
    assert evidence["blocking_after"] == []
    assert evidence["counters"]["expired_provider_observations"] == 1


def test_stale_operation_without_provider_id_keeps_resumable_state(client) -> None:
    """An old checkout with a live key must not lose its continue-payment state."""
    now = datetime.now(UTC).replace(microsecond=0)

    async def exercise() -> dict[str, object]:
        sessionmaker = client.app_state["sessionmaker"]
        async with sessionmaker() as db:
            await apply_tenant_context(db, _maintenance_context())
            workspace_id, user_id = await _seed_workspace(db)
            operation_id, _invoice_id = await _seed_initial_checkout(
                db,
                workspace_id=workspace_id,
                state="scheduled",
                provider_id=None,
                # Started two hours ago, untouched since: stale, but the key is alive.
                created_at=now - timedelta(hours=2),
                updated_at=now - timedelta(hours=2),
                key_expires_at=now + PROVIDER_KEY_WINDOW - timedelta(hours=2),
            )
            await db.commit()

        counters = await _run_maintenance(sessionmaker, now=now)

        async with sessionmaker() as db:
            await apply_tenant_context(db, _request_context(workspace_id, user_id))
            operation = await db.scalar(
                select(BillingOperation).where(BillingOperation.id == operation_id)
            )
            assert operation is not None
            state = operation.state
            can_continue = _initial_checkout_can_continue(operation, now=now)
            # Supporting check: this row does satisfy the age and state conditions
            # of the stale pass, so the provider-id guard is the only reason it is
            # still resumable instead of classified unknown.
            stale_rows_without_provider_guard = await db.scalar(
                select(func.count())
                .select_from(BillingOperation)
                .where(
                    BillingOperation.workspace_id == workspace_id,
                    BillingOperation.state.in_(("scheduled", "provider_pending")),
                    BillingOperation.kind != "renewal",
                    BillingOperation.updated_at <= now - STUCK_OPERATION_MAX_AGE,
                )
            )

        return {
            "counters": counters,
            "state": state,
            "can_continue": can_continue,
            "stale_rows_without_provider_guard": stale_rows_without_provider_guard,
        }

    evidence = asyncio.run(exercise())

    # Losing this state would remove the "continue payment" action.
    assert evidence["state"] == "scheduled"
    assert evidence["can_continue"] is True
    assert evidence["stale_rows_without_provider_guard"] == 1
    assert evidence["counters"]["stuck_operations"] == 0
