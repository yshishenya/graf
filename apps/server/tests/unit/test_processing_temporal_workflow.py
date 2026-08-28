from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from temporalio import activity, workflow
from temporalio.client import WorkflowHistory
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, Worker
from temporalio.workflow import ActivityCancellationType

from twobrain_rec_server.workflows.processing_workflow import (
    MediaScribeProcessingWorkflow,
    processing_retry_policy,
)

SERVER_SRC = Path(__file__).parents[2] / "src"


@workflow.defn(name="MediaScribeProcessingWorkflow")
class LegacyMediaScribeProcessingWorkflow:
    """The pre-recovery command shape used to produce a legacy history."""

    @workflow.run
    async def run(self, payload: dict[str, str]) -> dict[str, str]:
        return await workflow.execute_activity(
            "run_processing_pipeline_activity",
            payload,
            schedule_to_close_timeout=timedelta(hours=4),
            heartbeat_timeout=timedelta(seconds=60),
            retry_policy=processing_retry_policy(),
        )


@workflow.defn(name="MediaScribeProcessingWorkflow")
class PreNormalizationMediaScribeProcessingWorkflow:
    """The recovery command shape immediately before normalization waiting."""

    def __init__(self) -> None:
        self._manual_check_requested = False

    @workflow.run
    async def run(self, payload: dict[str, str]) -> dict[str, str]:
        assert workflow.patched("processing-recovery-v1")
        step_payload = {**payload, "single_step": "true"}
        cancellation_type = (
            ActivityCancellationType.WAIT_CANCELLATION_COMPLETED
            if workflow.patched("processing-cancellation-v1")
            else ActivityCancellationType.TRY_CANCEL
        )
        result = await workflow.execute_activity(
            "run_processing_pipeline_activity",
            step_payload,
            schedule_to_close_timeout=timedelta(minutes=20),
            heartbeat_timeout=timedelta(seconds=60),
            retry_policy=processing_retry_policy(),
            cancellation_type=cancellation_type,
        )
        with suppress(TimeoutError):
            await workflow.wait_condition(
                lambda: self._manual_check_requested,
                timeout=timedelta(seconds=int(result["next_poll_seconds"])),
                timeout_summary="next provider processing check",
            )
        return await workflow.execute_activity(
            "run_processing_pipeline_activity",
            step_payload,
            schedule_to_close_timeout=timedelta(minutes=20),
            heartbeat_timeout=timedelta(seconds=60),
            retry_policy=processing_retry_policy(),
            cancellation_type=cancellation_type,
        )


def _payload() -> dict[str, str]:
    return {"meeting_id": "meeting-1", "workspace_id": "workspace-1"}


@pytest.mark.asyncio
async def test_recovery_workflow_uses_durable_timer_and_bounded_activity_options() -> None:
    calls: list[dict[str, str]] = []

    @activity.defn(name="run_processing_pipeline_activity")
    async def fake_processing_activity(payload: dict[str, str]) -> dict[str, str]:
        calls.append(payload)
        if len(calls) == 1:
            return {"processing_status": "polling", "next_poll_seconds": "30"}
        return {"processing_status": "processed"}

    async with await WorkflowEnvironment.start_time_skipping() as env:
        task_queue = f"processing-temporal-{uuid4()}"
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[MediaScribeProcessingWorkflow],
            activities=[fake_processing_activity],
        ):
            handle = await env.client.start_workflow(
                MediaScribeProcessingWorkflow.run,
                _payload(),
                id=f"processing-test/{uuid4()}",
                task_queue=task_queue,
            )
            assert await handle.result() == {"processing_status": "processed"}
            history = await handle.fetch_history()

    assert len(calls) == 2
    assert all(call["single_step"] == "true" for call in calls)
    assert any(event.HasField("timer_started_event_attributes") for event in history.events)

    scheduled = next(
        event.activity_task_scheduled_event_attributes
        for event in history.events
        if event.HasField("activity_task_scheduled_event_attributes")
    )
    assert scheduled.schedule_to_close_timeout.seconds == 20 * 60
    assert scheduled.heartbeat_timeout.seconds == 60
    workflow_source = (
        SERVER_SRC / "twobrain_rec_server/workflows/processing_workflow.py"
    ).read_text(encoding="utf-8")
    assert "ActivityCancellationType.WAIT_CANCELLATION_COMPLETED" in workflow_source


@pytest.mark.asyncio
async def test_signal_during_activity_wakes_the_next_same_job_check() -> None:
    first_started = asyncio.Event()
    release_first = asyncio.Event()
    second_started = asyncio.Event()
    calls: list[dict[str, str]] = []

    @activity.defn(name="run_processing_pipeline_activity")
    async def fake_processing_activity(payload: dict[str, str]) -> dict[str, str]:
        calls.append(payload)
        if len(calls) == 1:
            first_started.set()
            await release_first.wait()
            return {"processing_status": "polling", "next_poll_seconds": "30"}
        second_started.set()
        return {"processing_status": "processed"}

    async with await WorkflowEnvironment.start_local() as env:
        task_queue = f"processing-signal-{uuid4()}"
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[MediaScribeProcessingWorkflow],
            activities=[fake_processing_activity],
        ):
            handle = await env.client.start_workflow(
                MediaScribeProcessingWorkflow.run,
                _payload(),
                id=f"processing-signal-test/{uuid4()}",
                task_queue=task_queue,
            )
            await asyncio.wait_for(first_started.wait(), timeout=5)
            await handle.signal(MediaScribeProcessingWorkflow.request_manual_check)
            release_first.set()
            await asyncio.wait_for(second_started.wait(), timeout=5)
            assert await handle.result() == {"processing_status": "processed"}

    assert len(calls) == 2


@pytest.mark.asyncio
async def test_unknown_outcome_uses_durable_timer_for_same_key_reconciliation() -> None:
    calls: list[dict[str, str]] = []

    @activity.defn(name="run_processing_pipeline_activity")
    async def fake_processing_activity(payload: dict[str, str]) -> dict[str, str]:
        calls.append(payload)
        if len(calls) == 1:
            return {
                "processing_status": "blocked_unknown",
                "next_poll_seconds": "30",
            }
        return {"processing_status": "processed"}

    async with await WorkflowEnvironment.start_time_skipping() as env:
        task_queue = f"processing-unknown-{uuid4()}"
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[MediaScribeProcessingWorkflow],
            activities=[fake_processing_activity],
        ):
            handle = await env.client.start_workflow(
                MediaScribeProcessingWorkflow.run,
                _payload(),
                id=f"processing-unknown-test/{uuid4()}",
                task_queue=task_queue,
            )
            assert await handle.result() == {"processing_status": "processed"}
            history = await handle.fetch_history()

    assert len(calls) == 2
    assert any(event.HasField("timer_started_event_attributes") for event in history.events)


@pytest.mark.asyncio
async def test_watchdog_waits_for_manual_same_job_check_without_auto_retry() -> None:
    first_finished = asyncio.Event()
    calls: list[dict[str, str]] = []

    @activity.defn(name="run_processing_pipeline_activity")
    async def fake_processing_activity(payload: dict[str, str]) -> dict[str, str]:
        calls.append(payload)
        if len(calls) == 1:
            first_finished.set()
            return {
                "processing_status": "failed_retryable",
                "reason_code": "processing_retry_deadline_exceeded",
            }
        return {"processing_status": "processed"}

    async with await WorkflowEnvironment.start_local() as env:
        task_queue = f"processing-watchdog-{uuid4()}"
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[MediaScribeProcessingWorkflow],
            activities=[fake_processing_activity],
        ):
            handle = await env.client.start_workflow(
                MediaScribeProcessingWorkflow.run,
                _payload(),
                id=f"processing-watchdog/{uuid4()}",
                task_queue=task_queue,
            )
            await asyncio.wait_for(first_finished.wait(), timeout=5)
            await handle.signal(MediaScribeProcessingWorkflow.request_manual_check)
            assert await handle.result() == {"processing_status": "processed"}

    assert len(calls) == 2


@pytest.mark.asyncio
async def test_update_handler_is_registered_and_wakes_the_same_timer() -> None:
    first_finished = asyncio.Event()
    second_started = asyncio.Event()
    calls: list[dict[str, str]] = []

    @activity.defn(name="run_processing_pipeline_activity")
    async def fake_processing_activity(payload: dict[str, str]) -> dict[str, str]:
        calls.append(payload)
        if len(calls) == 1:
            first_finished.set()
            return {"processing_status": "waiting_retry", "next_poll_seconds": "30"}
        second_started.set()
        return {"processing_status": "processed"}

    async with await WorkflowEnvironment.start_local() as env:
        task_queue = f"processing-update-{uuid4()}"
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[MediaScribeProcessingWorkflow],
            activities=[fake_processing_activity],
        ):
            handle = await env.client.start_workflow(
                MediaScribeProcessingWorkflow.run,
                _payload(),
                id=f"processing-update-test/{uuid4()}",
                task_queue=task_queue,
            )
            await asyncio.wait_for(first_finished.wait(), timeout=5)
            assert await handle.execute_update(
                MediaScribeProcessingWorkflow.request_manual_check_update
            ) == {"status": "accepted"}
            await asyncio.wait_for(second_started.wait(), timeout=5)
            assert await handle.result() == {"processing_status": "processed"}

    definition = MediaScribeProcessingWorkflow.__temporal_workflow_definition
    assert set(definition.signals) == {"request_manual_check"}
    assert set(definition.updates) == {"request_manual_check"}
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_normalization_pending_wait_is_bounded_and_continues_as_new() -> None:
    calls: list[dict[str, str]] = []

    @activity.defn(name="run_processing_pipeline_activity")
    async def fake_processing_activity(payload: dict[str, str]) -> dict[str, str]:
        calls.append(payload)
        if len(calls) <= 32:
            return {
                "processing_status": "normalization_pending",
                "reason_code": "normalization_retry_wait",
                "next_attempt_at": "2026-08-28T00:00:00+00:00",
                "next_poll_seconds": "900",
            }
        return {"processing_status": "processed"}

    async with await WorkflowEnvironment.start_time_skipping() as env:
        task_queue = f"processing-normalization-{uuid4()}"
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[MediaScribeProcessingWorkflow],
            activities=[fake_processing_activity],
        ):
            handle = await env.client.start_workflow(
                MediaScribeProcessingWorkflow.run,
                _payload(),
                id=f"processing-normalization-test/{uuid4()}",
                task_queue=task_queue,
            )
            first_run_handle = env.client.get_workflow_handle(
                handle.id,
                run_id=handle.first_execution_run_id,
            )
            assert await handle.result() == {"processing_status": "processed"}
            first_run_history = await first_run_handle.fetch_history()

    assert len(calls) == 33
    assert all(call["single_step"] == "true" for call in calls)
    assert any(
        event.HasField("workflow_execution_continued_as_new_event_attributes")
        for event in first_run_history.events
    )


@pytest.mark.asyncio
async def test_provider_polling_history_is_bounded_with_continue_as_new() -> None:
    calls = 0

    @activity.defn(name="run_processing_pipeline_activity")
    async def fake_processing_activity(_payload: dict[str, str]) -> dict[str, str]:
        nonlocal calls
        calls += 1
        if calls <= 32:
            return {"processing_status": "waiting_retry", "next_poll_seconds": "5"}
        return {"processing_status": "processed"}

    async with await WorkflowEnvironment.start_time_skipping() as env:
        task_queue = f"processing-provider-history-{uuid4()}"
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[MediaScribeProcessingWorkflow],
            activities=[fake_processing_activity],
        ):
            handle = await env.client.start_workflow(
                MediaScribeProcessingWorkflow.run,
                _payload(),
                id=f"processing-provider-history/{uuid4()}",
                task_queue=task_queue,
            )
            first_run_handle = env.client.get_workflow_handle(
                handle.id,
                run_id=handle.first_execution_run_id,
            )
            assert await handle.result() == {"processing_status": "processed"}
            first_run_history = await first_run_handle.fetch_history()

    assert calls == 33
    assert any(
        event.HasField("workflow_execution_continued_as_new_event_attributes")
        for event in first_run_history.events
    )


@pytest.mark.asyncio
async def test_normalization_pending_uses_slow_fallback_when_schedule_is_missing() -> None:
    calls = 0

    @activity.defn(name="run_processing_pipeline_activity")
    async def fake_processing_activity(_payload: dict[str, str]) -> dict[str, str]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"processing_status": "normalization_pending"}
        return {"processing_status": "processed"}

    async with await WorkflowEnvironment.start_time_skipping() as env:
        task_queue = f"processing-normalization-fallback-{uuid4()}"
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[MediaScribeProcessingWorkflow],
            activities=[fake_processing_activity],
        ):
            handle = await env.client.start_workflow(
                MediaScribeProcessingWorkflow.run,
                _payload(),
                id=f"processing-normalization-fallback/{uuid4()}",
                task_queue=task_queue,
            )
            assert await handle.result() == {"processing_status": "processed"}
            history = await handle.fetch_history()

    timer = next(
        event.timer_started_event_attributes
        for event in history.events
        if event.HasField("timer_started_event_attributes")
    )
    assert timer.start_to_fire_timeout.seconds == 900


@pytest.mark.asyncio
async def test_manual_check_wakes_normalization_wait() -> None:
    first_finished = asyncio.Event()
    calls = 0

    @activity.defn(name="run_processing_pipeline_activity")
    async def fake_processing_activity(_payload: dict[str, str]) -> dict[str, str]:
        nonlocal calls
        calls += 1
        if calls == 1:
            first_finished.set()
            return {
                "processing_status": "normalization_pending",
                "next_poll_seconds": "900",
            }
        return {"processing_status": "processed"}

    async with await WorkflowEnvironment.start_local() as env:
        task_queue = f"processing-normalization-manual-{uuid4()}"
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[MediaScribeProcessingWorkflow],
            activities=[fake_processing_activity],
        ):
            handle = await env.client.start_workflow(
                MediaScribeProcessingWorkflow.run,
                _payload(),
                id=f"processing-normalization-manual/{uuid4()}",
                task_queue=task_queue,
            )
            await asyncio.wait_for(first_finished.wait(), timeout=5)
            await handle.signal(MediaScribeProcessingWorkflow.request_manual_check)
            assert await handle.result() == {"processing_status": "processed"}

    assert calls == 2


@pytest.mark.asyncio
async def test_current_recovery_history_replays_with_normalization_branch() -> None:
    calls = 0

    @activity.defn(name="run_processing_pipeline_activity")
    async def fake_processing_activity(_payload: dict[str, str]) -> dict[str, str]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"processing_status": "polling", "next_poll_seconds": "5"}
        return {"processing_status": "processed"}

    async with await WorkflowEnvironment.start_time_skipping() as env:
        task_queue = f"processing-current-replay-{uuid4()}"
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[PreNormalizationMediaScribeProcessingWorkflow],
            activities=[fake_processing_activity],
        ):
            handle = await env.client.start_workflow(
                PreNormalizationMediaScribeProcessingWorkflow.run,
                _payload(),
                id=f"processing-current-replay/{uuid4()}",
                task_queue=task_queue,
            )
            assert await handle.result() == {"processing_status": "processed"}
            history = await handle.fetch_history()

    await Replayer(workflows=[MediaScribeProcessingWorkflow]).replay_workflow(history)


@pytest.mark.asyncio
async def test_legacy_history_replays_without_recovery_commands() -> None:
    @activity.defn(name="run_processing_pipeline_activity")
    async def fake_processing_activity(payload: dict[str, str]) -> dict[str, str]:
        assert "single_step" not in payload
        return {"processing_status": "processed"}

    history: WorkflowHistory
    async with await WorkflowEnvironment.start_local() as env:
        task_queue = f"processing-legacy-{uuid4()}"
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[LegacyMediaScribeProcessingWorkflow],
            activities=[fake_processing_activity],
        ):
            handle = await env.client.start_workflow(
                LegacyMediaScribeProcessingWorkflow.run,
                _payload(),
                id=f"processing-legacy-test/{uuid4()}",
                task_queue=task_queue,
            )
            assert await handle.result() == {"processing_status": "processed"}
            history = await handle.fetch_history()

    scheduled = next(
        event.activity_task_scheduled_event_attributes
        for event in history.events
        if event.HasField("activity_task_scheduled_event_attributes")
    )
    assert scheduled.schedule_to_close_timeout.seconds == 4 * 60 * 60
    assert scheduled.heartbeat_timeout.seconds == 60
    assert not any(event.HasField("marker_recorded_event_attributes") for event in history.events)
    await Replayer(workflows=[MediaScribeProcessingWorkflow]).replay_workflow(history)


def test_processing_workflow_has_no_asyncio_sleep_and_worker_bounds_heartbeat_loop() -> None:
    source = (SERVER_SRC / "twobrain_rec_server/workflows/processing_workflow.py").read_text(
        encoding="utf-8"
    )

    assert "asyncio.sleep" not in source
    assert "workflow.wait_condition" in source
    worker_source = (SERVER_SRC / "twobrain_rec_server/workflows/worker.py").read_text(
        encoding="utf-8"
    )
    assert "processing_retry_deadline_exceeded" in worker_source
    assert "MEDIASCRIBE_RETRIES_EXHAUSTED" not in worker_source
    assert "processing_recovery_attempt_limit_exceeded" in worker_source
    assert "PROCESSING_ACTIVITY_HEARTBEAT_INTERVAL_SECONDS = 15" in worker_source


@pytest.mark.asyncio
async def test_long_processing_operation_heartbeats_and_honors_cancellation() -> None:
    processing_worker = pytest.importorskip("twobrain_rec_server.workflows.worker")
    operation_cancelled = asyncio.Event()

    class FakeActivity:
        def __init__(self) -> None:
            self.cancelled = False
            self.heartbeats: list[dict[str, str]] = []

        def heartbeat(self, details: dict[str, str]) -> None:
            self.heartbeats.append(details)

        def is_cancelled(self) -> bool:
            return self.cancelled

    activity_context = FakeActivity()

    async def long_operation() -> None:
        try:
            await asyncio.Event().wait()
        finally:
            operation_cancelled.set()

    task = asyncio.create_task(
        processing_worker._await_processing_operation(
            long_operation(),
            activity_context=activity_context,
            state="submitting",
            meeting_id="meeting-1",
            heartbeat_interval_seconds=0.01,
        )
    )
    await asyncio.sleep(0)
    activity_context.cancelled = True

    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=1)

    assert operation_cancelled.is_set()
    assert activity_context.heartbeats == [{"state": "submitting", "meeting_id": "meeting-1"}]


@pytest.mark.asyncio
async def test_provider_egress_finishes_after_caller_cancellation() -> None:
    submit_module = pytest.importorskip("twobrain_rec_server.processing.submit")
    release_egress = asyncio.Event()
    operation_finished = asyncio.Event()

    async def bounded_egress() -> None:
        await release_egress.wait()
        operation_finished.set()

    task = asyncio.create_task(submit_module._await_provider_egress(bounded_egress()))
    await asyncio.sleep(0)
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    release_egress.set()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert operation_finished.is_set()


@pytest.mark.asyncio
async def test_worker_failure_stops_siblings_before_shared_resource_cleanup() -> None:
    processing_worker = pytest.importorskip("twobrain_rec_server.workflows.worker")
    sibling_stopped = asyncio.Event()

    class FailedWorker:
        async def run(self) -> None:
            await asyncio.sleep(0)
            raise RuntimeError("worker failed")

    class SiblingWorker:
        async def run(self) -> None:
            try:
                await asyncio.Event().wait()
            finally:
                sibling_stopped.set()

    with pytest.raises(RuntimeError, match="worker failed"):
        await processing_worker._run_temporal_workers([FailedWorker(), SiblingWorker()])

    assert sibling_stopped.is_set()
