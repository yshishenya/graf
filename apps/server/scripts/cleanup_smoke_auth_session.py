#!/usr/bin/env python3
"""Remove temporary AuthSession rows created for production smoke uploads."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from twobrain_rec_server.config import Settings
from twobrain_rec_server.deployment import build_smoke_identity_seed


async def _table_exists(conn: Any, table_name: str) -> bool:
    result = await conn.execute(
        text("select to_regclass(:table_name) is not null"),
        {"table_name": table_name},
    )
    return bool(result.scalar())


async def cleanup_smoke_auth_session(
    settings: Settings,
    *,
    run_id: str,
    auth_session_id: str | None,
    execute: bool,
) -> dict[str, Any]:
    seed = build_smoke_identity_seed(run_id)
    if not execute:
        return {
            "auth_cleanup_result": "dry_run",
            "auth_rows_removed": 0,
            "auth_session_id": auth_session_id,
            "run_id": run_id,
        }

    engine = create_async_engine(settings.database_url)
    rows_removed = 0
    try:
        async with engine.begin() as conn:
            has_bindings = await _table_exists(conn, "auth_session_device_bindings")
            has_sessions = await _table_exists(conn, "auth_sessions")
            if not has_sessions:
                return {
                    "auth_cleanup_result": "skipped_missing_auth_tables",
                    "auth_rows_removed": 0,
                    "auth_session_id": auth_session_id,
                    "run_id": run_id,
                }

            if has_bindings:
                if auth_session_id:
                    result = await conn.execute(
                        text(
                            """
                            delete from auth_session_device_bindings
                            where auth_session_id = cast(:auth_session_id as uuid)
                            """
                        ),
                        {"auth_session_id": auth_session_id},
                    )
                    rows_removed += result.rowcount or 0

                result = await conn.execute(
                    text(
                        """
                        delete from auth_session_device_bindings
                        where registered_device_id = cast(:device_id as uuid)
                        """
                    ),
                    {"device_id": str(seed.device_id)},
                )
                rows_removed += result.rowcount or 0

            if auth_session_id:
                result = await conn.execute(
                    text(
                        """
                        delete from auth_sessions
                        where id = cast(:auth_session_id as uuid)
                        """
                    ),
                    {"auth_session_id": auth_session_id},
                )
                rows_removed += result.rowcount or 0

            result = await conn.execute(
                text(
                    """
                    delete from auth_sessions
                    where user_id = cast(:user_id as uuid)
                      and workspace_id = cast(:workspace_id as uuid)
                    """
                ),
                {
                    "user_id": str(seed.user_id),
                    "workspace_id": str(seed.workspace_id),
                },
            )
            rows_removed += result.rowcount or 0
    finally:
        await engine.dispose()

    return {
        "auth_cleanup_result": "pass",
        "auth_rows_removed": rows_removed,
        "auth_session_id": auth_session_id,
        "run_id": run_id,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean temporary AuthSession rows created by production smoke."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--auth-session-id")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(
        cleanup_smoke_auth_session(
            Settings(),
            run_id=args.run_id,
            auth_session_id=args.auth_session_id,
            execute=args.execute,
        )
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
