"""F256 T016: comments follow the real proof-bound account merge under FORCE RLS."""

from uuid import uuid4

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
from twobrain_rec_server.db.models import (
    MediaRevision,
    MeetingComment,
    MeetingCommentMention,
    MeetingCommentReaction,
    Workspace,
)
from twobrain_rec_server.db.tenant_context import AccountMergeTenantContext, apply_tenant_context


def test_comments_merge_with_proof_and_deny_missing_proof(client):
    source = duplicate_account_fixture(191, email="comment-merge@example.test")

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
            media = MediaRevision(
                workspace_id=source.workspace_id,
                meeting_id=meeting.id,
                local_media_revision_id=uuid4().hex,
            )
            db.add(media)
            await db.flush()
            request_id = uuid4()
            comments = [
                MeetingComment(
                    id=uuid4(),
                    workspace_id=source.workspace_id,
                    meeting_id=meeting.id,
                    media_revision_id=media.id,
                    author_user_id=author,
                    request_id=request_id,
                    request_hash="a" * 64,
                    start_ms=0,
                    body="Synthetic merge discussion",
                    resolved=True,
                    resolved_by=source.user_id,
                )
                for author in (source.user_id, USER_ID)
            ]
            db.add_all(comments)
            await db.flush()
            for author in (source.user_id, USER_ID):
                db.add(
                    MeetingCommentMention(
                        workspace_id=source.workspace_id,
                        meeting_id=meeting.id,
                        comment_id=comments[0].id,
                        user_id=author,
                        start=0,
                        end=1,
                    )
                )
                db.add(
                    MeetingCommentReaction(
                        workspace_id=source.workspace_id,
                        meeting_id=meeting.id,
                        comment_id=comments[0].id,
                        user_id=author,
                        emoji="👍",
                    )
                )
            db.add(
                MeetingCommentReaction(
                    workspace_id=source.workspace_id,
                    meeting_id=meeting.id,
                    comment_id=comments[0].id,
                    user_id=source.user_id,
                    emoji="❤️",
                )
            )
            await db.flush()
            intent, preview = await _create_ready_merge(db, source_user_id=source.user_id)
            assert preview.blocker_codes == ()
            await db.commit()
            intent_id, meeting_id = intent.id, meeting.id
            callback_id = intent.proof_callback_state_id

        async with _exact_app_role_engine(client.app.state.settings.database_url) as engine:
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            # Valid-looking account IDs alone never unlock the comment graph.
            for probe_intent, probe_workspace, proof_present in (
                (uuid4(), WORKSPACE_ID, True),
                (intent_id, WORKSPACE_ID, False),
                (intent_id, uuid4(), True),
            ):
                async with client.app_state["sessionmaker"]() as seed:
                    await seed.execute(
                        text(
                            "UPDATE account_merge_intents SET proof_callback_state_id=:proof WHERE id=:intent"
                        ),
                        dict(proof=callback_id if proof_present else None, intent=intent_id),
                    )
                    await seed.commit()
                async with sessions() as db:
                    await apply_tenant_context(
                        db,
                        AccountMergeTenantContext(
                            intent_id=probe_intent,
                            workspace_id=probe_workspace,
                            survivor_user_id=USER_ID,
                            source_user_id=source.user_id,
                        ),
                    )
                    assert await db.scalar(text("SELECT session_user")) == "twobrain_rec_app"
                    assert not await db.scalar(text("SELECT rec_account_merge_context_valid()"))
                    for table in (
                        "meeting_comments",
                        "meeting_comment_mentions",
                        "meeting_comment_reactions",
                    ):
                        assert await db.scalar(text(f"SELECT count(*) FROM {table}")) == 0
                        for mutation in (
                            f"DELETE FROM {table}",
                            f"UPDATE {table} SET workspace_id=workspace_id",
                        ):
                            assert (
                                await db.execute(
                                    text(mutation + " WHERE meeting_id=:meeting"),
                                    {"meeting": meeting_id},
                                )
                            ).rowcount == 0
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
                assert await db.scalar(text("SELECT rec_maintenance_allowed()"))
                result = await confirm_merge_intent(
                    db,
                    intent_id=intent_id,
                    preview_fingerprint=preview.fingerprint,
                    idempotency_key="comment-merge-review",
                )
                assert result.status == "completed"
                await db.commit()
                assert not await db.scalar(text("SELECT rec_account_merge_context_valid()"))
                assert await db.scalar(text("SELECT count(*) FROM meeting_comments")) == 0

        async with client.app_state["sessionmaker"]() as db:
            rows = list(
                await db.scalars(
                    select(MeetingComment).where(MeetingComment.meeting_id == meeting_id)
                )
            )
            assert len(rows) == 2
            assert {row.author_user_id for row in rows} == {USER_ID}
            assert {row.resolved_by for row in rows} == {USER_ID}
            assert {row.workspace_id for row in rows} == {PERSONAL_WORKSPACE_ID}
            assert len({row.request_id for row in rows}) == 2
            mentions = list(
                await db.scalars(
                    select(MeetingCommentMention).where(
                        MeetingCommentMention.meeting_id == meeting_id
                    )
                )
            )
            reactions = list(
                await db.scalars(
                    select(MeetingCommentReaction).where(
                        MeetingCommentReaction.meeting_id == meeting_id
                    )
                )
            )
            assert len(mentions) == 1 and len(reactions) == 2
            assert {row.user_id for row in mentions + reactions} == {USER_ID}
            assert {row.workspace_id for row in mentions + reactions} == {PERSONAL_WORKSPACE_ID}
            assert {row.emoji for row in reactions} == {"👍", "❤️"}
            assert await db.get(Workspace, source.workspace_id) is None

    client.portal.call(exercise)
