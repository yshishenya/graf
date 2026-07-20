from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.integration.test_playback_normalization_backfill import _seed_legacy_revision
from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context
from twobrain_rec_server.normalization.pickup import enumerate_backfill_workspace_candidates


def test_global_inventory_context_returns_only_bounded_tenant_scope_ids(client) -> None:
    now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            await _seed_legacy_revision(db, ordinal=3000, created_at=now)
        async with client.app_state["media_sessionmaker"]() as db:
            context = MaintenanceTenantContext(
                operation_name="playback_normalization_inventory",
                actor_id="rls-maintenance-test",
                reason_category="automatic_backfill",
                feature_area="playback_normalization",
            )
            await apply_tenant_context(db, context)
            rows = await enumerate_backfill_workspace_candidates(
                db,
                after_workspace_id=None,
                page_size=50,
            )
            settings = dict(db.info["tenant_context"])
            with pytest.raises(ValueError, match="page_size"):
                await enumerate_backfill_workspace_candidates(
                    db,
                    after_workspace_id=None,
                    page_size=51,
                )
            return rows, settings

    rows, settings = asyncio.run(exercise())
    assert rows
    assert settings == {
        "app.context_kind": "maintenance",
        "app.maintenance_operation": "playback_normalization_inventory",
        "app.maintenance_actor": "rls-maintenance-test",
        "app.maintenance_reason": "automatic_backfill",
        "app.maintenance_feature_area": "playback_normalization",
    }
    assert set(rows[0].__dataclass_fields__) == {"tenant_scope"}


def test_postgres_workspace_inventory_function_exposes_no_content_columns() -> None:
    migration = Path(__file__).resolve().parents[2] / (
        "src/twobrain_rec_server/db/migrations/versions/0022_playback_normalization.py"
    )
    text = migration.read_text(encoding="utf-8").lower()
    marker = "create or replace function rec_playback_normalization_workspace_page"
    assert marker in text
    function_body = text.split(marker, 1)[1].split("$$;", 1)[0]
    for forbidden in (
        "title",
        "local_recording_id",
        "local_media_revision_id",
        "storage_object_key",
        "transcript",
        "summary",
        "filename",
    ):
        assert forbidden not in function_body
