"""F256 T014: bounded discussion reads and author labels under real RLS."""

from dataclasses import replace
from uuid import UUID, uuid4

from sqlalchemy import event, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID, tenant_scope
from tests.fixtures.cabinet_access import SHARED_USER_ID, auth_headers_for
from tests.integration.test_meeting_comments import setup_comments
from tests.integration.test_rls_postgres_policies import _create_probe_role, _drop_probe_role
from twobrain_rec_server.cabinet.access import (
    decide_meeting_access,
    hash_invitation_address,
    recipient_share_access_proof,
)
from twobrain_rec_server.cabinet.comments import comment_reader_context, comment_view, list_comments
from twobrain_rec_server.db.models import (
    ExternalIdentity,
    Meeting,
    MeetingComment,
    MeetingCommentMention,
    MeetingCommentReaction,
    MeetingShareGrant,
    Organization,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.db.tenant_context import apply_tenant_scope


def _comment(meeting_id, media_id, author=USER_ID, parent=None):
    return MeetingComment(
        id=uuid4(),
        workspace_id=WORKSPACE_ID,
        meeting_id=meeting_id,
        media_revision_id=media_id,
        author_user_id=author,
        parent_id=parent,
        request_id=uuid4(),
        request_hash="a" * 64,
        start_ms=1000,
        body="Synthetic discussion",
    )


def test_comment_list_query_count_is_bounded_and_cursors_preserved(client):
    seeds, _, payload = setup_comments(client)
    media_id = UUID(payload["media_revision_id"])

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            roots = [_comment(seeds.ready_id, media_id) for _ in range(100)]
            db.add_all(roots)
            await db.flush()
            replies = [
                _comment(seeds.ready_id, media_id, parent=root.id)
                for root in roots
                for _ in range(51)
            ]
            db.add_all(replies)
            await db.flush()
            for root in roots:
                db.add(
                    MeetingCommentMention(
                        workspace_id=WORKSPACE_ID,
                        meeting_id=seeds.ready_id,
                        comment_id=root.id,
                        user_id=USER_ID,
                        start=0,
                        end=1,
                    )
                )
                db.add(
                    MeetingCommentReaction(
                        workspace_id=WORKSPACE_ID,
                        meeting_id=seeds.ready_id,
                        comment_id=root.id,
                        user_id=USER_ID,
                        emoji="👍",
                    )
                )
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_scope(db, tenant_scope())
            meeting = await db.get(Meeting, seeds.ready_id)
            decision = await decide_meeting_access(
                db, meeting, workspace_id=WORKSPACE_ID, viewer_user_id=USER_ID
            )
            statements = []

            def count(_conn, _cursor, statement, _params, _context, _many):
                statements.append(statement)

            engine = db.bind.sync_engine
            event.listen(engine, "before_cursor_execute", count)
            try:
                page = await list_comments(
                    db, seeds.ready_id, media_id, decision, USER_ID, limit=100
                )
            finally:
                event.remove(engine, "before_cursor_execute", count)
            assert len(statements) <= 8, f"discussion SELECT count: {len(statements)}"
            print(f"comment_read_sql={len(statements)} roots=100 visible_replies=5000")
            assert page["total_count"] == 100 and len(page["items"]) == 100
            assert page["next_cursor"] is None
            for root in page["items"]:
                assert len(root["replies"]) == 50 and root["next_reply_cursor"]
                assert root["reactions"] == [dict(emoji="👍", count=1, selected=True)]
                assert root["mentions"] == [dict(user_id=str(USER_ID), start=0, end=1)]
            first = page["items"][0]
            next_page = await list_comments(
                db,
                seeds.ready_id,
                media_id,
                decision,
                USER_ID,
                parent_id=UUID(first["id"]),
                cursor=first["next_reply_cursor"],
            )
            assert len(next_page["items"]) == 1 and next_page["next_cursor"] is None
            assert next_page["items"][0]["id"] not in {r["id"] for r in first["replies"]}
            row = await db.get(MeetingComment, UUID(first["id"]))
            single = await comment_view(db, row, decision, USER_ID, with_replies=True)
            assert single == first

    client.portal.call(exercise)


def test_external_author_labels_for_owner_and_read_only_invitee_rls(client):
    seeds, url, payload = setup_comments(client)
    media_id = UUID(payload["media_revision_id"])
    organization, author, external_reader, external_workspace = uuid4(), uuid4(), uuid4(), uuid4()

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            db.add(Organization(id=organization, slug=str(organization), name="Synthetic external"))
            await db.flush()
            db.add(
                UserIdentity(
                    id=author,
                    organization_id=organization,
                    external_subject=str(author),
                    display_name="External author",
                    status="active",
                )
            )
            db.add(
                UserIdentity(
                    id=external_reader,
                    organization_id=organization,
                    external_subject=str(external_reader),
                    display_name="External reader",
                    status="active",
                )
            )
            await db.flush()
            db.add(
                Workspace(
                    id=external_workspace,
                    organization_id=organization,
                    slug=str(external_workspace),
                    name="External",
                    kind="corporate",
                )
            )
            await db.flush()
            db.add(
                WorkspaceMembership(
                    workspace_id=external_workspace,
                    user_id=external_reader,
                    role="owner",
                    status="active",
                )
            )
            db.add(
                ExternalIdentity(
                    user_id=external_reader,
                    provider="synthetic",
                    provider_subject=str(external_reader),
                    email="reader@example.test",
                    is_active=True,
                    is_verified=True,
                )
            )
            db.add(
                MeetingShareGrant(
                    workspace_id=WORKSPACE_ID,
                    meeting_id=seeds.ready_id,
                    grant_type="user",
                    grantee_user_id=external_reader,
                    audience_type="user",
                    audience_id=external_reader,
                    created_by_user_id=USER_ID,
                    content_scope="full_meeting",
                    metadata_json={
                        "source": "accepted_external_invitation",
                        "recipient_address_hash": hash_invitation_address("reader@example.test"),
                    },
                )
            )
            root = _comment(seeds.ready_id, media_id, author=author)
            db.add(root)
            await db.flush()
            db.add(_comment(seeds.ready_id, media_id, parent=root.id))
            db.add(
                MeetingShareGrant(
                    workspace_id=WORKSPACE_ID,
                    meeting_id=seeds.ready_id,
                    grant_type="user",
                    grantee_user_id=SHARED_USER_ID,
                    audience_type="user",
                    audience_id=SHARED_USER_ID,
                    created_by_user_id=USER_ID,
                    content_scope="full_meeting",
                )
            )
            await db.commit()
            owner_label = (await db.get(UserIdentity, USER_ID)).display_name
        database_url = client.app.state.settings.database_url
        role, password = await _create_probe_role(
            database_url, role_name="graf_read_" + uuid4().hex[:12]
        )
        engine = create_async_engine(make_url(database_url).set(username=role, password=password))
        try:
            for reader in (USER_ID, SHARED_USER_ID, external_reader):
                async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                    await apply_tenant_scope(
                        db,
                        replace(
                            tenant_scope(),
                            user_id=reader,
                            organization_id=organization
                            if reader == external_reader
                            else tenant_scope().organization_id,
                        ),
                    )
                    hidden_author = USER_ID if reader == external_reader else author
                    assert await db.get(UserIdentity, hidden_author) is None
                    meeting = await db.get(Meeting, seeds.ready_id)
                    proof = None
                    if reader == external_reader:
                        proof = await recipient_share_access_proof(
                            async_sessionmaker(engine, expire_on_commit=False),
                            recipient_scope=replace(
                                tenant_scope(),
                                user_id=reader,
                                organization_id=organization,
                                workspace_id=external_workspace,
                            ),
                            owner_workspace_id=WORKSPACE_ID,
                        )
                    decision = await decide_meeting_access(
                        db,
                        meeting,
                        workspace_id=WORKSPACE_ID,
                        viewer_user_id=reader,
                        recipient_proof=proof,
                    )
                    assert decision.can_view_full_meeting
                    if reader == external_reader:
                        no_proof = (
                            await db.execute(
                                text(
                                    "SELECT * FROM rec_comment_author_labels(:meeting, CAST(:users AS uuid[]))"
                                ),
                                dict(meeting=seeds.ready_id, users=[USER_ID]),
                            )
                        ).all()
                        assert no_proof == []
                    # Mirrors the dependency only after its real ACL decision.
                    async with comment_reader_context(db, meeting, decision, reader):
                        page = await list_comments(db, seeds.ready_id, media_id, decision, reader)
                    assert "comment_reader_access" not in db.info
                    assert not await db.scalar(
                        text(
                            "SELECT NULLIF(current_setting('app.comment_reader_user_id', true),'')"
                        )
                    )
                    assert page["items"][0]["author_label"] == "External author"
                    assert page["items"][0]["replies"][0]["author_label"] == owner_label
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                await apply_tenant_scope(db, replace(tenant_scope(), user_id=uuid4()))
                labels = (
                    await db.execute(
                        text(
                            "SELECT * FROM rec_comment_author_labels(:meeting, CAST(:users AS uuid[]))"
                        ),
                        dict(meeting=seeds.ready_id, users=[author]),
                    )
                ).all()
                assert labels == []
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                await apply_tenant_scope(
                    db,
                    replace(tenant_scope(), organization_id=organization, user_id=external_reader),
                )
                await db.execute(
                    text(
                        "SELECT set_config('app.comment_reader_meeting_id', :meeting, true), set_config('app.comment_reader_user_id', :user, true)"
                    ),
                    dict(meeting=str(seeds.ready_id), user=str(external_reader)),
                )
                query = text(
                    "SELECT * FROM rec_comment_author_labels(:meeting, CAST(:users AS uuid[]))"
                )
                params = dict(meeting=seeds.ready_id, users=[USER_ID, author, external_reader])
                projected = (await db.execute(query, params)).mappings().all()
                assert {r["user_id"] for r in projected} == {USER_ID, author}
                assert all(set(r) == {"user_id", "display_label"} for r in projected)
                await db.execute(
                    text("SELECT set_config('app.comment_reader_user_id', :user, true)"),
                    dict(user=str(USER_ID)),
                )
                assert (await db.execute(query, params)).all() == []
                await db.execute(
                    text(
                        "SELECT set_config('app.comment_reader_user_id', :user, true), set_config('app.workspace_id', :workspace, true)"
                    ),
                    dict(user=str(external_reader), workspace=str(uuid4())),
                )
                assert (await db.execute(query, params)).all() == []
                await db.execute(
                    text("SELECT set_config('app.workspace_id', :workspace, true)"),
                    dict(workspace=str(WORKSPACE_ID)),
                )
                async with client.app_state["sessionmaker"]() as writer:
                    active = await writer.scalar(
                        select(MeetingShareGrant).where(
                            MeetingShareGrant.grantee_user_id == external_reader
                        )
                    )
                    active.status = "revoked"
                    await writer.commit()
                assert (await db.execute(query, params)).all() == []
                meeting = await db.get(Meeting, seeds.ready_id)
                denied = await decide_meeting_access(
                    db, meeting, workspace_id=WORKSPACE_ID, viewer_user_id=external_reader
                )
                assert not denied.can_view
        finally:
            await engine.dispose()
            await _drop_probe_role(database_url, role)

    client.portal.call(exercise)
    # The API still fences discussion reads before any author projection.
    assert (
        client.get(
            url.replace(str(seeds.ready_id), str(seeds.processing_id)), headers=auth_headers_for()
        ).status_code
        == 404
    )
    assert client.get(url, headers=auth_headers()).status_code == 200
