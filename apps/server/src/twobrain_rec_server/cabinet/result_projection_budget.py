"""Numeric preflight only; this does not establish Session ownership or admission."""

from dataclasses import dataclass

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    Interval,
    LargeBinary,
    Numeric,
    String,
    Text,
    Time,
    Uuid,
    case,
    cast,
    func,
    inspect,
    literal,
    select,
    true,
    union_all,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import Select, visitors
from sqlalchemy.sql.elements import ColumnClause, TextClause, TypeCoerce
from sqlalchemy.sql.functions import FunctionElement

_ROWS_PER_QUERY = 4096
_TOTAL_ROWS = 16384
_TOTAL_BYTES = 8 * 1024 * 1024
_ROW_BYTES = 512 * 1024
_FIELD_BYTES = 256 * 1024
_JSON_DEPTH = 32
_JSON_NODES = 65536
_READ_FUNCTIONS = frozenset({
    "btrim", "coalesce", "concat", "count", "floor", "greatest", "left", "nullif",
    "regexp_replace", "replace", "row_number", "sum", "timezone", "to_char",
})


class ProjectionBudgetExceeded(Exception):
    def __init__(self):
        super().__init__("result projection unavailable")


def _field_bytes(column):
    kind = column.type
    if isinstance(kind, (String, JSON)):
        length = func.octet_length(func.convert_to(cast(column, Text), "UTF8"))
        if isinstance(kind, JSONB):
            length += 1  # asyncpg's binary JSONB value includes the version byte.
    elif isinstance(kind, LargeBinary):
        length = func.octet_length(column)
    elif isinstance(kind, Numeric) and not isinstance(kind, Float):
        # SQL expression type metadata does not bound the returned numeric.
        length = func.octet_length(func.pg_catalog.numeric_send(column))
    elif isinstance(kind, (Boolean, Integer, Float, Uuid, Date, Time, DateTime, Interval)):
        length = literal(32)  # Covers the fixed PostgreSQL binary scalar formats.
    else:
        raise ProjectionBudgetExceeded
    return case((column.is_(None), 0), else_=length)


def _bounded_projection(statement):
    if not isinstance(statement, Select) or not list(statement.selected_columns):
        raise ProjectionBudgetExceeded
    options = statement.get_execution_options()
    if options.get("stream_results") or options.get("yield_per"):
        raise ProjectionBudgetExceeded
    for node in visitors.iterate(statement):
        if (
            isinstance(node, (TextClause, TypeCoerce))
            or isinstance(node, ColumnClause) and node.is_literal
            or isinstance(node, FunctionElement) and (
                node.name.lower() not in _READ_FUNCTIONS or node.packagenames
            )
        ):
            raise ProjectionBudgetExceeded
    for description in statement.column_descriptions:
        entity = description.get("entity")
        if entity is not None and inspect(entity).mapper.relationships:
            raise ProjectionBudgetExceeded  # No implicit eager-load projection.
    original = statement.subquery()
    # Count a cap+1 prefix of the complete Q, including scalar() without LIMIT.
    return select(*original.c).limit(_ROWS_PER_QUERY + 1).subquery()


def _size_query(source):
    sizes = [_field_bytes(column) for column in source.c]
    row_size = sum(sizes)
    return select(
        func.count(), func.coalesce(func.sum(row_size), 0),
        func.coalesce(func.max(row_size), 0),
        func.coalesce(func.max(func.greatest(*sizes)), 0),
    ).select_from(source)


def _shape_query(source):
    columns = [column for column in source.c if isinstance(column.type, JSON)]
    if not columns:
        return None
    source = select(*source.c).cte("t112_projection_rows").prefix_with("MATERIALIZED")
    roots = [select(cast(source.c[c.key], JSON).label("node"), literal(0).label("depth"))
             .where(source.c[c.key].is_not(None)) for c in columns]
    seeds = (union_all(*roots) if len(roots) > 1 else roots[0]).subquery()
    walk = select(seeds.c.node, seeds.c.depth).cte("t112_projection_walk", recursive=True)
    objects = func.json_each(case(
        (func.json_typeof(walk.c.node) == "object", walk.c.node),
        else_=cast(literal("{}"), JSON),
    )).table_valued("key", "value")
    arrays = func.json_array_elements(case(
        (func.json_typeof(walk.c.node) == "array", walk.c.node),
        else_=cast(literal("[]"), JSON),
    )).table_valued("value")
    children = union_all(select(objects.c.value), select(arrays.c.value)).lateral()
    walk = walk.union_all(select(children.c.value, walk.c.depth + 1)
                          .select_from(walk.join(children, true()))
                          .where(walk.c.depth <= _JSON_DEPTH))
    bounded = select(walk.c.depth).limit(_JSON_NODES + 1).subquery()
    return select(func.count(), func.coalesce(func.max(bounded.c.depth), 0)).select_from(bounded)


@dataclass
class ProjectionReadBudget:
    rows: int = 0
    raw_bytes: int = 0
    json_nodes: int = 0
    failed: bool = False

    def check(self, connection, statement, parameters=None):
        """Inspect numeric values before the caller executes the unchanged SELECT.

        The future owner must supply a fresh RR Session, intercept every actual
        read, count all SQL and enforce its existing absolute time/lock budget.
        This helper neither invokes the original reader nor opens T113.
        """
        if self.failed:
            raise ProjectionBudgetExceeded
        self.failed = True  # Any uncertain outcome permanently closes this budget.
        if parameters is not None and not isinstance(parameters, dict):
            raise ProjectionBudgetExceeded
        source = _bounded_projection(statement)
        try:
            rows, raw_bytes, row_bytes, field_bytes = connection.execute(
                _size_query(source), parameters or {},
            ).one()
            self.rows += int(rows)
            self.raw_bytes += int(raw_bytes)
            if (rows > _ROWS_PER_QUERY or self.rows > _TOTAL_ROWS
                    or self.raw_bytes > _TOTAL_BYTES or row_bytes > _ROW_BYTES
                    or field_bytes > _FIELD_BYTES):
                raise ProjectionBudgetExceeded
            shape = _shape_query(source)
            if shape is not None:
                nodes, depth = connection.execute(shape, parameters or {}).one()
                self.json_nodes += int(nodes)
                if self.json_nodes > _JSON_NODES or depth > _JSON_DEPTH:
                    raise ProjectionBudgetExceeded
            self.failed = False
        except SQLAlchemyError:
            raise ProjectionBudgetExceeded from None
