"""Deterministic, content-free fixtures for summary-type slot tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid5

from twobrain_rec_server.db.models import MeetingSummarySlot

FIXTURE_NAMESPACE = UUID("f04e5f3c-9d4c-4b36-a9cf-1f88d9b4f183")
AUTO_TEMPLATE_KEY = "auto"
MINUTES_TEMPLATE_KEY = "meeting_minutes"


@dataclass(frozen=True, slots=True)
class SummaryTypeRevisionFixture:
    """Opaque identities only; no summary text, transcript, or participant data."""

    workspace_id: UUID
    meeting_id: UUID
    template_key: str
    slot_id: UUID
    current_outcome_set_id: UUID
    replacement_outcome_set_id: UUID


def _id(*parts: str) -> UUID:
    return uuid5(FIXTURE_NAMESPACE, ":".join(parts))


def two_type_revision_fixtures(
    workspace_id: UUID,
    meeting_id: UUID,
) -> tuple[SummaryTypeRevisionFixture, SummaryTypeRevisionFixture]:
    """Return two independent type lineages for cross-slot isolation tests."""

    return tuple(
        SummaryTypeRevisionFixture(
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            template_key=template_key,
            slot_id=_id(str(meeting_id), template_key, "slot"),
            current_outcome_set_id=_id(str(meeting_id), template_key, "current"),
            replacement_outcome_set_id=_id(str(meeting_id), template_key, "replacement"),
        )
        for template_key in (AUTO_TEMPLATE_KEY, MINUTES_TEMPLATE_KEY)
    )


def empty_type_slots(
    workspace_id: UUID,
    meeting_id: UUID,
) -> list[MeetingSummarySlot]:
    """Build two null-current slots without embedding any private meeting data."""

    return [
        MeetingSummarySlot(
            id=_id(str(meeting_id), template_key, "slot"),
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            template_key=template_key,
            current_outcome_set_id=None,
            current_binding_class=None,
            is_meeting_default=template_key == AUTO_TEMPLATE_KEY,
            default_resolution_source="explicit_meeting" if template_key == AUTO_TEMPLATE_KEY else None,
            default_resolution_version="fixture-v1" if template_key == AUTO_TEMPLATE_KEY else None,
            default_resolved_at=(
                datetime(2026, 1, 1, tzinfo=UTC) if template_key == AUTO_TEMPLATE_KEY else None
            ),
        )
        for template_key in (AUTO_TEMPLATE_KEY, MINUTES_TEMPLATE_KEY)
    ]
