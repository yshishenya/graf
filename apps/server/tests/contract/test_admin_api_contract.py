from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import ORG_ID, WORKSPACE_ID
from tests.fixtures.admin import (
    DEFAULT_ADMIN_DEVICE_ID,
    DEFAULT_ADMIN_USER_ID,
    DEFAULT_MEMBER_DEVICE_ID,
    DEFAULT_MEMBER_USER_ID,
    auth_headers_for,
    seed_default_workspace_admin_roles,
)
from tests.fixtures.cabinet import seed_cabinet_meetings
from twobrain_rec_server.db.models import AdminAuditEvent, UserIdentity


def test_admin_overview_contract_for_owner_and_admin(client) -> None:
    asyncio.run(_seed_roles(client))

    owner_response = client.get("/api/v1/admin/overview", headers=auth_headers())
    admin_response = client.get(
        "/api/v1/admin/overview",
        headers=auth_headers_for(user_id=DEFAULT_ADMIN_USER_ID, device_id=DEFAULT_ADMIN_DEVICE_ID),
    )

    for response in (owner_response, admin_response):
        assert response.status_code == 200
        payload = response.json()
        assert payload["workspace_id"]
        assert payload["actor"]["role"] in {"owner", "admin"}
        assert set(payload["user_counts"]) >= {
            "active",
            "pending",
            "inactive",
            "blocked",
            "revoked",
        }
        assert set(payload["usage_summary"]) >= {
            "recording_minutes",
            "storage_bytes",
            "processing_jobs",
            "quota_risk",
            "freshness",
        }
        assert set(payload["file_summary"]) >= {"server_known_meetings", "deleting", "problem"}
        assert set(payload["metrics_summary"]) >= {"families", "freshness"}
        assert isinstance(payload["recent_audit"], list)


def test_admin_overview_contract_denies_member_without_admin_payload(client) -> None:
    asyncio.run(_seed_roles(client))

    response = client.get(
        "/api/v1/admin/overview",
        headers=auth_headers_for(
            user_id=DEFAULT_MEMBER_USER_ID, device_id=DEFAULT_MEMBER_DEVICE_ID
        ),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "admin_forbidden"
    assert "user_counts" not in response.text


async def _seed_roles(client) -> None:
    async with client.app_state["sessionmaker"]() as db:
        await seed_default_workspace_admin_roles(db)


def test_admin_user_and_invitation_contract(client) -> None:
    asyncio.run(_seed_roles(client))

    users = client.get("/api/v1/admin/users", headers=auth_headers())
    assert users.status_code == 200
    users_payload = users.json()
    assert "members" in users_payload
    assert "invitations" in users_payload

    owner_invite = client.post(
        "/api/v1/admin/invitations",
        headers=auth_headers(),
        json={"target_contact": "new-admin@example.test", "invited_role": "admin"},
    )
    assert owner_invite.status_code == 201
    assert owner_invite.json()["status"] == "pending"

    duplicate = client.post(
        "/api/v1/admin/invitations",
        headers=auth_headers(),
        json={"target_contact": "NEW-admin@example.test", "invited_role": "admin"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "invitation_duplicate_active"

    admin_owner_invite = client.post(
        "/api/v1/admin/invitations",
        headers=auth_headers_for(user_id=DEFAULT_ADMIN_USER_ID, device_id=DEFAULT_ADMIN_DEVICE_ID),
        json={"target_contact": "owner@example.test", "invited_role": "owner"},
    )
    assert admin_owner_invite.status_code == 403
    assert admin_owner_invite.json()["code"] == "admin_role_authority_forbidden"

    revoke = client.post(
        f"/api/v1/admin/invitations/{owner_invite.json()['id']}/revoke",
        headers=auth_headers(),
        json={"reason_code": "created_by_mistake"},
    )
    assert revoke.status_code == 200
    assert revoke.json()["status"] == "revoked"

    async def load_revocation_audit() -> AdminAuditEvent:
        async with client.app_state["sessionmaker"]() as db:
            event = await db.scalar(
                select(AdminAuditEvent).where(
                    AdminAuditEvent.action == "invite_revoked",
                    AdminAuditEvent.target_id == owner_invite.json()["id"],
                )
            )
            assert event is not None
            return event

    event = asyncio.run(load_revocation_audit())
    assert event.outcome == "completed"
    assert "target_contact" not in event.metadata_json


def test_admin_invitation_resend_is_generic_and_keeps_terminal_invites_terminal(monkeypatch, client) -> None:
    asyncio.run(_seed_roles(client))
    sent_to: list[str] = []

    async def send_review_notice(*, settings, recipient_email: str) -> None:
        _ = settings
        sent_to.append(recipient_email)

    monkeypatch.setattr(
        "twobrain_rec_server.api.admin.email_delivery.send_workspace_invitation_review_notice",
        send_review_notice,
    )
    invite = client.post(
        "/api/v1/admin/invitations",
        headers=auth_headers(),
        json={"target_contact": "review-invitee@example.test", "invited_role": "member"},
    )
    assert invite.status_code == 201

    resend = client.post(
        f"/api/v1/admin/invitations/{invite.json()['id']}/resend",
        headers=auth_headers(),
    )
    assert resend.status_code == 200
    assert resend.json()["status"] == "pending"
    assert sent_to == ["review-invitee@example.test"]

    revoke = client.post(
        f"/api/v1/admin/invitations/{invite.json()['id']}/revoke",
        headers=auth_headers(),
        json={"reason_code": "no_longer_needed"},
    )
    assert revoke.status_code == 200
    terminal_resend = client.post(
        f"/api/v1/admin/invitations/{invite.json()['id']}/resend",
        headers=auth_headers(),
    )
    assert terminal_resend.status_code == 409
    assert terminal_resend.json()["code"] == "invitation_resend_unavailable"
    assert sent_to == ["review-invitee@example.test"]


def test_admin_invitation_completion_contract(client) -> None:
    asyncio.run(_seed_roles(client))
    invited_user_id = UUID("30000000-0000-0000-0000-000000000150")
    asyncio.run(_seed_invited_identity(client, invited_user_id))
    invite = client.post(
        "/api/v1/admin/invitations",
        headers=auth_headers(),
        json={
            "target_contact": "invitee@example.test",
            "target_provider": "email",
            "invited_role": "member",
            "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )
    assert invite.status_code == 201

    complete = client.post(
        f"/api/v1/admin/invitations/{invite.json()['id']}/complete",
        headers=auth_headers_for(user_id=invited_user_id, device_id=DEFAULT_MEMBER_DEVICE_ID),
        json={
            "workspace_id": str(WORKSPACE_ID),
            "login_contact": "INVITEE@example.test",
            "provider": "email",
        },
    )

    assert complete.status_code == 200
    assert complete.json()["status"] == "completed"
    assert complete.json()["completed_by_user_id"] == str(invited_user_id)


def test_admin_invitation_completion_does_not_change_existing_member_role(client) -> None:
    asyncio.run(_seed_roles(client))
    invite = client.post(
        "/api/v1/admin/invitations",
        headers=auth_headers(),
        json={"target_contact": str(DEFAULT_MEMBER_USER_ID), "invited_role": "admin"},
    )
    assert invite.status_code == 201

    complete = client.post(
        f"/api/v1/admin/invitations/{invite.json()['id']}/complete",
        headers=auth_headers_for(
            user_id=DEFAULT_MEMBER_USER_ID, device_id=DEFAULT_MEMBER_DEVICE_ID
        ),
        json={
            "workspace_id": str(WORKSPACE_ID),
            "login_contact": str(DEFAULT_MEMBER_USER_ID),
            "provider": "email",
        },
    )
    detail = client.get(f"/api/v1/admin/users/{DEFAULT_MEMBER_USER_ID}", headers=auth_headers())

    assert complete.status_code == 200
    assert complete.json()["status"] == "completed"
    assert detail.status_code == 200
    assert detail.json()["role"] == "member"
    assert detail.json()["status"] == "active"


async def _seed_invited_identity(client, user_id: UUID) -> None:
    async with client.app_state["sessionmaker"]() as db:
        db.add(
            UserIdentity(
                id=user_id,
                organization_id=ORG_ID,
                external_subject=str(user_id),
                display_name="Invitee",
            )
        )
        await db.commit()


def test_admin_file_contract_metadata_safe(client) -> None:
    asyncio.run(_seed_roles(client))
    seeds = seed_cabinet_meetings(client)

    response = client.get("/api/v1/admin/files", headers=auth_headers())
    detail = client.get(f"/api/v1/admin/files/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["meeting_id"] == str(seeds.ready_id)
    assert set(payload) >= {
        "meeting_id",
        "owner_user_id",
        "processing_state",
        "deletion_state",
        "access",
        "actions",
    }
    assert "transcript_text" not in detail.text
    assert "storage_object_key" not in detail.text


def test_admin_metrics_and_audit_contract(client) -> None:
    metrics = client.get("/api/v1/admin/metrics", headers=auth_headers())
    audit = client.get("/api/v1/admin/audit", headers=auth_headers())

    assert metrics.status_code == 200
    assert audit.status_code == 200
    metric_payload = metrics.json()
    assert {card["family"] for card in metric_payload["metrics"]} == {
        "adoption",
        "usage",
        "funnel",
        "reliability",
        "governance",
    }
    for card in metric_payload["metrics"]:
        assert set(card) >= {
            "metric_id",
            "label",
            "definition",
            "denominator",
            "source_category",
            "date_window",
            "freshness",
            "value",
            "drill_down_path",
        }
    assert "entries" in audit.json()
    assert "sample" not in metrics.text.lower()
