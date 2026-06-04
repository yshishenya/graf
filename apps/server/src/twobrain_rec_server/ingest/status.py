from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.ingest.parts import get_session_for_tenant
from twobrain_rec_server.ingest.store import UploadSessionRecord


async def get_upload_session_status(
    session_id: UUID,
    tenant_scope: TenantScope,
    db: AsyncSession | None = None,
) -> UploadSessionRecord:
    return await get_session_for_tenant(session_id, tenant_scope, db)
