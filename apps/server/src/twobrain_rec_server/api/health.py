from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from twobrain_rec_server.api.schemas import HealthResponse, ReadyDetailResponse, ReadyResponse

router = APIRouter(prefix="/api/v1/health", tags=["health"])

REQUIRED_INGEST_TABLES = (
    "organizations",
    "workspaces",
    "user_identities",
    "workspace_memberships",
    "registered_devices",
    "meetings",
    "upload_sessions",
    "upload_parts",
    "track_artifacts",
    "manifest_snapshots",
    "processing_placeholders",
    "temporary_upload_objects",
    "ingest_audit_events",
    "processing_workflows",
    "mediascribe_jobs",
    "processing_results",
    "transcript_segments",
    "diarization_segments",
    "processing_audit_events",
    "processing_dependency_states",
)


@router.get("/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    return HealthResponse()


async def readiness_checks(request: Request) -> tuple[str, dict[str, str]]:
    settings = request.app.state.settings
    postgres_status = "configured" if settings.database_url else "missing"
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        postgres_status = "unreachable"
    elif postgres_status != "missing":
        try:
            async with sessionmaker() as session:
                await session.execute(text("SELECT 1"))
                for table_name in REQUIRED_INGEST_TABLES:
                    await session.execute(text(f"SELECT 1 FROM {table_name} LIMIT 1"))
            postgres_status = "ok"
        except Exception:
            postgres_status = "unreachable"

    minio_status = "configured" if settings.minio_endpoint and settings.minio_bucket else "missing"
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        minio_status = "unreachable"
    elif minio_status != "missing":
        try:
            is_ready_async = getattr(storage, "is_ready_async", None)
            is_ready = getattr(storage, "is_ready", None)
            if is_ready_async is not None:
                minio_status = "ok" if await is_ready_async() else "unreachable"
            else:
                minio_status = "ok" if is_ready is not None and is_ready() else "unreachable"
        except Exception:
            minio_status = "unreachable"

    temporal_status = "not_required"
    if settings.processing_enabled:
        temporal_status = "configured" if settings.temporal_address else "missing"
    mediascribe_status = "not_configured"
    if settings.processing_enabled:
        mediascribe_status = (
            "configured"
            if settings.mediascribe_base_url is not None and settings.mediascribe_api_key_file is not None
            else "dispatcher_only"
        )
    elif settings.mediascribe_base_url is not None:
        mediascribe_status = "configured"

    checks = {
        "api_config": "ok",
        "postgres": postgres_status,
        "minio": minio_status,
        "ingest_limits": "configured",
        "processing": "enabled" if settings.processing_enabled else "disabled",
        "temporal": temporal_status,
        "mediascribe": mediascribe_status,
        "langfuse": "not_configured" if settings.langfuse_base_url is None else "configured",
        "support_incidents": getattr(
            request.app.state,
            "support_incident_integration_status",
            "configuration_invalid",
        ),
    }
    non_blocking_statuses = {
        "ok",
        "configured",
        "dispatcher_only",
        "not_required",
        "not_configured",
        "disabled",
        "enabled",
        "configuration_invalid",
    }
    status = "ready" if all(v in non_blocking_statuses for v in checks.values()) else "not_ready"
    return status, checks


@router.get("/ready", response_model=ReadyResponse, responses={503: {"model": ReadyResponse}})
async def ready(request: Request) -> JSONResponse:
    status, _checks = await readiness_checks(request)
    return JSONResponse(status_code=200 if status == "ready" else 503, content={"status": status})


@router.get("/ready/internal", response_model=ReadyDetailResponse, responses={503: {"model": ReadyDetailResponse}})
async def ready_internal(
    request: Request,
    x_internal_health_check: str | None = Header(default=None, alias="X-Internal-Health-Check"),
) -> JSONResponse:
    if x_internal_health_check != "true":
        return JSONResponse(status_code=403, content={"status": "forbidden"})
    status, checks = await readiness_checks(request)
    return JSONResponse(status_code=200 if status == "ready" else 503, content={"status": status, "checks": checks})
