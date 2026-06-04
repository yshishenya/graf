from fastapi import APIRouter, Request

from twobrain_rec_server.api.schemas import HealthResponse, ReadyResponse

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    return HealthResponse()


@router.get("/ready", response_model=ReadyResponse)
async def ready(request: Request) -> ReadyResponse:
    settings = request.app.state.settings
    checks = {
        "api_config": "ok",
        "postgres": "configured" if settings.database_url else "missing",
        "minio": "configured" if settings.minio_endpoint and settings.minio_bucket else "missing",
        "ingest_limits": "configured",
        "temporal": "not_required",
        "mediascribe": "not_required",
    }
    status = "ready" if all(v in {"ok", "configured", "not_required"} for v in checks.values()) else "not_ready"
    return ReadyResponse(status=status, checks=checks)
