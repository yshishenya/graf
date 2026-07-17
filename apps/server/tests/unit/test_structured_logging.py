import json
import logging
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

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


def test_request_logging_middleware_never_captures_request_headers(caplog) -> None:
    app = FastAPI()
    app.state.settings = SimpleNamespace(
        redact_headers=("authorization", "cookie", "set-cookie", "x-content-sha256")
    )
    app.middleware("http")(request_logging_middleware)

    @app.get("/health/{item_id}")
    async def health(item_id: str) -> dict[str, bool]:
        return {"ok": True}

    markers = {
        "authorization": "Bearer synthetic-auth-marker",
        "cookie": "session=synthetic-cookie-marker",
        "referer": "https://example.test/synthetic-referer-marker",
        "x-private-header": "synthetic-private-header-marker",
    }
    with caplog.at_level(logging.INFO, logger="twobrain_rec.request"):
        response = TestClient(app).get(
            "/health/11111111-1111-1111-1111-111111111111?synthetic-query-marker",
            headers=markers,
        )

    assert response.status_code == 200
    records = [record for record in caplog.records if record.name == "twobrain_rec.request"]
    assert [record.getMessage() for record in records] == ["request.start", "request.end"]
    for record in records:
        assert "headers" not in record.__dict__
        payload = json.loads(JsonFormatter().format(record))
        assert all(marker not in json.dumps(payload) for marker in markers.values())
