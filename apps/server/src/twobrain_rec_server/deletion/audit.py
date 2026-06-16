from __future__ import annotations

from enum import StrEnum
from typing import Any

SAFE_METADATA_KEYS = frozenset(
    {
        "state",
        "artifact_class",
        "control_scope",
        "dependency_name",
        "policy_source",
        "backup_expiry_days",
        "outcome",
        "attempt_count",
        "safe_reason",
        "reason_code",
        "request_source",
        "task_type",
        "device_state",
    }
)

PRIVATE_KEY_FRAGMENTS = (
    "authorization",
    "bearer",
    "credential",
    "external_job_id",
    "file",
    "hash",
    "key",
    "local_path",
    "object",
    "path",
    "payload",
    "secret",
    "signed_url",
    "summary",
    "token",
    "transcript",
    "url",
)

PRIVATE_VALUE_FRAGMENTS = (
    "bearer ",
    "credential",
    "/users/",
    "object_key",
    "secret",
    "signed",
    "transcript",
)


def build_lifecycle_audit_metadata(**metadata: Any) -> dict[str, str | int | bool | None]:
    """Return a metadata-only lifecycle audit payload or fail closed."""

    sanitized: dict[str, str | int | bool | None] = {}
    for key, value in metadata.items():
        _assert_safe_key(key)
        sanitized[key] = _sanitize_value(value)
    return sanitized


def _assert_safe_key(key: str) -> None:
    normalized = key.lower()
    if key not in SAFE_METADATA_KEYS or any(fragment in normalized for fragment in PRIVATE_KEY_FRAGMENTS):
        raise ValueError("lifecycle audit metadata-only payload rejected")


def _sanitize_value(value: Any) -> str | int | bool | None:
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, str):
        normalized = value.lower()
        if any(fragment in normalized for fragment in PRIVATE_VALUE_FRAGMENTS):
            raise ValueError("lifecycle audit metadata-only payload rejected")
        return value
    raise ValueError("lifecycle audit metadata-only payload rejected")
