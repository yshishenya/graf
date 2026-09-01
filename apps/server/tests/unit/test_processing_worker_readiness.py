from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from temporalio.api.enums.v1 import TaskQueueType

from twobrain_rec_server.config import Settings
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.mediascribe.client import MediaScribeClient, MediaScribeClientError
from twobrain_rec_server.workflows.temporal_client import processing_worker_identity
from twobrain_rec_server.workflows.worker import (
    _processing_mediascribe_client,
    _processing_status_for_client_error,
    _processing_status_for_runtime_error,
)

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


def test_malformed_mediascribe_payload_is_terminal_even_if_client_marks_retryable() -> None:
    error = MediaScribeClientError("mediascribe_malformed_response", retryable=True)

    assert _processing_status_for_client_error(error) == ProcessingStatus.FAILED_TERMINAL


def test_known_processing_runtime_failures_have_bounded_classification() -> None:
    blocked = _processing_status_for_runtime_error(RuntimeError("blocked_missing_artifacts"))
    retryable = _processing_status_for_runtime_error(
        RuntimeError("processing_temp_storage_unavailable")
    )

    assert blocked == (ProcessingStatus.BLOCKED, False)
    assert retryable == (ProcessingStatus.FAILED_RETRYABLE, True)
    assert _processing_status_for_runtime_error(RuntimeError("unexpected_worker_bug")) is None


def test_dev_processing_worker_allows_unconfigured_provider_without_network_egress(monkeypatch) -> None:
    settings = Settings(
        env="development",
        processing_enabled=True,
        temporal_address="temporal:7233",
    )

    def blocked_from_settings(_settings, *, reuse_connections=False):
        assert reuse_connections is True
        raise MediaScribeClientError("blocked_config", retryable=False)

    monkeypatch.setattr(MediaScribeClient, "from_settings", blocked_from_settings)

    assert _processing_mediascribe_client(settings) is None


def test_production_processing_worker_does_not_downgrade_provider_config_failure(monkeypatch) -> None:
    settings = SimpleNamespace(env="production")

    def blocked_from_settings(_settings, *, reuse_connections=False):
        raise MediaScribeClientError("blocked_config", retryable=False)

    monkeypatch.setattr(MediaScribeClient, "from_settings", blocked_from_settings)

    with pytest.raises(MediaScribeClientError, match="blocked_config"):
        _processing_mediascribe_client(settings)


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
