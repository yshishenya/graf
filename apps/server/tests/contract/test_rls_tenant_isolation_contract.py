from __future__ import annotations

from tests.fixtures.rls import RLS_DIRECT_WORKSPACE_TABLES


def test_outcome_tables_are_direct_workspace_tenant_scoped() -> None:
    assert {
        "meeting_outcome_sets",
        "meeting_outcome_items",
        "meeting_outcome_generation_attempts",
    } <= RLS_DIRECT_WORKSPACE_TABLES
