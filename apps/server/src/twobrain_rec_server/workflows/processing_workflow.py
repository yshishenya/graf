from __future__ import annotations

from datetime import timedelta

try:
    from temporalio import workflow
except Exception:  # pragma: no cover - import fallback for docs/unit tests without worker runtime
    workflow = None

PROCESSING_ACTIVITY_MAX_ATTEMPTS = 6


def processing_retry_policy():
    from temporalio.common import RetryPolicy

    return RetryPolicy(
        initial_interval=timedelta(seconds=15),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(minutes=2),
        maximum_attempts=PROCESSING_ACTIVITY_MAX_ATTEMPTS,
    )


if workflow is not None:

    @workflow.defn
    class MediaScribeProcessingWorkflow:
        @workflow.run
        async def run(self, payload: dict[str, str]) -> dict[str, str]:
            return await workflow.execute_activity(
                "run_processing_pipeline_activity",
                payload,
                schedule_to_close_timeout=timedelta(hours=4),
                heartbeat_timeout=timedelta(seconds=60),
                retry_policy=processing_retry_policy(),
            )

else:

    class MediaScribeProcessingWorkflow:
        async def run(self, payload: dict[str, str]) -> dict[str, str]:
            return payload
