"""T015: API links, auditable permission changes and cross-organization sharing."""

from contextlib import aclosing
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.cabinet_access import SHARED_USER_ID
from tests.integration.test_meeting_comments import grant, setup_comments
from twobrain_rec_server.db.models import MeetingComment, MeetingEgressAuditEvent, MeetingShareGrant


def test_direct_reply_link_includes_target_without_losing_sibling_pagination(client):
    seeds, url, body = setup_comments(client)
    root = client.post(url, headers=auth_headers(), json=body).json()
    reply_ids = [uuid4() for _ in range(120)]

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            for i, identifier in enumerate(reply_ids):
                db.add(
                    MeetingComment(
                        id=identifier,
                        workspace_id=WORKSPACE_ID,
                        meeting_id=seeds.ready_id,
                        author_user_id=USER_ID,
                        media_revision_id=UUID(body["media_revision_id"]),
                        parent_id=UUID(root["id"]),
                        request_id=uuid4(),
                        request_hash="0" * 64,
                        start_ms=1000,
                        body=f"Synthetic reply {i}",
                        version=1,
                        created_at=datetime.now(UTC) + timedelta(seconds=i),
                    )
                )
            await db.commit()

    client.portal.call(seed)
    response = client.get(url + "/" + str(reply_ids[110]), headers=auth_headers())
    assert response.status_code == 200, response.text
    linked = response.json()
    assert linked["id"] == root["id"]
    assert len(linked["replies"]) <= 50
    assert str(reply_ids[110]) in {reply["id"] for reply in linked["replies"]}
    seen = {reply["id"] for reply in linked["replies"]}
    cursor = linked["next_reply_cursor"]
    while cursor:
        page = client.get(
            url + "/" + root["id"] + "/replies", headers=auth_headers(), params={"cursor": cursor}
        ).json()
        seen.update(reply["id"] for reply in page["items"])
        cursor = page["next_cursor"]
    assert seen == {str(identifier) for identifier in reply_ids}
    ordinary = client.get(url + "/" + root["id"], headers=auth_headers()).json()
    assert [item["id"] for item in ordinary["replies"]] == [str(item) for item in reply_ids[:50]]


def test_permission_update_records_audit_and_rolls_back_if_audit_fails(client, monkeypatch):
    from twobrain_rec_server.api.problems import ProblemDetail
    from twobrain_rec_server.cabinet import egress

    seeds, _url, _body = setup_comments(client)
    result = grant(client, seeds.ready_id)
    grant_id = result["grant"]["grant_id"]
    url = f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares/{grant_id}/permissions"
    allowed = client.patch(
        url, headers=auth_headers(), json={"can_comment": True, "can_edit": False}
    )
    assert allowed.status_code == 200, allowed.text

    async def inspect():
        async with client.app_state["sessionmaker"]() as db:
            events = list(
                await db.scalars(
                    select(MeetingEgressAuditEvent).where(
                        MeetingEgressAuditEvent.meeting_id == seeds.ready_id,
                        MeetingEgressAuditEvent.policy_reason == "comment_permissions_updated",
                    )
                )
            )
            assert len(events) == 1
            event = events[0]
            assert event.event_type == "share_updated" and event.outcome == "allowed"
            assert event.actor_user_id == USER_ID and event.device_id == DEVICE_ID
            assert event.metadata_json == {"share_grant_id": grant_id}
            row = await db.get(MeetingShareGrant, UUID(grant_id))
            assert row.can_comment and not row.can_edit

    client.portal.call(inspect)

    async def failed_audit(db, **_kwargs):
        await db.flush()  # Include a flushed permissions write in the rollback proof.
        raise ProblemDetail(status=503, code="audit_unavailable", title="Audit unavailable")

    monkeypatch.setattr(egress, "record_egress_audit_event", failed_audit)
    denied = client.patch(url, headers=auth_headers(), json={"can_comment": True, "can_edit": True})
    assert denied.status_code == 503
    client.portal.call(inspect)


def test_cross_organization_share_dependency_validates_actor_before_owner_identity_scope(client):
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from tests.integration.test_rls_postgres_policies import _create_probe_role, _drop_probe_role
    from twobrain_rec_server.api.cabinet import get_share_operation_db_session
    from twobrain_rec_server.api.problems import ProblemDetail
    from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
    from twobrain_rec_server.cabinet.access import (
        create_scoped_share_grant,
        hash_invitation_address,
        search_share_recipients,
    )
    from twobrain_rec_server.db.models import (
        ExternalIdentity,
        Meeting,
        Organization,
        RegisteredDevice,
        UserIdentity,
        Workspace,
        WorkspaceMembership,
    )

    seeds, _url, _body = setup_comments(client)
    organization, workspace, editor, device = (uuid4() for _ in range(4))

    async def exercise():
        database_url = client.app.state.settings.database_url
        async with client.app_state["sessionmaker"]() as db:
            db.add(Organization(id=organization, slug=str(organization), name="Synthetic external"))
            await db.flush()
            db.add_all(
                [
                    Workspace(
                        id=workspace,
                        organization_id=organization,
                        slug=str(workspace),
                        name="Synthetic external",
                    ),
                    UserIdentity(
                        id=editor,
                        organization_id=organization,
                        external_subject=str(editor),
                        display_name="External editor",
                        status="active",
                    ),
                ]
            )
            await db.flush()
            db.add_all(
                [
                    WorkspaceMembership(
                        workspace_id=workspace, user_id=editor, role="owner", status="active"
                    ),
                    RegisteredDevice(
                        id=device,
                        workspace_id=workspace,
                        user_id=editor,
                        device_public_id=str(device),
                        status="active",
                    ),
                    ExternalIdentity(
                        user_id=editor,
                        provider="test",
                        provider_subject=str(editor),
                        email="api-editor@example.test",
                        is_active=True,
                        is_verified=True,
                    ),
                    ExternalIdentity(
                        user_id=SHARED_USER_ID,
                        provider="test",
                        provider_subject=str(SHARED_USER_ID),
                        email="api-recipient@example.test",
                        is_active=True,
                        is_verified=True,
                    ),
                    MeetingShareGrant(
                        workspace_id=WORKSPACE_ID,
                        meeting_id=seeds.ready_id,
                        grant_type="user",
                        grantee_user_id=editor,
                        audience_type="user",
                        audience_id=editor,
                        created_by_user_id=USER_ID,
                        content_scope="full_meeting",
                        can_comment=True,
                        can_edit=True,
                        metadata_json={
                            "source": "accepted_external_invitation",
                            "recipient_address_hash": hash_invitation_address(
                                "api-editor@example.test"
                            ),
                        },
                    ),
                ]
            )
            await db.commit()
        role, password = await _create_probe_role(
            database_url, role_name="graf_api_" + uuid4().hex[:12]
        )
        engine = create_async_engine(make_url(database_url).set(username=role, password=password))
        factory = async_sessionmaker(engine, expire_on_commit=False)
        request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(db_sessionmaker=factory))
        )
        scope = TenantScope(
            organization_id=organization, workspace_id=workspace, user_id=editor, device_id=device
        )
        principal = AuthenticatedPrincipal(
            user_id=editor,
            organization_id=organization,
            workspace_ids=frozenset([workspace]),
            subject=str(editor),
        )
        try:
            dependency = get_share_operation_db_session(
                request, seeds.ready_id, WORKSPACE_ID, scope, principal
            )
            async with aclosing(dependency):
                db = await anext(dependency)
                assert await db.scalar(text("select rec_current_organization_id()")) == ORG_ID
                for marker in ("", str(uuid4())):
                    await db.execute(
                        text("select set_config('app.comment_editor_meeting_id', :marker, true)"),
                        {"marker": marker},
                    )
                    assert not await db.scalar(
                        text("select rec_comment_editor_member_visible(:target)"),
                        {"target": SHARED_USER_ID},
                    )
                await db.execute(
                    text("select set_config('app.comment_editor_meeting_id', :meeting, true)"),
                    {"meeting": str(seeds.ready_id)},
                )
                assert await db.get(UserIdentity, SHARED_USER_ID) is not None
                meeting = await db.get(Meeting, seeds.ready_id)
                candidates = await search_share_recipients(
                    db,
                    workspace_id=WORKSPACE_ID,
                    meeting_id=meeting.id,
                    viewer_user_id=editor,
                    device_id=device,
                    query="api-recipient@example.test",
                )
                assert SHARED_USER_ID in {item.user_id for item in candidates}
                created, _token = await create_scoped_share_grant(
                    db,
                    workspace_id=WORKSPACE_ID,
                    meeting=meeting,
                    actor_user_id=editor,
                    device_id=device,
                    audience_type="user",
                    audience_id=SHARED_USER_ID,
                    content_scope="full_meeting",
                    can_download=False,
                    can_export=False,
                    can_comment=True,
                    can_edit=False,
                    expires_at=None,
                    broader_audience_enabled=True,
                )
                assert created.grantee_user_id == SHARED_USER_ID and created.can_comment
                await db.commit()
                assert await db.scalar(
                    text("select current_setting('app.comment_editor_meeting_id', true)")
                ) in (None, "")
                assert not await db.scalar(
                    text("select rec_comment_editor_member_visible(:target)"),
                    {"target": SHARED_USER_ID},
                )
            async with client.app_state["sessionmaker"]() as db:
                editor_grant = await db.scalar(
                    select(MeetingShareGrant).where(
                        MeetingShareGrant.meeting_id == seeds.ready_id,
                        MeetingShareGrant.grantee_user_id == editor,
                    )
                )
                editor_grant.can_edit = False
                await db.commit()
            downgraded = get_share_operation_db_session(
                request, seeds.ready_id, WORKSPACE_ID, scope, principal
            )
            async with aclosing(downgraded):
                db = await anext(downgraded)
                # Even a stale/forged marker cannot replace a live editor grant.
                await db.execute(
                    text(
                        "select set_config('app.comment_editor_meeting_id', :meeting, true), "
                        "set_config('app.comment_editor_user_id', :actor, true)"
                    ),
                    {"meeting": str(seeds.ready_id), "actor": str(editor)},
                )
                assert not await db.scalar(
                    text("select rec_comment_editor_member_visible(:target)"),
                    {"target": SHARED_USER_ID},
                )
            async with client.app_state["sessionmaker"]() as db:
                identity = await db.scalar(
                    select(ExternalIdentity).where(ExternalIdentity.user_id == editor)
                )
                identity.is_verified = False
                await db.commit()
            denied = get_share_operation_db_session(
                request, seeds.ready_id, WORKSPACE_ID, scope, principal
            )
            async with aclosing(denied):
                with pytest.raises(ProblemDetail) as failure:
                    await anext(denied)
                assert failure.value.status == 404
        finally:
            await engine.dispose()
            await _drop_probe_role(database_url, role)

    client.portal.call(exercise)


@pytest.mark.parametrize("actor_role", ["owner", "editor"])
def test_same_workspace_sharing_reads_recipients_under_restricted_rls(client, actor_role):
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from tests.fixtures.cabinet_access import add_workspace_user
    from tests.integration.test_rls_postgres_policies import _create_probe_role, _drop_probe_role
    from twobrain_rec_server.api.cabinet import get_share_operation_db_session
    from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
    from twobrain_rec_server.cabinet.access import (
        create_scoped_share_grant,
        search_share_recipients,
    )
    from twobrain_rec_server.db.models import ExternalIdentity, Meeting

    seeds, _url, _body = setup_comments(client)
    actor, device = (USER_ID, DEVICE_ID) if actor_role == "owner" else (uuid4(), uuid4())
    if actor_role == "editor":
        add_workspace_user(client, user_id=actor, device_id=device, display_name="Internal editor")

    async def exercise():
        database_url = client.app.state.settings.database_url
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                ExternalIdentity(
                    user_id=SHARED_USER_ID,
                    provider="test",
                    provider_subject=str(SHARED_USER_ID),
                    email="internal-recipient@example.test",
                    is_active=True,
                    is_verified=True,
                )
            )
            if actor_role == "editor":
                db.add(
                    MeetingShareGrant(
                        workspace_id=WORKSPACE_ID,
                        meeting_id=seeds.ready_id,
                        grant_type="user",
                        grantee_user_id=actor,
                        audience_type="user",
                        audience_id=actor,
                        created_by_user_id=USER_ID,
                        content_scope="full_meeting",
                        can_comment=True,
                        can_edit=True,
                    )
                )
            await db.commit()
        role, password = await _create_probe_role(
            database_url, role_name="graf_api_" + uuid4().hex[:12]
        )
        engine = create_async_engine(make_url(database_url).set(username=role, password=password))
        factory = async_sessionmaker(engine, expire_on_commit=False)
        request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(db_sessionmaker=factory))
        )
        scope = TenantScope(
            organization_id=ORG_ID, workspace_id=WORKSPACE_ID, user_id=actor, device_id=device
        )
        principal = AuthenticatedPrincipal(
            user_id=actor,
            organization_id=ORG_ID,
            workspace_ids=frozenset([WORKSPACE_ID]),
            subject=str(actor),
        )
        try:
            dependency = get_share_operation_db_session(
                request, seeds.ready_id, WORKSPACE_ID, scope, principal
            )
            async with aclosing(dependency):
                db = await anext(dependency)
                candidates = await search_share_recipients(
                    db,
                    workspace_id=WORKSPACE_ID,
                    meeting_id=seeds.ready_id,
                    viewer_user_id=actor,
                    device_id=device,
                    query="internal-recipient@example.test",
                )
                assert SHARED_USER_ID in {item.user_id for item in candidates}
                meeting = await db.get(Meeting, seeds.ready_id)
                created, _token = await create_scoped_share_grant(
                    db,
                    workspace_id=WORKSPACE_ID,
                    meeting=meeting,
                    actor_user_id=actor,
                    device_id=device,
                    audience_type="user",
                    audience_id=SHARED_USER_ID,
                    content_scope="full_meeting",
                    can_download=False,
                    can_export=False,
                    can_comment=True,
                    can_edit=False,
                    expires_at=None,
                    broader_audience_enabled=True,
                )
                assert created.grantee_user_id == SHARED_USER_ID and created.can_comment
                await db.commit()
        finally:
            await engine.dispose()
            await _drop_probe_role(database_url, role)

    client.portal.call(exercise)
