from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, text

from tests.fakes.auth_contexts import (
    DEVICE_ID,
    ORG_ID,
    USER_ID,
    WORKSPACE_ID,
    duplicate_account_fixture,
)
from twobrain_rec_server.auth.account_merge import (
    MergeEntityCounts,
    cancel_merge_intent,
    confirm_merge_intent,
    create_merge_intent,
    preview_merge_intent,
)
from twobrain_rec_server.auth.context import AuthenticatedPrincipal
from twobrain_rec_server.auth.provider_links import confirm_provider_link
from twobrain_rec_server.auth.sessions import issue_auth_session
from twobrain_rec_server.db.models import (
    AccountMergeIntent,
    AccountMergeJournal,
    AuthCallbackState,
    AuthSession,
    AuthSessionDeviceBinding,
    ExternalIdentity,
    Meeting,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
    WorkspaceProviderLinkState,
)

SOURCE_USER_ID = UUID("30000000-0000-0000-0000-000000000099")
SOURCE_WORKSPACE_ID = UUID("20000000-0000-0000-0000-000000000099")
MERGE_USER_REFERENCE_COLUMNS = {
    ("user_identities", "merged_into_user_id"),
    ("external_identities", "user_id"),
    ("workspace_memberships", "user_id"),
    ("meetings", "created_by_user_id"),
    ("workspaces", "owner_user_id"),
    ("registered_devices", "user_id"),
    ("auth_sessions", "user_id"),
    ("account_merge_intents", "survivor_user_id"),
    ("account_merge_intents", "source_user_id"),
    ("account_merge_journals", "survivor_user_id"),
    ("account_merge_journals", "source_user_id"),
}


async def _merge_foreign_key_inventory(db) -> set[tuple[str, str]]:
    rows = await db.execute(
        text(
            """
            select key_columns.table_name, key_columns.column_name
            from information_schema.key_column_usage key_columns
            join information_schema.constraint_column_usage referenced
              on referenced.constraint_name = key_columns.constraint_name
             and referenced.constraint_schema = key_columns.constraint_schema
            where key_columns.table_schema = 'public'
              and referenced.table_schema = 'public'
              and referenced.table_name = 'user_identities'
            """
        )
    )
    return {(row.table_name, row.column_name) for row in rows}


async def _lock_merge_users(db, *user_ids: UUID) -> list[UserIdentity]:
    return list(
        await db.scalars(
            select(UserIdentity)
            .where(UserIdentity.id.in_(user_ids))
            .order_by(UserIdentity.id)
            .with_for_update()
        )
    )


async def _seed_empty_source(db, *, user_id: UUID, workspace_id: UUID, email: str) -> None:
    db.add(
        UserIdentity(
            id=user_id,
            organization_id=ORG_ID,
            external_subject=f"oauth:{user_id}",
            display_name="Source",
        )
    )
    db.add(
        Workspace(
            id=workspace_id,
            organization_id=ORG_ID,
            owner_user_id=user_id,
            slug=f"source-{user_id}",
            name="Source workspace",
            kind="corporate",
        )
    )
    await db.flush()
    db.add_all(
        [
            WorkspaceMembership(
                workspace_id=workspace_id,
                user_id=user_id,
                role="owner",
                status="active",
            ),
            ExternalIdentity(
                user_id=user_id,
                provider="yandex",
                provider_subject=email,
                email=email,
                is_verified=True,
                is_active=True,
            ),
        ]
    )
    await db.flush()


def test_dataful_merge_preserves_meeting_id_and_workspace(client) -> None:
    meeting_id = uuid4()

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add_all(
                [
                    UserIdentity(
                        id=SOURCE_USER_ID,
                        organization_id=ORG_ID,
                        external_subject="oauth:source",
                        display_name="Source",
                    ),
                    Workspace(
                        id=SOURCE_WORKSPACE_ID,
                        organization_id=ORG_ID,
                        owner_user_id=SOURCE_USER_ID,
                        slug="source-workspace",
                        name="Source workspace",
                        kind="corporate",
                    ),
                ]
            )
            await db.flush()
            db.add_all(
                [
                    WorkspaceMembership(
                        workspace_id=SOURCE_WORKSPACE_ID,
                        user_id=SOURCE_USER_ID,
                        role="owner",
                        status="active",
                    ),
                    ExternalIdentity(
                        user_id=SOURCE_USER_ID,
                        provider="email",
                        provider_subject="merge-source@example.test",
                        email="merge-source@example.test",
                        is_verified=True,
                        is_active=True,
                    ),
                    Meeting(
                        id=meeting_id,
                        workspace_id=SOURCE_WORKSPACE_ID,
                        created_by_user_id=SOURCE_USER_ID,
                        device_id=UUID("40000000-0000-0000-0000-000000000001"),
                        local_recording_id="merge-meeting",
                        duration_seconds=1,
                    ),
                ]
            )
            await db.flush()
            assert await _merge_foreign_key_inventory(db) >= MERGE_USER_REFERENCE_COLUMNS
            assert len(await _lock_merge_users(db, USER_ID, SOURCE_USER_ID)) == 2
            await db.commit()
            intent, preview = await create_merge_intent(
                db,
                workspace_id=WORKSPACE_ID,
                survivor_user_id=USER_ID,
                source_user_id=SOURCE_USER_ID,
                email_proof_state="verified",
                oauth_proof_state="verified",
                actor_user_id=USER_ID,
            )
            assert preview.counts == MergeEntityCounts(meetings=1)
            result = await confirm_merge_intent(
                db,
                intent_id=intent.id,
                preview_fingerprint=preview.fingerprint,
                idempotency_key="merge-test-1",
            )
            assert result.status == "completed"
            await db.commit()

            source = await db.get(UserIdentity, SOURCE_USER_ID)
            meeting = await db.get(Meeting, meeting_id)
            membership = await db.get(
                WorkspaceMembership,
                {"workspace_id": SOURCE_WORKSPACE_ID, "user_id": USER_ID},
            )
            identity = await db.scalar(
                select(ExternalIdentity).where(
                    ExternalIdentity.provider_subject == "merge-source@example.test"
                )
            )
            journal = await db.scalar(
                select(AccountMergeJournal).where(AccountMergeJournal.merge_intent_id == intent.id)
            )
            assert source is not None and source.status == "merged"
            assert source.merged_into_user_id == USER_ID
            assert meeting is not None and meeting.id == meeting_id
            assert meeting.workspace_id == SOURCE_WORKSPACE_ID
            assert meeting.created_by_user_id == USER_ID
            assert membership is not None and membership.role == "owner"
            assert identity is not None and identity.user_id == USER_ID
            assert journal is not None and journal.status == "completed"

    client.portal.call(exercise)


def test_empty_duplicate_explicit_confirmation_and_retry_are_idempotent(client) -> None:
    source = duplicate_account_fixture(98, email="empty-source@example.test")
    source_user_id = source.user_id
    source_workspace_id = source.workspace_id

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source_user_id,
                workspace_id=source_workspace_id,
                email=source.email,
            )
            await db.commit()
            intent, preview = await create_merge_intent(
                db,
                workspace_id=WORKSPACE_ID,
                survivor_user_id=USER_ID,
                source_user_id=source_user_id,
                email_proof_state="verified",
                oauth_proof_state="verified",
                actor_user_id=USER_ID,
            )
            assert preview.counts == MergeEntityCounts()
            result = await confirm_merge_intent(
                db,
                intent_id=intent.id,
                preview_fingerprint=preview.fingerprint,
                idempotency_key="empty-merge-1",
            )
            await db.commit()
            retry = await confirm_merge_intent(
                db,
                intent_id=intent.id,
                preview_fingerprint=preview.fingerprint,
                idempotency_key="empty-merge-1",
            )
            assert result.status == retry.status == "completed"
            assert (await db.get(UserIdentity, source_user_id)).status == "merged"

    client.portal.call(exercise)


def test_merge_confirm_rejects_header_session_without_mutating_intent(client) -> None:
    source = duplicate_account_fixture(95, email="header-only-merge@example.test")

    async def seed() -> tuple[UUID, str, str]:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source.user_id,
                workspace_id=source.workspace_id,
                email=source.email,
            )
            issued = await issue_auth_session(
                db,
                user_id=USER_ID,
                workspace_id=WORKSPACE_ID,
                device_id=DEVICE_ID,
                provider="email",
            )
            db.add(
                AuthSessionDeviceBinding(
                    auth_session_id=issued.id,
                    registered_device_id=DEVICE_ID,
                    device_state="trusted",
                )
            )
            await db.commit()
            intent, preview = await create_merge_intent(
                db,
                workspace_id=WORKSPACE_ID,
                survivor_user_id=USER_ID,
                source_user_id=source.user_id,
                email_proof_state="verified",
                oauth_proof_state="verified",
            )
            await db.commit()
            return intent.id, issued.token, preview.fingerprint

    intent_id, token, fingerprint = client.portal.call(seed)
    client.cookies.clear()
    response = client.post(
        f"/settings/account/merge/{intent_id}/confirm",
        headers={"X-Auth-Session": token},
        data={"preview_fingerprint": fingerprint, "idempotency_key": "header-only-merge"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith("error=reauth_required")

    async def assert_unchanged() -> None:
        async with client.app_state["sessionmaker"]() as db:
            intent = await db.get(AccountMergeIntent, intent_id)
            source_user = await db.get(UserIdentity, source.user_id)
            assert intent is not None and intent.status == "preview_ready"
            assert source_user is not None and source_user.status == "active"

    client.portal.call(assert_unchanged)


def test_cancel_and_expiry_are_non_mutating_terminal_states(client) -> None:
    source_user_id = UUID("30000000-0000-0000-0000-000000000097")
    source_workspace_id = UUID("20000000-0000-0000-0000-000000000097")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source_user_id,
                workspace_id=source_workspace_id,
                email="terminal-source@example.test",
            )
            await db.commit()
            intent, preview = await create_merge_intent(
                db,
                workspace_id=WORKSPACE_ID,
                survivor_user_id=USER_ID,
                source_user_id=source_user_id,
                email_proof_state="verified",
                oauth_proof_state="verified",
                actor_user_id=USER_ID,
                now=datetime.now(UTC),
            )
            await cancel_merge_intent(db, intent_id=intent.id, actor_user_id=USER_ID)
            await db.commit()
            source = await db.get(UserIdentity, source_user_id)
            assert source is not None and source.status == "active"
            assert intent.status == "cancelled"

            expired, _ = await create_merge_intent(
                db,
                workspace_id=WORKSPACE_ID,
                survivor_user_id=USER_ID,
                source_user_id=source_user_id,
                email_proof_state="verified",
                oauth_proof_state="verified",
                actor_user_id=USER_ID,
                now=datetime.now(UTC),
                ttl_seconds=-1,
            )
            try:
                await preview_merge_intent(db, intent_id=expired.id)
            except ValueError as exc:
                assert str(exc) == "merge_intent_expired"
            else:
                raise AssertionError("expired merge intent was previewable")
            await db.rollback()

    client.portal.call(exercise)


def test_provider_link_email_session_requires_preview_for_empty_duplicate(client) -> None:
    source_user_id = UUID("30000000-0000-0000-0000-000000000096")
    source_workspace_id = UUID("20000000-0000-0000-0000-000000000096")
    session_id = UUID("50000000-0000-0000-0000-000000000096")
    callback_state_id = UUID("60000000-0000-0000-0000-000000000096")
    link_id = UUID("70000000-0000-0000-0000-000000000096")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source_user_id,
                workspace_id=source_workspace_id,
                email="oauth-duplicate@example.test",
            )
            email_identity = ExternalIdentity(
                user_id=USER_ID,
                provider="email",
                provider_subject="email-owner@example.test",
                email="email-owner@example.test",
                is_verified=True,
                is_active=True,
            )
            db.add(email_identity)
            await db.flush()
            session = AuthSession(
                id=session_id,
                user_id=USER_ID,
                workspace_id=WORKSPACE_ID,
                provider="email",
                session_token_hash="email-session-hash",
                status="active",
                expires_at=datetime.now(UTC) + timedelta(minutes=15),
            )
            callback_state = AuthCallbackState(
                id=callback_state_id,
                provider="yandex",
                workspace_id=WORKSPACE_ID,
                state_nonce="oauth-link-state",
                expected_state="oauth-link-state",
                result="completed",
                expires_at=datetime.now(UTC) + timedelta(minutes=15),
            )
            link = WorkspaceProviderLinkState(
                id=link_id,
                workspace_id=WORKSPACE_ID,
                initiating_user_id=USER_ID,
                initiating_auth_session_id=session_id,
                source_provider_identity_id=email_identity.id,
                callback_state_id=callback_state_id,
                candidate_provider="yandex",
                candidate_identity_subject="oauth-duplicate@example.test",
                status="callback_verified",
                expires_at=datetime.now(UTC) + timedelta(minutes=15),
            )
            db.add_all([session, callback_state, link])
            await db.commit()

            confirmed = await confirm_provider_link(
                db,
                principal=AuthenticatedPrincipal(
                    user_id=USER_ID,
                    organization_id=ORG_ID,
                    workspace_ids=frozenset({WORKSPACE_ID}),
                    subject=str(USER_ID),
                    session_id=session_id,
                    auth_via_session=True,
                    session_workspace_id=WORKSPACE_ID,
                ),
                link_state_id=link_id,
            )
            await db.commit()

            source = await db.get(UserIdentity, source_user_id)
            intent = await db.get(AccountMergeIntent, confirmed.merge_intent_id)
            assert confirmed.status == "merge_preview_ready"
            assert source is not None and source.status == "active"
            assert intent is not None and intent.status == "preview_ready"

    client.portal.call(exercise)
