#!/usr/bin/env python3
"""Reconcile the first trusted outcome baseline without exposing meeting content."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    apply_tenant_context_to_connection,
    maintenance_context_settings,
)
from twobrain_rec_server.outcomes.service import ensure_outcomes_for_meeting
from twobrain_rec_server.processing.store import ProcessingLifecycleBlocked

OPERATION_NAME = "outcome_initial_baseline_reconciliation"
ACTOR_ID = "reconcile_initial_outcomes.py"
FEATURE_AREA = "outcomes"


def _positive_limit(value: str) -> int:
    limit = int(value)
    if limit < 1:
        raise argparse.ArgumentTypeError("limit must be positive")
    return limit


def _maintenance_sessionmaker(base_sessionmaker: Callable[..., AsyncSession]) -> Callable[..., AsyncSession]:
    context_settings = maintenance_context_settings(
        MaintenanceTenantContext(
            operation_name=OPERATION_NAME,
            actor_id=ACTOR_ID,
            reason_category="initial_baseline_reconciliation",
            feature_area=FEATURE_AREA,
        )
    )

    def sessionmaker(*args: Any, **kwargs: Any) -> AsyncSession:
        session = base_sessionmaker(*args, **kwargs)
        sync_session = getattr(session, "sync_session", session)
        sync_session.info["tenant_context"] = dict(context_settings)
        return session

    return sessionmaker


async def _find_candidates(
    engine,
    *,
    meeting_id: UUID | None,
    limit: int,
) -> list[UUID]:
    context = MaintenanceTenantContext(
        operation_name=OPERATION_NAME,
        actor_id=ACTOR_ID,
        reason_category="initial_baseline_reconciliation",
        feature_area=FEATURE_AREA,
    )
    async with engine.begin() as connection:
        await apply_tenant_context_to_connection(connection, context)
        rows = (
            await connection.execute(
                text(
                    """
                    select distinct m.id
                    from meetings m
                    join processing_results pr on pr.meeting_id = m.id
                    where m.current_outcome_set_id is null
                      and m.deleted_at is null
                      and coalesce(m.deletion_state, 'none') = 'none'
                      and pr.status = 'imported'
                      and pr.transcript_status = 'available'
                      and pr.segment_count > 0
                      and (
                          cast(:meeting_id as uuid) is null
                          or m.id = cast(:meeting_id as uuid)
                      )
                    order by m.id
                    limit :limit
                    """
                ),
                {
                    "meeting_id": str(meeting_id) if meeting_id is not None else None,
                    "limit": limit,
                },
            )
        ).scalars()
        return [UUID(str(row)) for row in rows]


async def _reconcile_one(sessionmaker, meeting_id: UUID) -> dict[str, object]:
    try:
        outcome_set = await ensure_outcomes_for_meeting(
            sessionmaker,
            meeting_id=meeting_id,
            publish_initial_baseline=True,
            ai_dispatch_planned=False,
        )
    except ProcessingLifecycleBlocked as exc:
        return {
            "meeting_id": str(meeting_id),
            "status": "skipped",
            "reason_code": str(exc),
        }
    if outcome_set is None:
        return {"meeting_id": str(meeting_id), "status": "skipped", "reason_code": "no_result"}
    return {
        "meeting_id": str(meeting_id),
        "status": outcome_set.status,
        "revision_state": outcome_set.revision_state,
    }


async def run(args: argparse.Namespace) -> int:
    settings = Settings()
    engine = create_engine(settings)
    try:
        candidates = await _find_candidates(
            engine,
            meeting_id=UUID(args.meeting_id) if args.meeting_id else None,
            limit=args.limit,
        )
        if not args.execute:
            print(
                json.dumps(
                    {
                        "mode": "dry_run",
                        "candidate_count": len(candidates),
                        "meeting_ids": [str(candidate) for candidate in candidates],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        sessionmaker = _maintenance_sessionmaker(create_sessionmaker(engine))
        results = [await _reconcile_one(sessionmaker, candidate) for candidate in candidates]
        print(
            json.dumps(
                {"mode": "execute", "candidate_count": len(candidates), "results": results},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconcile the first trusted outcome baseline without exposing content"
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--meeting-id")
    target.add_argument("--all", action="store_true")
    parser.add_argument("--limit", type=_positive_limit, default=25)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
