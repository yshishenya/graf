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
SHARE_TOKEN_PATH_RE = re.compile(
    r"(/(?:api/v1/cabinet/(?:share|public-shares|share-invitations)|share|share-invitations|referral)/)[^/?]+"
)
LOG_RECORD_BASE_FIELDS = frozenset(logging.makeLogRecord({}).__dict__)


def sanitize_request_id(value: str) -> str:
    cleaned = "".join(char if 32 <= ord(char) < 127 else "_" for char in value).strip()
    return cleaned[:120] or str(uuid.uuid4())


def template_path(path: str) -> str:
    path = SHARE_TOKEN_PATH_RE.sub(r"\1{share_token}", path)
    return UUID_RE.sub("{uuid}", path)


def is_share_token_path(path: str) -> bool:
    return bool(SHARE_TOKEN_PATH_RE.search(path))


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


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = sanitize_request_id(request.headers.get("x-request-id", str(uuid.uuid4())))
    request.state.request_id = request_id
    started = time.perf_counter()
    templated_path = template_path(request.url.path)

    logger = logging.getLogger("twobrain_rec.request")
    logger.info(
        "request.start",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": templated_path,
        },
    )
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    if is_share_token_path(request.url.path):
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["Pragma"] = "no-cache"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    logger.info(
        "request.end",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": templated_path,
            "status_code": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        },
    )
    return response
