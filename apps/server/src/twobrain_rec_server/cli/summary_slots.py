"""Metadata-only reconciliation for the slot-backed summary lifecycle."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select

from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.models import Meeting, MeetingOutcomeSet, MeetingSummarySlot
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    maintenance_context_settings,
)

OPERATION_NAME = "summary_slots_reconciliation"
ACTOR_ID = "summary-slots-cli"
FEATURE_AREA = "outcomes"
DEFAULT_LIMIT = 1000


@dataclass(frozen=True, slots=True)
class SlotMetadata:
    slot_id: UUID
    workspace_id: UUID
    meeting_id: UUID
    template_key: str
    is_meeting_default: bool
    current_outcome_set_id: UUID | None
    current_binding_class: str | None
    legacy_migration_proof_hash: str | None
    meeting_workspace_id: UUID | None
    meeting_current_outcome_set_id: UUID | None
    meeting_deleted: bool
    outcome_id: UUID | None
    outcome_workspace_id: UUID | None
    outcome_meeting_id: UUID | None
    outcome_template_key: str | None


def _violation_counts(rows: list[SlotMetadata]) -> Counter[str]:
    violations: Counter[str] = Counter()
    defaults_by_meeting: defaultdict[UUID, int] = defaultdict(int)
    slots_by_meeting: defaultdict[UUID, int] = defaultdict(int)
    for row in rows:
        slots_by_meeting[row.meeting_id] += 1
        if row.is_meeting_default:
            defaults_by_meeting[row.meeting_id] += 1
        if row.meeting_workspace_id is None:
            violations["slot_meeting_missing"] += 1
            continue
        if row.meeting_workspace_id != row.workspace_id:
            violations["slot_scope_mismatch"] += 1
        if row.current_outcome_set_id is None:
            if row.current_binding_class is not None or row.legacy_migration_proof_hash is not None:
                violations["empty_slot_has_binding_metadata"] += 1
        else:
            if row.outcome_id is None:
                violations["current_outcome_missing"] += 1
            else:
                if row.outcome_workspace_id != row.workspace_id or row.outcome_meeting_id != row.meeting_id:
                    violations["current_outcome_scope_mismatch"] += 1
                if row.outcome_template_key != row.template_key:
                    violations["current_outcome_template_mismatch"] += 1
            if row.current_binding_class not in {"verified_complete", "migrated_legacy_read_only"}:
                violations["current_binding_class_invalid"] += 1
        if (
            row.is_meeting_default
            and row.meeting_current_outcome_set_id != row.current_outcome_set_id
            and not row.meeting_deleted
        ):
            violations["legacy_pointer_mismatch"] += 1

    for meeting_id, _slot_count in slots_by_meeting.items():
        default_count = defaults_by_meeting[meeting_id]
        if default_count == 0:
            violations["meeting_default_missing"] += 1
        elif default_count > 1:
            violations["meeting_default_ambiguous"] += 1
    return violations


def summarize_slot_metadata(rows: list[SlotMetadata], *, truncated: bool = False) -> dict[str, Any]:
    violations = _violation_counts(rows)
    result: dict[str, Any] = {
        "slot_count": len(rows),
        "meeting_count": len({row.meeting_id for row in rows}),
        "default_slot_count": sum(row.is_meeting_default for row in rows),
        "current_slot_count": sum(row.current_outcome_set_id is not None for row in rows),
        "migrated_legacy_slot_count": sum(
            row.current_binding_class == "migrated_legacy_read_only" for row in rows
        ),
        "violations": dict(sorted(violations.items())),
        "status": "attention" if violations or truncated else "ok",
    }
    if truncated:
        result["truncated"] = True
    return result


async def _load_rows(
    session,
    *,
    meeting_id: UUID | None,
    limit: int,
) -> tuple[list[SlotMetadata], bool]:
    statement = (
        select(
            MeetingSummarySlot.id.label("slot_id"),
            MeetingSummarySlot.workspace_id,
            MeetingSummarySlot.meeting_id,
            MeetingSummarySlot.template_key,
            MeetingSummarySlot.is_meeting_default,
            MeetingSummarySlot.current_outcome_set_id,
            MeetingSummarySlot.current_binding_class,
            MeetingSummarySlot.legacy_migration_proof_hash,
            Meeting.workspace_id.label("meeting_workspace_id"),
            Meeting.current_outcome_set_id.label("meeting_current_outcome_set_id"),
            Meeting.deleted_at,
            MeetingOutcomeSet.id.label("outcome_id"),
            MeetingOutcomeSet.workspace_id.label("outcome_workspace_id"),
            MeetingOutcomeSet.meeting_id.label("outcome_meeting_id"),
            MeetingOutcomeSet.template_key.label("outcome_template_key"),
        )
        .select_from(MeetingSummarySlot)
        .outerjoin(Meeting, Meeting.id == MeetingSummarySlot.meeting_id)
        .outerjoin(MeetingOutcomeSet, MeetingOutcomeSet.id == MeetingSummarySlot.current_outcome_set_id)
        .order_by(MeetingSummarySlot.meeting_id, MeetingSummarySlot.template_key)
        .limit(limit + 1)
    )
    if meeting_id is not None:
        statement = statement.where(MeetingSummarySlot.meeting_id == meeting_id)
    values = (await session.execute(statement)).mappings().all()
    truncated = len(values) > limit
    rows = values[:limit]
    return [
        SlotMetadata(
            slot_id=row["slot_id"],
            workspace_id=row["workspace_id"],
            meeting_id=row["meeting_id"],
            template_key=row["template_key"],
            is_meeting_default=bool(row["is_meeting_default"]),
            current_outcome_set_id=row["current_outcome_set_id"],
            current_binding_class=row["current_binding_class"],
            legacy_migration_proof_hash=row["legacy_migration_proof_hash"],
            meeting_workspace_id=row["meeting_workspace_id"],
            meeting_current_outcome_set_id=row["meeting_current_outcome_set_id"],
            meeting_deleted=row["deleted_at"] is not None,
            outcome_id=row["outcome_id"],
            outcome_workspace_id=row["outcome_workspace_id"],
            outcome_meeting_id=row["outcome_meeting_id"],
            outcome_template_key=row["outcome_template_key"],
        )
        for row in rows
    ], truncated


async def run(*, meeting_id: UUID | None, limit: int) -> dict[str, Any]:
    settings = get_settings()
    engine = create_engine(settings)
    context = MaintenanceTenantContext(
        operation_name=OPERATION_NAME,
        actor_id=ACTOR_ID,
        reason_category="summary_slots_reconciliation",
        feature_area=FEATURE_AREA,
    )
    sessionmaker = create_sessionmaker(engine)
    try:
        async with sessionmaker() as session:
            session.sync_session.info["tenant_context"] = dict(maintenance_context_settings(context))
            rows, truncated = await _load_rows(session, meeting_id=meeting_id, limit=limit)
        report = summarize_slot_metadata(rows, truncated=truncated)
        report["scope"] = {"meeting_id": str(meeting_id) if meeting_id else "all"}
        return report
    finally:
        await engine.dispose()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reconcile GRAF summary slots using metadata only; never reads content fields"
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--meeting-id", type=UUID)
    target.add_argument("--all", action="store_true")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be positive")
    report = asyncio.run(run(meeting_id=args.meeting_id, limit=args.limit))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
