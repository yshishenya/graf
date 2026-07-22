from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta
from typing import Any

APPROVAL_MAX_DAYS = 7


def prompt_optimization_retry_policy():
    from temporalio.common import RetryPolicy

    return RetryPolicy(
        initial_interval=timedelta(seconds=10),
        backoff_coefficient=2,
        maximum_interval=timedelta(minutes=5),
        maximum_attempts=6,
        non_retryable_error_types=[
            "PromptOptimizationError",
            "PromptOptimizationContractError",
        ],
    )


try:
    from temporalio import workflow
    from temporalio.workflow import ActivityCancellationType
except Exception:  # pragma: no cover - docs/unit environment
    workflow = None
    ActivityCancellationType = None


if workflow is not None:

    @workflow.defn
    class PromptOptimizationWorkflow:
        def __init__(self) -> None:
            self._candidate_ready = False
            self._approval_state = "not_requested"
            self._approval_action_id: str | None = None
            self._approval_expires_at = None

        @workflow.run
        async def run(self, payload: dict[str, Any]) -> dict[str, object]:
            try:
                return await self._run_impl(payload)
            except asyncio.CancelledError:
                async def finalize_cancelled() -> dict[str, object]:
                    return await workflow.execute_activity(
                        "finalize_prompt_optimization_activity",
                        {
                            **payload,
                            "status": "cancelled",
                            "failure_code": "optimization_workflow_cancelled",
                        },
                        start_to_close_timeout=timedelta(minutes=2),
                        retry_policy=prompt_optimization_retry_policy(),
                    )

                # Temporal Python uses asyncio cancellation. Shielding a separate
                # deterministic task is the non-cancellable cleanup scope for the
                # DB transition and deterministic terminal Langfuse observation.
                terminal = await asyncio.shield(asyncio.ensure_future(finalize_cancelled()))
                # Promotion is the commit point: cancellation arriving after the
                # production label mutation must complete as promoted, not report
                # a cancelled workflow over promoted durable state.
                if terminal.get("status") == "promoted":
                    return terminal
                raise
            except Exception:
                await workflow.execute_activity(
                    "finalize_prompt_optimization_activity",
                    {
                        **payload,
                        "status": "failed",
                        "failure_code": "optimization_workflow_failed",
                    },
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=prompt_optimization_retry_policy(),
                )
                raise

        async def _run_impl(self, payload: dict[str, Any]) -> dict[str, object]:
            resolved = await workflow.execute_activity(
                "resolve_prompt_optimization_contract_activity",
                payload,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=prompt_optimization_retry_policy(),
            )
            optimized = await workflow.execute_activity(
                "run_gepa_prompt_optimization_activity",
                {**payload, "resolved_contract": resolved},
                start_to_close_timeout=timedelta(hours=24),
                heartbeat_timeout=timedelta(minutes=5),
                retry_policy=prompt_optimization_retry_policy(),
                cancellation_type=ActivityCancellationType.WAIT_CANCELLATION_COMPLETED,
            )
            await self._retain_plaintext_history(payload, optimized["temporal_history"])
            optimized_for_next = dict(optimized)
            optimized_for_next.pop("temporal_history")
            heldout = await workflow.execute_activity(
                "validate_heldout_prompt_candidate_activity",
                {
                    **payload,
                    "resolved_contract": resolved,
                    "optimization_result": optimized_for_next,
                },
                start_to_close_timeout=timedelta(hours=4),
                heartbeat_timeout=timedelta(minutes=5),
                retry_policy=prompt_optimization_retry_policy(),
                cancellation_type=ActivityCancellationType.WAIT_CANCELLATION_COMPLETED,
            )
            await self._retain_plaintext_history(payload, heldout["temporal_history"])
            heldout_for_next = dict(heldout)
            heldout_for_next.pop("temporal_history")
            if not heldout_for_next.get("hard_gates_passed"):
                return await workflow.execute_activity(
                    "finalize_prompt_optimization_activity",
                    {
                        **payload,
                        "status": "rejected",
                        "aggregate_scores": heldout_for_next,
                    },
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=prompt_optimization_retry_policy(),
                )
            approval_expires_at = workflow.now() + timedelta(days=APPROVAL_MAX_DAYS)
            candidate = await workflow.execute_activity(
                "publish_prompt_candidate_activity",
                {
                    **payload,
                    "resolved_contract": resolved,
                    "optimization_result": optimized_for_next,
                    "heldout_result": heldout_for_next,
                    "approval_expires_at": approval_expires_at.isoformat(),
                },
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=prompt_optimization_retry_policy(),
                cancellation_type=ActivityCancellationType.WAIT_CANCELLATION_COMPLETED,
            )
            self._candidate_ready = True
            self._approval_state = "awaiting_human"
            self._approval_expires_at = datetime.fromisoformat(
                str(candidate["approval_expires_at"])
            )
            try:
                await workflow.wait_condition(
                    lambda: self._approval_state in {"approved", "rejected"},
                    timeout=self._approval_expires_at - workflow.now(),
                )
            except TimeoutError:
                self._approval_state = "expired"
            if self._approval_state != "approved":
                return await workflow.execute_activity(
                    "finalize_prompt_optimization_activity",
                    {
                        **payload,
                        "status": self._approval_state,
                        "candidate_prompt_version": candidate["candidate_prompt_version"],
                    },
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=prompt_optimization_retry_policy(),
                )
            promoted = await workflow.execute_activity(
                "promote_prompt_candidate_activity",
                {
                    **payload,
                    "approval_action_id": self._approval_action_id,
                    "candidate_prompt_version": candidate["candidate_prompt_version"],
                    "expected_source_prompt_version": resolved["source_prompt_version"],
                    "rollback_prompt_version": resolved["rollback_prompt_version"],
                },
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=prompt_optimization_retry_policy(),
                cancellation_type=ActivityCancellationType.WAIT_CANCELLATION_COMPLETED,
            )
            return promoted

        async def _retain_plaintext_history(
            self,
            payload: dict[str, Any],
            descriptor: object,
        ) -> None:
            if not isinstance(descriptor, dict):
                raise ValueError("prompt optimization history descriptor is invalid")
            chunk_count = descriptor.get("chunk_count")
            phase = descriptor.get("phase")
            if (
                not isinstance(chunk_count, int)
                or chunk_count < 1
                or phase not in {"evolution", "heldout"}
            ):
                raise ValueError("prompt optimization history descriptor is invalid")
            for chunk_index in range(chunk_count):
                await workflow.execute_activity(
                    "snapshot_prompt_optimization_history_chunk_activity",
                    {
                        "run_id": payload["run_id"],
                        "phase": phase,
                        "chunk_index": chunk_index,
                        "history": descriptor,
                    },
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=prompt_optimization_retry_policy(),
                )
            await workflow.execute_activity(
                "finalize_prompt_optimization_history_materialization_activity",
                {
                    "run_id": payload["run_id"],
                    "phase": phase,
                    "history": descriptor,
                },
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=prompt_optimization_retry_policy(),
            )

        @workflow.update
        async def decide(self, payload: dict[str, str]) -> str:
            action_id = payload["action_id"]
            decision = payload["decision"]
            authorized = await workflow.execute_activity(
                "authorize_prompt_optimization_action_activity",
                {"action_id": action_id, "decision": decision},
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=prompt_optimization_retry_policy(),
            )
            if authorized.get("status") != "authorized":
                return "denied"
            self._approval_action_id = action_id
            self._approval_state = decision
            return decision

        @decide.validator
        def decide_validator(self, payload: dict[str, str]) -> None:
            if not self._candidate_ready or self._approval_state != "awaiting_human":
                raise ValueError("prompt optimization is not awaiting approval")
            if set(payload) != {"action_id", "decision"}:
                raise ValueError("approval update must contain action_id and decision only")
            if payload["decision"] not in {"approved", "rejected"}:
                raise ValueError("approval decision is invalid")
            if not re.fullmatch(
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                payload["action_id"],
            ):
                raise ValueError("approval action id must be a UUID")
            if self._approval_expires_at is None or workflow.now() >= self._approval_expires_at:
                raise ValueError("prompt optimization approval expired")

        @workflow.query
        def status(self) -> dict[str, object]:
            return {
                "candidate_ready": self._candidate_ready,
                "approval_state": self._approval_state,
                "approval_expires_at": (
                    self._approval_expires_at.isoformat()
                    if self._approval_expires_at is not None
                    else None
                ),
            }

else:

    class PromptOptimizationWorkflow:
        async def run(self, payload: dict[str, Any]) -> dict[str, object]:
            return payload
