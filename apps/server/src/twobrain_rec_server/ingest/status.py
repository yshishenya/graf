from uuid import UUID

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.ingest.parts import get_session_for_tenant
from twobrain_rec_server.ingest.store import UploadSessionRecord


def get_upload_session_status(session_id: UUID, tenant_scope: TenantScope) -> UploadSessionRecord:
    return get_session_for_tenant(session_id, tenant_scope)
