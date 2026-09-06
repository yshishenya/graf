"""Bounded SQL projections. Content never enters metadata queries."""

from dataclasses import replace
from uuid import UUID

from sqlalchemy import text

from twobrain_rec_server.db.tenant_context import apply_system_context


async def meetings(sessions, context, *, after: UUID | None = None):
    async with sessions() as session:
        await apply_system_context(session, replace(context, permission="meetings.metadata"))
        rows = await session.execute(text("""select id,workspace_id,created_by_user_id,status,
            processing_status,deletion_state,duration_seconds,created_at,control_version
            from public.meetings where (cast(:after as uuid) is null or id>cast(:after as uuid))
            order by id limit 101"""), {"after": str(after) if after else None})
        items = [dict(row) for row in rows.mappings()]
    return {"items": items[:100], "next_cursor": str(items[99]["id"]) if len(items)>100 else None}


async def audit(sessions, context, *, after: UUID | None = None):
    async with sessions() as session:
        await apply_system_context(session, replace(context, permission="audit.read"))
        rows = await session.execute(text("""select id,principal_id,action,target_type,target_id,
            result,occurred_at,reason from system_control.audit_events
            where (cast(:after as uuid) is null or id>cast(:after as uuid)) order by id limit 101"""),
            {"after": str(after) if after else None})
        items = [dict(row) for row in rows.mappings()]
    return {"items": items[:100], "next_cursor": str(items[99]["id"]) if len(items)>100 else None}


async def users(sessions, context, *, after: UUID | None = None, email: str | None = None,
                plan: str | None = None, status: str | None = None):
    async with sessions() as session:
        await apply_system_context(session, replace(context,permission="users.read"))
        items = await session.scalar(text("select system_control.list_users(:after,:email,:plan,:status)"),
            {"after":after,"email":email,"plan":plan,"status":status})
    if items is None:
        raise PermissionError("system user projection denied")
    return {"items":items[:100],"next_cursor":items[99]["id"] if len(items)>100 else None}


async def meeting_content(sessions, context, *, after: int = -1,
                          result_id: UUID | None = None, search: str | None = None):
    from sqlalchemy import select

    from twobrain_rec_server.db.models import DiarizationSegment, MediaRevision, ProcessingResult
    from twobrain_rec_server.processing.results import effective_processing_result_query
    from twobrain_rec_server.system_admin.audit import authorize_access

    context = await authorize_access(sessions, context)
    async with sessions() as session:
        await apply_system_context(session, context)
        header = await session.scalar(text("select system_control.meeting_content_header(:id)"),
                                      {"id": context.target_id})
        if header is None:
            raise PermissionError("meeting content unavailable")
        revision_id = await session.scalar(select(MediaRevision.id).where(
            MediaRevision.workspace_id == UUID(header["workspace_id"]),
            MediaRevision.meeting_id == context.target_id,
            MediaRevision.status == "accepted", MediaRevision.immutable.is_(True),
        ).order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc()).limit(1))
        result = (await session.execute(effective_processing_result_query(
            workspace_id=UUID(header["workspace_id"]), meeting_id=context.target_id,
            media_revision_id=revision_id,
        ).with_only_columns(ProcessingResult.id, ProcessingResult.result_version,
                            ProcessingResult.diarization_segment_count).limit(1))).mappings().first()
        if result_id is not None and (result is None or result["id"] != result_id):
            raise ValueError("Результат изменился. Откройте текст заново")
        segments = []
        if result is not None:
            query = select(DiarizationSegment.sequence, DiarizationSegment.start_seconds,
                DiarizationSegment.end_seconds, DiarizationSegment.speaker_label,
                DiarizationSegment.text, DiarizationSegment.source_role).where(
                    DiarizationSegment.processing_result_id == result["id"],
                    DiarizationSegment.meeting_id == context.target_id,
                    DiarizationSegment.sequence > after)
            if search:
                query = query.where(DiarizationSegment.text.icontains(search, autoescape=True))
            segments = [dict(row) for row in (await session.execute(
                query.order_by(DiarizationSegment.sequence).limit(101))).mappings()]
        # Recheck after all reads so a revocation/deletion during assembly does
        # not release the earlier header or segments in the response.
        if not await session.scalar(text("select system_control.meeting_content_allowed(:id)"),
                                    {"id": context.target_id}):
            raise PermissionError("meeting content unavailable")
        return {"meeting": header, "media_revision_id": revision_id,
                "result_id": result["id"] if result else None,
                "result_version": result["result_version"] if result else None,
                "state": "available" if result else "unavailable",
                "items": segments[:100],
                "next_cursor": segments[99]["sequence"] if len(segments)>100 else None}


async def check_content_access(sessions, context):
    from twobrain_rec_server.system_admin.audit import authorize_access

    context = await authorize_access(sessions, context)
    async with sessions() as session:
        await apply_system_context(session, context)
        if not await session.scalar(text("select system_control.meeting_content_allowed(:id)"),
                                    {"id": context.target_id}):
            raise PermissionError("meeting content unavailable")


async def meeting_overview(sessions, context, meeting_id: UUID):
    async with sessions() as session:
        await apply_system_context(session, replace(context, permission="meetings.metadata",
                                                    target_type="meeting", target_id=meeting_id))
        return await session.scalar(text("select system_control.meeting_overview(:id)"), {"id": meeting_id})


async def meeting_history(sessions, context, meeting_id: UUID, *, before: UUID | None = None):
    async with sessions() as session:
        await apply_system_context(session, replace(context, permission="processing.read",
                                                    target_type="meeting", target_id=meeting_id))
        items = await session.scalar(text("select system_control.meeting_history(:id,:before)"),
                                     {"id": meeting_id, "before": before})
    if items is None:
        raise PermissionError("processing metadata denied")
    return {"items": items[:100], "next_cursor": items[99]["id"] if len(items)>100 else None}


async def meeting_revisions(sessions, context, meeting_id: UUID, *, before: int | None = None):
    async with sessions() as session:
        await apply_system_context(session, replace(context, permission="meetings.metadata",
                                                    target_type="meeting", target_id=meeting_id))
        items = await session.scalar(text("select system_control.meeting_revisions(:id,:before)"),
                                     {"id": meeting_id, "before": before})
    if items is None:
        raise PermissionError("revision metadata denied")
    return {"items": items[:100], "next_cursor": items[99]["revision_number"] if len(items)>100 else None}
