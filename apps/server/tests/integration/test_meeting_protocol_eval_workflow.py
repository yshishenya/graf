"""Synthetic real-Temporal proof for the isolated evaluator's shared workflow."""
import asyncio
import shutil
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer

from tests.fixtures.cabinet import create_outcome_ready_meeting
from tests.fixtures.meeting_protocol import (
    extraction_result,
    pin_evaluation_prompts,
    protocol_evaluation_runtime,
    protocol_gateway_response,
    protocol_result,
)
from twobrain_rec_server.cli.meeting_protocol_eval import mirror_source, snapshot_source
from twobrain_rec_server.cli.meeting_protocol_eval_runtime import EvaluationActivities
from twobrain_rec_server.db.models import (
    GenerationCall,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingSummarySlot,
    RegisteredDevice,
    Workspace,
)
from twobrain_rec_server.outcomes import ai_service
from twobrain_rec_server.outcomes.generator import canonical_transcript
from twobrain_rec_server.outcomes.prompts import EXTRACTOR_PROMPT_NAME, VERIFIER_PROMPT_NAME
from twobrain_rec_server.workflows.outcome_generation_workflow import OutcomeGenerationWorkflow
from twobrain_rec_server.workflows.temporal_client import outcome_generation_task_queue


@pytest.mark.skipif(shutil.which("temporal") is None, reason="Synthetic real-workflow check requires local Temporal CLI")
@pytest.mark.parametrize("verdict", ["pass", "fail"])
def test_eval_http_dispatch_uses_real_temporal_history_and_never_accepts(client, monkeypatch, verdict, tmp_path):
    meeting_id = create_outcome_ready_meeting(client, "synthetic-temporal-protocol-evaluation")
    invoked = []
    checked = []
    monkeypatch.setattr(ai_service, "_read_secret", lambda _path: "synthetic-unused")

    async def run(temporal, runtime):
        sessions, settings = runtime.sessions, runtime.settings
        async with client.app_state["sessionmaker"]() as db:
            source = await snapshot_source(db, meeting_id)
        async with sessions() as db:
            await mirror_source(db, source, runtime.run_id, create_attempt=False)
            meeting = await db.get(Meeting, meeting_id)
            workspace = await db.get(Workspace, meeting.workspace_id)
            device = await db.scalar(select(RegisteredDevice).where(RegisteredDevice.workspace_id == meeting.workspace_id))
            headers = {
                "X-Organization-Id": str(workspace.organization_id), "X-Workspace-Id": str(workspace.id),
                "X-User-Id": str(meeting.created_by_user_id), "X-Device-Id": str(device.id),
            }
            await db.commit()
        monkeypatch.setattr(client.app.state, "db_sessionmaker", sessions)
        monkeypatch.setattr(client.app.state.settings, "outcome_generation_enabled", True)
        monkeypatch.setattr(client.app.state.settings, "temporal_task_queue", settings.temporal_task_queue)
        client.app.state.outcome_temporal_client = temporal.client
        response = await asyncio.to_thread(
            client.post, f"/api/v1/cabinet/meetings/{meeting_id}/summaries/graf-auto-v1/ensure",
            headers=headers, json={"idempotency_key": uuid4().hex},
        )
        assert response.status_code == 202, response.json()
        async with sessions() as db:
            attempt = await db.scalar(select(MeetingOutcomeGenerationAttempt).where(
                MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
            ))
            assert attempt is not None
            pin_evaluation_prompts(attempt, settings=settings, workdir=runtime.workdir, run_id=runtime.run_id)
            segments = await ai_service._candidate_segments(db, attempt)
            attempt.metadata_json = {
                **attempt.metadata_json, "evaluation_only": True,
                "evaluation_source": {"meeting_id": str(meeting_id), "snapshot_hash": source["source_hash"]},
            }
            workspace_id, candidate_id = attempt.workspace_id, attempt.candidate_id
            await db.commit()

        async def source_check(source_id, source_hash):
            assert source_id == str(meeting_id) and source_hash == source["source_hash"]
            async with client.app_state["sessionmaker"]() as db:
                assert (await snapshot_source(db, meeting_id))["source_hash"] == source_hash
            checked.append(True)

        async def generate(_self, *, snapshot, messages, **_kwargs):
            invoked.append(snapshot.name)
            result = (extraction_result(segments) if snapshot.name == EXTRACTOR_PROMPT_NAME else
                      {"verdict": "pass", "findings": []} if snapshot.name == VERIFIER_PROMPT_NAME else protocol_result(segments))
            if snapshot.name == VERIFIER_PROMPT_NAME and verdict == "fail":
                result = {"verdict": "fail", "findings": [{
                    "code": "missing_topic", "path": "/topics",
                    "source_refs": protocol_result(segments)["executive_summary"][0]["source_refs"],
                }]}
            return protocol_gateway_response(snapshot, messages, result)

        async def publish(_sessions, **_kwargs):
            async with sessions() as db:
                rows = (await db.scalars(select(GenerationCall).where(GenerationCall.candidate_id == candidate_id))).all()
                for row in rows:
                    row.export_status = "confirmed"
                candidate = await db.get(MeetingOutcomeGenerationAttempt, attempt.id)
                terminal = candidate.status not in ai_service.ACTIVE_CANDIDATE_STATUSES
                await db.commit()
            return {"candidate_terminal": terminal, "pending_count": 0, "published_count": len(rows)}

        monkeypatch.setattr(ai_service.LiteLLMGateway, "generate", generate)
        monkeypatch.setattr(ai_service, "publish_candidate_generation_calls", publish)
        activities = EvaluationActivities(settings, sessions, SimpleNamespace(check=source_check))
        async with activities.worker(temporal.client):
            handle = temporal.client.get_workflow_handle(f"outcome-generation/{candidate_id}")
            assert (await handle.describe()).task_queue == outcome_generation_task_queue(settings)
            result = await asyncio.wait_for(handle.result(), timeout=45)
            history = await handle.fetch_history()
            assert result["state"] == ("candidate" if verdict == "pass" else "failed")
            # Full plaintext transcript is recorded in actual ActivityCompleted payloads.
            outputs = []
            for event in history.events:
                if event.HasField("activity_task_completed_event_attributes"):
                    outputs.extend(await temporal.client.data_converter.decode(
                        event.activity_task_completed_event_attributes.result.payloads,
                    ))
            chunks = [row for row in outputs if isinstance(row, dict) and "transcript_utf8" in row]
            assert "".join(row["transcript_utf8"] for row in chunks) == canonical_transcript(segments)
            await Replayer(workflows=[OutcomeGenerationWorkflow]).replay_workflow(history)
        response = await asyncio.to_thread(
            client.get, f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}",
            headers=headers,
        )
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "private, no-store"
        assert response.json()["current_outcome_set_id"] is None
        async with sessions() as db:
            calls = (await db.scalars(select(GenerationCall).where(GenerationCall.candidate_id == candidate_id))).all()
            assert len(calls) == len(invoked) == 3
            assert all(call.call_state == "completed" for call in calls)
            slot = await db.scalar(select(MeetingSummarySlot).where(MeetingSummarySlot.workspace_id == workspace_id, MeetingSummarySlot.meeting_id == meeting_id))
            assert slot.current_outcome_set_id is None
            assert len(checked) >= 9

    async def evaluate(runtime):
        async with await WorkflowEnvironment.start_local(dev_server_existing_path=shutil.which("temporal")) as temporal:
            await run(temporal, runtime)

    with protocol_evaluation_runtime(tmp_path) as runtime:
        asyncio.run(evaluate(runtime))
