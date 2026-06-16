from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class DeletionLifecycleSeed:
    ready_meeting_id: UUID
    processing_meeting_id: UUID | None = None
    deleted_meeting_id: UUID | None = None
