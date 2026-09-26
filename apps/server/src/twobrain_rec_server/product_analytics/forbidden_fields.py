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
    "ip_address",
    "client_ip",
    "remote_address",
    "device_address",
    "device_ip",
    "user_agent",
    "user_agent_string",
    "device_fingerprint",
    "fingerprint",
    "browser_fingerprint",
    "session_id",
    "session_identifier",
    "visit_id",
    "visit_identifier",
    "anonymous_id",
    "cookie_id",
    "browser_id",
    "yclid",
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
# The loose phone shape of a generic payload value. It is a *candidate* shape,
# never the final answer: a date such as ``2026-09-18`` is nothing but a run of
# digits joined by separators, and this pattern used to read it as a number
# (FR-008 must not turn an ``occurred_at`` timestamp into a rejected field).
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{8,}\d)")
# A date or a timestamp in the shapes the measurement actually stores:
# ``2026-09-18``, ``2026-09-18T12:00:00+00:00``, ``2026-09-18 12:00:00Z`` and a
# date range are dates, not phone numbers. A real phone number is written with
# three or more groups of uneven length ("8-916-123-45-67"), so it never
# matches this shape, while every masked token is removed before the phone
# check — a phone written next to a date is still found.
_DATE_OR_TIME_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}"
    r"(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,9})?)?(?:Z|[+-]\d{2}:?\d{2})?)?"
)
# A phone number carries at least this many digits. A date carries eight and a
# version such as ``1.2.3`` carries three, so neither can reach the threshold;
# a bare run of ten or more digits (a click identifier, a raw numeric
# identifier) still can, exactly as before.
MINIMUM_PHONE_DIGITS = 10
_SECRET_WORD_RE = re.compile(
    r"(access[_-]?token|refresh[_-]?token|id[_-]?token|api[_-]?key|secret|password|passcode|signed[_-]?url)",
    re.IGNORECASE,
)
_LOCAL_PATH_RE = re.compile(r"(^|[\s=:])(/Users/|/home/|[A-Za-z]:\\)")
_SAFE_PSEUDONYMOUS_VALUE_RE = re.compile(r"^graf_pseudo_(?:user|workspace|account|bridge)_[0-9a-f]{8,64}$")
_IPV4_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
# A strict IPv6 shape: either the full eight-group form or a compressed form
# with ``::``. A loose pattern would flag ordinary clock and timestamp values.
_IPV6_RE = re.compile(
    r"(?<![\w:])(?:[0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4}(?![\w:])"
    r"|(?<![\w:])[0-9A-Fa-f:]*::[0-9A-Fa-f:]*(?![\w:])"
)
_USER_AGENT_RE = re.compile(
    r"(mozilla/\d|applewebkit/|gecko/\d|chrome/\d|safari/\d|edg/|opr/|curl/\d|python-requests/|wget/|headlesschrome|bot/\d|crawler)",
    re.IGNORECASE,
)
_ANY_PSEUDONYM_RE = re.compile(r"^graf_pseudo_[a-z_]*[0-9a-f]{4,}$|^graf_pseudo_browser")
# Phone-shaped values inside the new entities must contain a ``+`` prefix or a
# separator, so a bare click identifier such as ``yclid`` is not mistaken for a
# phone number.
_PHONE_LIKE_RE = re.compile(
    r"(?:\+\d[\d\s().-]{7,}\d)|(?:\d{1,4}[\s().-]\d[\d\s().-]{5,}\d)"
)


def _mask_dates_and_times(value: str) -> str:
    """Remove date and time tokens, so none of them can read as a phone number.

    Only the date token is removed: everything around it stays in place, so a
    phone number written beside a timestamp is still detected.
    """
    return _DATE_OR_TIME_RE.sub(" ", value)


def _looks_like_a_phone_number(value: str, pattern: re.Pattern[str]) -> bool:
    """Say whether a value carries a phone number rather than a date or a time.

    Two rules together, because either one alone is wrong: the date and time
    tokens are masked first, so ``2026-09-18T12:00:00+00:00`` is a timestamp; and
    what remains must carry at least :data:`MINIMUM_PHONE_DIGITS` digits, so a
    version such as ``1.2.3`` or a short numeric identifier is not a phone.
    """
    candidate = _mask_dates_and_times(value)
    return any(
        sum(character.isdigit() for character in match.group()) >= MINIMUM_PHONE_DIGITS
        for match in pattern.finditer(candidate)
    )

# Level 1 (anonymous aggregate) and the two level 2 entities added by feature
# 273 use closed allowlists: a key outside the entity's own contract is a
# violation, so a new field can never leak identifiers by accident.
ANONYMOUS_AGGREGATE_ALLOWED_FIELDS = (
    "bucket_date",
    "bucket_hour",
    "surface",
    "landing_path",
    "source",
    "medium",
    "campaign",
    "content",
    "term",
    "device_class",
    "referrer_category",
    "traffic_class",
    "visits",
)
VISIT_ATTRIBUTION_ALLOWED_FIELDS = (
    "attribution_ref",
    "source",
    "medium",
    "campaign",
    "content",
    "term",
    "yclid",
    "landing_path",
    "first_seen_at",
    "expires_at",
)
CLIENT_ACQUISITION_ALLOWED_FIELDS = (
    "account_pseudonym",
    "source",
    "medium",
    "campaign",
    "content",
    "term",
    "yclid_present",
    "graf_attribution_id",
    "landing_path",
    "attribution_rule",
    "attribution_confidence",
    "captured_at",
)


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


def find_anonymous_aggregate_violations(
    payload: Mapping[str, Any] | Sequence[Any] | Any,
) -> tuple[str, ...]:
    """Return paths that would turn a level 1 bucket into personal data.

    Level 1 gets its legal basis from the complete absence of identifiers, so
    this check is stricter than the general one: any key outside the aggregate
    contract, any pseudonym (even the "safe" one built by ``identity.py``) and
    any identifier-shaped value is a violation.
    """
    findings: list[str] = []
    _walk_allowlisted(
        payload,
        "$",
        findings,
        allowed_fields=ANONYMOUS_AGGREGATE_ALLOWED_FIELDS,
        value_predicate=_is_anonymous_identifier_value,
    )
    return tuple(dict.fromkeys(findings))


def assert_no_anonymous_aggregate_identifiers(payload: Mapping[str, Any] | Sequence[Any] | Any) -> None:
    findings = find_anonymous_aggregate_violations(payload)
    if findings:
        raise ForbiddenFieldViolation(findings)


def find_visit_attribution_violations(
    payload: Mapping[str, Any] | Sequence[Any] | Any,
) -> tuple[str, ...]:
    """Level 2 visit attribution: only its own contract plus safe campaign labels."""
    findings: list[str] = []
    _walk_allowlisted(
        payload,
        "$",
        findings,
        allowed_fields=VISIT_ATTRIBUTION_ALLOWED_FIELDS,
        value_predicate=_is_entity_identifier_value,
    )
    return tuple(dict.fromkeys(findings))


def assert_safe_visit_attribution(payload: Mapping[str, Any] | Sequence[Any] | Any) -> None:
    findings = find_visit_attribution_violations(payload)
    if findings:
        raise ForbiddenFieldViolation(findings)


def find_client_acquisition_violations(
    payload: Mapping[str, Any] | Sequence[Any] | Any,
) -> tuple[str, ...]:
    """Level 2 client acquisition attribute.

    The attribute keys on a pseudonymous account, never on a raw account id:
    the analytics-safe view is checked here, the storage row lives in the
    product database and is not an analytics payload.
    """
    findings: list[str] = []
    _walk_allowlisted(
        payload,
        "$",
        findings,
        allowed_fields=CLIENT_ACQUISITION_ALLOWED_FIELDS,
        value_predicate=_is_entity_identifier_value,
    )
    return tuple(dict.fromkeys(findings))


def assert_safe_client_acquisition_attribute(payload: Mapping[str, Any] | Sequence[Any] | Any) -> None:
    findings = find_client_acquisition_violations(payload)
    if findings:
        raise ForbiddenFieldViolation(findings)


def find_identifier_value_fields(payload: Mapping[str, Any] | Sequence[Any] | Any) -> tuple[str, ...]:
    """Return paths whose value looks like a device address, user agent or pseudonym."""
    findings: list[str] = []
    _walk_values(payload, "$", findings, value_predicate=_is_anonymous_identifier_value)
    return tuple(dict.fromkeys(findings))


def _walk_allowlisted(
    value: Any,
    path: str,
    findings: list[str],
    *,
    allowed_fields: tuple[str, ...],
    value_predicate,
) -> None:
    allowed = set(allowed_fields)
    if isinstance(value, Mapping):
        for raw_key, nested in value.items():
            key = str(raw_key).strip().lower().replace("-", "_")
            nested_path = f"{path}.{key}"
            if key not in allowed:
                findings.append(nested_path)
                continue
            _walk_allowlisted(
                nested,
                nested_path,
                findings,
                allowed_fields=allowed_fields,
                value_predicate=value_predicate,
            )
        return
    if isinstance(value, str) and value_predicate(value):
        findings.append(path)
        return
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for index, nested in enumerate(value):
            _walk_allowlisted(
                nested,
                f"{path}[{index}]",
                findings,
                allowed_fields=allowed_fields,
                value_predicate=value_predicate,
            )


def _walk_values(value: Any, path: str, findings: list[str], *, value_predicate) -> None:
    if isinstance(value, Mapping):
        for raw_key, nested in value.items():
            key = str(raw_key).strip().lower().replace("-", "_")
            _walk_values(nested, f"{path}.{key}", findings, value_predicate=value_predicate)
        return
    if isinstance(value, str) and value_predicate(value):
        findings.append(path)
        return
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for index, nested in enumerate(value):
            _walk_values(nested, f"{path}[{index}]", findings, value_predicate=value_predicate)


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
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
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
    if _EMAIL_RE.search(stripped) or _looks_like_a_phone_number(stripped, _PHONE_RE):
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


def _is_anonymous_identifier_value(value: str) -> bool:
    """Level 1 values: no identifier, not even an approved level 2 pseudonym.

    The legacy loose phone pattern is deliberately not reused here: level 1
    stores ISO dates such as ``2026-09-18``, which that pattern reads as a
    phone number.
    """
    stripped = value.strip()
    if not stripped:
        return False
    if _has_contact_or_secret_value(stripped):
        return True
    if _ANY_PSEUDONYM_RE.fullmatch(stripped):
        return True
    return _looks_like_network_identifier(stripped)


def _is_entity_identifier_value(value: str) -> bool:
    """Level 2 entities: campaign labels, click identifiers and timestamps only.

    Approved level 2 pseudonyms stay allowed here; raw identifiers, contact
    details, user agents and network addresses remain violations.
    """
    stripped = value.strip()
    if not stripped:
        return False
    if _has_contact_or_secret_value(stripped):
        return True
    if _SAFE_PSEUDONYMOUS_VALUE_RE.fullmatch(stripped):
        return False
    return _looks_like_network_identifier(stripped)


def _has_contact_or_secret_value(value: str) -> bool:
    return bool(
        _EMAIL_RE.search(value)
        or _looks_like_a_phone_number(value, _PHONE_LIKE_RE)
        or _SECRET_WORD_RE.search(value)
        or _LOCAL_PATH_RE.search(value)
    )


def _looks_like_network_identifier(value: str) -> bool:
    if _USER_AGENT_RE.search(value):
        return True
    return bool(_IPV4_RE.search(value) or _IPV6_RE.search(value))
