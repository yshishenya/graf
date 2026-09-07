from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from unittest.mock import DEFAULT, MagicMock

import pytest
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
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
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeSet,
    MeetingSummarySlot,
)
from twobrain_rec_server.outcomes import ai_service
from twobrain_rec_server.outcomes.prompts import EXTRACTOR_PROMPT_NAME, VERIFIER_PROMPT_NAME


def _call_snapshot(call):
    return deepcopy({column.name: getattr(call, column.name) for column in GenerationCall.__table__.c})


@pytest.mark.parametrize("retry_delivery", [False, True])
@pytest.mark.parametrize("stage", [1, 2, 3])
def test_stage_observation_is_delivered_from_retained_ledger_after_deletion(
    client, monkeypatch, retry_delivery, stage
):
    meeting_id = create_outcome_ready_meeting(client, "retained-protocol-stage")
    sessionmaker = client.app_state["sessionmaker"]
    invoked = []
    monkeypatch.setattr(ai_service, "_read_secret", lambda _path: "synthetic-unused")

    async def generate_protocol():
        async with sessionmaker() as db:
            attempt, segments = await prepare_protocol_candidate(db, meeting_id)
            workspace_id, candidate_id = attempt.workspace_id, attempt.candidate_id
            kept_metadata = {key: deepcopy(attempt.metadata_json[key]) for key in (
                "extractor_prompt", "verifier_prompt", "pipeline", "execution_authority",
            )}
            stage_prompt = {
                1: kept_metadata["extractor_prompt"],
                2: {"name": attempt.prompt_name, "version": attempt.prompt_version, "hash": attempt.prompt_hash},
                3: kept_metadata["verifier_prompt"],
            }[stage]
            transcript_hash = attempt.temporal_transcript_hash

        async def generate(_self, *, snapshot, messages, **_kwargs):
            invoked.append(snapshot.name)
            if snapshot.name == EXTRACTOR_PROMPT_NAME:
                result = extraction_result(segments)
            elif snapshot.name == VERIFIER_PROMPT_NAME:
                result = {"verdict": "pass", "findings": []}
            else:
                result = protocol_result(segments)
            return protocol_gateway_response(snapshot, messages, result)

        monkeypatch.setattr(ai_service.LiteLLMGateway, "generate", generate)
        result = await ai_service.execute_candidate_generation(
            sessionmaker,
            workspace_id=workspace_id,
            candidate_id=candidate_id,
            expected_snapshot_hash=transcript_hash,
            settings=Settings(langfuse_project_id="synthetic-project", litellm_base_url="https://example.invalid"),
        )
        assert result["state"] == "accepted"
        async with sessionmaker() as db:
            calls = (await db.scalars(select(GenerationCall).where(
                GenerationCall.candidate_id == candidate_id,
            ).order_by(GenerationCall.call_sequence))).all()
            assert [call.call_sequence for call in calls] == [1, 2, 3]
            assert all(call.call_state == "completed" and call.export_status == "pending" for call in calls)
            assert all(call.execution_authority_json == kept_metadata["execution_authority"] for call in calls)
            outcome = await db.get(MeetingOutcomeSet, result["outcome_set_id"])
            attempt = await db.get(MeetingOutcomeGenerationAttempt, attempt.id)
            assert outcome.protocol_json and attempt.header_snapshot_json
            assert calls[2].validated_result_json["protocol"] == outcome.protocol_json
            assert calls[2].validated_result_json["draft_hash"] == calls[1].validated_result_hash
            assert calls[2].validated_result_json["extraction_hash"] == calls[0].validated_result_hash
            assert calls[0].predecessor_call_id is None
            for previous, current in zip(calls[:-1], calls[1:], strict=True):
                assert current.predecessor_call_id == previous.id
                assert current.predecessor_result_hash == previous.validated_result_hash
            return workspace_id, candidate_id, kept_metadata, stage_prompt, [_call_snapshot(call) for call in calls]

    workspace_id, candidate_id, kept_metadata, stage_prompt, retained = asyncio.run(generate_protocol())
    assert len(invoked) == 3 and invoked[0] == EXTRACTOR_PROMPT_NAME and invoked[2] == VERIFIER_PROMPT_NAME
    index = stage - 1
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": "Delete this meeting everywhere GRAF controls."},
    )
    assert response.status_code == 202

    async def inspect_purged():
        async with sessionmaker() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting.deleted_at is not None and meeting.current_outcome_set_id is None
            assert await db.scalar(select(MeetingSummarySlot.id).where(
                MeetingSummarySlot.meeting_id == meeting_id,
            )) is None
            outcome = await db.scalar(select(MeetingOutcomeSet).where(
                MeetingOutcomeSet.candidate_id == candidate_id,
            ))
            assert outcome.protocol_json is None and outcome.content_hash is None
            assert outcome.protocol_state == "unavailable" and outcome.lifecycle_state == "deleted"
            attempt = await db.scalar(select(MeetingOutcomeGenerationAttempt).where(
                MeetingOutcomeGenerationAttempt.candidate_id == candidate_id,
            ))
            assert attempt.status == "cancelled" and attempt.failure_code == "meeting_deleted"
            assert attempt.header_snapshot_json is None
            assert attempt.metadata_json == {"purged_for_deletion": True, **kept_metadata}
            calls = (await db.scalars(select(GenerationCall).where(
                GenerationCall.candidate_id == candidate_id,
            ).order_by(GenerationCall.call_sequence))).all()
            for call in calls:
                ai_service._verify_generation_call_hashes(call)
            return [_call_snapshot(call) for call in calls]

    # Deletion must retain every ledger column, not only the parsed protocol.
    assert asyncio.run(inspect_purged()) == retained
    langfuse = MagicMock()
    langfuse.get_prompt.return_value = object()
    if retry_delivery:
        langfuse.start_observation.side_effect = [RuntimeError("synthetic pre-export failure"), DEFAULT]
    monkeypatch.setattr(ai_service, "create_langfuse_client", lambda _settings: langfuse)

    async def publish():
        await ai_service.publish_generation_call(
            sessionmaker,
            workspace_id=workspace_id,
            call_id=retained[index]["id"],
            settings=client.app.state.settings,
            activity_attempt=3,
            temporal_workflow_id=f"outcome-generation/{candidate_id}",
            temporal_run_id="synthetic-delivery-run",
            temporal_activity_id=f"publish-stage-{stage}-observation",
        )

    if retry_delivery:
        with pytest.raises(ai_service.OutcomeGenerationDependencyError, match="langfuse_delivery_failed"):
            asyncio.run(publish())
        pending = asyncio.run(inspect_purged())
        assert pending[index]["call_state"] == "completed"
        assert pending[index]["export_status"] == "pending"
        assert pending[index]["last_export_error_code"] == "langfuse_delivery_failed"
        assert pending[index]["next_export_attempt_at"] > datetime.now(UTC)
        assert pending[index]["export_attempt_count"] == 1
        # Backoff suppresses premature redelivery without rerunning inference.
        asyncio.run(publish())
        assert asyncio.run(inspect_purged()) == pending
        assert langfuse.start_observation.call_count == 1

        async def make_retry_due():
            async with sessionmaker() as db:
                call = await db.get(GenerationCall, retained[index]["id"])
                call.next_export_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
                await db.commit()

        asyncio.run(make_retry_due())

    asyncio.run(publish())
    confirmed = asyncio.run(inspect_purged())
    assert all(confirmed[other] == retained[other] for other in range(3) if other != index)
    assert confirmed[index]["export_status"] == "confirmed"
    assert confirmed[index]["export_confirmed_at"] is not None
    assert confirmed[index]["export_attempt_count"] == (2 if retry_delivery else 1)
    assert confirmed[index]["last_export_error_code"] is None
    assert confirmed[index]["next_export_attempt_at"] is None
    export_fields = {
        "export_status", "export_attempt_count", "export_confirmed_at",
        "last_export_attempt_at", "next_export_attempt_at", "last_export_error_code",
        "updated_at",
    }
    assert confirmed[index]["updated_at"] >= retained[index]["updated_at"]
    assert {key: value for key, value in confirmed[index].items() if key not in export_fields} == {
        key: value for key, value in retained[index].items() if key not in export_fields
    }
    langfuse.get_prompt.assert_called_with(
        stage_prompt["name"], version=stage_prompt["version"], type="chat",
        cache_ttl_seconds=60, max_retries=0, fetch_timeout_seconds=10,
    )
    observation = langfuse.start_observation.call_args.kwargs
    assert observation["as_type"] == "generation"
    assert observation["input"] == {"request": retained[index]["request_json"]}
    assert observation["output"] == {
        "raw_response": retained[index]["raw_response_json"],
        "validated_result": retained[index]["validated_result_json"],
    }
    assert observation["prompt"] is langfuse.get_prompt.return_value
    assert observation["metadata"]["call_sequence"] == stage
    assert observation["metadata"]["observation_id"] == retained[index]["observation_id"]
    assert observation["metadata"]["prompt_name"] == stage_prompt["name"]
    assert observation["metadata"]["prompt_version"] == stage_prompt["version"]
    assert observation["metadata"]["prompt_hash"] == stage_prompt["hash"]
    assert observation["metadata"]["temporal_activity_id"] == f"publish-stage-{stage}-observation"
    langfuse.start_observation.return_value.end.assert_called_once()
    assert langfuse.flush.called
    # Confirmed replay emits no new observation and resurrects no product content.
    deliveries = langfuse.start_observation.call_count
    prompt_fetches = langfuse.get_prompt.call_count
    asyncio.run(publish())
    assert asyncio.run(inspect_purged()) == confirmed
    assert langfuse.start_observation.call_count == deliveries == (2 if retry_delivery else 1)
    assert langfuse.get_prompt.call_count == prompt_fetches
    assert len(invoked) == 3
