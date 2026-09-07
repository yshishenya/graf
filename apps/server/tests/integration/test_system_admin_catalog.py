"""System-console catalog and campaign operations use isolated SQL functions."""

import base64
import json
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
import httpx
import pytest
from sqlalchemy.engine import make_url

from tests.integration import test_system_admin_security as security
from twobrain_rec_server.system_admin.app import create_app
from twobrain_rec_server.system_admin.auth import encrypt_totp, hash_password, totp_code

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


@pytest.mark.asyncio
async def test_subscription_adjustment_is_previewed_committed_and_claimed(system_database, test_settings):
    db = system_database
    await db["owner"].execute("update system_control.role_assignments set role='superadmin'")
    workspace = await db["owner"].fetchval("select id from workspaces order by id limit 1")
    await db["owner"].execute(
        "insert into workspace_subscriptions(workspace_id) values($1) on conflict (workspace_id) do nothing", workspace
    )
    version = await db["owner"].fetchval(
        "select greatest(1,coalesce(application_version,0)) from workspace_subscriptions where workspace_id=$1",
        workspace,
    ) or 1
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        starts = datetime.now(UTC).replace(microsecond=0)
        ends = starts + timedelta(days=7)
        command = {
            "kind": "subscription.adjust", "target_id": str(workspace), "expected_version": version,
            "reason": "Synthetic support compensation", "parameters": {
                "workspace_id": str(workspace), "adjustment_kind": "extra_quota", "feature_key": "processing_seconds",
                "value": 3600, "unit": "seconds", "plan_version_id": None, "plan_mode": None,
                "starts_at": starts.isoformat(), "ends_at": ends.isoformat(), "timezone": "UTC",
                "source_ref": f"admin:test:{uuid4().hex}", "subject_user_id": None,
            },
        }
        async with conn.transaction():
            await security._context(conn, db, **{
                "app.system_permission": "billing.manage", "app.system_target_type": "subscription",
                "app.system_target_id": str(workspace),
            })
            preview = json.loads(await conn.fetchval(
                "select system_control.preview_subscription_operation($1::jsonb)", json.dumps(command),
            ))
            assert "error" not in preview, preview
            commit_key = uuid4()
            committed = json.loads(await conn.fetchval(
                "select system_control.commit_subscription_operation($1,$2,$3)",
                preview["preview_id"], preview["effect_hash"], commit_key,
            ))
            assert committed["state"] == "queued"
            repeated = json.loads(await conn.fetchval(
                "select system_control.commit_subscription_operation($1,$2,$3)",
                preview["preview_id"], preview["effect_hash"], commit_key,
            ))
            assert repeated == committed
        password = uuid4().hex
        quoted = await db["owner"].fetchval("select quote_literal($1::text)", password)
        await db["owner"].execute(f"alter role twobrain_rec_maintenance login password {quoted}")
        await db["owner"].execute("grant usage on schema public to twobrain_rec_maintenance")
        await db["owner"].execute("grant select,insert,update,delete on all tables in schema public to twobrain_rec_maintenance")
        worker_url = make_url(db["url"]).set(username="twobrain_rec_maintenance", password=password).render_as_string(hide_password=False)
        from sqlalchemy.ext.asyncio import create_async_engine

        from twobrain_rec_server.db.session import create_sessionmaker
        from twobrain_rec_server.system_admin.worker import execute_operation
        engine = create_async_engine(worker_url)
        try:
            async with create_sessionmaker(engine)() as session:
                await execute_operation(session, operation_id=UUID(committed["operation_id"]), target_id=workspace,
                                        settings=test_settings, temporal_client=None, storage=None)
        finally:
            await engine.dispose()
        count = await db["owner"].fetchval(
            "select count(*) from billing_access_adjustments where admin_operation_id=$1", committed["operation_id"]
        )
        details = await db["owner"].fetchrow("select o.state,t.state,t.error_code,t.domain_ref from system_control.operations o join system_control.operation_targets t on t.operation_id=o.id where o.id=$1", committed["operation_id"])
        assert count == 1, f"operation={details}"
        adjustment_id = await db["owner"].fetchval(
            "select id from billing_access_adjustments where admin_operation_id=$1", committed["operation_id"]
        )
        next_version = await db["owner"].fetchval(
            "select application_version from workspace_subscriptions where workspace_id=$1", workspace
        )
        revoke_command = {
            "kind": "subscription.adjustment.revoke", "target_id": str(workspace),
            "expected_version": max(1, next_version or 1), "reason": "Synthetic revoke correction",
            "parameters": {"adjustment_id": str(adjustment_id), "source_ref": f"admin:test:{uuid4().hex}"},
        }
        async with conn.transaction():
            await security._context(conn, db, **{
                "app.system_permission": "billing.manage", "app.system_target_type": "subscription",
                "app.system_target_id": str(workspace),
            })
            revoke_preview = json.loads(await conn.fetchval(
                "select system_control.preview_subscription_operation($1::jsonb)", json.dumps(revoke_command),
            ))
            assert "error" not in revoke_preview, revoke_preview
            revoke_committed = json.loads(await conn.fetchval(
                "select system_control.commit_subscription_operation($1,$2,$3)",
                revoke_preview["preview_id"], revoke_preview["effect_hash"], uuid4(),
            ))
            assert revoke_committed["state"] == "queued"
        engine = create_async_engine(worker_url)
        try:
            async with create_sessionmaker(engine)() as session:
                await execute_operation(session, operation_id=UUID(revoke_committed["operation_id"]), target_id=workspace,
                                        settings=test_settings, temporal_client=None, storage=None)
        finally:
            await engine.dispose()
        assert await db["owner"].fetchval(
            "select count(*) from billing_access_revocations where admin_operation_id=$1", revoke_committed["operation_id"]
        ) == 1
        assert await db["owner"].fetchval(
            "select application_version from workspace_subscriptions where workspace_id=$1", workspace
        ) == max(1, next_version or 1) + 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_subscription_adjustment_http_is_idempotent_and_scoped(system_database, monkeypatch, tmp_path):
    db = system_database
    key = bytes(range(32))
    seed = b"12345678901234567890"
    password = "Synthetic billing password 254"
    nonce, cipher = encrypt_totp(base64.b32encode(seed).decode(), principal_id=db["actor"], key=key)
    await db["owner"].execute("update system_control.role_assignments set role='superadmin'")
    await db["owner"].execute("update system_control.principals set password_hash=$1", hash_password(password))
    await db["owner"].execute(
        "insert into system_control.credentials(principal_id,encrypted_totp_seed,key_id,nonce) values($1,$2,'test',$3)",
        db["actor"], cipher, nonce,
    )
    workspace = await db["owner"].fetchval("select id from workspaces order by id limit 1")
    await db["owner"].execute(
        "insert into workspace_subscriptions(workspace_id) values($1) on conflict (workspace_id) do nothing", workspace
    )
    database = tmp_path / "database"
    database.write_text(db["url"])
    keys = tmp_path / "keys"
    keys.write_text(json.dumps({"active": "test", "keys": {"test": base64.b64encode(key).decode()}}))
    monkeypatch.setenv("SYSTEM_ADMIN_ENABLED", "true")
    monkeypatch.setenv("SYSTEM_ADMIN_COMMANDS_ENABLED", "true")
    monkeypatch.setenv("SYSTEM_ADMIN_PUBLIC_ORIGIN", "https://admin.example.invalid")
    monkeypatch.setenv("SYSTEM_ADMIN_DATABASE_URL_FILE", str(database))
    monkeypatch.setenv("SYSTEM_ADMIN_TOTP_KEYS_FILE", str(keys))
    app = create_app()
    prefix = "/api/system-admin/v1"
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://admin.example.invalid",
    ) as client:
        csrf = (await client.get(f"{prefix}/auth/csrf")).json()["csrf_token"]
        client.headers.update({"Origin": "https://admin.example.invalid", "X-CSRF-Token": csrf})
        login = await client.post(f"{prefix}/auth/login", json={"email": "synthetic@example.invalid", "password": password})
        assert login.status_code == 200, login.text
        mfa = await client.post(f"{prefix}/auth/mfa", json={
            "challenge": login.json()["challenge"], "code": totp_code(seed, int(time.time() // 30)),
        })
        assert mfa.status_code == 200, mfa.text
        assert (await client.get(f"{prefix}/subscriptions/{workspace}/adjustments")).status_code == 200
        for section in ("subscriptions", "payments", "plans", "campaigns", "operations", "incidents",
                        "devices", "integrations", "metrics", "alerts", "storage", "dependencies", "settings"):
            page = await client.get(f"/system-admin?section={section}")
            assert page.status_code == 200, f"section={section}: {page.text}"
            assert page.text.count("<thead>") == 1 and page.text.count("<tbody>") == 1
        for path in ("/overview", "/operations", "/incidents", "/devices", "/integrations",
                     "/metrics", "/alerts", "/storage", "/dependencies", "/settings"):
            response = await client.get(f"{prefix}{path}")
            assert response.status_code == 200, f"path={path}: {response.text}"
        assert "id=\"reason-dialog\"" in (await client.get("/system-admin?section=plans")).text
        starts = datetime.now(UTC).replace(microsecond=0)
        payload = {
            "kind": "subscription.adjust", "adjustment_kind": "extra_quota", "feature_key": "processing_seconds",
            "value": 3600, "unit": "seconds", "subject_user_id": None, "plan_version_id": None, "plan_mode": None,
            "starts_at": starts.isoformat(), "ends_at": (starts + timedelta(days=7)).isoformat(), "timezone": "UTC",
            "source_ref": f"admin:http:{uuid4().hex}", "reason": "Synthetic HTTP compensation", "expected_version": 1,
        }
        preview_response = await client.post(f"{prefix}/subscriptions/{workspace}/adjustments/preview", json=payload)
        assert preview_response.status_code == 200, preview_response.text
        preview = preview_response.json()
        commit_payload = {"preview_id": preview["preview_id"], "expected_preview_hash": preview["effect_hash"]}
        assert (await client.post(f"{prefix}/subscriptions/{workspace}/adjustments", json=commit_payload)).status_code == 422
        idem = str(uuid4())
        first = await client.post(f"{prefix}/subscriptions/{workspace}/adjustments", json=commit_payload,
                                  headers={"Idempotency-Key": idem})
        repeat = await client.post(f"{prefix}/subscriptions/{workspace}/adjustments", json=commit_payload,
                                   headers={"Idempotency-Key": idem})
        assert first.status_code == 202, first.text
        assert repeat.status_code == 202 and repeat.json() == first.json()
        assert (await client.get(first.json()["status_url"])).json()["state"] == "queued"
