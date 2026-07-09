from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from twobrain_rec_server.db.models import (
    AdminAuditEvent,
    AuthAuditEvent,
    MeetingLifecycleAuditEvent,
)


def test_admin_audit_journal_normalizes_metadata_only_sources(client) -> None:
    asyncio.run(_seed_audit(client))

    response = client.get("/api/v1/admin/audit", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["entries"]) >= 2
    assert {entry["source"] for entry in payload["entries"]} >= {"admin_audit_events", "auth_audit_events"}
    quota_entry = next(entry for entry in payload["entries"] if entry["action"] == "quota_viewed")
    auth_entry = next(
        entry for entry in payload["entries"] if entry["action"] == "provider_callback_success"
    )
    assert quota_entry["source_label"] == "Админские действия"
    assert quota_entry["actor_label"]
    assert quota_entry["action_label"] == "Просмотр квоты"
    assert quota_entry["object_label"] == "Квота рабочей области"
    assert quota_entry["outcome_label"] == "Разрешено"
    assert quota_entry["drill_down_path"] == "/admin/balance"
    assert auth_entry["source_label"] == "Авторизация"
    assert auth_entry["object_label"] == "Авторизация: email"
    assert auth_entry["drill_down_path"].startswith("/admin/users/")
    assert "storage_object_key" not in response.text
    assert "transcript_text" not in response.text
    assert "secret" not in response.text.lower()


def test_admin_audit_filters_before_limit_and_includes_lifecycle_events(client) -> None:
    asyncio.run(_seed_filtered_audit(client))

    filtered = client.get("/api/v1/admin/audit?action=target_old_event&limit=5", headers=auth_headers())
    lifecycle = client.get("/api/v1/admin/audit?action=deletion_requested", headers=auth_headers())

    assert filtered.status_code == 200
    assert [entry["action"] for entry in filtered.json()["entries"]] == ["target_old_event"]
    assert lifecycle.status_code == 200
    assert any(
        entry["source"] == "meeting_lifecycle_audit_events"
        for entry in lifecycle.json()["entries"]
    )


async def _seed_audit(client) -> None:
    async with client.app_state["sessionmaker"]() as db:
        db.add(
            AdminAuditEvent(
                workspace_id=WORKSPACE_ID,
                actor_user_id=USER_ID,
                actor_role="owner",
                action="quota_viewed",
                target_kind="quota",
                outcome="allowed",
                metadata_json={"status": "viewed"},
            )
        )
        db.add(
            AuthAuditEvent(
                workspace_id=WORKSPACE_ID,
                user_id=USER_ID,
                actor_user_id=USER_ID,
                event_type="provider_callback_success",
                provider="email",
                outcome="success",
                metadata_json={"status": "ok"},
            )
        )
        await db.commit()


async def _seed_filtered_audit(client) -> None:
    now = datetime.now(UTC)
    async with client.app_state["sessionmaker"]() as db:
        db.add(
            AdminAuditEvent(
                workspace_id=WORKSPACE_ID,
                actor_user_id=USER_ID,
                actor_role="owner",
                action="target_old_event",
                target_kind="quota",
                outcome="allowed",
                created_at=now - timedelta(days=2),
                metadata_json={},
            )
        )
        db.add_all(
            AdminAuditEvent(
                workspace_id=WORKSPACE_ID,
                actor_user_id=USER_ID,
                actor_role="owner",
                action=f"noise_{index}",
                target_kind="quota",
                outcome="allowed",
                created_at=now - timedelta(minutes=index),
                metadata_json={},
            )
            for index in range(60)
        )
        db.add(
            MeetingLifecycleAuditEvent(
                workspace_id=WORKSPACE_ID,
                actor_user_id=USER_ID,
                event_type="deletion_requested",
                outcome="accepted",
                safe_reason="user_request",
                created_at=now,
                metadata_json={},
            )
        )
        await db.commit()
