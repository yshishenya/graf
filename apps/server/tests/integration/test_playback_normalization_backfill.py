from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import func, select

from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.integration.test_playback_normalization_workflow import (
    FakeManualNormalizationPipeline,
)
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.db.models import (
    IngestAuditEvent,
    MediaRevision,
    Meeting,
    PlaybackBackfillRun,
    PlaybackNormalizationJob,
    SupportIncident,
    TrackArtifact,
)
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    apply_tenant_context,
    apply_tenant_scope,
)
from twobrain_rec_server.ingest.media_revisions import source_fingerprint_sha256
from twobrain_rec_server.normalization.service import (
    inventory_playback_backfill_page,
    run_normalization_job,
)
from twobrain_rec_server.normalization.statuses import (
    CANONICAL_PROFILE_VERSION,
    VALIDATION_VERSION,
    NormalizationReason,
)
from twobrain_rec_server.support.incidents import (
    record_impossible_legacy_normalization_incident,
)


@dataclass(frozen=True, slots=True)
class LegacySeed:
    meeting_id: UUID
    media_revision_id: UUID
    created_at: datetime
    title: str


def _worker_scope() -> TenantScope:
    return TenantScope(
        organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID,
        user_id=USER_ID,
        device_id=DEVICE_ID,
    )


async def _seed_legacy_revision(
    db,
    *,
    ordinal: int,
    created_at: datetime,
    revision_status: str = "accepted",
    source_state: str = "valid",
    playback_candidates: int = 0,
    canonical: bool = False,
) -> LegacySeed:
    await apply_tenant_scope(db, _worker_scope(), context_kind="worker")
    meeting_id = uuid4()
    revision_id = uuid4()
    title = f"Synthetic legacy meeting {ordinal}"
    source_body = f"synthetic-manual-source-{ordinal}".encode()
    source_digest = sha256(source_body).hexdigest()
    manifest_digest = sha256(f"synthetic-manifest-{ordinal}".encode()).hexdigest()
    revision = MediaRevision(
        id=revision_id,
        workspace_id=WORKSPACE_ID,
        meeting_id=meeting_id,
        local_media_revision_id=f"synthetic-legacy-revision-{ordinal}",
        revision_number=1,
        source_kind="manual_upload",
        status=revision_status,
        manifest_sha256=manifest_digest if revision_status == "accepted" else None,
        track_sha256_by_role={"media": source_digest},
        duration_seconds=60,
        immutable=True,
        accepted_at=created_at if revision_status == "accepted" else None,
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(
        Meeting(
            id=meeting_id,
            workspace_id=WORKSPACE_ID,
            created_by_user_id=USER_ID,
            device_id=DEVICE_ID,
            local_recording_id=f"synthetic-legacy-meeting-{ordinal}",
            title=title,
            title_source="manual_upload",
            duration_seconds=60,
            status="ingested_pending_processing",
            processing_status="submitted",
            deletion_state="none",
            created_at=created_at,
            updated_at=created_at,
        )
    )
    await db.flush()
    db.add(revision)
    await db.flush()

    if source_state != "missing":
        db.add(
            TrackArtifact(
                meeting_id=meeting_id,
                media_revision_id=revision_id,
                workspace_id=WORKSPACE_ID,
                track_role="media",
                codec="aac",
                sample_rate_hz=48_000,
                channel_count=1,
                duration_seconds=60,
                byte_length=len(source_body),
                sha256=("f" * 64 if source_state == "mismatch" else source_digest),
                storage_object_key=f"tests/legacy/{ordinal}/source",
                status="stored",
                created_at=created_at,
                updated_at=created_at,
            )
        )

    for candidate_index in range(playback_candidates):
        candidate_body = f"synthetic-playback-{ordinal}-{candidate_index}".encode()
        db.add(
            TrackArtifact(
                meeting_id=meeting_id,
                media_revision_id=revision_id,
                workspace_id=WORKSPACE_ID,
                track_role="playback",
                codec="aac",
                sample_rate_hz=48_000,
                channel_count=1,
                duration_seconds=60,
                byte_length=len(candidate_body),
                sha256=sha256(candidate_body).hexdigest(),
                storage_object_key=f"tests/legacy/{ordinal}/candidate-{candidate_index}",
                status="candidate",
                created_at=created_at,
                updated_at=created_at,
            )
        )

    if canonical:
        fingerprint = source_fingerprint_sha256(
            media_revision_id=revision_id,
            source_kind="manual_upload",
            manifest_sha256=manifest_digest,
            track_sha256_by_role={"media": source_digest},
            duration_seconds=60,
        )
        canonical_body = f"synthetic-canonical-{ordinal}".encode()
        db.add(
            TrackArtifact(
                meeting_id=meeting_id,
                media_revision_id=revision_id,
                workspace_id=WORKSPACE_ID,
                track_role="playback",
                codec="aac",
                sample_rate_hz=48_000,
                channel_count=1,
                duration_seconds=60,
                byte_length=len(canonical_body),
                sha256=sha256(canonical_body).hexdigest(),
                storage_object_key=f"tests/legacy/{ordinal}/canonical",
                status="stored",
                normalization_profile_version=CANONICAL_PROFILE_VERSION,
                validated_at=created_at,
                derivation_kind="uploaded_candidate",
                source_fingerprint_sha256=fingerprint,
                validation_version=VALIDATION_VERSION,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    await db.commit()
    return LegacySeed(
        meeting_id=meeting_id,
        media_revision_id=revision_id,
        created_at=created_at,
        title=title,
    )


def test_backfill_records_zero_eligible_workspace_and_reuses_completed_run(client) -> None:
    now = datetime(2026, 7, 14, 8, 0, tzinfo=UTC)

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            await _seed_legacy_revision(
                db,
                ordinal=1,
                created_at=now,
                revision_status="pending_upload",
            )
            first = await inventory_playback_backfill_page(
                db,
                workspace_id=WORKSPACE_ID,
                page_size=100,
                now=now,
            )
            second = await inventory_playback_backfill_page(
                db,
                workspace_id=WORKSPACE_ID,
                page_size=100,
                now=now + timedelta(minutes=1),
            )
            run_count = await db.scalar(select(func.count()).select_from(PlaybackBackfillRun))
            audit_count = await db.scalar(
                select(func.count())
                .select_from(IngestAuditEvent)
                .where(IngestAuditEvent.event_type == "playback_backfill_inventory_completed")
            )
            run = await db.get(PlaybackBackfillRun, first.run_id)
            return first, second, run_count, audit_count, run

    first, second, run_count, audit_count, run = __import__("asyncio").run(exercise())
    assert first.inventory_completed is True
    assert second.reused_completed is True
    assert first.run_id == second.run_id
    assert run_count == 1
    assert audit_count == 1
    assert run.state == "complete"
    assert run.inventory_completed_at is not None
    assert run.completed_at is not None
    assert run.evaluated_count == 0


def test_legacy_completion_persists_one_backfilled_audit_event(client, tmp_path: Path) -> None:
    now = datetime(2026, 7, 14, 8, 30, tzinfo=UTC)

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            seed = await _seed_legacy_revision(db, ordinal=9, created_at=now)
            source_key = "tests/legacy/9/source"
            client.app_state["storage"].put_bytes(
                source_key,
                b"synthetic-manual-source-9",
            )
            await inventory_playback_backfill_page(
                db,
                workspace_id=WORKSPACE_ID,
                page_size=100,
                now=now + timedelta(minutes=1),
            )
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.media_revision_id == seed.media_revision_id
                )
            )
            assert job is not None
            await run_normalization_job(
                db=db,
                storage=client.app_state["storage"],
                job_id=job.id,
                work_directory=tmp_path,
                pipeline=FakeManualNormalizationPipeline(),
            )
            events = list(
                await db.scalars(
                    select(IngestAuditEvent).where(
                        IngestAuditEvent.meeting_id == seed.meeting_id,
                        IngestAuditEvent.event_type.in_(
                            (
                                "playback_normalization_completed",
                                "playback_normalization_backfilled",
                            )
                        ),
                    )
                )
            )
            return await db.get(PlaybackNormalizationJob, job.id), events

    job, events = __import__("asyncio").run(exercise())
    event_types = [event.event_type for event in events]
    assert job.state == "ready"
    assert event_types.count("playback_normalization_completed") == 1
    assert event_types.count("playback_normalization_backfilled") == 1


def test_backfill_inventory_plans_every_safe_action_before_mutation(client) -> None:
    now = datetime(2026, 7, 14, 9, 0, tzinfo=UTC)

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            seeds = [
                await _seed_legacy_revision(
                    db,
                    ordinal=10,
                    created_at=now,
                    source_state="missing",
                    canonical=True,
                ),
                await _seed_legacy_revision(
                    db,
                    ordinal=11,
                    created_at=now + timedelta(seconds=1),
                    playback_candidates=1,
                ),
                await _seed_legacy_revision(
                    db,
                    ordinal=12,
                    created_at=now + timedelta(seconds=2),
                ),
                await _seed_legacy_revision(
                    db,
                    ordinal=13,
                    created_at=now + timedelta(seconds=3),
                    playback_candidates=2,
                ),
                await _seed_legacy_revision(
                    db,
                    ordinal=14,
                    created_at=now + timedelta(seconds=4),
                    source_state="missing",
                ),
                await _seed_legacy_revision(
                    db,
                    ordinal=15,
                    created_at=now + timedelta(seconds=5),
                    source_state="mismatch",
                ),
            ]
            result = await inventory_playback_backfill_page(
                db,
                workspace_id=WORKSPACE_ID,
                page_size=100,
                now=now + timedelta(minutes=1),
            )
            jobs = list(
                await db.scalars(
                    select(PlaybackNormalizationJob).order_by(
                        PlaybackNormalizationJob.media_revision_id
                    )
                )
            )
            run = await db.get(PlaybackBackfillRun, result.run_id)
            meetings = list(
                await db.scalars(
                    select(Meeting).where(Meeting.id.in_([seed.meeting_id for seed in seeds]))
                )
            )
            audits = list(
                await db.scalars(
                    select(IngestAuditEvent).where(
                        IngestAuditEvent.event_type == "playback_backfill_inventory_planned"
                    )
                )
            )
            lifecycle_audits = list(
                await db.scalars(
                    select(IngestAuditEvent).where(
                        IngestAuditEvent.event_type.like("playback_normalization_%")
                    )
                )
            )
            incidents = list(
                await db.scalars(
                    select(SupportIncident).where(
                        SupportIncident.problem_code
                        == "playback_normalization.legacy_source_unavailable"
                    )
                )
            )
            return (
                seeds,
                result,
                jobs,
                run,
                meetings,
                audits,
                lifecycle_audits,
                incidents,
            )

    seeds, result, jobs, run, meetings, audits, lifecycle_audits, incidents = __import__(
        "asyncio"
    ).run(exercise())
    by_revision = {job.media_revision_id: job for job in jobs}
    assert result.evaluated == 6
    assert result.inventory_completed is True
    assert run.state == "dispatching"
    assert run.evaluated_count == 6
    assert run.preserve_valid_count == 1
    assert run.validate_candidate_count == 1
    assert run.normalize_source_count == 2
    assert run.unavailable_source_count == 2
    assert by_revision[seeds[0].media_revision_id].planned_action == "preserve_valid"
    assert by_revision[seeds[0].media_revision_id].state == "ready"
    assert by_revision[seeds[1].media_revision_id].planned_action == "validate_candidate"
    assert by_revision[seeds[2].media_revision_id].planned_action == "normalize_source"
    assert by_revision[seeds[3].media_revision_id].planned_action == "normalize_source"
    assert by_revision[seeds[4].media_revision_id].planned_action == "unavailable_source"
    assert by_revision[seeds[4].media_revision_id].reason_code == "source_missing"
    assert by_revision[seeds[5].media_revision_id].planned_action == "unavailable_source"
    assert by_revision[seeds[5].media_revision_id].reason_code == "source_mismatch"
    assert all(job.trigger_kind == "legacy_backfill" for job in jobs)
    assert all(job.priority_class == "legacy_backfill" for job in jobs)
    assert {meeting.title for meeting in meetings} == {seed.title for seed in seeds}
    assert len(audits) == 6
    assert all(
        set(event.metadata_json)
        <= {"profile_version", "state", "trigger_kind", "planned_action", "reason_code"}
        for event in audits
    )
    lifecycle_event_types = [event.event_type for event in lifecycle_audits]
    assert lifecycle_event_types.count("playback_normalization_requested") == 6
    assert lifecycle_event_types.count("playback_normalization_skipped") == 3
    assert (
        lifecycle_event_types.count("playback_normalization_legacy_source_unavailable")
        == 2
    )
    assert len(incidents) == 2
    assert {incident.failure_category for incident in incidents} == {
        "source_missing",
        "source_mismatch",
    }
    assert all(incident.retry_class == "terminal" for incident in incidents)
    assert all(
        incident.latest_safe_report_json["redaction_state"] == "metadata_only"
        for incident in incidents
    )

    async def replay_impossible_incident():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.media_revision_id == seeds[4].media_revision_id
                )
            )
            assert job is not None
            first = await record_impossible_legacy_normalization_incident(
                db=db,
                job=job,
                reason_code=NormalizationReason.SOURCE_MISSING,
                recorded_at=datetime(2026, 7, 14, 12, 0, tzinfo=UTC),
            )
            second = await record_impossible_legacy_normalization_incident(
                db=db,
                job=job,
                reason_code=NormalizationReason.SOURCE_MISSING,
                recorded_at=datetime(2026, 7, 14, 12, 1, tzinfo=UTC),
            )
            await db.commit()
            count = await db.scalar(
                select(func.count(SupportIncident.id)).where(
                    SupportIncident.problem_code
                    == "playback_normalization.legacy_source_unavailable"
                )
            )
            return first, second, count

    first_replay, second_replay, incident_count = __import__("asyncio").run(
        replay_impossible_incident()
    )
    assert first_replay.created is False
    assert second_replay.created is False
    assert incident_count == 2


def test_completed_profile_run_reopens_only_for_a_later_eligible_watermark(client) -> None:
    now = datetime(2026, 7, 14, 9, 30, tzinfo=UTC)

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            first_seed = await _seed_legacy_revision(
                db,
                ordinal=20,
                created_at=now,
                source_state="missing",
            )
            first = await inventory_playback_backfill_page(
                db,
                workspace_id=WORKSPACE_ID,
                page_size=100,
                now=now + timedelta(minutes=1),
            )
            reused = await inventory_playback_backfill_page(
                db,
                workspace_id=WORKSPACE_ID,
                page_size=100,
                now=now + timedelta(minutes=2),
            )
            second_seed = await _seed_legacy_revision(
                db,
                ordinal=21,
                created_at=now + timedelta(minutes=3),
                source_state="missing",
            )
            reopened = await inventory_playback_backfill_page(
                db,
                workspace_id=WORKSPACE_ID,
                page_size=100,
                now=now + timedelta(minutes=4),
            )
            run = await db.get(PlaybackBackfillRun, first.run_id)
            jobs = list(await db.scalars(select(PlaybackNormalizationJob)))
            return first_seed, second_seed, first, reused, reopened, run, jobs

    first_seed, second_seed, first, reused, reopened, run, jobs = __import__("asyncio").run(
        exercise()
    )
    assert first.state == "complete"
    assert reused.reused_completed is True
    assert reopened.run_id == first.run_id
    assert reopened.evaluated == 1
    assert reopened.inventory_completed is True
    assert reopened.state == "complete"
    assert run.evaluated_count == 2
    assert run.unavailable_source_count == 2
    assert run.terminal_count == 2
    assert {job.media_revision_id for job in jobs} == {
        first_seed.media_revision_id,
        second_seed.media_revision_id,
    }


def test_backfill_persists_page_100_cursor_and_blocks_dispatch_until_inventory_complete(
    client,
) -> None:
    from twobrain_rec_server.normalization.pickup import enumerate_normalization_pickup_candidates

    now = datetime(2026, 7, 14, 10, 0, tzinfo=UTC)

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            for ordinal in range(101):
                await _seed_legacy_revision(
                    db,
                    ordinal=1000 + ordinal,
                    created_at=now + timedelta(seconds=ordinal),
                )
            first = await inventory_playback_backfill_page(
                db,
                workspace_id=WORKSPACE_ID,
                page_size=100,
                now=now + timedelta(minutes=3),
            )
            run_after_first = await db.get(PlaybackBackfillRun, first.run_id)
            first_cursor = (
                run_after_first.cursor_created_at,
                run_after_first.cursor_media_revision_id,
            )
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="playback_normalization_dispatch",
                    actor_id="test-worker",
                    reason_category="test",
                    feature_area="playback_normalization",
                ),
            )
            before_complete = await enumerate_normalization_pickup_candidates(
                db,
                now=now + timedelta(minutes=3),
                batch_size=25,
            )

        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_scope(db, _worker_scope(), context_kind="worker")
            second = await inventory_playback_backfill_page(
                db,
                workspace_id=WORKSPACE_ID,
                page_size=100,
                now=now + timedelta(minutes=4),
            )
            run_after_second = await db.get(PlaybackBackfillRun, second.run_id)
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="playback_normalization_dispatch",
                    actor_id="test-worker",
                    reason_category="test",
                    feature_area="playback_normalization",
                ),
            )
            after_complete = await enumerate_normalization_pickup_candidates(
                db,
                now=now + timedelta(minutes=4),
                batch_size=25,
            )
            job_count = await db.scalar(select(func.count()).select_from(PlaybackNormalizationJob))
            return (
                first,
                second,
                first_cursor,
                before_complete,
                after_complete,
                run_after_second,
                job_count,
            )

    (
        first,
        second,
        first_cursor,
        before_complete,
        after_complete,
        run,
        job_count,
    ) = __import__("asyncio").run(exercise())
    assert first.evaluated == 100
    assert first.inventory_completed is False
    assert first_cursor[0] is not None and first_cursor[1] is not None
    assert before_complete == []
    assert second.evaluated == 1
    assert second.inventory_completed is True
    assert run.inventory_completed_at is not None
    assert run.evaluated_count == 101
    assert job_count == 101
    assert len(after_complete) == 25
