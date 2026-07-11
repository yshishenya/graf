from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from urllib.parse import urlsplit

SUPPORTED_SCHEMA_VERSION = "desktop-support-incident.v1"
SERVER_REDACTION_VERSION = "support-incident-redaction.v1"
REDACTED_METADATA = "redacted_metadata"
UNKNOWN = "unknown"

ALLOWED_REPORT_FIELDS = (
    "schema_version",
    "app_name",
    "bundle_id",
    "app_version",
    "build_version",
    "macos_version",
    "architecture",
    "locale",
    "timezone",
    "environment_base_url_identity",
    "workspace_fingerprint",
    "user_fingerprint",
    "device_fingerprint",
    "safe_device_identifier",
    "safe_recording_identity",
    "local_recording_id_fingerprint",
    "server_meeting_fingerprint",
    "server_media_revision_fingerprint",
    "server_meeting_present",
    "server_media_revision_present",
    "custody_lifecycle_state",
    "upload_queue_item_state",
    "retry_class",
    "retry_mode",
    "normal_user_action",
    "failure_category",
    "problem_code",
    "sync_conflict_state",
    "created_at",
    "updated_at",
    "retention_deadline",
    "server_identity_present",
    "local_media_retained",
    "data_loss_risk",
    "server_copy_known",
    "upload_attempt_count",
    "last_attempt_at",
    "next_retry_at",
    "last_safe_http_status",
    "last_safe_problem_code",
    "upload_session_present",
    "upload_session_fingerprint",
    "expected_parts_count",
    "uploaded_parts_count",
    "range_mismatch_metadata",
    "local_file_completeness_profile",
    "local_purge_state",
    "local_purge_tasks",
    "local_purge_ack_state",
    "processing_status",
    "app_queue_schema_version",
    "ledger_schema_version",
    "redaction_state",
    "affected_count",
    "safe_affected_identities",
)

NESTED_ALLOWED_FIELDS = {
    "range_mismatch_metadata": {
        "has_mismatch",
        "missing_range_count",
        "corrupt_range_count",
        "expected_range_count",
        "uploaded_range_count",
    },
    "local_file_completeness_profile": {
        "manifest_present",
        "manifest_schema_version",
        "audio_files_present",
        "microphone_present",
        "system_audio_present",
        "missing_file_count",
        "corrupt_file_count",
        "total_size_bucket",
        "duration_bucket",
    },
}

BOOL_FIELDS = {
    "server_meeting_present",
    "server_media_revision_present",
    "server_identity_present",
    "local_media_retained",
    "server_copy_known",
    "upload_session_present",
}
INT_FIELDS = {
    "upload_attempt_count",
    "expected_parts_count",
    "uploaded_parts_count",
    "affected_count",
}

UNSAFE_KEY_PARTS = (
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "signed_url",
    "raw_path",
    "local_path",
    "transcript",
    "meeting_content",
    "meeting_title",
    "account_label",
    "human_name",
    "display_name",
    "email",
    "filename",
    "file_name",
    "raw_log",
    "screenshot",
)
BLOCKING_UNKNOWN_KEY_PARTS = (
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "signed_url",
    "raw_audio",
    "transcript",
    "meeting_content",
    "meeting_title",
    "human_name",
    "display_name",
    "email",
    "raw_log",
    "screenshot",
)

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
BEARER_RE = re.compile(r"\bbearer\s+[a-z0-9._~+/-]+=*", re.IGNORECASE)
SECRET_RE = re.compile(r"\b(api[_-]?key|token|password|secret)\s*[:=]", re.IGNORECASE)
SIGNED_URL_RE = re.compile(
    r"https?://[^\s]+(X-Amz-Signature=|[?&](token|signature|sig)=)", re.IGNORECASE
)
RAW_PATH_RE = re.compile(r"(^|[\s=:])(/Users/|/private/|/var/folders/|file://|[A-Za-z]:\\)")
SAFE_TEXT_RE = re.compile(r"^[A-Za-z0-9 ._:/+@-]{1,256}$")
SAFE_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,159}$")
SAFE_VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){0,3}(?:[-+][A-Za-z0-9._-]{1,40})?$")
SAFE_BUILD_RE = re.compile(r"^[A-Za-z0-9._-]{1,40}$")
SAFE_BUNDLE_ID_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+){1,8}$")
SAFE_LOCALE_RE = re.compile(r"^[a-z]{2,3}(?:[-_][A-Z]{2})?$")
SAFE_TIMEZONE_RE = re.compile(r"^[A-Za-z_]+/[A-Za-z0-9_+.-]+(?:/[A-Za-z0-9_+.-]+)?$")
SAFE_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
SAFE_FINGERPRINT_RE = re.compile(r"^(?:fpr|[a-z0-9]+_fpr)_[a-f0-9]{2,64}$")
SAFE_AFFECTED_FINGERPRINT_RE = re.compile(r"^affected_fpr_[a-f0-9]{2,64}$")
SAFE_SENTINELS = {"unknown", "not_applicable"}
FINGERPRINT_FIELDS = {
    "workspace_fingerprint",
    "user_fingerprint",
    "device_fingerprint",
    "local_recording_id_fingerprint",
    "server_meeting_fingerprint",
    "server_media_revision_fingerprint",
    "upload_session_fingerprint",
}
REPORT_FINGERPRINT_EXCLUDED_FIELDS = {
    "received_at",
    "safe_report_fingerprint",
    "dedupe_key",
    "affected_identity_fingerprint",
}

STRICT_STRING_FIELD_VALIDATORS: dict[str, Callable[[str], bool]] = {
    "app_name": lambda value: value == "GRAF",
    "bundle_id": lambda value: SAFE_BUNDLE_ID_RE.match(value) is not None,
    "app_version": lambda value: SAFE_VERSION_RE.match(value) is not None,
    "build_version": lambda value: SAFE_BUILD_RE.match(value) is not None,
    "macos_version": lambda value: SAFE_VERSION_RE.match(value) is not None,
    "architecture": lambda value: value in {"arm64", "x86_64", "universal", UNKNOWN},
    "locale": lambda value: SAFE_LOCALE_RE.match(value) is not None or value == UNKNOWN,
    "timezone": lambda value: SAFE_TIMEZONE_RE.match(value) is not None or value in {"UTC", UNKNOWN},
    "custody_lifecycle_state": lambda value: SAFE_CODE_RE.match(value) is not None,
    "upload_queue_item_state": lambda value: SAFE_CODE_RE.match(value) is not None,
    "retry_class": lambda value: SAFE_CODE_RE.match(value) is not None,
    "retry_mode": lambda value: SAFE_CODE_RE.match(value) is not None,
    "normal_user_action": lambda value: SAFE_CODE_RE.match(value) is not None,
    "failure_category": lambda value: SAFE_CODE_RE.match(value) is not None,
    "problem_code": lambda value: SAFE_CODE_RE.match(value) is not None,
    "sync_conflict_state": lambda value: SAFE_CODE_RE.match(value) is not None,
    "created_at": lambda value: SAFE_TIMESTAMP_RE.match(value) is not None,
    "updated_at": lambda value: SAFE_TIMESTAMP_RE.match(value) is not None,
    "retention_deadline": lambda value: SAFE_TIMESTAMP_RE.match(value) is not None,
    "data_loss_risk": lambda value: SAFE_CODE_RE.match(value) is not None,
    "last_attempt_at": lambda value: SAFE_TIMESTAMP_RE.match(value) is not None or value in SAFE_SENTINELS,
    "next_retry_at": lambda value: SAFE_TIMESTAMP_RE.match(value) is not None or value in SAFE_SENTINELS,
    "last_safe_http_status": lambda value: value in SAFE_SENTINELS or value.isdigit(),
    "last_safe_problem_code": lambda value: SAFE_CODE_RE.match(value) is not None or value in SAFE_SENTINELS,
    "local_purge_state": lambda value: SAFE_CODE_RE.match(value) is not None,
    "local_purge_ack_state": lambda value: SAFE_CODE_RE.match(value) is not None,
    "processing_status": lambda value: SAFE_CODE_RE.match(value) is not None,
    "app_queue_schema_version": lambda value: SAFE_CODE_RE.match(value) is not None,
    "ledger_schema_version": lambda value: SAFE_CODE_RE.match(value) is not None,
    "redaction_state": lambda value: value == "metadata_only",
}

SAFE_LOCAL_PURGE_TASK_VALUES = {
    "purge_local_buffers",
    "purge_local_exports",
    "confirm_local_expiry",
    "pending",
    "claimed",
    "acknowledged",
    "failed",
    "unreachable",
    "expired",
    "local_expiry_relied_upon",
}


class SupportIncidentRedactionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def build_server_redacted_report(
    payload: Mapping[str, Any],
    *,
    received_at: datetime | None = None,
) -> dict[str, Any]:
    if payload.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        raise SupportIncidentRedactionError("support_incident.unsupported_schema")
    if payload.get("redaction_state") != "metadata_only":
        raise SupportIncidentRedactionError("support_incident.unsafe_payload")
    if blocking_unsafe_unknown_fields(payload):
        raise SupportIncidentRedactionError("support_incident.unsafe_payload")

    forbidden_count = count_forbidden_content(payload)
    report: dict[str, Any] = {}
    for field in ALLOWED_REPORT_FIELDS:
        value, redacted_count = _redact_field(field, payload.get(field, UNKNOWN))
        report[field] = value
        forbidden_count += redacted_count

    now = received_at or datetime.now(UTC)
    report["received_at"] = now.isoformat().replace("+00:00", "Z")
    report["server_redaction_version"] = SERVER_REDACTION_VERSION
    report["redaction_result"] = "accepted_with_redactions" if forbidden_count else "accepted"
    report["forbidden_field_count"] = forbidden_count

    report["safe_report_fingerprint"] = stable_report_fingerprint(report)
    report["dedupe_key"] = derive_dedupe_key(report)
    report["affected_identity_fingerprint"] = derive_affected_identity(report)
    return report


def canonical_report_json(report: Mapping[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def stable_report_fingerprint(report: Mapping[str, Any]) -> str:
    stable_report = {
        key: value for key, value in report.items() if key not in REPORT_FINGERPRINT_EXCLUDED_FIELDS
    }
    return _fingerprint("report_fpr", canonical_report_json(stable_report))


def count_forbidden_content(value: Any) -> int:
    count = 0
    if isinstance(value, Mapping):
        for key, nested in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in UNSAFE_KEY_PARTS):
                count += 1
            count += count_forbidden_content(nested)
    elif isinstance(value, list):
        count += sum(count_forbidden_content(item) for item in value)
    elif isinstance(value, str) and _is_unsafe_string(value):
        count += 1
    return count


def blocking_unsafe_unknown_fields(payload: Mapping[str, Any]) -> tuple[str, ...]:
    blocked: list[str] = []
    for key, value in payload.items():
        if key in ALLOWED_REPORT_FIELDS:
            continue
        lowered = str(key).lower()
        if any(part in lowered for part in BLOCKING_UNKNOWN_KEY_PARTS) or count_forbidden_content(
            value
        ):
            blocked.append(str(key))
    return tuple(sorted(blocked))


def derive_dedupe_key(report: Mapping[str, Any]) -> str:
    parts = [
        str(report.get("problem_code", UNKNOWN)),
        str(report.get("failure_category", UNKNOWN)),
        str(report.get("retry_class", UNKNOWN)),
        str(report.get("sync_conflict_state", UNKNOWN)),
        str(report.get("workspace_fingerprint", UNKNOWN)),
        str(report.get("device_fingerprint", UNKNOWN)),
        str(report.get("build_version", UNKNOWN)),
    ]
    return _fingerprint("support_dedupe", "|".join(parts), length=24)


def derive_affected_identity(report: Mapping[str, Any]) -> str:
    parts = [
        str(report.get("workspace_fingerprint", UNKNOWN)),
        str(report.get("device_fingerprint", UNKNOWN)),
        str(report.get("local_recording_id_fingerprint", UNKNOWN)),
        str(report.get("safe_recording_identity", UNKNOWN)),
    ]
    return _fingerprint("affected", "|".join(parts), length=20)


def _redact_field(field: str, value: Any) -> tuple[Any, int]:
    if value is None:
        return UNKNOWN, 0
    if field == "environment_base_url_identity":
        return _safe_base_identity(value)
    if field in BOOL_FIELDS:
        return value if isinstance(value, bool) else UNKNOWN, 0
    if field in INT_FIELDS:
        return value if isinstance(value, int) and value >= 0 else UNKNOWN, 0
    if field in NESTED_ALLOWED_FIELDS:
        return _redact_nested(field, value)
    if field == "local_purge_tasks":
        return _redact_safe_list(value, limit=10, item_validator=_is_safe_local_purge_task)
    if field == "safe_affected_identities":
        return _redact_safe_list(value, limit=5, item_validator=_is_safe_affected_identity)
    if field in FINGERPRINT_FIELDS:
        return _redact_safe_identity(value, allow_device_prefix=False, allow_recording_prefix=False)
    if field == "safe_device_identifier":
        return _redact_safe_identity(value, allow_device_prefix=True, allow_recording_prefix=False)
    if field == "safe_recording_identity":
        return _redact_safe_identity(value, allow_device_prefix=False, allow_recording_prefix=True)
    if isinstance(value, str):
        return _redact_string_field(field, value)
    return value if isinstance(value, bool | int | float) else REDACTED_METADATA, 1


def _redact_string_field(field: str, value: str) -> tuple[str, int]:
    validator = STRICT_STRING_FIELD_VALIDATORS.get(field)
    if validator is None:
        return REDACTED_METADATA, 1
    if _is_unsafe_string(value) or not validator(value):
        return REDACTED_METADATA, 1
    return value, 0


def _redact_nested_string_value(field: str, value: str) -> tuple[str, int]:
    if _is_unsafe_string(value):
        return REDACTED_METADATA, 1
    if field == "manifest_schema_version" and SAFE_CODE_RE.match(value):
        return value, 0
    if field in {"total_size_bucket", "duration_bucket"} and SAFE_CODE_RE.match(value):
        return value, 0
    return REDACTED_METADATA, 1


def _redact_nested(field: str, value: Any) -> tuple[dict[str, Any], int]:
    allowed = NESTED_ALLOWED_FIELDS[field]
    if not isinstance(value, Mapping):
        return {}, 0
    redacted: dict[str, Any] = {}
    count = 0
    for key in sorted(allowed):
        if key not in value:
            continue
        nested = value[key]
        if isinstance(nested, str):
            safe_nested, redacted_count = _redact_nested_string_value(key, nested)
            redacted[key] = safe_nested
            count += redacted_count
        elif isinstance(nested, bool | int):
            redacted[key] = nested
        else:
            redacted[key] = REDACTED_METADATA
            count += 1
    return redacted, count


def _redact_safe_list(
    value: Any,
    *,
    limit: int | None = None,
    item_validator: Callable[[Any], bool] | None = None,
) -> tuple[list[Any], int]:
    if not isinstance(value, list):
        return [], 0
    redacted: list[Any] = []
    count = 0
    for item in value[:limit]:
        is_safe = item_validator(item) if item_validator is not None else _is_safe_text(item)
        if is_safe:
            redacted.append(item)
        else:
            redacted.append(REDACTED_METADATA)
            count += 1
    return redacted, count


def _redact_safe_identity(
    value: Any,
    *,
    allow_device_prefix: bool,
    allow_recording_prefix: bool,
) -> tuple[str, int]:
    if not isinstance(value, str):
        return REDACTED_METADATA, 1
    if value in SAFE_SENTINELS or SAFE_FINGERPRINT_RE.match(value):
        return value, 0
    if (
        allow_device_prefix
        and value.startswith("device:")
        and _is_safe_fingerprint(value.removeprefix("device:"))
    ):
        return value, 0
    if (
        allow_recording_prefix
        and value.startswith(("local:", "server:"))
        and _is_safe_fingerprint(value.split(":", 1)[1])
    ):
        return value, 0
    return REDACTED_METADATA, 1


def _is_safe_text(value: Any) -> bool:
    return (
        isinstance(value, str)
        and not _is_unsafe_string(value)
        and SAFE_TEXT_RE.match(value) is not None
    )


def _is_safe_fingerprint(value: str) -> bool:
    return value in SAFE_SENTINELS or SAFE_FINGERPRINT_RE.match(value) is not None


def _is_safe_affected_identity(value: Any) -> bool:
    return isinstance(value, str) and SAFE_AFFECTED_FINGERPRINT_RE.match(value) is not None


def _safe_base_identity(value: Any) -> tuple[str, int]:
    if not isinstance(value, str) or _is_unsafe_string(value):
        if isinstance(value, str):
            parsed = urlsplit(value if "://" in value else f"https://{value}")
            if parsed.hostname:
                return parsed.hostname.lower(), 1
        return REDACTED_METADATA, 1
    parsed = urlsplit(value if "://" in value else f"https://{value}")
    host = parsed.hostname or value
    return host.lower(), 0


def _is_unsafe_string(value: str) -> bool:
    return bool(
        EMAIL_RE.search(value)
        or BEARER_RE.search(value)
        or SECRET_RE.search(value)
        or SIGNED_URL_RE.search(value)
        or RAW_PATH_RE.search(value)
        or "transcript text" in value.lower()
        or "meeting content" in value.lower()
    )


def _fingerprint(prefix: str, value: str, *, length: int = 16) -> str:
    digest = sha256(value.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}_{digest}"


def _is_safe_local_purge_task(value: Any) -> bool:
    return isinstance(value, str) and value in SAFE_LOCAL_PURGE_TASK_VALUES
