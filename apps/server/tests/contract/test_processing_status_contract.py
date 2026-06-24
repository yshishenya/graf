import asyncio
from pathlib import Path
from uuid import UUID

import yaml
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting, enable_processing_autostart
from twobrain_rec_server.db.models import ProcessingAuditEvent

ROOT = Path(__file__).parents[4]


def test_processing_status_openapi_contract_has_content_safe_fields() -> None:
    contract = yaml.safe_load(
        (ROOT / "specs/015-mediascribe-processing-pipeline/contracts/processing-status.openapi.yaml").read_text(
            encoding="utf-8"
        )
    )
    properties = contract["components"]["schemas"]["ProcessingStatusResponse"]["properties"]
    assert "transcript_available" in properties
    assert "diarization_available" in properties
    assert "workflow_id" in properties
    assert "transcript_text" not in properties
    assert "audio_download_url" not in properties
    assert "mediascribe_api_key" not in properties


def test_processing_status_endpoint_returns_no_content_or_secret_fields(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "processing-status-contract")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    pickup = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": str(meeting_id)},
    )
    assert pickup.status_code == 202
    status = client.get(f"/api/v1/meetings/{meeting_id}/processing", headers=auth_headers())
    assert status.status_code == 200
    payload = status.json()
    assert payload["workflow_id"] == f"processing/{media_revision_id}"
    assert payload["mediascribe_job_id_present"] is False
    forbidden = {"transcript_text", "audio_download_url", "mediascribe_job_id", "api_key", "signed_url"}
    assert forbidden.isdisjoint(payload)


def test_finalize_autostart_audit_metadata_is_content_safe(client) -> None:
    enable_processing_autostart(client, FakeTemporalClient())
    finalized = create_finalized_meeting(client, "processing-autostart-audit")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])

    async def audit_metadata() -> dict[str, object]:
        async with client.app_state["sessionmaker"]() as db:
            event = await db.scalar(
                select(ProcessingAuditEvent)
                .where(
                    ProcessingAuditEvent.meeting_id == meeting_id,
                    ProcessingAuditEvent.event_type == "workflow_started",
                )
                .order_by(ProcessingAuditEvent.created_at.desc())
            )
            assert event is not None
            return event.metadata_json

    metadata = asyncio.run(audit_metadata())
    assert set(metadata) <= {"workflow_id", "started_count"}
    serialized = str(metadata).lower()
    forbidden = {"transcript", "audio_download_url", "api_key", "signed_url", "/users/"}
    assert all(token not in serialized for token in forbidden)
