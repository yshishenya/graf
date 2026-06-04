import json
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from twobrain_rec_server.config import Settings
from twobrain_rec_server.observability.redaction import redact_mapping

UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
LOG_RECORD_BASE_FIELDS = frozenset(logging.makeLogRecord({}).__dict__)


def sanitize_request_id(value: str) -> str:
    cleaned = "".join(char if 32 <= ord(char) < 127 else "_" for char in value).strip()
    return cleaned[:120] or str(uuid.uuid4())


def template_path(path: str) -> str:
    return UUID_RE.sub("{uuid}", path)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in LOG_RECORD_BASE_FIELDS or key.startswith("_"):
                continue
            payload[key] = redact_mapping(value) if isinstance(value, dict) else value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True, default=str)


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())


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
    request_id = sanitize_request_id(request.headers.get("x-request-id", str(uuid.uuid4())))
    request.state.request_id = request_id
    started = time.perf_counter()
    templated_path = template_path(request.url.path)
    safe_headers = _safe_headers(request, settings)

    logger = logging.getLogger("twobrain_rec.request")
    logger.info(
        "request.start",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": templated_path,
            "headers": safe_headers,
        },
    )
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request.end",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": templated_path,
            "status_code": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "headers": safe_headers,
        },
    )
    return response
