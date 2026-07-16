from __future__ import annotations

import asyncio
import json
from datetime import timedelta

from temporalio.api.enums.v1 import TaskQueueType
from temporalio.api.taskqueue.v1 import TaskQueue
from temporalio.api.workflowservice.v1 import DescribeTaskQueueRequest

from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.workflows.temporal_client import (
    connect_temporal_client,
    processing_worker_identity,
)


async def _poller_identities(
    *,
    temporal_client: object,
    settings: Settings,
    task_queue_type: int,
) -> set[str]:
    response = await temporal_client.workflow_service.describe_task_queue(
        DescribeTaskQueueRequest(
            namespace=settings.temporal_namespace,
            task_queue=TaskQueue(name=settings.temporal_task_queue),
            task_queue_type=task_queue_type,
            report_pollers=True,
        ),
        timeout=timedelta(seconds=5),
    )
    return {poller.identity for poller in response.pollers if poller.identity}


async def verify_processing_worker_pollers(
    *,
    temporal_client: object,
    settings: Settings,
    expected_worker_identity: str,
) -> None:
    for task_queue_type in (
        TaskQueueType.TASK_QUEUE_TYPE_WORKFLOW,
        TaskQueueType.TASK_QUEUE_TYPE_ACTIVITY,
    ):
        identities = await _poller_identities(
            temporal_client=temporal_client,
            settings=settings,
            task_queue_type=task_queue_type,
        )
        if expected_worker_identity not in identities:
            raise RuntimeError("processing worker poller is not ready")


async def verify_processing_worker_readiness() -> dict[str, str]:
    settings = get_settings()
    expected_worker_identity = processing_worker_identity()
    temporal_client = await connect_temporal_client(
        settings,
        identity=f"{expected_worker_identity}:readiness-probe",
    )
    await verify_processing_worker_pollers(
        temporal_client=temporal_client,
        settings=settings,
        expected_worker_identity=expected_worker_identity,
    )
    return {
        "result": "pass",
        "workflow_poller": "ready",
        "activity_poller": "ready",
        "worker_identity": expected_worker_identity,
    }


def main() -> int:
    try:
        receipt = asyncio.run(verify_processing_worker_readiness())
    except Exception as exc:
        print(
            json.dumps(
                {"result": "blocked", "reason": type(exc).__name__},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
