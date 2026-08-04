#!/usr/bin/env python3
"""Attach a bounded synthetic transcript to an existing production smoke meeting."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    MediaRevision,
    MediaScribeJob,
    Meeting,
    ProcessingResult,
    ProcessingWorkflow,
    TrackArtifact,
    TranscriptSegment,
)
from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context
from twobrain_rec_server.deployment import build_smoke_identity_seed
from twobrain_rec_server.domain.statuses import (
    MediaScribeJobStatus,
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
)
from twobrain_rec_server.ingest.media_revisions import source_fingerprint_for_revision
from twobrain_rec_server.outcomes.ai_service import ensure_automatic_summary_candidate
from twobrain_rec_server.outcomes.service import ensure_outcomes_for_processing_result

try:
    from scripts.smoke_target import validate_run_id
except ModuleNotFoundError:
    from smoke_target import validate_run_id


async def seed_outcome(settings: Settings, *, run_id: str, meeting_id: UUID, execute: bool) -> dict[str, object]:
    run_id = validate_run_id(run_id)
    seed = build_smoke_identity_seed(run_id)
    if not execute:
        return {"mode": "dry_run", "meeting_id": str(meeting_id), "identity_class": seed.identity_class}

    source_hash = sha256(f"graf-production-smoke-outcome:{run_id}".encode()).hexdigest()
    engine = create_async_engine(settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="production_smoke_setup",
                    actor_id="seed_smoke_outcome.py",
                    reason_category="smoke_setup",
                    feature_area="outcomes",
                ),
            )
            existing = await db.scalar(
                select(ProcessingResult).where(
                    ProcessingResult.workspace_id == seed.workspace_id,
                    ProcessingResult.meeting_id == meeting_id,
                    ProcessingResult.source_result_hash == source_hash,
                )
            )
            if existing is not None:
                candidate = await ensure_automatic_summary_candidate(
                    db, workspace_id=seed.workspace_id, meeting_id=meeting_id
                )
                await db.commit()
                return {
                    "mode": "execute",
                    "meeting_id": str(meeting_id),
                    "result_id": str(existing.id),
                    "candidate_id": str(candidate.candidate_id) if candidate and candidate.candidate_id else None,
                    "status": "reused",
                }

            revision = await db.scalar(
                select(MediaRevision).where(
                    MediaRevision.workspace_id == seed.workspace_id,
                    MediaRevision.meeting_id == meeting_id,
                    MediaRevision.status == "accepted",
                    MediaRevision.immutable.is_(True),
                ).order_by(MediaRevision.revision_number.desc())
            )
            if revision is None:
                raise RuntimeError("smoke_media_revision_unavailable")
            meeting = await db.get(Meeting, meeting_id)
            if meeting is None or meeting.workspace_id != seed.workspace_id:
                raise RuntimeError("smoke_meeting_unavailable")
            artifacts = (
                await db.scalars(
                    select(TrackArtifact)
                    .where(
                        TrackArtifact.workspace_id == seed.workspace_id,
                        TrackArtifact.meeting_id == meeting_id,
                    )
                    .order_by(TrackArtifact.track_role)
                )
            ).all()
            if len(artifacts) < 2:
                raise RuntimeError("smoke_track_artifacts_unavailable")
            now = datetime.now(UTC)
            source_fingerprint = source_fingerprint_for_revision(revision)
            workflow = ProcessingWorkflow(
                workspace_id=seed.workspace_id,
                meeting_id=meeting_id,
                media_revision_id=revision.id,
                workflow_id=f"production-smoke/{run_id}",
                purpose="transcription",
                source_fingerprint=source_fingerprint,
                status="processed",
                attempt_count=1,
                started_at=now,
                ended_at=now,
            )
            db.add(workflow)
            await db.flush()
            job = MediaScribeJob(
                workspace_id=seed.workspace_id,
                meeting_id=meeting_id,
                media_revision_id=revision.id,
                processing_workflow_id=workflow.id,
                idempotency_key=f"production-smoke/{run_id}",
                source_fingerprint=source_fingerprint,
                external_job_id=f"production-smoke-{run_id}",
                status=MediaScribeJobStatus.READY.value,
                mic_track_artifact_id=artifacts[0].id,
                incoming_track_artifact_id=artifacts[1].id,
                submitted_at=now,
                ready_at=now,
            )
            db.add(job)
            await db.flush()
            result = ProcessingResult(
                workspace_id=seed.workspace_id,
                meeting_id=meeting_id,
                media_revision_id=revision.id,
                mediascribe_job_id=job.id,
                processing_workflow_id=workflow.id,
                deletion_epoch_at_start=meeting.deletion_epoch,
                result_version=1,
                status=ProcessingResultStatus.IMPORTED.value,
                transcript_status=ProcessingAvailabilityStatus.AVAILABLE.value,
                diarization_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
                language="en",
                segment_count=3,
                diarization_segment_count=0,
                source_result_hash=source_hash,
                imported_at=now,
            )
            db.add(result)
            await db.flush()
            db.add_all(
                [
                    TranscriptSegment(
                        workspace_id=seed.workspace_id,
                        meeting_id=meeting_id,
                        processing_result_id=result.id,
                        sequence=0,
                        start_seconds=Decimal("0.000"),
                        end_seconds=Decimal("3.000"),
                        text="Synthetic smoke: the team approved the release checklist.",
                        source_role="mic",
                        source_role_original="microphone",
                    ),
                    TranscriptSegment(
                        workspace_id=seed.workspace_id,
                        meeting_id=meeting_id,
                        processing_result_id=result.id,
                        sequence=1,
                        start_seconds=Decimal("3.000"),
                        end_seconds=Decimal("6.000"),
                        text="Synthetic smoke: Alex will publish the checklist tomorrow.",
                        source_role="incoming",
                        source_role_original="system",
                    ),
                    TranscriptSegment(
                        workspace_id=seed.workspace_id,
                        meeting_id=meeting_id,
                        processing_result_id=result.id,
                        sequence=2,
                        start_seconds=Decimal("6.000"),
                        end_seconds=Decimal("9.000"),
                        text="Synthetic smoke: the team will review the result next week.",
                        source_role="mic",
                        source_role_original="microphone",
                    ),
                ]
            )
            await db.flush()
            await ensure_outcomes_for_processing_result(
                db, result=result, publish_initial_baseline=True
            )
            candidate = await ensure_automatic_summary_candidate(
                db, workspace_id=seed.workspace_id, meeting_id=meeting_id
            )
            await db.commit()
            return {
                "mode": "execute",
                "meeting_id": str(meeting_id),
                "result_id": str(result.id),
                "candidate_id": str(candidate.candidate_id) if candidate and candidate.candidate_id else None,
                "status": "seeded",
            }
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a synthetic production outcome smoke result")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--meeting-id", required=True, type=UUID)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(seed_outcome(Settings(), run_id=args.run_id, meeting_id=args.meeting_id, execute=args.execute)), sort_keys=True))


if __name__ == "__main__":
    main()
