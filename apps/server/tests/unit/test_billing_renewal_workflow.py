from __future__ import annotations

import inspect
from datetime import UTC, datetime
from uuid import UUID

import pytest
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from twobrain_rec_server.billing.entitlements import grant_confirmed_renewal
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingOperation,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)
from twobrain_rec_server.workflows.billing_renewal_workflow import (
    BillingRenewalWorkflow,
    billing_renewal_retry_policy,
    billing_renewal_task_queue,
    billing_renewal_workflow_id,
    start_billing_renewal_workflow,
    validate_billing_renewal_payload,
)
from twobrain_rec_server.workflows.worker import (
    _validate_authoritative_renewal_payment,
    run_billing_renewal_activity,
    run_billing_renewal_reconciler,
)

OPERATION_ID = UUID("11111111-1111-4111-8111-111111111111")
WORKSPACE_ID = UUID("22222222-2222-4222-8222-222222222222")
OWNER_ID = UUID("33333333-3333-4333-8333-333333333333")
ORGANIZATION_ID = UUID("44444444-4444-4444-8444-444444444444")


def _personal_workspace(*, kind: str = "personal") -> Workspace:
    return Workspace(
        id=WORKSPACE_ID,
        organization_id=ORGANIZATION_ID,
        slug="personal-owner",
        name="Моё пространство",
        kind=kind,
        owner_user_id=OWNER_ID,
    )


def _active_owner() -> WorkspaceMembership:
    return WorkspaceMembership(
        workspace_id=WORKSPACE_ID,
        user_id=OWNER_ID,
        role="owner",
        status="active",
    )


@pytest.mark.anyio
async def test_confirmed_renewal_extends_paid_through_once() -> None:
    class FakeDb:
        def __init__(self, values):
            self.values = iter(values)
            self.added = []

        async def scalar(self, _query):
            return next(self.values)

        def add(self, value):
            self.added.append(value)

        async def flush(self):
            return None

    operation = BillingOperation(
        id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        kind="renewal",
        idempotency_key="renewal-1",
        provider_id="pay-renewal-1",
        request_snapshot={
            "plan_code": "personal",
            "cycle": "month",
            "billing_actor_user_id": str(OWNER_ID),
        },
    )
    invoice = BillingInvoice(
        workspace_id=WORKSPACE_ID,
        operation_id=OPERATION_ID,
        safe_number="INV-RENEWAL-1",
        amount_minor=79_000,
        currency="RUB",
    )
    subscription = WorkspaceSubscription(
        workspace_id=WORKSPACE_ID,
        billing_owner_id=OWNER_ID,
        state="free",
        plan_code="free",
        paid_through=datetime(2026, 8, 1, tzinfo=UTC),
        recurring_allowed=True,
        recurring_authority_version=0,
    )
    operation.request_snapshot["recurring_authority_version"] = 0
    db = FakeDb([_personal_workspace(), subscription, operation, invoice, None, _active_owner()])

    result = await grant_confirmed_renewal(
        db,
        workspace_id=WORKSPACE_ID,
        provider_payment_id="pay-renewal-1",
        amount_minor=79_000,
        currency="RUB",
        grant_starts_at=datetime(2026, 8, 7, tzinfo=UTC),
    )

    assert result == "granted"
    assert subscription.plan_code == "personal"
    assert subscription.paid_through == datetime(2026, 9, 7, tzinfo=UTC)
    assert any(getattr(row, "source", None) == "renewal_provider_confirmed" for row in db.added)


@pytest.mark.anyio
async def test_late_success_after_provider_key_expiry_restores_access_without_refusal() -> None:
    class FakeDb:
        def __init__(self, values):
            self.values = iter(values)
            self.added = []

        async def scalar(self, _query):
            return next(self.values)

        def add(self, value):
            self.added.append(value)

        async def flush(self):
            return None

    operation = BillingOperation(
        id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        kind="renewal",
        idempotency_key="renewal-expired",
        provider_id="pay-expired",
        state="provider_key_expired",
        request_snapshot={
            "plan_code": "personal",
            "cycle": "month",
            "billing_actor_user_id": str(OWNER_ID),
            "recurring_authority_version": 4,
        },
    )
    invoice = BillingInvoice(
        workspace_id=WORKSPACE_ID,
        operation_id=OPERATION_ID,
        safe_number="INV-RENEWAL-EXPIRED",
        amount_minor=79_000,
        currency="RUB",
    )
    subscription = WorkspaceSubscription(
        workspace_id=WORKSPACE_ID,
        billing_owner_id=OWNER_ID,
        recurring_allowed=True,
        recurring_authority_version=4,
    )
    db = FakeDb([_personal_workspace(), subscription, operation, invoice, None, _active_owner()])

    result = await grant_confirmed_renewal(
        db,
        workspace_id=WORKSPACE_ID,
        provider_payment_id="pay-expired",
        amount_minor=79_000,
        currency="RUB",
        grant_starts_at=datetime(2026, 8, 7, tzinfo=UTC),
    )

    assert result == "granted"
    assert operation.state == "succeeded"
    assert invoice.status == "succeeded"
    assert subscription.plan_code == "personal"
    assert subscription.recurring_allowed is True
    assert subscription.recurring_authority_version == 4


@pytest.mark.anyio
async def test_late_success_after_refusal_is_recorded_and_notified_once() -> None:
    class FakeDb:
        def __init__(self, values):
            self.values = iter(values)
            self.added = []

        async def scalar(self, _query):
            return next(self.values)

        def add(self, value):
            self.added.append(value)

        async def flush(self):
            return None

    operation = BillingOperation(
        id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        kind="renewal",
        idempotency_key="renewal-refused",
        provider_id="pay-refused",
        state="provider_key_expired",
        request_snapshot={
            "plan_code": "personal",
            "cycle": "month",
            "billing_actor_user_id": str(OWNER_ID),
            "recurring_authority_version": 4,
        },
    )
    invoice = BillingInvoice(
        workspace_id=WORKSPACE_ID,
        operation_id=OPERATION_ID,
        safe_number="INV-RENEWAL-REFUSED",
        amount_minor=79_000,
        currency="RUB",
    )
    subscription = WorkspaceSubscription(
        workspace_id=WORKSPACE_ID,
        billing_owner_id=OWNER_ID,
        state="free",
        plan_code="free",
        recurring_allowed=False,
        recurring_authority_version=5,
    )
    db = FakeDb(
        [_personal_workspace(), subscription, operation, invoice, None, _active_owner(), None,
         _personal_workspace(), subscription, operation, invoice]
    )

    first = await grant_confirmed_renewal(
        db,
        workspace_id=WORKSPACE_ID,
        provider_payment_id="pay-refused",
        amount_minor=79_000,
        currency="RUB",
        grant_starts_at=datetime(2026, 8, 7, tzinfo=UTC),
    )
    duplicate = await grant_confirmed_renewal(
        db,
        workspace_id=WORKSPACE_ID,
        provider_payment_id="pay-refused",
        amount_minor=79_000,
        currency="RUB",
        grant_starts_at=datetime(2026, 8, 7, tzinfo=UTC),
    )

    assert first == "refused"
    assert duplicate == "duplicate"
    assert operation.state == "succeeded_refused"
    assert subscription.plan_code == "free"
    assert sum(getattr(row, "action", None) == "renewal_success_refused" for row in db.added) == 1
    deliveries = [
        row
        for row in db.added
        if getattr(row, "template_key", None) == "renewal_late_success_refused"
    ]
    assert len(deliveries) == 1
    assert deliveries[0].safe_payload == {
        "invoice": "INV-RENEWAL-REFUSED",
        "action_path": "/billing/history",
    }


@pytest.mark.anyio
async def test_confirmed_renewal_is_refused_without_active_personal_owner() -> None:
    class FakeDb:
        def __init__(self, values):
            self.values = iter(values)
            self.added = []

        async def scalar(self, _query):
            return next(self.values)

        def add(self, value):
            self.added.append(value)

        async def flush(self):
            return None

    operation = BillingOperation(
        id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        kind="renewal",
        idempotency_key="renewal-invalid-owner",
        provider_id="pay-invalid-owner",
        request_snapshot={
            "plan_code": "personal",
            "cycle": "month",
            "billing_actor_user_id": str(OWNER_ID),
            "recurring_authority_version": 4,
        },
    )
    invoice = BillingInvoice(
        workspace_id=WORKSPACE_ID,
        operation_id=OPERATION_ID,
        safe_number="INV-RENEWAL-INVALID",
        amount_minor=79_000,
        currency="RUB",
    )
    subscription = WorkspaceSubscription(
        workspace_id=WORKSPACE_ID,
        billing_owner_id=OWNER_ID,
        recurring_allowed=True,
        recurring_authority_version=4,
    )
    db = FakeDb(
        [_personal_workspace(kind="corporate"), subscription, operation, invoice, None, None]
    )

    result = await grant_confirmed_renewal(
        db,
        workspace_id=WORKSPACE_ID,
        provider_payment_id="pay-invalid-owner",
        amount_minor=79_000,
        currency="RUB",
        grant_starts_at=datetime(2026, 8, 7, tzinfo=UTC),
    )

    assert result == "refused"
    assert operation.state == "succeeded_refused"
    assert invoice.status == "succeeded"
    assert subscription.plan_code != "personal"
    assert subscription.recurring_allowed is False
    assert subscription.renewal_resolution == "workspace_scope_invalid"
    assert not any(getattr(row, "source", None) == "renewal_provider_confirmed" for row in db.added)


def test_renewal_identity_and_payload_are_bounded() -> None:
    assert billing_renewal_workflow_id(OPERATION_ID) == (
        "billing-renewal/11111111-1111-4111-8111-111111111111/v1"
    )
    assert validate_billing_renewal_payload(
        {"operation_id": str(OPERATION_ID), "workspace_id": str(WORKSPACE_ID)}
    ) == {"operation_id": str(OPERATION_ID), "workspace_id": str(WORKSPACE_ID)}

    with pytest.raises(ValueError, match="unsupported fields"):
        validate_billing_renewal_payload(
            {
                "operation_id": str(OPERATION_ID),
                "workspace_id": str(WORKSPACE_ID),
                "provider_payload": "not-allowed",
            }
        )


def test_renewal_retry_repeats_only_authoritative_observation() -> None:
    policy = billing_renewal_retry_policy()

    assert policy.maximum_attempts == 12
    assert "BillingRenewalProviderMismatch" in policy.non_retryable_error_types
    source = inspect.getsource(run_billing_renewal_activity)
    assert ".get_payment(" in source
    assert "grant_confirmed_renewal" in source
    assert "if not _renewal_authority_matches" not in source
    assert ".create_payment(" not in source
    assert ".create_refund(" not in source

    scheduler_source = inspect.getsource(run_billing_renewal_reconciler)
    assert 'Workspace.kind == "personal"' in scheduler_source
    assert 'WorkspaceMembership.role == "owner"' in scheduler_source
    assert 'WorkspaceMembership.status == "active"' in scheduler_source
    assert source.index('WorkspaceMembership.status == "active"') < source.index(".get_payment(")

    webhook_source = inspect.getsource(
        __import__(
            "twobrain_rec_server.billing.webhook_reconciliation",
            fromlist=["_reconcile_event"],
        )._reconcile_event
    )
    assert 'operation.state == "provider_key_expired"' in webhook_source
    assert "else observation.provider_created_at" in webhook_source


@pytest.mark.anyio
async def test_start_renewal_uses_separate_queue_and_stable_operation_id() -> None:
    class TemporalClient:
        kwargs: dict[str, object] | None = None

        async def start_workflow(self, workflow, payload, **kwargs):
            self.kwargs = {"workflow": workflow, "payload": payload, **kwargs}
            return {"result_run_id": "run-1"}

    client = TemporalClient()
    settings = Settings(temporal_task_queue="graf-processing")

    started = await start_billing_renewal_workflow(
        temporal_client=client,
        settings=settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
    )

    assert started.run_id == "run-1"
    assert started.reused is False
    assert client.kwargs == {
        "workflow": BillingRenewalWorkflow.run,
        "payload": {
            "operation_id": str(OPERATION_ID),
            "workspace_id": str(WORKSPACE_ID),
        },
        "id": billing_renewal_workflow_id(OPERATION_ID),
        "task_queue": billing_renewal_task_queue(settings),
        "id_reuse_policy": WorkflowIDReusePolicy.ALLOW_DUPLICATE,
    }


@pytest.mark.anyio
async def test_active_renewal_workflow_is_reused() -> None:
    class TemporalClient:
        async def start_workflow(self, *_args, **_kwargs):
            raise WorkflowAlreadyStartedError(
                billing_renewal_workflow_id(OPERATION_ID),
                "BillingRenewalWorkflow",
            )

    started = await start_billing_renewal_workflow(
        temporal_client=TemporalClient(),
        settings=Settings(),
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
    )

    assert started.reused is True
    assert started.workflow_id == billing_renewal_workflow_id(OPERATION_ID)


def test_authoritative_payment_requires_exact_operation_amount() -> None:
    operation = BillingOperation(
        id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        kind="renewal",
        idempotency_key="renewal-period-1",
        provider_id="payment-1",
        request_snapshot={"recurring_authority_version": 4},
    )
    invoice = BillingInvoice(
        id=UUID("33333333-3333-4333-8333-333333333333"),
        workspace_id=WORKSPACE_ID,
        operation_id=OPERATION_ID,
        safe_number="INV-RENEWAL-1",
        amount_minor=99900,
        currency="RUB",
    )
    payment = {
        "id": "payment-1",
        "status": "succeeded",
        "amount": {"value": "999.00", "currency": "RUB"},
        "metadata": {
            "workspace_id": str(WORKSPACE_ID),
            "operation_id": str(OPERATION_ID),
        },
    }

    assert (
        _validate_authoritative_renewal_payment(
            payment,
            operation=operation,
            invoice=invoice,
        )
        == "succeeded"
    )
    with pytest.raises(ValueError, match="amount does not match"):
        _validate_authoritative_renewal_payment(
            {**payment, "amount": {"value": "998.00", "currency": "RUB"}},
            operation=operation,
            invoice=invoice,
        )
