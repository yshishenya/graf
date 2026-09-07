"""System-console catalog and campaign operations use isolated SQL functions."""

import json
from uuid import uuid4

import asyncpg
import pytest

from tests.integration import test_system_admin_security as security

system_database = security.system_database
pytestmark = pytest.mark.strict_rls


def _caps() -> dict:
    return {
        "processing_unlimited": False, "audio_archive": True, "audio_download": False,
        "content_export": True, "meeting_sharing": True, "ai_summary": True, "ai_outcomes": True,
        "storage_bytes": 4_000_000_000, "processing_seconds": 24_000, "processing_window": "calendar_month_moscow",
        "export_formats": ["txt", "md"],
    }


def _terms(name: str = "Synthetic") -> dict:
    return {"name": name, "description": "", "audience": "public", "trial_days": 0}


@pytest.mark.asyncio
async def test_catalog_plan_lifecycle_and_campaign_codes(system_database):
    db = system_database
    await db["owner"].execute("update system_control.role_assignments set role='superadmin'")
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        async with conn.transaction():
            await security._context(conn, db, **{"app.system_permission": "catalog.draft"})
            plan_code = f"synthetic_{uuid4().hex[:8]}"
            created = json.loads(await conn.fetchval(
                "select system_control.create_catalog_plan($1,$2,$3::jsonb,$4::jsonb,$5,$6)",
                plan_code, "Synthetic Plan", json.dumps(_caps()), json.dumps(_terms()), 123400, 1234000,
            ))
            assert created["status"] == "draft"
            plan_id, version_id = created["id"], created["version_id"]
        async with conn.transaction():
            await security._context(conn, db, **{"app.system_permission": "catalog.publish"})
            published = json.loads(await conn.fetchval(
                "select system_control.publish_catalog_plan($1,$2)", plan_id, version_id,
            ))
            assert published["status"] == "published"
            await conn.execute("select set_config('app.system_permission','catalog.read',true)")
            listed = json.loads(await conn.fetchval("select system_control.list_catalog_plans(null)"))
            row = next(item for item in listed if item["id"] == plan_id)
            assert row["version_status"] == "published" and row["prices"]["month"] == 123400
        async with conn.transaction():
            await security._context(conn, db, **{"app.system_permission": "promotions.draft"})
            campaign = json.loads(await conn.fetchval(
                "select system_control.create_promotion_campaign($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)",
                uuid4().hex * 2, "synthetic-v1", plan_code, "month", "discount", 20, None, "all", None, 2, 100000,
                None, None, "Synthetic campaign",
            ))
            assert campaign["status"] == "draft"
            campaign_id = campaign["id"]
        async with conn.transaction():
            await security._context(conn, db, **{"app.system_permission": "promotions.publish"})
            active = json.loads(await conn.fetchval(
                "select system_control.set_promotion_campaign_state($1,'active')", campaign_id,
            ))
            assert active["status"] == "active"
        async with conn.transaction():
            await security._context(conn, db, **{"app.system_permission": "promotions.manage"})
            hashes = [uuid4().hex * 2, uuid4().hex * 2]
            batch = json.loads(await conn.fetchval(
                "select system_control.issue_promotion_codes($1,$2,$3::jsonb,$4::jsonb)",
                campaign_id, str(uuid4()), json.dumps(hashes), json.dumps([None, None]),
            ))
            assert batch["code_count"] == 2
    finally:
        await conn.close()
