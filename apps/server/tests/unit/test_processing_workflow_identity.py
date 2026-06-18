from __future__ import annotations

import asyncio
from uuid import UUID

from tests.fakes.fake_temporal import FakeTemporalClient
from twobrain_rec_server.workflows.temporal_client import (
    processing_workflow_id,
    start_processing_workflow,
)


def test_processing_workflow_id_uses_media_revision_id() -> None:
    media_revision_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    assert processing_workflow_id(media_revision_id=media_revision_id) == f"processing/{media_revision_id}"


def test_start_processing_workflow_payload_carries_media_revision_id(test_settings) -> None:
    meeting_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    media_revision_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    workspace_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    temporal = FakeTemporalClient()

    started = asyncio.run(
        start_processing_workflow(
            temporal_client=temporal,
            settings=test_settings,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
            workspace_id=workspace_id,
        )
    )

    assert started.workflow_id == f"processing/{media_revision_id}"
    payload = temporal.starts[started.workflow_id]["payload"]
    assert payload["meeting_id"] == str(meeting_id)
    assert payload["media_revision_id"] == str(media_revision_id)
    assert payload["workspace_id"] == str(workspace_id)
