from __future__ import annotations

from hashlib import sha256
from types import SimpleNamespace
from typing import Any, get_type_hints
from uuid import UUID

import pytest
from temporalio.converter import DataConverter

from twobrain_rec_server.workflows import outcome_generation_workflow as workflow_module
from twobrain_rec_server.workflows import temporal_client


def test_child_completion_result_uses_temporal_compatible_type_hint() -> None:
    """A completed child result must decode when the parent applies its event."""
    return_hint = get_type_hints(
        workflow_module.OutcomeObservabilityReconcilerWorkflow.run
    )["return"]
    assert return_hint == dict[str, Any]

    result = {
        "candidate_id": "candidate",
        "candidate_terminal": True,
        "pending_count": 0,
        "published_count": 0,
    }
    payload = DataConverter.default.payload_converter.to_payloads([result])
    assert DataConverter.default.payload_converter.from_payloads(payload, [return_hint]) == [
        result
    ]


def _workflow_runtime(execute_activity, child_starts: list[tuple[dict, dict]]):
    async def start_child_workflow(_workflow_run, payload, **kwargs):
        child_starts.append((payload, kwargs))
        return object()

    return SimpleNamespace(
        execute_activity=execute_activity,
        start_child_workflow=start_child_workflow,
        info=lambda: SimpleNamespace(workflow_id="outcome-generation/candidate", run_id="run-1"),
        patched=lambda _marker: True,
    )


@pytest.mark.anyio
async def test_observability_outage_retries_without_replaying_model_inference(monkeypatch) -> None:
    activity_names: list[str] = []
    child_starts: list[tuple[dict, dict]] = []

    async def execute_activity(name, payload, **kwargs):
        activity_names.append(name)
        snapshot_hash = sha256(b"full transcript").hexdigest()
        if name == "resolve_outcome_prompt_config_activity":
            return {"prompt_hash": "prompt-hash"}
        if name == "snapshot_outcome_transcript_metadata_activity":
            return {
                "candidate_id": payload["candidate_id"],
                "source_result_id": payload["source_result_id"],
                "snapshot_hash": snapshot_hash,
                "chunk_count": 1,
                "transcript_bytes": len("full transcript"),
            }
        if name == "snapshot_outcome_transcript_chunk_activity":
            return {
                "candidate_id": payload["candidate_id"],
                "source_result_id": payload["source_result_id"],
                "snapshot_hash": snapshot_hash,
                "chunk_index": 0,
                "chunk_count": 1,
                "transcript_utf8": "full transcript",
            }
        if name == "execute_outcome_generation_activity":
            return {"generation_call_id": "call", "candidate_state": "ready"}
        raise AssertionError(name)

    fake_runtime = _workflow_runtime(execute_activity, child_starts)
    monkeypatch.setattr(workflow_module, "workflow", fake_runtime)
    payload = {
        "candidate_id": "candidate",
        "meeting_id": "meeting",
        "workspace_id": "workspace",
        "source_result_id": "result",
        "template_key": "graf-auto-v1",
        "template_version": "1",
        "prompt_name": "graf/meeting-outcome/auto",
    }

    result = await workflow_module.OutcomeGenerationWorkflow().run(payload)

    assert result == {"generation_call_id": "call", "candidate_state": "ready"}
    assert activity_names.count("execute_outcome_generation_activity") == 1
    assert "publish_outcome_observability_activity" not in activity_names
    assert child_starts[0][0]["generation_workflow_id"] == "outcome-generation/candidate"
    assert child_starts[0][0]["generation_workflow_run_id"] == "run-1"
    assert child_starts[0][1]["id"] == "outcome-observability/candidate/run-1"
    assert child_starts[0][1]["parent_close_policy"].name == "ABANDON"


@pytest.mark.anyio
async def test_child_start_failure_is_projected_to_terminal_failure_activity(monkeypatch) -> None:
    activity_names: list[str] = []
    finalizer_payloads: list[dict] = []
    child_starts: list[tuple[dict, dict]] = []

    async def execute_activity(name, payload, **_kwargs):
        activity_names.append(name)
        if name == "finalize_outcome_generation_failure_activity":
            finalizer_payloads.append(payload)
            return {"candidate_id": payload["candidate_id"], "status": "failed"}
        raise AssertionError(name)

    runtime = _workflow_runtime(execute_activity, child_starts)

    async def start_child_failure(*_args, **_kwargs):
        raise RuntimeError("child_start_unavailable")

    runtime.start_child_workflow = start_child_failure
    monkeypatch.setattr(workflow_module, "workflow", runtime)
    payload = {
        "candidate_id": "candidate",
        "meeting_id": "meeting",
        "workspace_id": "workspace",
        "source_result_id": "result",
        "template_key": "graf-auto-v1",
        "template_version": "1",
        "prompt_name": "graf/meeting-outcome/auto",
    }

    with pytest.raises(RuntimeError, match="child_start_unavailable"):
        await workflow_module.OutcomeGenerationWorkflow().run(payload)

    assert activity_names == ["finalize_outcome_generation_failure_activity"]
    assert finalizer_payloads == [
        {**payload, "failure_code": "child_start_unavailable", "failure_reason": "child_start_unavailable"}
    ]


@pytest.mark.anyio
async def test_pre_reconciler_history_keeps_legacy_activity_command_order(monkeypatch) -> None:
    activity_names: list[str] = []
    child_starts: list[tuple[dict, dict]] = []
    snapshot_hash = sha256(b"full transcript").hexdigest()

    async def execute_activity(name, payload, **_kwargs):
        activity_names.append(name)
        if name == "resolve_outcome_prompt_config_activity":
            return {"prompt_hash": "prompt-hash"}
        if name == "snapshot_outcome_transcript_metadata_activity":
            return {
                "candidate_id": payload["candidate_id"],
                "source_result_id": payload["source_result_id"],
                "snapshot_hash": snapshot_hash,
                "chunk_count": 1,
                "transcript_bytes": len("full transcript"),
            }
        if name == "snapshot_outcome_transcript_chunk_activity":
            return {
                "candidate_id": payload["candidate_id"],
                "source_result_id": payload["source_result_id"],
                "snapshot_hash": snapshot_hash,
                "chunk_index": 0,
                "chunk_count": 1,
                "transcript_utf8": "full transcript",
            }
        if name == "execute_outcome_generation_activity":
            return {"generation_call_id": "call", "candidate_state": "ready"}
        if name == "publish_outcome_observability_activity":
            assert payload["generation_call_id"] == "call"
            return {"candidate_terminal": True, "pending_count": 0}
        raise AssertionError(name)

    runtime = _workflow_runtime(execute_activity, child_starts)
    runtime.patched = lambda _marker: False
    monkeypatch.setattr(workflow_module, "workflow", runtime)
    payload = {
        "candidate_id": "candidate",
        "meeting_id": "meeting",
        "workspace_id": "workspace",
        "source_result_id": "result",
        "template_key": "graf-auto-v1",
        "template_version": "1",
        "prompt_name": "graf/meeting-outcome/auto",
    }

    result = await workflow_module.OutcomeGenerationWorkflow().run(payload)

    assert result["generation_call_id"] == "call"
    assert child_starts == []
    assert activity_names == [
        "resolve_outcome_prompt_config_activity",
        "snapshot_outcome_transcript_metadata_activity",
        "snapshot_outcome_transcript_chunk_activity",
        "execute_outcome_generation_activity",
        "publish_outcome_observability_activity",
    ]


@pytest.mark.anyio
async def test_exhausted_generation_activity_is_projected_to_failed_state(monkeypatch) -> None:
    activity_names: list[str] = []
    child_starts: list[tuple[dict, dict]] = []

    async def execute_activity(name, payload, **_kwargs):
        activity_names.append(name)
        snapshot_hash = sha256(b"full transcript").hexdigest()
        if name == "resolve_outcome_prompt_config_activity":
            return {"prompt_hash": "prompt-hash"}
        if name == "snapshot_outcome_transcript_metadata_activity":
            return {
                "candidate_id": payload["candidate_id"],
                "source_result_id": payload["source_result_id"],
                "snapshot_hash": snapshot_hash,
                "chunk_count": 1,
                "transcript_bytes": len("full transcript"),
            }
        if name == "snapshot_outcome_transcript_chunk_activity":
            return {
                "candidate_id": payload["candidate_id"],
                "source_result_id": payload["source_result_id"],
                "snapshot_hash": snapshot_hash,
                "chunk_index": 0,
                "chunk_count": 1,
                "transcript_utf8": "full transcript",
            }
        if name == "execute_outcome_generation_activity":
            raise RuntimeError("activity retries exhausted")
        if name == "finalize_outcome_generation_failure_activity":
            return {"candidate_id": payload["candidate_id"], "status": "failed"}
        raise AssertionError(name)

    fake_runtime = _workflow_runtime(execute_activity, child_starts)
    monkeypatch.setattr(workflow_module, "workflow", fake_runtime)
    payload = {
        "candidate_id": "candidate",
        "meeting_id": "meeting",
        "workspace_id": "workspace",
        "source_result_id": "result",
        "template_key": "graf-auto-v1",
        "template_version": "1",
        "prompt_name": "graf/meeting-outcome/auto",
    }

    with pytest.raises(RuntimeError, match="retries exhausted"):
        await workflow_module.OutcomeGenerationWorkflow().run(payload)

    assert activity_names.count("execute_outcome_generation_activity") == 1
    assert activity_names.count("finalize_outcome_generation_failure_activity") == 1
    assert activity_names[-1] == "finalize_outcome_generation_failure_activity"
    assert len(child_starts) == 1


@pytest.mark.anyio
async def test_transcript_snapshot_failure_is_projected_to_failed_state(monkeypatch) -> None:
    activity_names: list[str] = []
    child_starts: list[tuple[dict, dict]] = []

    async def execute_activity(name, payload, **_kwargs):
        activity_names.append(name)
        if name == "resolve_outcome_prompt_config_activity":
            return {"prompt_hash": "prompt-hash"}
        if name == "snapshot_outcome_transcript_metadata_activity":
            raise RuntimeError("snapshot retries exhausted")
        if name == "finalize_outcome_generation_failure_activity":
            return {"candidate_id": payload["candidate_id"], "status": "failed"}
        raise AssertionError(name)

    monkeypatch.setattr(
        workflow_module,
        "workflow",
        _workflow_runtime(execute_activity, child_starts),
    )
    payload = {
        "candidate_id": "candidate",
        "meeting_id": "meeting",
        "workspace_id": "workspace",
        "source_result_id": "result",
        "template_key": "graf-auto-v1",
        "template_version": "1",
        "prompt_name": "graf/meeting-outcome/auto",
    }

    with pytest.raises(RuntimeError, match="snapshot retries exhausted"):
        await workflow_module.OutcomeGenerationWorkflow().run(payload)

    assert "execute_outcome_generation_activity" not in activity_names
    assert activity_names.count("finalize_outcome_generation_failure_activity") == 1
    assert len(child_starts) == 1


@pytest.mark.anyio
async def test_workflow_snapshot_validation_preserves_terminal_failure_code(monkeypatch) -> None:
    activity_names: list[str] = []
    finalizer_payloads: list[dict] = []
    child_starts: list[tuple[dict, dict]] = []

    async def execute_activity(name, payload, **_kwargs):
        activity_names.append(name)
        if name == "resolve_outcome_prompt_config_activity":
            return {"prompt_hash": "prompt-hash"}
        if name == "snapshot_outcome_transcript_metadata_activity":
            return {
                "candidate_id": payload["candidate_id"],
                "source_result_id": payload["source_result_id"],
                "snapshot_hash": "wrong-hash",
                "chunk_count": 1,
                "transcript_bytes": len("full transcript"),
            }
        if name == "snapshot_outcome_transcript_chunk_activity":
            return {
                "candidate_id": payload["candidate_id"],
                "source_result_id": payload["source_result_id"],
                "snapshot_hash": "wrong-hash",
                "chunk_index": 0,
                "chunk_count": 1,
                "transcript_utf8": "full transcript",
            }
        if name == "finalize_outcome_generation_failure_activity":
            finalizer_payloads.append(payload)
            return {"candidate_id": payload["candidate_id"], "status": "failed"}
        raise AssertionError(name)

    monkeypatch.setattr(
        workflow_module,
        "workflow",
        _workflow_runtime(execute_activity, child_starts),
    )
    payload = {
        "candidate_id": "candidate",
        "meeting_id": "meeting",
        "workspace_id": "workspace",
        "source_result_id": "result",
        "template_key": "graf-auto-v1",
        "template_version": "1",
        "prompt_name": "graf/meeting-outcome/auto",
    }

    with pytest.raises(workflow_module.TranscriptSnapshotError, match="hash_invalid"):
        await workflow_module.OutcomeGenerationWorkflow().run(payload)

    assert activity_names[-1] == "finalize_outcome_generation_failure_activity"
    assert finalizer_payloads == [
        {**payload, "failure_code": "outcome_transcript_hash_invalid"}
    ]


@pytest.mark.anyio
async def test_observability_reconciler_waits_then_exits_after_terminal_delivery(
    monkeypatch,
) -> None:
    states = [
        {"candidate_terminal": False, "pending_count": 0, "published_count": 0},
        {"candidate_terminal": True, "pending_count": 0, "published_count": 2},
    ]
    sleeps: list[object] = []
    retry_attempts: list[int] = []

    async def execute_activity(name, _payload, **kwargs):
        assert name == "publish_outcome_observability_activity"
        retry_attempts.append(kwargs["retry_policy"].maximum_attempts)
        return states.pop(0)

    async def sleep(duration):
        sleeps.append(duration)

    monkeypatch.setattr(
        workflow_module,
        "workflow",
        SimpleNamespace(execute_activity=execute_activity, sleep=sleep),
    )
    result = await workflow_module.OutcomeObservabilityReconcilerWorkflow().run(
        {"candidate_id": "candidate", "workspace_id": "workspace"}
    )

    assert result == {"candidate_terminal": True, "pending_count": 0, "published_count": 2}
    assert len(sleeps) == 1
    assert retry_attempts == [0, 0]


@pytest.mark.anyio
async def test_late_completion_is_observability_only_and_never_dispatches_replacement(
    monkeypatch,
) -> None:
    activity_names: list[str] = []
    child_starts: list[tuple[dict, dict]] = []

    async def execute_activity(name, payload, **_kwargs):
        activity_names.append(name)
        snapshot_hash = sha256(b"synthetic transcript").hexdigest()
        if name == "resolve_outcome_prompt_config_activity":
            return {"prompt_hash": "prompt-hash"}
        if name == "snapshot_outcome_transcript_metadata_activity":
            return {
                "candidate_id": payload["candidate_id"],
                "source_result_id": payload["source_result_id"],
                "snapshot_hash": snapshot_hash,
                "chunk_count": 1,
                "transcript_bytes": len("synthetic transcript"),
            }
        if name == "snapshot_outcome_transcript_chunk_activity":
            return {
                "candidate_id": payload["candidate_id"],
                "source_result_id": payload["source_result_id"],
                "snapshot_hash": snapshot_hash,
                "chunk_index": 0,
                "chunk_count": 1,
                "transcript_utf8": "synthetic transcript",
            }
        if name == "execute_outcome_generation_activity":
            # A provider response that arrives after the source fence changed
            # remains retained for observability, not a publication trigger.
            return {
                "generation_call_id": "call",
                "candidate_state": "stale",
                "failure_code": "summary_source_revision_stale",
            }
        if name == "publish_outcome_observability_activity":
            assert payload["generation_call_id"] == "call"
            return {"candidate_terminal": True, "pending_count": 0}
        raise AssertionError(name)

    runtime = _workflow_runtime(execute_activity, child_starts)
    runtime.patched = lambda _marker: False
    monkeypatch.setattr(workflow_module, "workflow", runtime)

    result = await workflow_module.OutcomeGenerationWorkflow().run(
        {
            "candidate_id": "candidate",
            "meeting_id": "meeting",
            "workspace_id": "workspace",
            "source_result_id": "result",
            "template_key": "graf-auto-v1",
            "template_version": "1",
            "prompt_name": "graf/meeting-outcome/auto",
        }
    )

    assert result["candidate_state"] == "stale"
    assert activity_names.count("execute_outcome_generation_activity") == 1
    assert activity_names.count("publish_outcome_observability_activity") == 1
    assert not any("replacement" in name or "ensure" in name for name in activity_names)
    assert child_starts == []


@pytest.mark.anyio
async def test_duplicate_temporal_dispatch_reuses_existing_run_without_new_workflow_identity(
) -> None:
    calls: list[tuple[str, str]] = []

    class WorkflowAlreadyStartedError(Exception):
        run_id = "existing-run"

    class TemporalClient:
        async def start_workflow(self, workflow_run, _payload, *, id, task_queue, id_reuse_policy):
            calls.append((id, task_queue))
            raise WorkflowAlreadyStartedError("already started")

    settings = SimpleNamespace(
        temporal_task_queue="graf",
        langfuse_environment="test",
    )
    candidate_id = UUID("11111111-1111-1111-1111-111111111111")
    start = temporal_client.start_outcome_generation_workflow

    first = await start(
        temporal_client=TemporalClient(),
        settings=settings,
        candidate_id=candidate_id,
        meeting_id=UUID("22222222-2222-2222-2222-222222222222"),
        workspace_id=UUID("33333333-3333-3333-3333-333333333333"),
        source_result_id=UUID("44444444-4444-4444-4444-444444444444"),
        template_key="graf-auto-v1",
        template_version=1,
        prompt_name="graf/meeting-outcome/auto",
    )
    second = await start(
        temporal_client=TemporalClient(),
        settings=settings,
        candidate_id=candidate_id,
        meeting_id=UUID("22222222-2222-2222-2222-222222222222"),
        workspace_id=UUID("33333333-3333-3333-3333-333333333333"),
        source_result_id=UUID("44444444-4444-4444-4444-444444444444"),
        template_key="graf-auto-v1",
        template_version=1,
        prompt_name="graf/meeting-outcome/auto",
    )

    assert first.reused is True and first.run_id == "existing-run"
    assert second.reused is True and second.run_id == "existing-run"
    assert calls == [
        ("outcome-generation/11111111-1111-1111-1111-111111111111", "graf-outcomes"),
        ("outcome-generation/11111111-1111-1111-1111-111111111111", "graf-outcomes"),
    ]


def test_stale_slot_event_identity_is_stable_and_type_scoped() -> None:
    meeting_id = UUID("55555555-5555-5555-5555-555555555555")

    # Summary reads use the same immutable tuple (meeting, type, state version)
    # for Feature 197's later coalescing decision; a workflow identity is not a
    # substitute for that slot event.
    from twobrain_rec_server.api.cabinet import _summary_event_id

    auto_v7 = _summary_event_id(
        meeting_id=meeting_id,
        template_key="graf-auto-v1",
        state_version=7,
    )
    auto_v7_replay = _summary_event_id(
        meeting_id=meeting_id,
        template_key="graf-auto-v1",
        state_version=7,
    )
    minutes_v7 = _summary_event_id(
        meeting_id=meeting_id,
        template_key="graf-meeting-minutes-v1",
        state_version=7,
    )
    auto_v8 = _summary_event_id(
        meeting_id=meeting_id,
        template_key="graf-auto-v1",
        state_version=8,
    )

    assert auto_v7 == auto_v7_replay
    assert auto_v7 != minutes_v7
    assert auto_v7 != auto_v8
