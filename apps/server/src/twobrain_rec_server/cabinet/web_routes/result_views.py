"""Private result visibility; collection remains behind the real T113 gate."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.product_analytics_guard import _run_result_view_operation
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.cabinet.result_visibility import (
    load_fresh_result_view_bindings,
    result_view_proof_age,
    verify_result_view_proof,
)
from twobrain_rec_server.cabinet.web_routes.support import (
    PrincipalDependency,
    WebCSRFDependency,
    WebTenantDependency,
)
from twobrain_rec_server.config import SMOKE_IDENTITY_CLASS
from twobrain_rec_server.product_analytics.ingest import ProductAnalyticsIngestService
from twobrain_rec_server.product_analytics.traffic_class import classify_public_traffic

router = APIRouter()


def _eligible(request, principal, workspace_id):
    settings = request.app.state.settings
    if not settings.product_analytics_enabled or principal is None:
        return False
    if settings.smoke_identity_class == SMOKE_IDENTITY_CLASS and (
        principal.user_id == settings.smoke_user_id
        or workspace_id == settings.smoke_workspace_id
        or (settings.smoke_device_id is not None and principal.session_device_id == settings.smoke_device_id)
    ):
        return False
    return classify_public_traffic(
        headers=request.headers, user_agent=request.headers.get("user-agent"),
        client_host=request.client.host if request.client is not None else None,
        internal_hosts=settings.product_analytics_internal_hosts,
    ) == "external"


async def optional_result_view_proofs(
    request, *, principal, workspace_id, meeting_id, review, selection,
    embedded=False, source_result_id=None,
):
    loop = asyncio.get_running_loop()
    cleanup_deadline = loop.time() + 2
    work_deadline = cleanup_deadline - 0.5
    try:
        async with asyncio.timeout_at(cleanup_deadline):
            async with asyncio.timeout_at(work_deadline):
                if (review.access is None or review.access.state != "owner"
                        or not review.access.can_view or not review.access.can_view_full_meeting
                        or not _eligible(request, principal, workspace_id)):
                    return {}
                service = ProductAnalyticsIngestService(request.app.state.settings)
                return await _run_result_view_operation(lambda: service.issue_result_view_proofs(
                    principal=principal, workspace_id=workspace_id,
                    sessionmaker=getattr(request.app.state, "db_sessionmaker", None),
                    meeting_id=meeting_id, review=review, selection=selection.get("selection"),
                    secret=getattr(request.app.state, "web_csrf_secret", None),
                    surface="cabinet_desktop" if embedded else "cabinet_web",
                    work_deadline=work_deadline, cleanup_deadline=cleanup_deadline,
                    selected_summary_template_key=request.query_params.get("summary_format"),
                    source_result_id=None if embedded else source_result_id,
                ))
    except Exception:
        return {}


@router.post("/meetings/{meeting_id}/result-viewed", dependencies=[WebCSRFDependency])
@router.post("/desktop/meetings/{meeting_id}/result-viewed", dependencies=[WebCSRFDependency])
async def result_viewed(
    request: Request, meeting_id: UUID, tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
):
    response = {"status": "unavailable"}
    embedded = request.url.path.startswith("/desktop/")
    source_result_id = None
    if not embedded and (value := request.query_params.get("source_result_id")) is not None:
        try:
            source_result_id = UUID(value)
        except ValueError:
            raise ProblemDetail(status=422, code="validation_error", title="Invalid request") from None
    deadline = getattr(request.state, "result_view_deadline", None)
    cleanup_deadline = getattr(request.state, "result_view_cleanup_deadline", None)
    if deadline is None or cleanup_deadline is None or not _eligible(request, principal, tenant_scope.workspace_id):
        return JSONResponse(response, headers={"Cache-Control": "private, no-store"})
    body = await request.json()
    if (not isinstance(body, dict) or set(body) != {"proof"}
            or not isinstance(body["proof"], str) or not body["proof"].isascii()
            or not 0 < len(body["proof"]) <= 1536):
        return JSONResponse(response, headers={"Cache-Control": "private, no-store"})
    proof = body["proof"]
    secret = getattr(request.app.state, "web_csrf_secret", None)
    age = result_view_proof_age(proof, secret=secret, now=datetime.now(UTC))
    if age != "invalid" and asyncio.get_running_loop().time() < deadline:
        service = ProductAnalyticsIngestService(request.app.state.settings)
        common = dict(
            principal=principal, workspace_id=tenant_scope.workspace_id,
            sessionmaker=getattr(request.app.state, "db_sessionmaker", None),
            surface="cabinet_desktop" if embedded else "cabinet_web",
            work_deadline=deadline, cleanup_deadline=cleanup_deadline,
        )
        summary_key = request.query_params.get("summary_format")
        if age == "expired":
            renewed = await service.renew_result_view_proof(
                **common, meeting_id=meeting_id, proof=proof, secret=secret,
                selected_summary_template_key=summary_key, source_result_id=source_result_id,
            )
            if renewed is not None:
                response = {"status": "renewed", "proof": renewed}
        else:
            async def verify(db, started_at):
                bindings = await load_fresh_result_view_bindings(
                    db, principal=principal, workspace_id=tenant_scope.workspace_id,
                    meeting_id=meeting_id, started_at=started_at,
                    selected_summary_template_key=summary_key, source_result_id=source_result_id,
                )
                owner = db.sync_session._projection_owner
                for binding in bindings.values():
                    owner.checkpoint()
                    status = verify_result_view_proof(proof, binding, secret=secret, now=datetime.now(UTC))
                    owner.checkpoint()
                    if status == "valid":
                        return binding
                return None

            if await service.admit_result_view(**common, verify_view=verify):
                response = {"status": "accepted"}
    return JSONResponse(response, headers={"Cache-Control": "private, no-store"})
