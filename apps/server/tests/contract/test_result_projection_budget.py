"""Numeric phases inspect raw SQL JSON without sending its body to Python."""

import pytest
from sqlalchemy import (
    JSON,
    Column,
    Integer,
    MetaData,
    Numeric,
    Table,
    Text,
    cast,
    event,
    func,
    literal,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from tests.contract.test_result_visibility import _run
from twobrain_rec_server.cabinet.result_projection_budget import (
    ProjectionBudgetExceeded,
    ProjectionReadBudget,
)

_PROBE = Table(
    "t112_projection_probe", MetaData(), Column("id", Integer, primary_key=True),
    Column("body", Text), Column("j", JSON), Column("jb", JSONB),
)


async def _prepare(db):
    await db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
    await db.execute(text("SET LOCAL statement_timeout='500ms'"))
    await db.execute(text("SET LOCAL lock_timeout='250ms'"))
    await db.run_sync(lambda sync: _PROBE.create(sync.connection()))


async def _check(db, budget, statement, parameters=None):
    try:
        return await db.run_sync(lambda sync: budget.check(sync.connection(), statement, parameters))
    except ProjectionBudgetExceeded as error:
        if error.__context__ is not None:
            original = getattr(error.__context__, "orig", None)
            raise AssertionError(f"numeric SQL failure: {type(error.__context__).__name__} "
                                 f"code={getattr(original, 'sqlstate', None)} "
                                 f"{str(error.__context__)[:200]}") from error
        raise


@pytest.mark.parametrize("shape", ["coalesce", "arithmetic"])
def test_numeric_expression_type_does_not_bound_its_actual_wire_size(postgres_seeded_database_url, shape):
    async def scenario(sessions):
        async with sessions() as db:
            await _prepare(db)
            if shape == "coalesce":
                number = func.coalesce(cast(literal(None), Numeric(1, 0)),
                                       cast(literal("9" * 50000), Numeric()))
                assert number.type.precision == 1 and number.type.scale == 0
                repeats = 22
            else:
                source = select(cast(literal("9" * 1000), Numeric(1000, 0)).label("n")).cte("n0")
                for step in range(1, 8):
                    source = select((source.c.n * source.c.n).label("n")).cte(f"n{step}")
                number = source.c.n
                assert number.type.precision == 1000 and number.type.scale == 0
                repeats = 9
            wire_bytes = await db.scalar(select(func.octet_length(func.numeric_send(number))))
            assert wire_bytes * repeats > 512 * 1024
            source = select(number.label("n")).cte("numeric_expression").prefix_with("MATERIALIZED")
            budget = ProjectionReadBudget()
            with pytest.raises(ProjectionBudgetExceeded):
                await _check(db, budget, select(*[source.c.n for _ in range(repeats)]))
            assert budget.failed and not db.identity_map
            await db.rollback()
    _run(postgres_seeded_database_url, scenario)


def test_numeric_values_use_exact_binary_size_including_null(postgres_seeded_database_url):
    async def scenario(sessions):
        async with sessions() as db:
            await _prepare(db)
            for raw in (None, "0", "12.345", "0." + "0" * 1000 + "1"):
                number = cast(literal(raw), Numeric())
                wire_bytes = await db.scalar(select(func.coalesce(
                    func.octet_length(func.numeric_send(number)), 0,
                )))
                budget = ProjectionReadBudget()
                await _check(db, budget, select(number))
                assert budget.raw_bytes == wire_bytes
                assert not budget.failed and not db.identity_map
            await db.rollback()
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("raw,expected", [
    ('{"x":1}', (7, 2)),
    ('{"x":1,"x":2}', (13, 3)),
    ('"😀"', (6, 1)),
    ('null', (4, 1)),
    (None, (0, 0)),
], ids=["object", "duplicate-keys", "unicode", "json-null", "sql-null"])
def test_numeric_phases_preserve_raw_bytes_nodes_and_null(postgres_seeded_database_url, raw, expected):
    async def scenario(sessions):
        async with sessions() as db:
            await _prepare(db)
            await db.execute(text("INSERT INTO t112_projection_probe(id,j) VALUES (1,CAST(:raw AS json))"),
                             {"raw": raw})
            budget = ProjectionReadBudget()
            await _check(db, budget, select(_PROBE.c.j))
            assert (budget.rows, budget.raw_bytes, budget.json_nodes) == (1, *expected)
            assert not db.identity_map
            await db.rollback()
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("raw", [
    '{' + ' ' * 262144 + '"x":1}',
    '{' + '"x":1,' * 45000 + '"x":1}',
    '{"x":' + '[' * 33 + '0' + ']' * 33 + ',"x":0}',
    '{"x":[' + ','.join(['0'] * 65534) + '],"x":0}',
], ids=["whitespace", "duplicate-bytes", "shadowed-depth", "shadowed-nodes"])
def test_shadowed_or_whitespace_input_is_rejected_before_any_original_read(
    postgres_seeded_database_url, raw,
):
    async def scenario(sessions):
        async with sessions() as db:
            await _prepare(db)
            await db.execute(text("INSERT INTO t112_projection_probe(id,j) VALUES (1,CAST(:raw AS json))"),
                             {"raw": raw})
            statements = []
            conn = await db.connection()
            def capture(conn, cursor, statement, parameters, context, executemany):
                statements.append([column.name for column in context.compiled.statement.selected_columns])
            event.listen(conn.sync_connection, "before_cursor_execute", capture)
            budget = ProjectionReadBudget()
            try:
                with pytest.raises(ProjectionBudgetExceeded, match="^result projection unavailable$"):
                    await _check(db, budget, select(_PROBE.c.j))
                assert budget.failed
                assert not db.identity_map
                assert 1 <= len(statements) <= 2
                # Only count/sum/max projections, never a returned private JSON column.
                assert all(columns in (["count", "coalesce"],
                                       ["count", "coalesce", "coalesce", "coalesce"])
                           for columns in statements)
            finally:
                event.remove(conn.sync_connection, "before_cursor_execute", capture)
            await db.rollback()
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("length,allowed", [(262143, True), (262144, True), (262145, False)])
def test_field_byte_boundary(postgres_seeded_database_url, length, allowed):
    async def scenario(sessions):
        async with sessions() as db:
            await _prepare(db)
            await db.execute(_PROBE.insert().values(id=1, body="x" * length))
            budget = ProjectionReadBudget()
            if allowed:
                await _check(db, budget, select(_PROBE.c.body))
                assert budget.raw_bytes == length
            else:
                with pytest.raises(ProjectionBudgetExceeded):
                    await _check(db, budget, select(_PROBE.c.body))
            await db.rollback()
    _run(postgres_seeded_database_url, scenario)


def test_aliases_count_repeated_fields_and_jsonb_transport_byte(postgres_seeded_database_url):
    async def scenario(sessions):
        async with sessions() as db:
            await _prepare(db)
            await db.execute(text("INSERT INTO t112_projection_probe(id,j,jb) "
                                  "VALUES (1,CAST(:raw AS json),CAST(:raw AS jsonb))"),
                             {"raw": '{"x":1}'})
            budget = ProjectionReadBudget()
            one, two = _PROBE.alias(), _PROBE.alias()
            await _check(db, budget, select(one.c.j, two.c.j, one.c.jb).where(one.c.id == two.c.id))
            assert budget.rows == 1 and budget.raw_bytes == 7 + 7 + 9
            assert budget.json_nodes == 6
            await db.rollback()
    _run(postgres_seeded_database_url, scenario)


def test_scalar_without_limit_counts_all_sql_rows_and_closes_budget(postgres_seeded_database_url):
    async def scenario(sessions):
        async with sessions() as db:
            await _prepare(db)
            await db.execute(text("INSERT INTO t112_projection_probe(id) SELECT generate_series(1,4097)"))
            budget = ProjectionReadBudget()
            with pytest.raises(ProjectionBudgetExceeded):
                await _check(db, budget, select(_PROBE.c.id))
            assert budget.rows == 4097
            with pytest.raises(ProjectionBudgetExceeded):
                await _check(db, budget, select(_PROBE.c.id).limit(1))
            await db.rollback()
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("depth,allowed", [(31, True), (32, True), (33, False)])
def test_raw_depth_boundary(postgres_seeded_database_url, depth, allowed):
    async def scenario(sessions):
        async with sessions() as db:
            await _prepare(db)
            raw = "[" * depth + "0" + "]" * depth
            await db.execute(text("INSERT INTO t112_projection_probe(id,j) VALUES (1,CAST(:raw AS json))"),
                             {"raw": raw})
            budget = ProjectionReadBudget()
            if allowed:
                await _check(db, budget, select(_PROBE.c.j))
                assert budget.json_nodes == depth + 1
            else:
                with pytest.raises(ProjectionBudgetExceeded):
                    await _check(db, budget, select(_PROBE.c.j))
                assert budget.json_nodes == 34
            await db.rollback()
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("nodes,allowed", [(65535, True), (65536, True), (65537, False)])
def test_raw_node_boundary(postgres_seeded_database_url, nodes, allowed):
    async def scenario(sessions):
        async with sessions() as db:
            await _prepare(db)
            raw = "[" + ",".join(["0"] * (nodes - 1)) + "]"
            await db.execute(text("INSERT INTO t112_projection_probe(id,j) VALUES (1,CAST(:raw AS json))"),
                             {"raw": raw})
            budget = ProjectionReadBudget()
            if allowed:
                await _check(db, budget, select(_PROBE.c.j))
            else:
                with pytest.raises(ProjectionBudgetExceeded):
                    await _check(db, budget, select(_PROBE.c.j))
            assert budget.json_nodes == nodes
            await db.rollback()
    _run(postgres_seeded_database_url, scenario)


def test_cumulative_bytes_and_duplicate_column_row_boundary(postgres_seeded_database_url):
    async def scenario(sessions):
        async with sessions() as db:
            await _prepare(db)
            await db.execute(_PROBE.insert().values(id=1, body="x" * 262144))
            row_budget = ProjectionReadBudget()
            await _check(db, row_budget, select(_PROBE.c.body, _PROBE.c.body))
            assert row_budget.raw_bytes == 524288
            with pytest.raises(ProjectionBudgetExceeded):
                await _check(db, ProjectionReadBudget(), select(
                    _PROBE.c.body, _PROBE.c.body, _PROBE.c.body,
                ))
            budget = ProjectionReadBudget()
            for _ in range(32):
                await _check(db, budget, select(_PROBE.c.body))
            assert budget.raw_bytes == 8 * 1024 * 1024
            with pytest.raises(ProjectionBudgetExceeded):
                await _check(db, budget, select(_PROBE.c.body))
            await db.rollback()
    _run(postgres_seeded_database_url, scenario)


def test_cumulative_rows_and_empty_original_query(postgres_seeded_database_url):
    async def scenario(sessions):
        async with sessions() as db:
            await _prepare(db)
            empty = ProjectionReadBudget()
            await _check(db, empty, select(_PROBE.c.j))
            assert (empty.rows, empty.raw_bytes, empty.json_nodes) == (0, 0, 0)
            await db.execute(text("INSERT INTO t112_projection_probe(id) SELECT generate_series(1,4096)"))
            budget = ProjectionReadBudget()
            for _ in range(4):
                await _check(db, budget, select(_PROBE.c.id))
            assert budget.rows == 16384
            with pytest.raises(ProjectionBudgetExceeded):
                await _check(db, budget, select(_PROBE.c.id).limit(1))
            await db.rollback()
    _run(postgres_seeded_database_url, scenario)


def test_recursive_numeric_query_compilation_is_stable():
    from sqlalchemy.dialects import postgresql

    from twobrain_rec_server.cabinet.result_projection_budget import (
        _bounded_projection,
        _shape_query,
    )

    # Regression for anonymous CTE identities colliding across repeated construction.
    for _ in range(50):
        query = _shape_query(_bounded_projection(select(_PROBE.c.j)))
        query.compile(dialect=postgresql.dialect())


def test_real_shared_projection_keeps_original_response_under_numeric_phases(
    postgres_seeded_database_url,
):
    from tests.contract.test_result_view_projection import _seed_projection
    from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
    from twobrain_rec_server.cabinet.queries import get_cabinet_meeting_review

    async def scenario(sessions):
        async with sessions() as db:
            review, *_ = await _seed_projection(db)
            meeting_id = review.meeting.meeting_id
        async with sessions() as db:
            original = await get_cabinet_meeting_review(
                db, workspace_id=WORKSPACE_ID, meeting_id=meeting_id, viewer_user_id=USER_ID,
            )
        async with sessions() as db:
            await db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
            await db.execute(text("SET LOCAL statement_timeout='500ms'"))
            await db.execute(text("SET LOCAL lock_timeout='250ms'"))
            budget = ProjectionReadBudget()
            def numeric_read(state):
                if state.is_select:
                    budget.check(state.session.connection(), state.statement, state.parameters)
                return state.invoke_statement()
            event.listen(db.sync_session, "do_orm_execute", numeric_read, retval=True)
            try:
                checked = await get_cabinet_meeting_review(
                    db, workspace_id=WORKSPACE_ID, meeting_id=meeting_id, viewer_user_id=USER_ID,
                )
                assert checked.model_dump() == original.model_dump()
                assert budget.rows > 0 and budget.raw_bytes > 0 and budget.json_nodes > 0
                assert not budget.failed
            finally:
                event.remove(db.sync_session, "do_orm_execute", numeric_read)
            await db.rollback()
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("raw", [
    '{' + ' ' * 262144 + '"x":1}',
    '{"x":' + '[' * 33 + '0' + ']' * 33 + ',"x":0}',
    '{"x":[' + ','.join(['0'] * 65534) + '],"x":0}',
], ids=["bytes", "depth", "nodes"])
def test_normalization_control_would_admit_what_raw_preflight_rejects(
    postgres_seeded_database_url, raw,
):
    async def scenario(sessions):
        async with sessions() as db:
            await _prepare(db)
            await db.execute(text("INSERT INTO t112_projection_probe(id,j) VALUES (1,CAST(:raw AS json))"),
                             {"raw": raw})
            with pytest.raises(ProjectionBudgetExceeded):
                await _check(db, ProjectionReadBudget(), select(_PROBE.c.j))
            normalized = ProjectionReadBudget()
            # Deliberately different Q witnesses the discarded data; never used by the owner.
            await _check(db, normalized, select(cast(cast(_PROBE.c.j, JSONB), JSON)))
            assert normalized.raw_bytes < 32 and normalized.json_nodes == 2
            await db.rollback()
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("statement", [
    text("SELECT j FROM t112_projection_probe"), select(func.random()),
    select(cast(_PROBE.c.j, JSONB)).with_only_columns(func.random()),
    select(literal("x", type_=Text)).execution_options(stream_results=True),
])
def test_unknown_or_volatile_shape_is_closed(postgres_seeded_database_url, statement):
    async def scenario(sessions):
        async with sessions() as db:
            await _prepare(db)
            with pytest.raises(ProjectionBudgetExceeded):
                await _check(db, ProjectionReadBudget(), statement)
            await db.rollback()
    _run(postgres_seeded_database_url, scenario)
