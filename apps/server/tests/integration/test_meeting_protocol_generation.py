from __future__ import annotations

import asyncio
from contextlib import nullcontext
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import create_outcome_ready_meeting
from tests.fixtures.meeting_protocol import (
    extraction_result,
    pin_protocol_authority,
    prepare_evaluation_candidate,
    prepare_protocol_candidate,
    protocol_evaluation_runtime,
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
    ProcessingResult,
)
from twobrain_rec_server.outcomes import ai_service
from twobrain_rec_server.outcomes.generator import canonical_transcript, model_transcript
from twobrain_rec_server.outcomes.prompts import (
    EXTRACTOR_PROMPT_NAME,
    VERIFIER_PROMPT_NAME,
    canonical_json,
)
from twobrain_rec_server.outcomes.templates import BUILT_IN_BY_KEY


@pytest.mark.parametrize("stage", [1, 2, 3])
def test_proxy_timeout_retains_error_response_without_replaying_inference(client, monkeypatch, stage):
    meeting_id = create_outcome_ready_meeting(client, "synthetic-proxy-timeout")
    invoked = []
    monkeypatch.setattr(ai_service, "_read_secret", lambda _path: "synthetic-unused")

    async def run():
        sessions = client.app_state["sessionmaker"]
        async with sessions() as db:
            attempt, segments = await prepare_protocol_candidate(db, meeting_id)

        async def generate(_self, *, snapshot, messages, **_kwargs):
            invoked.append(snapshot.name)
            if len(invoked) == stage:
                raise ai_service.LiteLLMError(
                    "litellm_outcome_ambiguous", retryable=False, egress_state="unknown",
                    raw_response={"http_status": 504, "body_text": "synthetic gateway timeout"},
                )
            result = extraction_result(segments) if snapshot.name == EXTRACTOR_PROMPT_NAME else protocol_result(segments)
            return protocol_gateway_response(snapshot, messages, result)

        monkeypatch.setattr(ai_service.LiteLLMGateway, "generate", generate)
        kwargs = dict(
            workspace_id=attempt.workspace_id, candidate_id=attempt.candidate_id,
            expected_snapshot_hash=attempt.temporal_transcript_hash,
            settings=Settings(litellm_base_url="https://example.invalid", langfuse_project_id="synthetic-project"),
        )
        result = await ai_service.execute_candidate_generation(sessions, **kwargs)
        assert result["failure_code"] == "summary_provider_outcome_ambiguous"
        async with sessions() as db:
            call = await ai_service._latest_protocol_call(db, attempt, stage)
            assert call.call_state == "ambiguous" and ai_service._generation_call_is_publishable(call)
            retained = (call.completed_at, call.raw_response_hash, call.validated_result_hash, call.export_status)
        with pytest.raises(ai_service.OutcomeGenerationTerminalError, match="summary_candidate_terminal"):
            await ai_service.execute_candidate_generation(sessions, **kwargs)
        async with sessions() as db:
            call = await ai_service._latest_protocol_call(db, attempt, stage)
            assert retained == (call.completed_at, call.raw_response_hash, call.validated_result_hash, call.export_status)
            assert ai_service._generation_call_is_publishable(call)
        assert len(invoked) == stage

    asyncio.run(run())


def test_resolved_generation_parameters_match_request_and_hash(client, monkeypatch):
    from tests.fixtures.prompt_authority import promotion_row
    meeting_id = create_outcome_ready_meeting(client, "pinned-parameters")
    hashed_inputs = []
    content_hash = ai_service._content_hash

    def capture_hash(value):
        if isinstance(value, dict) and "model_parameters" in value:
            hashed_inputs.append(value)
        return content_hash(value)

    monkeypatch.setattr(ai_service, "_content_hash", capture_hash)

    async def run():
        sessionmaker = client.app_state["sessionmaker"]
        async with sessionmaker() as db:
            db.add(promotion_row())
            meeting = await db.get(Meeting, meeting_id)
            attempt = await ai_service.create_summary_candidate(
                db, workspace_id=meeting.workspace_id, meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-auto-v1", template_id=None,
                template_version=BUILT_IN_BY_KEY["graf-auto-v1"].version,
                expected_current_outcome_set_id=None,
            )
            workspace_id, candidate_id = attempt.workspace_id, attempt.candidate_id
            await db.commit()
        kwargs = dict(
            settings=Settings(langfuse_project_id="synthetic-project"),
            workspace_id=workspace_id, candidate_id=candidate_id,
        )
        first = await ai_service.resolve_candidate_prompt(sessionmaker, **kwargs)
        reused = await ai_service.resolve_candidate_prompt(sessionmaker, **kwargs)
        assert first["generation_timeout_seconds"] == reused["generation_timeout_seconds"] == 1920
        custom = await ai_service.resolve_candidate_prompt(sessionmaker, **{
            **kwargs, "settings": kwargs["settings"].model_copy(update={"litellm_request_timeout_seconds": 900}),
        })
        assert custom["generation_timeout_seconds"] == 2820
        async with sessionmaker() as db:
            attempt = await ai_service._candidate_attempt(db, workspace_id, candidate_id)
            snapshot = ai_service._stored_prompt_snapshot(attempt)
            request = snapshot.litellm_request([])
            expected = {key: value for key, value in request.items() if key not in {"model", "messages"}}
            assert "reasoning_effort" not in expected
            assert attempt.model_parameters == snapshot.model_parameters == expected
            assert hashed_inputs[-1]["model_parameters"] == expected
            assert content_hash(hashed_inputs[-1]) == attempt.generator_config_hash
            changed = deepcopy(hashed_inputs[-1])
            changed["model_parameters"]["reasoning_effort"] = "medium"
            assert content_hash(changed) != attempt.generator_config_hash

    asyncio.run(run())


@pytest.mark.parametrize("personal", [False, True])
def test_automatic_generation_uses_current_contract_without_rewriting_saved_default(client, personal):
    from twobrain_rec_server.db.models import Meeting, SummaryTemplate, Workspace
    from twobrain_rec_server.outcomes.ai_service import ensure_automatic_summary_candidate

    meeting_id = create_outcome_ready_meeting(client, "protocol-default-preserved")

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            workspace = await db.get(Workspace, meeting.workspace_id)
            workspace.default_summary_template_key = "graf-project-sync-v1"
            workspace.default_summary_template_version = 1
            if personal:
                template = SummaryTemplate(
                    workspace_id=workspace.id, owner_user_id=meeting.created_by_user_id,
                    template_key="personal-synthetic", kind="personal", name="Синтетический формат",
                    purpose="Проверка", sections_json=["summary", "action_items"],
                    output_language="ru", detail_level="detailed", version=1,
                )
                db.add(template)
                await db.flush()
                workspace.default_summary_template_key = template.template_key
                workspace.default_summary_template_id = template.id
            await db.commit()
            saved = (workspace.default_summary_template_key, workspace.default_summary_template_id, workspace.default_summary_template_version)
            attempt = await ensure_automatic_summary_candidate(db, workspace_id=workspace.id, meeting_id=meeting.id)
            assert attempt is not None
            assert attempt.template_key == saved[0] and attempt.template_id == saved[1]
            assert attempt.template_version == (1 if personal else 2)
            assert saved == (workspace.default_summary_template_key, workspace.default_summary_template_id, workspace.default_summary_template_version)

    asyncio.run(run())


@pytest.mark.parametrize("mutation", ["expire", "source", "delete_epoch"])
def test_evaluation_replay_rechecks_local_fences(client, monkeypatch, mutation, tmp_path):
    meeting_id = create_outcome_ready_meeting(client, "synthetic-evaluation-replay")
    monkeypatch.setattr(ai_service, "_read_secret", lambda _path: "synthetic-unused")
    invoked = []

    async def run(runtime):
        sessionmaker = runtime.sessions
        attempt, segments = await prepare_evaluation_candidate(client.app_state["sessionmaker"], runtime, meeting_id)
        candidate_id, workspace_id = attempt.candidate_id, attempt.workspace_id
        snapshot_hash = attempt.temporal_transcript_hash

        async def generate(_self, *, snapshot, messages, **_kwargs):
            invoked.append(snapshot.name)
            result = (extraction_result(segments) if snapshot.name == EXTRACTOR_PROMPT_NAME else
                      {"verdict": "pass", "findings": []} if snapshot.name == VERIFIER_PROMPT_NAME else protocol_result(segments))
            return protocol_gateway_response(snapshot, messages, result)

        async def guard():
            pass

        monkeypatch.setattr(ai_service.LiteLLMGateway, "generate", generate)
        kwargs = dict(
            settings=runtime.settings,
            workspace_id=workspace_id, candidate_id=candidate_id,
            expected_snapshot_hash=snapshot_hash, evaluation_source_guard=guard,
        )
        assert (await ai_service.execute_candidate_generation(sessionmaker, **kwargs))["state"] == "candidate"
        async with sessionmaker() as db:
            current = await db.get(MeetingOutcomeGenerationAttempt, attempt.id)
            if mutation == "expire":
                current.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            elif mutation == "source":
                source = await db.get(ProcessingResult, current.source_result_id)
                source.source_result_hash = "synthetic-source-replaced"
            else:
                meeting = await db.get(Meeting, meeting_id)
                meeting.deletion_epoch += 1
            await db.commit()
        with pytest.raises(ai_service.OutcomeGenerationTerminalError):
            await ai_service.execute_candidate_generation(sessionmaker, **kwargs)
        assert len(invoked) == 3

    with protocol_evaluation_runtime(tmp_path) as runtime:
        asyncio.run(run(runtime))


@pytest.mark.parametrize("stage", [1, 2, 3])
@pytest.mark.parametrize("mutation", ["delete", "cancel", "replace_source", "expire", "revoke_source_access"])
def test_protocol_race_retains_response_without_publishing(client, monkeypatch, stage, mutation, tmp_path):
    meeting_id = create_outcome_ready_meeting(client, "protocol-stage-race")
    invoked = []
    revoked = []
    monkeypatch.setattr(ai_service, "_read_secret", lambda _path: "synthetic-unused")

    async def run(runtime):
        sessionmaker = runtime.sessions if runtime else client.app_state["sessionmaker"]
        if runtime:
            attempt, segments = await prepare_evaluation_candidate(client.app_state["sessionmaker"], runtime, meeting_id)
        else:
            async with sessionmaker() as db:
                attempt, segments = await prepare_protocol_candidate(db, meeting_id)
        transcript_hash = attempt.temporal_transcript_hash
        workspace_id, candidate_id, attempt_id = attempt.workspace_id, attempt.candidate_id, attempt.id
        source_id = attempt.source_result_id

        async def generate(_self, *, snapshot, messages, **_kwargs):
            invoked.append(snapshot.name)
            result = (extraction_result(segments) if snapshot.name == EXTRACTOR_PROMPT_NAME else
                      {"verdict": "pass", "findings": []} if snapshot.name == VERIFIER_PROMPT_NAME else protocol_result(segments))
            if len(invoked) == stage:
                async with sessionmaker() as db:
                    current = await db.get(MeetingOutcomeGenerationAttempt, attempt_id)
                    if mutation == "delete":
                        meeting = await db.get(Meeting, meeting_id)
                        meeting.deleted_at = datetime.now(UTC)
                        meeting.deletion_epoch += 1
                    elif mutation == "cancel":
                        current.status = "cancelled"
                    elif mutation == "replace_source":
                        source = await db.get(ProcessingResult, source_id)
                        source.source_result_hash = "synthetic-replaced-source"
                    elif mutation == "expire":
                        current.expires_at = datetime.now(UTC) - timedelta(seconds=1)
                    else:
                        revoked.append(True)
                    await db.commit()
            return protocol_gateway_response(snapshot, messages, result)

        monkeypatch.setattr(ai_service.LiteLLMGateway, "generate", generate)
        async def source_guard():
            if revoked:
                raise ai_service.OutcomeGenerationTerminalError("evaluation_source_changed")

        evaluation = mutation == "revoke_source_access"
        settings = runtime.settings if runtime else Settings(litellm_base_url="https://example.invalid", langfuse_project_id="synthetic-project")
        try:
            result = await ai_service.execute_candidate_generation(
                sessionmaker, workspace_id=workspace_id, candidate_id=candidate_id,
                expected_snapshot_hash=transcript_hash, settings=settings,
                evaluation_source_guard=source_guard if evaluation else None,
            )
            assert result["state"] in {"cancelled", "stale", "expired"}
        except ai_service.OutcomeGenerationTerminalError as exc:
            assert str(exc) in {"meeting_deleting", "summary_candidate_expired", "evaluation_source_changed"}
        async with sessionmaker() as db:
            calls = (await db.scalars(select(GenerationCall).where(
                GenerationCall.candidate_id == candidate_id,
            ).order_by(GenerationCall.call_sequence))).all()
            assert len(calls) == len(invoked) == stage
            assert all(call.call_state == "completed" and call.raw_response_json for call in calls)
            slot = await db.scalar(select(MeetingSummarySlot).where(MeetingSummarySlot.meeting_id == meeting_id))
            assert slot.current_outcome_set_id is None
            assert await db.scalar(select(MeetingOutcomeSet.id).where(MeetingOutcomeSet.candidate_id == candidate_id)) is None

    with protocol_evaluation_runtime(tmp_path) if mutation == "revoke_source_access" else nullcontext(None) as runtime:
        asyncio.run(run(runtime))


@pytest.mark.parametrize("scenario", ["pass", "verifier_fail", "bad_ref", "verify_ambiguous", "title_edit", "evaluation", "partial"])
def test_three_calls_are_required_before_protocol_publication(client, monkeypatch, scenario, tmp_path):
    meeting_id = create_outcome_ready_meeting(client, "synthetic-three-stage-protocol")
    invoked = []
    monkeypatch.setattr(ai_service, "_read_secret", lambda _path: "synthetic-unused")

    async def run(runtime):
        sessionmaker = runtime.sessions if runtime else client.app_state["sessionmaker"]
        prepared = None
        if runtime:
            prepared, _ = await prepare_evaluation_candidate(client.app_state["sessionmaker"], runtime, meeting_id)
        async with sessionmaker() as db:
            meeting = await db.get(Meeting, meeting_id)
            meeting.title = "Закреплённое название"
            if scenario == "partial":
                processing = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
                processing.diarization_status = "unavailable"
                processing.diarization_segment_count = 0
                await db.flush()
            if prepared:
                attempt = await db.get(MeetingOutcomeGenerationAttempt, prepared.id)
            else:
                attempt = await ai_service.ensure_automatic_summary_candidate(
                    db, workspace_id=meeting.workspace_id, meeting_id=meeting.id,
                )
                assert attempt is not None
                await pin_protocol_authority(db, attempt)
            source = await ai_service._candidate_segments(db, attempt)
            transcript = canonical_transcript(source)
            transcript_hash = __import__("hashlib").sha256(transcript.encode()).hexdigest()
            attempt.temporal_transcript_hash = transcript_hash
            workspace_id, candidate_id = meeting.workspace_id, attempt.candidate_id
            draft = protocol_result(source)
            if scenario == "bad_ref":
                draft["executive_summary"][0]["source_refs"][0]["sequence"] += 100
            await db.commit()

        async def generate(_self, *, snapshot, messages, **_kwargs):
            invoked.append(snapshot.name)
            assert model_transcript(transcript) in messages[1]["content"]
            if snapshot.name == VERIFIER_PROMPT_NAME:
                assert canonical_json(draft) in messages[1]["content"]
                async with sessionmaker() as db:
                    slot = await db.scalar(select(MeetingSummarySlot).where(
                        MeetingSummarySlot.meeting_id == meeting_id,
                        MeetingSummarySlot.template_key == "graf-auto-v1",
                    ))
                    assert slot.current_outcome_set_id is None
                if scenario == "verify_ambiguous":
                    raise ai_service.LiteLLMError("litellm_outcome_ambiguous", retryable=False, egress_state="unknown")
                result = {"verdict": "pass", "findings": []}
                if scenario == "verifier_fail":
                    result = {"verdict": "fail", "findings": [
                        {"code": "missing_topic", "path": "/topics", "source_refs": []},
                    ]}
            elif snapshot.name == EXTRACTOR_PROMPT_NAME:
                result = extraction_result(source)
            else:
                result = deepcopy(draft)
                if scenario == "title_edit":
                    async with sessionmaker() as db:
                        meeting = await db.get(Meeting, meeting_id)
                        meeting.title = "Позднее изменение"
                        await db.commit()
            return protocol_gateway_response(snapshot, messages, result)

        monkeypatch.setattr(ai_service.LiteLLMGateway, "generate", generate)
        kwargs = dict(
            workspace_id=workspace_id, candidate_id=candidate_id,
            expected_snapshot_hash=transcript_hash,
            settings=Settings(litellm_base_url="https://example.invalid", langfuse_project_id="synthetic-project"),
        )
        guards = []
        if scenario == "evaluation":
            async def source_guard():
                guards.append(True)

            kwargs["evaluation_source_guard"] = source_guard
            kwargs["settings"] = runtime.settings
        try:
            first = await ai_service.execute_candidate_generation(sessionmaker, **kwargs)
        except ai_service.OutcomeGenerationTerminalError:
            assert scenario == "verify_ambiguous"
            first = {"state": "failed"}
        if scenario in {"pass", "title_edit", "evaluation", "partial"}:
            replay = await ai_service.execute_candidate_generation(sessionmaker, **kwargs)
            assert first["state"] == replay["state"] == ("candidate" if scenario == "evaluation" else "accepted")
        else:
            assert first["state"] == "failed"
        async with sessionmaker() as db:
            calls = (await db.scalars(select(GenerationCall).where(
                GenerationCall.candidate_id == candidate_id,
            ).order_by(GenerationCall.call_sequence))).all()
            assert len(calls) == len(invoked) == (2 if scenario == "bad_ref" else 3)
            assert [call.call_sequence for call in calls] == list(range(1, len(calls) + 1))
            assert all(call.transcript_text == transcript for call in calls)
            assert all("reasoning_effort" not in call.request_json for call in calls)
            slot = await db.scalar(select(MeetingSummarySlot).where(
                MeetingSummarySlot.meeting_id == meeting_id, MeetingSummarySlot.template_key == "graf-auto-v1",
            ))
            if scenario == "evaluation":
                assert len(guards) >= 6
                assert slot.current_outcome_set_id is None
                assert (await db.get(Meeting, meeting_id)).current_outcome_set_id is None
                outcome = await db.get(MeetingOutcomeSet, first["outcome_set_id"])
                assert outcome.accepted_at is None and outcome.revision_state == "candidate"
                attempt = await db.scalar(select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.candidate_id == candidate_id,
                ))
                with pytest.raises(ai_service.OutcomeGenerationTerminalError, match="summary_evaluation_not_publishable"):
                    await ai_service.publish_model_generated_outcome(
                        db, workspace_id=workspace_id, meeting_id=meeting_id, candidate_id=candidate_id,
                        expected_current_outcome_set_id=None,
                        publication_proof=ai_service._protocol_publication_proof(attempt, *calls), settings=kwargs["settings"],
                    )
                return
            if scenario not in {"pass", "title_edit", "partial"}:
                assert slot.current_outcome_set_id is None
                return
            outcome = await db.get(MeetingOutcomeSet, slot.current_outcome_set_id)
            assert outcome.protocol_state == "available"
            assert outcome.protocol_json["header"]["title"] == "Закреплённое название"
            assert calls[0].validated_result_json == extraction_result(source)
            assert calls[1].validated_result_json == draft
            assert calls[2].validated_result_json["protocol"] == outcome.protocol_json
            assert calls[2].validated_result_json["draft_hash"] == calls[1].validated_result_hash
            assert outcome.content_hash == ai_service._content_hash(outcome.protocol_json)
            assert outcome.content_hash != calls[2].validated_result_hash
            return deepcopy(outcome.protocol_json)

    with protocol_evaluation_runtime(tmp_path) if scenario == "evaluation" else nullcontext(None) as runtime:
        published = asyncio.run(run(runtime))
    if published is not None:
        # Read the automatically published result, without seeding or manual acceptance.
        page = client.get(f"/meetings/{meeting_id}", headers=auth_headers())
        assert page.status_code == 200
        assert "Закреплённое название" in page.text
        if scenario == "partial":
            # Partial transcripts are hidden by the existing transcript policy;
            # keep the source time visible without offering a missing destination.
            assert "notes-source-time" in page.text
            assert "notes-source-link" not in page.text
        else:
            assert "data-seek-seconds" in page.text
        endpoint = f"/api/v1/cabinet/meetings/{meeting_id}/content-exports"
        capability = client.get(endpoint, headers=auth_headers())
        assert capability.status_code == 200
        capability = capability.json()
        assert capability["summary"]["state"] == "available"
        if scenario == "partial":
            assert capability["transcript"]["state"] != "available"
            assert capability["combined"]["state"] != "available"
            for scope in ("transcript", "combined"):
                denied = client.post(endpoint, headers=auth_headers(), json={
                    "content_scope": scope, "format": "md",
                    "processing_result_id": capability["processing_result_id"],
                    "outcome_set_id": capability["outcome_set_id"] if scope == "combined" else None,
                })
                assert denied.status_code == 409
        for export_format in ("json", "md"):
            exported = client.post(endpoint, headers=auth_headers(), json={
                "content_scope": "summary", "format": export_format,
                "processing_result_id": capability["processing_result_id"],
                "outcome_set_id": capability["outcome_set_id"],
            })
            assert exported.status_code == 200, exported.text
            if export_format == "json":
                assert exported.json()["summary"]["protocol"] == published
            else:
                assert "Закреплённое название" in exported.text
                assert published["executive_summary"][0]["text"] in exported.text
        assert len(invoked) == 3  # Rendering/export/replay did not invoke the model again.
