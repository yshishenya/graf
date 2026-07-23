from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import pytest
from sqlalchemy import select

from tests.fixtures.cabinet import create_outcome_ready_meeting
from twobrain_rec_server.cabinet.egress import current_outcome_set
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    GenerationCall,
    MediaScribeJob,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeSet,
    ProcessingResult,
)
from twobrain_rec_server.outcomes.ai_service import (
    OutcomeGenerationTerminalError,
    _candidate_segments,
    create_summary_candidate,
    execute_candidate_generation,
    resolve_summary_candidate,
)
from twobrain_rec_server.outcomes.generator import canonical_transcript
from twobrain_rec_server.outcomes.prompts import outcome_config, prompt_snapshot_hash


class _InjectingSessionmaker:
    """Inject a newer source after reservation commit, before the second guard."""

    def __init__(self, actual, inject) -> None:
        self.actual = actual
        self.inject = inject
        self.closed_sessions = 0

    def __call__(self, *args, **kwargs):
        context = self.actual(*args, **kwargs)
        parent = self

        class _Context:
            async def __aenter__(self):
                return await context.__aenter__()

            async def __aexit__(self, exc_type, exc, traceback):
                result = await context.__aexit__(exc_type, exc, traceback)
                parent.closed_sessions += 1
                if parent.closed_sessions == 1:
                    await parent.inject()
                return result

        return _Context()


def test_candidate_request_is_idempotent_and_does_not_replace_accepted_notes(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert meeting is not None
            accepted_before = meeting.current_outcome_set_id
            first = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=accepted_before,
            )
            second = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=accepted_before,
            )
            await db.commit()
            return first.candidate_id, second.candidate_id, meeting.current_outcome_set_id

    first, second, accepted_after = asyncio.run(run())
    assert first == second
    assert accepted_after is None


def test_review_reads_the_accepted_pointer_instead_of_the_newest_outcome(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None
            assert result is not None
            accepted = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=result.media_revision_id,
                processing_result_id=result.id,
                status="available",
                generator_version="accepted-test-v1",
                revision_state="accepted",
            )
            db.add(accepted)
            await db.flush()
            meeting.current_outcome_set_id = accepted.id
            candidate = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=result.media_revision_id,
                processing_result_id=result.id,
                status="available",
                generator_version="newer-candidate-test-v1",
                revision_state="candidate",
            )
            db.add(candidate)
            await db.flush()
            selected = await current_outcome_set(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
            )
            return selected.id if selected is not None else None, accepted.id, candidate.id

    selected_id, accepted_id, candidate_id = asyncio.run(run())

    assert selected_id == accepted_id
    assert selected_id != candidate_id


def test_accept_candidate_is_atomic_and_rejects_stale_expected_revision(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert meeting is not None
            attempt = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=None,
            )
            candidate = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=attempt.media_revision_id,
                processing_result_id=attempt.source_result_id,
                status="available",
                generator_version=f"test:{attempt.candidate_id}",
                revision_state="candidate",
            )
            db.add(candidate)
            await db.flush()
            attempt.outcome_set_id = candidate.id
            attempt.status = "candidate"
            await resolve_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                candidate_id=attempt.candidate_id,
                requested_by_user_id=meeting.created_by_user_id,
                accept=True,
                expected_current_outcome_set_id=None,
            )
            await db.commit()
            accepted_id = meeting.current_outcome_set_id
            accepted_state = candidate.revision_state
            accepted_actor = candidate.accepted_by_user_id
            with pytest.raises(OutcomeGenerationTerminalError, match="conflict"):
                await resolve_summary_candidate(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    candidate_id=attempt.candidate_id,
                    requested_by_user_id=meeting.created_by_user_id,
                    accept=True,
                    expected_current_outcome_set_id=None,
                )
            await db.rollback()
            return accepted_id, accepted_state, accepted_actor

    accepted_id, state, actor = asyncio.run(run())
    assert accepted_id is not None
    assert state == "accepted"
    assert actor is not None


def test_reject_stale_candidate_closes_it_after_a_new_transcript_result(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert meeting is not None
            source = await db.scalar(
                select(ProcessingResult)
                .where(ProcessingResult.meeting_id == meeting_id)
                .order_by(ProcessingResult.imported_at.desc())
            )
            assert source is not None
            attempt = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=None,
            )
            candidate = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=attempt.media_revision_id,
                processing_result_id=attempt.source_result_id,
                status="available",
                generator_version=f"test:{attempt.candidate_id}",
                revision_state="candidate",
            )
            db.add(candidate)
            await db.flush()
            attempt.outcome_set_id = candidate.id
            attempt.status = "candidate"

            job = await db.get(MediaScribeJob, source.mediascribe_job_id)
            assert job is not None
            newer = ProcessingResult(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=source.media_revision_id,
                mediascribe_job_id=job.id,
                result_version=source.result_version + 1,
                status="imported",
                transcript_status="available",
                source_result_hash="new-transcript",
                imported_at=datetime.now(UTC) + timedelta(seconds=1),
            )
            db.add(newer)
            await db.flush()

            await resolve_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                candidate_id=attempt.candidate_id,
                requested_by_user_id=meeting.created_by_user_id,
                accept=False,
                expected_current_outcome_set_id=None,
            )
            await db.commit()
            return attempt.status, attempt.failure_code, candidate.revision_state

    status, failure_code, revision_state = asyncio.run(run())
    assert status == "rejected"
    assert failure_code == "summary_transcript_changed"
    assert revision_state == "rejected"


def test_resolving_an_already_accepted_candidate_cannot_reject_the_current_pointer(
    client,
) -> None:
    meeting_id = create_outcome_ready_meeting(client)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert meeting is not None
            source = await db.scalar(
                select(ProcessingResult)
                .where(ProcessingResult.meeting_id == meeting_id)
                .order_by(ProcessingResult.imported_at.desc())
            )
            assert source is not None
            attempt = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=None,
            )
            candidate = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=attempt.media_revision_id,
                processing_result_id=attempt.source_result_id,
                status="available",
                generator_version=f"test:{attempt.candidate_id}",
                revision_state="candidate",
            )
            db.add(candidate)
            await db.flush()
            attempt.outcome_set_id = candidate.id
            attempt.status = "candidate"
            await resolve_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                candidate_id=attempt.candidate_id,
                requested_by_user_id=meeting.created_by_user_id,
                accept=True,
                expected_current_outcome_set_id=None,
            )
            await db.commit()

            job = await db.get(MediaScribeJob, source.mediascribe_job_id)
            assert job is not None
            db.add(
                ProcessingResult(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    media_revision_id=source.media_revision_id,
                    mediascribe_job_id=job.id,
                    result_version=source.result_version + 1,
                    status="imported",
                    transcript_status="available",
                    source_result_hash="new-transcript",
                    imported_at=datetime.now(UTC) + timedelta(seconds=1),
                )
            )
            await db.flush()
            with pytest.raises(OutcomeGenerationTerminalError, match="unavailable"):
                await resolve_summary_candidate(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    candidate_id=attempt.candidate_id,
                    requested_by_user_id=meeting.created_by_user_id,
                    accept=False,
                    expected_current_outcome_set_id=candidate.id,
                )
            accepted_id = meeting.current_outcome_set_id
            revision_state = candidate.revision_state
            status = attempt.status
            await db.rollback()
            return accepted_id, revision_state, status

    accepted_id, revision_state, status = asyncio.run(run())
    assert accepted_id is not None
    assert revision_state == "accepted"
    assert status == "accepted"


def test_new_source_after_reservation_is_blocked_before_litellm_egress(client, tmp_path, monkeypatch) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    key_path = tmp_path / "litellm-key"
    key_path.write_text("test-key", encoding="utf-8")
    settings = Settings(
        litellm_base_url="https://litellm.example.test",
        litellm_api_key_file=key_path,
    )
    gateway_calls = 0

    async def unexpected_gateway_call(*_args, **_kwargs):
        nonlocal gateway_calls
        gateway_calls += 1
        raise AssertionError("LiteLLM must not receive a stale transcript")

    monkeypatch.setattr(
        "twobrain_rec_server.outcomes.ai_service._read_secret",
        lambda _path: "test-key",
    )
    monkeypatch.setattr(
        "twobrain_rec_server.outcomes.ai_service.LiteLLMGateway.generate",
        unexpected_gateway_call,
    )

    async def run():
        actual = client.app_state["sessionmaker"]
        async with actual() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            source = await db.scalar(
                select(ProcessingResult)
                .where(ProcessingResult.meeting_id == meeting_id)
                .order_by(ProcessingResult.imported_at.desc())
            )
            assert meeting is not None and source is not None
            attempt = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=None,
            )
            prompt = [
                {
                    "role": "system",
                    "content": "{{transcript_json}} {{output_language}} {{detail_level}} {{template_sections_json}}",
                }
            ]
            config = outcome_config(schema_name="graf_outcome")
            attempt.prompt_name = "graf/meeting-outcome/graf-auto-v1"
            attempt.prompt_version = 1
            attempt.prompt_definition = prompt
            attempt.prompt_config = config
            attempt.prompt_source = "verified_promoted_snapshot"
            attempt.prompt_hash = prompt_snapshot_hash(prompt=prompt, config=config)
            transcript_hash = sha256(
                canonical_transcript(await _candidate_segments(db, attempt)).encode("utf-8")
            ).hexdigest()
            attempt.temporal_transcript_hash = transcript_hash
            attempt.status = "generating"
            await db.commit()
            source_result_id = source.id
            candidate_id = attempt.candidate_id
            workspace_id = meeting.workspace_id

        async def inject_new_result() -> None:
            async with actual() as db:
                current = await db.get(ProcessingResult, source_result_id)
                assert current is not None
                job = await db.get(MediaScribeJob, current.mediascribe_job_id)
                assert job is not None
                db.add(
                    ProcessingResult(
                        workspace_id=workspace_id,
                        meeting_id=meeting_id,
                        media_revision_id=current.media_revision_id,
                        mediascribe_job_id=job.id,
                        result_version=current.result_version + 1,
                        status="imported",
                        transcript_status="available",
                        source_result_hash="new-transcript",
                        imported_at=current.imported_at + timedelta(seconds=1),
                    )
                )
                await db.commit()

        sessionmaker = _InjectingSessionmaker(actual, inject_new_result)
        with pytest.raises(OutcomeGenerationTerminalError, match="summary_transcript_changed"):
            await execute_candidate_generation(
                sessionmaker,
                workspace_id=workspace_id,
                candidate_id=candidate_id,
                expected_snapshot_hash=transcript_hash,
                settings=settings,
            )
        async with actual() as db:
            persisted_attempt = await db.scalar(
                select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.candidate_id == candidate_id
                )
            )
            call = await db.scalar(
                select(GenerationCall).where(GenerationCall.candidate_id == candidate_id)
            )
            return persisted_attempt, call

    persisted_attempt, call = asyncio.run(run())
    assert gateway_calls == 0
    assert persisted_attempt is not None
    assert persisted_attempt.failure_code == "summary_transcript_changed"
    assert persisted_attempt.status == "failed"
    assert call is not None
    assert call.call_state == "failed"
