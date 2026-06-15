from __future__ import annotations

from datetime import timedelta

try:
    from temporalio import workflow
except Exception:  # pragma: no cover - import fallback for docs/unit tests without worker runtime
    workflow = None


if workflow is not None:

    @workflow.defn
    class MediaScribeProcessingWorkflow:
        @workflow.run
        async def run(self, payload: dict[str, str]) -> dict[str, str]:
            return await workflow.execute_activity(
                "run_processing_pipeline_activity",
                payload,
                schedule_to_close_timeout=timedelta(hours=4),
            )

else:

    class MediaScribeProcessingWorkflow:
        async def run(self, payload: dict[str, str]) -> dict[str, str]:
            return payload
