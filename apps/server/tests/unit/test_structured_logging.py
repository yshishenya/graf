import asyncio
import json
import logging
from types import SimpleNamespace

from starlette.requests import Request
from starlette.responses import Response

from twobrain_rec_server.observability import logging as observability_logging
from twobrain_rec_server.observability.logging import (
    JsonFormatter,
    request_logging_middleware,
    template_path,
)


def test_json_formatter_emits_structured_request_metadata_without_headers() -> None:
    record = logging.makeLogRecord(
        {
            "name": "twobrain_rec.request",
            "levelno": logging.INFO,
            "levelname": "INFO",
            "msg": "request.end",
            "request_id": "request-123",
            "method": "GET",
            "path": template_path("/api/v1/upload-sessions/11111111-1111-1111-1111-111111111111"),
            "status_code": 503,
            "duration_ms": 12.34,
        }
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "request.end"
    assert payload["request_id"] == "request-123"
    assert payload["status_code"] == 503
    assert payload["duration_ms"] == 12.34
    assert payload["path"] == "/api/v1/upload-sessions/{uuid}"
    assert "11111111-1111-1111-1111-111111111111" not in payload["path"]
    assert "headers" not in payload


class _RecordingLogger:
    def __init__(self) -> None:
        self.records: list[logging.LogRecord] = []

    def info(self, event: str, *, extra: dict[str, object]) -> None:
        self.records.append(
            logging.makeLogRecord(
                {
                    "name": "twobrain_rec.request",
                    "levelno": logging.INFO,
                    "levelname": "INFO",
                    "msg": event,
                    **extra,
                }
            )
        )


def test_request_logging_middleware_never_captures_request_headers(monkeypatch) -> None:
    markers = {
        "authorization": "Bearer synthetic-auth-marker",
        "cookie": "session=synthetic-cookie-marker",
        "referer": "https://example.test/synthetic-referer-marker",
        "x-private-header": "synthetic-private-header-marker",
    }
    recorder = _RecordingLogger()
    monkeypatch.setattr(
        observability_logging,
        "logging",
        SimpleNamespace(getLogger=lambda _name: recorder),
    )

    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": "/health/11111111-1111-1111-1111-111111111111",
            "raw_path": b"/health/11111111-1111-1111-1111-111111111111",
            "query_string": b"synthetic-query-marker",
            "headers": [(key.encode(), value.encode()) for key, value in markers.items()],
            "client": ("testclient", 50000),
            "server": ("testserver", 443),
        }
    )

    async def call_next(_: Request) -> Response:
        return Response(status_code=200)

    response = asyncio.run(request_logging_middleware(request, call_next))

    assert response.status_code == 200
    assert [record.getMessage() for record in recorder.records] == ["request.start", "request.end"]
    for record in recorder.records:
        assert "headers" not in record.__dict__
        payload = json.loads(JsonFormatter().format(record))
        assert "synthetic-query-marker" not in json.dumps(payload)
        assert all(marker not in json.dumps(payload) for marker in markers.values())
