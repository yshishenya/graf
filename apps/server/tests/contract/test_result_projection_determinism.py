"""Shared projection limits choose the same rows at equal timestamps."""

from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import event, text

from tests.contract.test_result_visibility import NOW, _run, _seed_source
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from twobrain_rec_server.cabinet.egress import activity_response
from twobrain_rec_server.cabinet.queries import (
    _meeting_review_read_scope,
    _prefetch_meeting_review_reads,
)
from twobrain_rec_server.db.models import (
    MeetingEgressAuditEvent,
    ProcessingDependencyState,
    ProcessingWorkflow,
)


@pytest.mark.parametrize(("ordinal", "seconds", "new_wins"), [
    (2, 0, True), (1, 1, False), (3, -1, True), (2, -1, False), (2, 1, True),
])
def test_workflow_tie_uses_id_after_existing_priorities(
    postgres_seeded_database_url, ordinal, seconds, new_wins,
):
    async def scenario(sessions):
        async with sessions() as db:
            meeting, revision, _, original, _, _ = await _seed_source(db)
            original.attempt_ordinal, original.created_at = 2, NOW
            other = ProcessingWorkflow(
                id=UUID(int=2**128-1), workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
                media_revision_id=revision.id, workflow_id="synthetic-projection-tie",
                status="processed", attempt_ordinal=ordinal,
                created_at=NOW + timedelta(seconds=seconds),
            )
            db.add(other)
            await db.commit()
            with _meeting_review_read_scope(db):
                prefetch = await _prefetch_meeting_review_reads(
                    db, meeting=meeting, viewer_user_id=USER_ID,
                    selected_summary_template_key=None, source_result_id=None,
                )
                expected = other.id if new_wins else original.id
                assert prefetch.workflows[(meeting.id, revision.id)].id == expected
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize(("seconds", "new_wins"), [(0, True), (-1, False), (1, True)])
def test_dependency_tie_uses_id_after_update_time(postgres_seeded_database_url, seconds, new_wins):
    async def scenario(sessions):
        async with sessions() as db:
            meeting, revision, *_ = await _seed_source(db)
            original = ProcessingDependencyState(
                id=UUID(int=1), workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
                media_revision_id=revision.id, dependency="mediascribe", state="imported",
                updated_at=NOW,
            )
            other = ProcessingDependencyState(
                id=UUID(int=2), workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
                media_revision_id=revision.id, dependency="minio", state="stored",
                updated_at=NOW + timedelta(seconds=seconds),
            )
            db.add_all([original, other])
            await db.commit()
            with _meeting_review_read_scope(db):
                prefetch = await _prefetch_meeting_review_reads(
                    db, meeting=meeting, viewer_user_id=USER_ID,
                    selected_summary_template_key=None, source_result_id=None,
                )
                assert prefetch.dependencies[meeting.id].id == (other.id if new_wins else original.id)
    _run(postgres_seeded_database_url, scenario)


def test_activity_limit_keeps_same_rows_in_both_plans_and_preserves_time_priority(
    postgres_seeded_database_url,
):
    async def scenario(sessions):
        async with sessions() as db:
            meeting, *_ = await _seed_source(db)
            for number in [*range(100, 151), 1, 2**128-1]:
                offset = 1 if number == 1 else -1 if number == 2**128-1 else 0
                db.add(MeetingEgressAuditEvent(
                    id=UUID(int=number), workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
                    actor_user_id=USER_ID, event_type="meeting_viewed", outcome="completed",
                    created_at=NOW + timedelta(seconds=offset),
                    metadata_json={"synthetic": "x" * 262145} if number == 150 else {},
                ))
            await db.commit()
            meeting_id = meeting.id
        async with sessions() as db:
            await db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
            # Rollback drops this fixture index; it never becomes an app migration.
            await db.execute(text("CREATE INDEX t112_activity_tie_fixture ON "
                                  "meeting_egress_audit_events(created_at DESC,id DESC)"))
            for indexed in (False, True):
                for option, enabled in (
                    ("enable_seqscan", not indexed), ("enable_indexscan", indexed),
                    ("enable_bitmapscan", False), ("enable_indexonlyscan", False),
                ):
                    await db.execute(text(f"SET LOCAL {option}={'on' if enabled else 'off'}"))
                statements = []
                def capture(state, statements=statements):
                    if state.is_select:
                        statements.append(state.statement)
                event.listen(db.sync_session, "do_orm_execute", capture)
                try:
                    result = await activity_response(
                        db, workspace_id=WORKSPACE_ID, meeting_id=meeting_id, viewer_user_id=USER_ID,
                    )
                finally:
                    event.remove(db.sync_session, "do_orm_execute", capture)
                assert len(statements) == 1
                compiled = statements[0].compile(
                    dialect=db.bind.dialect, compile_kwargs={"literal_binds": True},
                )
                plan = await db.scalar(text("EXPLAIN (FORMAT JSON,COSTS OFF) " + str(compiled)))
                def node_types(node):
                    return {node["Node Type"]}.union(*(node_types(c) for c in node.get("Plans", [])))
                assert ("Index Scan" if indexed else "Seq Scan") in node_types(plan[0]["Plan"])
                expected = [UUID(int=1), *(UUID(int=n) for n in range(150, 101, -1))]
                assert [item.event_id for item in result.items] == expected
                assert result.redaction_state == "metadata_only"
            await db.rollback()
    _run(postgres_seeded_database_url, scenario)
