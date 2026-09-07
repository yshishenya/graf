"""Real Temporal histories: retired child commands replay, never execute again."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from temporalio import activity, workflow
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, Worker
from temporalio.workflow import ActivityCancellationType

from twobrain_rec_server.workflows.prompt_optimization_workflow import (
    APPROVAL_MAX_DAYS,
    PromptOptimizationWorkflow,
    prompt_optimization_retry_policy,
)
from twobrain_rec_server.workflows.prompt_rollback_workflow import PromptRollbackWorkflow


@workflow.defn
class RetainedObservationRetryWorkflow:
    @workflow.run
    async def run(self) -> str:
        return await workflow.execute_activity(
            "optimizer_retained_observation_activity", start_to_close_timeout=timedelta(seconds=30),
            retry_policy=prompt_optimization_retry_policy(),
        )


@workflow.defn(name="PromptOptimizationWorkflow")
class PreCandidateOnlyOptimizationWorkflow:
    """Frozen pre-F239 success/decision command shape, with synthetic activities."""

    def __init__(self):
        self.decision = "awaiting_human"
        self.action_id = None
        self.candidate_ready = False

    @workflow.run
    async def run(self, payload: dict) -> dict:
        resolved = await workflow.execute_activity(
            "resolve_prompt_optimization_contract_activity", payload,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=prompt_optimization_retry_policy(),
        )
        optimized = await workflow.execute_activity(
            "run_gepa_prompt_optimization_activity", {**payload, "resolved_contract": resolved},
            start_to_close_timeout=timedelta(hours=24), heartbeat_timeout=timedelta(minutes=5),
            retry_policy=prompt_optimization_retry_policy(),
            cancellation_type=ActivityCancellationType.WAIT_CANCELLATION_COMPLETED,
        )
        await PromptOptimizationWorkflow._retain_plaintext_history(
            self, payload, optimized.pop("temporal_history"),
        )
        heldout = await workflow.execute_activity(
            "validate_heldout_prompt_candidate_activity",
            {**payload, "resolved_contract": resolved, "optimization_result": optimized},
            start_to_close_timeout=timedelta(hours=4), heartbeat_timeout=timedelta(minutes=5),
            retry_policy=prompt_optimization_retry_policy(),
            cancellation_type=ActivityCancellationType.WAIT_CANCELLATION_COMPLETED,
        )
        await PromptOptimizationWorkflow._retain_plaintext_history(
            self, payload, heldout.pop("temporal_history"),
        )
        candidate = await workflow.execute_activity(
            "publish_prompt_candidate_activity",
            {**payload, "resolved_contract": resolved, "optimization_result": optimized,
             "heldout_result": heldout,
             "approval_expires_at": (workflow.now() + timedelta(days=APPROVAL_MAX_DAYS)).isoformat()},
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=prompt_optimization_retry_policy(),
            cancellation_type=ActivityCancellationType.WAIT_CANCELLATION_COMPLETED,
        )
        self.candidate_ready = True
        try:
            await workflow.wait_condition(
                lambda: self.decision in {"approved", "rejected"},
                timeout=datetime.fromisoformat(candidate["approval_expires_at"]) - workflow.now(),
            )
        except TimeoutError:
            self.decision = "expired"
        if self.decision != "approved":
            return await workflow.execute_activity(
                "finalize_prompt_optimization_activity",
                {**payload, "status": self.decision,
                 "candidate_prompt_version": candidate["candidate_prompt_version"]},
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=prompt_optimization_retry_policy(),
            )
        return await workflow.execute_activity(
            "promote_prompt_candidate_activity",
            {**payload, "approval_action_id": self.action_id,
             "candidate_prompt_version": candidate["candidate_prompt_version"],
             "expected_source_prompt_version": resolved["source_prompt_version"],
             "rollback_prompt_version": resolved["rollback_prompt_version"]},
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=prompt_optimization_retry_policy(),
            cancellation_type=ActivityCancellationType.WAIT_CANCELLATION_COMPLETED,
        )

    @workflow.update
    async def decide(self, payload: dict) -> str:
        result = await workflow.execute_activity(
            "authorize_prompt_optimization_action_activity", payload,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=prompt_optimization_retry_policy(),
        )
        assert result["status"] == "authorized"
        self.action_id, self.decision = payload["action_id"], payload["decision"]
        return self.decision

    @workflow.query
    def ready(self) -> bool:
        return self.candidate_ready


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["new", "promoted", "rejected", "expired", "rollback"])
async def test_completed_optimizer_history_replays_without_activity_execution(case):
    calls = []
    definition = (
        PromptOptimizationWorkflow if case == "new"
        else PromptRollbackWorkflow if case == "rollback"
        else PreCandidateOnlyOptimizationWorkflow
    )
    names = [
        "resolve_prompt_optimization_contract_activity", "run_gepa_prompt_optimization_activity",
        "snapshot_prompt_optimization_history_chunk_activity",
        "finalize_prompt_optimization_history_materialization_activity",
        "validate_heldout_prompt_candidate_activity", "publish_prompt_candidate_activity",
        "finalize_prompt_optimization_activity", "authorize_prompt_optimization_action_activity",
        "promote_prompt_candidate_activity", "authorize_prompt_rollback_action_activity",
        "rollback_prompt_production_label_activity",
    ]

    def fake_activity(name):
        @activity.defn(name=name)
        async def run(payload: dict) -> dict:
            calls.append(name)
            if name == "resolve_prompt_optimization_contract_activity":
                return {"source_prompt_version": 1, "rollback_prompt_version": 1}
            if name in {"run_gepa_prompt_optimization_activity", "validate_heldout_prompt_candidate_activity"}:
                return {"hard_gates_passed": True, "temporal_history": {
                    "phase": "evolution" if name.startswith("run_gepa") else "heldout", "chunk_count": 1,
                }}
            if name == "publish_prompt_candidate_activity":
                if case == "new":
                    assert "approval_expires_at" not in payload
                    return {"candidate_prompt_version": 2, "approval_expires_at": None}
                return {"candidate_prompt_version": 2, "approval_expires_at": (
                    datetime.now(UTC) + timedelta(seconds=1 if case == "expired" else 30)
                ).isoformat()}
            if name.startswith("authorize_"):
                return {"status": "authorized"}
            if name == "promote_prompt_candidate_activity":
                return {"status": "promoted", "production_prompt_version": 2}
            if name == "rollback_prompt_production_label_activity":
                return {"status": "rolled_back", "production_prompt_version": 1}
            if name == "finalize_prompt_optimization_activity":
                return {"status": payload["status"]}
            return {}
        return run

    async with await WorkflowEnvironment.start_local() as env:
        queue = f"synthetic-optimizer-{uuid4()}"
        async with Worker(env.client, task_queue=queue, workflows=[definition],
                          activities=[fake_activity(name) for name in names]):
            handle = await env.client.start_workflow(
                "PromptRollbackWorkflow" if case == "rollback" else "PromptOptimizationWorkflow",
                {"run_id": str(uuid4())}, id=str(uuid4()), task_queue=queue, result_type=dict,
            )
            if case in {"promoted", "rejected"}:
                async def wait_for_candidate():
                    while not await handle.query("ready"):
                        await asyncio.sleep(0.01)
                await asyncio.wait_for(wait_for_candidate(), timeout=5)
                await handle.execute_update("decide", {
                    "action_id": str(uuid4()),
                    "decision": "approved" if case == "promoted" else "rejected",
                })
            result = await handle.result()
            history = await handle.fetch_history()
    expected = "completed" if case == "new" else "rolled_back" if case == "rollback" else case
    assert result["status"] == expected
    if case == "new":
        assert not any(name.startswith(("authorize_", "promote_", "rollback_")) for name in calls)
        assert not any(event.HasField("timer_started_event_attributes") for event in history.events)
    elif case == "expired":
        assert any(event.HasField("timer_started_event_attributes") for event in history.events)
    before = list(calls)
    # Replayer has no activities registered and no server/provider clients.
    await Replayer(workflows=[PromptOptimizationWorkflow, PromptRollbackWorkflow]).replay_workflow(history)
    assert calls == before
