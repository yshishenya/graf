"""Closed command inputs. Domain handlers add their own typed commands here."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter

Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class MeetingCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: UUID
    expected_version: Annotated[int, Field(strict=True, ge=1)]
    reason: Reason


class ReprocessMeeting(MeetingCommand):
    kind: Literal["meeting.reprocess"]


class DeleteMeeting(MeetingCommand):
    kind: Literal["meeting.delete"]


Command = Annotated[ReprocessMeeting | DeleteMeeting, Field(discriminator="kind")]
COMMAND_ADAPTER = TypeAdapter(Command)
COMMAND_PERMISSIONS = {
    "meeting.reprocess": "processing.reprocess",
    "meeting.delete": "deletion.manage",
}


class CommitOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preview_id: UUID
    expected_preview_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
