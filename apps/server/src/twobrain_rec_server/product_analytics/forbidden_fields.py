from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

SAFE_IDENTIFIER_FIELDS = {
    "stable_pseudonymous_user_id",
    "posthog_distinct_id",
    "workspace_pseudonym",
    "account_pseudonym",
    "graf_attribution_id",
    "bridge_token_hash",
    "bridge_present",
    "posthog_anonymous_id_present",
    "yandex_client_id_present",
    "yandex_user_id_present",
    "yclid_present",
}

FORBIDDEN_FIELD_NAMES = (
    "email",
    "phone",
    "full_name",
    "first_name",
    "last_name",
    "display_name",
    "company_name",
    "organization_name",
    "workspace_name",
    "account_name",
    "raw_user_id",
    "raw_account_id",
    "raw_workspace_id",
    "raw_meeting_id",
    "raw_device_id",
    "user_id",
    "account_id",
    "workspace_id",
    "meeting_id",
    "device_id",
    "device_name",
    "machine_id",
    "local_username",
    "local_path",
    "local_file_path",
    "file_path",
    "object_key",
    "signed_url",
    "signed_download_url",
    "oauth_code",
    "authorization_code",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "oauth_token",
    "api_key",
    "secret",
    "client_secret",
    "provider_secret",
    "posthog_project_key",
    "yandex_oauth_token",
    "yandex_counter_id",
    "password",
    "passcode",
    "cookie",
    "authorization",
    "meeting_title",
    "meeting_link",
    "participants",
    "participant_names",
    "calendar_event_id",
    "calendar_text",
    "transcript",
    "transcript_text",
    "summary_text",
    "generated_summary",
    "raw_audio",
    "audio",
    "audio_url",
    "private_text",
    "free_text",
)

_FORBIDDEN_EXACT_KEYS = set(FORBIDDEN_FIELD_NAMES)
_FORBIDDEN_KEY_PARTS = (
    "access_token",
    "refresh_token",
    "id_token",
    "oauth_token",
    "oauth_code",
    "authorization_code",
    "api_key",
    "signed_url",
    "signed_download_url",
    "local_path",
    "object_key",
    "meeting_title",
    "calendar_text",
    "transcript",
    "raw_audio",
)
SECURITY_CREDENTIAL_FIELD_NAMES = (
    "local_path",
    "local_file_path",
    "file_path",
    "object_key",
    "signed_url",
    "signed_download_url",
    "oauth_code",
    "authorization_code",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "oauth_token",
    "api_key",
    "secret",
    "client_secret",
    "provider_secret",
    "posthog_project_key",
    "yandex_oauth_token",
    "password",
    "passcode",
    "cookie",
    "authorization",
    "calendar_text",
    "transcript",
    "transcript_text",
    "summary_text",
    "generated_summary",
    "raw_audio",
    "audio",
    "audio_url",
    "private_text",
    "free_text",
    "raw_payload",
)
_SECURITY_CREDENTIAL_EXACT_KEYS = set(SECURITY_CREDENTIAL_FIELD_NAMES)
_SECURITY_CREDENTIAL_KEY_PARTS = (
    "access_token",
    "refresh_token",
    "id_token",
    "oauth_token",
    "oauth_code",
    "authorization_code",
    "api_key",
    "signed_url",
    "signed_download_url",
    "local_path",
    "object_key",
    "calendar_text",
    "transcript",
    "raw_audio",
    "raw_payload",
)
_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{8,}\d)")
_SECRET_WORD_RE = re.compile(
    r"(access[_-]?token|refresh[_-]?token|id[_-]?token|api[_-]?key|secret|password|passcode|signed[_-]?url)",
    re.IGNORECASE,
)
_LOCAL_PATH_RE = re.compile(r"(^|[\s=:])(/Users/|/home/|[A-Za-z]:\\)")
_SAFE_PSEUDONYMOUS_VALUE_RE = re.compile(r"^graf_pseudo_(?:user|workspace|account|bridge)_[0-9a-f]{8,64}$")


@dataclass(frozen=True, slots=True)
class ForbiddenFieldViolation(ValueError):
    """Raised when an analytics payload contains private or content-bearing data."""

    paths: tuple[str, ...]

    def __str__(self) -> str:
        return "forbidden analytics fields: " + ", ".join(self.paths)


def find_forbidden_fields(payload: Mapping[str, Any] | Sequence[Any] | Any) -> tuple[str, ...]:
    findings: list[str] = []
    _walk(payload, "$", findings)
    return tuple(dict.fromkeys(findings))


def assert_no_forbidden_fields(payload: Mapping[str, Any] | Sequence[Any] | Any) -> None:
    findings = find_forbidden_fields(payload)
    if findings:
        raise ForbiddenFieldViolation(findings)


def find_security_credential_fields(payload: Mapping[str, Any] | Sequence[Any] | Any) -> tuple[str, ...]:
    findings: list[str] = []
    _walk(
        payload,
        "$",
        findings,
        key_predicate=_is_security_credential_key,
        value_predicate=_is_security_credential_value,
    )
    return tuple(dict.fromkeys(findings))


def assert_no_security_credential_fields(payload: Mapping[str, Any] | Sequence[Any] | Any) -> None:
    findings = find_security_credential_fields(payload)
    if findings:
        raise ForbiddenFieldViolation(findings)


def _walk(
    value: Any,
    path: str,
    findings: list[str],
    *,
    key_predicate=None,
    value_predicate=None,
) -> None:
    key_predicate = key_predicate or _is_forbidden_key
    value_predicate = value_predicate or _is_forbidden_value
    if isinstance(value, Mapping):
        for raw_key, nested in value.items():
            key = str(raw_key)
            nested_path = f"{path}.{key}" if path else key
            if key_predicate(key):
                findings.append(nested_path)
                continue
            _walk(nested, nested_path, findings, key_predicate=key_predicate, value_predicate=value_predicate)
        return
    if isinstance(value, str) and value_predicate(value):
        findings.append(path)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _walk(
                nested,
                f"{path}[{index}]",
                findings,
                key_predicate=key_predicate,
                value_predicate=value_predicate,
            )


def _is_forbidden_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    if normalized in SAFE_IDENTIFIER_FIELDS:
        return False
    if normalized in _FORBIDDEN_EXACT_KEYS:
        return True
    if any(part in normalized for part in _FORBIDDEN_KEY_PARTS):
        return True
    return normalized.endswith(("_token", "_secret", "_password", "_passcode", "_cookie"))


def _is_forbidden_value(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    if _SAFE_PSEUDONYMOUS_VALUE_RE.fullmatch(stripped):
        return False
    if _EMAIL_RE.search(stripped) or _PHONE_RE.search(stripped):
        return True
    if _SECRET_WORD_RE.search(stripped):
        return True
    return bool(_LOCAL_PATH_RE.search(stripped))


def _is_security_credential_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    if normalized in SAFE_IDENTIFIER_FIELDS:
        return False
    if normalized in _SECURITY_CREDENTIAL_EXACT_KEYS:
        return True
    if any(part in normalized for part in _SECURITY_CREDENTIAL_KEY_PARTS):
        return True
    return normalized.endswith(("_token", "_secret", "_password", "_passcode", "_cookie"))


def _is_security_credential_value(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    if _SAFE_PSEUDONYMOUS_VALUE_RE.fullmatch(stripped):
        return False
    if _SECRET_WORD_RE.search(stripped):
        return True
    return bool(_LOCAL_PATH_RE.search(stripped))
