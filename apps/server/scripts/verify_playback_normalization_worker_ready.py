from __future__ import annotations

import argparse
import asyncio
import json
from datetime import timedelta
from uuid import uuid4

from temporalio.api.enums.v1 import TaskQueueType
from temporalio.api.taskqueue.v1 import TaskQueue
from temporalio.api.workflowservice.v1 import DescribeTaskQueueRequest

from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.normalization.statuses import (
    CANONICAL_PROFILE_VERSION,
    VALIDATION_VERSION,
)
from twobrain_rec_server.normalization.worker_readiness import (
    WORKER_READINESS_SCHEMA_VERSION,
    PlaybackNormalizationReadinessWorkflow,
    playback_normalization_readiness_task_queue,
    playback_normalization_worker_identity,
    require_worker_readiness_marker,
)
from twobrain_rec_server.workflows.temporal_client import connect_temporal_client


async def _poller_identities(
    *,
    temporal_client: object,
    settings: Settings,
    task_queue_type: int,
) -> set[str]:
    response = await temporal_client.workflow_service.describe_task_queue(
        DescribeTaskQueueRequest(
            namespace=settings.temporal_namespace,
            task_queue=TaskQueue(name=settings.playback_normalization_task_queue),
            task_queue_type=task_queue_type,
            report_pollers=True,
        ),
        timeout=timedelta(seconds=5),
    )
    return {poller.identity for poller in response.pollers if poller.identity}


async def verify_worker_pollers(
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
            raise RuntimeError("playback normalization worker poller is not ready")


async def run_control_probe(
    *,
    temporal_client: object,
    settings: Settings,
    expected_worker_identity: str,
) -> dict[str, str]:
    probe_id = str(uuid4())
    result = await asyncio.wait_for(
        temporal_client.execute_workflow(
            PlaybackNormalizationReadinessWorkflow.run,
            {"probe_id": probe_id},
            id=f"playback-normalization-readiness/{probe_id}",
            task_queue=playback_normalization_readiness_task_queue(
                settings.playback_normalization_task_queue
            ),
            execution_timeout=timedelta(seconds=20),
            run_timeout=timedelta(seconds=20),
            task_timeout=timedelta(seconds=5),
        ),
        timeout=30,
    )
    expected = {
        "schema_version": WORKER_READINESS_SCHEMA_VERSION,
        "probe_id": probe_id,
        "worker_identity": expected_worker_identity,
        "profile_version": CANONICAL_PROFILE_VERSION,
        "validation_version": VALIDATION_VERSION,
    }
    if result != expected:
        raise RuntimeError("playback normalization worker control receipt is invalid")
    return result


async def verify_worker_readiness(*, control: bool) -> dict[str, str]:
    settings = get_settings()
    require_worker_readiness_marker(settings.playback_normalization_work_directory)
    expected_worker_identity = playback_normalization_worker_identity()
    temporal_client = await connect_temporal_client(
        settings,
        identity=f"{expected_worker_identity}:readiness-probe",
    )
    await verify_worker_pollers(
        temporal_client=temporal_client,
        settings=settings,
        expected_worker_identity=expected_worker_identity,
    )
    if control:
        await run_control_probe(
            temporal_client=temporal_client,
            settings=settings,
            expected_worker_identity=expected_worker_identity,
        )
    return {
        "result": "pass",
        "mode": "control" if control else "pollers",
        "workflow_poller": "ready",
        "activity_poller": "ready",
        "profile_version": CANONICAL_PROFILE_VERSION,
        "validation_version": VALIDATION_VERSION,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", action="store_true")
    args = parser.parse_args()
    try:
        receipt = asyncio.run(verify_worker_readiness(control=args.control))
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
