from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from twobrain_rec_server.db.models import UserUsageDaily, WorkspaceQuotaPolicy, WorkspaceUsageDaily


def test_admin_usage_and_quota_policy_are_read_only_and_source_backed(client) -> None:
    asyncio.run(_seed_usage(client))

    usage = client.get("/api/v1/admin/usage", headers=auth_headers())
    policy = client.get("/api/v1/admin/quota-policy", headers=auth_headers())

    assert usage.status_code == 200
    assert policy.status_code == 200
    usage_payload = usage.json()
    policy_payload = policy.json()
    assert usage_payload["totals"]["recording_minutes"] == 90
    assert usage_payload["totals"]["storage_bytes"] == 2048
    assert usage_payload["totals"]["processing_jobs"] == 4
    assert usage_payload["totals"]["date_window"] == {"from": "2026-06-27", "to": "2026-06-27"}
    assert usage_payload["quota_risk"]["recording_minutes"] == "near_limit"
    assert usage_payload["top_consumers"][0]["user_id"] == str(USER_ID)
    assert policy_payload["status"] == "configured"
    assert "invoice" not in usage.text.lower()
    assert "payment" not in usage.text.lower()
    assert "tariff" not in usage.text.lower()
    assert "edit" not in policy.text.lower()


async def _seed_usage(client) -> None:
    async with client.app_state["sessionmaker"]() as db:
        db.add(
            WorkspaceQuotaPolicy(
                workspace_id=WORKSPACE_ID,
                recording_minutes_limit=100,
                storage_bytes_limit=4096,
                processing_jobs_limit=10,
                policy_source="seed",
                status="configured",
                effective_from=datetime(2026, 6, 1, tzinfo=UTC),
            )
        )
        db.add(
            WorkspaceUsageDaily(
                workspace_id=WORKSPACE_ID,
                usage_date=date(2026, 6, 27),
                recording_minutes=90,
                storage_bytes=2048,
                processing_jobs=4,
                recording_count=3,
                accepted_count=3,
                freshness_state="fresh",
                source_cutoff_at=datetime(2026, 6, 27, 12, 0, tzinfo=UTC),
            )
        )
        db.add(
            UserUsageDaily(
                workspace_id=WORKSPACE_ID,
                user_id=USER_ID,
                usage_date=date(2026, 6, 27),
                recording_minutes=90,
                storage_bytes=2048,
                processing_jobs=4,
                file_count=3,
                freshness_state="fresh",
                source_cutoff_at=datetime(2026, 6, 27, 12, 0, tzinfo=UTC),
            )
        )
        await db.commit()
