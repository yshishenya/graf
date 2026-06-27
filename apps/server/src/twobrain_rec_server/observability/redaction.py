import re
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
    "api_key",
    "x-api-key",
    "access_key",
    "device_token",
    "auth_header",
    "raw_log",
    "object_key",
    "mic_file",
    "incoming_file",
    "diarization",
    "mediascribe_result",
    "transcript_segment",
    "session",
    "provider",
    "provider_subject",
    "provider_username",
    "external_subject",
    "external_identity_id",
    "claims_fingerprint",
    "session_token",
    "session_token_hash",
    "registration_state",
    "workspace_auth_policy",
    "auth_callback_state",
    "id_token",
    "attendee",
    "calendar_passcode",
    "conference_url",
    "credential",
    "description",
    "meeting_url",
    "passcode",
    "provider_payload",
    "raw_event_payload",
}

FORBIDDEN_EVIDENCE_PATTERNS = (
    re.compile(r"bearer\s+[a-z0-9._~+/-]+=*", re.IGNORECASE),
    re.compile(r"authorization\s*[:=]", re.IGNORECASE),
    re.compile(r"password\s*[:=]", re.IGNORECASE),
    re.compile(r"secret\s*[:=]", re.IGNORECASE),
    re.compile(r"api[_-]?key\s*[:=]", re.IGNORECASE),
    re.compile(r"aws[_-]?access[_-]?key[_-]?id\s*[:=]", re.IGNORECASE),
    re.compile(r"access[_-]?key\s*[:=]", re.IGNORECASE),
    re.compile(r"minio.*(secret|password|credential)", re.IGNORECASE),
    re.compile(r"mediascribe.*(secret|token|credential|api[_-]?key)", re.IGNORECASE),
    re.compile(r"x-api-key\s*[:=]", re.IGNORECASE),
    re.compile(r"(mic_file|incoming_file)\s*[:=]", re.IGNORECASE),
    re.compile(r"(transcript|diarization|mediascribe_result).*text\s*[:=]", re.IGNORECASE),
    re.compile(r"langfuse.*(secret|token|credential|api[_-]?key)", re.IGNORECASE),
    re.compile(r"https?://[^\\s]+X-Amz-Signature=", re.IGNORECASE),
    re.compile(r"(refresh_token|app_password|signed_url|attendee_email_dump|raw_event_payload|passcode)\s*[:=]", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


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


def contains_forbidden_evidence_content(text: str) -> bool:
    lowered = text.lower()
    literal_markers = (
        "raw audio",
        "transcript text",
        "diarization text",
        "mediascribe result text",
        "meeting content",
        "set-cookie:",
        "x-amz-signature=",
    )
    return any(marker in lowered for marker in literal_markers) or any(
        pattern.search(text) for pattern in FORBIDDEN_EVIDENCE_PATTERNS
    )
