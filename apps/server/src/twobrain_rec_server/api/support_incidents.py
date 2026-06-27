from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    Problem,
    SupportIncidentReportRequest,
    SupportIncidentResponse,
)
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.auth.dependencies import (
    get_device_context,
    get_principal,
    get_tenant_scope,
)
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.support.github_issues import GitHubIssueClient
from twobrain_rec_server.support.incidents import (
    SupportIncidentSubmissionError,
    submit_support_incident,
)

PROBLEM_RESPONSES = {
    400: {"model": Problem, "description": "Unsafe support incident payload"},
    401: {"model": Problem, "description": "Unauthorized"},
    403: {"model": Problem, "description": "Forbidden"},
    409: {"model": Problem, "description": "Idempotency conflict"},
    422: {"model": Problem, "description": "Unsupported support incident schema"},
    429: {"model": Problem, "description": "Support incident rate limited"},
    503: {"model": Problem, "description": "Support incident unavailable"},
}

router = APIRouter(prefix="/api/v1", tags=["support-incidents"], responses=PROBLEM_RESPONSES)

TenantDependency = Depends(get_tenant_scope)
PrincipalDependency = Depends(get_principal)
DeviceDependency = Depends(get_device_context)


async def get_request_db_session(
    request: Request,
    tenant_scope: TenantScope = TenantDependency,
):
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        yield None
        return
    async with sessionmaker() as session:
        await apply_tenant_scope(session, tenant_scope)
        yield session


DbDependency = Depends(get_request_db_session)


async def commit_if_available(db: AsyncSession | None) -> None:
    if db is not None:
        await db.commit()


def get_github_issue_client(request: Request) -> object:
    client = getattr(request.app.state, "support_incident_github_client", None)
    if client is not None:
        return client
    settings = request.app.state.settings
    token_file = settings.support_incident_github_token_file
    if token_file is None:
        raise ProblemDetail(
            status=503,
            code="support_incident.configuration_invalid",
            title="Support incident GitHub token unavailable",
        )
    try:
        token = token_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ProblemDetail(
            status=503,
            code="support_incident.configuration_invalid",
            title="Support incident GitHub token unavailable",
        ) from exc
    if not token:
        raise ProblemDetail(
            status=503,
            code="support_incident.configuration_invalid",
            title="Support incident GitHub token unavailable",
        )
    return GitHubIssueClient(token=token, timeout_seconds=float(settings.support_incident_github_timeout_seconds))


GitHubClientDependency = Depends(get_github_issue_client)


@router.post(
    "/desktop/support-incidents",
    status_code=201,
    response_model=SupportIncidentResponse,
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def create_support_incident(
    payload: SupportIncidentReportRequest,
    response: Response,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
    github_client: object = GitHubClientDependency,
) -> SupportIncidentResponse:
    _ = idempotency_key
    try:
        result = await submit_support_incident(
            settings=request.app.state.settings,
            tenant_scope=tenant_scope,
            db=db,
            payload=payload.model_dump(mode="json"),
            github_client=github_client,
        )
    except SupportIncidentSubmissionError as exc:
        await commit_if_available(db)
        raise ProblemDetail(
            status=exc.status,
            code=exc.code,
            title=exc.title,
            detail=exc.detail,
            custody_owner="support",
            retry_class="not_retryable",
            normal_user_action="copy_safe_report",
            metadata_safety="metadata_only",
        ) from exc
    await commit_if_available(db)
    if result.dedupe_status == "updated":
        response.status_code = 200
    return SupportIncidentResponse(
        incident_id=result.incident_id,
        incident_status=result.incident_status,
        github_issue_number=result.github_issue_number,
        github_issue_url=result.github_issue_url,
        dedupe_status=result.dedupe_status,
        affected_count=result.affected_count,
        user_message=f"Отчет отправлен. Мы разберемся. Номер: {result.incident_id}",
    )
