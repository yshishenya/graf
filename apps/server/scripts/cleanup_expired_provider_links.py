#!/usr/bin/env python3
"""Expire abandoned verified-provider link intents without exposing their claims."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import create_async_engine
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import AuthAuditEvent
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    apply_tenant_context_to_connection,
)


async def cleanup_expired_provider_links(settings: Settings, *, execute: bool) -> dict[str, Any]:
    if not execute:
        return {"provider_link_cleanup_result": "dry_run", "expired_links": 0}

    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as conn:
            await apply_tenant_context_to_connection(
                conn,
                MaintenanceTenantContext(
                    operation_name="provider_link_cleanup",
                    actor_id="cleanup_expired_provider_links.py",
                    reason_category="expired_intent_cleanup",
                    feature_area="auth",
                ),
            )
            expired = (
                await conn.execute(
                    text(
                        """
                        update workspace_provider_link_states
                        set candidate_identity_subject = null,
                            candidate_email = null,
                            candidate_phone = null,
                            candidate_display_name = null,
                            status = 'expired',
                            resolution = 'expired'
                        where expires_at <= current_timestamp
                          and status in ('initiated', 'callback_verified')
                        returning workspace_id, initiating_user_id, candidate_provider
                        """
                    )
                )
            ).mappings().all()
            for row in expired:
                await conn.execute(
                    insert(AuthAuditEvent).values(
                        id=uuid4(),
                        workspace_id=UUID(str(row["workspace_id"])),
                        actor_user_id=UUID(str(row["initiating_user_id"])),
                        event_type="provider_link_expired",
                        provider=row["candidate_provider"],
                        outcome="failure",
                        metadata_json={"error_code": "provider_link_expired"},
                    )
                )
    finally:
        await engine.dispose()
    return {"provider_link_cleanup_result": "pass", "expired_links": len(expired)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Expire abandoned provider-link intents")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(cleanup_expired_provider_links(Settings(), execute=args.execute)), sort_keys=True))


if __name__ == "__main__":
    main()
