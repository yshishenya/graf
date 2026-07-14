from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from temporalio.api.enums.v1 import TaskQueueType

from twobrain_rec_server.config import Settings
from twobrain_rec_server.normalization.worker_readiness import (
    WORKER_READINESS_SCHEMA_VERSION,
    build_worker_readiness_receipt,
    playback_normalization_readiness_task_queue,
    playback_normalization_worker_identity,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
READINESS_SCRIPT = REPO_ROOT / "apps/server/scripts/verify_playback_normalization_worker_ready.py"


def _load_readiness_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "verify_playback_normalization_worker_ready",
        READINESS_SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_worker_identity_and_receipt_are_bounded_metadata_only() -> None:
    identity = playback_normalization_worker_identity("container/$unsafe")
    receipt = build_worker_readiness_receipt(
        {"probe_id": "11111111-1111-4111-8111-111111111111"},
        hostname="container/$unsafe",
    )

    assert identity == "graf-playback-normalization:container-unsafe"
    assert (
        playback_normalization_readiness_task_queue("twobrain-rec-playback-normalization")
        == "twobrain-rec-playback-normalization-readiness"
    )
    assert receipt == {
        "schema_version": WORKER_READINESS_SCHEMA_VERSION,
        "probe_id": "11111111-1111-4111-8111-111111111111",
        "worker_identity": identity,
        "profile_version": "review_m4a_aac_lc_48k_mono_64k_v1",
        "validation_version": "playback_validator_v1",
    }
    with pytest.raises(ValueError, match="payload is invalid"):
        build_worker_readiness_receipt(
            {
                "probe_id": "11111111-1111-4111-8111-111111111111",
                "meeting_id": "private",
            },
            hostname="container",
        )


@pytest.mark.anyio
async def test_poller_readiness_requires_same_worker_for_workflow_and_activity() -> None:
    script = _load_readiness_script()
    expected_identity = playback_normalization_worker_identity("container-a")

    class WorkflowService:
        def __init__(self, missing_type: int | None = None) -> None:
            self.missing_type = missing_type
            self.calls: list[int] = []

        async def describe_task_queue(self, request, *, timeout):
            assert timeout.total_seconds() == 5
            self.calls.append(request.task_queue_type)
            pollers = (
                []
                if request.task_queue_type == self.missing_type
                else [SimpleNamespace(identity=expected_identity)]
            )
            return SimpleNamespace(pollers=pollers)

    settings = Settings(
        playback_normalization_enabled=True,
        temporal_address="temporal:7233",
    )
    ready_service = WorkflowService()
    await script.verify_worker_pollers(
        temporal_client=SimpleNamespace(workflow_service=ready_service),
        settings=settings,
        expected_worker_identity=expected_identity,
    )
    assert ready_service.calls == [
        TaskQueueType.TASK_QUEUE_TYPE_WORKFLOW,
        TaskQueueType.TASK_QUEUE_TYPE_ACTIVITY,
    ]

    with pytest.raises(RuntimeError, match="poller is not ready"):
        await script.verify_worker_pollers(
            temporal_client=SimpleNamespace(
                workflow_service=WorkflowService(TaskQueueType.TASK_QUEUE_TYPE_ACTIVITY)
            ),
            settings=settings,
            expected_worker_identity=expected_identity,
        )


@pytest.mark.anyio
async def test_control_probe_requires_exact_worker_receipt() -> None:
    script = _load_readiness_script()
    expected_identity = playback_normalization_worker_identity("container-a")

    class TemporalClient:
        async def execute_workflow(self, _workflow, payload, **kwargs):
            assert kwargs["task_queue"] == "twobrain-rec-playback-normalization-readiness"
            return build_worker_readiness_receipt(payload, hostname="container-a")

    result = await script.run_control_probe(
        temporal_client=TemporalClient(),
        settings=Settings(
            playback_normalization_enabled=True,
            temporal_address="temporal:7233",
        ),
        expected_worker_identity=expected_identity,
    )

    assert result["worker_identity"] == expected_identity
    assert result["schema_version"] == WORKER_READINESS_SCHEMA_VERSION
