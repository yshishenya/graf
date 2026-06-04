import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from twobrain_rec_server.config import Settings
from twobrain_rec_server.observability.redaction import redact_mapping


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _safe_headers(request: Request, settings: Settings) -> dict[str, str]:
    redacted = set(settings.redact_headers)
    safe: dict[str, str] = {}
    for key, value in request.headers.items():
        lowered = key.lower()
        safe[key] = "[REDACTED]" if lowered in redacted else value
    return redact_mapping(safe)


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    settings: Settings = request.app.state.settings
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    started = time.perf_counter()

    logger = logging.getLogger("twobrain_rec.request")
    logger.info(
        "request.start",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "headers": _safe_headers(request, settings),
        },
    )
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request.end",
        extra={
            "request_id": request_id,
            "status_code": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        },
    )
    return response
