"""F286 disclosure regressions: stable document, owner authority, atomic batches."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import WORKSPACE_ID
from tests.fixtures.cabinet import create_ready_meeting
from tests.fixtures.cabinet_access import add_workspace_user, auth_headers_for
from tests.integration.test_rls_postgres_policies import (
    _exact_app_role_engine,
    _request_context,
    _seed_probe_rows,
    apply_tenant_context_to_connection,
)
from twobrain_rec_server.db.models import Meeting, MeetingOutcomeSet, MeetingSummarySlot
from twobrain_rec_server.db.models.summary_sharing import (
    PublishedMeetingSummary,
    SummaryDeliveryBatch,
    SummaryRecipientDelivery,
)

pytest_plugins = ("tests.integration.test_rls_postgres_policies",)


def prepare(client, tmp_path):
    from cryptography.fernet import Fernet

    key = tmp_path / "sharing.key"
    key.write_bytes(Fernet.generate_key())
    settings = client.app.state.settings
    settings.credential_encryption_key_file = key
    settings.share_public_links_enabled = True
    settings.share_public_links_abuse_gate_approved = True
    settings.share_external_invitations_enabled = True
    settings.public_base_url = "https://graf.example.test"
    meeting_id = create_ready_meeting(client)
    from tests.integration.test_recording_share_public_link import _seed_external_full_summary

    asyncio.run(_seed_external_full_summary(client, meeting_id))

    async def template():
        async with client.app.state.db_sessionmaker() as db:
            return await db.scalar(
                select(MeetingSummarySlot.template_key).where(
                    MeetingSummarySlot.meeting_id == UUID(str(meeting_id))
                )
            )

    return meeting_id, asyncio.run(template())


def test_copy_is_stable_and_survives_superseded_source(client, tmp_path):
    meeting_id, template = prepare(client, tmp_path)
    url = f"/api/v1/cabinet/meetings/{meeting_id}/summary-sharing/link"
    first = client.post(url, headers=auth_headers(), json={"template_key": template})
    assert first.status_code == 200, first.text
    saved = first.json()

    async def supersede():
        async with client.app.state.db_sessionmaker() as db:
            meeting = await db.get(Meeting, UUID(str(meeting_id)))
            meeting.title = "changed title"
            source = await db.get(MeetingOutcomeSet, UUID(saved["summary"]["source_outcome_id"]))
            source.revision_state = "superseded"
            await db.commit()

    asyncio.run(supersede())
    again = client.post(url, headers=auth_headers(), json={"template_key": template})
    assert again.json() == saved
    public_path = saved["share_url"].split("https://graf.example.test")[-1]
    response = client.get(public_path)
    assert response.status_code == 200, response.text
    assert response.json()["meeting_label"] == saved["summary"]["projection"]["meeting_label"]
    assert response.headers["cache-control"] == "private, no-store"
    stale = client.post(
        url + "/rotate",
        headers=auth_headers(),
        json={"grant_id": saved["grant_id"], "expected_version": saved["version"] + 1},
    )
    assert stale.status_code == 409
    revoke = client.request(
        "DELETE",
        url,
        headers=auth_headers(),
        json={"grant_id": saved["grant_id"], "expected_version": saved["version"]},
    )
    assert revoke.status_code == 200
    assert client.get(public_path).status_code == 404


def test_batch_idempotency_no_grants_before_dispatch(client, tmp_path):
    meeting_id, template = prepare(client, tmp_path)
    url = f"/api/v1/cabinet/meetings/{meeting_id}/summary-sharing/batches"
    payload = {
        "template_key": template,
        "recipients": ["First@example.test", "first@example.test", "second@example.test"],
        "idempotency_key": "same-operation",
    }
    first = client.post(url, headers=auth_headers(), json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["counts"] == {"pending": 2}
    second = client.post(url, headers=auth_headers(), json=payload)
    assert second.json()["batch_id"] == first.json()["batch_id"]
    conflict = client.post(
        url, headers=auth_headers(), json={**payload, "recipients": ["third@example.test"]}
    )
    assert conflict.status_code == 409

    async def ledger():
        async with client.app.state.db_sessionmaker() as db:
            assert await db.scalar(select(func.count()).select_from(SummaryDeliveryBatch)) == 1
            rows = (await db.scalars(select(SummaryRecipientDelivery))).all()
            assert all(row.invitation_id is None and row.grant_id is None for row in rows)
            assert await db.scalar(select(func.count()).select_from(PublishedMeetingSummary)) == 1

    asyncio.run(ledger())
    oversized = client.post(
        url,
        headers=auth_headers(),
        json={
            **payload,
            "idempotency_key": "too-many",
            "recipients": [f"r{i}@example.test" for i in range(51)],
        },
    )
    assert oversized.status_code == 422
    add_workspace_user(client)
    denied = client.post(
        url, headers=auth_headers_for(), json={**payload, "idempotency_key": "other"}
    )
    assert denied.status_code == 404


def test_forwarded_magic_never_creates_session(client):
    response = client.post(
        "/share-invitations/continue/magic?workspace_id=" + str(WORKSPACE_ID),
        data={"state": "x" * 32, "magic_csrf": "x" * 32},
        follow_redirects=False,
    )
    assert response.status_code in (401, 404, 303)
    if response.status_code == 303:
        assert response.headers["location"].startswith("/login")
    assert "graf_auth_session" not in response.cookies


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_f286_runtime_roles_isolate_publications(rls_engine, migrated_postgres_urls):
    from uuid import uuid4

    from twobrain_rec_server.db.tenant_context import apply_tenant_context
    from twobrain_rec_server.workflows.summary_delivery import tenant

    ids = await _seed_probe_rows(rls_engine)
    publication_id = uuid4()
    async with async_sessionmaker(rls_engine, expire_on_commit=False)() as db:
        await apply_tenant_context(db, _request_context(ids, "a"))
        db.add(
            PublishedMeetingSummary(
                id=publication_id,
                workspace_id=ids["workspace_a"],
                meeting_id=ids["meeting_a"],
                owner_user_id=ids["user_a"],
                source_outcome_id=uuid4(),
                template_key="meeting_minutes",
                schema_version=1,
                projection_json={
                    "meeting_label": "synthetic",
                    "occurred_at": datetime.now(UTC).isoformat(),
                    "duration_seconds": 0,
                    "summary_sections": [],
                    "protocol": None,
                },
            )
        )
        await db.commit()
    async with _exact_app_role_engine(migrated_postgres_urls.migration_url) as engine:
        for scope in (None, "b", "a"):
            async with engine.begin() as connection:
                if scope:
                    await apply_tenant_context_to_connection(
                        connection, _request_context(ids, scope)
                    )
                found = await connection.scalar(
                    select(PublishedMeetingSummary.id).where(
                        PublishedMeetingSummary.id == publication_id
                    )
                )
                assert found == (publication_id if scope == "a" else None)
                for table in (
                    "published_meeting_summaries",
                    "summary_delivery_batches",
                    "summary_recipient_deliveries",
                    "summary_email_suppressions",
                ):
                    assert await connection.scalar(
                        text(
                            "SELECT relrowsecurity AND relforcerowsecurity FROM pg_class WHERE relname = :table"
                        ),
                        {"table": table},
                    )
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            assert await tenant(db, ids["workspace_a"], ids["user_a"])
            assert (
                await db.scalar(
                    select(PublishedMeetingSummary.id).where(
                        PublishedMeetingSummary.id == publication_id
                    )
                )
                == publication_id
            )


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_real_app_role_reserves_manual_email(rls_engine, migrated_postgres_urls, tmp_path):
    from datetime import timedelta
    from types import SimpleNamespace
    from uuid import uuid4

    from cryptography.fernet import Fernet

    from twobrain_rec_server.cabinet.access import hash_invitation_address
    from twobrain_rec_server.cabinet.summary_sharing import seal
    from twobrain_rec_server.db.tenant_context import apply_tenant_context
    from twobrain_rec_server.workflows.summary_delivery import reserve_recipient

    ids = await _seed_probe_rows(rls_engine)
    key = Fernet.generate_key()
    path = tmp_path / "key"
    path.write_bytes(key)
    settings = SimpleNamespace(
        credential_encryption_key_file=path,
        public_base_url="https://graf.example.test",
        share_external_invitations_enabled=True,
    )
    publication_id, batch_id, recipient_id = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    async with async_sessionmaker(rls_engine, expire_on_commit=False)() as db:
        await apply_tenant_context(db, _request_context(ids, "a"))
        db.add(
            PublishedMeetingSummary(
                id=publication_id,
                workspace_id=ids["workspace_a"],
                meeting_id=ids["meeting_a"],
                owner_user_id=ids["user_a"],
                source_outcome_id=uuid4(),
                template_key="summary",
                schema_version=1,
                projection_json={
                    "meeting_label": "synthetic",
                    "occurred_at": now.isoformat(),
                    "duration_seconds": 0,
                    "summary_sections": [],
                    "protocol": None,
                },
            )
        )
        await db.flush()
        db.add(
            SummaryDeliveryBatch(
                id=batch_id,
                workspace_id=ids["workspace_a"],
                meeting_id=ids["meeting_a"],
                owner_user_id=ids["user_a"],
                published_summary_id=publication_id,
                idempotency_key="app-role",
                request_fingerprint="synthetic",
                state="pending",
                automatic=False,
                scheduled_at=now,
                deadline_at=now + timedelta(hours=24),
            )
        )
        await db.flush()
        db.add(
            SummaryRecipientDelivery(
                id=recipient_id,
                workspace_id=ids["workspace_a"],
                batch_id=batch_id,
                normalized_address_hash=hash_invitation_address("synthetic@example.test"),
                encrypted_address=seal("synthetic@example.test", key),
                state="pending",
                attempt_count=0,
            )
        )
        await db.commit()
    async with _exact_app_role_engine(migrated_postgres_urls.migration_url) as engine:
        payload = await reserve_recipient(
            async_sessionmaker(engine, expire_on_commit=False),
            settings=settings,
            workspace_id=ids["workspace_a"],
            batch_id=batch_id,
            recipient_id=recipient_id,
        )
        assert payload is not None
        assert payload["recipient_email"] == "synthetic@example.test"


def test_nojs_form_validates_and_preserves_operation_and_workspace(client, tmp_path):
    meeting_id, template = prepare(client, tmp_path)
    base = f"/api/v1/cabinet/meetings/{meeting_id}/summary-sharing/form"
    page = client.get(base, params={"template_key": template}, headers=auth_headers())
    assert page.status_code == 200, page.text
    invalid = client.post(
        base,
        headers=auth_headers(),
        data={
            "action": "send",
            "template_key": template,
            "recipients": "bad-address",
            "idempotency_key": "form-operation",
        },
    )
    assert invalid.status_code == 422, invalid.text
    assert 'value="form-operation"' in invalid.text
    sent = client.post(
        base,
        headers=auth_headers(),
        data={
            "action": "send",
            "template_key": template,
            "recipients": "valid@example.test",
            "idempotency_key": "form-operation",
        },
        follow_redirects=False,
    )
    assert sent.status_code == 303, sent.text
    assert f"workspace_id={WORKSPACE_ID}" in sent.headers["location"]
