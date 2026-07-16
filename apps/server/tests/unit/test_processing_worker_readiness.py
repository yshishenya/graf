from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from temporalio.api.enums.v1 import TaskQueueType

from twobrain_rec_server.config import Settings
from twobrain_rec_server.workflows.temporal_client import processing_worker_identity

REPO_ROOT = Path(__file__).resolve().parents[4]
READINESS_SCRIPT = REPO_ROOT / "apps/server/scripts/verify_processing_worker_ready.py"


def _load_readiness_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "verify_processing_worker_ready",
        READINESS_SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_processing_worker_identity_is_bounded_metadata_only() -> None:
    assert processing_worker_identity("container/$unsafe") == "graf-processing:container-unsafe"
    with pytest.raises(RuntimeError, match="hostname is unavailable"):
        processing_worker_identity("/$")


@pytest.mark.anyio
async def test_processing_readiness_requires_same_worker_for_both_pollers() -> None:
    script = _load_readiness_script()
    expected_identity = processing_worker_identity("container-a")

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

    settings = Settings(temporal_address="temporal:7233")
    ready_service = WorkflowService()
    await script.verify_processing_worker_pollers(
        temporal_client=SimpleNamespace(workflow_service=ready_service),
        settings=settings,
        expected_worker_identity=expected_identity,
    )
    assert ready_service.calls == [
        TaskQueueType.TASK_QUEUE_TYPE_WORKFLOW,
        TaskQueueType.TASK_QUEUE_TYPE_ACTIVITY,
    ]

    with pytest.raises(RuntimeError, match="poller is not ready"):
        await script.verify_processing_worker_pollers(
            temporal_client=SimpleNamespace(
                workflow_service=WorkflowService(TaskQueueType.TASK_QUEUE_TYPE_ACTIVITY)
            ),
            settings=settings,
            expected_worker_identity=expected_identity,
        )
