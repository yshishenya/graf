from collections.abc import Mapping
from typing import Any

SECRET_KEYS = {
    "authorization",
    "bearer",
    "cookie",
    "password",
    "secret",
    "token",
    "minio_secret_key",
    "mediascribe_api_key",
    "signed_url",
    "raw_audio",
    "transcript",
    "meeting_content",
}


def redact_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in values.items():
        lowered = key.lower()
        if any(secret in lowered for secret in SECRET_KEYS):
            redacted[key] = "[REDACTED]"
        elif isinstance(value, Mapping):
            redacted[key] = redact_mapping(value)
        elif isinstance(value, list):
            redacted[key] = [redact_mapping(item) if isinstance(item, Mapping) else item for item in value]
        else:
            redacted[key] = value
    return redacted
