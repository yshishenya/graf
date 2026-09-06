"""Synthetic content crosses the separate role only after durable authorization."""

from dataclasses import replace
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.integration import test_system_admin_security as security
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    MediaRevision,
    MediaScribeJob,
    ProcessingResult,
    ProcessingWorkflow,
)
from twobrain_rec_server.db.session import create_system_admin_database
from twobrain_rec_server.db.tenant_context import SystemDatabaseContext
from twobrain_rec_server.system_admin.audit import authorize_access, create_case_context
from twobrain_rec_server.system_admin.queries import meeting_content

system_database = security.system_database
pytestmark = pytest.mark.strict_rls


async def seed_content(db, url):
    meeting = await db["owner"].fetchrow("select id,workspace_id from meetings order by id limit 1")
    engine = create_async_engine(url)
    revision, workflow, job, result = (uuid4() for _ in range(4))
    common = {"meeting_id": meeting["id"], "workspace_id": meeting["workspace_id"]}
    try:
        async with async_sessionmaker(engine)() as session:
            session.add(MediaRevision(id=revision, **common, local_media_revision_id=str(revision),
                                      status="accepted", immutable=True))
            await session.flush()
            session.add(ProcessingWorkflow(id=workflow, **common, media_revision_id=revision,
                                           workflow_id=str(workflow), status="processed"))
            await session.flush()
            session.add(MediaScribeJob(id=job, **common, media_revision_id=revision, processing_workflow_id=workflow))
            await session.flush()
            session.add(ProcessingResult(id=result, **common, media_revision_id=revision,
                processing_workflow_id=workflow, mediascribe_job_id=job, status="imported",
                transcript_status="available", diarization_status="available", segment_count=105,
                diarization_segment_count=105, downloads_json={"private": "synthetic-storage-secret"}))
            await session.flush()
            session.add_all([DiarizationSegment(id=uuid4(), **common, processing_result_id=result,
                sequence=i, start_seconds=i, end_seconds=i+1, speaker_label="speaker_1",
                text=f"Synthetic <script>throw Error('unsafe')</script> {i}", source_role="system") for i in range(105)])
            await session.commit()
    finally:
        await engine.dispose()
    return meeting["id"], revision, result


def context_for(db, meeting):
    return SystemDatabaseContext(actor_id=db["actor"], admin_session_id=db["session"],
        session_token_hash=db["token_hash"], permission="content.read", target_type="meeting", target_id=meeting)


@pytest.mark.asyncio
async def test_content_requires_role_case_committed_audit_and_live_target(system_database, postgres_seeded_database_url):
    db = system_database
    meeting, _, result = await seed_content(db, postgres_seeded_database_url)
    engine, sessions = create_system_admin_database(database_url=db["url"])
    context = context_for(db, meeting)
    try:
        case = await create_case_context(sessions, context, reason="Synthetic support investigation")
        context = replace(context, case_context_id=case)
        with pytest.raises(PermissionError):
            await meeting_content(sessions, context)
        assert await db["owner"].fetchval("select count(*) from system_control.audit_events where result='denied'") == 1
        await db["owner"].execute("update system_control.role_assignments set role='superadmin'")
        with pytest.raises(PermissionError):
            await meeting_content(sessions, replace(context, case_context_id=None))
        first = await meeting_content(sessions, context)
        assert first["result_id"] == result
        assert len(first["items"]) == 100 and first["next_cursor"] == 99
        assert first["meeting"]["title"] == "Synthetic private title"
        second = await meeting_content(sessions, context, result_id=result, after=99)
        assert len(second["items"]) == 5 and second["next_cursor"] is None
        assert (await meeting_content(sessions, context, search="%"))["items"] == []
        with pytest.raises(ValueError, match="Результат изменился"):
            await meeting_content(sessions, context, result_id=uuid4())
        await db["owner"].execute("update meetings set deletion_state='requested' where id=$1", meeting)
        with pytest.raises(PermissionError):
            await meeting_content(sessions, context)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_content_rls_blocks_forged_context_and_revocation_even_with_permissive_policy(system_database, postgres_seeded_database_url):
    db = system_database
    meeting, _, _ = await seed_content(db, postgres_seeded_database_url)
    await db["owner"].execute("update system_control.role_assignments set role='superadmin'")
    engine, sessions = create_system_admin_database(database_url=db["url"])
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    context = context_for(db, meeting)
    try:
        case = await create_case_context(sessions, context, reason="Synthetic RLS check")
        context = await authorize_access(sessions, replace(context, case_context_id=case))
        await db["owner"].execute("create policy f254_content_probe on diarization_segments using(true)")
        async with conn.transaction():
            await security._context(conn, db)
            assert await conn.fetch("select text from diarization_segments") == []
            await security._context(conn, db, **{"app.system_permission":"content.read",
                "app.system_target_type":"meeting", "app.system_target_id":str(meeting),
                "app.system_case_context_id":str(case), "app.system_audit_event_id":str(context.audit_event_id)})
            assert len(await conn.fetch("select text from diarization_segments")) == 105
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                async with conn.transaction():
                    await conn.fetch("select downloads_json from processing_results")
            await db["owner"].execute("update system_control.sessions set revoked_at=now()")
            assert await conn.fetch("select text from diarization_segments") == []
    finally:
        await db["owner"].execute("drop policy if exists f254_content_probe on diarization_segments")
        await conn.close()
        await engine.dispose()
