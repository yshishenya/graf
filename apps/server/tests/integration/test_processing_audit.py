import asyncio
from uuid import UUID

from sqlalchemy import select

from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.db.models import ProcessingAuditEvent
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.processing import store


def test_processing_audit_persists_metadata_only(client) -> None:
    finalized = create_finalized_meeting(client, "processing-audit")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def record() -> dict:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            await store.record_processing_audit_event(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                processing_workflow_id=workflow.id,
                event_type="result_imported",
                metadata={"segment_count": 2, "transcript_text": "do not store", "api_key": "secret"},
            )
            event = await db.scalar(select(ProcessingAuditEvent).where(ProcessingAuditEvent.meeting_id == meeting_id))
            return event.metadata_json

    metadata = asyncio.run(record())
    assert metadata == {"segment_count": 2}


def test_processing_audit_persists_result_contract_classification_metadata(client) -> None:
    finalized = create_finalized_meeting(client, "processing-audit-result-contract")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def record() -> dict:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            await store.record_processing_audit_event(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                processing_workflow_id=workflow.id,
                event_type="processed_no_transcript",
                metadata={
                    "transcript_status": "unavailable",
                    "transcript_reason": "no_recognizable_speech",
                    "failure_reason": "no_recognizable_speech",
                    "failure_source": "input_audio",
                    "diagnostic_class": "processed_no_transcript",
                    "transcript_text": "do not store",
                    "api_key": "secret",
                },
            )
            event = await db.scalar(select(ProcessingAuditEvent).where(ProcessingAuditEvent.meeting_id == meeting_id))
            return event.metadata_json

    metadata = asyncio.run(record())
    assert metadata == {
        "transcript_status": "unavailable",
        "transcript_reason": "no_recognizable_speech",
        "failure_reason": "no_recognizable_speech",
        "failure_source": "input_audio",
        "diagnostic_class": "processed_no_transcript",
    }
