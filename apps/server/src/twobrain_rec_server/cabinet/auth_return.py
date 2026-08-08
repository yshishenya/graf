from __future__ import annotations

from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.cabinet.access import decide_meeting_access
from twobrain_rec_server.db.models import Meeting
from twobrain_rec_server.db.tenant_context import TenantDatabaseContext, apply_tenant_context


def _safe_local_path(value: str | None) -> tuple[str, str] | None:
    if value is None:
        return None
    path = value.strip()
    if not path or not path.startswith("/") or path.startswith("//"):
        return None
    if any(char in path for char in "\r\n"):
        return None
    try:
        parsed = urlsplit(path)
    except ValueError:
        return None
    if parsed.scheme or parsed.netloc:
        return None
    return path, parsed.path


def _detail_candidate(path: str) -> tuple[UUID | None, str] | None:
    for collection_path in ("/meetings", "/desktop/meetings"):
        if not path.startswith(f"{collection_path}/"):
            continue
        candidate = path.removeprefix(f"{collection_path}/")
        if not candidate or "/" in candidate:
            return None, collection_path
        try:
            return UUID(candidate), collection_path
        except ValueError:
            return None, collection_path
    return None


async def resolve_browser_auth_return_path(
    db: AsyncSession,
    *,
    requested_redirect: str | None,
    organization_id: UUID,
    workspace_id: UUID,
    user_id: UUID,
    auth_session_id: UUID | None,
) -> str | None:
    """Keep a browser return only when its detail target is visible to the new session.

    The resolver intentionally performs only the minimal meeting/access lookup.
    It never loads a review, transcript, artifact, or any other detail-bearing
    surface while deciding whether a browser may return to a saved URL.
    """

    local_path = _safe_local_path(requested_redirect)
    if local_path is None:
        return None
    preserved_path, parsed_path = local_path
    meeting_id, fallback_path = _detail_candidate(parsed_path) or (None, "")
    if not fallback_path:
        return preserved_path
    if meeting_id is None:
        return fallback_path

    await apply_tenant_context(
        db,
        TenantDatabaseContext(
            organization_id=organization_id,
            workspace_id=workspace_id,
            user_id=user_id,
            auth_session_id=auth_session_id,
        ),
    )
    meeting = await db.scalar(
        select(Meeting).where(
            Meeting.id == meeting_id,
            Meeting.workspace_id == workspace_id,
        )
    )
    if meeting is None:
        return fallback_path
    decision = await decide_meeting_access(
        db,
        meeting,
        workspace_id=workspace_id,
        viewer_user_id=user_id,
    )
    return preserved_path if decision.can_view else fallback_path
