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
except Exception:  # pragma: no cover - import fallback for docs and narrow unit tests
    workflow = None


BILLING_RENEWAL_ACTIVITY_NAME = "run_billing_renewal_activity"
BILLING_RENEWAL_WORKFLOW_ID_PATTERN = re.compile(
    r"^billing-renewal/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/v1$"
)


@dataclass(frozen=True, slots=True)
class BillingRenewalWorkflowStart:
    workflow_id: str
    run_id: str | None = None
    reused: bool = False


def billing_renewal_task_queue(settings: Settings) -> str:
    return f"{settings.temporal_task_queue}-billing-renewal"


def billing_renewal_workflow_id(operation_id: UUID) -> str:
    workflow_id = f"billing-renewal/{operation_id}/v1"
    validate_billing_renewal_workflow_id(workflow_id)
    return workflow_id


def validate_billing_renewal_workflow_id(workflow_id: str) -> None:
    if not BILLING_RENEWAL_WORKFLOW_ID_PATTERN.fullmatch(workflow_id):
        raise ValueError(
            "billing renewal workflow id must contain only the fixed prefix, operation UUID, and version"
        )


def validate_billing_renewal_payload(payload: dict[str, str]) -> dict[str, str]:
    if set(payload) != {"operation_id", "workspace_id"}:
        raise ValueError("billing renewal payload contains unsupported fields")
    try:
        operation_id = UUID(payload["operation_id"])
        workspace_id = UUID(payload["workspace_id"])
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("billing renewal payload identifiers are invalid") from exc
    return {
        "operation_id": str(operation_id),
        "workspace_id": str(workspace_id),
    }


def billing_renewal_retry_policy():
    from temporalio.common import RetryPolicy

    # Every retry is an authoritative GET for the same persisted operation.
    # The activity never creates a new payment or a new provider key.
    return RetryPolicy(
        initial_interval=timedelta(minutes=1),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(minutes=15),
        maximum_attempts=12,
        non_retryable_error_types=[
            "BillingRenewalInvalidPayload",
            "BillingRenewalAuthorityMismatch",
            "BillingRenewalProviderMismatch",
        ],
    )


def _started_workflow_run_id(handle: object) -> str | None:
    if isinstance(handle, dict):
        value = handle.get("result_run_id") or handle.get("run_id")
    else:
        value = getattr(handle, "result_run_id", None) or getattr(handle, "run_id", None)
    return value if isinstance(value, str) and value else None


async def start_billing_renewal_workflow(
    *,
    temporal_client: object,
    settings: Settings,
    operation_id: UUID,
    workspace_id: UUID,
) -> BillingRenewalWorkflowStart:
    from temporalio.common import WorkflowIDReusePolicy
    from temporalio.exceptions import WorkflowAlreadyStartedError

    workflow_id = billing_renewal_workflow_id(operation_id)
    payload = validate_billing_renewal_payload(
        {"operation_id": str(operation_id), "workspace_id": str(workspace_id)}
    )
    try:
        handle = await temporal_client.start_workflow(
            BillingRenewalWorkflow.run,
            payload,
            id=workflow_id,
            task_queue=billing_renewal_task_queue(settings),
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
        )
    except WorkflowAlreadyStartedError:
        return BillingRenewalWorkflowStart(workflow_id=workflow_id, reused=True)
    return BillingRenewalWorkflowStart(
        workflow_id=workflow_id,
        run_id=_started_workflow_run_id(handle),
    )


if workflow is not None:

    @workflow.defn
    class BillingRenewalWorkflow:
        @workflow.run
        async def run(self, payload: dict[str, str]) -> dict[str, str]:
            safe_payload = validate_billing_renewal_payload(payload)
            # ponytail: one activity is enough while renewal recovery is one
            # authoritative provider read plus one atomic database projection.
            return await workflow.execute_activity(
                BILLING_RENEWAL_ACTIVITY_NAME,
                safe_payload,
                start_to_close_timeout=timedelta(minutes=2),
                schedule_to_close_timeout=timedelta(hours=3),
                retry_policy=billing_renewal_retry_policy(),
            )

else:

    class BillingRenewalWorkflow:
        async def run(self, payload: dict[str, str]) -> dict[str, str]:
            return validate_billing_renewal_payload(payload)
