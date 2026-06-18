from __future__ import annotations

import asyncio
from uuid import uuid4

from twobrain_rec_server.db.models import MediaRevision, Meeting, ProcessingPlaceholder
from twobrain_rec_server.ingest.store import MeetingRecord, persist_meeting


class RecordingAsyncSession:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def get(self, model: type[object], _id: object) -> None:
        self.calls.append(f"get:{model.__name__}")
        return None

    def add(self, model: object) -> None:
        self.calls.append(f"add:{type(model).__name__}")

    async def flush(self) -> None:
        self.calls.append("flush")

    async def commit(self) -> None:
        self.calls.append("commit")


def test_new_meeting_persistence_flushes_parent_before_revision() -> None:
    session = RecordingAsyncSession()
    meeting = MeetingRecord(
        id=uuid4(),
        workspace_id=uuid4(),
        organization_id=uuid4(),
        created_by_user_id=uuid4(),
        device_id=uuid4(),
        local_recording_id="postgres-fk-order",
        duration_seconds=60,
        title=None,
    )

    asyncio.run(persist_meeting(session, meeting))

    assert session.calls == [
        f"get:{Meeting.__name__}",
        f"add:{Meeting.__name__}",
        "flush",
        f"add:{MediaRevision.__name__}",
        f"add:{ProcessingPlaceholder.__name__}",
        "commit",
    ]
