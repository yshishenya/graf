from __future__ import annotations

import inspect
from uuid import UUID

import pytest
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingOperation,
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
    _renewal_authority_matches,
    _validate_authoritative_renewal_payment,
    run_billing_renewal_activity,
)

OPERATION_ID = UUID("11111111-1111-4111-8111-111111111111")
WORKSPACE_ID = UUID("22222222-2222-4222-8222-222222222222")


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
    assert ".create_payment(" not in source
    assert ".create_refund(" not in source


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


def test_authoritative_payment_requires_exact_operation_amount_and_authority() -> None:
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
    subscription = WorkspaceSubscription(
        workspace_id=WORKSPACE_ID,
        recurring_allowed=True,
        recurring_authority_version=4,
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
    assert _renewal_authority_matches(operation, subscription)

    subscription.recurring_authority_version = 5
    assert not _renewal_authority_matches(operation, subscription)
    with pytest.raises(ValueError, match="amount does not match"):
        _validate_authoritative_renewal_payment(
            {**payment, "amount": {"value": "998.00", "currency": "RUB"}},
            operation=operation,
            invoice=invoice,
        )
