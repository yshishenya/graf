"""Persist access decisions in their own transaction before returning authority."""

from dataclasses import replace
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from twobrain_rec_server.db.tenant_context import SystemDatabaseContext, apply_system_context


async def create_case_context(
    sessions: async_sessionmaker[AsyncSession],
    context: SystemDatabaseContext,
    *,
    reason: str,
) -> UUID:
    if not reason.strip() or len(reason) > 1000:
        raise ValueError("case reason must contain 1 to 1000 characters")
    if context.target_id is None:
        raise ValueError("case requires an exact target")
    async with sessions() as session:
        await apply_system_context(session, context)
        case_id = await session.scalar(
            text("select system_control.open_case_context(:reason)"),
            {"reason": reason},
        )
        await session.commit()
    if case_id is None:
        raise PermissionError("case target is not accessible")
    return case_id


async def authorize_access(
    sessions: async_sessionmaker[AsyncSession],
    context: SystemDatabaseContext,
) -> SystemDatabaseContext:
    async with sessions() as session:
        await apply_system_context(session, context)
        decision = (
            await session.execute(text("select * from system_control.record_access()"))
        ).one()
        # A denial must survive the caller's exception/rollback. A failed commit
        # never produces an access ticket. Do not catch database outages here.
        await session.commit()
    if not decision.allowed:
        raise PermissionError("system access denied")
    return replace(context, audit_event_id=decision.audit_event_id)


async def record_admin_mutation(
    session: AsyncSession,
    *,
    permission: str,
    action: str,
    target_type: str | None,
    target_id: UUID | None,
    reason: str,
) -> UUID:
    """Write the immutable audit event in the command transaction."""
    event_id = await session.scalar(
        text("""select system_control.record_admin_mutation(
            :permission,:action,:target_type,:target_id,:reason)"""),
        {"permission": permission, "action": action, "target_type": target_type,
         "target_id": target_id, "reason": reason},
    )
    if event_id is None:
        raise PermissionError("administrative mutation audit denied")
    return event_id
