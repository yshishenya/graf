"""At-most-once reservation and transport outcomes are separate from workflow retries."""

import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.integration.test_summary_sharing import prepare
from twobrain_rec_server.auth.email_delivery import EmailLoginDeliveryError
from twobrain_rec_server.workflows.summary_delivery import deliver_summary_batch


def test_unknown_never_replays_and_cancel_preserves_accepted(client, tmp_path):
    meeting, template = prepare(client, tmp_path)
    result = client.post(
        f"/api/v1/cabinet/meetings/{meeting}/summary-sharing/batches",
        headers=auth_headers(),
        json={
            "template_key": template,
            "recipients": ["first@example.test", "second@example.test"],
            "idempotency_key": "delivery",
        },
    )
    assert result.status_code == 200, result.text
    batch_id = UUID(result.json()["batch_id"])
    sender = AsyncMock()
    sender.send_summary_delivery.side_effect = [
        None,
        EmailLoginDeliveryError("postal_timeout", outcome_unknown=True, retryable=False),
    ]
    from tests.fakes.auth_contexts import WORKSPACE_ID

    async def deliver():
        await deliver_summary_batch(
            client.app.state.db_sessionmaker,
            settings=client.app.state.settings,
            batch_id=batch_id,
            workspace_id=WORKSPACE_ID,
            mail_client=sender,
        )

    asyncio.run(deliver())
    asyncio.run(deliver())
    assert sender.send_summary_delivery.await_count == 2
    status = client.get(
        f"/api/v1/cabinet/meetings/{meeting}/summary-sharing/batches/{batch_id}",
        headers=auth_headers(),
    ).json()
    assert status["counts"] == {"accepted": 1, "unknown": 1}
    unknown = next(row for row in status["recipients"] if row["state"] == "unknown")
    assert (
        client.post(
            f"/api/v1/cabinet/meetings/{meeting}/summary-sharing/batches/{batch_id}/recipients/{unknown['recipient_id']}/retry",
            headers=auth_headers(),
        ).status_code
        == 409
    )
    cancelled = client.post(
        f"/api/v1/cabinet/meetings/{meeting}/summary-sharing/batches/{batch_id}/cancel",
        headers=auth_headers(),
    )
    assert cancelled.json()["counts"] == status["counts"]


def test_known_failure_retry_and_addressed_saved_reader_preserve_full_grant(client, tmp_path):
    from datetime import UTC, datetime, timedelta

    from tests.fakes.auth_contexts import WORKSPACE_ID
    from tests.fixtures.cabinet_access import SHARED_USER_ID, add_workspace_user, auth_headers_for
    from twobrain_rec_server.cabinet.access import (
        invitation_address_hashes,
    )
    from twobrain_rec_server.db.models import ExternalIdentity, Meeting, MeetingShareGrant
    from twobrain_rec_server.db.models.summary_sharing import SummaryRecipientDelivery

    meeting_id, template = prepare(client, tmp_path)
    add_workspace_user(client)
    settings = client.app.state.settings

    async def setup():
        async with client.app.state.db_sessionmaker() as db:
            # Deliberately mimic a pre-existing accepted full invitation for the
            # same verified email: neither its ACL nor token may be rebound.
            db.add(
                ExternalIdentity(
                    user_id=SHARED_USER_ID,
                    provider="email",
                    provider_subject="reader@example.test",
                    email="reader@example.test",
                    is_verified=True,
                    is_active=True,
                )
            )
            grant = MeetingShareGrant(
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                grant_type="user",
                audience_type="user",
                audience_id=SHARED_USER_ID,
                grantee_user_id=SHARED_USER_ID,
                created_by_user_id=(await db.get(Meeting, meeting_id)).created_by_user_id,
                status="active",
                content_scope="full_meeting",
                can_download=True,
                can_export=True,
                expires_at=datetime.now(UTC) + timedelta(days=90),
                share_token_hash="existing-token-hash",
                metadata_json={
                    "source": "accepted_external_invitation",
                    "recipient_address_hash": next(
                        iter(invitation_address_hashes("reader@example.test"))
                    ),
                },
            )
            db.add(grant)
            await db.commit()
            return grant.id, grant.expires_at

    grant_id, expiry = asyncio.run(setup())
    result = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-sharing/batches",
        headers=auth_headers(),
        json={
            "template_key": template,
            "recipients": ["reader@example.test"],
            "idempotency_key": "failure-retry",
        },
    )
    assert result.status_code == 200, result.text
    batch = result.json()
    sender = AsyncMock()
    sender.send_summary_delivery.side_effect = [
        EmailLoginDeliveryError("postal_delivery_rejected"),
        "postal-message-id",
    ]

    async def deliver():
        await deliver_summary_batch(
            client.app.state.db_sessionmaker,
            settings=settings,
            workspace_id=WORKSPACE_ID,
            batch_id=UUID(batch["batch_id"]),
            mail_client=sender,
        )

    asyncio.run(deliver())
    status_url = (
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-sharing/batches/{batch['batch_id']}"
    )
    failed = client.get(status_url, headers=auth_headers()).json()
    recipient = failed["recipients"][0]
    assert recipient["state"] == "failed" and recipient["can_retry"]
    retry = client.post(
        status_url + f"/recipients/{recipient['recipient_id']}/retry", headers=auth_headers()
    )
    assert retry.status_code == 200, retry.text
    asyncio.run(deliver())
    assert sender.send_summary_delivery.await_count == 2
    url = sender.send_summary_delivery.call_args.kwargs["read_url"].replace(
        "https://graf.example.test", ""
    )
    doc = client.get(url, headers=auth_headers_for())
    assert doc.status_code == 200, doc.text
    assert doc.json() == batch["summary"]["projection"]

    async def verify():
        async with client.app.state.db_sessionmaker() as db:
            grant = await db.get(MeetingShareGrant, grant_id)
            assert (
                grant.content_scope,
                grant.can_download,
                grant.can_export,
                grant.share_token_hash,
                grant.expires_at,
                grant.published_summary_id,
            ) == ("full_meeting", True, True, "existing-token-hash", expiry, None)
            delivery = await db.get(SummaryRecipientDelivery, UUID(recipient["recipient_id"]))
            assert delivery.provider_message_id == "postal-message-id"

    asyncio.run(verify())


def test_dispatch_commit_start_gap_recovers_once_and_stale_reservation_is_unknown(client, tmp_path):
    from datetime import UTC, datetime, timedelta

    from tests.fakes.auth_contexts import WORKSPACE_ID
    from twobrain_rec_server.db.models.summary_sharing import SummaryRecipientDelivery
    from twobrain_rec_server.workflows.summary_delivery import (
        reconcile_summary_delivery_once,
        reserve_recipient,
    )

    meeting_id, template = prepare(client, tmp_path)
    result = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-sharing/batches",
        headers=auth_headers(),
        json={
            "template_key": template,
            "recipients": ["recover@example.test"],
            "idempotency_key": "recover",
        },
    ).json()
    now = datetime.now(UTC)
    from types import SimpleNamespace

    from temporalio.client import WorkflowExecutionStatus

    temporal = AsyncMock()
    temporal.get_workflow_handle = Mock(
        return_value=SimpleNamespace(
            describe=AsyncMock(return_value=SimpleNamespace(status=WorkflowExecutionStatus.RUNNING))
        )
    )
    temporal.start_workflow.side_effect = [TimeoutError(), None]

    async def recover():
        factory = client.app.state.db_sessionmaker
        assert (
            await reconcile_summary_delivery_once(
                factory, settings=client.app.state.settings, temporal_client=temporal, now=now
            )
            == 1
        )
        assert (
            await reconcile_summary_delivery_once(
                factory,
                settings=client.app.state.settings,
                temporal_client=temporal,
                now=now + timedelta(seconds=30),
            )
            == 1
        )
        assert (
            await reconcile_summary_delivery_once(
                factory,
                settings=client.app.state.settings,
                temporal_client=temporal,
                now=now + timedelta(seconds=60),
            )
            == 0
        )
        first, second = temporal.start_workflow.call_args_list
        assert first.kwargs["id"] == second.kwargs["id"]
        recipient_id = UUID(result["recipients"][0]["recipient_id"])
        payload = await reserve_recipient(
            factory,
            settings=client.app.state.settings,
            workspace_id=WORKSPACE_ID,
            batch_id=UUID(result["batch_id"]),
            recipient_id=recipient_id,
        )
        assert payload is not None
        await reconcile_summary_delivery_once(
            factory,
            settings=client.app.state.settings,
            temporal_client=temporal,
            now=now + timedelta(minutes=3),
        )
        async with factory() as db:
            recipient = await db.get(SummaryRecipientDelivery, recipient_id)
            assert recipient.state == "unknown"

    asyncio.run(recover())


def test_addressed_acceptance_reopens_frozen_document_and_revocation_denies(client, tmp_path):
    from datetime import UTC, datetime, timedelta

    from tests.fakes.auth_contexts import WORKSPACE_ID
    from tests.fixtures.cabinet_access import (
        SHARED_USER_ID,
        add_workspace_user,
        auth_headers_for,
    )
    from twobrain_rec_server.db.models import ExternalIdentity, MeetingOutcomeSet, MeetingShareGrant
    from twobrain_rec_server.db.models.summary_sharing import SummaryRecipientDelivery

    meeting_id, template = prepare(client, tmp_path)
    add_workspace_user(client)

    # With no current permission, dispatch creates an addressed invitation.
    async def identity():
        async with client.app.state.db_sessionmaker() as db:
            db.add(
                ExternalIdentity(
                    user_id=SHARED_USER_ID,
                    provider="email",
                    provider_subject="addressed@example.test",
                    email="addressed@example.test",
                    is_verified=True,
                    is_active=True,
                )
            )
            await db.commit()

    asyncio.run(identity())
    base = f"/api/v1/cabinet/meetings/{meeting_id}/summary-sharing/batches"
    response = client.post(
        base,
        headers=auth_headers(),
        json={
            "template_key": template,
            "recipients": ["addressed@example.test"],
            "idempotency_key": "addressed",
        },
    )
    batch = response.json()
    sender = AsyncMock()
    sender.send_summary_delivery.return_value = None

    async def deliver():
        await deliver_summary_batch(
            client.app.state.db_sessionmaker,
            settings=client.app.state.settings,
            workspace_id=WORKSPACE_ID,
            batch_id=UUID(batch["batch_id"]),
            mail_client=sender,
        )

    asyncio.run(deliver())
    email_path = sender.send_summary_delivery.call_args.kwargs["read_url"].replace(
        "https://graf.example.test", ""
    )
    token = email_path.split("/share-invitations/")[1].split("?")[0]
    accepted = client.post(
        f"/api/v1/cabinet/share-invitations/{token}/accept?workspace_id={WORKSPACE_ID}",
        headers=auth_headers_for(),
    )
    assert accepted.status_code == 200, accepted.text
    received = accepted.json()["share_url"]

    async def supersede():
        async with client.app.state.db_sessionmaker() as db:
            source = await db.get(MeetingOutcomeSet, UUID(batch["summary"]["source_outcome_id"]))
            source.revision_state = "superseded"
            delivery = await db.get(
                SummaryRecipientDelivery, UUID(batch["recipients"][0]["recipient_id"])
            )
            grant = await db.get(MeetingShareGrant, delivery.grant_id)
            # An independent grant lifetime can expire before this document.
            grant.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()

    asyncio.run(supersede())
    repeat = client.get(email_path, headers=auth_headers_for(), follow_redirects=False)
    assert repeat.status_code == 303
    doc = client.get(repeat.headers["location"], headers=auth_headers_for())
    assert doc.status_code == 200, doc.text
    assert doc.json() == batch["summary"]["projection"]

    async def revoke():
        async with client.app.state.db_sessionmaker() as db:
            delivery = await db.get(
                SummaryRecipientDelivery, UUID(batch["recipients"][0]["recipient_id"])
            )
            grant = await db.get(MeetingShareGrant, delivery.grant_id)
            grant.status = "revoked"
            await db.commit()

    asyncio.run(revoke())
    assert client.get(received, headers=auth_headers_for()).status_code == 404

    async def unrelated_grant():
        from uuid import uuid4

        from tests.fakes.auth_contexts import USER_ID
        from twobrain_rec_server.cabinet.access import hash_share_token

        async with client.app.state.db_sessionmaker() as db:
            db.add(
                MeetingShareGrant(
                    id=uuid4(),
                    workspace_id=WORKSPACE_ID,
                    meeting_id=UUID(str(meeting_id)),
                    grant_type="user",
                    grantee_user_id=SHARED_USER_ID,
                    audience_type="user",
                    audience_id=SHARED_USER_ID,
                    created_by_user_id=USER_ID,
                    status="active",
                    content_scope="full_meeting",
                    share_token_hash=hash_share_token("synthetic-replacement"),
                )
            )
            await db.commit()

    asyncio.run(unrelated_grant())
    replay = client.post(
        f"/api/v1/cabinet/share-invitations/{token}/accept?workspace_id={WORKSPACE_ID}",
        headers=auth_headers_for(),
    )
    assert replay.status_code == 404, replay.text
    assert client.get(received, headers=auth_headers_for()).status_code == 404


def test_deactivated_sender_cancels_unreserved_mail(client, tmp_path):
    from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
    from twobrain_rec_server.db.models import UserIdentity

    meeting_id, template = prepare(client, tmp_path)
    batch = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-sharing/batches",
        headers=auth_headers(),
        json={
            "template_key": template,
            "recipients": ["inactive-owner@example.test"],
            "idempotency_key": "inactive",
        },
    ).json()
    sender = AsyncMock()

    async def run():
        async with client.app.state.db_sessionmaker() as db:
            owner = await db.get(UserIdentity, USER_ID)
            owner.status = "disabled"
            await db.commit()
        await deliver_summary_batch(
            client.app.state.db_sessionmaker,
            settings=client.app.state.settings,
            workspace_id=WORKSPACE_ID,
            batch_id=UUID(batch["batch_id"]),
            mail_client=sender,
        )
        from twobrain_rec_server.db.models.summary_sharing import SummaryRecipientDelivery

        async with client.app.state.db_sessionmaker() as db:
            recipient = await db.get(
                SummaryRecipientDelivery, UUID(batch["recipients"][0]["recipient_id"])
            )
            assert recipient.state == "cancelled"
            assert recipient.failure_code == "summary_owner_authority_lost"

    asyncio.run(run())
    sender.send_summary_delivery.assert_not_awaited()


def test_finished_workflow_recovers_only_unreserved_recipients(client, tmp_path):
    from datetime import UTC, datetime, timedelta
    from types import SimpleNamespace

    from temporalio.client import WorkflowExecutionStatus
    from temporalio.common import WorkflowIDReusePolicy

    from tests.fakes.auth_contexts import WORKSPACE_ID
    from twobrain_rec_server.workflows.summary_delivery import reconcile_summary_delivery_once

    meeting, template = prepare(client, tmp_path)
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting}/summary-sharing/batches",
        headers=auth_headers(),
        json={
            "template_key": template,
            "recipients": ["recover-terminal@example.test"],
            "idempotency_key": "recover-terminal",
        },
    )
    assert response.status_code == 200, response.text
    batch_id = UUID(response.json()["batch_id"])
    temporal = AsyncMock()
    describe = AsyncMock(return_value=SimpleNamespace(status=WorkflowExecutionStatus.FAILED))
    temporal.get_workflow_handle = Mock(return_value=SimpleNamespace(describe=describe))
    sender = AsyncMock()
    sender.send_summary_delivery.return_value = None
    now = datetime.now(UTC)

    async def verify():
        factory = client.app.state.db_sessionmaker
        settings = client.app.state.settings
        assert (
            await reconcile_summary_delivery_once(
                factory, settings=settings, temporal_client=temporal, now=now
            )
            == 1
        )
        first = temporal.start_workflow.call_args.kwargs["id"]
        assert (
            temporal.start_workflow.call_args.kwargs["id_reuse_policy"]
            == WorkflowIDReusePolicy.REJECT_DUPLICATE
        )
        # Temporal exhausted retries before the activity reserved any recipient.
        assert (
            await reconcile_summary_delivery_once(
                factory, settings=settings, temporal_client=temporal, now=now + timedelta(minutes=1)
            )
            == 0
        )
        assert (
            await reconcile_summary_delivery_once(
                factory, settings=settings, temporal_client=temporal, now=now + timedelta(minutes=2)
            )
            == 1
        )
        second = temporal.start_workflow.call_args.kwargs["id"]
        assert second != first
        await deliver_summary_batch(
            factory,
            settings=settings,
            workspace_id=WORKSPACE_ID,
            batch_id=batch_id,
            mail_client=sender,
        )
        assert (
            await reconcile_summary_delivery_once(
                factory, settings=settings, temporal_client=temporal, now=now + timedelta(minutes=3)
            )
            == 0
        )
        assert (
            await reconcile_summary_delivery_once(
                factory, settings=settings, temporal_client=temporal, now=now + timedelta(minutes=4)
            )
            == 0
        )
        await deliver_summary_batch(
            factory,
            settings=settings,
            workspace_id=WORKSPACE_ID,
            batch_id=batch_id,
            mail_client=sender,
        )
        assert sender.send_summary_delivery.await_count == 1
        assert temporal.start_workflow.await_count == 2

    asyncio.run(verify())


def test_external_delivery_switch_rechecked_before_reservation(client, tmp_path):
    from tests.fakes.auth_contexts import WORKSPACE_ID
    from twobrain_rec_server.db.models.summary_sharing import SummaryRecipientDelivery

    meeting, template = prepare(client, tmp_path)
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting}/summary-sharing/batches",
        headers=auth_headers(),
        json={
            "template_key": template,
            "recipients": ["switched-off@example.test"],
            "idempotency_key": "switched-off",
        },
    )
    assert response.status_code == 200, response.text
    batch = response.json()
    client.app.state.settings.share_external_invitations_enabled = False
    sender = AsyncMock()

    async def verify():
        await deliver_summary_batch(
            client.app.state.db_sessionmaker,
            settings=client.app.state.settings,
            workspace_id=WORKSPACE_ID,
            batch_id=UUID(batch["batch_id"]),
            mail_client=sender,
        )
        async with client.app.state.db_sessionmaker() as db:
            row = await db.get(
                SummaryRecipientDelivery, UUID(batch["recipients"][0]["recipient_id"])
            )
            assert row.state == "cancelled"
            assert row.invitation_id is None
        assert sender.send_summary_delivery.await_count == 0

    asyncio.run(verify())


@pytest.mark.parametrize("started", [False, True])
def test_delivery_deadline_finishes_only_unreserved_rows(client, tmp_path, started):
    from datetime import UTC, datetime, timedelta
    from types import SimpleNamespace

    from temporalio.client import WorkflowExecutionStatus

    from twobrain_rec_server.db.models import DispatchIntent
    from twobrain_rec_server.db.models.summary_sharing import (
        SummaryDeliveryBatch,
        SummaryRecipientDelivery,
    )
    from twobrain_rec_server.workflows.summary_delivery import reconcile_summary_delivery_once

    meeting, template = prepare(client, tmp_path)
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting}/summary-sharing/batches",
        headers=auth_headers(),
        json={
            "template_key": template,
            "recipients": [f"deadline-{i}@example.test" for i in range(4)],
            "idempotency_key": "deadline",
        },
    )
    assert response.status_code == 200, response.text
    batch_id = UUID(response.json()["batch_id"])
    now = datetime.now(UTC) + timedelta(hours=25)
    temporal = AsyncMock()
    temporal.get_workflow_handle = Mock(
        return_value=SimpleNamespace(
            describe=AsyncMock(return_value=SimpleNamespace(status=WorkflowExecutionStatus.FAILED))
        )
    )

    async def verify():
        from sqlalchemy import select

        factory = client.app.state.db_sessionmaker
        async with factory() as db:
            rows = list(
                await db.scalars(
                    select(SummaryRecipientDelivery)
                    .where(SummaryRecipientDelivery.batch_id == batch_id)
                    .order_by(SummaryRecipientDelivery.id)
                )
            )
            for row, state in zip(rows, ("pending", "accepted", "unknown", "sending"), strict=True):
                row.state = state
                if state == "sending":
                    row.reserved_at = now - timedelta(seconds=1)
            preserved_ids = {row.id: row.state for row in rows if row.state != "pending"}
            intent = await db.scalar(
                select(DispatchIntent).where(DispatchIntent.meeting_id == UUID(str(meeting)))
            )
            if started:
                intent.state = "started"
                intent.external_workflow_id = "synthetic-deadline-workflow"
            await db.commit()
        assert (
            await reconcile_summary_delivery_once(
                factory, settings=client.app.state.settings, temporal_client=temporal, now=now
            )
            == 0
        )
        async with factory() as db:
            rows = list(
                await db.scalars(
                    select(SummaryRecipientDelivery).where(
                        SummaryRecipientDelivery.batch_id == batch_id
                    )
                )
            )
            assert {row.state for row in rows} == {"cancelled", "accepted", "unknown", "sending"}
            assert all(
                row.state == preserved_ids[row.id] for row in rows if row.id in preserved_ids
            )
            batch = await db.get(SummaryDeliveryBatch, batch_id)
            assert batch.failure_code == "summary_delivery_deadline_expired"
        temporal.start_workflow.assert_not_awaited()

    asyncio.run(verify())
