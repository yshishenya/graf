from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from twobrain_rec_server.config import Settings

try:
    from temporalio import workflow
except Exception:  # pragma: no cover - narrow unit-test/import fallback
    workflow = None


BILLING_RECONCILIATION_ACTIVITY_NAME = "run_billing_reconciliation_activity"
BILLING_RECONCILIATION_WORKFLOW_ID_PATTERN = re.compile(
    r"^billing-reconciliation/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/v1$"
)


@dataclass(frozen=True, slots=True)
class BillingReconciliationWorkflowStart:
    workflow_id: str
    run_id: str | None = None
    reused: bool = False


def billing_reconciliation_task_queue(settings: Settings) -> str:
    return f"{settings.temporal_task_queue}-billing-reconciliation"


def billing_reconciliation_workflow_id(run_id: UUID) -> str:
    workflow_id = f"billing-reconciliation/{run_id}/v1"
    if not BILLING_RECONCILIATION_WORKFLOW_ID_PATTERN.fullmatch(workflow_id):
        raise ValueError("billing reconciliation workflow id is invalid")
    return workflow_id


def validate_billing_reconciliation_payload(payload: dict[str, str]) -> dict[str, str]:
    if set(payload) != {"run_id"}:
        raise ValueError("billing reconciliation payload contains unsupported fields")
    try:
        run_id = UUID(payload["run_id"])
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("billing reconciliation run id is invalid") from exc
    return {"run_id": str(run_id)}


def billing_reconciliation_retry_policy():
    from temporalio.common import RetryPolicy

    return RetryPolicy(
        initial_interval=timedelta(minutes=1),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(minutes=15),
        maximum_attempts=12,
        non_retryable_error_types=["BillingReconciliationInvalidPayload"],
    )


def _started_workflow_run_id(handle: object) -> str | None:
    if isinstance(handle, dict):
        value = handle.get("result_run_id") or handle.get("run_id")
    else:
        value = getattr(handle, "result_run_id", None) or getattr(handle, "run_id", None)
    return value if isinstance(value, str) and value else None


async def start_billing_reconciliation_workflow(
    *,
    temporal_client: object,
    settings: Settings,
    run_id: UUID,
) -> BillingReconciliationWorkflowStart:
    from temporalio.common import WorkflowIDReusePolicy
    from temporalio.exceptions import WorkflowAlreadyStartedError

    workflow_id = billing_reconciliation_workflow_id(run_id)
    payload = validate_billing_reconciliation_payload({"run_id": str(run_id)})
    try:
        handle = await temporal_client.start_workflow(
            BillingReconciliationWorkflow.run,
            payload,
            id=workflow_id,
            task_queue=billing_reconciliation_task_queue(settings),
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
        )
    except WorkflowAlreadyStartedError:
        return BillingReconciliationWorkflowStart(workflow_id=workflow_id, reused=True)
    return BillingReconciliationWorkflowStart(
        workflow_id=workflow_id,
        run_id=_started_workflow_run_id(handle),
    )


if workflow is not None:

    @workflow.defn
    class BillingReconciliationWorkflow:
        @workflow.run
        async def run(self, payload: dict[str, str]) -> dict[str, int | str]:
            safe_payload = validate_billing_reconciliation_payload(payload)
            return await workflow.execute_activity(
                BILLING_RECONCILIATION_ACTIVITY_NAME,
                safe_payload,
                start_to_close_timeout=timedelta(minutes=5),
                schedule_to_close_timeout=timedelta(hours=3),
                retry_policy=billing_reconciliation_retry_policy(),
            )

else:

    class BillingReconciliationWorkflow:
        async def run(self, payload: dict[str, str]) -> dict[str, str]:
            return validate_billing_reconciliation_payload(payload)
