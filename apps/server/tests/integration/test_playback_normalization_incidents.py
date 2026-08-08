from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from tests.fixtures.processing import apply_job_worker_scope
from tests.integration.test_playback_normalization_finalize import (
    _accept_first_party_recording,
)
from twobrain_rec_server.db.models import PlaybackNormalizationJob, SupportIncident
from twobrain_rec_server.normalization.service import record_normalization_failure
from twobrain_rec_server.normalization.statuses import NormalizationReason


def test_cycle_exhaustion_incident_is_metadata_only_and_deduplicated(client) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-incident-dedupe",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    now = datetime(2026, 7, 14, 15, 0, tzinfo=UTC)

    async def fail_twice():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            await apply_job_worker_scope(db, job)
            job.state = "running"
            job.attempt_count = 4
            job.cycle_attempt_count = 4
            await db.commit()
            first = await record_normalization_failure(
                db,
                job_id=job.id,
                reason_code=NormalizationReason.GENERATED_OUTPUT_INVALID,
                failed_at=now,
            )
            second = await record_normalization_failure(
                db,
                job_id=job.id,
                reason_code=NormalizationReason.GENERATED_OUTPUT_INVALID,
                failed_at=now,
            )
            incidents = list(
                await db.scalars(
                    select(SupportIncident).where(
                        SupportIncident.workspace_id == job.workspace_id,
                        SupportIncident.problem_code
                        == "playback_normalization.retry_cycle_exhausted",
                    )
                )
            )
            return first, second, incidents

    first, second, incidents = asyncio.run(fail_twice())
    assert first.cycle_exhausted is True
    assert second.cycle_exhausted is True
    assert first.next_attempt_at == second.next_attempt_at
    assert len(incidents) == 1
    incident = incidents[0]
    assert incident.status == "system_recorded"
    assert incident.affected_count == 1
    assert incident.github_issue_number is None
    assert incident.latest_safe_report_json["redaction_state"] == "metadata_only"
    serialized = str(incident.latest_safe_report_json).casefold()
    for forbidden in (
        "filename",
        "object_key",
        "transcript",
        "signed_url",
        "stderr",
        "stdout",
        "audio content",
    ):
        assert forbidden not in serialized
