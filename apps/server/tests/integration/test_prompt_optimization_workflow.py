from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import UUID

import pytest

from twobrain_rec_server.outcomes.prompt_optimization import (
    optimization_trace_id,
    rollback_trace_id,
)
from twobrain_rec_server.workflows.prompt_optimization_workflow import (
    APPROVAL_MAX_DAYS,
)
from twobrain_rec_server.workflows.temporal_client import (
    prompt_optimization_workflow_id,
    prompt_rollback_workflow_id,
)


def test_optimization_and_rollback_use_separate_deterministic_workflow_ids() -> None:
    run_id = "10000000-0000-0000-0000-000000000001"
    assert prompt_optimization_workflow_id(run_id) == f"prompt-optimization/{run_id}"
    assert prompt_rollback_workflow_id(run_id, 1) == f"prompt-rollback/{run_id}/1"
    assert APPROVAL_MAX_DAYS == 7
    assert optimization_trace_id(UUID(run_id)) != rollback_trace_id(UUID(run_id), 1)
    with pytest.raises(ValueError):
        prompt_optimization_workflow_id("unsafe")


def test_workflow_source_keeps_operator_identity_out_of_temporal_update() -> None:
    import inspect

    from twobrain_rec_server.workflows.prompt_optimization_workflow import (
        PromptOptimizationWorkflow,
    )

    source = inspect.getsource(PromptOptimizationWorkflow)
    assert 'set(payload) != {"action_id", "decision"}' in source
    assert "actor_id" not in source
    assert '"publish_prompt_candidate_activity"' in source
    assert source.index('"validate_heldout_prompt_candidate_activity"') < source.index(
        '"publish_prompt_candidate_activity"'
    )
    # Long-running evaluation, external candidate publication, and irreversible
    # promotion all wait for their activity cancellation acknowledgement.
    assert source.count("ActivityCancellationType.WAIT_CANCELLATION_COMPLETED") == 4

    from twobrain_rec_server.workflows.prompt_rollback_workflow import PromptRollbackWorkflow

    rollback_source = inspect.getsource(PromptRollbackWorkflow)
    assert rollback_source.count("ActivityCancellationType.WAIT_CANCELLATION_COMPLETED") == 2


def test_worker_isolates_all_optimizer_activities_on_concurrency_one_queue() -> None:
    import inspect

    from twobrain_rec_server.workflows import worker

    source = inspect.getsource(worker.run_worker)
    expected_activities = {
        "resolve_prompt_optimization_contract_activity",
        "run_gepa_prompt_optimization_activity",
        "snapshot_prompt_optimization_history_chunk_activity",
        "validate_heldout_prompt_candidate_activity",
        "publish_prompt_candidate_activity",
        "authorize_prompt_optimization_action_activity",
        "promote_prompt_candidate_activity",
        "finalize_prompt_optimization_activity",
        "finalize_prompt_optimization_history_materialization_activity",
        "authorize_prompt_rollback_action_activity",
        "rollback_prompt_production_label_activity",
    }
    for activity_name in expected_activities:
        assert activity_name in source
    assert "task_queue=prompt_optimization_task_queue(settings)" in source
    assert "workflows=[PromptOptimizationWorkflow, PromptRollbackWorkflow]" in source
    assert "max_concurrent_activities=1" in source
    assert "asyncio.gather(*(worker.run() for worker in workers))" in source


@pytest.mark.anyio
async def test_workflow_failure_finalizes_run_instead_of_leaving_it_active(monkeypatch) -> None:
    from twobrain_rec_server.workflows import prompt_optimization_workflow as workflow_module

    activity_names: list[str] = []

    async def execute_activity(name, payload, **_kwargs):
        activity_names.append(name)
        if name == "resolve_prompt_optimization_contract_activity":
            raise RuntimeError("contract unavailable")
        if name == "finalize_prompt_optimization_activity":
            assert payload["status"] == "failed"
            return {"status": "failed"}
        raise AssertionError(name)

    monkeypatch.setattr(
        workflow_module,
        "workflow",
        SimpleNamespace(execute_activity=execute_activity),
    )
    with pytest.raises(RuntimeError, match="contract unavailable"):
        await workflow_module.PromptOptimizationWorkflow().run(
            {"run_id": "10000000-0000-0000-0000-000000000001"}
        )

    assert activity_names == [
        "resolve_prompt_optimization_contract_activity",
        "finalize_prompt_optimization_activity",
    ]


@pytest.mark.anyio
async def test_workflow_cancellation_shields_terminal_cleanup(monkeypatch) -> None:
    from twobrain_rec_server.workflows import prompt_optimization_workflow as workflow_module

    activity_names: list[str] = []
    resolve_started = asyncio.Event()

    async def execute_activity(name, payload, **_kwargs):
        activity_names.append(name)
        if name == "resolve_prompt_optimization_contract_activity":
            resolve_started.set()
            await asyncio.Event().wait()
        if name == "finalize_prompt_optimization_activity":
            assert payload["status"] == "cancelled"
            assert payload["failure_code"] == "optimization_workflow_cancelled"
            return {"status": "cancelled"}
        raise AssertionError(name)

    monkeypatch.setattr(
        workflow_module,
        "workflow",
        SimpleNamespace(execute_activity=execute_activity),
    )
    task = asyncio.create_task(
        workflow_module.PromptOptimizationWorkflow().run(
            {"run_id": "10000000-0000-0000-0000-000000000001"}
        )
    )
    await resolve_started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert activity_names == [
        "resolve_prompt_optimization_contract_activity",
        "finalize_prompt_optimization_activity",
    ]


@pytest.mark.anyio
async def test_workflow_cancellation_returns_promoted_when_commit_point_already_won(
    monkeypatch,
) -> None:
    from twobrain_rec_server.workflows import prompt_optimization_workflow as workflow_module

    activity_names: list[str] = []
    activity_started = asyncio.Event()

    async def execute_activity(name, _payload, **_kwargs):
        activity_names.append(name)
        if name == "resolve_prompt_optimization_contract_activity":
            activity_started.set()
            await asyncio.Event().wait()
        if name == "finalize_prompt_optimization_activity":
            return {"status": "promoted", "run_id": "run-id"}
        raise AssertionError(name)

    monkeypatch.setattr(
        workflow_module,
        "workflow",
        SimpleNamespace(execute_activity=execute_activity),
    )
    task = asyncio.create_task(workflow_module.PromptOptimizationWorkflow().run({"run_id": "run-id"}))
    await activity_started.wait()
    task.cancel()

    assert await task == {"status": "promoted", "run_id": "run-id"}
    assert activity_names == [
        "resolve_prompt_optimization_contract_activity",
        "finalize_prompt_optimization_activity",
    ]


@pytest.mark.anyio
async def test_candidate_commit_re_raises_cancellation_then_terminal_cleanup_runs(
    monkeypatch,
) -> None:
    from twobrain_rec_server.workflows import prompt_optimization_workflow as workflow_module

    candidate_started = asyncio.Event()
    candidate_committed = False
    activity_names: list[str] = []

    async def execute_activity(name, _payload, **_kwargs):
        nonlocal candidate_committed
        activity_names.append(name)
        if name == "publish_prompt_candidate_activity":
            candidate_started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                candidate_committed = True
                raise
        if name == "finalize_prompt_optimization_activity":
            assert candidate_committed is True
            return {"status": "cancelled", "run_id": "run-id"}
        raise AssertionError(name)

    async def run_candidate_only(self, payload):
        return await workflow_module.workflow.execute_activity(
            "publish_prompt_candidate_activity",
            payload,
            cancellation_type=workflow_module.ActivityCancellationType.WAIT_CANCELLATION_COMPLETED,
        )

    monkeypatch.setattr(
        workflow_module,
        "workflow",
        SimpleNamespace(execute_activity=execute_activity),
    )
    monkeypatch.setattr(workflow_module.PromptOptimizationWorkflow, "_run_impl", run_candidate_only)
    task = asyncio.create_task(workflow_module.PromptOptimizationWorkflow().run({"run_id": "run-id"}))
    await candidate_started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert activity_names == [
        "publish_prompt_candidate_activity",
        "finalize_prompt_optimization_activity",
    ]


@pytest.mark.anyio
async def test_rollback_workflow_reconciles_committed_activity_after_cancellation(
    monkeypatch,
) -> None:
    from twobrain_rec_server.workflows import prompt_rollback_workflow as rollback_module

    rollback_started = asyncio.Event()
    committed = False
    activity_names: list[str] = []

    async def execute_activity(name, _payload, **_kwargs):
        nonlocal committed
        activity_names.append(name)
        if name == "authorize_prompt_rollback_action_activity":
            return {"status": "authorized"}
        if name == "rollback_prompt_production_label_activity" and not committed:
            rollback_started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                committed = True
                raise
        if name == "rollback_prompt_production_label_activity":
            return {"status": "rolled_back", "production_prompt_version": 1}
        raise AssertionError(name)

    monkeypatch.setattr(
        rollback_module,
        "workflow",
        SimpleNamespace(execute_activity=execute_activity),
    )
    task = asyncio.create_task(
        rollback_module.PromptRollbackWorkflow().run(
            {"run_id": "run-id", "action_id": "action-id"}
        )
    )
    await rollback_started.wait()
    task.cancel()

    assert await task == {"status": "rolled_back", "production_prompt_version": 1}
    assert activity_names == [
        "authorize_prompt_rollback_action_activity",
        "rollback_prompt_production_label_activity",
        "rollback_prompt_production_label_activity",
    ]


@pytest.mark.anyio
async def test_rollback_workflow_does_not_spin_when_reconciliation_is_cancelled(
    monkeypatch,
) -> None:
    from twobrain_rec_server.workflows import prompt_rollback_workflow as rollback_module

    rollback_started = asyncio.Event()
    rollback_attempts = 0

    async def execute_activity(name, _payload, **_kwargs):
        nonlocal rollback_attempts
        if name == "authorize_prompt_rollback_action_activity":
            return {"status": "authorized"}
        if name == "rollback_prompt_production_label_activity":
            rollback_attempts += 1
            if rollback_attempts == 1:
                rollback_started.set()
                await asyncio.Event().wait()
            raise asyncio.CancelledError
        raise AssertionError(name)

    monkeypatch.setattr(
        rollback_module,
        "workflow",
        SimpleNamespace(execute_activity=execute_activity),
    )
    task = asyncio.create_task(
        rollback_module.PromptRollbackWorkflow().run(
            {"run_id": "run-id", "action_id": "action-id"}
        )
    )
    await rollback_started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=1)
    assert rollback_attempts == 2
