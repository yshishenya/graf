import json
import logging

from twobrain_rec_server.observability.logging import JsonFormatter, template_path


def test_json_formatter_emits_structured_request_fields_and_redacts_headers() -> None:
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
            "headers": {"authorization": "Bearer secret", "x-client": "desktop"},
        }
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "request.end"
    assert payload["request_id"] == "request-123"
    assert payload["status_code"] == 503
    assert payload["duration_ms"] == 12.34
    assert payload["path"] == "/api/v1/upload-sessions/{uuid}"
    assert "11111111-1111-1111-1111-111111111111" not in payload["path"]
    assert payload["headers"]["authorization"] == "[REDACTED]"
    assert payload["headers"]["x-client"] == "desktop"
