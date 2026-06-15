from __future__ import annotations

from twobrain_rec_server.db.rls_validation import RLS_COVERED_TABLES, RLSTableStateEvidence


def passing_table_states() -> list[RLSTableStateEvidence]:
    return [
        RLSTableStateEvidence(table_name=table_name, rls_enabled=True, rls_forced=True)
        for table_name in RLS_COVERED_TABLES
    ]


def blocked_table_states(table_name: str = "meetings") -> list[RLSTableStateEvidence]:
    return [
        RLSTableStateEvidence(
            table_name=covered_table_name,
            rls_enabled=covered_table_name != table_name,
            rls_forced=covered_table_name != table_name,
        )
        for covered_table_name in RLS_COVERED_TABLES
    ]


def passing_table_state_json() -> dict[str, list[dict[str, bool | str]]]:
    return {
        "table_states": [
            {
                "table_name": state.table_name,
                "rls_enabled": state.rls_enabled,
                "rls_forced": state.rls_forced,
                "table_exists": state.table_exists,
            }
            for state in passing_table_states()
        ]
    }
