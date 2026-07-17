from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    Problem,
    SupportIncidentReportRequest,
    SupportIncidentResponse,
)
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.auth.dependencies import get_tenant_scope, require_web_csrf
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.support.github_issues import GitHubIssueClient
from twobrain_rec_server.support.incidents import (
    SupportIncidentSubmissionError,
    SupportIncidentSubmissionResult,
    submit_support_incident,
    sync_support_incident,
)

PROBLEM_RESPONSES = {
    400: {"model": Problem, "description": "Unsafe support incident payload"},
    401: {"model": Problem, "description": "Unauthorized"},
    403: {"model": Problem, "description": "Forbidden"},
    404: {"model": Problem, "description": "Support incident not found"},
    409: {"model": Problem, "description": "Idempotency conflict"},
    422: {"model": Problem, "description": "Unsupported support incident schema"},
    429: {"model": Problem, "description": "Support incident rate limited"},
    503: {"model": Problem, "description": "Support incident unavailable"},
}

router = APIRouter(prefix="/api/v1", tags=["support-incidents"], responses=PROBLEM_RESPONSES)

TenantDependency = Depends(get_tenant_scope)
WebCSRFDependency = Depends(require_web_csrf)


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


@dataclass(frozen=True, slots=True)
class GitHubIssueClientResolution:
    client: object | None
    failure_code: str | None = None


def get_github_issue_client(request: Request) -> GitHubIssueClientResolution:
    client = getattr(request.app.state, "support_incident_github_client", None)
    if client is not None:
        return GitHubIssueClientResolution(client=client)
    settings = request.app.state.settings
    token_file = settings.support_incident_github_token_file
    if token_file is None:
        return GitHubIssueClientResolution(
            client=None,
            failure_code="support_incident.configuration_invalid",
        )
    try:
        token = token_file.read_text(encoding="utf-8").strip()
    except OSError:
        return GitHubIssueClientResolution(
            client=None,
            failure_code="support_incident.configuration_invalid",
        )
    if not token:
        return GitHubIssueClientResolution(
            client=None,
            failure_code="support_incident.configuration_invalid",
        )
    return GitHubIssueClientResolution(
        client=GitHubIssueClient(
            token=token,
            timeout_seconds=float(settings.support_incident_github_timeout_seconds),
        )
    )


GitHubClientDependency = Depends(get_github_issue_client)


@router.post(
    "/desktop/support-incidents",
    status_code=201,
    response_model=SupportIncidentResponse,
    dependencies=[WebCSRFDependency],
)
async def create_support_incident(
    payload: SupportIncidentReportRequest,
    response: Response,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
    github_client: GitHubIssueClientResolution = GitHubClientDependency,
) -> SupportIncidentResponse:
    try:
        result = await submit_support_incident(
            settings=request.app.state.settings,
            tenant_scope=tenant_scope,
            db=db,
            payload=payload.model_dump(mode="json"),
            github_client=github_client.client,
            github_failure_code=github_client.failure_code,
            idempotency_key=idempotency_key,
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
    if result.incident_status == "pending_sync":
        response.status_code = 202
    elif result.dedupe_status == "updated":
        response.status_code = 200
    return _response_from_result(result)


@router.post(
    "/desktop/support-incidents/{incident_id}/sync",
    status_code=200,
    response_model=SupportIncidentResponse,
    dependencies=[WebCSRFDependency],
)
async def retry_support_incident_sync(
    incident_id: Annotated[str, Path(pattern=r"^CUST-[A-Z0-9-]{1,27}$")],
    response: Response,
    request: Request,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
    github_client: GitHubIssueClientResolution = GitHubClientDependency,
) -> SupportIncidentResponse:
    try:
        result = await sync_support_incident(
            settings=request.app.state.settings,
            tenant_scope=tenant_scope,
            db=db,
            incident_id=incident_id,
            github_client=github_client.client,
            github_failure_code=github_client.failure_code,
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
    if result.incident_status == "pending_sync":
        response.status_code = 202
    return _response_from_result(result)


def _response_from_result(result: SupportIncidentSubmissionResult) -> SupportIncidentResponse:
    if result.incident_status == "synced":
        user_message = f"Запрос принят и передан в поддержку. Номер: {result.incident_id}"
    else:
        user_message = (
            "Запрос принят сервером. Синхронизация с поддержкой ожидает проверки. "
            f"Номер: {result.incident_id}"
        )
    return SupportIncidentResponse(
        incident_id=result.incident_id,
        incident_status=result.incident_status,
        github_issue_number=result.github_issue_number,
        github_issue_url=result.github_issue_url,
        dedupe_status=result.dedupe_status,
        affected_count=result.affected_count,
        user_message=user_message,
    )
