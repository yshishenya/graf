"""Commercial restrictions at real HTTP egress boundaries under the actual app role."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from tests.fixtures.cabinet import SAFE_TRANSCRIPT_TEXT, seed_cabinet_meetings
from tests.fixtures.cabinet_access import (
    SHARED_USER_ID,
    add_retained_playback_m4a,
    add_workspace_user,
    audit_events,
    auth_headers_for,
    grant_meeting_to_user,
    set_artifact_policy,
)
from tests.integration.test_rls_postgres_policies import _exact_app_role_engine
from tests.integration.test_system_admin_billing import _managed_payment
from twobrain_rec_server.billing.admin_grants import create_adjustment, revoke_adjustment
from twobrain_rec_server.cabinet import egress

pytestmark = pytest.mark.strict_rls


@pytest.fixture
def commercial(client, monkeypatch):
    seeds = seed_cabinet_meetings(client)
    add_retained_playback_m4a(client, seeds.ready_id)
    add_workspace_user(client)
    grant_meeting_to_user(client, seeds.ready_id)
    set_artifact_policy(client, seeds.ready_id, audio_download="allowed",
                        transcript_download="allowed", package_export="allowed")
    role = _exact_app_role_engine(str(client.app.state.settings.database_url))
    engine = client.portal.call(role.__aenter__)

    async def check_role():
        async with engine.connect() as connection:
            assert await connection.scalar(text("select session_user")) == "twobrain_rec_app"
            assert not await connection.scalar(text(
                "select rolsuper or rolbypassrls or rolinherit from pg_roles where rolname=session_user"))
    client.portal.call(check_role)
    monkeypatch.setattr(client.app.state, "db_sessionmaker", async_sessionmaker(engine, expire_on_commit=False))
    try:
        yield client, seeds.ready_id
    finally:
        client.portal.call(role.__aexit__, None, None, None)


async def _deny(client, feature, *, subject=None):
    now = datetime.now(UTC)
    async with client.app_state["sessionmaker"]() as db:
        await db.execute(text("set local lock_timeout='3s'"))
        row = await create_adjustment(db, workspace_id=WORKSPACE_ID, subject_user_id=subject,
            kind="deny", feature_key=feature, value=False, unit="boolean",
            starts_at=now-timedelta(seconds=1), ends_at=now+timedelta(days=1),
            source_kind="migration", source_ref=f"synthetic:{uuid4()}", reason="Synthetic egress restriction")
        await db.commit()
        return row.id


@pytest.mark.parametrize("subject", [None, USER_ID])
def test_download_deny_revoke_and_playback_independence(commercial, subject):
    client, meeting = commercial
    path = f"/api/v1/cabinet/meetings/{meeting}"
    assert client.get(path+"/downloads/audio", headers=auth_headers()).status_code == 200
    adjustment = client.portal.call(lambda: _deny(client, "audio_download", subject=subject))
    denied = client.get(path+"/downloads/audio", headers=auth_headers())
    assert denied.status_code == 409 and "content-disposition" not in denied.headers
    assert audit_events(client, meeting)[-1].policy_reason == "commercial_audio_download_denied"
    assert client.get(path+"/playback", headers=auth_headers()).status_code == 200
    assert client.get(path+"/downloads/transcript", headers=auth_headers()).status_code == 200

    async def revoke():
        async with client.app_state["sessionmaker"]() as db:
            await revoke_adjustment(db, workspace_id=WORKSPACE_ID, adjustment_id=adjustment,
                source_kind="migration", source_ref=f"synthetic:{uuid4()}", reason="Synthetic egress restore")
            await db.commit()
    client.portal.call(revoke)
    assert client.get(path+"/downloads/audio", headers=auth_headers()).status_code == 200


def test_recipient_personal_deny_is_visible_in_authenticated_shared_context(commercial):
    client, meeting = commercial
    path = f"/api/v1/cabinet/shared-meetings/{meeting}"
    params = {"workspace_id":str(WORKSPACE_ID)}
    client.portal.call(lambda: _deny(client, "content_export", subject=SHARED_USER_ID))
    capability = client.get(path+"/content-exports", headers=auth_headers_for(), params=params)
    assert capability.status_code == 200, capability.text
    assert capability.json()["transcript"]["state"] == "denied"
    assert capability.json()["formats"]["transcript"] == []
    denied = client.get(path+"/downloads/transcript", headers=auth_headers_for(), params=params)
    assert denied.status_code == 409 and SAFE_TRANSCRIPT_TEXT not in denied.text
    # Another member's restriction must not leak onto the owner.
    own = client.get(f"/api/v1/cabinet/meetings/{meeting}/downloads/transcript", headers=auth_headers())
    assert own.status_code == 200


def test_content_deny_blocks_prepared_package_and_direct_post(commercial):
    client, meeting = commercial
    path = f"/api/v1/cabinet/meetings/{meeting}"
    capability = client.get(path+"/content-exports", headers=auth_headers()).json()
    created = client.post(path+"/exports", headers=auth_headers(), json={"artifact_classes":["transcript"]})
    assert created.status_code == 202, created.text
    export_path = path+f"/exports/{created.json()['export_id']}/download"
    assert client.get(export_path, headers=auth_headers()).status_code == 200
    client.portal.call(lambda: _deny(client, "content_export"))
    for response in (
        client.get(export_path, headers=auth_headers()),
        client.post(path+"/content-exports", headers=auth_headers(), json={"content_scope":"transcript",
            "format":"txt", "processing_result_id":capability["processing_result_id"]}),
    ):
        assert response.status_code in {403,409}, response.text
        assert "content-disposition" not in response.headers and SAFE_TRANSCRIPT_TEXT not in response.text


def test_deny_during_render_wins_final_egress_check(commercial, monkeypatch):
    client, meeting = commercial
    path = f"/api/v1/cabinet/meetings/{meeting}/content-exports"
    capability = client.get(path, headers=auth_headers()).json()
    original = egress.build_export_snapshot

    async def build_and_deny(*args, **kwargs):
        snapshot = await original(*args, **kwargs)
        await _deny(client, "content_export")
        return snapshot
    monkeypatch.setattr(egress, "build_export_snapshot", build_and_deny)
    denied = client.post(path, headers=auth_headers(), json={"content_scope":"transcript",
        "format":"txt", "processing_result_id":capability["processing_result_id"]})
    assert denied.status_code == 403, denied.text
    assert "content-disposition" not in denied.headers and SAFE_TRANSCRIPT_TEXT not in denied.text
    assert audit_events(client, meeting)[-1].policy_reason == "commercial_export_denied"


def test_managed_formats_apply_to_discovery_direct_post_and_legacy_download(commercial):
    client, meeting = commercial
    now = datetime.now(UTC)

    async def gift():
        async with client.app_state["sessionmaker"]() as db:
            version, _, _, _ = await _managed_payment(db)
            await create_adjustment(db, workspace_id=WORKSPACE_ID, kind="plan_interval",
                plan_version_id=version.id, plan_mode="overlay", starts_at=now-timedelta(seconds=1),
                ends_at=now+timedelta(days=1), source_kind="migration",
                source_ref=f"synthetic:{uuid4()}", reason="Synthetic export plan")
            await db.commit()
    client.portal.call(gift)
    path = f"/api/v1/cabinet/meetings/{meeting}"
    capability = client.get(path+"/content-exports", headers=auth_headers()).json()
    assert capability["formats"]["transcript"] == ["txt","md"]
    for format, status in (("txt",200),("csv",409),("json",409)):
        exported = client.post(path+"/content-exports", headers=auth_headers(), json={
            "content_scope":"transcript", "format":format,
            "processing_result_id":capability["processing_result_id"]})
        assert exported.status_code == status, exported.text
    legacy = client.post(path+"/exports", headers=auth_headers(), json={"artifact_classes":["transcript"]})
    assert legacy.status_code == 409  # Its manifest is JSON, outside the exact plan formats.


def test_shared_outsider_sees_owner_workspace_restrictions(commercial):
    from tests.fixtures.cabinet import (
        FOREIGN_DEVICE_ID,
        FOREIGN_ORG_ID,
        FOREIGN_USER_ID,
        FOREIGN_WORKSPACE_ID,
    )

    client, meeting = commercial
    from sqlalchemy import select

    from twobrain_rec_server.cabinet.access import hash_invitation_address
    from twobrain_rec_server.db.models import ExternalIdentity, MeetingShareGrant

    grant_meeting_to_user(client, meeting, user_id=FOREIGN_USER_ID)

    async def accepted_invitation():
        async with client.app_state["sessionmaker"]() as db:
            email = "synthetic-recipient@example.invalid"
            db.add(ExternalIdentity(user_id=FOREIGN_USER_ID, provider="email",
                provider_subject=email, email=email, is_verified=True, is_active=True))
            grant = await db.scalar(select(MeetingShareGrant).where(
                MeetingShareGrant.meeting_id == meeting, MeetingShareGrant.audience_id == FOREIGN_USER_ID))
            grant.metadata_json = {"source":"accepted_external_invitation",
                "recipient_address_hash":hash_invitation_address(email)}
            await db.commit()
    client.portal.call(accepted_invitation)
    headers = auth_headers_for(user_id=FOREIGN_USER_ID, device_id=FOREIGN_DEVICE_ID,
        workspace_id=FOREIGN_WORKSPACE_ID, organization_id=FOREIGN_ORG_ID)
    path = f"/api/v1/cabinet/shared-meetings/{meeting}/downloads/transcript"
    params = {"workspace_id":str(WORKSPACE_ID)}
    assert client.get(path, headers=headers, params=params).status_code == 200
    client.portal.call(lambda: _deny(client, "content_export"))
    denied = client.get(path, headers=headers, params=params)
    assert denied.status_code == 409 and SAFE_TRANSCRIPT_TEXT not in denied.text


def test_egress_workspace_fence_serializes_assignment_before_bytes(commercial):
    import asyncio

    from twobrain_rec_server.db.tenant_context import TenantDatabaseContext, apply_tenant_context

    client, _ = commercial

    async def check():
        async with client.app.state.db_sessionmaker() as db:
            await apply_tenant_context(db, TenantDatabaseContext(
                organization_id=uuid4(), workspace_id=WORKSPACE_ID, user_id=USER_ID))
            await egress.lock_commercial_workspace(db, WORKSPACE_ID)
            task = asyncio.create_task(_deny(client, "audio_download"))
            try:
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(asyncio.shield(task), timeout=0.2)
                await db.commit()
                assert await asyncio.wait_for(task, timeout=5)
            finally:
                await db.rollback()
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
    client.portal.call(check)


def test_scheduled_restriction_starting_during_audio_materialization_blocks_bytes(commercial, monkeypatch):
    client, meeting = commercial
    now = datetime.now(UTC)

    async def schedule():
        async with client.app_state["sessionmaker"]() as db:
            await create_adjustment(db, workspace_id=WORKSPACE_ID,
                kind="deny", feature_key="audio_download", value=False, unit="boolean",
                starts_at=now+timedelta(minutes=1), ends_at=now+timedelta(days=1),
                source_kind="migration", source_ref=f"synthetic:{uuid4()}", reason="Synthetic scheduled restriction")
            await db.commit()
    client.portal.call(schedule)
    original = egress._materialize_storage_stream

    class AfterRestrictionStart(datetime):
        @classmethod
        def now(cls, tz=None):
            return (now+timedelta(minutes=2)).astimezone(tz)

    async def materialize(*args, **kwargs):
        body = await original(*args, **kwargs)
        monkeypatch.setattr(egress, "datetime", AfterRestrictionStart)
        return body
    monkeypatch.setattr(egress, "_materialize_storage_stream", materialize)
    denied = client.get(f"/api/v1/cabinet/meetings/{meeting}/downloads/audio", headers=auth_headers())
    assert denied.status_code == 409 and "content-disposition" not in denied.headers
    assert audit_events(client, meeting)[-1].policy_reason == "commercial_audio_download_denied"


@pytest.mark.parametrize("subject", [None, USER_ID])
def test_sharing_deny_blocks_new_access_but_preserves_revoke(commercial, subject):
    client, meeting = commercial
    path = f"/api/v1/cabinet/meetings/{meeting}"
    payload = {"audience_type":"user", "audience_id":str(SHARED_USER_ID),
        "content_scope":"full_meeting", "can_download":True, "can_export":True}
    from sqlalchemy import select

    from twobrain_rec_server.db.models import MeetingShareGrant

    async def prior_grant():
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(select(MeetingShareGrant.id).where(MeetingShareGrant.meeting_id == meeting))
    grant = str(client.portal.call(prior_grant))
    assert client.post(path+f"/shares/{grant}/rotate", headers=auth_headers()).status_code == 200
    client.portal.call(lambda: _deny(client, "meeting_sharing", subject=subject))
    state = client.get(path+"/access", headers=auth_headers())
    assert state.status_code == 200, state.text
    assert state.json()["share"]["capability_state"] == "policy_blocked"
    assert state.json()["share"]["active_grants"]
    for response in (
        client.post(path+"/shares", headers=auth_headers(), json=payload),
        client.post(path+f"/shares/{grant}/rotate", headers=auth_headers()),
    ):
        assert response.status_code == 403 and response.json()["code"] == "commercial_sharing_denied"
        assert "share_url" not in response.text
    assert audit_events(client, meeting)[-1].policy_reason == "commercial_sharing_denied"
    page = client.get(f"/meetings/{meeting}/share", headers=auth_headers())
    assert page.status_code == 200 and "Новые приглашения недоступны" in page.text
    assert "data-share-recipient-input disabled" in page.text
    assert f'data-share-revoke-url="{path}/shares/{grant}"' in page.text
    # No silent rewrite of previously admitted grants; owner can still revoke them.
    assert client.get(path+"/downloads/transcript", headers=auth_headers_for()).status_code == 200
    assert client.delete(path+f"/shares/{grant}", headers=auth_headers()).status_code == 204


def test_sharing_deny_prevents_external_invitation_and_dispatch(commercial, monkeypatch, tmp_path):
    from cryptography.fernet import Fernet
    from sqlalchemy import func, select

    from twobrain_rec_server.api import cabinet
    from twobrain_rec_server.db.models import MeetingShareInvitation

    client, meeting = commercial
    key_file = tmp_path / "synthetic-invitation-key"
    key_file.write_bytes(Fernet.generate_key())
    monkeypatch.setattr(client.app.state.settings, "credential_encryption_key_file", key_file)
    monkeypatch.setattr(client.app.state.settings, "share_external_invitations_enabled", True)

    async def unexpected_dispatch(**_kwargs):
        raise AssertionError("denied invitation must not dispatch")
    monkeypatch.setattr(cabinet, "start_invitation_delivery_workflow", unexpected_dispatch)
    client.portal.call(lambda: _deny(client, "meeting_sharing"))
    response = client.post(f"/api/v1/cabinet/meetings/{meeting}/share-invitations", headers=auth_headers(),
        json={"address":"synthetic@example.invalid", "content_scope":"full_meeting", "can_download":True, "can_export":True})
    assert response.status_code == 403 and response.json()["code"] == "commercial_sharing_denied"

    async def count():
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(select(func.count()).select_from(MeetingShareInvitation))
    assert client.portal.call(count) == 0


def test_internal_invitation_search_create_duplicate_and_recipient_access(commercial):
    from sqlalchemy import select

    from twobrain_rec_server.db.models import ExternalIdentity, MeetingShareGrant

    client, meeting = commercial
    path = f"/api/v1/cabinet/meetings/{meeting}"

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            db.add(ExternalIdentity(user_id=SHARED_USER_ID, provider="synthetic",
                provider_subject="share-lookup", email="lookup@example.invalid", is_verified=True))
            grant = await db.scalar(select(MeetingShareGrant.id).where(MeetingShareGrant.meeting_id == meeting))
            await db.commit()
            return grant
    prior = client.portal.call(seed)
    assert client.delete(path+f"/shares/{prior}", headers=auth_headers()).status_code == 204
    search = client.get(path+"/share-recipients", headers=auth_headers(), params={"query":"lookup@example.invalid"})
    assert search.status_code == 200, search.text
    assert [item["user_id"] for item in search.json()["items"]] == [str(SHARED_USER_ID)]
    assert "lookup@example.invalid" not in search.text
    payload = {"audience_type":"user", "audience_id":str(SHARED_USER_ID), "content_scope":"full_meeting"}
    created = client.post(path+"/shares", headers=auth_headers(), json=payload)
    assert created.status_code == 201, created.text
    duplicate = client.post(path+"/shares", headers=auth_headers(), json=payload)
    assert duplicate.status_code == 409 and duplicate.json()["code"] == "grantee_already_has_access"
    resolved = client.get(created.json()["share_url"], headers=auth_headers_for(), follow_redirects=False)
    assert resolved.status_code == 302, resolved.text
    assert client.get(path, headers=auth_headers_for()).status_code == 200


def test_share_membership_lookup_is_scoped_and_does_not_open_rls(commercial):
    from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID
    from twobrain_rec_server.db.tenant_context import TenantDatabaseContext, apply_tenant_context

    client, meeting = commercial

    async def probe():
        async with client.app.state.db_sessionmaker() as db:
            async def check(*, actor=USER_ID, workspace=WORKSPACE_ID, context="request", target=SHARED_USER_ID, mid=meeting):
                await apply_tenant_context(db, TenantDatabaseContext(organization_id=ORG_ID,
                    workspace_id=workspace, user_id=actor, device_id=DEVICE_ID, context_kind=context))
                return await db.scalar(text("select rec_share_recipient_is_member(:m,:u)"), {"m":mid,"u":target})
            assert await check() is True
            assert await db.scalar(text("select count(*) from workspace_memberships where user_id=:u"),
                {"u":SHARED_USER_ID}) == 0
            assert await check(actor=SHARED_USER_ID, target=USER_ID) is False
            assert await check(workspace=uuid4()) is False
            assert await check(mid=uuid4()) is False
            assert await check(target=uuid4()) is False
            assert await check(context="worker") is False
            await db.execute(text("select set_config('app.context_kind','',true)"))
            assert await db.scalar(text("select rec_share_recipient_is_member(:m,:u)"),
                {"m":meeting,"u":SHARED_USER_ID}) is False
    client.portal.call(probe)


@pytest.mark.parametrize("blocked", ["membership", "identity", "organization", "deletion"])
def test_share_lookup_excludes_inactive_or_unrelated_recipients(commercial, blocked):
    client, meeting = commercial
    async def mutate():
        async with client.app_state["sessionmaker"]() as db:
            if blocked == "membership":
                await db.execute(text("update workspace_memberships set status='removed' where user_id=:u"), {"u":SHARED_USER_ID})
            elif blocked == "identity":
                await db.execute(text("update user_identities set status='disabled' where id=:u"), {"u":SHARED_USER_ID})
            elif blocked == "organization":
                other_org = uuid4()
                await db.execute(text("insert into organizations(id,slug,name) values (:id,:slug,'Synthetic')"),
                    {"id":other_org,"slug":str(other_org)})
                await db.execute(text("update user_identities set organization_id=:org where id=:u"),
                    {"u":SHARED_USER_ID,"org":other_org})
            else:
                await db.execute(text("update meetings set deletion_state='requested' where id=:m"), {"m":meeting})
            await db.commit()
    client.portal.call(mutate)
    path = f"/api/v1/cabinet/meetings/{meeting}"
    found = client.get(path+"/share-recipients", headers=auth_headers(), params={"query":"Shared"})
    assert found.status_code == 404 if blocked == "deletion" else found.status_code == 200 and not found.json()["items"]
    created = client.post(path+"/shares", headers=auth_headers(), json={"audience_type":"user",
        "audience_id":str(SHARED_USER_ID),"content_scope":"full_meeting"})
    assert created.status_code == 404, created.text


@pytest.mark.parametrize("subject", [None, USER_ID])
def test_archive_deny_preserves_upload_and_explicit_no_archive_processing(commercial, subject):
    from uuid import UUID

    from tests.fakes.fake_temporal import FakeTemporalClient
    from tests.integration.test_finalize_integrity import _create_session_with_parts
    from twobrain_rec_server.db.models import UploadSession

    client, _meeting = commercial
    session_id, tracks = _create_session_with_parts(client)
    client.portal.call(lambda: _deny(client, "audio_archive", subject=subject))
    client.app.state.settings.processing_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()
    path = f"/api/v1/upload-sessions/{session_id}/finalize"
    payload = {"manifest_sha256":tracks[0]["sha256"], "tracks":tracks, "archive_audio":True}
    objects_before = dict(client.app_state["storage"].objects)
    rejected = client.post(path, headers=auth_headers(), json=payload)
    assert rejected.status_code == 403 and rejected.json()["code"] == "commercial_audio_archive_denied"
    assert client.app_state["storage"].objects == objects_before
    accepted = client.post(path, headers=auth_headers(), json=payload | {"archive_audio":False})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["upload_session"]["status"] == "finalized"
    async def choice():
        async with client.app_state["sessionmaker"]() as db:
            return (await db.get(UploadSession, UUID(session_id))).archive_audio
    assert client.portal.call(choice) is False

    async def retry_choice():
        from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID
        from twobrain_rec_server.db.tenant_context import (
            TenantDatabaseContext,
            apply_tenant_context,
        )
        from twobrain_rec_server.processing.pickup import _archive_audio_for_meeting
        async with client.app.state.db_sessionmaker() as db:
            await apply_tenant_context(db, TenantDatabaseContext(organization_id=ORG_ID,
                workspace_id=WORKSPACE_ID, user_id=USER_ID, device_id=DEVICE_ID))
            # A later deny/override cannot rewrite either previously admitted choice.
            assert await _archive_audio_for_meeting(db, workspace_id=WORKSPACE_ID,
                meeting_id=_meeting, requested=False) is True
            assert await _archive_audio_for_meeting(db, workspace_id=WORKSPACE_ID,
                meeting_id=UUID(accepted.json()["meeting"]["meeting_id"]), requested=True) is False
    client.portal.call(retry_choice)


def test_manual_archive_deny_precedes_storage_and_keeps_explicit_choice(commercial, monkeypatch):
    from tests.fakes.fake_temporal import FakeTemporalClient
    from tests.fixtures.artifacts import deterministic_wav_bytes
    from twobrain_rec_server.api import ingest

    client, _meeting = commercial
    client.portal.call(lambda: _deny(client, "audio_archive"))
    client.app.state.settings.processing_enabled = True
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()
    streams = []
    original = ingest.read_manual_media_upload_body
    async def read(*args, **kwargs):
        upload = await original(*args, **kwargs)
        streams.append(upload.file.stream)
        return upload
    monkeypatch.setattr(ingest, "read_manual_media_upload_body", read)
    objects_before = dict(client.app_state["storage"].objects)
    data = {"duration_seconds":"60", "local_recording_id":"synthetic-denied-archive", "archive_audio":"true"}
    files = {"file":("synthetic.wav", deterministic_wav_bytes(128), "audio/wav")}
    denied = client.post("/api/v1/media-uploads", headers=auth_headers(), data=data, files=files)
    assert denied.status_code == 403 and denied.json()["code"] == "commercial_audio_archive_denied"
    assert client.app_state["storage"].objects == objects_before
    assert streams[0].closed
    accepted = client.post("/api/v1/media-uploads", headers=auth_headers(), data=data | {"archive_audio":"false"}, files=files)
    assert accepted.status_code == 202, accepted.text
    assert streams[1].closed


def test_archive_restriction_during_materialization_wins_admission(commercial, monkeypatch):
    from tests.integration.test_finalize_integrity import _create_session_with_parts
    from twobrain_rec_server.ingest import finalize

    client, _meeting = commercial
    session_id, tracks = _create_session_with_parts(client)
    original = finalize._materialize_track_object
    restricted = False
    async def materialize(*args, **kwargs):
        nonlocal restricted
        result = await original(*args, **kwargs)
        if not restricted:
            restricted = True
            await _deny(client, "audio_archive")
        return result
    monkeypatch.setattr(finalize, "_materialize_track_object", materialize)
    denied = client.post(f"/api/v1/upload-sessions/{session_id}/finalize", headers=auth_headers(),
        json={"manifest_sha256":tracks[0]["sha256"], "tracks":tracks,"archive_audio":True})
    assert restricted
    assert denied.status_code == 403 and denied.json()["code"] == "commercial_audio_archive_denied"


@pytest.mark.parametrize("action", ["admission", "dispatch_failure", "closed_workflow"])
def test_processing_admission_waits_for_workspace_before_locking_meeting(commercial, action):
    import asyncio

    from sqlalchemy import select

    from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID
    from twobrain_rec_server.db.models import Meeting, ProcessingWorkflow, Workspace
    from twobrain_rec_server.db.tenant_context import TenantDatabaseContext, apply_tenant_context
    from twobrain_rec_server.processing import store

    client, meeting = commercial
    async def race():
        async with client.app_state["sessionmaker"]() as writer:
            await writer.execute(text("set local lock_timeout='1s'"))
            await writer.scalar(select(Workspace.id).where(Workspace.id == WORKSPACE_ID).with_for_update())
            async def admission():
                async with client.app.state.db_sessionmaker() as worker:
                    await apply_tenant_context(worker, TenantDatabaseContext(organization_id=ORG_ID,
                        workspace_id=WORKSPACE_ID,user_id=USER_ID,device_id=DEVICE_ID,context_kind="worker"))
                    if action == "admission":
                        result = await store.create_processing_attempt(worker, workspace_id=WORKSPACE_ID,
                            meeting_id=meeting,owner_user_id=USER_ID,allow_processed=True)
                    else:
                        workflow = await worker.scalar(select(ProcessingWorkflow).where(
                            ProcessingWorkflow.meeting_id == meeting))
                        assert workflow is not None
                        if action == "dispatch_failure":
                            result = await store.fail_processing_attempt_dispatch(worker, workflow_id=workflow.id)
                        else:
                            result = await store.reconcile_closed_processing_workflow_result(worker, workflow=workflow)
                    await worker.rollback()
                    return result
            task = asyncio.create_task(admission())
            try:
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(asyncio.shield(task),timeout=0.15)
                # The waiting processing request must not own Meeting already.
                assert await writer.scalar(select(Meeting.id).where(Meeting.id == meeting).with_for_update()) == meeting
                assert await writer.scalar(select(ProcessingWorkflow.id).where(
                    ProcessingWorkflow.meeting_id == meeting).with_for_update()) is not None
                await writer.commit()
                assert await asyncio.wait_for(task,timeout=3) is not None
            finally:
                await writer.rollback()
                if not task.done():
                    task.cancel()
                await asyncio.gather(task,return_exceptions=True)
    client.portal.call(race)
