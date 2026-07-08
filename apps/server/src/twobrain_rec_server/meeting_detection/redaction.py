from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


class MeetingDetectionRedactionError(ValueError):
    """Raised when meeting-detection metadata contains forbidden content."""


FORBIDDEN_KEY_TOKENS = (
    "audio",
    "transcript",
    "summary",
    "screen",
    "raw_log",
    "raw_unified",
    "url",
    "passcode",
    "password",
    "secret",
    "token",
    "signed_url",
    "attendee_email",
    "email",
    "agenda",
    "private_title",
    "app_path",
    "home_path",
    "remote_ip",
    "ip_address",
)

FORBIDDEN_VALUE_MARKERS = (
    "raw unified-log",
    "raw_unified_log",
    "transcript_text",
    "raw_audio",
    "meeting content",
    "signed_url",
    "x-amz-",
    "authorization:",
    "bearer ",
    "passcode",
    "password",
    "secret",
)

URL_RE = re.compile(r"https?://", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
RAW_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
HOME_PATH_RE = re.compile(r"(?i)(/Users/[^\s'\"]+|[A-Z]:\\Users\\[^\s'\"]+)")


@dataclass(frozen=True, slots=True)
class RedactionFinding:
    path: str
    reason: str


def forbidden_content_findings(payload: Any, *, path: str = "$") -> list[RedactionFinding]:
    findings: list[RedactionFinding] = []
    _scan(payload, path=path, findings=findings)
    return findings


def assert_metadata_only(payload: Any) -> None:
    findings = forbidden_content_findings(payload)
    if findings:
        reasons = ", ".join(f"{finding.path}:{finding.reason}" for finding in findings[:5])
        raise MeetingDetectionRedactionError(f"meeting detection payload contains forbidden content: {reasons}")


def _scan(value: Any, *, path: str, findings: list[RedactionFinding]) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            key_lower = key_text.lower()
            if any(token in key_lower for token in FORBIDDEN_KEY_TOKENS):
                findings.append(RedactionFinding(f"{path}.{key_text}", "forbidden_key"))
            _scan(nested, path=f"{path}.{key_text}", findings=findings)
        return
    if isinstance(value, str):
        _scan_string(value, path=path, findings=findings)
        return
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        for index, nested in enumerate(value):
            _scan(nested, path=f"{path}[{index}]", findings=findings)


def _scan_string(value: str, *, path: str, findings: list[RedactionFinding]) -> None:
    lowered = value.lower()
    if any(marker in lowered for marker in FORBIDDEN_VALUE_MARKERS):
        findings.append(RedactionFinding(path, "forbidden_marker"))
    if URL_RE.search(value):
        findings.append(RedactionFinding(path, "raw_url"))
    if EMAIL_RE.search(value):
        findings.append(RedactionFinding(path, "email"))
    if RAW_IPV4_RE.search(value):
        findings.append(RedactionFinding(path, "raw_ip"))
    if HOME_PATH_RE.search(value):
        findings.append(RedactionFinding(path, "home_path"))
