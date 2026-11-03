"""Deterministic orchestration; content and transport live in activities."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy


@workflow.defn(name="SummaryDeliveryWorkflow")
class SummaryDeliveryWorkflow:
    @workflow.run
    async def run(self, payload: dict[str, str]):
        return await workflow.execute_activity(
            "deliver_summary_batch_activity",
            payload,
            start_to_close_timeout=timedelta(minutes=15),
            retry_policy=RetryPolicy(
                maximum_attempts=5,
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(minutes=2),
            ),
        )
