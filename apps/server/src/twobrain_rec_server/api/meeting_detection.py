from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    MeetingDetectionRegistryResponse,
    MeetingDetectionTelemetryRequest,
    MeetingDetectionTelemetryResponse,
    Problem,
)
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.auth.dependencies import (
    get_device_context,
    get_principal,
    get_tenant_scope,
)
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.meeting_detection.registry import (
    CACHE_CONTROL,
    MeetingTargetRegistryError,
    get_latest_published_registry,
    registry_etag,
)
from twobrain_rec_server.meeting_detection.telemetry import (
    MeetingDetectionTelemetryError,
    submit_meeting_detection_telemetry,
)

PROBLEM_RESPONSES = {
    400: {"model": Problem, "description": "Unsafe meeting detection telemetry payload"},
    401: {"model": Problem, "description": "Unauthorized"},
    403: {"model": Problem, "description": "Forbidden"},
    409: {"model": Problem, "description": "Idempotency conflict"},
    422: {"model": Problem, "description": "Schema invalid"},
    429: {"model": Problem, "description": "Meeting detection telemetry rate limited"},
    503: {"model": Problem, "description": "Meeting detection store unavailable"},
}

router = APIRouter(prefix="/api/v1", tags=["meeting-detection"], responses=PROBLEM_RESPONSES)

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


@router.post(
    "/desktop/meeting-detection/telemetry",
    status_code=status.HTTP_201_CREATED,
    response_model=MeetingDetectionTelemetryResponse,
    operation_id="createMeetingDetectionTelemetry",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def create_meeting_detection_telemetry(
    payload: MeetingDetectionTelemetryRequest,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingDetectionTelemetryResponse:
    try:
        result = await submit_meeting_detection_telemetry(
            tenant_scope=tenant_scope,
            db=db,
            payload=payload.model_dump(mode="json", by_alias=True, exclude_none=True),
            idempotency_key=idempotency_key,
        )
    except MeetingDetectionTelemetryError as exc:
        await commit_if_available(db)
        raise ProblemDetail(
            status=exc.status,
            code=exc.code,
            title=exc.title,
            detail=exc.detail,
            custody_owner="product_automatic",
            retry_class="automatic",
            normal_user_action="none",
            metadata_safety="metadata_only",
        ) from exc
    await commit_if_available(db)
    if result.dedupe_status == "duplicate":
        response.status_code = status.HTTP_200_OK
    return MeetingDetectionTelemetryResponse(
        batch_id=result.batch_id,
        dedupe_status=result.dedupe_status,
        accepted_target_rollup_count=result.accepted_target_rollup_count,
        accepted_candidate_count=result.accepted_candidate_count,
        suppressed_candidate_count=result.suppressed_candidate_count,
        registry_version=result.registry_version,
        next_upload_after=result.next_upload_after,
    )


@router.get(
    "/desktop/meeting-detection/target-registry",
    response_model=MeetingDetectionRegistryResponse,
    operation_id="getMeetingDetectionTargetRegistry",
    dependencies=[PrincipalDependency, DeviceDependency],
    responses={304: {"description": "Client registry cache is current"}},
)
async def get_meeting_detection_target_registry(
    response: Response,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingDetectionRegistryResponse | Response:
    if db is None:
        raise ProblemDetail(
            status=503,
            code="meeting_detection_registry_unavailable",
            title="Meeting detection registry unavailable",
            custody_owner="product_automatic",
            retry_class="automatic",
            normal_user_action="none",
            metadata_safety="metadata_only",
        )
    try:
        registry = await get_latest_published_registry(db, workspace_id=tenant_scope.workspace_id)
    except MeetingTargetRegistryError as exc:
        await commit_if_available(db)
        raise ProblemDetail(
            status=503,
            code="meeting_detection_registry_unavailable",
            title="Meeting detection registry unavailable",
            detail=str(exc),
            custody_owner="product_automatic",
            retry_class="automatic",
            normal_user_action="none",
            metadata_safety="metadata_only",
        ) from exc
    await commit_if_available(db)
    document = dict(registry.document)
    etag = registry_etag(document)
    headers = _registry_response_headers(
        etag=etag,
        registry_version=str(document["registryVersion"]),
    )
    if _etag_matches(if_none_match, etag):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    response.headers.update(headers)
    return MeetingDetectionRegistryResponse(**document, etag=etag)


def _registry_response_headers(*, etag: str, registry_version: str) -> dict[str, str]:
    return {
        "ETag": f'"{etag}"',
        "Cache-Control": CACHE_CONTROL,
        "X-GRAF-Registry-Version": registry_version,
    }


def _etag_matches(if_none_match: str | None, current_etag: str) -> bool:
    if not if_none_match:
        return False
    candidates = {value.strip().strip('"') for value in if_none_match.split(",")}
    return current_etag in candidates or "*" in candidates
