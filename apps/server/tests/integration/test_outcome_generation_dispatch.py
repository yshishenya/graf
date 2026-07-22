from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from twobrain_rec_server.config import Settings
from twobrain_rec_server.workflows.temporal_client import (
    outcome_generation_workflow_id,
    start_outcome_generation_workflow,
)


class _AlreadyStartedError(RuntimeError):
    pass


class _Handle:
    run_id = None
    result_run_id = "run-1"


class _TemporalClient:
    def __init__(self, *, already_started: bool = False) -> None:
        self.already_started = already_started
        self.calls: list[tuple[object, dict[str, str], dict[str, object]]] = []

    async def start_workflow(self, workflow, payload, **kwargs):
        self.calls.append((workflow, payload, kwargs))
        if self.already_started:
            raise _AlreadyStartedError("already started")
        return _Handle()


@pytest.mark.anyio
async def test_candidate_dispatch_uses_deterministic_id_and_plaintext_identifiers() -> None:
    candidate_id = UUID("11111111-1111-1111-1111-111111111111")
    client = _TemporalClient()

    started = await start_outcome_generation_workflow(
        temporal_client=client,
        settings=Settings(temporal_task_queue="graf-processing"),
        candidate_id=candidate_id,
        meeting_id=UUID("22222222-2222-2222-2222-222222222222"),
        workspace_id=UUID("33333333-3333-3333-3333-333333333333"),
        source_result_id=UUID("44444444-4444-4444-4444-444444444444"),
        template_key="graf-auto-v1",
        template_version=1,
        prompt_name="graf/meeting-outcome/auto",
    )

    assert started.workflow_id == outcome_generation_workflow_id(candidate_id)
    assert started.run_id == "run-1"
    assert started.reused is False
    _, payload, options = client.calls[0]
    assert payload["candidate_id"] == str(candidate_id)
    assert payload["prompt_name"] == "graf/meeting-outcome/auto"
    assert options["id"] == f"outcome-generation/{candidate_id}"
    assert options["task_queue"] == "graf-processing-outcomes"


@pytest.mark.anyio
async def test_duplicate_candidate_dispatch_reuses_existing_workflow() -> None:
    candidate_id = UUID("11111111-1111-1111-1111-111111111111")
    client = _TemporalClient(already_started=True)

    started = await start_outcome_generation_workflow(
        temporal_client=client,
        settings=Settings(),
        candidate_id=candidate_id,
        meeting_id=UUID("22222222-2222-2222-2222-222222222222"),
        workspace_id=UUID("33333333-3333-3333-3333-333333333333"),
        source_result_id=UUID("44444444-4444-4444-4444-444444444444"),
        template_key="graf-auto-v1",
        template_version=1,
        prompt_name="graf/meeting-outcome/auto",
    )

    assert started.workflow_id == f"outcome-generation/{candidate_id}"
    assert started.reused is True
    assert started.run_id is None


@pytest.mark.anyio
async def test_temporal_converter_accepts_mixed_payload_with_any_type_hint() -> None:
    from typing import Any

    from temporalio.converter import DataConverter

    payload = {"candidate_id": "candidate", "chunk_index": 0, "enabled": True}
    encoded = await DataConverter.default.encode([payload])

    assert await DataConverter.default.decode(encoded, [dict[str, Any]]) == [payload]


def test_ai_temporal_boundaries_never_annotate_mixed_payload_as_object() -> None:
    paths = (
        Path("src/twobrain_rec_server/workflows/worker.py"),
        Path("src/twobrain_rec_server/workflows/prompt_optimization_workflow.py"),
        Path("src/twobrain_rec_server/workflows/prompt_rollback_workflow.py"),
        Path("src/twobrain_rec_server/outcomes/prompt_optimization.py"),
    )

    for path in paths:
        assert "payload: dict[str, object]" not in path.read_text(encoding="utf-8")
