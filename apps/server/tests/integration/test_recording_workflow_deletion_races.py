from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.cabinet import create_outcome_ready_meeting
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.cabinet.access import AccessDecision
from twobrain_rec_server.cabinet.egress import create_content_export, create_export_package
from twobrain_rec_server.cabinet.exports import ExportSelection
from twobrain_rec_server.db.models import (
    ExportPackage,
    GenerationCall,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingShareGrant,
    MeetingShareInvitation,
    ProcessingResult,
)
from twobrain_rec_server.outcomes.ai_service import (
    publish_candidate_generation_calls,
    publish_generation_call,
)
from twobrain_rec_server.outcomes.prompts import (
    canonical_json,
    outcome_config,
    prompt_snapshot_hash,
)

BOUNDED_COPY = "Delete this meeting everywhere GRAF controls."
PLAINTEXT_MARKER = "synthetic plaintext transcript marker for retained observability"


@dataclass
class _WorkflowHandle:
    workflow_id: str
    cancelled: list[str]

    async def cancel(self) -> None:
        self.cancelled.append(self.workflow_id)


@dataclass
class _TemporalClient:
    requested: list[str] = field(default_factory=list)
    cancelled: list[str] = field(default_factory=list)

    def get_workflow_handle(self, workflow_id: str) -> _WorkflowHandle:
        self.requested.append(workflow_id)
        return _WorkflowHandle(workflow_id, self.cancelled)


class _LangfuseClient:
    def get_prompt(self, *_args, **_kwargs) -> object:
        return object()


def test_deletion_wins_pending_egress_and_preserves_completed_observability_delivery(
    client,
) -> None:
    meeting_id = create_outcome_ready_meeting(client, "recording-workflow-deletion-race")
    seeded = asyncio.run(_seed_race_rows(client, meeting_id))
    temporal = _TemporalClient()
    client.app.state.temporal_client = temporal

    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    state = asyncio.run(_race_state(client, seeded))

    assert response.status_code == 202
    assert temporal.requested == [seeded.workflow_id]
    assert temporal.cancelled == [seeded.workflow_id]
    assert state["attempt_status"] == "cancelled"
    assert state["attempt_failure"] == "meeting_deleted"
    assert state["attempt_prompt_name"] == "graf/meeting-outcome/auto"
    assert state["call_state"] == "completed"
    assert state["call_export_status"] == "pending"
    assert state["call_transcript"] == PLAINTEXT_MARKER
    assert state["grant_purged"] is True
    assert state["invitation_purged"] is True
    assert state["export_purged"] is True
    export_block_codes = asyncio.run(_stale_export_mutations(client, meeting_id, seeded.result_id))
    assert export_block_codes[0] in {"meeting_deletion_active", "export_unavailable"}
    assert export_block_codes[1] == "meeting_deletion_active"

    report = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-report",
        headers=auth_headers(),
    )
    report_rows = report.json()["artifact_states"] + report.json()["dependencies"]
    rows = {row["artifact_class"]: row for row in report_rows}
    assert rows["generation_call"]["state"] == "observability_retained"
    assert rows["langfuse"]["state"] == "observability_retained"
    assert rows["temporal_history"]["state"] == "observability_retained"
    assert PLAINTEXT_MARKER not in report.text

    published: list[str] = []
    with (
        patch(
            "twobrain_rec_server.outcomes.ai_service.create_langfuse_client",
            return_value=_LangfuseClient(),
        ),
        patch(
            "twobrain_rec_server.outcomes.ai_service.publish_completed_generation",
            side_effect=lambda _client, *, call, **_kwargs: published.append(call.transcript_text),
        ),
        patch("twobrain_rec_server.outcomes.ai_service.shutdown_langfuse"),
    ):
        asyncio.run(
            publish_generation_call(
                client.app_state["sessionmaker"],
                workspace_id=WORKSPACE_ID,
                call_id=seeded.call_id,
                settings=client.app.state.settings,
                activity_attempt=2,
            )
        )

    assert published == [PLAINTEXT_MARKER]
    assert asyncio.run(_generation_call_export_status(client, seeded.call_id)) == "confirmed"


def test_retryable_response_is_published_from_retained_failed_call(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "retryable-response-observability")
    seeded = asyncio.run(_seed_race_rows(client, meeting_id))
    second_call_id = asyncio.run(_seed_retryable_then_success(client, seeded.call_id))

    published: list[tuple[int, str]] = []
    with (
        patch(
            "twobrain_rec_server.outcomes.ai_service.create_langfuse_client",
            return_value=_LangfuseClient(),
        ),
        patch(
            "twobrain_rec_server.outcomes.ai_service.publish_completed_generation",
            side_effect=lambda _client, *, call, **_kwargs: published.append(
                (call.provider_attempt, call.call_state)
            ),
        ),
        patch("twobrain_rec_server.outcomes.ai_service.shutdown_langfuse"),
    ):
        result = asyncio.run(
            publish_candidate_generation_calls(
                client.app_state["sessionmaker"],
                workspace_id=WORKSPACE_ID,
                candidate_id=UUID(seeded.workflow_id.rsplit("/", 1)[1]),
                settings=client.app.state.settings,
                activity_attempt=6,
            )
        )

    assert result == {
        "candidate_terminal": True,
        "pending_count": 0,
        "published_count": 2,
    }
    assert published == [(1, "failed"), (2, "completed")]
    assert asyncio.run(_generation_call_export_status(client, seeded.call_id)) == "confirmed"
    assert asyncio.run(_generation_call_export_status(client, second_call_id)) == "confirmed"


@dataclass(frozen=True)
class _SeededRows:
    attempt_id: UUID
    call_id: UUID
    grant_id: UUID
    invitation_id: UUID
    export_id: UUID
    result_id: UUID
    workflow_id: str


async def _seed_race_rows(client, meeting_id: UUID) -> _SeededRows:
    async with client.app_state["sessionmaker"]() as db:
        result = await db.scalar(
            select(ProcessingResult)
            .where(ProcessingResult.meeting_id == meeting_id)
            .order_by(ProcessingResult.created_at.desc())
        )
        assert result is not None
        candidate_id = uuid4()
        workflow_id = f"outcome-generation/{candidate_id}"
        prompt_definition = [
            {
                "role": "user",
                "content": (
                    "{{transcript_json}} {{output_language}} "
                    "{{detail_level}} {{template_sections_json}}"
                ),
            }
        ]
        prompt_config = outcome_config(schema_name="graf_meeting_outcome")
        request_json = {"model": "gpt-5.6-luna", "messages": [PLAINTEXT_MARKER]}
        raw_response_json = {"result": PLAINTEXT_MARKER}
        validated_result_json = {"summary": PLAINTEXT_MARKER}
        attempt = MeetingOutcomeGenerationAttempt(
            workspace_id=WORKSPACE_ID,
            meeting_id=meeting_id,
            processing_result_id=result.id,
            source_result_id=result.id,
            candidate_id=candidate_id,
            status="generating",
            generator_version="outcomes-ai-v1",
            prompt_name="graf/meeting-outcome/auto",
            prompt_version=1,
            prompt_source="langfuse_production",
            prompt_definition=prompt_definition,
            prompt_config=prompt_config,
            prompt_hash=prompt_snapshot_hash(
                prompt=prompt_definition,
                config=prompt_config,
            ),
            model_route="gpt-5.6-luna",
            workflow_id=workflow_id,
        )
        call = GenerationCall(
            workspace_id=WORKSPACE_ID,
            meeting_id=meeting_id,
            candidate_id=candidate_id,
            provider_attempt=1,
            call_sequence=1,
            trace_id="b" * 32,
            observation_id="c" * 32,
            call_state="completed",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            request_json=request_json,
            transcript_text=PLAINTEXT_MARKER,
            raw_response_json=raw_response_json,
            validated_result_json=validated_result_json,
            request_hash=_content_hash(request_json),
            transcript_hash=sha256(PLAINTEXT_MARKER.encode()).hexdigest(),
            raw_response_hash=_content_hash(raw_response_json),
            validated_result_hash=_content_hash(validated_result_json),
            export_status="pending",
        )
        grant = MeetingShareGrant(
            workspace_id=WORKSPACE_ID,
            meeting_id=meeting_id,
            grant_type="user",
            grantee_user_id=USER_ID,
            share_token_hash="grant-token-hash",
            created_by_user_id=USER_ID,
            status="active",
        )
        invitation = MeetingShareInvitation(
            workspace_id=WORKSPACE_ID,
            meeting_id=meeting_id,
            invited_by_user_id=USER_ID,
            normalized_address_hash="address-hash",
            encrypted_delivery_address="synthetic@example.test",
            token_hash="invitation-token-hash",
            status="pending",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        export = ExportPackage(
            workspace_id=WORKSPACE_ID,
            meeting_id=meeting_id,
            requested_by_user_id=USER_ID,
            status="requested",
            included_artifacts=["transcript"],
            excluded_artifacts=[],
            manifest_json={"private": PLAINTEXT_MARKER},
        )
        db.add_all([attempt, call, grant, invitation, export])
        await db.commit()
        return _SeededRows(
            attempt_id=attempt.id,
            call_id=call.id,
            grant_id=grant.id,
            invitation_id=invitation.id,
            export_id=export.id,
            result_id=result.id,
            workflow_id=workflow_id,
        )


async def _race_state(client, seeded: _SeededRows) -> dict[str, object]:
    async with client.app_state["sessionmaker"]() as db:
        attempt = await db.get(MeetingOutcomeGenerationAttempt, seeded.attempt_id)
        call = await db.get(GenerationCall, seeded.call_id)
        grant = await db.get(MeetingShareGrant, seeded.grant_id)
        invitation = await db.get(MeetingShareInvitation, seeded.invitation_id)
        export = await db.get(ExportPackage, seeded.export_id)
        assert attempt is not None
        assert call is not None
        return {
            "attempt_status": attempt.status,
            "attempt_failure": attempt.failure_code,
            "attempt_prompt_name": attempt.prompt_name,
            "call_state": call.call_state,
            "call_export_status": call.export_status,
            "call_transcript": call.transcript_text,
            "grant_purged": grant is None,
            "invitation_purged": invitation is None,
            "export_purged": export is None,
        }


async def _seed_retryable_then_success(client, call_id: UUID) -> UUID:
    async with client.app_state["sessionmaker"]() as db:
        call = await db.get(GenerationCall, call_id)
        assert call is not None
        call.call_state = "failed"
        attempt = await db.scalar(
            select(MeetingOutcomeGenerationAttempt).where(
                MeetingOutcomeGenerationAttempt.candidate_id == call.candidate_id
            )
        )
        assert attempt is not None
        attempt.status = "candidate"
        second = GenerationCall(
            workspace_id=call.workspace_id,
            meeting_id=call.meeting_id,
            candidate_id=call.candidate_id,
            provider_attempt=2,
            call_sequence=1,
            trace_id=call.trace_id,
            observation_id="d" * 32,
            call_state="completed",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            request_json=call.request_json,
            transcript_text=call.transcript_text,
            raw_response_json=call.raw_response_json,
            validated_result_json=call.validated_result_json,
            request_hash=call.request_hash,
            transcript_hash=call.transcript_hash,
            raw_response_hash=call.raw_response_hash,
            validated_result_hash=call.validated_result_hash,
            export_status="pending",
        )
        db.add(second)
        await db.commit()
        return second.id


async def _generation_call_export_status(client, call_id: UUID) -> str:
    async with client.app_state["sessionmaker"]() as db:
        call = await db.get(GenerationCall, call_id)
        assert call is not None
        return call.export_status


async def _stale_export_mutations(
    client,
    meeting_id: UUID,
    result_id: UUID,
) -> list[str]:
    stale_meeting = Meeting(
        id=meeting_id,
        workspace_id=WORKSPACE_ID,
        created_by_user_id=USER_ID,
        device_id=DEVICE_ID,
        local_recording_id="stale-before-deletion",
        duration_seconds=60,
        deletion_state="none",
    )
    access = AccessDecision(
        state="owner",
        label="Owner",
        reason=None,
        can_view=True,
        can_share=True,
        can_manage_team_visibility=True,
        can_download=True,
        can_export=True,
    )
    codes: list[str] = []
    async with client.app_state["sessionmaker"]() as db:
        result = await db.get(ProcessingResult, result_id)
        assert result is not None
        with pytest.raises(ProblemDetail) as error:
            await create_content_export(
                db,
                meeting=stale_meeting,
                access=access,
                result=result,
                selection=ExportSelection(
                    content_scope="transcript",
                    format="txt",
                    processing_result_id=result_id,
                    outcome_set_id=None,
                    include_speaker_labels=True,
                    include_timestamps=True,
                    include_evidence=False,
                ),
                actor_user_id=USER_ID,
                device_id=DEVICE_ID,
            )
        codes.append(error.value.code)
    async with client.app_state["sessionmaker"]() as db:
        result = await db.get(ProcessingResult, result_id)
        assert result is not None
        with pytest.raises(ProblemDetail) as error:
            await create_export_package(
                db,
                meeting=stale_meeting,
                access=access,
                requested_artifacts=["transcript"],
                result=result,
                actor_user_id=USER_ID,
                device_id=DEVICE_ID,
            )
        codes.append(error.value.code)
    return codes


def _content_hash(value: object) -> str:
    return sha256(canonical_json(value).encode()).hexdigest()
