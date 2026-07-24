from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy


@workflow.defn(name="InvitationDeliveryWorkflow")
class InvitationDeliveryWorkflow:
    @workflow.run
    async def run(self, payload: dict[str, str]) -> dict[str, str]:
        return await workflow.execute_activity(
            "deliver_meeting_invitation_activity",
            payload,
            start_to_close_timeout=timedelta(seconds=45),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(minutes=5),
                maximum_attempts=5,
            ),
        )


@workflow.defn(name="AccountCreatedEmailWorkflow")
class AccountCreatedEmailWorkflow:
    @workflow.run
    async def run(self, payload: dict[str, str]) -> dict[str, str]:
        return await workflow.execute_activity(
            "send_account_created_email_activity",
            payload,
            start_to_close_timeout=timedelta(seconds=45),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(minutes=5),
                maximum_attempts=5,
            ),
        )
