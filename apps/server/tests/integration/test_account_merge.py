from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text

from tests.fakes.auth_contexts import (
    DEVICE_ID,
    ORG_ID,
    PERSONAL_WORKSPACE_ID,
    USER_ID,
    WORKSPACE_ID,
    duplicate_account_fixture,
)
from twobrain_rec_server.auth.account_merge import (
    AccountMergeError,
    MergeEntityCounts,
    cancel_merge_intent,
    confirm_merge_intent,
    create_merge_intent,
    preview_merge_intent,
)
from twobrain_rec_server.auth.context import AuthenticatedPrincipal
from twobrain_rec_server.auth.csrf import issue_csrf_token
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.provider_links import confirm_provider_link
from twobrain_rec_server.auth.sessions import issue_auth_session
from twobrain_rec_server.db.models import (
    AccountMergeIntent,
    AccountMergeJournal,
    AuthCallbackState,
    AuthSession,
    AuthSessionDeviceBinding,
    BillingNotificationPreference,
    CalendarSettingsPreference,
    ExportPackage,
    ExternalIdentity,
    FairUseReviewRecord,
    Meeting,
    MeetingShareGrant,
    RegisteredDevice,
    SummaryTemplate,
    UploadSession,
    UserIdentity,
    Workspace,
    WorkspaceInvitation,
    WorkspaceJoinOffer,
    WorkspaceMembership,
    WorkspaceProviderLinkState,
    WorkspaceSubscription,
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


async def _seed_empty_source(
    db,
    *,
    user_id: UUID,
    workspace_id: UUID,
    email: str,
    workspace_kind: str = "corporate",
    workspace_name: str = "Source workspace",
) -> None:
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
            name=workspace_name,
            kind=workspace_kind,
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


async def _seed_merge_proofs(db, *, source_user_id: UUID) -> dict[str, UUID]:
    now = datetime.now(UTC)
    source_identity = await db.scalar(
        select(ExternalIdentity).where(
            ExternalIdentity.user_id == source_user_id,
            ExternalIdentity.is_active.is_(True),
            ExternalIdentity.is_verified.is_(True),
        )
    )
    assert source_identity is not None
    session = AuthSession(
        id=uuid4(),
        user_id=USER_ID,
        workspace_id=WORKSPACE_ID,
        provider="email",
        session_token_hash=f"merge-proof-{uuid4()}",
        status="active",
        expires_at=now + timedelta(minutes=15),
    )
    callback = AuthCallbackState(
        id=uuid4(),
        provider="email_link",
        workspace_id=WORKSPACE_ID,
        state_nonce=f"merge-proof-{uuid4()}",
        expected_state="consumed",
        result="completed",
        used_at=now,
        expires_at=now + timedelta(minutes=15),
    )
    db.add_all([session, callback])
    await db.flush()
    return {
        "initiating_auth_session_id": session.id,
        "source_external_identity_id": source_identity.id,
        "proof_callback_state_id": callback.id,
    }


async def _create_ready_merge(db, *, source_user_id: UUID):
    proofs = await _seed_merge_proofs(db, source_user_id=source_user_id)
    return await create_merge_intent(
        db,
        workspace_id=WORKSPACE_ID,
        survivor_user_id=USER_ID,
        source_user_id=source_user_id,
        **proofs,
        email_proof_state="verified",
        oauth_proof_state="verified",
        actor_user_id=USER_ID,
    )


async def _seed_source_meeting(
    db,
    *,
    source_user_id: UUID,
    source_workspace_id: UUID,
    suffix: str,
) -> Meeting:
    meeting = Meeting(
        id=uuid4(),
        workspace_id=source_workspace_id,
        created_by_user_id=source_user_id,
        device_id=DEVICE_ID,
        local_recording_id=f"merge-domain-{suffix}",
        duration_seconds=1,
    )
    db.add(meeting)
    await db.flush()
    return meeting


def test_personal_profiles_merge_without_combining_workspaces(client) -> None:
    source = duplicate_account_fixture(94, email="personal-source@example.test")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            primary = await db.get(Workspace, PERSONAL_WORKSPACE_ID)
            assert primary is not None
            await _seed_empty_source(
                db,
                user_id=source.user_id,
                workspace_id=source.workspace_id,
                email=source.email,
                workspace_kind="personal",
                workspace_name="Моё пространство",
            )
            await db.commit()
            proofs = await _seed_merge_proofs(db, source_user_id=source.user_id)
            intent, preview = await create_merge_intent(
                db,
                workspace_id=WORKSPACE_ID,
                survivor_user_id=USER_ID,
                source_user_id=source.user_id,
                **proofs,
                email_proof_state="verified",
                oauth_proof_state="verified",
                actor_user_id=USER_ID,
            )

            assert preview.blocker_codes == ()
            result = await confirm_merge_intent(
                db,
                intent_id=intent.id,
                preview_fingerprint=preview.fingerprint,
                idempotency_key="personal-merge",
            )
            await db.commit()

            primary_workspace = await db.get(Workspace, PERSONAL_WORKSPACE_ID)
            linked_workspace = await db.get(Workspace, source.workspace_id)
            assert result.status == "completed"
            assert primary_workspace is not None
            assert primary_workspace.kind == "personal"
            assert primary_workspace.owner_user_id == USER_ID
            assert linked_workspace is not None
            assert linked_workspace.kind == "linked"
            assert linked_workspace.owner_user_id == USER_ID
            assert linked_workspace.name == "Пространство из другого профиля"

    client.portal.call(exercise)


def test_personal_merge_preserves_custom_workspace_name(client) -> None:
    source = duplicate_account_fixture(93, email="named-source@example.test")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            primary = await db.get(Workspace, PERSONAL_WORKSPACE_ID)
            assert primary is not None
            await _seed_empty_source(
                db,
                user_id=source.user_id,
                workspace_id=source.workspace_id,
                email=source.email,
                workspace_kind="personal",
                workspace_name="Проект Альфа",
            )
            await db.commit()
            proofs = await _seed_merge_proofs(db, source_user_id=source.user_id)
            intent, preview = await create_merge_intent(
                db,
                workspace_id=WORKSPACE_ID,
                survivor_user_id=USER_ID,
                source_user_id=source.user_id,
                **proofs,
                email_proof_state="verified",
                oauth_proof_state="verified",
                actor_user_id=USER_ID,
            )
            await confirm_merge_intent(
                db,
                intent_id=intent.id,
                preview_fingerprint=preview.fingerprint,
                idempotency_key="named-personal-merge",
            )
            await db.commit()

            linked_workspace = await db.get(Workspace, source.workspace_id)
            assert linked_workspace is not None
            assert linked_workspace.kind == "linked"
            assert linked_workspace.name == "Проект Альфа"

    client.portal.call(exercise)


@pytest.mark.parametrize(
    ("slot", "broken_proof"),
    [(90, "session"), (91, "identity"), (92, "callback")],
)
def test_merge_rechecks_exact_proof_records(client, slot: int, broken_proof: str) -> None:
    source = duplicate_account_fixture(slot, email=f"proof-{slot}@example.test")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source.user_id,
                workspace_id=source.workspace_id,
                email=source.email,
            )
            await db.commit()
            proofs = await _seed_merge_proofs(db, source_user_id=source.user_id)
            intent, preview = await create_merge_intent(
                db,
                workspace_id=WORKSPACE_ID,
                survivor_user_id=USER_ID,
                source_user_id=source.user_id,
                **proofs,
                email_proof_state="verified",
                oauth_proof_state="verified",
            )
            if broken_proof == "session":
                (await db.get(AuthSession, proofs["initiating_auth_session_id"])).status = "revoked"
            elif broken_proof == "identity":
                (
                    await db.get(ExternalIdentity, proofs["source_external_identity_id"])
                ).is_active = False
            else:
                (
                    await db.get(AuthCallbackState, proofs["proof_callback_state_id"])
                ).result = "failed"
            await db.flush()

            with pytest.raises(AccountMergeError, match="proof_required"):
                await confirm_merge_intent(
                    db,
                    intent_id=intent.id,
                    preview_fingerprint=preview.fingerprint,
                    idempotency_key=f"broken-{broken_proof}",
                )
            assert (await db.get(UserIdentity, source.user_id)).status == "active"
            assert (await db.get(Workspace, source.workspace_id)).owner_user_id == source.user_id

    client.portal.call(exercise)


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
            proofs = await _seed_merge_proofs(db, source_user_id=SOURCE_USER_ID)
            intent, preview = await create_merge_intent(
                db,
                workspace_id=WORKSPACE_ID,
                survivor_user_id=USER_ID,
                source_user_id=SOURCE_USER_ID,
                **proofs,
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
            proofs = await _seed_merge_proofs(db, source_user_id=source_user_id)
            intent, preview = await create_merge_intent(
                db,
                workspace_id=WORKSPACE_ID,
                survivor_user_id=USER_ID,
                source_user_id=source_user_id,
                **proofs,
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
            with pytest.raises(AccountMergeError, match="merge_idempotency_conflict"):
                await confirm_merge_intent(
                    db,
                    intent_id=intent.id,
                    preview_fingerprint=preview.fingerprint,
                    idempotency_key="different-key",
                )

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
            proofs = await _seed_merge_proofs(db, source_user_id=source.user_id)
            intent, preview = await create_merge_intent(
                db,
                workspace_id=WORKSPACE_ID,
                survivor_user_id=USER_ID,
                source_user_id=source.user_id,
                **proofs,
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


def test_merge_routes_reject_a_different_session_of_the_same_user(client) -> None:
    source = duplicate_account_fixture(96, email="second-session-merge@example.test")

    async def seed() -> tuple[UUID, str, UUID, str]:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source.user_id,
                workspace_id=source.workspace_id,
                email=source.email,
            )
            intent, preview = await _create_ready_merge(db, source_user_id=source.user_id)
            other_session = await issue_auth_session(
                db,
                user_id=USER_ID,
                workspace_id=WORKSPACE_ID,
                device_id=DEVICE_ID,
                provider="email",
            )
            db.add(
                AuthSessionDeviceBinding(
                    auth_session_id=other_session.id,
                    registered_device_id=DEVICE_ID,
                    device_state="trusted",
                )
            )
            await db.commit()
            return intent.id, other_session.token, other_session.id, preview.fingerprint

    intent_id, token, session_id, fingerprint = client.portal.call(seed)
    client.cookies.clear()
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, token)
    headers = {
        "X-CSRF-Token": issue_csrf_token(
            session_id=session_id,
            secret=str(client.app.state.web_csrf_secret),
        )
    }

    assert client.get(f"/settings/account/merge/{intent_id}").status_code == 404
    assert (
        client.post(
            f"/settings/account/merge/{intent_id}/confirm",
            headers=headers,
            data={
                "preview_fingerprint": fingerprint,
                "idempotency_key": "wrong-session-confirm",
            },
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/settings/account/merge/{intent_id}/cancel",
            headers=headers,
        ).status_code
        == 404
    )

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
            proofs = await _seed_merge_proofs(db, source_user_id=source_user_id)
            intent, preview = await create_merge_intent(
                db,
                workspace_id=WORKSPACE_ID,
                survivor_user_id=USER_ID,
                source_user_id=source_user_id,
                **proofs,
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

            proofs = await _seed_merge_proofs(db, source_user_id=source_user_id)
            expired, _ = await create_merge_intent(
                db,
                workspace_id=WORKSPACE_ID,
                survivor_user_id=USER_ID,
                source_user_id=source_user_id,
                **proofs,
                email_proof_state="verified",
                oauth_proof_state="verified",
                actor_user_id=USER_ID,
                now=datetime.now(UTC),
                ttl_seconds=-1,
            )
            with pytest.raises(AccountMergeError, match="merge_intent_expired"):
                await confirm_merge_intent(
                    db,
                    intent_id=expired.id,
                    preview_fingerprint=preview.fingerprint,
                    idempotency_key="expired-merge",
                )
            assert (await db.get(UserIdentity, source_user_id)).status == "active"
            assert (await db.get(Workspace, source_workspace_id)).owner_user_id == source_user_id
            await db.commit()

    client.portal.call(exercise)


def test_fresh_proof_replaces_an_abandoned_expired_intent(client) -> None:
    source_user_id = UUID("30000000-0000-0000-0000-000000000091")
    source_workspace_id = UUID("20000000-0000-0000-0000-000000000091")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source_user_id,
                workspace_id=source_workspace_id,
                email="fresh-after-expiry@example.test",
            )
            await db.commit()
            expired_proofs = await _seed_merge_proofs(db, source_user_id=source_user_id)
            expired, _ = await create_merge_intent(
                db,
                workspace_id=WORKSPACE_ID,
                survivor_user_id=USER_ID,
                source_user_id=source_user_id,
                **expired_proofs,
                email_proof_state="verified",
                oauth_proof_state="verified",
                actor_user_id=USER_ID,
                now=datetime.now(UTC) - timedelta(minutes=2),
                ttl_seconds=1,
            )
            await db.commit()

            fresh_proofs = await _seed_merge_proofs(db, source_user_id=source_user_id)
            fresh, preview = await create_merge_intent(
                db,
                workspace_id=WORKSPACE_ID,
                survivor_user_id=USER_ID,
                source_user_id=source_user_id,
                **fresh_proofs,
                email_proof_state="verified",
                oauth_proof_state="verified",
                actor_user_id=USER_ID,
                now=datetime.now(UTC),
            )

            assert fresh.id != expired.id
            assert fresh.status == "preview_ready"
            assert not preview.blocker_codes
            assert (await db.get(AccountMergeIntent, expired.id)).status == "expired"

    client.portal.call(exercise)


def test_merge_transfers_safe_free_billing_owner_with_personal_workspace(client) -> None:
    source_user_id = UUID("30000000-0000-0000-0000-000000000094")
    source_workspace_id = UUID("20000000-0000-0000-0000-000000000094")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source_user_id,
                workspace_id=source_workspace_id,
                email="free-billing-owner@example.test",
                workspace_kind="personal",
            )
            db.add(
                WorkspaceSubscription(
                    workspace_id=source_workspace_id,
                    billing_owner_id=source_user_id,
                    state="free",
                    plan_code="free",
                    cycle="none",
                    recurring_allowed=False,
                )
            )
            await db.commit()
            proofs = await _seed_merge_proofs(db, source_user_id=source_user_id)
            intent, preview = await create_merge_intent(
                db,
                workspace_id=WORKSPACE_ID,
                survivor_user_id=USER_ID,
                source_user_id=source_user_id,
                **proofs,
                email_proof_state="verified",
                oauth_proof_state="verified",
                actor_user_id=USER_ID,
            )
            assert preview.blocker_codes == ()
            await confirm_merge_intent(
                db,
                intent_id=intent.id,
                preview_fingerprint=preview.fingerprint,
                idempotency_key="free-billing-owner-transfer",
            )
            await db.commit()

            subscription = await db.get(WorkspaceSubscription, source_workspace_id)
            assert subscription is not None
            assert subscription.billing_owner_id == USER_ID

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


def test_merge_combines_notification_and_calendar_preferences(client) -> None:
    source = duplicate_account_fixture(80, email="preferences-source@example.test")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source.user_id,
                workspace_id=source.workspace_id,
                email=source.email,
            )
            source_calendar_id = uuid4()
            duplicate_calendar_id = uuid4()
            survivor_calendar_id = uuid4()
            db.add_all(
                [
                    BillingNotificationPreference(
                        user_id=USER_ID,
                        optional_email_enabled=True,
                        optional_in_app_enabled=False,
                    ),
                    BillingNotificationPreference(
                        user_id=source.user_id,
                        optional_email_enabled=False,
                        optional_in_app_enabled=True,
                    ),
                    CalendarSettingsPreference(
                        id=source_calendar_id,
                        workspace_id=source.workspace_id,
                        owner_user_id=source.user_id,
                        join_prompt_enabled=False,
                        record_prompt_enabled=True,
                    ),
                    CalendarSettingsPreference(
                        id=survivor_calendar_id,
                        workspace_id=WORKSPACE_ID,
                        owner_user_id=USER_ID,
                        show_upcoming_title=True,
                    ),
                    CalendarSettingsPreference(
                        id=duplicate_calendar_id,
                        workspace_id=WORKSPACE_ID,
                        owner_user_id=source.user_id,
                        show_upcoming_title=False,
                    ),
                ]
            )
            await db.commit()

            intent, preview = await _create_ready_merge(db, source_user_id=source.user_id)
            assert preview.blocker_codes == ()
            await confirm_merge_intent(
                db,
                intent_id=intent.id,
                preview_fingerprint=preview.fingerprint,
                idempotency_key="preferences-merge",
            )
            await db.commit()

            survivor_preference = await db.get(BillingNotificationPreference, USER_ID)
            assert survivor_preference is not None
            assert survivor_preference.optional_email_enabled is False
            assert survivor_preference.optional_in_app_enabled is False
            assert await db.get(BillingNotificationPreference, source.user_id) is None

            transferred = await db.get(CalendarSettingsPreference, source_calendar_id)
            survivor_calendar = await db.get(CalendarSettingsPreference, survivor_calendar_id)
            assert transferred is not None
            assert transferred.owner_user_id == USER_ID
            assert transferred.join_prompt_enabled is False
            assert transferred.record_prompt_enabled is True
            assert survivor_calendar is not None
            assert survivor_calendar.show_upcoming_title is True
            assert await db.get(CalendarSettingsPreference, duplicate_calendar_id) is None

    client.portal.call(exercise)


def test_merge_transfers_only_active_summary_templates(client) -> None:
    source = duplicate_account_fixture(81, email="templates-source@example.test")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source.user_id,
                workspace_id=source.workspace_id,
                email=source.email,
            )
            active_id = uuid4()
            archived_id = uuid4()
            db.add_all(
                [
                    SummaryTemplate(
                        id=active_id,
                        workspace_id=source.workspace_id,
                        owner_user_id=source.user_id,
                        template_key="source-active-v1",
                        kind="custom",
                        name="Active",
                        purpose="Integration test",
                        sections_json=[],
                        output_language="ru-RU",
                        detail_level="standard",
                        status="active",
                    ),
                    SummaryTemplate(
                        id=archived_id,
                        workspace_id=source.workspace_id,
                        owner_user_id=source.user_id,
                        template_key="source-archived-v1",
                        kind="custom",
                        name="Archived",
                        purpose="Integration test",
                        sections_json=[],
                        output_language="ru-RU",
                        detail_level="standard",
                        status="archived",
                    ),
                ]
            )
            await db.commit()

            intent, preview = await _create_ready_merge(db, source_user_id=source.user_id)
            assert preview.blocker_codes == ()
            await confirm_merge_intent(
                db,
                intent_id=intent.id,
                preview_fingerprint=preview.fingerprint,
                idempotency_key="template-transfer",
            )
            await db.commit()

            active = await db.get(SummaryTemplate, active_id)
            archived = await db.get(SummaryTemplate, archived_id)
            assert active is not None and active.owner_user_id == USER_ID
            assert archived is not None and archived.owner_user_id == source.user_id

    client.portal.call(exercise)


@pytest.mark.parametrize("survivor_status", ("active", "archived"))
def test_summary_template_collision_rejects_merge_without_partial_writes(
    client,
    survivor_status: str,
) -> None:
    source = duplicate_account_fixture(82, email="template-collision@example.test")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source.user_id,
                workspace_id=source.workspace_id,
                email=source.email,
            )
            source_template_id = uuid4()
            db.add_all(
                [
                    SummaryTemplate(
                        id=source_template_id,
                        workspace_id=source.workspace_id,
                        owner_user_id=source.user_id,
                        template_key="collision-v1",
                        kind="custom",
                        name="Source",
                        purpose="Integration test",
                        sections_json=[],
                        output_language="ru-RU",
                        detail_level="standard",
                        status="active",
                    ),
                    SummaryTemplate(
                        workspace_id=source.workspace_id,
                        owner_user_id=USER_ID,
                        template_key="collision-v1",
                        kind="custom",
                        name="Survivor",
                        purpose="Integration test",
                        sections_json=[],
                        output_language="ru-RU",
                        detail_level="standard",
                        status=survivor_status,
                    ),
                ]
            )
            await db.commit()

            intent, preview = await _create_ready_merge(db, source_user_id=source.user_id)
            assert preview.blocker_codes == ("settings_conflict",)
            with pytest.raises(AccountMergeError, match="blocked"):
                await confirm_merge_intent(
                    db,
                    intent_id=intent.id,
                    preview_fingerprint=preview.fingerprint,
                    idempotency_key="template-collision",
                )
            await db.rollback()

            source_user = await db.get(UserIdentity, source.user_id)
            source_workspace = await db.get(Workspace, source.workspace_id)
            source_template = await db.get(SummaryTemplate, source_template_id)
            assert source_user is not None and source_user.status == "active"
            assert source_workspace is not None
            assert source_workspace.owner_user_id == source.user_id
            assert source_template is not None
            assert source_template.owner_user_id == source.user_id

    client.portal.call(exercise)


def test_in_progress_upload_and_requested_export_block_merge(client) -> None:
    source = duplicate_account_fixture(83, email="active-work-source@example.test")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source.user_id,
                workspace_id=source.workspace_id,
                email=source.email,
            )
            meeting = await _seed_source_meeting(
                db,
                source_user_id=source.user_id,
                source_workspace_id=source.workspace_id,
                suffix="active-work",
            )
            upload_id = uuid4()
            export_id = uuid4()
            db.add_all(
                [
                    UploadSession(
                        id=upload_id,
                        meeting_id=meeting.id,
                        workspace_id=source.workspace_id,
                        device_id=DEVICE_ID,
                        created_by_user_id=source.user_id,
                        status="uploading",
                        processing_status="not_submitted",
                        max_package_bytes_snapshot=1024,
                        max_track_bytes_snapshot=1024,
                        expires_at=datetime.now(UTC) + timedelta(hours=1),
                    ),
                    ExportPackage(
                        id=export_id,
                        workspace_id=source.workspace_id,
                        meeting_id=meeting.id,
                        requested_by_user_id=source.user_id,
                        status="requested",
                    ),
                ]
            )
            await db.commit()

            intent, preview = await _create_ready_merge(db, source_user_id=source.user_id)
            assert set(preview.blocker_codes) == {
                "export_in_progress",
                "upload_in_progress",
            }
            with pytest.raises(AccountMergeError, match="blocked"):
                await confirm_merge_intent(
                    db,
                    intent_id=intent.id,
                    preview_fingerprint=preview.fingerprint,
                    idempotency_key="active-work-block",
                )
            await db.rollback()

            upload = await db.get(UploadSession, upload_id)
            export = await db.get(ExportPackage, export_id)
            assert upload is not None and upload.created_by_user_id == source.user_id
            assert export is not None and export.requested_by_user_id == source.user_id
            assert (await db.get(UserIdentity, source.user_id)).status == "active"

    client.portal.call(exercise)


def test_active_source_fair_use_review_blocks_merge_until_resolved(client) -> None:
    source = duplicate_account_fixture(90, email="fair-use-source@example.test")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source.user_id,
                workspace_id=source.workspace_id,
                email=source.email,
            )
            now = datetime.now(UTC)
            review = FairUseReviewRecord(
                workspace_id=source.workspace_id,
                subject_user_id=source.user_id,
                capability="server_processing",
                reason_code="resale",
                evidence_ref="fu-merge-lineage-90",
                starts_at=now,
                review_by=now + timedelta(hours=24),
                state="restricted",
            )
            db.add(review)
            await db.commit()
            review_id = review.id

            blocked_intent, blocked_preview = await _create_ready_merge(
                db, source_user_id=source.user_id
            )
            assert blocked_preview.blocker_codes == ("fair_use_conflict",)
            blocked_intent_id = blocked_intent.id
            await db.commit()
            with pytest.raises(AccountMergeError, match="blocked"):
                await confirm_merge_intent(
                    db,
                    intent_id=blocked_intent.id,
                    preview_fingerprint=blocked_preview.fingerprint,
                    idempotency_key="fair-use-blocked",
                )
            await db.rollback()

            review = await db.get(FairUseReviewRecord, review_id)
            assert review is not None
            review.state = "cleared"
            await db.commit()
            with pytest.raises(AccountMergeError, match="merge_blocked"):
                await preview_merge_intent(db, intent_id=blocked_intent_id)
            ready_intent, ready_preview = await _create_ready_merge(
                db, source_user_id=source.user_id
            )
            assert ready_intent.status == "preview_ready"
            assert "fair_use_conflict" not in ready_preview.blocker_codes
            review.state = "confirmed"
            await db.commit()
            confirmed_preview = await preview_merge_intent(db, intent_id=ready_intent.id)
            assert "fair_use_conflict" not in confirmed_preview.blocker_codes

    client.portal.call(exercise)


def test_terminal_upload_and_ready_export_remain_historical(client) -> None:
    source = duplicate_account_fixture(84, email="terminal-work-source@example.test")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source.user_id,
                workspace_id=source.workspace_id,
                email=source.email,
            )
            meeting = await _seed_source_meeting(
                db,
                source_user_id=source.user_id,
                source_workspace_id=source.workspace_id,
                suffix="terminal-work",
            )
            upload_id = uuid4()
            export_id = uuid4()
            db.add_all(
                [
                    UploadSession(
                        id=upload_id,
                        meeting_id=meeting.id,
                        workspace_id=source.workspace_id,
                        device_id=DEVICE_ID,
                        created_by_user_id=source.user_id,
                        status="completed",
                        processing_status="completed",
                        max_package_bytes_snapshot=1024,
                        max_track_bytes_snapshot=1024,
                        expires_at=datetime.now(UTC) - timedelta(hours=1),
                        finalized_at=datetime.now(UTC) - timedelta(hours=2),
                    ),
                    ExportPackage(
                        id=export_id,
                        workspace_id=source.workspace_id,
                        meeting_id=meeting.id,
                        requested_by_user_id=source.user_id,
                        status="ready",
                        ready_at=datetime.now(UTC) - timedelta(minutes=5),
                    ),
                ]
            )
            await db.commit()

            intent, preview = await _create_ready_merge(db, source_user_id=source.user_id)
            assert preview.blocker_codes == ()
            await confirm_merge_intent(
                db,
                intent_id=intent.id,
                preview_fingerprint=preview.fingerprint,
                idempotency_key="terminal-work-history",
            )
            await db.commit()

            upload = await db.get(UploadSession, upload_id)
            export = await db.get(ExportPackage, export_id)
            merged_meeting = await db.get(Meeting, meeting.id)
            assert merged_meeting is not None
            await db.refresh(merged_meeting)
            assert upload is not None and upload.created_by_user_id == source.user_id
            assert export is not None and export.requested_by_user_id == source.user_id
            assert merged_meeting.created_by_user_id == USER_ID

    client.portal.call(exercise)


def test_merge_applies_active_and_inactive_membership_matrix(client) -> None:
    source = duplicate_account_fixture(85, email="memberships-source@example.test")
    access_owner_id = UUID("30000000-0000-0000-0000-000000000185")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source.user_id,
                workspace_id=source.workspace_id,
                email=source.email,
            )
            db.add(
                UserIdentity(
                    id=access_owner_id,
                    organization_id=ORG_ID,
                    external_subject="oauth:membership-owner",
                    display_name="Membership owner",
                )
            )
            workspaces = [
                Workspace(
                    id=uuid4(),
                    organization_id=ORG_ID,
                    owner_user_id=access_owner_id,
                    slug=f"merge-membership-{index}",
                    name=f"Membership {index}",
                    kind="corporate",
                )
                for index in range(3)
            ]
            db.add_all(workspaces)
            await db.flush()
            db.add_all(
                [
                    *(
                        WorkspaceMembership(
                            workspace_id=workspace.id,
                            user_id=access_owner_id,
                            role="owner",
                            status="active",
                        )
                        for workspace in workspaces
                    ),
                    WorkspaceMembership(
                        workspace_id=workspaces[0].id,
                        user_id=source.user_id,
                        role="member",
                        status="active",
                    ),
                    WorkspaceMembership(
                        workspace_id=workspaces[1].id,
                        user_id=source.user_id,
                        role="member",
                        status="active",
                    ),
                    WorkspaceMembership(
                        workspace_id=workspaces[1].id,
                        user_id=USER_ID,
                        role="viewer",
                        status="inactive",
                    ),
                    WorkspaceMembership(
                        workspace_id=workspaces[2].id,
                        user_id=source.user_id,
                        role="member",
                        status="inactive",
                    ),
                    WorkspaceMembership(
                        workspace_id=workspaces[2].id,
                        user_id=USER_ID,
                        role="viewer",
                        status="active",
                    ),
                ]
            )
            await db.commit()

            intent, preview = await _create_ready_merge(db, source_user_id=source.user_id)
            assert preview.blocker_codes == ()
            await confirm_merge_intent(
                db,
                intent_id=intent.id,
                preview_fingerprint=preview.fingerprint,
                idempotency_key="membership-matrix",
            )
            await db.commit()

            transferred = await db.get(
                WorkspaceMembership,
                {"workspace_id": workspaces[0].id, "user_id": USER_ID},
            )
            reactivated = await db.get(
                WorkspaceMembership,
                {"workspace_id": workspaces[1].id, "user_id": USER_ID},
            )
            inactive_source = await db.get(
                WorkspaceMembership,
                {"workspace_id": workspaces[2].id, "user_id": source.user_id},
            )
            active_survivor = await db.get(
                WorkspaceMembership,
                {"workspace_id": workspaces[2].id, "user_id": USER_ID},
            )
            assert transferred is not None
            assert (transferred.role, transferred.status) == ("member", "active")
            assert reactivated is not None
            assert (reactivated.role, reactivated.status) == ("member", "active")
            assert inactive_source is not None and inactive_source.status == "inactive"
            assert active_survivor is not None
            assert (active_survivor.role, active_survivor.status) == ("viewer", "active")

    client.portal.call(exercise)


def test_merge_transfers_active_and_preserves_expired_join_offers(client) -> None:
    source = duplicate_account_fixture(86, email="offers-source@example.test")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source.user_id,
                workspace_id=source.workspace_id,
                email=source.email,
            )
            now = datetime.now(UTC)
            active_invitation = WorkspaceInvitation(
                workspace_id=WORKSPACE_ID,
                target_contact="active-offer@example.test",
                invited_role="member",
                status="pending",
                created_by_user_id=USER_ID,
                expires_at=now + timedelta(days=1),
            )
            expired_invitation = WorkspaceInvitation(
                workspace_id=WORKSPACE_ID,
                target_contact="expired-offer@example.test",
                invited_role="viewer",
                status="expired",
                created_by_user_id=USER_ID,
                expires_at=now - timedelta(days=1),
            )
            db.add_all([active_invitation, expired_invitation])
            await db.flush()
            active_offer_id = uuid4()
            expired_offer_id = uuid4()
            db.add_all(
                [
                    WorkspaceJoinOffer(
                        id=active_offer_id,
                        workspace_id=WORKSPACE_ID,
                        user_id=source.user_id,
                        invitation_id=active_invitation.id,
                        workspace_name="Main",
                        invited_role="member",
                        status="offered",
                        expires_at=now + timedelta(days=1),
                    ),
                    WorkspaceJoinOffer(
                        id=expired_offer_id,
                        workspace_id=WORKSPACE_ID,
                        user_id=source.user_id,
                        invitation_id=expired_invitation.id,
                        workspace_name="Main",
                        invited_role="viewer",
                        status="offered",
                        expires_at=now - timedelta(days=1),
                    ),
                ]
            )
            await db.commit()

            intent, preview = await _create_ready_merge(db, source_user_id=source.user_id)
            assert preview.blocker_codes == ()
            await confirm_merge_intent(
                db,
                intent_id=intent.id,
                preview_fingerprint=preview.fingerprint,
                idempotency_key="join-offer-matrix",
            )
            await db.commit()

            active_offer = await db.get(WorkspaceJoinOffer, active_offer_id)
            expired_offer = await db.get(WorkspaceJoinOffer, expired_offer_id)
            assert active_offer is not None and active_offer.user_id == USER_ID
            assert active_offer.status == "offered"
            assert expired_offer is not None and expired_offer.user_id == source.user_id
            assert expired_offer.status == "offered"

    client.portal.call(exercise)


def test_merge_transfers_deduplicates_and_preserves_expired_share_grants(client) -> None:
    source = duplicate_account_fixture(87, email="grants-source@example.test")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source.user_id,
                workspace_id=source.workspace_id,
                email=source.email,
            )
            meetings = [
                await _seed_source_meeting(
                    db,
                    source_user_id=source.user_id,
                    source_workspace_id=source.workspace_id,
                    suffix=f"grant-{index}",
                )
                for index in range(3)
            ]
            now = datetime.now(UTC)
            transfer_id = uuid4()
            duplicate_source_id = uuid4()
            duplicate_survivor_id = uuid4()
            expired_id = uuid4()

            def grant(
                *, grant_id: UUID, meeting: Meeting, user_id: UUID, expires_at=None
            ) -> MeetingShareGrant:
                return MeetingShareGrant(
                    id=grant_id,
                    workspace_id=source.workspace_id,
                    meeting_id=meeting.id,
                    grant_type="user",
                    grantee_user_id=user_id,
                    created_by_user_id=USER_ID,
                    status="active",
                    audience_type="user",
                    audience_id=user_id,
                    expires_at=expires_at,
                )

            db.add_all(
                [
                    grant(
                        grant_id=transfer_id,
                        meeting=meetings[0],
                        user_id=source.user_id,
                    ),
                    grant(
                        grant_id=duplicate_source_id,
                        meeting=meetings[1],
                        user_id=source.user_id,
                    ),
                    grant(
                        grant_id=duplicate_survivor_id,
                        meeting=meetings[1],
                        user_id=USER_ID,
                    ),
                    grant(
                        grant_id=expired_id,
                        meeting=meetings[2],
                        user_id=source.user_id,
                        expires_at=now - timedelta(minutes=1),
                    ),
                ]
            )
            await db.commit()

            intent, preview = await _create_ready_merge(db, source_user_id=source.user_id)
            assert preview.blocker_codes == ()
            await confirm_merge_intent(
                db,
                intent_id=intent.id,
                preview_fingerprint=preview.fingerprint,
                idempotency_key="share-grant-matrix",
            )
            await db.commit()

            transferred = await db.get(MeetingShareGrant, transfer_id)
            duplicate_source = await db.get(MeetingShareGrant, duplicate_source_id)
            duplicate_survivor = await db.get(MeetingShareGrant, duplicate_survivor_id)
            expired = await db.get(MeetingShareGrant, expired_id)
            assert transferred is not None
            assert transferred.grantee_user_id == transferred.audience_id == USER_ID
            assert transferred.status == "active"
            assert duplicate_source is not None and duplicate_source.status == "revoked"
            assert duplicate_source.grantee_user_id == source.user_id
            assert duplicate_survivor is not None and duplicate_survivor.status == "active"
            assert expired is not None and expired.grantee_user_id == source.user_id
            assert expired.status == "active"

    client.portal.call(exercise)


def test_merge_preserves_terminal_device_and_session_actors(client) -> None:
    source = duplicate_account_fixture(88, email="history-source@example.test")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source.user_id,
                workspace_id=source.workspace_id,
                email=source.email,
            )
            device_id = uuid4()
            session_id = uuid4()
            db.add(
                RegisteredDevice(
                    id=device_id,
                    workspace_id=source.workspace_id,
                    user_id=source.user_id,
                    device_public_id="historical-merge-device",
                    status="revoked",
                    registration_state="revoked",
                    trusted_by=source.user_id,
                    revoked_by=source.user_id,
                )
            )
            await db.flush()
            db.add(
                AuthSession(
                    id=session_id,
                    user_id=source.user_id,
                    workspace_id=source.workspace_id,
                    device_id=device_id,
                    provider="email",
                    session_token_hash="historical-merge-session",
                    status="revoked",
                    expires_at=datetime.now(UTC) - timedelta(days=1),
                )
            )
            await db.commit()

            intent, preview = await _create_ready_merge(db, source_user_id=source.user_id)
            assert preview.blocker_codes == ()
            await confirm_merge_intent(
                db,
                intent_id=intent.id,
                preview_fingerprint=preview.fingerprint,
                idempotency_key="history-actors",
            )
            await db.commit()

            device = await db.get(RegisteredDevice, device_id)
            session = await db.get(AuthSession, session_id)
            assert device is not None
            assert device.user_id == source.user_id
            assert device.trusted_by == source.user_id
            assert device.revoked_by == source.user_id
            assert (device.status, device.registration_state) == ("revoked", "revoked")
            assert session is not None
            assert session.user_id == source.user_id
            assert session.status == "revoked"

    client.portal.call(exercise)


def test_merge_rejects_stale_fingerprint_after_domain_state_changes(client) -> None:
    source = duplicate_account_fixture(89, email="stale-domain-source@example.test")

    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db,
                user_id=source.user_id,
                workspace_id=source.workspace_id,
                email=source.email,
            )
            await db.commit()

            intent, preview = await _create_ready_merge(db, source_user_id=source.user_id)
            await db.commit()
            db.add(
                BillingNotificationPreference(
                    user_id=source.user_id,
                    optional_email_enabled=False,
                    optional_in_app_enabled=True,
                )
            )
            await db.commit()

            with pytest.raises(AccountMergeError, match="merge_preview_stale"):
                await confirm_merge_intent(
                    db,
                    intent_id=intent.id,
                    preview_fingerprint=preview.fingerprint,
                    idempotency_key="stale-domain-state",
                )
            await db.rollback()

            source_user = await db.get(UserIdentity, source.user_id)
            source_preference = await db.get(BillingNotificationPreference, source.user_id)
            assert source_user is not None and source_user.status == "active"
            assert source_preference is not None
            assert source_preference.optional_email_enabled is False

    client.portal.call(exercise)
