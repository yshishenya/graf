import asyncio
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from tests.fixtures.cabinet import create_outcome_ready_meeting
from tests.unit.test_meeting_protocol import protocol_fixture
from twobrain_rec_server.cli.langfuse_prompts import outcome_prompt
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    GenerationCall,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    MeetingSummarySlot,
    ProcessingResult,
    ServerNotification,
    UserIdentity,
    WorkspaceMembership,
)
from twobrain_rec_server.outcomes import ai_service
from twobrain_rec_server.outcomes.generator import LiteLLMError, LiteLLMGenerationResult
from twobrain_rec_server.outcomes.prompts import meeting_protocol_config


def test_full_document_roundtrip_keeps_historical_null(client):
    meeting_id = create_outcome_ready_meeting(client, "protocol-storage")

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(
                ProcessingResult.meeting_id == meeting_id,
            ))
            fields = dict(workspace_id=result.workspace_id, meeting_id=meeting_id,
                          processing_result_id=result.id, media_revision_id=result.media_revision_id)
            old = MeetingOutcomeSet(**fields, generator_version="historical")
            new = MeetingOutcomeSet(**fields, generator_version="protocol",
                                    protocol_json={"title": "  Точный текст  "})
            db.add_all([old, new])
            await db.flush()
            await db.refresh(old)
            await db.refresh(new)
            assert old.protocol_json is None
            assert new.protocol_json == {"title": "  Точный текст  "}
            await db.rollback()

    asyncio.run(run())


@pytest.mark.parametrize("active", [True, False])
def test_candidate_owner_fence_with_restricted_worker_role(client, active):
    from uuid import uuid4

    meeting_id = create_outcome_ready_meeting(client, f"protocol-worker-owner-{active}")

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            workspace_id, user_id = meeting.workspace_id, meeting.created_by_user_id
            if not active:
                identity = await db.get(UserIdentity, user_id)
                identity.status = "inactive"
                await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            # The media-only role intentionally lacks identity grants. Exercise
            # the worker's RLS predicates with a transactional non-bypass role.
            role = f"protocol_fence_{uuid4().hex}"
            await db.execute(text(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER NOBYPASSRLS"))
            await db.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
            await db.execute(text(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {role}"))
            await db.execute(text(f"GRANT UPDATE ON workspace_memberships, user_identities TO {role}"))
            await db.execute(text(f"SET LOCAL ROLE {role}"))
            await ai_service._apply_worker_workspace(db, workspace_id)
            context = dict(db.info["tenant_context"])
            meeting = await db.get(Meeting, meeting_id)
            attempt = SimpleNamespace(requested_by_user_id=user_id)
            if active:
                await ai_service._ensure_candidate_owner(db, meeting, attempt)
            else:
                with pytest.raises(ai_service.OutcomeGenerationTerminalError, match="summary_access_revoked"):
                    await ai_service._ensure_candidate_owner(db, meeting, attempt)
            assert db.info["tenant_context"] == context
            assert await db.scalar(text("select current_setting('app.context_kind')")) == "worker"

    asyncio.run(run())


@pytest.mark.parametrize("race", [
    "none", "expired", "cancelled", "deleted", "source", "access", "deleted_error",
    "identity", "identity_before_egress", "long_fields", "projection_failure",
    "projection_failure_expired", "projection_failure_cancelled", "projection_failure_deleted",
    "projection_failure_source", "projection_failure_access", "projection_failure_corrupt",
    "error_finalization_failure", "validation_finalization_failure", "invalid_response",
])
def test_generation_retains_response_and_fences_publication(client, monkeypatch, race):
    meeting_id = create_outcome_ready_meeting(client, f"protocol-{race}")
    actual = client.app_state["sessionmaker"]
    settings = Settings(litellm_base_url="https://gateway.example.test", outcome_prompt_label="dev")
    config = meeting_protocol_config(model="operator/test-model")
    fetches = []

    def fetch(_client, **kwargs):
        fetches.append(kwargs["label"])
        return SimpleNamespace(version=7, prompt=outcome_prompt("Полный протокол"), config=config)

    monkeypatch.setattr(ai_service, "create_langfuse_client", lambda _: object())
    monkeypatch.setattr(ai_service, "shutdown_langfuse", lambda _: None)
    monkeypatch.setattr(ai_service, "fetch_prompt_by_label", fetch)
    monkeypatch.setattr(ai_service, "get_storage", lambda _: object())
    monkeypatch.setattr(ai_service, "_read_secret", lambda _: "synthetic-key")
    calls = []
    raw = {"id": "synthetic-response", "model": "provider-model", "choices": []}

    async def generate(_gateway, *, snapshot, messages, **kwargs):
        calls.append(snapshot.litellm_request(messages))
        transcript = messages[-1]["content"].split("<transcript>")[1].split("</transcript>")[0]
        sequence = json.loads(transcript)[0]["sequence"]
        document = protocol_fixture()

        def refs(node):
            if isinstance(node, dict):
                if set(node) == {"sequence", "quote"}:
                    node.update(sequence=sequence, quote=None)
                else:
                    for child in node.values():
                        refs(child)
            elif isinstance(node, list):
                for child in node:
                    refs(child)
        refs(document)
        if race == "long_fields":
            document["action_items"][0].update(
                owner_text="  Исполнитель " + "я" * 241,
                due_date_text="  После согласования " + "я" * 121,
            )
        async with actual() as db:
            meeting = await db.get(Meeting, meeting_id)
            attempt = await db.scalar(select(MeetingOutcomeGenerationAttempt).where(
                MeetingOutcomeGenerationAttempt.candidate_id == candidate_id,
            ))
            if race == "expired":
                attempt.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            elif race == "cancelled":
                attempt.status = "cancelled"
            elif race in {"deleted", "deleted_error"}:
                meeting.deletion_epoch += 1
            elif race == "source":
                result = await db.get(ProcessingResult, attempt.source_result_id)
                result.source_result_hash = "changed-source"
            elif race == "access":
                membership = await db.scalar(select(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == meeting.workspace_id,
                    WorkspaceMembership.user_id == meeting.created_by_user_id,
                ))
                membership.status = "inactive"
            elif race == "identity":
                identity = await db.get(UserIdentity, meeting.created_by_user_id)
                identity.status = "inactive"
            await db.commit()
        if race in {"deleted_error", "error_finalization_failure"}:
            raise LiteLLMError("litellm_request_rejected", retryable=False, raw_response=raw)
        return LiteLLMGenerationResult(
            request=calls[-1], raw_response=raw,
            parsed_content={} if race in {"validation_finalization_failure", "invalid_response"} else document,
            actual_model="provider-model", actual_provider=None, provider_request_id="synthetic-response",
            token_usage=None, cost_details=None,
        )

    monkeypatch.setattr(ai_service.LiteLLMGateway, "generate", generate)
    projection_failure = race.startswith("projection_failure")
    if projection_failure:
        publish = ai_service.publish_model_generated_outcome
        projection_attempts = 0

        async def fail_projection(db, **_kwargs):
            nonlocal projection_attempts
            projection_attempts += 1
            if projection_attempts == 1:
                # A real PostgreSQL error aborts the projection transaction.
                await db.execute(text("SELECT 1 / 0"))
            return await publish(db, **_kwargs)

        monkeypatch.setattr(ai_service, "publish_model_generated_outcome", fail_projection)
    elif race in {"error_finalization_failure", "validation_finalization_failure"}:
        finalize = ai_service.finalize_dispatch_for_candidate
        finalization_attempts = 0

        async def fail_finalization(db, **_kwargs):
            nonlocal finalization_attempts
            finalization_attempts += 1
            if finalization_attempts == 1:
                await db.execute(text("SELECT 1 / 0"))
            return await finalize(db, **_kwargs)

        monkeypatch.setattr(ai_service, "finalize_dispatch_for_candidate", fail_finalization)
    candidate_id = None

    async def run():
        nonlocal candidate_id
        async with actual() as db:
            meeting = await db.get(Meeting, meeting_id)
            workspace_id = meeting.workspace_id
            attempt = await ai_service.create_summary_candidate(
                db, workspace_id=workspace_id, meeting_id=meeting_id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-auto-v1", template_id=None, template_version=1,
                expected_current_outcome_set_id=None,
            )
            candidate_id = attempt.candidate_id
            await db.commit()
        await ai_service.resolve_candidate_prompt(actual, settings=settings,
                                                  workspace_id=workspace_id, candidate_id=candidate_id)
        await ai_service.resolve_candidate_prompt(actual, settings=settings,
                                                  workspace_id=workspace_id, candidate_id=candidate_id)
        assert fetches == ["dev"]
        snapshot, _chunks = await ai_service.snapshot_candidate_transcript(
            actual, settings=settings, workspace_id=workspace_id, candidate_id=candidate_id,
        )
        kwargs = dict(workspace_id=workspace_id, candidate_id=candidate_id, settings=settings,
                      expected_snapshot_hash=snapshot["snapshot_hash"])
        if race == "identity_before_egress":
            async with actual() as db:
                meeting = await db.get(Meeting, meeting_id)
                identity = await db.get(UserIdentity, meeting.created_by_user_id)
                identity.status = "inactive"
                await db.commit()
            with pytest.raises(ai_service.OutcomeGenerationTerminalError, match="summary_access_revoked"):
                await ai_service.execute_candidate_generation(actual, **kwargs)
            async with actual() as db:
                assert await db.scalar(select(GenerationCall).where(
                    GenerationCall.candidate_id == candidate_id,
                )) is None
            assert calls == []
            return
        if projection_failure or race in {"error_finalization_failure", "validation_finalization_failure"}:
            with pytest.raises(DBAPIError):
                await ai_service.execute_candidate_generation(actual, **kwargs)
        elif race in {"expired", "deleted", "deleted_error"}:
            with pytest.raises(ai_service.OutcomeGenerationTerminalError):
                await ai_service.execute_candidate_generation(actual, **kwargs)
        else:
            result = await ai_service.execute_candidate_generation(actual, **kwargs)
            assert result["state"] == ("accepted" if race in {"none", "long_fields"} else {
                "source": "stale", "access": "failed", "identity": "failed", "cancelled": "cancelled", "invalid_response": "failed",
            }[race])
            if race == "identity":
                assert result["failure_code"] == "summary_access_revoked"
        async with actual() as db:
            call = await db.scalar(select(GenerationCall).where(GenerationCall.candidate_id == candidate_id))
            slot = await db.scalar(select(MeetingSummarySlot).where(MeetingSummarySlot.meeting_id == meeting_id))
            assert call is not None and call.raw_response_json == raw
            assert call.raw_response_hash and call.validated_result_hash
            ai_service._verify_generation_call_hashes(call)
            assert call.export_status == "pending"
            assert (slot.current_outcome_set_id is not None) == (race in {"none", "long_fields"})
            if race in {"none", "long_fields"}:
                outcome = await db.get(MeetingOutcomeSet, slot.current_outcome_set_id)
                assert outcome.protocol_json == call.validated_result_json["protocol"]
                if race == "long_fields":
                    item = await db.scalar(select(MeetingOutcomeItem).where(
                        MeetingOutcomeItem.outcome_set_id == outcome.id,
                        MeetingOutcomeItem.category == "action_items",
                    ))
                    task = outcome.protocol_json["action_items"][0]
                    assert item.owner_text == task["owner_text"] == "  Исполнитель " + "я" * 241
                    assert item.due_date_text == task["due_date_text"] == "  После согласования " + "я" * 121
            if projection_failure or race in {"error_finalization_failure", "validation_finalization_failure"}:
                assert await db.scalar(select(MeetingOutcomeSet).where(
                    MeetingOutcomeSet.candidate_id == candidate_id,
                )) is None
        if race == "validation_finalization_failure":
            replay = await ai_service.execute_candidate_generation(actual, **kwargs)
            assert replay["reused"] is True
            assert replay["state"] == "failed"
            assert replay["failure_code"] == "summary_response_invalid"
        if race in {"validation_finalization_failure", "invalid_response"}:
            async with actual() as db:
                notices = (await db.scalars(select(ServerNotification).where(
                    ServerNotification.meeting_id == meeting_id,
                    ServerNotification.kind == "summary_failed",
                ))).all()
                assert len(notices) == 1
            assert len(calls) == 1
        if race == "error_finalization_failure":
            with pytest.raises(ai_service.OutcomeGenerationTerminalError, match="summary_provider_attempt_not_retryable"):
                await ai_service.execute_candidate_generation(actual, **kwargs)
        if projection_failure and race != "projection_failure":
            async with actual() as db:
                attempt = await db.scalar(select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.candidate_id == candidate_id,
                ))
                meeting = await db.get(Meeting, meeting_id)
                if race.endswith("expired"):
                    attempt.expires_at = datetime.now(UTC) - timedelta(seconds=1)
                elif race.endswith("cancelled"):
                    attempt.status = "cancelled"
                elif race.endswith("deleted"):
                    meeting.deletion_epoch += 1
                elif race.endswith("source"):
                    source = await db.get(ProcessingResult, attempt.source_result_id)
                    source.source_result_hash = "new-source-after-response"
                elif race.endswith("access"):
                    identity = await db.get(UserIdentity, meeting.created_by_user_id)
                    identity.status = "inactive"
                elif race.endswith("corrupt"):
                    call = await db.scalar(select(GenerationCall).where(
                        GenerationCall.candidate_id == candidate_id,
                    ))
                    call.validated_result_hash = "invalid"
                await db.commit()
            with pytest.raises(ai_service.OutcomeGenerationTerminalError):
                await ai_service.execute_candidate_generation(actual, **kwargs)
            async with actual() as db:
                assert await db.scalar(select(MeetingOutcomeSet).where(
                    MeetingOutcomeSet.candidate_id == candidate_id,
                )) is None
        elif race in {"none", "long_fields", "projection_failure"}:
            replay = await ai_service.execute_candidate_generation(actual, **kwargs)
            assert replay["reused"] is True
            assert replay["state"] == "accepted"
            repeated = await ai_service.execute_candidate_generation(actual, **kwargs)
            assert repeated["outcome_set_id"] == replay["outcome_set_id"]
            async with actual() as db:
                outcomes = (await db.scalars(select(MeetingOutcomeSet).where(
                    MeetingOutcomeSet.candidate_id == candidate_id,
                ))).all()
                call = await db.scalar(select(GenerationCall).where(
                    GenerationCall.candidate_id == candidate_id,
                ))
                assert len(outcomes) == 1
                assert outcomes[0].protocol_json == call.validated_result_json["protocol"]
        assert len(calls) == 1
        assert "temperature" not in calls[0]

    asyncio.run(run())


@pytest.mark.parametrize("field,limit", [("owner_text", 240), ("due_date_text", 120)])
def test_protocol_migration_preserves_history_and_refuses_lossy_downgrade(client, field, limit):
    from importlib import import_module

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migration = import_module("twobrain_rec_server.db.migrations.versions.0088_meeting_protocol")
    meeting_id = create_outcome_ready_meeting(client, f"protocol-migration-{field}")

    def migrate(connection, direction):
        with Operations.context(MigrationContext.configure(connection)):
            getattr(migration, direction)()

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            outcome = MeetingOutcomeSet(
                workspace_id=result.workspace_id, meeting_id=meeting_id,
                processing_result_id=result.id, generator_version="historical",
            )
            db.add(outcome)
            await db.flush()
            item = MeetingOutcomeItem(
                workspace_id=result.workspace_id, meeting_id=meeting_id,
                outcome_set_id=outcome.id, category="action_items", sequence=0,
                owner_text="  Исполнитель  ", due_date_text="  Завтра  ",
            )
            db.add(item)
            await db.commit()
            item_id, outcome_id = item.id, outcome.id
        async with client.app_state["engine"].begin() as connection:
            await connection.run_sync(migrate, "downgrade")
            await connection.run_sync(migrate, "upgrade")
        async with client.app_state["sessionmaker"]() as db:
            item = await db.get(MeetingOutcomeItem, item_id)
            outcome = await db.get(MeetingOutcomeSet, outcome_id)
            assert (item.owner_text, item.due_date_text) == ("  Исполнитель  ", "  Завтра  ")
            assert outcome.protocol_json is None
            setattr(item, field, "я" * (limit + 1))
            outcome.protocol_json = {"title": "Сохранённый документ"}
            await db.commit()
        with pytest.raises(DBAPIError, match="value too long"):
            async with client.app_state["engine"].begin() as connection:
                await connection.run_sync(migrate, "downgrade")
        async with client.app_state["sessionmaker"]() as db:
            item = await db.get(MeetingOutcomeItem, item_id)
            outcome = await db.get(MeetingOutcomeSet, outcome_id)
            assert getattr(item, field) == "я" * (limit + 1)
            assert outcome.protocol_json == {"title": "Сохранённый документ"}

    asyncio.run(run())


@pytest.mark.parametrize("title_source", ["user_confirmed", "calendar", "upload_provided", "generic"])
def test_protocol_pins_authoritative_title_and_recording_timezone(client, title_source):
    meeting_id = create_outcome_ready_meeting(client, "protocol-metadata-" + title_source)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            meeting.title = "Название из источника"
            meeting.title_source = title_source
            meeting.recording_display_timezone_offset_minutes = 300
            attempt = await ai_service.create_summary_candidate(
                db, workspace_id=meeting.workspace_id, meeting_id=meeting_id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-auto-v1", template_id=None, template_version=1,
                expected_current_outcome_set_id=None,
            )
            metadata = attempt.metadata_json["meeting_metadata"]
            assert metadata["title"] == (None if title_source == "generic" else meeting.title)
            assert metadata["recording_display_timezone_offset_minutes"] == 300
            assert metadata["recording_started_at"] == meeting.started_at.isoformat()
            await db.rollback()

    asyncio.run(run())
