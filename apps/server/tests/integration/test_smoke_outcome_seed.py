from uuid import uuid4

import pytest
from sqlalchemy import func, select

from scripts import seed_smoke_outcome as seeder
from scripts.seed_smoke_identity import seed_identity
from twobrain_rec_server.db.models import (
    MediaRevision,
    MediaScribeJob,
    Meeting,
    TrackArtifact,
    TranscriptSegment,
)
from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context
from twobrain_rec_server.deployment import build_smoke_identity_seed
from twobrain_rec_server.processing.store import ProcessingLifecycleBlocked

RUN_ID = "f275-local-smoke-seed"


async def scope(db):
    await apply_tenant_context(
        db,
        MaintenanceTenantContext(
            operation_name="production_smoke_setup",
            actor_id="test_smoke_outcome_seed",
            reason_category="smoke_setup",
            feature_area="outcomes",
        ),
    )


def media(revision, **overrides):
    values = dict(
        id=uuid4(),
        workspace_id=revision.workspace_id,
        meeting_id=revision.meeting_id,
        media_revision_id=revision.id,
        track_role="media",
        codec="wav-pcm-s16le",
        sample_rate_hz=16000,
        channel_count=1,
        duration_seconds=9,
        byte_length=288044,
        sha256=revision.track_sha256_by_role["media"],
        storage_object_key=f"synthetic/{uuid4()}",
        status="stored",
    )
    return TrackArtifact(**(values | overrides))


@pytest.fixture
async def smoke_rows(client):
    settings = client.app.state.settings
    await seed_identity(settings, RUN_ID, execute=True)
    seed = build_smoke_identity_seed(RUN_ID)
    async with client.app_state["sessionmaker"]() as db:
        await scope(db)
        meeting = Meeting(
            id=uuid4(),
            workspace_id=seed.workspace_id,
            created_by_user_id=seed.user_id,
            device_id=seed.device_id,
            local_recording_id=RUN_ID,
            duration_seconds=9,
            status="ingested_pending_processing",
        )
        db.add(meeting)
        await db.flush()
        revisions = [
            MediaRevision(
                id=uuid4(),
                workspace_id=seed.workspace_id,
                meeting_id=meeting.id,
                local_media_revision_id=f"{RUN_ID}-{number}",
                revision_number=number,
                source_kind="initial_mixed_recording",
                status="accepted",
                immutable=True,
                duration_seconds=9,
                manifest_sha256="c" * 64,
                track_sha256_by_role={"manifest": "c" * 64, "media": digest * 64},
            )
            for number, digest in [(1, "a"), (2, "b")]
        ]
        db.add_all(revisions)
        await db.flush()
        sources = [media(revision) for revision in revisions]
        db.add_all(sources)
        # A positional choice would pick this manifest or the other revision.
        db.add(media(revisions[0], track_role="manifest", codec="json", sample_rate_hz=1))
        db.add(media(revisions[0], track_role="playback", codec="m4a-aac-lc", sample_rate_hz=48000))
        await db.commit()
    return settings, meeting, revisions, sources


async def test_seed_pins_exact_revision_and_persists_single_source(client, smoke_rows):
    settings, meeting, revisions, sources = smoke_rows
    async with client.app_state["sessionmaker"]() as db:
        await scope(db)
        for revision, source in zip(revisions, sources, strict=True):
            assert (await seeder.load_canonical_media(db, revision)).id == source.id
    result = await seeder.seed_outcome(
        settings,
        run_id=RUN_ID,
        meeting_id=meeting.id,
        media_revision_id=revisions[1].id,
        execute=True,
    )
    assert result["status"] == "seeded"
    repeated = await seeder.seed_outcome(
        settings,
        run_id=RUN_ID,
        meeting_id=meeting.id,
        media_revision_id=revisions[1].id,
        execute=True,
    )
    assert repeated["status"] == "reused"
    assert repeated["result_id"] == result["result_id"]
    async with client.app_state["sessionmaker"]() as db:
        await scope(db)
        jobs = (
            await db.scalars(select(MediaScribeJob).where(MediaScribeJob.meeting_id == meeting.id))
        ).all()
        assert len(jobs) == 1
        job = jobs[0]
        assert job.media_revision_id == revisions[1].id
        assert job.source_track_artifact_id == sources[1].id
        assert job.request_mode == "single_track"
        assert job.mic_track_artifact_id is None and job.incoming_track_artifact_id is None
        segments = (
            await db.scalars(
                select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id)
            )
        ).all()
        assert len(segments) == 3
        assert {segment.source_role for segment in segments} == {"mixed"}


async def test_seed_preserves_stale_revision_outcome_fence(client, smoke_rows):
    settings, meeting, revisions, _sources = smoke_rows
    with pytest.raises(ProcessingLifecycleBlocked, match="summary_source_revision_stale"):
        await seeder.seed_outcome(
            settings,
            run_id=RUN_ID,
            meeting_id=meeting.id,
            media_revision_id=revisions[0].id,
            execute=True,
        )
    async with client.app_state["sessionmaker"]() as db:
        await scope(db)
        assert await db.scalar(select(func.count()).select_from(MediaScribeJob)) == 0


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "duplicate",
        "wrong_revision",
        "wrong_meeting",
        "wrong_workspace",
        "purged",
        "codec",
        "checksum",
        "legacy",
    ],
)
async def test_seed_rejects_unavailable_or_ambiguous_source_before_job(client, smoke_rows, damage):
    settings, meeting, revisions, sources = smoke_rows
    async with client.app_state["sessionmaker"]() as db:
        await scope(db)
        source = await db.get(TrackArtifact, sources[0].id)
        if damage == "missing":
            await db.delete(source)
        elif damage == "duplicate":
            db.add(media(revisions[0]))
        elif damage == "wrong_revision":
            source.media_revision_id = revisions[1].id
        elif damage == "wrong_meeting":
            from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID

            other = Meeting(
                id=uuid4(),
                workspace_id=WORKSPACE_ID,
                created_by_user_id=USER_ID,
                device_id=DEVICE_ID,
                local_recording_id="other-smoke",
                duration_seconds=9,
            )
            db.add(other)
            await db.flush()
            source.meeting_id = other.id
        elif damage == "wrong_workspace":
            from tests.fakes.auth_contexts import WORKSPACE_ID

            source.workspace_id = WORKSPACE_ID
        elif damage == "purged":
            source.status = "purged"
        elif damage == "codec":
            source.sample_rate_hz = 48000
        elif damage == "checksum":
            source.sha256 = "d" * 64
        else:
            revision = await db.get(MediaRevision, revisions[0].id)
            revision.source_kind = "initial_recording"
        await db.commit()
    with pytest.raises(RuntimeError, match="smoke_canonical_media"):
        await seeder.seed_outcome(
            settings,
            run_id=RUN_ID,
            meeting_id=meeting.id,
            media_revision_id=revisions[0].id,
            execute=True,
        )
    async with client.app_state["sessionmaker"]() as db:
        await scope(db)
        assert await db.scalar(select(func.count()).select_from(MediaScribeJob)) == 0


async def test_seed_never_substitutes_latest_revision_for_unknown_id(smoke_rows):
    settings, meeting, _revisions, _sources = smoke_rows
    with pytest.raises(RuntimeError, match="smoke_media_revision_unavailable"):
        await seeder.seed_outcome(
            settings, run_id=RUN_ID, meeting_id=meeting.id, media_revision_id=uuid4(), execute=True
        )
