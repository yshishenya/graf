"""Deletion removes frozen documents and queued delivery addresses before FK parents."""
import asyncio
from uuid import UUID

from sqlalchemy import func, select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.integration.test_summary_sharing import prepare
from twobrain_rec_server.db.models import (
    DispatchIntent,
    PublishedMeetingSummary,
    SummaryDeliveryBatch,
    SummaryRecipientDelivery,
)


def test_delete_removes_publication_and_unsent_batch(client, tmp_path):
    meeting, template = prepare(client, tmp_path)
    base = f"/api/v1/cabinet/meetings/{meeting}/summary-sharing"
    link = client.post(base + "/link", headers=auth_headers(), json={"template_key": template})
    assert link.status_code == 200, link.text
    batch = client.post(base + "/batches", headers=auth_headers(), json={"template_key": template, "recipients": ["synthetic@example.test"], "idempotency_key": "delete-regression"})
    assert batch.status_code == 200, batch.text
    response = client.post(f"/api/v1/cabinet/meetings/{meeting}/deletion-requests", headers=auth_headers(), json={"confirmation_boundary": "Delete this meeting everywhere GRAF controls."})
    assert response.status_code == 202, response.text
    assert client.get(link.json()["share_url"].split("https://graf.example.test")[-1]).status_code == 404
    async def inspect():
        async with client.app.state.db_sessionmaker() as db:
            for model in (PublishedMeetingSummary, SummaryDeliveryBatch):
                assert await db.scalar(select(func.count()).select_from(model).where(model.meeting_id == UUID(str(meeting)))) == 0
            assert await db.scalar(select(func.count()).select_from(SummaryRecipientDelivery).where(SummaryRecipientDelivery.batch_id == UUID(batch.json()["batch_id"]))) == 0
            intents = (await db.scalars(select(DispatchIntent).where(DispatchIntent.meeting_id == UUID(str(meeting)), DispatchIntent.intent_kind == "summary_delivery"))).all()
            assert intents and all(row.state == "cancelled" for row in intents)
    asyncio.run(inspect())
