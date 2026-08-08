from __future__ import annotations

from datetime import timedelta

try:
    from temporalio import workflow
except Exception:  # pragma: no cover - import fallback for docs and narrow unit tests
    workflow = None


def playback_normalization_retry_policy():
    from temporalio.common import RetryPolicy

    return RetryPolicy(
        initial_interval=timedelta(seconds=30),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(minutes=15),
        maximum_attempts=4,
    )


if workflow is not None:
    @workflow.defn
    class PlaybackNormalizationWorkflow:
        @workflow.run
        async def run(self, payload: dict[str, str]) -> dict[str, str]:
            return await workflow.execute_activity(
                "run_playback_normalization_activity",
                payload,
                start_to_close_timeout=timedelta(hours=6),
                heartbeat_timeout=timedelta(seconds=60),
                retry_policy=playback_normalization_retry_policy(),
            )

else:

    class PlaybackNormalizationWorkflow:
        async def run(self, payload: dict[str, str]) -> dict[str, str]:
            return payload
