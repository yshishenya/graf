from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

try:
    from temporalio import workflow
    from temporalio.workflow import ActivityCancellationType
except Exception:  # pragma: no cover - docs/unit environment
    workflow = None
    ActivityCancellationType = None


if workflow is not None:

    @workflow.defn
    class PromptRollbackWorkflow:
        @workflow.run
        async def run(self, payload: dict[str, Any]) -> dict[str, object]:
            authorized = await workflow.execute_activity(
                "authorize_prompt_rollback_action_activity",
                payload,
                start_to_close_timeout=timedelta(minutes=2),
            )
            if authorized.get("status") != "authorized":
                return {"status": "denied"}
            # Rollback owns a separate linked trace and reuses the same serialized
            # label mutation/expected-current/post-verification activity as promotion.
            try:
                return await workflow.execute_activity(
                    "rollback_prompt_production_label_activity",
                    payload,
                    start_to_close_timeout=timedelta(minutes=5),
                    cancellation_type=ActivityCancellationType.WAIT_CANCELLATION_COMPLETED,
                )
            except asyncio.CancelledError:
                async def reconcile_rollback() -> dict[str, object]:
                    return await workflow.execute_activity(
                        "rollback_prompt_production_label_activity",
                        payload,
                        start_to_close_timeout=timedelta(minutes=5),
                        cancellation_type=(
                            ActivityCancellationType.WAIT_CANCELLATION_COMPLETED
                        ),
                    )

                reconciliation_task = asyncio.ensure_future(reconcile_rollback())
                while True:
                    try:
                        reconciled = await asyncio.shield(reconciliation_task)
                        break
                    except asyncio.CancelledError:
                        if reconciliation_task.cancelled():
                            raise
                        # Repeated workflow cancellation must not detach the
                        # commit-wins reconciliation activity.
                        continue
                if reconciled.get("status") == "rolled_back":
                    return reconciled
                raise

else:

    class PromptRollbackWorkflow:
        async def run(self, payload: dict[str, Any]) -> dict[str, object]:
            return payload
