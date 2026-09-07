"""Synthetic PostgreSQL regressions for generation access and retained-call recovery."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.fixtures.cabinet import create_outcome_ready_meeting
from tests.fixtures.meeting_protocol import (
    extraction_result,
    prepare_evaluation_candidate,
    prepare_protocol_candidate,
    protocol_evaluation_runtime,
    protocol_gateway_response,
    protocol_result,
)
from twobrain_rec_server.cli import meeting_protocol_eval as evaluator
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    GenerationCall,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeSet,
    MeetingSummarySlot,
    ProcessingResult,
    PromptRootPromotion,
    UserIdentity,
    WorkspaceMembership,
)
from twobrain_rec_server.outcomes import ai_service
from twobrain_rec_server.outcomes.prompts import EXTRACTOR_PROMPT_NAME, VERIFIER_PROMPT_NAME


def _stage_result(snapshot, segments):
    if snapshot.name == EXTRACTOR_PROMPT_NAME:
        return extraction_result(segments)
    if snapshot.name == VERIFIER_PROMPT_NAME:
        return {"verdict": "pass", "findings": []}
    return protocol_result(segments)


@pytest.fixture
def isolated_generation(client, tmp_path):
    """Exercise evaluation fences against a real run-owned database and snapshot."""
    meeting_id = create_outcome_ready_meeting(client, "synthetic-source-fence")
    with protocol_evaluation_runtime(tmp_path) as runtime:
        async def setup():
            attempt, segments = await prepare_evaluation_candidate(
                client.app_state["sessionmaker"], runtime, meeting_id,
            )
            async with runtime.sessions() as db:
                assert await db.scalar(select(PromptRootPromotion.id)) is None
            return attempt, segments

        attempt, segments = asyncio.run(setup())

        async def source_guard():
            async with client.app_state["sessionmaker"]() as db:
                current = await evaluator.snapshot_source(db, meeting_id)
            if current["source_hash"] != attempt.metadata_json["evaluation_source"]["snapshot_hash"]:
                raise ai_service.OutcomeGenerationTerminalError("evaluation_source_changed")

        yield SimpleNamespace(
            meeting_id=meeting_id, sessions=runtime.sessions, attempt=attempt, segments=segments,
            settings=runtime.settings, source_guard=source_guard,
        )


def _ledger(call):
    return deepcopy({column.name: getattr(call, column.name) for column in GenerationCall.__table__.c})


async def _calls(db, candidate_id):
    return (await db.scalars(select(GenerationCall).where(
        GenerationCall.candidate_id == candidate_id,
    ).order_by(GenerationCall.call_sequence, GenerationCall.provider_attempt))).all()


async def _revoke(db, meeting_id, mutation):
    meeting = await db.get(Meeting, meeting_id)
    if mutation == "owner":
        owner = await db.get(UserIdentity, meeting.created_by_user_id)
        owner.status = "disabled"
    else:
        membership = await db.get(WorkspaceMembership, (meeting.workspace_id, meeting.created_by_user_id))
        membership.status = "revoked"
    await db.flush()


@pytest.mark.parametrize("mutation", ["owner", "membership"])
@pytest.mark.parametrize("boundary", [
    "extract_egress", "draft_egress", "verifier_egress",
    "extract_response", "draft_response", "verifier_response",
    "publication", "candidate_publication", "accepted_replay",
])
def test_ordinary_generation_rechecks_access(client, monkeypatch, mutation, boundary):
    meeting_id = create_outcome_ready_meeting(client, "synthetic-owner-revocation")
    sessionmaker = client.app_state["sessionmaker"]
    invoked = []
    revoked = []
    monkeypatch.setattr(ai_service, "_read_secret", lambda _path: "synthetic-unused")

    async def run():
        async with sessionmaker() as db:
            attempt, segments = await prepare_protocol_candidate(db, meeting_id)
        kwargs = dict(workspace_id=attempt.workspace_id, candidate_id=attempt.candidate_id,
                      expected_snapshot_hash=attempt.temporal_transcript_hash,
                      settings=Settings(langfuse_project_id="synthetic-project", litellm_base_url="https://example.invalid"))
        original_fence = ai_service._ensure_candidate_source_fence
        original_publish = ai_service.publish_model_generated_outcome

        async def fence(db, current):
            calls = await _calls(db, current.candidate_id)
            stage = {"extract_egress": 1, "draft_egress": 2, "verifier_egress": 3}.get(boundary)
            if not revoked and any(call.call_sequence == stage and call.call_state == "reserved" for call in calls):
                await _revoke(db, meeting_id, mutation)
                revoked.append(True)
            return await original_fence(db, current)

        async def publish(db, **options):
            if boundary == "publication" and not revoked:
                await _revoke(db, meeting_id, mutation)
                revoked.append(True)
            if boundary == "candidate_publication" and not revoked:
                # Exercise real authority/proof/publication checks, then interrupt
                # only acceptance so the next invocation resumes a stored candidate.
                async with db.begin_nested() as savepoint:
                    await original_publish(db, **options)
                    await savepoint.rollback()
                current = await db.scalar(select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.candidate_id == attempt.candidate_id,
                ).execution_options(populate_existing=True))
                return await db.get(MeetingOutcomeSet, current.outcome_set_id)
            return await original_publish(db, **options)

        async def generate(_self, *, snapshot, messages, **_kwargs):
            invoked.append(snapshot.name)
            stage = {"extract_response": 1, "draft_response": 2, "verifier_response": 3}.get(boundary)
            if len(invoked) == stage:
                async with sessionmaker() as db:
                    await _revoke(db, meeting_id, mutation)
                    await db.commit()
                revoked.append(True)
            result = _stage_result(snapshot, segments)
            return protocol_gateway_response(snapshot, messages, result)

        monkeypatch.setattr(ai_service, "_ensure_candidate_source_fence", fence)
        monkeypatch.setattr(ai_service, "publish_model_generated_outcome", publish)
        monkeypatch.setattr(ai_service.LiteLLMGateway, "generate", generate)
        replay = boundary in {"accepted_replay", "candidate_publication"}
        before = None
        if replay:
            first = await ai_service.execute_candidate_generation(sessionmaker, **kwargs)
            assert first["state"] == ("accepted" if boundary == "accepted_replay" else "candidate")
            async with sessionmaker() as db:
                before = [_ledger(call) for call in await _calls(db, attempt.candidate_id)]
                outcome = await db.get(MeetingOutcomeSet, first["outcome_set_id"])
                saved_protocol = deepcopy(outcome.protocol_json)
                slot = await db.scalar(select(MeetingSummarySlot).where(MeetingSummarySlot.meeting_id == meeting_id))
                saved_pointer = slot.current_outcome_set_id
                await _revoke(db, meeting_id, mutation)
                await db.commit()
            revoked.append(True)
        try:
            result = await ai_service.execute_candidate_generation(sessionmaker, **kwargs)
            assert not replay and result["state"] in {"stale", "cancelled", "failed"}
            assert result["failure_code"] == "summary_source_access_revoked"
        except ai_service.OutcomeGenerationTerminalError as exc:
            assert str(exc) == "summary_source_access_revoked"
        assert revoked
        assert len(invoked) == {
            "extract_egress": 0, "draft_egress": 1, "verifier_egress": 2,
            "extract_response": 1, "draft_response": 2,
        }.get(boundary, 3)
        async with sessionmaker() as db:
            calls = await _calls(db, attempt.candidate_id)
            assert sum(call.call_state == "completed" for call in calls) == len(invoked)
            assert all(call.raw_response_json and call.export_status == "pending" for call in calls if call.call_state == "completed")
            assert all(call.execution_authority_json["kind"] == "production" for call in calls)
            slot = await db.scalar(select(MeetingSummarySlot).where(MeetingSummarySlot.meeting_id == meeting_id))
            assert slot.current_outcome_set_id == (saved_pointer if replay else None)
            if before is not None:
                assert [_ledger(call) for call in calls] == before
                outcome = await db.get(MeetingOutcomeSet, first["outcome_set_id"])
                assert outcome.protocol_json == saved_protocol

    asyncio.run(run())


@pytest.mark.parametrize("stage", [1, 2, 3])
@pytest.mark.parametrize("mutation", ["source", "deletion", "ambiguous"])
def test_stage_failure_retains_truth_and_never_repeats_egress(client, monkeypatch, stage, mutation):
    meeting_id = create_outcome_ready_meeting(client, "synthetic-stage-fence")
    sessions = client.app_state["sessionmaker"]
    invoked = []
    monkeypatch.setattr(ai_service, "_read_secret", lambda _path: "synthetic-unused")

    async def run():
        async with sessions() as db:
            attempt, segments = await prepare_protocol_candidate(db, meeting_id)

        async def generate(_self, *, snapshot, messages, **_kwargs):
            invoked.append(snapshot.name)
            if len(invoked) == stage:
                if mutation == "ambiguous":
                    raise ai_service.LiteLLMError(
                        "litellm_outcome_ambiguous", retryable=False, egress_state="unknown",
                    )
                async with sessions() as db:
                    if mutation == "source":
                        source = await db.get(ProcessingResult, attempt.source_result_id)
                        source.source_result_hash = "synthetic-replaced-source"
                    else:
                        meeting = await db.get(Meeting, meeting_id)
                        meeting.deleted_at = datetime.now(UTC)
                        meeting.deletion_epoch += 1
                    await db.commit()
            return protocol_gateway_response(snapshot, messages, _stage_result(snapshot, segments))

        monkeypatch.setattr(ai_service.LiteLLMGateway, "generate", generate)
        kwargs = dict(
            workspace_id=attempt.workspace_id, candidate_id=attempt.candidate_id,
            expected_snapshot_hash=attempt.temporal_transcript_hash,
            settings=Settings(langfuse_project_id="synthetic-project", litellm_base_url="https://example.invalid"),
        )
        try:
            result = await ai_service.execute_candidate_generation(sessions, **kwargs)
            assert result["state"] in {"failed", "stale", "cancelled"}
            assert result["failure_code"] == {
                "source": "summary_source_revision_stale", "deletion": "meeting_deleting",
                "ambiguous": "summary_provider_outcome_ambiguous",
            }[mutation]
        except ai_service.OutcomeGenerationTerminalError as exc:
            assert mutation == "deletion" and str(exc) == "meeting_deleting"
        async with sessions() as db:
            calls = await _calls(db, attempt.candidate_id)
            assert len(calls) == len(invoked) == stage
            assert [call.call_sequence for call in calls] == list(range(1, stage + 1))
            assert all(call.execution_authority_json["kind"] == "production" for call in calls)
            completed = calls[:-1] if mutation == "ambiguous" else calls
            assert all(call.call_state == "completed" and call.raw_response_json for call in completed)
            if mutation == "ambiguous":
                assert calls[-1].call_state == "ambiguous"
                assert calls[-1].raw_response_json is None and calls[-1].export_status == "not_required"
            assert await db.scalar(select(MeetingSummarySlot.current_outcome_set_id).where(
                MeetingSummarySlot.meeting_id == meeting_id,
            )) is None
            assert await db.scalar(select(MeetingOutcomeSet.id).where(
                MeetingOutcomeSet.candidate_id == attempt.candidate_id,
            )) is None
            retained = [_ledger(call) for call in calls]
        with pytest.raises(ai_service.OutcomeGenerationTerminalError):
            await ai_service.execute_candidate_generation(sessions, **kwargs)
        assert len(invoked) == stage
        async with sessions() as db:
            assert [_ledger(call) for call in await _calls(db, attempt.candidate_id)] == retained

    asyncio.run(run())


@pytest.mark.parametrize("stage", [1, 2, 3])
@pytest.mark.parametrize("resume_action", [
    "resume", "source_changed", "tamper", "read_failed_again", "rejected_response",
    "parameter_missing", "parameter_changed",
])
def test_transient_source_failure_resumes_retained_response_without_inference(isolated_generation, monkeypatch, stage, resume_action):
    case = isolated_generation
    meeting_id, sessionmaker = case.meeting_id, case.sessions
    invoked = []
    failed = []
    monkeypatch.setattr(ai_service, "_read_secret", lambda _path: "synthetic-unused")

    async def run():
        attempt, segments = case.attempt, case.segments

        async def generate(_self, *, snapshot, messages, **_kwargs):
            invoked.append(snapshot.name)
            result = _stage_result(snapshot, segments)
            if resume_action == "rejected_response" and len(invoked) == stage:
                result = {} if stage < 3 else {"verdict": "fail", "findings": [
                    {"code": "missing_topic", "path": "/topics", "source_refs": []},
                ]}
            return protocol_gateway_response(snapshot, messages, result)

        async def guard():
            await case.source_guard()
            if len(invoked) == stage and not failed:
                failed.append(True)
                raise ai_service.OutcomeGenerationTerminalError("evaluation_source_read_failed")

        monkeypatch.setattr(ai_service.LiteLLMGateway, "generate", generate)
        kwargs = dict(workspace_id=attempt.workspace_id, candidate_id=attempt.candidate_id,
                      expected_snapshot_hash=attempt.temporal_transcript_hash,
                      settings=case.settings,
                      evaluation_source_guard=guard)
        with pytest.raises(ai_service.OutcomeGenerationDependencyError, match="^evaluation_source_read_failed$"):
            await ai_service.execute_candidate_generation(sessionmaker, **kwargs)
        async with sessionmaker() as db:
            current = await db.get(MeetingOutcomeGenerationAttempt, attempt.id)
            if resume_action == "rejected_response":
                assert current.status == "failed"
                assert current.failure_code == ("summary_response_invalid" if stage < 3 else "summary_verification_failed")
                retained = [_ledger(call) for call in await _calls(db, attempt.candidate_id)]
                with pytest.raises(ai_service.OutcomeGenerationTerminalError, match="^summary_candidate_terminal$"):
                    await ai_service.execute_candidate_generation(sessionmaker, **kwargs)
                assert len(invoked) == stage
                assert [_ledger(call) for call in await _calls(db, attempt.candidate_id)] == retained
                return
            assert current.status in ai_service.ACTIVE_CANDIDATE_STATUSES
            assert current.ended_at is None
            retained = [_ledger(call) for call in await _calls(db, attempt.candidate_id)]
            assert len(retained) == stage
            assert all(call["call_state"] == "completed" and call["export_status"] == "pending" for call in retained)
        if resume_action == "source_changed":
            async def revoked_guard():
                raise ai_service.OutcomeGenerationTerminalError("evaluation_source_changed")

            kwargs["evaluation_source_guard"] = revoked_guard
            with pytest.raises(ai_service.OutcomeGenerationTerminalError, match="^evaluation_source_changed$"):
                await ai_service.execute_candidate_generation(sessionmaker, **kwargs)
            assert len(invoked) == stage
            async with sessionmaker() as db:
                assert [_ledger(call) for call in await _calls(db, attempt.candidate_id)] == retained
            return
        if resume_action == "tamper":
            async with sessionmaker() as db:
                call = (await _calls(db, attempt.candidate_id))[-1]
                call.raw_response_json = {"synthetic": "tampered"}
                await db.commit()
            with pytest.raises(ai_service.OutcomeGenerationTerminalError, match="^generation_call_content_hash_mismatch$"):
                await ai_service.execute_candidate_generation(sessionmaker, **kwargs)
            assert len(invoked) == stage
            return
        if resume_action in {"parameter_missing", "parameter_changed"}:
            async with sessionmaker() as db:
                call = (await _calls(db, attempt.candidate_id))[0]
                request = dict(call.request_json)
                if resume_action == "parameter_missing":
                    request.pop("temperature")
                else:
                    request["temperature"] = 0.5
                call.request_json = request
                call.request_hash = ai_service._content_hash(request)
                await db.commit()
                retained = [_ledger(item) for item in await _calls(db, attempt.candidate_id)]
            with pytest.raises(ai_service.OutcomeGenerationTerminalError, match="^generation_call_request_mismatch$"):
                await ai_service.execute_candidate_generation(sessionmaker, **kwargs)
            assert len(invoked) == stage
            async with sessionmaker() as db:
                assert [_ledger(item) for item in await _calls(db, attempt.candidate_id)] == retained
            return
        if resume_action == "read_failed_again":
            failed.clear()
            with pytest.raises(ai_service.OutcomeGenerationDependencyError, match="^evaluation_source_read_failed$"):
                await ai_service.execute_candidate_generation(sessionmaker, **kwargs)
            assert len(invoked) == stage
        resumed = await ai_service.execute_candidate_generation(sessionmaker, **kwargs)
        assert resumed["state"] == "candidate"
        replayed = await ai_service.execute_candidate_generation(sessionmaker, **kwargs)
        assert replayed["state"] == "candidate" and replayed["reused"]
        assert len(invoked) == 3
        async with sessionmaker() as db:
            calls = await _calls(db, attempt.candidate_id)
            assert [_ledger(call) for call in calls[:stage]] == retained
            assert len(calls) == 3
            assert all(call.execution_authority_json["kind"] == "evaluation" for call in calls)
            assert await db.scalar(select(MeetingSummarySlot.current_outcome_set_id).where(MeetingSummarySlot.meeting_id == meeting_id)) is None

    asyncio.run(run())


@pytest.mark.parametrize("mutation", [None, "owner", "membership"])
def test_generation_access_with_real_app_role_rls(client, monkeypatch, mutation):
    from tests.fixtures.postgres_rls import validate_rls_test_database_url
    from tests.integration.test_rls_postgres_policies import _exact_app_role_engine

    meeting_id = create_outcome_ready_meeting(client, "synthetic-app-role-access")
    sessions = client.app_state["sessionmaker"]
    migration_url = validate_rls_test_database_url(
        client.app_state["engine"].url.render_as_string(hide_password=False),
        variable_name="synthetic_fixture_database",
    )
    invoked = []
    monkeypatch.setattr(ai_service, "_read_secret", lambda _path: "synthetic-unused")

    async def run():
        async with sessions() as db:
            attempt, segments = await prepare_protocol_candidate(db, meeting_id)
            if mutation:
                await _revoke(db, meeting_id, mutation)
                await db.commit()

        async def generate(_self, *, snapshot, messages, **_kwargs):
            invoked.append(snapshot.name)
            result = _stage_result(snapshot, segments)
            return protocol_gateway_response(snapshot, messages, result)

        monkeypatch.setattr(ai_service.LiteLLMGateway, "generate", generate)
        async with _exact_app_role_engine(migration_url) as engine:
            app_sessions = async_sessionmaker(engine, expire_on_commit=False)
            async with app_sessions() as db:
                assert await db.scalar(text("select current_user")) == "twobrain_rec_app"
                assert not await db.scalar(text("select rolsuper or rolbypassrls from pg_roles where rolname = current_user"))
                await ai_service._apply_worker_workspace(db, attempt.workspace_id)
                assert await db.scalar(select(UserIdentity.id)) is None
                assert await db.scalar(select(WorkspaceMembership.user_id)) is None
                meeting = await db.get(Meeting, meeting_id)
                previous = dict(db.info["tenant_context"])
                if mutation:
                    with pytest.raises(ai_service.OutcomeGenerationTerminalError, match="^summary_source_access_revoked$"):
                        await ai_service._ensure_candidate_access(db, meeting, attempt)
                else:
                    await ai_service._ensure_candidate_access(db, meeting, attempt)
                assert db.info["tenant_context"] == previous
                assert await db.scalar(text("select rec_context_kind()")) == "worker"
                await db.commit()
                assert await db.scalar(text("select rec_context_kind()")) == "worker"
            kwargs = dict(workspace_id=attempt.workspace_id, candidate_id=attempt.candidate_id,
                          expected_snapshot_hash=attempt.temporal_transcript_hash,
                          settings=Settings(langfuse_project_id="synthetic-project", litellm_base_url="https://example.invalid"))
            if mutation:
                with pytest.raises(ai_service.OutcomeGenerationTerminalError, match="^summary_source_access_revoked$"):
                    await ai_service.execute_candidate_generation(app_sessions, **kwargs)
                assert invoked == []
            else:
                assert (await ai_service.execute_candidate_generation(app_sessions, **kwargs))["state"] == "accepted"
                assert (await ai_service.execute_candidate_generation(app_sessions, **kwargs))["reused"]
                assert len(invoked) == 3

    asyncio.run(run())


@pytest.mark.parametrize("stage", [1, 2, 3])
def test_transient_source_failure_before_egress_is_not_ambiguous(isolated_generation, monkeypatch, stage):
    case = isolated_generation
    sessions = case.sessions
    invoked, failed = [], []
    monkeypatch.setattr(ai_service, "_read_secret", lambda _path: "synthetic-unused")

    async def run():
        attempt, segments = case.attempt, case.segments

        async def generate(_self, *, snapshot, messages, **_kwargs):
            invoked.append(snapshot.name)
            result = _stage_result(snapshot, segments)
            return protocol_gateway_response(snapshot, messages, result)

        async def guard():
            await case.source_guard()
            if failed:
                return
            async with sessions() as db:
                calls = await _calls(db, attempt.candidate_id)
            if any(call.call_sequence == stage and call.call_state == "reserved" for call in calls):
                failed.append(True)
                raise ai_service.OutcomeGenerationTerminalError("evaluation_source_read_failed")

        monkeypatch.setattr(ai_service.LiteLLMGateway, "generate", generate)
        kwargs = dict(workspace_id=attempt.workspace_id, candidate_id=attempt.candidate_id,
                      expected_snapshot_hash=attempt.temporal_transcript_hash,
                      settings=case.settings,
                      evaluation_source_guard=guard)
        with pytest.raises(ai_service.OutcomeGenerationDependencyError, match="^evaluation_source_read_failed$"):
            await ai_service.execute_candidate_generation(sessions, **kwargs)
        assert len(invoked) == stage - 1
        async with sessions() as db:
            retained = [_ledger(call) for call in await _calls(db, attempt.candidate_id)]
            assert retained[-1]["call_state"] == "failed"
            assert retained[-1]["export_status"] == "not_required"
            assert retained[-1]["raw_response_json"] is None
            assert retained[-1]["validated_result_json"]["generation_error"]["egress_state"] == "not_sent"
        assert (await ai_service.execute_candidate_generation(sessions, **kwargs))["state"] == "candidate"
        assert len(invoked) == 3
        async with sessions() as db:
            calls = await _calls(db, attempt.candidate_id)
            by_id = {call.id: _ledger(call) for call in calls}
            assert all(by_id[call["id"]] == call for call in retained)
            assert len(calls) == 4
            assert sum(call.call_state == "completed" for call in calls) == 3

    asyncio.run(run())
