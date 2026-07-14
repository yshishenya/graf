from __future__ import annotations

import asyncio
from uuid import UUID

from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fakes.fake_temporal import FakeTemporalClient
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.normalization.statuses import (
    CANONICAL_PROFILE_VERSION,
    VALIDATION_VERSION,
)
from twobrain_rec_server.workflows.temporal_client import (
    playback_normalization_workflow_id,
    start_playback_normalization_workflow,
)


def test_playback_normalization_workflow_identity_and_payload_are_content_free(
    test_settings,
) -> None:
    meeting_id = UUID("11111111-1111-4111-8111-111111111111")
    revision_id = UUID("22222222-2222-4222-8222-222222222222")
    job_id = UUID("33333333-3333-4333-8333-333333333333")
    tenant_scope = TenantScope(
        organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID,
        user_id=USER_ID,
        device_id=DEVICE_ID,
    )
    temporal = FakeTemporalClient()

    started = asyncio.run(
        start_playback_normalization_workflow(
            temporal_client=temporal,
            settings=test_settings,
            job_id=job_id,
            meeting_id=meeting_id,
            media_revision_id=revision_id,
            tenant_scope=tenant_scope,
            profile_version=CANONICAL_PROFILE_VERSION,
            validation_version=VALIDATION_VERSION,
        )
    )

    expected_id = f"playback-normalization/{revision_id}/v1"
    assert playback_normalization_workflow_id(revision_id) == expected_id
    assert started.workflow_id == expected_id
    payload = temporal.starts[expected_id]["payload"]
    assert payload == {
        "organization_id": str(ORG_ID),
        "workspace_id": str(WORKSPACE_ID),
        "user_id": str(USER_ID),
        "device_id": str(DEVICE_ID),
        "meeting_id": str(meeting_id),
        "media_revision_id": str(revision_id),
        "job_id": str(job_id),
        "profile_version": CANONICAL_PROFILE_VERSION,
        "validation_version": VALIDATION_VERSION,
        "requested_by": "playback-normalization-dispatch",
    }
    serialized = str(payload).lower()
    assert all(
        forbidden not in serialized
        for forbidden in {
            "filename",
            "title",
            "object_key",
            "storage",
            "audio",
            "transcript",
            "content",
            "signed_url",
        }
    )
    assert temporal.starts[expected_id]["task_queue"] == test_settings.playback_normalization_task_queue
