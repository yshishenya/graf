from uuid import UUID

import pytest
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from twobrain_rec_server.config import Settings
from twobrain_rec_server.workflows.billing_reconciliation_workflow import (
    BillingReconciliationWorkflow,
    billing_reconciliation_retry_policy,
    billing_reconciliation_task_queue,
    billing_reconciliation_workflow_id,
    start_billing_reconciliation_workflow,
    validate_billing_reconciliation_payload,
)


def test_reconciliation_workflow_payload_is_bounded_and_versioned() -> None:
    run_id = UUID("11111111-1111-4111-8111-111111111111")
    assert billing_reconciliation_workflow_id(run_id).endswith("/v1")
    assert validate_billing_reconciliation_payload({"run_id": str(run_id)}) == {
        "run_id": str(run_id)
    }
    with pytest.raises(ValueError):
        validate_billing_reconciliation_payload({"run_id": str(run_id), "workspace_id": str(run_id)})


def test_reconciliation_workflow_is_bounded_and_uses_a_dedicated_queue() -> None:
    settings = Settings(temporal_task_queue="graf-processing")
    assert billing_reconciliation_task_queue(settings) == "graf-processing-billing-reconciliation"
    policy = billing_reconciliation_retry_policy()
    assert policy.maximum_attempts == 12
    assert "BillingReconciliationInvalidPayload" in policy.non_retryable_error_types


@pytest.mark.anyio
async def test_reconciliation_workflow_start_is_idempotent() -> None:
    run_id = UUID("11111111-1111-4111-8111-111111111111")

    class TemporalClient:
        kwargs: dict[str, object] | None = None

        async def start_workflow(self, workflow, payload, **kwargs):
            self.kwargs = {"workflow": workflow, "payload": payload, **kwargs}
            return {"result_run_id": "run-1"}

    client = TemporalClient()
    settings = Settings(temporal_task_queue="graf-processing")
    started = await start_billing_reconciliation_workflow(
        temporal_client=client,
        settings=settings,
        run_id=run_id,
    )
    assert started.run_id == "run-1"
    assert client.kwargs == {
        "workflow": BillingReconciliationWorkflow.run,
        "payload": {"run_id": str(run_id)},
        "id": billing_reconciliation_workflow_id(run_id),
        "task_queue": billing_reconciliation_task_queue(settings),
        "id_reuse_policy": WorkflowIDReusePolicy.ALLOW_DUPLICATE,
    }


@pytest.mark.anyio
async def test_reconciliation_workflow_running_instance_is_reused() -> None:
    run_id = UUID("11111111-1111-4111-8111-111111111111")

    class TemporalClient:
        async def start_workflow(self, *_args, **_kwargs):
            raise WorkflowAlreadyStartedError(
                billing_reconciliation_workflow_id(run_id),
                "BillingReconciliationWorkflow",
            )

    started = await start_billing_reconciliation_workflow(
        temporal_client=TemporalClient(),
        settings=Settings(),
        run_id=run_id,
    )
    assert started.reused is True
