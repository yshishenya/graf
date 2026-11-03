"""F286 fixed documents follow a real proof-bound merge under FORCE RLS."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.fakes.auth_contexts import (
    PERSONAL_WORKSPACE_ID,
    USER_ID,
    WORKSPACE_ID,
    duplicate_account_fixture,
)
from tests.integration.test_account_merge import (
    _create_ready_merge,
    _seed_empty_source,
    _seed_source_meeting,
)
from tests.integration.test_rls_postgres_policies import _exact_app_role_engine
from twobrain_rec_server.auth.account_merge import confirm_merge_intent
from twobrain_rec_server.cabinet.access import hash_invitation_address, hash_share_token
from twobrain_rec_server.cabinet.summary_sharing import seal
from twobrain_rec_server.db.models import (
    Meeting,
    MeetingShareGrant,
    MeetingShareInvitation,
    Workspace,
)
from twobrain_rec_server.db.models.summary_sharing import (
    PublishedMeetingSummary,
    SummaryDeliveryBatch,
    SummaryRecipientDelivery,
)
from twobrain_rec_server.db.tenant_context import AccountMergeTenantContext, apply_tenant_context
from twobrain_rec_server.workflows.summary_delivery import deliver_summary_batch

# The exact application's login role is cluster-wide; use the serial strict phase.
pytestmark = pytest.mark.strict_rls

SCOPE_CONSTRAINTS = (
    "fk_published_summary_meeting_scope",
    "fk_summary_batch_publication_scope",
    "fk_summary_recipient_batch_scope",
    "fk_grant_publication_scope",
    "fk_invitation_publication_scope",
)


def test_fixed_summary_graph_merges_with_original_authority_and_no_replayed_mail(client, tmp_path):
    source = duplicate_account_fixture(287, email="summary-merge@example.test")
    key = Fernet.generate_key()
    key_file = tmp_path / "summary-merge.key"
    key_file.write_bytes(key)
    settings = client.app.state.settings
    settings.credential_encryption_key_file = key_file
    settings.share_external_invitations_enabled = True
    settings.public_base_url = "https://graf.example.test"
    now = datetime.now(UTC)
    document = {
        "meeting_label": "Synthetic merge summary",
        "occurred_at": now.isoformat(),
        "duration_seconds": 1,
        "summary_sections": [{"category": "summary", "text": "Synthetic summary"}],
        "protocol": None,
    }
    public_token = "synthetic-public-merge-token"
    recipient_token = "synthetic-addressed-merge-token"

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db, user_id=source.user_id, workspace_id=source.workspace_id, email=source.email
            )
            meeting = await _seed_source_meeting(
                db,
                source_user_id=source.user_id,
                source_workspace_id=source.workspace_id,
                suffix=uuid4().hex,
            )
            publication = PublishedMeetingSummary(
                id=uuid4(),
                workspace_id=source.workspace_id,
                meeting_id=meeting.id,
                owner_user_id=source.user_id,
                source_outcome_id=uuid4(),
                template_key="summary",
                projection_json=document,
            )
            db.add(publication)
            await db.flush()
            grants = [
                MeetingShareGrant(
                    id=uuid4(),
                    workspace_id=source.workspace_id,
                    meeting_id=meeting.id,
                    created_by_user_id=source.user_id,
                    published_summary_id=publication.id,
                    grant_type=kind,
                    audience_type=kind,
                    audience_id=USER_ID if kind == "user" else None,
                    grantee_user_id=USER_ID if kind == "user" else None,
                    share_token_hash=hash_share_token(token),
                    share_token_ciphertext=seal(token, key),
                    content_scope="summary_only",
                    status="active",
                )
                for kind, token in (("link", public_token), ("user", recipient_token))
            ]
            invitation = MeetingShareInvitation(
                id=uuid4(),
                workspace_id=source.workspace_id,
                meeting_id=meeting.id,
                invited_by_user_id=source.user_id,
                resolved_user_id=USER_ID,
                published_summary_id=publication.id,
                normalized_address_hash=hash_invitation_address("accepted@example.test"),
                encrypted_delivery_address="",
                token_hash=hash_share_token("synthetic-invitation-merge-token"),
                status="accepted",
                accepted_at=now,
                expires_at=now + timedelta(days=7),
                read_expires_at=now + timedelta(days=30),
            )
            batch = SummaryDeliveryBatch(
                id=uuid4(),
                workspace_id=source.workspace_id,
                meeting_id=meeting.id,
                owner_user_id=source.user_id,
                published_summary_id=publication.id,
                idempotency_key="synthetic-merge-delivery",
                request_fingerprint="a" * 64,
                automatic=False,
                scheduled_at=now,
                deadline_at=now + timedelta(hours=24),
            )
            db.add_all([*grants, invitation, batch])
            await db.flush()
            recipients = [
                SummaryRecipientDelivery(
                    id=uuid4(),
                    workspace_id=source.workspace_id,
                    batch_id=batch.id,
                    normalized_address_hash=hash_invitation_address(f"{state}@example.test"),
                    encrypted_address=seal(f"{state}@example.test", key),
                    state=state,
                    user_id=USER_ID if state == "accepted" else None,
                    invitation_id=invitation.id if state == "accepted" else None,
                    grant_id=grants[1].id if state == "accepted" else None,
                    reserved_at=now if state != "pending" else None,
                    completed_at=now if state != "pending" else None,
                    attempt_count=1 if state != "pending" else 0,
                    provider_message_id="synthetic-provider-receipt"
                    if state == "accepted"
                    else None,
                )
                for state in ("pending", "accepted", "unknown")
            ]
            db.add_all(recipients)
            await db.flush()
            rows = [meeting, publication, batch, invitation, *grants, *recipients]
            row_ids = [(type(row), row.id) for row in rows]
            original_recipients = {
                row.id: (
                    row.state,
                    row.encrypted_address,
                    row.user_id,
                    row.invitation_id,
                    row.grant_id,
                    row.reserved_at,
                    row.completed_at,
                    row.attempt_count,
                    row.provider_message_id,
                )
                for row in recipients
            }
            original_grants = {
                row.id: (row.share_token_hash, row.share_token_ciphertext, row.publication_version)
                for row in grants
            }
            publication_id, batch_id, meeting_id = publication.id, batch.id, meeting.id
            invitation_id = invitation.id
            invitation_token_hash = invitation.token_hash
            intent, preview = await _create_ready_merge(db, source_user_id=source.user_id)
            assert preview.blocker_codes == ()
            await db.commit()
            intent_id = intent.id

        async with _exact_app_role_engine(settings.database_url) as engine:
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            async with sessions() as db:
                assert await db.scalar(text("SELECT session_user")) == "twobrain_rec_app"
                assert not await db.scalar(
                    text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=session_user")
                )
                constraints = dict(
                    (
                        await db.execute(
                            text(
                                "SELECT conname, confupdtype::text FROM pg_constraint WHERE conname=ANY(:names)"
                            ),
                            {"names": list(SCOPE_CONSTRAINTS)},
                        )
                    ).all()
                )
                assert constraints == {name: "c" for name in SCOPE_CONSTRAINTS}
                await apply_tenant_context(
                    db,
                    AccountMergeTenantContext(
                        intent_id=uuid4(),
                        workspace_id=WORKSPACE_ID,
                        survivor_user_id=USER_ID,
                        source_user_id=source.user_id,
                    ),
                )
                assert not await db.scalar(text("SELECT rec_account_merge_context_valid()"))
                for model in (
                    PublishedMeetingSummary,
                    SummaryDeliveryBatch,
                    SummaryRecipientDelivery,
                ):
                    assert not list(await db.scalars(select(model.id)))
                    assert (
                        await db.execute(
                            model.__table__.update()
                            .where(model.workspace_id == source.workspace_id)
                            .values(workspace_id=PERSONAL_WORKSPACE_ID)
                        )
                    ).rowcount == 0
                await db.rollback()
            async with sessions() as db:
                await apply_tenant_context(
                    db,
                    AccountMergeTenantContext(
                        intent_id=intent_id,
                        workspace_id=WORKSPACE_ID,
                        survivor_user_id=USER_ID,
                        source_user_id=source.user_id,
                    ),
                )
                assert await db.scalar(text("SELECT rec_account_merge_context_valid()"))
                result = await confirm_merge_intent(
                    db,
                    intent_id=intent_id,
                    preview_fingerprint=preview.fingerprint,
                    idempotency_key="fixed-summary-graph-merge",
                )
                assert result.status == "completed"
                await db.commit()
                assert not await db.scalar(text("SELECT rec_account_merge_context_valid()"))
                assert not list(await db.scalars(select(PublishedMeetingSummary.id)))

            # A new session proves the DB cascade, including recipient rows that
            # have no meeting_id and are outside the merge's metadata table scan.
            async with client.app_state["sessionmaker"]() as db:
                for model, row_id in row_ids:
                    row = await db.get(model, row_id)
                    assert row is not None and row.workspace_id == PERSONAL_WORKSPACE_ID
                publication = await db.get(PublishedMeetingSummary, publication_id)
                assert publication.projection_json == document
                assert publication.owner_user_id == source.user_id
                assert (await db.get(Meeting, meeting_id)).created_by_user_id == USER_ID
                assert (
                    await db.get(SummaryDeliveryBatch, batch_id)
                ).owner_user_id == source.user_id
                assert (
                    await db.get(MeetingShareInvitation, invitation_id)
                ).token_hash == invitation_token_hash
                for row_id, original in original_grants.items():
                    row = await db.get(MeetingShareGrant, row_id)
                    assert (
                        row.share_token_hash,
                        row.share_token_ciphertext,
                        row.publication_version,
                    ) == original
                for row_id, original in original_recipients.items():
                    row = await db.get(SummaryRecipientDelivery, row_id)
                    assert (
                        row.state,
                        row.encrypted_address,
                        row.user_id,
                        row.invitation_id,
                        row.grant_id,
                        row.reserved_at,
                        row.completed_at,
                        row.attempt_count,
                        row.provider_message_id,
                    ) == original
                assert await db.get(Workspace, source.workspace_id) is None

            sender = AsyncMock()
            await deliver_summary_batch(
                sessions,
                settings=settings,
                workspace_id=PERSONAL_WORKSPACE_ID,
                batch_id=batch_id,
                mail_client=sender,
            )
            sender.send_summary_delivery.assert_not_awaited()

        async with client.app_state["sessionmaker"]() as db:
            for row_id, original in original_recipients.items():
                row = await db.get(SummaryRecipientDelivery, row_id)
                if original[0] == "pending":
                    assert row.state == "cancelled"
                    assert row.failure_code == "summary_owner_authority_lost"
                    assert row.attempt_count == 0
                    assert row.invitation_id is None
                else:
                    assert row.state == original[0]
                    assert row.attempt_count == original[7]
                    assert row.provider_message_id == original[8]

    client.portal.call(exercise)
