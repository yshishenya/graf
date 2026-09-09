"""F256: real database/HTTP boundaries, using synthetic meetings only."""

from uuid import UUID, uuid4

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID, tenant_scope
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import SHARED_USER_ID, add_workspace_user, auth_headers_for
from twobrain_rec_server.db.models import MediaRevision, Meeting, MeetingShareGrant


def setup_comments(client):
    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)

    async def revision():
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(MediaRevision.id).where(MediaRevision.meeting_id == seeds.ready_id)
            )

    media = client.portal.call(revision)
    url = f"/api/v1/cabinet/meetings/{seeds.ready_id}/comments"
    body = dict(
        request_id=str(uuid4()),
        media_revision_id=str(media),
        start_ms=1000,
        body="Synthetic comment",
        mentions=[],
    )
    return seeds, url, body


def grant(client, meeting_id, **rights):
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/shares",
        headers=auth_headers(),
        json=dict(
            audience_type="user",
            audience_id=str(SHARED_USER_ID),
            content_scope="full_meeting",
            **rights,
        ),
    )
    if response.status_code == 409 and rights:

        async def identifier():
            async with client.app_state["sessionmaker"]() as db:
                return await db.scalar(
                    select(MeetingShareGrant.id).where(
                        MeetingShareGrant.meeting_id == meeting_id,
                        MeetingShareGrant.grantee_user_id == SHARED_USER_ID,
                        MeetingShareGrant.status == "active",
                    )
                )

        identifier = client.portal.call(identifier)
        response = client.patch(
            f"/api/v1/cabinet/meetings/{meeting_id}/shares/{identifier}/permissions",
            headers=auth_headers(),
            json=dict(
                can_comment=rights.get("can_comment", False), can_edit=rights.get("can_edit", False)
            ),
        )
        assert response.status_code == 200, response.text
        return response.json()
    assert response.status_code == 201, response.text
    return response.json()


def test_comment_access_and_request_fences(client):
    seeds, url, body = setup_comments(client)
    assert client.get(url, headers=auth_headers_for()).status_code == 404
    grant(client, seeds.ready_id)
    assert client.post(url, json=body, headers=auth_headers_for()).status_code == 403
    grant(client, seeds.ready_id, can_comment=True)
    invalid = {**body, "media_revision_id": str(uuid4())}
    assert client.post(url, json=invalid, headers=auth_headers_for()).status_code == 409
    assert (
        client.post(url, json={**body, "start_ms": -1}, headers=auth_headers_for()).status_code
        == 422
    )
    created = client.post(url, json=body, headers=auth_headers_for())
    assert created.status_code == 201, created.text
    comment = created.json()
    assert client.post(url, json=body, headers=auth_headers_for()).json()["id"] == comment["id"]
    assert (
        client.post(url, json={**body, "body": "Different"}, headers=auth_headers_for()).status_code
        == 409
    )
    assert (
        client.patch(
            url + "/" + comment["id"],
            json=dict(expected_version=99, body="Edit", mentions=[]),
            headers=auth_headers_for(),
        ).status_code
        == 409
    )
    # A viewer cannot grant itself the new authority.
    denied = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers_for(),
        json=dict(
            audience_type="user",
            audience_id=str(SHARED_USER_ID),
            content_scope="full_meeting",
            can_edit=True,
            can_comment=True,
        ),
    )
    assert denied.status_code in (403, 404)


def test_comment_lifecycle_and_mentions(client):
    seeds, url, body = setup_comments(client)
    grant(client, seeds.ready_id, can_comment=True)
    body.update(
        body="@Teammate Synthetic", mentions=[dict(user_id=str(SHARED_USER_ID), start=0, end=9)]
    )
    response = client.post(url, json=body, headers=auth_headers())
    assert response.status_code == 201, response.text
    root = response.json()
    reply = client.post(
        url + "/" + root["id"] + "/replies",
        headers=auth_headers_for(),
        json=dict(request_id=str(uuid4()), body="Reply", mentions=[]),
    )
    assert reply.status_code == 201, reply.text
    for _ in range(2):
        reaction = client.put(
            url + "/" + root["id"] + "/reaction",
            headers=auth_headers_for(),
            json=dict(emoji="👍", selected=True),
        )
        assert reaction.status_code == 200, reaction.text
        assert reaction.json()["reactions"][0]["count"] == 1
    result = client.put(
        url + "/" + root["id"] + "/resolution",
        headers=auth_headers(),
        json=dict(expected_version=root["version"], resolved=True),
    )
    assert result.status_code == 200, result.text
    assert client.get(url, headers=auth_headers()).json()["items"] == []
    assert len(client.get(url + "?status=resolved", headers=auth_headers()).json()["items"]) == 1
    inbox = client.get("/api/v1/notifications?filter=history", headers=auth_headers_for()).json()
    assert any("comment_id=" in item["href"] for item in inbox["items"])
    deleted = client.request(
        "DELETE",
        url + "/" + root["id"],
        headers=auth_headers(),
        json=dict(expected_version=result.json()["version"]),
    )
    assert deleted.status_code == 204, deleted.text
    assert client.get(url + "/" + reply.json()["id"], headers=auth_headers_for()).status_code == 404
    inbox = client.get("/api/v1/notifications?filter=history", headers=auth_headers_for()).json()
    assert not any("comment_id=" in item["href"] for item in inbox["items"])


def test_comment_summary_scope_revocation_and_legacy_team_access(client):
    from tests.fakes.auth_contexts import WORKSPACE_ID
    from twobrain_rec_server.db.models import Meeting, WorkspaceMembership

    seeds, url, body = setup_comments(client)
    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers(),
        json=dict(
            audience_type="user", audience_id=str(SHARED_USER_ID), content_scope="summary_only"
        ),
    )
    assert response.status_code == 201
    assert client.get(url, headers=auth_headers_for()).status_code == 404
    invalid = client.patch(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares/{response.json()['grant']['grant_id']}/permissions",
        headers=auth_headers(),
        json=dict(can_edit=True, can_comment=False),
    )
    assert invalid.status_code == 422

    async def team():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, seeds.ready_id)
            meeting.visibility = "team"
            member = await db.scalar(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == WORKSPACE_ID,
                    WorkspaceMembership.user_id == SHARED_USER_ID,
                )
            )
            member.role = "admin"
            await db.commit()

    client.portal.call(team)
    page = client.get(url, headers=auth_headers_for())
    assert page.status_code == 200
    assert not page.json()["capabilities"]["can_comment"]
    escalated = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers_for(),
        json=dict(
            audience_type="user",
            audience_id=str(SHARED_USER_ID),
            content_scope="full_meeting",
            can_comment=True,
            can_edit=True,
        ),
    )
    assert escalated.status_code == 403
    grant(client, seeds.ready_id, can_comment=True)
    assert client.post(url, json=body, headers=auth_headers_for()).status_code == 201

    async def revoke():
        async with client.app_state["sessionmaker"]() as db:
            member = await db.scalar(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == WORKSPACE_ID,
                    WorkspaceMembership.user_id == SHARED_USER_ID,
                )
            )
            member.status = "inactive"
            await db.commit()

    client.portal.call(revoke)
    assert client.post(
        url, json={**body, "request_id": str(uuid4())}, headers=auth_headers_for()
    ).status_code in (401, 403, 404)


def test_comment_validation_pagination_and_full_purge(client):
    from sqlalchemy import func

    from twobrain_rec_server.db.models import (
        MeetingComment,
        MeetingCommentMention,
        MeetingCommentReaction,
    )

    seeds, url, body = setup_comments(client)
    assert client.post(url, headers=auth_headers(), json={**body, "body": "  "}).status_code == 422
    assert (
        client.post(
            url,
            headers=auth_headers(),
            json={
                **body,
                "body": "@Other",
                "mentions": [dict(user_id=str(SHARED_USER_ID), start=0, end=6)],
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            url, headers=auth_headers(), json={**body, "source_segment_id": str(uuid4())}
        ).status_code
        == 422
    )
    root = client.post(url, headers=auth_headers(), json=body).json()
    for number in range(3):
        reply = client.post(
            url + "/" + root["id"] + "/replies",
            headers=auth_headers(),
            json=dict(request_id=str(uuid4()), body=f"Reply {number}", mentions=[]),
        )
        assert reply.status_code == 201
    nested = client.post(
        url + "/" + reply.json()["id"] + "/replies",
        headers=auth_headers(),
        json=dict(request_id=str(uuid4()), body="Nested", mentions=[]),
    )
    assert nested.status_code == 422
    page = client.get(url + "/" + root["id"] + "/replies?limit=2", headers=auth_headers()).json()
    assert len(page["items"]) == 2 and page["next_cursor"]
    second = client.get(
        url + "/" + root["id"] + "/replies",
        headers=auth_headers(),
        params={"limit": 2, "cursor": page["next_cursor"]},
    ).json()
    assert len(second["items"]) == 1 and second["next_cursor"] is None
    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": "Delete this meeting everywhere GRAF controls."},
    )
    assert response.status_code == 202, response.text
    assert client.get(url, headers=auth_headers()).status_code == 404

    async def counts():
        async with client.app_state["sessionmaker"]() as db:
            return [
                await db.scalar(
                    select(func.count())
                    .select_from(model)
                    .where(model.meeting_id == seeds.ready_id)
                )
                for model in (MeetingComment, MeetingCommentMention, MeetingCommentReaction)
            ]

    assert client.portal.call(counts) == [0, 0, 0]


def test_comment_edit_mentions_no_renotify_and_readd(client):
    from twobrain_rec_server.db.models import ServerNotification

    seeds, url, body = setup_comments(client)
    grant(client, seeds.ready_id, can_comment=True)
    # Astral emoji: positions count code points, not UTF-16 units.
    mentions = [dict(user_id=str(SHARED_USER_ID), start=2, end=11)]
    body.update(body="🎉 @Teammate hello", mentions=mentions)
    row = client.post(url, headers=auth_headers(), json=body).json()

    async def notice():
        async with client.app_state["sessionmaker"]() as db:
            n = await db.scalar(
                select(ServerNotification).where(
                    ServerNotification.family == "comment",
                    ServerNotification.meeting_id == seeds.ready_id,
                )
            )
            return n.id, n.revision

    first = client.portal.call(notice)
    edited = client.patch(
        url + "/" + row["id"],
        headers=auth_headers(),
        json=dict(expected_version=row["version"], body=body["body"] + "!", mentions=mentions),
    ).json()
    assert client.portal.call(notice) == first
    removed = client.patch(
        url + "/" + row["id"],
        headers=auth_headers(),
        json=dict(expected_version=edited["version"], body="Removed mention", mentions=[]),
    ).json()
    readded = client.patch(
        url + "/" + row["id"],
        headers=auth_headers(),
        json=dict(expected_version=removed["version"], body=body["body"], mentions=mentions),
    )
    assert readded.status_code == 200, readded.text
    assert client.portal.call(notice) == (first[0], first[1] + 1)


def test_comment_rls_legitimate_producer_and_forgery(client):
    from dataclasses import replace

    import pytest
    from sqlalchemy.engine import make_url
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID, tenant_scope
    from tests.integration.test_rls_postgres_policies import _create_probe_role, _drop_probe_role
    from twobrain_rec_server.cabinet.access import decide_meeting_access
    from twobrain_rec_server.cabinet.comments import CreateComment, create_comment
    from twobrain_rec_server.db.models import Meeting, ServerNotification
    from twobrain_rec_server.db.tenant_context import apply_tenant_scope

    seeds, url, body = setup_comments(client)
    grant(client, seeds.ready_id, can_comment=True)

    async def exercise():
        database_url = client.app.state.settings.database_url
        role, password = await _create_probe_role(
            database_url, role_name="graf_comments_" + uuid4().hex[:12]
        )
        engine = create_async_engine(make_url(database_url).set(username=role, password=password))
        try:
            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with factory() as db:
                await apply_tenant_scope(db, replace(tenant_scope(), user_id=SHARED_USER_ID))
                meeting = await db.get(Meeting, seeds.ready_id)
                decision = await decide_meeting_access(
                    db, meeting, workspace_id=WORKSPACE_ID, viewer_user_id=SHARED_USER_ID
                )
                payload = CreateComment(
                    **{
                        **body,
                        "body": "@Owner hello",
                        "mentions": [dict(user_id=USER_ID, start=0, end=6)],
                    }
                )
                row = await create_comment(db, meeting, decision, SHARED_USER_ID, payload)
                await db.commit()
                await apply_tenant_scope(db, replace(tenant_scope(), user_id=SHARED_USER_ID))
                db.add(
                    ServerNotification(
                        recipient_id=SHARED_USER_ID,
                        workspace_id=WORKSPACE_ID,
                        meeting_id=seeds.ready_id,
                        family="comment",
                        source_id=row.id,
                        source_revision="1",
                        kind="mentioned",
                        revision=1,
                        read_revision=0,
                        requires_action=False,
                    )
                )
                with pytest.raises(DBAPIError):
                    await db.flush()
                await db.rollback()
        finally:
            await engine.dispose()
            await _drop_probe_role(database_url, role)

    client.portal.call(exercise)


def test_comment_identity_merge_preserves_threads_and_deduplicates(client):
    from sqlalchemy import func

    from tests.fakes.auth_contexts import USER_ID
    from twobrain_rec_server.cabinet.comments import merge_comment_identity
    from twobrain_rec_server.db.models import (
        MeetingComment,
        MeetingCommentMention,
        MeetingCommentReaction,
    )

    seeds, url, body = setup_comments(client)
    grant(client, seeds.ready_id, can_comment=True)
    body.update(
        body="@Owner @Other",
        mentions=[
            dict(user_id=str(USER_ID), start=0, end=6),
            dict(user_id=str(SHARED_USER_ID), start=7, end=13),
        ],
    )
    root = client.post(url, headers=auth_headers(), json=body).json()
    second = client.post(
        url, headers=auth_headers_for(), json={**body, "body": "Second", "mentions": []}
    )
    assert second.status_code == 201, second.text
    for headers in (auth_headers(), auth_headers_for()):
        assert (
            client.put(
                url + "/" + root["id"] + "/reaction",
                headers=headers,
                json=dict(emoji="👍", selected=True),
            ).status_code
            == 200
        )

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            await merge_comment_identity(db, SHARED_USER_ID, USER_ID)
            await db.commit()
            comments = list(
                await db.scalars(
                    select(MeetingComment).where(MeetingComment.meeting_id == seeds.ready_id)
                )
            )
            assert len(comments) == 2 and all(c.author_user_id == USER_ID for c in comments)
            assert len({c.request_id for c in comments}) == 2
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(MeetingCommentMention)
                    .where(MeetingCommentMention.meeting_id == seeds.ready_id)
                )
                == 1
            )
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(MeetingCommentReaction)
                    .where(MeetingCommentReaction.meeting_id == seeds.ready_id)
                )
                == 1
            )

    client.portal.call(exercise)


def test_comment_cross_workspace_recipient_proof(client):
    from tests.fakes.auth_contexts import ORG_ID, USER_ID, WORKSPACE_ID
    from twobrain_rec_server.cabinet.access import hash_invitation_address
    from twobrain_rec_server.db.models import (
        ExternalIdentity,
        RegisteredDevice,
        UserIdentity,
        Workspace,
        WorkspaceMembership,
    )

    seeds, url, body = setup_comments(client)
    user, workspace, device = uuid4(), uuid4(), uuid4()

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            db.add_all(
                [
                    UserIdentity(
                        id=user,
                        organization_id=ORG_ID,
                        external_subject=str(user),
                        display_name="External synthetic",
                        status="active",
                    ),
                    Workspace(
                        id=workspace,
                        organization_id=ORG_ID,
                        slug=str(workspace),
                        name="External synthetic",
                        kind="corporate",
                    ),
                ]
            )
            await db.flush()
            db.add_all(
                [
                    WorkspaceMembership(
                        workspace_id=workspace, user_id=user, role="owner", status="active"
                    ),
                    RegisteredDevice(
                        id=device,
                        workspace_id=workspace,
                        user_id=user,
                        device_public_id=str(device),
                        status="active",
                    ),
                    ExternalIdentity(
                        user_id=user,
                        provider="test",
                        provider_subject=str(user),
                        email="comment@example.test",
                        is_verified=True,
                    ),
                    MeetingShareGrant(
                        workspace_id=WORKSPACE_ID,
                        meeting_id=seeds.ready_id,
                        grant_type="user",
                        grantee_user_id=user,
                        audience_type="user",
                        audience_id=user,
                        created_by_user_id=USER_ID,
                        content_scope="full_meeting",
                        can_comment=True,
                        can_edit=True,
                        metadata_json={
                            "source": "accepted_external_invitation",
                            "recipient_address_hash": hash_invitation_address(
                                "comment@example.test"
                            ),
                        },
                    ),
                ]
            )
            await db.commit()

    client.portal.call(seed)
    headers = {
        "X-Organization-Id": str(ORG_ID),
        "X-Workspace-Id": str(workspace),
        "X-User-Id": str(user),
        "X-Device-Id": str(device),
    }
    assert client.get(url, headers=headers).status_code == 404
    assert (
        client.get(url + "?workspace_id=" + str(WORKSPACE_ID), headers=headers).status_code == 200
    )
    assert (
        client.post(
            url + "?workspace_id=" + str(WORKSPACE_ID), headers=headers, json=body
        ).status_code
        == 201
    )

    for prefix in ("", "/desktop"):
        fragment = client.get(
            f"{prefix}/meetings/{seeds.ready_id}/share?workspace_id={WORKSPACE_ID}", headers=headers
        )
        assert fragment.status_code == 200, fragment.text
        assert (
            "data-share-existing-role" in fragment.text
            or "data-share-comment-role" in fragment.text
        )

    from tests.integration.test_speaker_names import _renameable_speaker_keys

    speaker = _renameable_speaker_keys(client, seeds.ready_id, auth_headers())[0]
    renamed = client.post(
        f"/meetings/{seeds.ready_id}/speakers/{speaker}?workspace_id={WORKSPACE_ID}",
        headers=headers,
        data={"display_name": "External editor"},
        follow_redirects=False,
    )
    assert renamed.status_code == 303, renamed.text
    assert renamed.headers["location"].startswith("/shared-meetings/")

    share_url = f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares"
    owner_query = "?workspace_id=" + str(WORKSPACE_ID)
    created = client.post(
        share_url + owner_query,
        headers=headers,
        json=dict(
            audience_type="user",
            audience_id=str(SHARED_USER_ID),
            content_scope="full_meeting",
            can_comment=True,
            can_edit=True,
        ),
    )
    assert created.status_code == 201, created.text
    shared_id = created.json()["grant"]["grant_id"]
    changed = client.patch(
        share_url + "/" + shared_id + "/permissions" + owner_query,
        headers=headers,
        json=dict(can_comment=True, can_edit=False),
    )
    assert changed.status_code == 200, changed.text
    rotated = client.post(share_url + "/" + shared_id + "/rotate" + owner_query, headers=headers)
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["grant"]["can_comment"] and not rotated.json()["grant"]["can_edit"]
    revoked = client.delete(share_url + "/" + shared_id + owner_query, headers=headers)
    assert revoked.status_code == 204, revoked.text

    async def revoke():
        async with client.app_state["sessionmaker"]() as db:
            identity = await db.scalar(
                select(ExternalIdentity).where(ExternalIdentity.user_id == user)
            )
            identity.is_verified = False
            await db.commit()

    client.portal.call(revoke)
    assert (
        client.get(url + "?workspace_id=" + str(WORKSPACE_ID), headers=headers).status_code == 404
    )

    denied_share = client.post(
        share_url + owner_query,
        headers=headers,
        json=dict(
            audience_type="user",
            audience_id=str(SHARED_USER_ID),
            content_scope="full_meeting",
            can_comment=True,
            can_edit=True,
        ),
    )
    assert denied_share.status_code == 404, denied_share.text


def test_editor_share_notice_rls_requires_real_grant(client):
    from dataclasses import replace

    import pytest
    from sqlalchemy.engine import make_url
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID, tenant_scope
    from tests.integration.test_rls_postgres_policies import _create_probe_role, _drop_probe_role
    from twobrain_rec_server.db.models import Meeting, ServerNotification
    from twobrain_rec_server.db.tenant_context import apply_tenant_scope
    from twobrain_rec_server.notifications.inbox import record_event

    seeds, _, _ = setup_comments(client)
    grant(client, seeds.ready_id, can_comment=True, can_edit=True)
    target_user, target_device = uuid4(), uuid4()
    add_workspace_user(client, user_id=target_user, device_id=target_device)
    created = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers(),
        json=dict(audience_type="user", audience_id=str(target_user), content_scope="full_meeting"),
    )
    assert created.status_code == 201, created.text
    from uuid import UUID

    target_id = UUID(created.json()["grant"]["grant_id"])

    async def exercise():
        database_url = client.app.state.settings.database_url
        role, password = await _create_probe_role(
            database_url, role_name="graf_editor_" + uuid4().hex[:12]
        )
        engine = create_async_engine(make_url(database_url).set(username=role, password=password))
        try:
            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with factory() as db:
                await apply_tenant_scope(db, replace(tenant_scope(), user_id=SHARED_USER_ID))
                meeting = await db.get(Meeting, seeds.ready_id)
                await record_event(
                    db,
                    meeting=meeting,
                    kind="shared",
                    source_revision="editor-rotation",
                    recipient_id=target_user,
                    share_id=target_id,
                )
                await db.commit()
                for family, source, recipient, kind in [
                    ("share", uuid4(), target_user, "shared"),
                    ("share", target_id, USER_ID, "shared"),
                    ("result", seeds.ready_id, target_user, "result_ready"),
                ]:
                    await apply_tenant_scope(db, replace(tenant_scope(), user_id=SHARED_USER_ID))
                    db.add(
                        ServerNotification(
                            recipient_id=recipient,
                            workspace_id=WORKSPACE_ID,
                            meeting_id=seeds.ready_id,
                            family=family,
                            source_id=source,
                            source_revision="forged",
                            kind=kind,
                            revision=1,
                            read_revision=0,
                            requires_action=False,
                        )
                    )
                    with pytest.raises(DBAPIError):
                        await db.flush()
                    await db.rollback()
        finally:
            await engine.dispose()
            await _drop_probe_role(database_url, role)

    client.portal.call(exercise)


def test_pending_media_preserves_accepted_comments(client):
    seeds, url, body = setup_comments(client)
    created = client.post(url, headers=auth_headers(), json=body)
    assert created.status_code == 201, created.text

    async def stage():
        from twobrain_rec_server.processing.store import latest_media_revision_for_meeting

        async with client.app_state["sessionmaker"]() as db:
            accepted = await db.get(MediaRevision, UUID(body["media_revision_id"]))
            staged = MediaRevision(
                workspace_id=accepted.workspace_id,
                meeting_id=accepted.meeting_id,
                local_media_revision_id=str(uuid4()),
                revision_number=accepted.revision_number + 1,
                status="pending_upload",
                immutable=False,
                duration_seconds=accepted.duration_seconds,
            )
            db.add(staged)
            await db.commit()
            canonical = await latest_media_revision_for_meeting(
                db, workspace_id=WORKSPACE_ID, meeting_id=seeds.ready_id
            )
            assert canonical.id == accepted.id
            return staged.id

    client.portal.call(stage)
    page = client.get(url, headers=auth_headers())
    assert page.status_code == 200, page.text
    assert page.json()["media_revision_id"] == body["media_revision_id"]
    assert len(page.json()["items"]) == 1
    old = client.get(url + "/" + created.json()["id"], headers=auth_headers())
    assert old.status_code == 200, old.text


def test_cross_organization_mention_rls(client):
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from tests.integration.test_rls_postgres_policies import _create_probe_role, _drop_probe_role
    from twobrain_rec_server.cabinet.access import (
        ShareRecipientAccessProof,
        decide_meeting_access,
        hash_invitation_address,
    )
    from twobrain_rec_server.cabinet.comments import eligible_user
    from twobrain_rec_server.db.models import (
        ExternalIdentity,
        MeetingShareGrant,
        Organization,
        UserIdentity,
    )
    from twobrain_rec_server.db.tenant_context import apply_tenant_scope

    seeds, url, body = setup_comments(client)
    organization, user = uuid4(), uuid4()
    address_hash = hash_invitation_address("external-review@example.test")

    async def exercise():
        database_url = client.app.state.settings.database_url
        async with client.app_state["sessionmaker"]() as db:
            db.add(Organization(id=organization, slug=str(organization), name="Synthetic external"))
            await db.flush()
            db.add(
                UserIdentity(
                    id=user,
                    organization_id=organization,
                    external_subject=str(user),
                    status="active",
                )
            )
            await db.flush()
            db.add_all(
                [
                    ExternalIdentity(
                        user_id=user,
                        provider="test",
                        provider_subject=str(user),
                        email="external-review@example.test",
                        is_verified=True,
                        is_active=True,
                    ),
                    MeetingShareGrant(
                        workspace_id=WORKSPACE_ID,
                        meeting_id=seeds.ready_id,
                        grant_type="user",
                        grantee_user_id=user,
                        audience_type="user",
                        audience_id=user,
                        created_by_user_id=USER_ID,
                        content_scope="full_meeting",
                        can_comment=True,
                        metadata_json={
                            "source": "accepted_external_invitation",
                            "recipient_address_hash": address_hash,
                        },
                    ),
                ]
            )
            await db.commit()
            meeting = await db.get(Meeting, seeds.ready_id)
            assert await eligible_user(db, meeting, user) is True
        role, password = await _create_probe_role(
            database_url, role_name="graf_review_" + uuid4().hex[:12]
        )
        engine = create_async_engine(make_url(database_url).set(username=role, password=password))
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                await apply_tenant_scope(db, tenant_scope())
                meeting = await db.get(Meeting, seeds.ready_id)
                proof = ShareRecipientAccessProof(
                    user_is_active=True,
                    workspace_membership_is_active=False,
                    verified_address_hashes=frozenset([address_hash]),
                )
                access = await decide_meeting_access(
                    db,
                    meeting,
                    workspace_id=WORKSPACE_ID,
                    viewer_user_id=user,
                    recipient_proof=proof,
                )
                assert access.can_view and access.can_view_full_meeting
                assert await eligible_user(db, meeting, user) is True
                from twobrain_rec_server.cabinet.comments import (
                    CreateComment,
                    create_comment,
                    mention_candidates,
                )

                candidates = await mention_candidates(db, meeting, "")
                assert str(user) in {item["user_id"] for item in candidates["items"]}
                assert all(
                    set(item) == {"user_id", "display_label"} for item in candidates["items"]
                )
                owner_access = await decide_meeting_access(
                    db, meeting, workspace_id=WORKSPACE_ID, viewer_user_id=USER_ID
                )
                await create_comment(
                    db,
                    meeting,
                    owner_access,
                    USER_ID,
                    CreateComment(
                        **{
                            **body,
                            "body": "@External hello",
                            "mentions": [dict(user_id=user, start=0, end=9)],
                        }
                    ),
                )
                await db.commit()
                async with client.app_state["sessionmaker"]() as privileged:
                    identity = await privileged.scalar(
                        select(ExternalIdentity).where(ExternalIdentity.user_id == user)
                    )
                    identity.is_verified = False
                    await privileged.commit()
                await apply_tenant_scope(db, tenant_scope())
                assert not await eligible_user(db, meeting, user)
                assert str(user) not in {
                    item["user_id"] for item in (await mention_candidates(db, meeting, ""))["items"]
                }
        finally:
            await engine.dispose()
            await _drop_probe_role(database_url, role)

    client.portal.call(exercise)


def test_root_author_delete_leaves_reply_notice(client):
    from dataclasses import replace

    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from tests.fixtures.cabinet_access import (
        SHARED_USER_ID,
        add_workspace_user,
        auth_headers_for,
        grant_meeting_to_user,
    )
    from tests.integration.test_meeting_comments import grant
    from tests.integration.test_rls_postgres_policies import _create_probe_role, _drop_probe_role
    from twobrain_rec_server.cabinet.access import decide_meeting_access
    from twobrain_rec_server.cabinet.comments import delete_comment
    from twobrain_rec_server.db.models import MeetingComment, ServerNotification
    from twobrain_rec_server.db.tenant_context import apply_tenant_scope

    seeds, url, body = setup_comments(client)
    grant(client, seeds.ready_id, can_comment=True)
    third = uuid4()
    add_workspace_user(client, user_id=third, device_id=uuid4())
    grant_meeting_to_user(client, seeds.ready_id, user_id=third)
    root = client.post(url, headers=auth_headers_for(), json=body)
    assert root.status_code == 201, root.text
    root = root.json()
    reply = client.post(
        url + "/" + root["id"] + "/replies",
        headers=auth_headers(),
        json=dict(
            request_id=str(uuid4()),
            body="@Third hello",
            mentions=[dict(user_id=str(third), start=0, end=6)],
        ),
    )
    assert reply.status_code == 201, reply.text
    reply_id = UUID(reply.json()["id"])

    async def exercise():
        database_url = client.app.state.settings.database_url
        role, password = await _create_probe_role(
            database_url, role_name="graf_review_" + uuid4().hex[:12]
        )
        engine = create_async_engine(make_url(database_url).set(username=role, password=password))
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                await apply_tenant_scope(db, replace(tenant_scope(), user_id=SHARED_USER_ID))
                meeting = await db.get(Meeting, seeds.ready_id)
                decision = await decide_meeting_access(
                    db, meeting, workspace_id=WORKSPACE_ID, viewer_user_id=SHARED_USER_ID
                )
                assert decision.can_comment and not decision.can_edit
                row = await db.get(MeetingComment, UUID(root["id"]))
                await delete_comment(db, meeting, decision, SHARED_USER_ID, row, row.version)
                await db.commit()
            async with client.app_state["sessionmaker"]() as db:
                assert await db.get(MeetingComment, reply_id) is None
                orphan = await db.scalar(
                    select(ServerNotification).where(
                        ServerNotification.source_id == reply_id,
                        ServerNotification.family == "comment",
                    )
                )
                assert orphan is None
        finally:
            await engine.dispose()
            await _drop_probe_role(database_url, role)

    client.portal.call(exercise)


def test_source_counts_ignore_pagination_status_and_author_filters(client):
    from twobrain_rec_server.db.models import TranscriptSegment

    seeds, url, body = setup_comments(client)

    async def sources():
        async with client.app_state["sessionmaker"]() as db:
            return list(
                await db.execute(
                    select(TranscriptSegment.id, TranscriptSegment.processing_result_id)
                    .where(TranscriptSegment.meeting_id == seeds.ready_id)
                    .order_by(TranscriptSegment.sequence)
                )
            )

    segments = client.portal.call(sources)
    ids = []
    for source, result in (segments[0], segments[0], segments[1]):
        response = client.post(
            url,
            headers=auth_headers(),
            json={
                **body,
                "request_id": str(uuid4()),
                "source_segment_id": str(source),
                "processing_result_id": str(result),
            },
        )
        assert response.status_code == 201, response.text
        ids.append(response.json()["id"])
    assert (
        client.put(
            url + "/" + ids[0] + "/resolution",
            headers=auth_headers(),
            json=dict(expected_version=1, resolved=True),
        ).status_code
        == 200
    )
    assert (
        client.post(
            url + "/" + ids[0] + "/replies",
            headers=auth_headers(),
            json=dict(request_id=str(uuid4()), body="Reply", mentions=[]),
        ).status_code
        == 201
    )
    expected = {str(segments[0][0]): 2, str(segments[1][0]): 1}
    page = client.get(url + "?limit=1", headers=auth_headers()).json()
    assert len(page["items"]) == 1 and page["next_cursor"]
    assert page["total_count"] == 3
    assert {r["source_segment_id"]: r["count"] for r in page["source_counts"]} == expected
    filtered = client.get(
        url,
        headers=auth_headers(),
        params=[("status", "all"), ("source_segment_ids", str(segments[0][0]))],
    ).json()
    assert len(filtered["items"]) == 2 and filtered["total_count"] == 3
    together = client.get(
        url,
        headers=auth_headers(),
        params=[("status", "all"), *[("source_segment_ids", str(s[0])) for s in segments]],
    ).json()
    assert len(together["items"]) == 3
    none = client.get(url, headers=auth_headers(), params=dict(author_id=str(uuid4()))).json()
    assert none["items"] == [] and none["total_count"] == 3
    assert (
        client.get(
            url, headers=auth_headers(), params=[("source_segment_ids", str(uuid4()))] * 101
        ).status_code
        == 422
    )


def test_workspace_editor_grant_adds_to_individual_viewer(client):
    seeds, url, _ = setup_comments(client)
    grant(client, seeds.ready_id)

    async def broad_grant():
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                MeetingShareGrant(
                    workspace_id=WORKSPACE_ID,
                    meeting_id=seeds.ready_id,
                    grant_type="workspace",
                    audience_type="workspace",
                    audience_id=WORKSPACE_ID,
                    created_by_user_id=USER_ID,
                    content_scope="full_meeting",
                    can_comment=True,
                    can_edit=True,
                )
            )
            await db.commit()

    client.portal.call(broad_grant)
    response = client.get(url, headers=auth_headers_for())
    assert response.status_code == 200, response.text
    assert response.json()["capabilities"]["can_edit"]
    assert response.json()["capabilities"]["can_comment"]


def test_canonical_diarization_comment_source_fence(client):
    from twobrain_rec_server.db.models import DiarizationSegment

    seeds, url, body = setup_comments(client)

    async def source():
        async with client.app_state["sessionmaker"]() as db:
            return (
                await db.execute(
                    select(DiarizationSegment.id, DiarizationSegment.processing_result_id)
                    .where(DiarizationSegment.meeting_id == seeds.ready_id)
                    .limit(1)
                )
            ).one()

    source_id, result_id = client.portal.call(source)
    payload = {**body, "source_segment_id": str(source_id), "processing_result_id": str(result_id)}
    created = client.post(url, headers=auth_headers(), json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["source_segment_id"] == str(source_id)
    assert client.get(
        url, headers=auth_headers(), params=dict(source_segment_ids=str(source_id))
    ).json()["source_counts"] == [dict(source_segment_id=str(source_id), count=1)]
    invalid = client.post(
        url,
        headers=auth_headers(),
        json={**payload, "request_id": str(uuid4()), "processing_result_id": str(uuid4())},
    )
    assert invalid.status_code == 422, invalid.text
    foreign_url = url.replace(str(seeds.ready_id), str(seeds.processing_id))
    foreign = client.post(
        foreign_url, headers=auth_headers(), json={**payload, "request_id": str(uuid4())}
    )
    assert foreign.status_code in (409, 422), foreign.text


def test_removed_mention_then_root_delete_leaves_notice(client):
    from dataclasses import replace

    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from tests.fixtures.cabinet_access import (
        SHARED_USER_ID,
        add_workspace_user,
        auth_headers_for,
        grant_meeting_to_user,
    )
    from tests.integration.test_meeting_comments import grant
    from tests.integration.test_rls_postgres_policies import _create_probe_role, _drop_probe_role
    from twobrain_rec_server.cabinet.access import decide_meeting_access
    from twobrain_rec_server.cabinet.comments import delete_comment
    from twobrain_rec_server.db.models import MeetingComment, ServerNotification
    from twobrain_rec_server.db.tenant_context import apply_tenant_scope

    seeds, url, body = setup_comments(client)
    grant(client, seeds.ready_id, can_comment=True)
    third = uuid4()
    add_workspace_user(client, user_id=third, device_id=uuid4())
    grant_meeting_to_user(client, seeds.ready_id, user_id=third)
    root = client.post(url, headers=auth_headers_for(), json=body)
    assert root.status_code == 201, root.text
    root = root.json()
    reply = client.post(
        url + "/" + root["id"] + "/replies",
        headers=auth_headers(),
        json=dict(
            request_id=str(uuid4()),
            body="@Third hello",
            mentions=[dict(user_id=str(third), start=0, end=6)],
        ),
    )
    assert reply.status_code == 201, reply.text
    reply_id = UUID(reply.json()["id"])
    edited = client.patch(
        url + "/" + str(reply_id),
        headers=auth_headers(),
        json=dict(expected_version=reply.json()["version"], body="Mention removed", mentions=[]),
    )
    assert edited.status_code == 200, edited.text

    async def exercise():
        database_url = client.app.state.settings.database_url
        role, password = await _create_probe_role(
            database_url, role_name="graf_review_" + uuid4().hex[:12]
        )
        engine = create_async_engine(make_url(database_url).set(username=role, password=password))
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                await apply_tenant_scope(db, replace(tenant_scope(), user_id=SHARED_USER_ID))
                meeting = await db.get(Meeting, seeds.ready_id)
                decision = await decide_meeting_access(
                    db, meeting, workspace_id=WORKSPACE_ID, viewer_user_id=SHARED_USER_ID
                )
                assert decision.can_comment and not decision.can_edit
                row = await db.get(MeetingComment, UUID(root["id"]))
                await delete_comment(db, meeting, decision, SHARED_USER_ID, row, row.version)
                await db.commit()
            async with client.app_state["sessionmaker"]() as db:
                assert await db.get(MeetingComment, reply_id) is None
                orphan = await db.scalar(
                    select(ServerNotification).where(
                        ServerNotification.source_id == reply_id,
                        ServerNotification.family == "comment",
                    )
                )
                assert orphan is None
        finally:
            await engine.dispose()
            await _drop_probe_role(database_url, role)

    client.portal.call(exercise)
