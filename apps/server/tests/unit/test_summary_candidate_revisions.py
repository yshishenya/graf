from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from uuid import uuid4

import pytest
from sqlalchemy import select

from tests.fixtures.cabinet import create_outcome_ready_meeting
from twobrain_rec_server.cabinet.egress import current_outcome_set
from twobrain_rec_server.cabinet.speakers import save_speaker_name
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    GenerationCall,
    MediaScribeJob,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeSet,
    MeetingSpeakerName,
    ProcessingResult,
    SummaryTemplate,
)
from twobrain_rec_server.domain.speaker_turns import stable_speaker_key
from twobrain_rec_server.ingest.desktop_sync import (
    _latest_processing_result as latest_desktop_result,
)
from twobrain_rec_server.outcomes.ai_service import (
    AI_GENERATOR_VERSION,
    OutcomeGenerationTerminalError,
    _candidate_segments,
    _canonical_source_refs,
    _stored_prompt_snapshot,
    create_summary_candidate,
    execute_candidate_generation,
    resolve_summary_candidate,
)
from twobrain_rec_server.outcomes.generator import canonical_transcript
from twobrain_rec_server.outcomes.models import OutcomeTranscriptSegment
from twobrain_rec_server.outcomes.prompts import outcome_config, prompt_snapshot_hash
from twobrain_rec_server.processing.store import latest_processing_result as latest_store_result
from twobrain_rec_server.workflows.outcome_generation_workflow import (
    outcome_generation_retry_policy,
)


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


def test_latest_processing_result_prefers_version_over_import_time(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "result-version-ordering")

    async def run() -> tuple[object, object, object]:
        async with client.app_state["sessionmaker"]() as db:
            current = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert current is not None and current.imported_at is not None
            newer = ProcessingResult(
                workspace_id=current.workspace_id,
                meeting_id=current.meeting_id,
                media_revision_id=current.media_revision_id,
                mediascribe_job_id=current.mediascribe_job_id,
                processing_workflow_id=current.processing_workflow_id,
                result_version=current.result_version + 1,
                status="imported",
                transcript_status=current.transcript_status,
                diarization_status=current.diarization_status,
                summary_status=current.summary_status,
                language=current.language,
                segment_count=current.segment_count,
                diarization_segment_count=current.diarization_segment_count,
                source_result_hash=f"result-version-ordering-{uuid4().hex}",
                imported_at=current.imported_at - timedelta(minutes=1),
            )
            db.add(newer)
            await db.commit()
            desktop = await latest_desktop_result(
                db,
                workspace_id=current.workspace_id,
                meeting_id=current.meeting_id,
                media_revision_id=current.media_revision_id,
            )
            store = await latest_store_result(
                db,
                workspace_id=current.workspace_id,
                meeting_id=current.meeting_id,
                media_revision_id=current.media_revision_id,
            )
            return (
                newer.id,
                desktop.id if desktop is not None else None,
                store.id if store is not None else None,
            )

    newer_id, desktop_id, store_id = asyncio.run(run())
    assert desktop_id == newer_id
    assert store_id == newer_id


def test_invalid_pinned_prompt_is_terminal_and_not_retryable() -> None:
    attempt = MeetingOutcomeGenerationAttempt(
        prompt_name="graf/meeting-outcome/auto",
        prompt_version=1,
        prompt_definition=[{"role": "user", "content": "{{unexpected}}"}],
        prompt_config=outcome_config(schema_name="graf_meeting_outcome_auto_v1"),
        prompt_source="verified_promoted_snapshot",
        prompt_hash="not-used-after-validation",
    )

    with pytest.raises(OutcomeGenerationTerminalError, match="summary_prompt_snapshot_corrupt"):
        _stored_prompt_snapshot(attempt)
    assert (
        "OutcomeGenerationTerminalError"
        in outcome_generation_retry_policy().non_retryable_error_types
    )


def test_ai_source_refs_use_canonical_pinned_segment_metadata() -> None:
    segment = OutcomeTranscriptSegment(
        segment_id=uuid4(),
        sequence=4,
        start_seconds=Decimal("12.345"),
        end_seconds=Decimal("18.765"),
        speaker_label="Алексей",
        source_role="system",
        text="Подтверждённое решение.",
    )

    assert _canonical_source_refs(
        [
            {
                "transcript_segment_id": str(segment.segment_id),
                "sequence": 4,
                "evidence_kind": "decision",
                "start_seconds": 999,
                "source_role": "untrusted",
            }
        ],
        [segment],
    ) == [
        {
            "transcript_segment_id": str(segment.segment_id),
            "sequence": 4,
            "start_seconds": 12.345,
            "end_seconds": 18.765,
            "speaker_label": "Алексей",
            "source_role": "system",
            "evidence_kind": "decision",
        }
    ]
    assert AI_GENERATOR_VERSION == "outcomes-ai-v1"


def test_candidate_segments_use_stable_confirmed_speaker_name(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "stable-candidate-speaker")

    async def run() -> list[str]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert result is not None
            diarization = (
                await db.scalars(
                    select(DiarizationSegment)
                    .where(DiarizationSegment.processing_result_id == result.id)
                    .order_by(DiarizationSegment.sequence)
                )
            ).all()
            assert len(diarization) == 2
            for row in diarization:
                row.speaker_label = "same-person"
            db.add(
                MeetingSpeakerName(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    speaker_key=stable_speaker_key(result.id, "same-person"),
                    display_name="Алексей",
                    updated_by_user_id=meeting.created_by_user_id,
                )
            )
            attempt = MeetingOutcomeGenerationAttempt(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                source_result_id=result.id,
            )
            await db.flush()
            return [segment.speaker_label for segment in await _candidate_segments(db, attempt)]

    assert asyncio.run(run()) == ["Алексей", "Алексей"]


def test_candidate_segments_preserve_overlapping_provider_turns(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "same-source-candidate-speaker")

    async def run() -> list[str]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            diarization = (
                await db.scalars(
                    select(DiarizationSegment)
                    .where(DiarizationSegment.processing_result_id == result.id)
                    .order_by(DiarizationSegment.sequence)
                )
            ).all()
            assert len(diarization) == 2
            local, remote = diarization
            local.end_seconds = Decimal("8.000")
            local.speaker_label = "local-person"
            remote.start_seconds = Decimal("0.000")
            remote.end_seconds = Decimal("9.000")
            remote.speaker_label = "remote-person"
            db.add_all(
                [
                    MeetingSpeakerName(
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting.id,
                        speaker_key=stable_speaker_key(result.id, "local-person"),
                        display_name="Локальный участник",
                        updated_by_user_id=meeting.created_by_user_id,
                    ),
                    MeetingSpeakerName(
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting.id,
                        speaker_key=stable_speaker_key(result.id, "remote-person"),
                        display_name="Удалённый участник",
                        updated_by_user_id=meeting.created_by_user_id,
                    ),
                ]
            )
            attempt = MeetingOutcomeGenerationAttempt(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                source_result_id=result.id,
            )
            await db.flush()
            return [segment.speaker_label for segment in await _candidate_segments(db, attempt)]

    assert asyncio.run(run()) == ["Локальный участник", "Удалённый участник"]


def test_candidate_segments_use_unknown_without_diarization(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "unknown-candidate-speaker")

    async def run() -> list[str]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            await db.execute(
                DiarizationSegment.__table__.delete().where(
                    DiarizationSegment.processing_result_id == result.id
                )
            )
            attempt = MeetingOutcomeGenerationAttempt(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                source_result_id=result.id,
            )
            await db.flush()
            return [segment.speaker_label for segment in await _candidate_segments(db, attempt)]

    assert asyncio.run(run()) == ["Спикер не определён", "Спикер не определён"]


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
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=accepted_before,
            )
            second = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=accepted_before,
            )
            await db.commit()
            return first.candidate_id, second.candidate_id, meeting.current_outcome_set_id

    first, second, accepted_after = asyncio.run(run())
    assert first == second
    assert accepted_after is None


def test_rejected_revision_baseline_is_not_reopened_by_automatic_reconcile(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "rejected-baseline-reconcile")
    service = __import__(
        "twobrain_rec_server.outcomes.service", fromlist=["ensure_outcomes_for_processing_result"]
    )

    async def run() -> tuple[object, object, object]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            accepted = await service.ensure_outcomes_for_processing_result(db, result=result)
            accepted.revision_state = "rejected"
            accepted.accepted_at = None
            meeting.current_outcome_set_id = None
            await db.commit()

            reconciled = await service.ensure_outcomes_for_processing_result(db, result=result)
            await db.commit()
            return accepted.id, reconciled.id, meeting.current_outcome_set_id

    accepted_id, reconciled_id, current_id = asyncio.run(run())
    assert reconciled_id == accepted_id
    assert current_id is None


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


def test_archived_personal_template_replays_pinned_candidate_but_cannot_start_new_one(
    client,
) -> None:
    meeting_id = create_outcome_ready_meeting(client, "archived-template-replay")

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert meeting is not None
            template = SummaryTemplate(
                workspace_id=meeting.workspace_id,
                owner_user_id=meeting.created_by_user_id,
                template_key="personal-archived",
                kind="personal",
                name="Архивный формат",
                purpose="Проверка pinned версии",
                sections_json=["summary", "action_items"],
                output_language="ru",
                detail_level="standard",
                version=1,
                status="active",
            )
            db.add(template)
            await db.flush()
            kwargs = {
                "workspace_id": meeting.workspace_id,
                "meeting_id": meeting.id,
                "requested_by_user_id": meeting.created_by_user_id,
                "template_key": template.template_key,
                "template_id": template.id,
                "template_version": template.version,
                "expected_current_outcome_set_id": meeting.current_outcome_set_id,
            }
            first = await create_summary_candidate(db, **kwargs)
            template.status = "archived"
            await db.flush()
            replay = await create_summary_candidate(db, **kwargs)
            with pytest.raises(
                OutcomeGenerationTerminalError, match="summary_template_unavailable"
            ):
                await create_summary_candidate(
                    db,
                    **kwargs,
                    request_intent="manual_refresh",
                    request_intent_id=uuid4(),
                )
            await db.commit()
            return first.candidate_id, replay.candidate_id

    first, replay = asyncio.run(run())
    assert first == replay


def test_same_format_requires_explicit_refresh_and_refresh_is_idempotent(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "same-format-refresh")

    async def run():
        service = __import__(
            "twobrain_rec_server.outcomes.service", fromlist=["ensure_outcomes_for_meeting"]
        )
        async with client.app_state["sessionmaker"]() as seed_db:
            seed_meeting = await seed_db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await seed_db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert seed_meeting is not None and result is not None
            accepted = await service.ensure_outcomes_for_processing_result(seed_db, result=result)
            accepted.revision_state = "accepted"
            seed_meeting.current_outcome_set_id = accepted.id
            await seed_db.commit()
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert (
                meeting is not None
                and result is not None
                and meeting.current_outcome_set_id is not None
            )
            with pytest.raises(OutcomeGenerationTerminalError, match="same_format_noop"):
                await create_summary_candidate(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    requested_by_user_id=meeting.created_by_user_id,
                    template_key="graf-auto-v1",
                    template_id=None,
                    template_version=1,
                    expected_current_outcome_set_id=meeting.current_outcome_set_id,
                    request_intent="manual_format",
                )
            intent_id = uuid4()
            first = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
                request_intent="manual_refresh",
                request_intent_id=intent_id,
            )
            duplicate = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
                request_intent="manual_refresh",
                request_intent_id=intent_id,
            )
            first.status = "failed"
            await db.flush()
            terminal_replay = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
                request_intent="manual_refresh",
                request_intent_id=intent_id,
            )
            duplicate_terminal_replay = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
                request_intent="manual_refresh",
                request_intent_id=intent_id,
            )
            second_intent = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
                request_intent="manual_refresh",
                request_intent_id=uuid4(),
            )
            # A different format is blocked while this refresh is active; once
            # the prior run reaches a terminal state, the owner may request it.
            second_intent.status = "failed"
            second_intent.failure_code = "summary_generation_retries_exhausted"
            await db.flush()
            format_first = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
                request_intent="manual_format",
            )
            format_first.status = "failed"
            await db.flush()
            format_terminal_replay = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
                request_intent="manual_format",
            )
            await db.commit()
            return (
                first,
                duplicate,
                terminal_replay,
                duplicate_terminal_replay,
                second_intent,
                format_first,
                format_terminal_replay,
            )

    (
        first,
        duplicate,
        terminal_replay,
        duplicate_terminal_replay,
        second,
        format_first,
        format_terminal_replay,
    ) = asyncio.run(run())
    assert first.candidate_id == duplicate.candidate_id
    assert first.candidate_id == terminal_replay.candidate_id
    assert terminal_replay.candidate_id == duplicate_terminal_replay.candidate_id
    assert ":retry:" not in (first.idempotency_key or "")
    assert first.candidate_id != second.candidate_id
    assert format_first.candidate_id == format_terminal_replay.candidate_id
    assert ":retry:" not in (format_first.idempotency_key or "")


def test_manual_refresh_does_not_reuse_accepted_ai_candidate(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "accepted-ai-refresh")

    async def run():
        service = __import__(
            "twobrain_rec_server.outcomes.service", fromlist=["ensure_outcomes_for_meeting"]
        )
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            accepted = await service.ensure_outcomes_for_processing_result(db, result=result)
            accepted.revision_state = "accepted"
            meeting.current_outcome_set_id = accepted.id
            await db.flush()
            prior = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=accepted.id,
                request_intent="manual_format",
            )
            prior.status = "accepted"
            prior.outcome_set_id = accepted.id
            await db.flush()
            refreshed = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=accepted.id,
                request_intent="manual_refresh",
                request_intent_id=uuid4(),
            )
            await db.commit()
            return prior, refreshed

    prior, refreshed = asyncio.run(run())
    assert prior.status == "accepted"
    assert refreshed.candidate_id != prior.candidate_id
    assert refreshed.status == "queued"


def test_active_refresh_reuses_candidate_across_intent_ids(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "active-refresh-intent-dedupe")

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert meeting is not None
            kwargs = {
                "workspace_id": meeting.workspace_id,
                "meeting_id": meeting.id,
                "requested_by_user_id": meeting.created_by_user_id,
                "template_key": "graf-auto-v1",
                "template_id": None,
                "template_version": 1,
                "expected_current_outcome_set_id": meeting.current_outcome_set_id,
                "request_intent": "manual_refresh",
            }
            first = await create_summary_candidate(db, **kwargs, request_intent_id=uuid4())
            # Prompt pinning may replace the mutable provider snapshot hash;
            # active dedupe must remain anchored to the immutable input/config.
            first.generator_config_hash = "pinned-provider-snapshot"
            await db.flush()
            replay = await create_summary_candidate(db, **kwargs, request_intent_id=uuid4())
            await db.commit()
            return first.candidate_id, replay.candidate_id

    first, replay = asyncio.run(run())
    assert first == replay


def test_retryable_failed_candidate_with_changed_source_is_not_reactivated(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "retryable-failed-source-fence")

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert meeting is not None
            intent_id = uuid4()
            kwargs = {
                "workspace_id": meeting.workspace_id,
                "meeting_id": meeting.id,
                "requested_by_user_id": meeting.created_by_user_id,
                "template_key": "graf-meeting-minutes-v1",
                "template_id": None,
                "template_version": 1,
                "expected_current_outcome_set_id": meeting.current_outcome_set_id,
                "request_intent": "manual_refresh",
                "request_intent_id": intent_id,
            }
            failed = await create_summary_candidate(db, **kwargs)
            failed.status = "failed"
            failed.failure_code = "summary_generation_retries_exhausted"
            failed.source_result_hash = "different-source-result"
            replacement = await create_summary_candidate(db, **kwargs)
            await db.commit()
            return failed.candidate_id, replacement.candidate_id

    failed_id, replacement_id = asyncio.run(run())
    assert failed_id != replacement_id


def test_expired_candidate_does_not_block_a_different_format(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "expired-cross-format")

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert meeting is not None
            first = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
            )
            first.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            second = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-outline-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
            )
            await db.commit()
            return first, second

    first, second = asyncio.run(run())
    assert first.status == "expired"
    assert second.candidate_id != first.candidate_id


def test_expired_active_refresh_is_closed_before_new_intent(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "expired-active-refresh")

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert meeting is not None
            kwargs = {
                "workspace_id": meeting.workspace_id,
                "meeting_id": meeting.id,
                "requested_by_user_id": meeting.created_by_user_id,
                "template_key": "graf-auto-v1",
                "template_id": None,
                "template_version": 1,
                "expected_current_outcome_set_id": meeting.current_outcome_set_id,
                "request_intent": "manual_refresh",
            }
            intent_id = uuid4()
            first = await create_summary_candidate(db, **kwargs, request_intent_id=intent_id)
            first.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.flush()
            exact_replay = await create_summary_candidate(db, **kwargs, request_intent_id=intent_id)
            replay = await create_summary_candidate(db, **kwargs, request_intent_id=uuid4())
            await db.commit()
            return first, exact_replay, replay

    first, exact_replay, replay = asyncio.run(run())
    assert first.status == "expired"
    assert exact_replay.candidate_id == first.candidate_id
    assert exact_replay.status == "expired"
    assert first.candidate_id != replay.candidate_id


def test_superseded_accepted_candidate_is_not_reused_for_a_new_format_request(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "superseded-candidate-retry")

    async def run():
        service = __import__(
            "twobrain_rec_server.outcomes.service", fromlist=["ensure_outcomes_for_meeting"]
        )
        async with client.app_state["sessionmaker"]() as seed_db:
            seed_meeting = await seed_db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await seed_db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert seed_meeting is not None and result is not None
            accepted = await service.ensure_outcomes_for_processing_result(seed_db, result=result)
            accepted.revision_state = "accepted"
            seed_meeting.current_outcome_set_id = accepted.id
            await seed_db.commit()
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert (
                meeting is not None
                and result is not None
                and meeting.current_outcome_set_id is not None
            )
            first = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
            )
            superseded_outcome = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                candidate_id=first.candidate_id,
                status="available",
                generator_version=f"test:{uuid4()}",
                revision_state="accepted",
            )
            db.add(superseded_outcome)
            await db.flush()
            first.status = "accepted"
            first.outcome_set_id = superseded_outcome.id
            replacement = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
                request_intent="manual_format",
            )
            await db.rollback()
            return first.candidate_id, replacement.candidate_id

    first, replacement = asyncio.run(run())
    assert first != replacement


def test_superseded_accepted_format_does_not_reopen_when_selected_again(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "accepted-format-switch-back")

    async def run():
        service = __import__(
            "twobrain_rec_server.outcomes.service", fromlist=["ensure_outcomes_for_meeting"]
        )
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            baseline = await service.ensure_outcomes_for_processing_result(db, result=result)
            baseline.revision_state = "accepted"
            meeting.current_outcome_set_id = baseline.id
            await db.flush()

            async def accept_format(template_key: str) -> MeetingOutcomeGenerationAttempt:
                attempt = await create_summary_candidate(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    requested_by_user_id=meeting.created_by_user_id,
                    template_key=template_key,
                    template_id=None,
                    template_version=1,
                    expected_current_outcome_set_id=meeting.current_outcome_set_id,
                    request_intent="manual_format",
                )
                outcome = MeetingOutcomeSet(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    media_revision_id=result.media_revision_id,
                    processing_result_id=result.id,
                    candidate_id=attempt.candidate_id,
                    status="available",
                    generator_version=f"test:{uuid4()}",
                    revision_state="accepted",
                )
                db.add(outcome)
                await db.flush()
                attempt.status = "accepted"
                attempt.outcome_set_id = outcome.id
                meeting.current_outcome_set_id = outcome.id
                await db.flush()
                return attempt

            first = await accept_format("graf-meeting-minutes-v1")
            await accept_format("graf-outline-v1")
            replacement = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
                request_intent="manual_format",
            )
            await db.commit()
            return first, replacement

    first, replacement = asyncio.run(run())
    assert first.status == "accepted"
    assert replacement.candidate_id != first.candidate_id
    assert replacement.status == "queued"


def test_personal_candidate_pins_template_and_generator_provenance(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "personal-candidate-provenance")

    async def run() -> tuple[str, str, str]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert meeting is not None
            template = SummaryTemplate(
                workspace_id=meeting.workspace_id,
                owner_user_id=meeting.created_by_user_id,
                template_key="personal-provenance",
                kind="personal",
                name="Мой формат",
                purpose="Проверка provenance",
                sections_json=["summary", "decisions"],
                output_language="ru",
                detail_level="standard",
                version=1,
                status="active",
            )
            db.add(template)
            await db.flush()
            attempt = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key=template.template_key,
                template_id=template.id,
                template_version=template.version,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
            )
            await db.commit()
            return (
                attempt.display_format_name or "",
                attempt.generator_config_hash or "",
                attempt.template_key or "",
            )

    name, config_hash, template_key = asyncio.run(run())
    assert name == "Мой формат"
    assert len(config_hash) == 64
    assert template_key == "personal-provenance"


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
                candidate_id=attempt.candidate_id,
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


def test_speaker_name_change_stales_candidate_before_acceptance(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "speaker-freshness-fence")

    async def run() -> tuple[str, str | None, str]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
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
                candidate_id=attempt.candidate_id,
                status="available",
                generator_version=f"test:{attempt.candidate_id}",
                revision_state="candidate",
            )
            db.add(candidate)
            await db.flush()
            attempt.outcome_set_id = candidate.id
            attempt.status = "candidate"
            candidate_id = attempt.candidate_id
            workspace_id = meeting.workspace_id
            creator_id = meeting.created_by_user_id
            await db.commit()

        assert candidate_id is not None
        async with client.app_state["sessionmaker"]() as db:
            await save_speaker_name(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                speaker_key="speaker_00",
                display_name="Алексей",
                actor_user_id=creator_id,
                known_speaker_keys={"speaker_00"},
            )
            await db.commit()

        async with client.app_state["sessionmaker"]() as db:
            with pytest.raises(
                OutcomeGenerationTerminalError,
                match="summary_source_revision_stale",
            ):
                await resolve_summary_candidate(
                    db,
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    candidate_id=candidate_id,
                    requested_by_user_id=creator_id,
                    accept=True,
                    expected_current_outcome_set_id=None,
                )
            await db.commit()
            persisted = await db.scalar(
                select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.candidate_id == candidate_id
                )
            )
            outcome = await db.scalar(
                select(MeetingOutcomeSet).where(MeetingOutcomeSet.candidate_id == candidate_id)
            )
            assert persisted is not None and outcome is not None
            return persisted.status, persisted.failure_code, outcome.revision_state

    status, failure_code, revision_state = asyncio.run(run())
    assert status == "stale"
    assert failure_code == "summary_source_revision_stale"
    assert revision_state == "stale"


def test_speaker_name_change_rekeys_generation_and_stales_active_attempt(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "speaker-generation-rekey")

    async def run() -> tuple:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            kwargs = {
                "workspace_id": meeting.workspace_id,
                "meeting_id": meeting.id,
                "requested_by_user_id": meeting.created_by_user_id,
                "template_key": "graf-auto-v1",
                "template_id": None,
                "template_version": 1,
                "expected_current_outcome_set_id": meeting.current_outcome_set_id,
            }
            first = await create_summary_candidate(db, **kwargs)
            first_revision = (first.metadata_json or {}).get("speaker_attribution_revision")
            await save_speaker_name(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                speaker_key="speaker_00",
                display_name="Алексей",
                actor_user_id=meeting.created_by_user_id,
                known_speaker_keys={"speaker_00"},
            )
            await db.flush()
            second = await create_summary_candidate(db, **kwargs)
            attempts = (
                await db.scalars(
                    select(MeetingOutcomeGenerationAttempt).where(
                        MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
                        MeetingOutcomeGenerationAttempt.generator_version == AI_GENERATOR_VERSION,
                    )
                )
            ).all()
            await db.rollback()
            return (
                first.candidate_id,
                second.candidate_id,
                first.status,
                first.failure_code,
                first_revision,
                (second.metadata_json or {}).get("speaker_attribution_revision"),
                len(attempts),
            )

    first_id, second_id, status, code, first_revision, second_revision, count = asyncio.run(run())
    assert first_id != second_id
    assert (status, code) == ("stale", "summary_source_revision_stale")
    assert first_revision == ""
    assert isinstance(second_revision, str) and second_revision
    assert count == 2


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
                candidate_id=attempt.candidate_id,
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

            with pytest.raises(
                OutcomeGenerationTerminalError, match="summary_source_revision_stale"
            ):
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
    assert status == "stale"
    assert failure_code == "summary_source_revision_stale"
    assert revision_state == "stale"


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
                candidate_id=attempt.candidate_id,
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


def test_new_source_after_reservation_is_blocked_before_litellm_egress(
    client, tmp_path, monkeypatch
) -> None:
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
        with pytest.raises(OutcomeGenerationTerminalError, match="summary_source_revision_stale"):
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
    assert persisted_attempt.failure_code == "summary_source_revision_stale"
    assert persisted_attempt.status == "stale"
    assert call is not None
    assert call.call_state == "failed"
