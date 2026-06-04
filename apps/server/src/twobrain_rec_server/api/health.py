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

    checks = {
        "api_config": "ok",
        "postgres": postgres_status,
        "minio": minio_status,
        "ingest_limits": "configured",
        "temporal": "not_required",
        "mediascribe": "not_required",
    }
    status = "ready" if all(v in {"ok", "configured", "not_required"} for v in checks.values()) else "not_ready"
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
