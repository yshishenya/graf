from __future__ import annotations

import asyncio

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import create_outcome_ready_meeting
from twobrain_rec_server.db.models import MeetingOutcomeItem, MeetingOutcomeSet
from twobrain_rec_server.outcomes.service import ensure_outcomes_for_meeting

BOUNDED_COPY = "Delete this meeting everywhere 2brain Rec controls."


def test_deletion_report_accounts_for_stored_outcomes_without_content(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "outcome-deletion-report")
    asyncio.run(ensure_outcomes_for_meeting(client.app_state["sessionmaker"], meeting_id=meeting_id))
    outcome_text = asyncio.run(_first_outcome_text(client, meeting_id))
    assert outcome_text

    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    report = client.get(f"/api/v1/cabinet/meetings/{meeting_id}/deletion-report", headers=auth_headers())
    lifecycle_state = asyncio.run(_outcome_lifecycle_state(client, meeting_id))
    content_count = asyncio.run(_stored_outcome_content_count(client, meeting_id))

    assert delete_response.status_code == 202
    assert report.status_code == 200
    notes_row = next(row for row in report.json()["artifact_states"] if row["artifact_class"] == "notes_summary")
    assert notes_row["control_scope"] == "controlled"
    assert notes_row["state"] == "purged"
    assert lifecycle_state == "deleted"
    assert content_count == 0
    assert outcome_text not in report.text
    assert "source_refs_json" not in report.text


async def _first_outcome_text(client, meeting_id) -> str:
    async with client.app_state["sessionmaker"]() as db:
        text = await db.scalar(
            select(MeetingOutcomeItem.text)
            .where(MeetingOutcomeItem.meeting_id == meeting_id)
            .where(MeetingOutcomeItem.text.is_not(None))
            .order_by(MeetingOutcomeItem.category, MeetingOutcomeItem.sequence)
        )
        assert text is not None
        return text


async def _outcome_lifecycle_state(client, meeting_id) -> str:
    async with client.app_state["sessionmaker"]() as db:
        state = await db.scalar(
            select(MeetingOutcomeSet.lifecycle_state).where(MeetingOutcomeSet.meeting_id == meeting_id)
        )
        assert state is not None
        return state


async def _stored_outcome_content_count(client, meeting_id) -> int:
    async with client.app_state["sessionmaker"]() as db:
        items = (
            await db.scalars(select(MeetingOutcomeItem).where(MeetingOutcomeItem.meeting_id == meeting_id))
        ).all()
        return sum(1 for item in items if item.text or item.owner_text or item.due_date_text or item.source_refs_json)
