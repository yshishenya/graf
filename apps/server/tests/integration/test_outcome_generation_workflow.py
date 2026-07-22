from __future__ import annotations

from hashlib import sha256
from types import SimpleNamespace

import pytest

from twobrain_rec_server.workflows import outcome_generation_workflow as workflow_module


@pytest.mark.anyio
async def test_observability_outage_retries_without_replaying_model_inference(monkeypatch) -> None:
    activity_names: list[str] = []
    publish_retry_attempts: list[int] = []

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
        if name == "publish_outcome_observability_activity":
            publish_retry_attempts.append(kwargs["retry_policy"].maximum_attempts)
            return {"state": "confirmed"}
        raise AssertionError(name)

    fake_runtime = SimpleNamespace(execute_activity=execute_activity)
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
    assert activity_names.count("publish_outcome_observability_activity") == 1
    assert publish_retry_attempts == [0]


@pytest.mark.anyio
async def test_exhausted_generation_activity_is_projected_to_failed_state(monkeypatch) -> None:
    activity_names: list[str] = []

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

    fake_runtime = SimpleNamespace(execute_activity=execute_activity)
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


@pytest.mark.anyio
async def test_transcript_snapshot_failure_is_projected_to_failed_state(monkeypatch) -> None:
    activity_names: list[str] = []

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
        SimpleNamespace(execute_activity=execute_activity),
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
