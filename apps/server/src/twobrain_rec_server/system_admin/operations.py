"""Commit an audited command before dispatch; never send a domain effect here."""

import json
from dataclasses import replace
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from twobrain_rec_server.db.tenant_context import SystemDatabaseContext, apply_system_context
from twobrain_rec_server.system_admin.schemas import COMMAND_PERMISSIONS, Command


async def preview_operation(
    sessions: async_sessionmaker[AsyncSession], context: SystemDatabaseContext, command: Command,
) -> dict:
    context = replace(
        context, permission=COMMAND_PERMISSIONS[command.kind],
        target_type="meeting", target_id=command.target_id,
    )
    async with sessions() as session:
        await apply_system_context(session, context)
        result = await session.scalar(
            text("select system_control.preview_meeting_operation(cast(:command as jsonb))"),
            {"command": command.model_dump_json()},
        )
        await session.commit()
    return result


async def commit_operation(
    sessions: async_sessionmaker[AsyncSession], context: SystemDatabaseContext,
    *, preview_id: UUID, expected_preview_hash: str, idempotency_key: UUID,
) -> dict:
    async with sessions() as session:
        await apply_system_context(session, context)
        result = await session.scalar(
            text("select system_control.commit_operation(:preview, :hash, :key)"),
            {"preview": preview_id, "hash": expected_preview_hash, "key": idempotency_key},
        )
        await session.commit()
    return result


async def read_operation(
    sessions: async_sessionmaker[AsyncSession], context: SystemDatabaseContext, operation_id: UUID,
) -> dict | None:
    async with sessions() as session:
        await apply_system_context(session, context)
        return await session.scalar(
            text("select system_control.read_operation(:id)"), {"id": operation_id},
        )


def decode_command(value: dict | str) -> Command:
    from twobrain_rec_server.system_admin.schemas import COMMAND_ADAPTER

    return COMMAND_ADAPTER.validate_python(json.loads(value) if isinstance(value, str) else value)
