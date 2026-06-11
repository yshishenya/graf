import asyncio
from uuid import UUID

from sqlalchemy import select

from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.db.models import ProcessingDependencyState
from twobrain_rec_server.domain.statuses import (
    ProcessingDependencyName,
    ProcessingDependencyStateValue,
)
from twobrain_rec_server.processing import store


def test_processing_dependency_state_records_future_deletion_truth_without_claiming_delete(client) -> None:
    finalized = create_finalized_meeting(client, "processing-dependency")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def record() -> tuple[str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            await store.set_dependency_state(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                dependency=ProcessingDependencyName.MEDIASCRIBE,
                state=ProcessingDependencyStateValue.DELETION_PENDING_FUTURE,
                external_reference="job_safe_ref",
            )
            state = await db.scalar(
                select(ProcessingDependencyState).where(
                    ProcessingDependencyState.meeting_id == meeting_id,
                    ProcessingDependencyState.dependency == "mediascribe",
                )
            )
            return state.state, state.external_reference

    assert asyncio.run(record()) == ("deletion_pending_future", "job_safe_ref")
