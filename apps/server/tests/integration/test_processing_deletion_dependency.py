import asyncio
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.processing import create_finalized_meeting, create_finalized_mixed_recording
from twobrain_rec_server.db.models import MediaRevision, ProcessingDependencyState, TrackArtifact
from twobrain_rec_server.domain.statuses import (
    ProcessingDependencyName,
    ProcessingDependencyStateValue,
)
from twobrain_rec_server.processing import store


def test_processing_dependency_state_records_future_deletion_truth_without_claiming_delete(client) -> None:
    finalized = create_finalized_meeting(client, "processing-dependency")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def record() -> tuple[str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            await store.set_dependency_state(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                dependency=ProcessingDependencyName.MEDIASCRIBE,
                state=ProcessingDependencyStateValue.DELETION_PENDING_FUTURE,
                external_reference="job_safe_ref",
            )
            state = await db.scalar(
                select(ProcessingDependencyState).where(
                    ProcessingDependencyState.meeting_id == meeting_id,
                    ProcessingDependencyState.dependency == "mediascribe",
                )
            )
            return state.state, state.external_reference

    assert asyncio.run(record()) == ("deletion_pending_future", "job_safe_ref")


def test_v5_deletion_purges_canonical_media_and_review_playback_without_dual_roles(client) -> None:
    finalized = create_finalized_mixed_recording(client, "v5-deletion-boundary")
    meeting_id = UUID(str(finalized["meeting"]["meeting_id"]))

    async def accepted_v5_truth() -> tuple[str, set[str], set[str]]:
        async with client.app_state["sessionmaker"]() as db:
            revision = await db.scalar(
                select(MediaRevision).where(MediaRevision.meeting_id == meeting_id)
            )
            assert revision is not None
            artifacts = (
                await db.scalars(
                    select(TrackArtifact).where(TrackArtifact.media_revision_id == revision.id)
                )
            ).all()
            return (
                revision.source_kind,
                {artifact.track_role for artifact in artifacts},
                {artifact.storage_object_key for artifact in artifacts},
            )

    source_kind, roles, object_keys = asyncio.run(accepted_v5_truth())
    assert source_kind == "initial_mixed_recording"
    assert roles == {"manifest", "media", "playback"}
    assert all(key in client.app_state["storage"].objects for key in object_keys)

    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": "Delete this meeting everywhere GRAF controls."},
    )
    assert response.status_code == 202
    assert all(key not in client.app_state["storage"].objects for key in object_keys)

    async def purged_roles() -> tuple[set[str], set[str]]:
        async with client.app_state["sessionmaker"]() as db:
            artifacts = (
                await db.scalars(
                    select(TrackArtifact).where(TrackArtifact.meeting_id == meeting_id)
                )
            ).all()
            return {artifact.track_role for artifact in artifacts}, {artifact.status for artifact in artifacts}

    assert asyncio.run(purged_roles()) == ({"manifest", "media", "playback"}, {"purged"})
