"""Actual PostgreSQL journal -> three calls -> publication, using only synthetic data."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from tests.fixtures.cabinet import create_outcome_ready_meeting
from tests.fixtures.meeting_protocol import (
    extraction_result,
    prepare_protocol_candidate,
    protocol_gateway_response,
    protocol_result,
)
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    GenerationCall,
    MeetingOutcomeSet,
    MeetingSummarySlot,
)
from twobrain_rec_server.outcomes import ai_service
from twobrain_rec_server.outcomes.prompts import (
    EXTRACTOR_PROMPT_NAME,
    VERIFIER_PROMPT_NAME,
    canonical_json,
)


@pytest.mark.parametrize("scenario", ["pass", "resolve", "missing_authority", "wrong_project", "missing_extractor", "verifier_fail"])
def test_three_calls_need_journal_authority_and_preserve_exact_output(client, monkeypatch, scenario):
    meeting_id = create_outcome_ready_meeting(client, "synthetic-authorized-chain")
    monkeypatch.setattr(ai_service, "_read_secret", lambda _: "synthetic-unused")
    invoked = []

    async def run():
        sessions = client.app_state["sessionmaker"]
        async with sessions() as db:
            attempt, segments = await prepare_protocol_candidate(db, meeting_id)
            workspace_id, candidate_id, snapshot_hash = attempt.workspace_id, attempt.candidate_id, attempt.temporal_transcript_hash
            if scenario == "resolve":
                attempt.prompt_version = None
                attempt.prompt_definition = attempt.prompt_config = attempt.prompt_hash = None
                attempt.metadata_json = {key: value for key, value in attempt.metadata_json.items() if key not in {
                    "execution_authority", "prompt_bundle", "extractor_prompt", "verifier_prompt", "pipeline",
                }}
                await db.commit()
            if scenario in {"missing_authority", "missing_extractor"}:
                metadata = dict(attempt.metadata_json)
                metadata.pop("execution_authority" if scenario == "missing_authority" else "extractor_prompt")
                attempt.metadata_json = metadata
                await db.commit()
        extraction, draft = extraction_result(segments), protocol_result(segments)

        async def generate(_self, *, snapshot, messages, **_kwargs):
            invoked.append(snapshot.name)
            if snapshot.name == EXTRACTOR_PROMPT_NAME:
                result = extraction
            elif snapshot.name == VERIFIER_PROMPT_NAME:
                assert canonical_json(draft) in messages[1]["content"]
                result = {"verdict": "pass", "findings": []} if scenario != "verifier_fail" else {
                    "verdict": "fail", "findings": [{"code": "missing_topic", "path": "/topics", "source_refs": []}],
                }
            else:
                assert canonical_json(extraction) in messages[1]["content"]
                result = draft
            return protocol_gateway_response(snapshot, messages, result)

        monkeypatch.setattr(ai_service.LiteLLMGateway, "generate", generate)
        settings = Settings(litellm_base_url="https://example.invalid", langfuse_project_id=(
            "wrong-project" if scenario == "wrong_project" else "synthetic-project"
        ))
        kwargs = dict(settings=settings, workspace_id=workspace_id, candidate_id=candidate_id,
                      expected_snapshot_hash=snapshot_hash)
        if scenario == "resolve":
            def forbidden(_settings):
                raise AssertionError("runtime cannot fetch labels or rewrite the admission")
            monkeypatch.setattr(ai_service, "create_langfuse_client", forbidden)
            resolved = await ai_service.resolve_candidate_prompt(
                sessions, settings=settings, workspace_id=workspace_id, candidate_id=candidate_id,
            )
            assert resolved["generation_timeout_seconds"] == 3 * settings.litellm_request_timeout_seconds + 120
        if scenario not in {"pass", "resolve", "verifier_fail"}:
            with pytest.raises(ai_service.OutcomeGenerationTerminalError):
                await ai_service.execute_candidate_generation(sessions, **kwargs)
            assert invoked == []
            return
        result = await ai_service.execute_candidate_generation(sessions, **kwargs)
        assert result["state"] == ("failed" if scenario == "verifier_fail" else "accepted")
        assert len(invoked) == 3
        if scenario in {"pass", "resolve"}:
            assert (await ai_service.execute_candidate_generation(sessions, **kwargs))["reused"] is True
            assert len(invoked) == 3
        async with sessions() as db:
            calls = (await db.scalars(select(GenerationCall).where(
                GenerationCall.candidate_id == candidate_id,
            ).order_by(GenerationCall.call_sequence))).all()
            slot = await db.scalar(select(MeetingSummarySlot).where(MeetingSummarySlot.meeting_id == meeting_id))
            assert calls[0].validated_result_json == extraction
            assert calls[1].validated_result_json == draft
            assert calls[1].predecessor_call_id == calls[0].id
            assert calls[2].predecessor_call_id == calls[1].id
            assert len({call.execution_authority_hash for call in calls}) == 1
            if scenario == "verifier_fail":
                assert slot.current_outcome_set_id is None
                return
            outcome = await db.get(MeetingOutcomeSet, slot.current_outcome_set_id)
            assert outcome.protocol_json == calls[2].validated_result_json["protocol"]
            # A pinned generation binding cannot be edited even with a recomputed JSON hash.
            calls[1].predecessor_call_id = uuid4()
            with pytest.raises(DBAPIError):
                await db.commit()
            await db.rollback()

    asyncio.run(run())
