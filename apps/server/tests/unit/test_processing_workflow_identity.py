from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from temporalio.client import WorkflowExecutionStatus
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from tests.fakes.fake_temporal import FakeTemporalClient
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.lifecycle import processing_start_reconciliation_due
from twobrain_rec_server.processing.store import ProcessingLifecycleBlocked
from twobrain_rec_server.workflows import worker as processing_worker
from twobrain_rec_server.workflows.temporal_client import (
    processing_workflow_id,
    start_processing_workflow,
)


def test_processing_workflow_id_uses_media_revision_id() -> None:
    media_revision_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    assert (
        processing_workflow_id(media_revision_id=media_revision_id)
        == f"processing/{media_revision_id}"
    )


def test_manual_check_command_id_deduplicates_one_version_only() -> None:
    identity = {
        "workspace_id": UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
        "meeting_id": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        "media_revision_id": UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        "workflow_id": "processing/cccccccc-cccc-cccc-cccc-cccccccccccc",
        "command_key": "client-command",
    }

    first = store._processing_manual_command_id(**identity, command_version=1)
    assert first == store._processing_manual_command_id(**identity, command_version=1)
    assert first != store._processing_manual_command_id(**identity, command_version=2)


def test_only_stale_start_intents_are_due_for_reconciliation() -> None:
    now = datetime(2026, 8, 27, 12, tzinfo=UTC)

    assert processing_start_reconciliation_due(
        status="starting",
        updated_at=now - timedelta(minutes=1),
        now=now,
    )
    assert not processing_start_reconciliation_due(
        status="workflow_started",
        updated_at=now - timedelta(seconds=59),
        now=now,
    )
    assert not processing_start_reconciliation_due(
        status="polling",
        updated_at=now - timedelta(days=1),
        now=now,
    )
    assert not processing_start_reconciliation_due(
        status="workflow_started",
        updated_at=now - timedelta(minutes=14),
        now=now,
        workflow_run_id="run-known",
    )
    assert processing_start_reconciliation_due(
        status="polling",
        updated_at=now - timedelta(minutes=15),
        now=now,
        workflow_run_id="run-known",
    )


def test_start_processing_workflow_payload_carries_media_revision_id(test_settings) -> None:
    processing_workflow_row_id = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    meeting_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    media_revision_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    workspace_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    temporal = FakeTemporalClient()

    started = asyncio.run(
        start_processing_workflow(
            temporal_client=temporal,
            settings=test_settings,
            processing_workflow_row_id=processing_workflow_row_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
            workspace_id=workspace_id,
        )
    )

    assert started.workflow_id == f"processing/{media_revision_id}"
    payload = temporal.starts[started.workflow_id]["payload"]
    assert payload["processing_workflow_id"] == str(processing_workflow_row_id)
    assert payload["meeting_id"] == str(meeting_id)
    assert payload["media_revision_id"] == str(media_revision_id)
    assert payload["workspace_id"] == str(workspace_id)
    assert (
        temporal.starts[started.workflow_id]["options"]["id_reuse_policy"]
        is WorkflowIDReusePolicy.REJECT_DUPLICATE
    )


@pytest.mark.parametrize(
    ("field_name", "mismatched_value"),
    [
        ("workspace_id", UUID("11111111-1111-1111-1111-111111111111")),
        ("meeting_id", UUID("22222222-2222-2222-2222-222222222222")),
        ("media_revision_id", UUID("33333333-3333-3333-3333-333333333333")),
        ("workflow_id", "processing/cccccccc-cccc-cccc-cccc-cccccccccccc/2"),
    ],
)
def test_exact_processing_activity_identity_rejects_lineage_mismatch(
    field_name: str,
    mismatched_value: object,
) -> None:
    processing_workflow_row_id = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    workspace_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    meeting_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    media_revision_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    temporal_workflow_id = f"processing/{media_revision_id}"
    workflow = SimpleNamespace(
        id=processing_workflow_row_id,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        workflow_id=temporal_workflow_id,
    )
    setattr(workflow, field_name, mismatched_value)

    class FakeDb:
        async def scalar(self, _query):
            return workflow

    with pytest.raises(
        ProcessingLifecycleBlocked,
        match="processing_workflow_identity_mismatch",
    ):
        asyncio.run(
            processing_worker._load_processing_workflow_for_activity(
                FakeDb(),
                processing_workflow_id=processing_workflow_row_id,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                temporal_workflow_id=temporal_workflow_id,
                active_only=False,
            )
        )


def test_legacy_activity_cannot_attach_to_newer_attempt(monkeypatch) -> None:
    workspace_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    meeting_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    media_revision_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    newer_workflow = SimpleNamespace(
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        workflow_id=f"processing/{media_revision_id}/2",
    )

    async def get_newer_workflow(*_args, **_kwargs):
        return newer_workflow

    monkeypatch.setattr(store, "get_processing_workflow", get_newer_workflow)
    with pytest.raises(
        ProcessingLifecycleBlocked,
        match="processing_workflow_identity_mismatch",
    ):
        asyncio.run(
            processing_worker._load_processing_workflow_for_activity(
                object(),
                processing_workflow_id=None,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                temporal_workflow_id=f"processing/{media_revision_id}",
                active_only=True,
            )
        )


def test_recovery_can_address_persisted_legacy_workflow_id(test_settings) -> None:
    temporal = FakeTemporalClient()
    legacy_workflow_id = "processing/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    started = asyncio.run(
        start_processing_workflow(
            temporal_client=temporal,
            settings=test_settings,
            processing_workflow_row_id=UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
            meeting_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            media_revision_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
            workspace_id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
            workflow_id=legacy_workflow_id,
        )
    )

    assert started.workflow_id == legacy_workflow_id
    assert list(temporal.starts) == [legacy_workflow_id]


def test_start_processing_workflow_reuses_running_duplicate(test_settings) -> None:
    class RunningDuplicateClient:
        async def start_workflow(self, *_args, **_kwargs):
            raise WorkflowAlreadyStartedError(
                "processing/test", "MediaScribeProcessingWorkflow", run_id="run-1"
            )

        def get_workflow_handle(self, *_args, **_kwargs):
            async def describe():
                return SimpleNamespace(status=WorkflowExecutionStatus.RUNNING)

            return SimpleNamespace(describe=describe)

    started = asyncio.run(
        start_processing_workflow(
            temporal_client=RunningDuplicateClient(),
            settings=test_settings,
            processing_workflow_row_id=UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
            meeting_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            media_revision_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
            workspace_id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
        )
    )

    assert started.reused is True
    assert started.closed is False
    assert started.ambiguous is False
    assert started.run_id == "run-1"


def test_start_processing_workflow_classifies_closed_duplicate(test_settings) -> None:
    class ClosedDuplicateClient:
        async def start_workflow(self, *_args, **_kwargs):
            raise WorkflowAlreadyStartedError(
                "processing/test", "MediaScribeProcessingWorkflow", run_id="run-closed"
            )

        def get_workflow_handle(self, *_args, **_kwargs):
            async def describe():
                return SimpleNamespace(status=WorkflowExecutionStatus.COMPLETED)

            return SimpleNamespace(describe=describe)

    started = asyncio.run(
        start_processing_workflow(
            temporal_client=ClosedDuplicateClient(),
            settings=test_settings,
            processing_workflow_row_id=UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
            meeting_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            media_revision_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
            workspace_id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
        )
    )

    assert started.reused is True
    assert started.closed is True
    assert started.ambiguous is False
    assert started.run_id == "run-closed"


def test_start_processing_workflow_keeps_timeout_outcome_ambiguous(test_settings) -> None:
    class AmbiguousClient:
        async def start_workflow(self, *_args, **_kwargs):
            raise TimeoutError("transport outcome unknown")

    started = asyncio.run(
        start_processing_workflow(
            temporal_client=AmbiguousClient(),
            settings=test_settings,
            processing_workflow_row_id=UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
            meeting_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            media_revision_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
            workspace_id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
        )
    )

    assert started.reused is True
    assert started.closed is False
    assert started.ambiguous is True
    assert started.run_id is None
