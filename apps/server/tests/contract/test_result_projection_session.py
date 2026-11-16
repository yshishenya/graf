"""Actual Session entry points and connection bypass on disposable PostgreSQL."""

import asyncio
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import JSON, Integer, Text, event, insert, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from tests.contract.test_result_visibility import _run
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID, principal
from twobrain_rec_server.cabinet.result_projection_budget import ProjectionBudgetExceeded
from twobrain_rec_server.cabinet.result_projection_session import result_projection_session
from twobrain_rec_server.db.tenant_context import WorkspaceAuthContext


class ProbeBase(DeclarativeBase):
    pass


class Probe(ProbeBase):
    __tablename__ = "t112_projection_session_probe"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    body: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON, default=dict)


@pytest.mark.parametrize("routing", ["factory", "execute", "connection", "mapper", "table"])
def test_other_session_bind_never_executes_unchecked_sql(postgres_seeded_database_url, routing):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    async def scenario(sessions):
        other = create_async_engine(postgres_seeded_database_url)
        observed = []
        def capture(conn, cursor, sql, params, context, many):
            observed.append(sql)
        try:
            async with other.connect() as warm:
                await warm.execute(text("SELECT 1"))
            event.listen(other.sync_engine, "before_cursor_execute", capture)
            async with _probe(sessions):
                factory = (async_sessionmaker(sessions.kw["bind"], binds={Probe: other})
                           if routing == "factory" else sessions)
                owners = []
                with pytest.raises(ProjectionBudgetExceeded):
                    async with result_projection_session(factory) as owner:
                        owners.append(owner)
                        if routing == "connection":
                            connection = await owner.db.connection(
                                bind_arguments={"bind": other.sync_engine},
                            )
                            await connection.execute(select(Probe))
                        else:
                            arguments = {}
                            if routing == "execute":
                                arguments["bind_arguments"] = {"bind": other.sync_engine}
                            elif routing in {"mapper", "table"}:
                                await owner.db.run_sync(lambda sync: (
                                    sync.bind_mapper(Probe, other.sync_engine) if routing == "mapper"
                                    else sync.bind_table(Probe.__table__, other.sync_engine)
                                ))
                            await owner.db.execute(select(Probe), **arguments)
                assert not observed
                assert all(item.failed and not item.db.identity_map for item in owners)
        finally:
            event.remove(other.sync_engine, "before_cursor_execute", capture)
            await other.dispose()
    _run(postgres_seeded_database_url, scenario)


def test_borrowed_nested_connection_is_refused_before_a_savepoint(postgres_seeded_database_url):
    from sqlalchemy.ext.asyncio import create_async_engine

    async def scenario(sessions):
        other = create_async_engine(postgres_seeded_database_url)
        try:
            async with other.connect() as borrowed:
                await borrowed.begin()
                await borrowed.begin_nested()
                observed = []
                def capture(conn, cursor, sql, params, context, many):
                    observed.append(sql)
                event.listen(borrowed.sync_connection, "before_cursor_execute", capture)
                try:
                    with pytest.raises(ProjectionBudgetExceeded):
                        async with result_projection_session(sessions) as owner:
                            with pytest.raises(ProjectionBudgetExceeded):
                                await owner.db.connection(bind_arguments={"bind": borrowed.sync_connection})
                    assert owner.failed and not owner.db.identity_map
                    assert not observed and borrowed.in_nested_transaction()
                finally:
                    event.remove(borrowed.sync_connection, "before_cursor_execute", capture)
                assert await borrowed.scalar(text("SELECT 1")) == 1
        finally:
            await other.dispose()
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("operation", ["insert", "update", "delete"])
@pytest.mark.parametrize("referenced", [False, True], ids=["independent", "referenced"])
def test_data_modifying_cte_is_refused_before_any_sql(
    postgres_seeded_database_url, operation, referenced,
):
    from sqlalchemy import delete, literal, update

    async def scenario(sessions):
        async with _probe(sessions):
            modifying = {
                "insert": insert(Probe).values(id=2, body="synthetic added"),
                "update": update(Probe).values(body="synthetic changed"),
                "delete": delete(Probe).where(Probe.id == 1),
            }[operation].returning(Probe.id).cte("modifying")
            statement = select(modifying.c.id) if referenced else select(literal(1)).add_cte(modifying)
            with pytest.raises(ProjectionBudgetExceeded):
                async with result_projection_session(sessions) as owner:
                    with pytest.raises(ProjectionBudgetExceeded):
                        await owner.db.execute(statement)
            assert owner.sql_count == 2 and not owner.db.identity_map
            assert owner.failed and owner.budget.failed
            async with sessions() as verify:
                assert (await verify.execute(select(Probe.id, Probe.body))).all() == [(1, "synthetic")]
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("nested", [False, True], ids=["outer", "nested"])
def test_skip_locked_cannot_change_the_checked_rows_before_original_read(postgres_seeded_database_url, nested):
    async def scenario(sessions):
        async with _probe(sessions, body="x" * (256 * 1024 + 1)), sessions() as writer:
            await writer.execute(select(Probe.id).with_for_update())
            loaded_sizes = []
            with pytest.raises(ProjectionBudgetExceeded):
                async with result_projection_session(sessions) as owner:
                    check = owner.budget.check
                    released = []
                    def release_after_preflight(connection, statement, parameters):
                        check(connection, statement, parameters)
                        writer.sync_session.rollback()
                        released.append(True)
                    owner.budget.check = release_after_preflight
                    if nested:
                        locked = select(Probe.id).with_for_update(skip_locked=True).cte("locked")
                        statement = select(Probe).where(Probe.id.in_(select(locked.c.id)))
                    else:
                        statement = select(Probe).with_for_update(skip_locked=True)
                    result = await owner.db.execute(statement)
                    loaded_sizes.append(len(result.scalar_one().body))
            assert owner.sql_count == 2 and not owner.db.identity_map and not released
            assert owner.failed and owner.budget.failed
            assert not loaded_sizes
            await writer.rollback()
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("locking", [{}, {"read": True}, {"nowait": True}], ids=["update", "share", "nowait"])
def test_ordinary_row_lock_modes_keep_the_checked_result(postgres_seeded_database_url, locking):
    async def scenario(sessions):
        async with _probe(sessions), result_projection_session(sessions) as owner:
            row = (await owner.db.scalars(select(Probe).with_for_update(**locking))).one()
            actual = row.id, row.body
            count = owner.sql_count
        assert actual == (1, "synthetic") and count == 5
    _run(postgres_seeded_database_url, scenario)


@asynccontextmanager
async def _probe(sessions, *, body="synthetic", rows=1):
    async with sessions() as db:
        await db.run_sync(lambda sync: Probe.__table__.create(sync.connection()))
        await db.execute(insert(Probe), [dict(id=n + 1, body=body) for n in range(rows)])
        await db.commit()
    try:
        yield
    finally:
        async with sessions() as db:
            await db.run_sync(lambda sync: Probe.__table__.drop(sync.connection()))
            await db.commit()


@pytest.mark.parametrize("entry", ["execute", "scalar", "scalars", "get"])
def test_all_session_read_entries_reject_before_original_model_load(postgres_seeded_database_url, entry):
    async def scenario(sessions):
        async with _probe(sessions, body="x" * (256 * 1024 + 1)), result_projection_session(sessions) as owner:
            db = owner.db
            with pytest.raises(ProjectionBudgetExceeded):
                if entry == "get":
                    await db.get(Probe, 1)
                else:
                    await getattr(db, entry)(select(Probe))
            assert not db.identity_map and owner.budget.failed
    with pytest.raises(ProjectionBudgetExceeded):
        _run(postgres_seeded_database_url, scenario)


def test_original_shapes_parameters_cache_and_tenant_controls_are_preserved(postgres_seeded_database_url):
    async def scenario(sessions):
        async with _probe(sessions, rows=2):
            async with result_projection_session(sessions) as owner:
                context = WorkspaceAuthContext(
                    organization_id=principal().organization_id,
                    workspace_id=WORKSPACE_ID, user_id=USER_ID, context_kind="auth_bootstrap",
                )
                await owner.tenant(context)
                assert owner.sql_count == 3  # Two fixed SETs and exactly one tenant SELECT.
                db = owner.db
                first = await db.get(Probe, 1)
                count = owner.sql_count
                assert await db.get(Probe, 1) is first
                assert owner.sql_count == count
                from sqlalchemy import bindparam
                statement = select(Probe.body, Probe.body).where(Probe.id == bindparam("wanted"))
                assert (await db.execute(statement, {"wanted": 2})).all() == [("synthetic", "synthetic")]
                assert await db.scalar(select(Probe.id).where(Probe.id == 0)) is None
                assert list(await db.scalars(select(Probe.id).order_by(Probe.id.desc()))) == [2, 1]
                assert owner.budget.rows == 4
                assert owner.budget.json_nodes == 1
                assert not owner.failed and not db.autoflush
                assert owner._listeners
            assert owner._listeners == [] and not db.in_transaction() and not db.identity_map
            async with sessions() as next_db:
                assert await next_db.scalar(text("SELECT 1")) == 1
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("bypass", ["core", "driver", "session-raw", "set-config", "write", "commit", "stream"])
def test_unknown_control_raw_connection_and_writes_are_closed(postgres_seeded_database_url, bypass):
    async def scenario(sessions):
        async with _probe(sessions), result_projection_session(sessions) as owner:
            db = owner.db
            with pytest.raises(ProjectionBudgetExceeded):
                connection = await db.connection()
                if bypass == "core":
                    await connection.execute(select(Probe))
                elif bypass == "driver":
                    await connection.exec_driver_sql("SELECT body FROM t112_projection_session_probe")
                elif bypass == "session-raw":
                    await db.execute(text("SELECT body FROM t112_projection_session_probe"))
                elif bypass == "set-config":
                    from sqlalchemy import func
                    await db.execute(select(func.set_config("statement_timeout", "0", True)))
                elif bypass == "write":
                    await db.execute(insert(Probe).values(id=3, body="unexpected"))
                elif bypass == "stream":
                    await db.stream(select(Probe))
                else:
                    await db.commit()
            assert owner.failed or owner.budget.failed
    with pytest.raises(ProjectionBudgetExceeded):
        _run(postgres_seeded_database_url, scenario)


def test_cap_counts_numeric_control_and_original_sql_not_only_logical_reads(postgres_seeded_database_url):
    async def scenario(sessions):
        async with _probe(sessions), result_projection_session(sessions) as owner:
            for _ in range(63):
                assert await owner.db.scalar(select(Probe.id)) == 1
            assert owner.sql_count == 128  # 2 controls + 63 * (numeric + original).
            with pytest.raises(ProjectionBudgetExceeded):
                await owner.db.scalar(select(Probe.id))
            assert owner.sql_count == 128
    with pytest.raises(ProjectionBudgetExceeded):
        _run(postgres_seeded_database_url, scenario)


def test_rr_snapshot_precedes_first_tenant_sql_and_keeps_preflight_payload(postgres_seeded_database_url):
    async def scenario(sessions):
        async with _probe(sessions), result_projection_session(sessions) as owner:
            context = WorkspaceAuthContext(
                organization_id=principal().organization_id,
                workspace_id=WORKSPACE_ID, user_id=USER_ID, context_kind="auth_bootstrap",
            )
            await owner.tenant(context)
            assert await owner.db.scalar(select(Probe.body)) == "synthetic"
            async with sessions() as writer:
                from sqlalchemy import update
                await writer.execute(update(Probe).values(body="x" * (256 * 1024 + 1)))
                await writer.commit()
            # populate_existing defeats the identity map; RR still reads the checked snapshot.
            row = await owner.db.get(Probe, 1, populate_existing=True)
            assert row.body == "synthetic"
    _run(postgres_seeded_database_url, scenario)


def test_timeout_covers_sync_work_and_listener_cleanup(postgres_seeded_database_url):
    async def scenario(sessions):
        async with _probe(sessions):
            loop = asyncio.get_running_loop()
            started = loop.time()
            with pytest.raises(ProjectionBudgetExceeded):
                async with result_projection_session(sessions, deadline=started + 0.65) as owner:
                    await owner.db.scalar(select(Probe.id))
                    # A synchronous digest cannot rely on an asyncio cancellation callback.
                    import time
                    time.sleep(0.2)
                    owner.checkpoint()
            assert loop.time() - started < 0.65
            assert owner._listeners == [] and not owner.db.in_transaction()
            assert not [task for task in asyncio.all_tasks()
                        if task is not asyncio.current_task() and not task.done()]
    _run(postgres_seeded_database_url, scenario)


def test_borrowed_session_is_refused_without_ending_its_transaction(postgres_seeded_database_url):
    async def scenario(sessions):
        async with sessions() as borrowed:
            assert await borrowed.scalar(text("SELECT 1")) == 1
            with pytest.raises(ProjectionBudgetExceeded):
                async with result_projection_session(lambda **kwargs: borrowed):
                    pytest.fail("borrowed Session must not reach the reader")
            assert borrowed.in_transaction() and await borrowed.scalar(text("SELECT 2")) == 2
    _run(postgres_seeded_database_url, scenario)


def test_actual_preflight_lock_timeout_never_loads_a_model_or_retries(postgres_seeded_database_url):
    async def scenario(sessions):
        async with _probe(sessions), sessions() as writer:
            await writer.execute(select(Probe.id).with_for_update())
            started = asyncio.get_running_loop().time()
            with pytest.raises(ProjectionBudgetExceeded):
                async with result_projection_session(sessions) as owner:
                    await owner.db.get(Probe, 1, with_for_update=True)
            assert owner.sql_count == 3 and not owner.db.identity_map
            assert asyncio.get_running_loop().time() - started < 0.8
            assert owner._listeners == [] and not owner.db.in_transaction()
            await writer.rollback()
    _run(postgres_seeded_database_url, scenario)


def test_actual_rr_conflict_is_40001_without_retry(postgres_seeded_database_url):
    from sqlalchemy import update

    async def scenario(sessions):
        async with _probe(sessions):
            errors = []
            with pytest.raises(ProjectionBudgetExceeded):
                async with result_projection_session(sessions) as owner:
                    assert await owner.db.scalar(select(Probe.id)) == 1
                    async with sessions() as writer:
                        await writer.execute(update(Probe).values(body="changed after snapshot"))
                        await writer.commit()
                    def capture(context):
                        errors.append(context.original_exception.sqlstate)
                    engine = owner._connection.engine
                    event.listen(engine, "handle_error", capture)
                    try:
                        await owner.db.get(Probe, 1, with_for_update=True)
                    finally:
                        event.remove(engine, "handle_error", capture)
            assert errors == ["40001"] and owner.sql_count == 5
            assert not owner.db.identity_map and owner._listeners == []
    _run(postgres_seeded_database_url, scenario)


def test_cancelled_owner_has_no_surviving_session_or_task(postgres_seeded_database_url):
    async def scenario(sessions):
        holder = []
        ready = asyncio.Event()
        async def read():
            async with result_projection_session(sessions) as owner:
                holder.append(owner)
                await owner.db.scalar(select(Probe.id))
                ready.set()
                await asyncio.Event().wait()
        async with _probe(sessions):
            task = asyncio.create_task(read())
            await asyncio.wait_for(ready.wait(), 1)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert holder[0]._listeners == [] and not holder[0].db.in_transaction()
            assert not [item for item in asyncio.all_tasks()
                        if item is not asyncio.current_task() and not item.done()]
    _run(postgres_seeded_database_url, scenario)


def test_same_pool_connection_has_no_leftover_guard(postgres_seeded_database_url):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    async def scenario(sessions):
        engine = create_async_engine(postgres_seeded_database_url, pool_size=1, max_overflow=0)
        pooled = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with _probe(sessions):
                async with result_projection_session(pooled) as owner:
                    assert await owner.db.scalar(select(Probe.id)) == 1
                    driver = owner._driver
                async with pooled() as db:
                    assert await db.scalar(text("SELECT 1")) == 1
                    connection = await db.connection()
                    assert connection.sync_connection.connection.driver_connection is driver
                async with result_projection_session(pooled) as second:
                    assert await second.db.scalar(select(Probe.id)) == 1
                    assert second._driver is driver and second.sql_count == 4
        finally:
            await engine.dispose()
    _run(postgres_seeded_database_url, scenario)


def test_close_timeout_terminates_exact_connection_without_a_background_task(postgres_seeded_database_url):
    async def scenario(sessions):
        async with _probe(sessions):
            loop = asyncio.get_running_loop()
            started = loop.time()
            with pytest.raises(TimeoutError):
                async with result_projection_session(sessions, deadline=started + 0.7) as owner:
                    await owner.db.scalar(select(Probe.id))
                    async def stuck_close():
                        await asyncio.Event().wait()
                    owner.db.close = stuck_close
            assert loop.time() - started < 0.9
            assert owner._driver.is_closed() and not owner.db.in_transaction()
            assert owner._listeners == [] and not [task for task in asyncio.all_tasks()
                if task is not asyncio.current_task() and not task.done()]
    _run(postgres_seeded_database_url, scenario)


def test_close_timeout_never_terminates_a_released_connection_reused_by_another_session(
    postgres_seeded_database_url,
):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    async def scenario(sessions):
        engine = create_async_engine(postgres_seeded_database_url, pool_size=1, max_overflow=0)
        pooled = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with _probe(sessions), pooled() as replacement:
                with pytest.raises(TimeoutError):
                    async with result_projection_session(
                        pooled, deadline=asyncio.get_running_loop().time() + 0.7,
                    ) as owner:
                        await owner.db.scalar(select(Probe.id))
                        original_close = owner.db.close
                        async def released_close():
                            await original_close()
                            assert await replacement.scalar(text("SELECT 1")) == 1
                            connection = await replacement.connection()
                            assert connection.sync_connection.connection.driver_connection is owner._driver
                            await asyncio.Event().wait()
                        owner.db.close = released_close
                assert not owner._driver.is_closed()
                assert await replacement.scalar(text("SELECT 2")) == 2
                assert not owner.db.in_transaction() and not owner._listeners
        finally:
            await engine.dispose()
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("variant", ["review", "bindings"])
def test_shared_reader_preserves_complete_ordinary_meeting(postgres_seeded_database_url, variant):
    from dataclasses import asdict, replace
    from datetime import timedelta
    from uuid import uuid4

    from tests.contract.test_result_view_projection import _seed_projection
    from tests.contract.test_result_visibility import NOW, _seed_source
    from twobrain_rec_server.cabinet.queries import get_cabinet_meeting_review
    from twobrain_rec_server.cabinet.result_visibility import load_fresh_result_view_bindings
    from twobrain_rec_server.db.models import (
        DiarizationSegment,
        Meeting,
        MeetingSummarySlot,
        RecordingCalendarContextLink,
        TranscriptSegment,
    )

    async def scenario(sessions):
        async with sessions() as db:
            seed, pinned, current, old = await _seed_projection(db)
            meeting_id = seed.meeting.meeting_id
            meeting = await db.get(Meeting, meeting_id)
            meeting.duration_seconds = 3600
            meeting.local_recording_id = "synthetic-current-session-guard"
            pinned.template_key = "graf-auto-v1"
            pinned.template_version = 1
            pinned.revision_state = "accepted"
            db.add(MeetingSummarySlot(
                workspace_id=WORKSPACE_ID, meeting_id=meeting_id,
                template_key="graf-auto-v1", current_outcome_set_id=pinned.id,
                current_binding_class="verified_complete", is_meeting_default=True,
                default_resolution_source="explicit_meeting", default_resolution_version="synthetic",
                default_resolved_at=NOW,
            ))
            current.provenance_json = {"synthetic": True, "segments": list(range(600))}
            current.segment_count = current.diarization_segment_count = 600
            for n in range(1, 600):
                value = "Синтетический разговор руководителя и специалиста. " * 8
                db.add(TranscriptSegment(
                    workspace_id=WORKSPACE_ID, meeting_id=meeting_id, processing_result_id=current.id,
                    sequence=n, start_seconds=n * 6, end_seconds=(n + 1) * 6,
                    text=value, source_role="canonical_mixed",
                ))
                db.add(DiarizationSegment(
                    workspace_id=WORKSPACE_ID, meeting_id=meeting_id, processing_result_id=current.id,
                    sequence=n, start_seconds=n * 6, end_seconds=(n + 1) * 6,
                    text=value, source_role="canonical_mixed", speaker_label=f"SPEAKER_{n % 4:02d}",
                ))
            await db.commit()
            previous, *_ = await _seed_source(db)
            previous.started_at = NOW - timedelta(days=7)
            previous.duration_seconds = 1800
            for row, start in ((previous, NOW - timedelta(days=7)), (meeting, NOW)):
                db.add(RecordingCalendarContextLink(
                    workspace_id=WORKSPACE_ID, meeting_id=row.id, context_state="matched_auto",
                    context_confidence="high", matcher_version="synthetic-session-guard",
                    recurring_series_key_sha256="e" * 64, matched_event_starts_at=start,
                    matched_event_ends_at=start + timedelta(hours=1), matched_title="Synthetic review",
                    matched_title_state="available", matched_roster_state="available",
                    matched_roster_count=4, matched_roster_json=[{
                        "display_name": f"Synthetic participant {n}", "participant_kind": "required_attendee",
                        "response_status": "accepted", "email_present": False,
                    } for n in range(4)],
                ))
            await db.commit()
            previous_id = previous.id
        params = dict(workspace_id=WORKSPACE_ID, meeting_id=meeting_id, viewer_user_id=USER_ID)
        actor = replace(principal(), session_id=uuid4(), auth_via_session=True,
                        session_workspace_id=WORKSPACE_ID)
        async def read(db):
            if variant == "review":
                return await get_cabinet_meeting_review(db, **params)
            return await load_fresh_result_view_bindings(
                db, principal=actor, workspace_id=WORKSPACE_ID, meeting_id=meeting_id,
                started_at=NOW - timedelta(days=1),
            )
        def dump(value):
            return value.model_dump() if variant == "review" else {k: asdict(v) for k, v in value.items()}
        async with sessions() as db:
            expected = await read(db)
        observed = []
        async with result_projection_session(sessions) as owner:
            connection = await owner.db.connection()
            def capture(conn, cursor, sql, values, context, many):
                observed.append(sql)
            event.listen(connection.sync_connection, "before_cursor_execute", capture)
            try:
                actual = await read(owner.db)
                dumped = dump(actual)
                owner.checkpoint()
            finally:
                event.remove(connection.sync_connection, "before_cursor_execute", capture)
        assert dumped == dump(expected)
        if variant == "review":
            assert actual.calendar_context_detail.previous_recurring_meeting.meeting_id == previous_id
            assert actual.calendar_roster.available and len(actual.calendar_roster.participants) == 4
            assert actual.template.outcome_set_id == pinned.id
        else:
            assert actual and all(binding.source.owner_id == USER_ID for binding in actual.values())
            assert actual["transcript:0"].source.result_id == current.id
            assert actual["outcome:summary:0"].source.result_id == old.id
            assert actual["outcome:summary:0"].outcome_set_id == pinned.id
        assert owner.budget.rows >= 1200 and owner.budget.raw_bytes > 100000
        assert owner.sql_count == len(observed) + 2 and owner.sql_count <= 128
        print(f"ordinary_projection_variant={variant} sql={owner.sql_count} rows={owner.budget.rows} "
              f"bytes={owner.budget.raw_bytes} nodes={owner.budget.json_nodes}")
    _run(postgres_seeded_database_url, scenario)
