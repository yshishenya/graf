"""Metadata-only access governance evidence for analytics provider readiness.

This module deliberately does not talk to PostHog, Yandex or any other
provider.  It reads one operator-maintained state file outside git and uses it
to decide whether a *live readiness claim* is supportable.  A state file is
proof of a reviewed metadata record, not proof of live membership: the record
contains counts, review statuses and digests, never names, addresses,
credentials or provider responses.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from twobrain_rec_server.product_analytics.forbidden_fields import (
    find_security_credential_fields,
)

ACCESS_GOVERNANCE_STATE_FILE_ENV = "GRAF_PRODUCT_ANALYTICS_ACCESS_GOVERNANCE_STATE_FILE"
ACCESS_GOVERNANCE_STATE_DIR_ENV = "GRAF_PRODUCT_ANALYTICS_ACCESS_GOVERNANCE_STATE_DIR"
DEFAULT_ACCESS_GOVERNANCE_STATE_DIR = "/var/lib/graf-product-analytics-access"
DEFAULT_ACCESS_GOVERNANCE_STATE_NAME = "access-governance-state"
ACCESS_GOVERNANCE_STATE_VERSION = "1"
ACCESS_GOVERNANCE_MAX_BYTES = 64 * 1024
MINIMUM_ACCEPTED_OPERATORS = 2
MINIMUM_MFA_OPERATORS = 2
REQUIRED_REVIEW_STATE = "complete"
DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")

BLOCKER_ACCESS_STATE_UNAVAILABLE = "access_governance_state_unavailable"
BLOCKER_ACCESS_STATE_INVALID = "access_governance_state_invalid"
BLOCKER_ACCESS_STATE_STALE = "access_governance_state_stale"
BLOCKER_ACCEPTED_OPERATORS_BELOW_MINIMUM = "access_governance_accepted_operators_below_minimum"
BLOCKER_MFA_OPERATORS_BELOW_MINIMUM = "access_governance_mfa_operators_below_minimum"
BLOCKER_DIGEST_MISMATCH = "access_governance_guard_digest_mismatch"
BLOCKER_REVOCATION_REVIEW_MISSING = "access_governance_revocation_review_missing"
BLOCKER_ROTATION_REVIEW_MISSING = "access_governance_rotation_review_missing"
BLOCKER_AUDIT_REVIEW_MISSING = "access_governance_audit_review_missing"

_REVIEW_FIELDS = (
    "revocation_review",
    "credential_rotation_review",
    "audit_review",
)
_REQUIRED_FIELDS = {
    "access_governance_state_version",
    "reviewed_at",
    "expires_at",
    "accepted_operator_count",
    "mfa_operator_count",
    "repository_digest",
    "config_digest",
    "installed_guard_digest",
    *_REVIEW_FIELDS,
}


@dataclass(frozen=True, slots=True)
class AccessGovernanceEvidence:
    """Parsed metadata-only evidence; no provider membership is inferred."""

    state_available: bool = False
    state_readable: bool = False
    state_valid: bool = False
    reviewed_at: int | None = None
    expires_at: int | None = None
    accepted_operator_count: int | None = None
    mfa_operator_count: int | None = None
    repository_digest: str | None = None
    config_digest: str | None = None
    installed_guard_digest: str | None = None
    revocation_review: str | None = None
    credential_rotation_review: str | None = None
    audit_review: str | None = None
    file_errors: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """Return owned scalar metadata only; no path or live provider object."""

        return {
            "evidence": "metadata_only",
            "state_available": self.state_available,
            "state_readable": self.state_readable,
            "state_valid": self.state_valid,
            "reviewed_at": self.reviewed_at,
            "expires_at": self.expires_at,
            "accepted_operator_count": self.accepted_operator_count,
            "mfa_operator_count": self.mfa_operator_count,
            "repository_digest": self.repository_digest,
            "config_digest": self.config_digest,
            "installed_guard_digest": self.installed_guard_digest,
            "revocation_review": self.revocation_review,
            "credential_rotation_review": self.credential_rotation_review,
            "audit_review": self.audit_review,
            "file_errors": list(self.file_errors),
        }


def access_governance_state_file_path(environ: Mapping[str, str] | None = None) -> str:
    environment = os.environ if environ is None else environ
    explicit = environment.get(ACCESS_GOVERNANCE_STATE_FILE_ENV)
    if explicit:
        return explicit
    directory = environment.get(ACCESS_GOVERNANCE_STATE_DIR_ENV) or DEFAULT_ACCESS_GOVERNANCE_STATE_DIR
    return os.path.join(directory, DEFAULT_ACCESS_GOVERNANCE_STATE_NAME)


def _read_state(path: str) -> tuple[bool, bool, str | None, tuple[str, ...]]:
    """Read bounded UTF-8 text and distinguish missing from unreadable state."""

    state_path = Path(path)
    try:
        state_path.stat()
    except FileNotFoundError:
        return False, False, None, (BLOCKER_ACCESS_STATE_UNAVAILABLE,)
    except OSError:
        return True, False, None, (BLOCKER_ACCESS_STATE_UNAVAILABLE,)
    try:
        if state_path.stat().st_size > ACCESS_GOVERNANCE_MAX_BYTES:
            return True, False, None, (BLOCKER_ACCESS_STATE_INVALID,)
        return True, True, state_path.read_text(encoding="utf-8"), ()
    except (OSError, UnicodeError):
        return True, False, None, (BLOCKER_ACCESS_STATE_UNAVAILABLE,)


def _parse_pairs(text: str) -> tuple[dict[str, str], tuple[str, ...]]:
    values: dict[str, str] = {}
    errors: list[str] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not separator or not key or not value or key in values:
            errors.append(f"line_{line_number}_invalid")
            continue
        values[key] = value
    return values, tuple(errors)


def _positive_int(value: str | None) -> int | None:
    if value is None or not value.isdigit():
        return None
    parsed = int(value)
    return parsed if parsed >= 0 else None


def _digest(value: str | None) -> str | None:
    return value if value is not None and DIGEST_PATTERN.fullmatch(value) else None


def read_access_governance_state(
    environ: Mapping[str, str] | None = None,
) -> AccessGovernanceEvidence:
    """Read the out-of-git state without making network or provider calls."""

    available, readable, text, read_errors = _read_state(access_governance_state_file_path(environ))
    if text is None:
        return AccessGovernanceEvidence(
            state_available=available,
            state_readable=readable,
            file_errors=read_errors,
        )

    values, parse_errors = _parse_pairs(text)
    errors = list(read_errors) + list(parse_errors)
    if values.get("access_governance_state_version") != ACCESS_GOVERNANCE_STATE_VERSION:
        errors.append(BLOCKER_ACCESS_STATE_INVALID)
    if set(values) - _REQUIRED_FIELDS:
        errors.append(BLOCKER_ACCESS_STATE_INVALID)
    if _REQUIRED_FIELDS - set(values):
        errors.append(BLOCKER_ACCESS_STATE_INVALID)

    # The access state is intentionally a small metadata record. Generic
    # analytics field rules treat timestamp values such as epoch seconds as
    # identifier-like numbers, so only credential/content detectors apply here.
    metadata_findings = find_security_credential_fields(values)
    if metadata_findings:
        errors.append(BLOCKER_ACCESS_STATE_INVALID)

    reviewed_at = _positive_int(values.get("reviewed_at"))
    expires_at = _positive_int(values.get("expires_at"))
    accepted = _positive_int(values.get("accepted_operator_count"))
    mfa = _positive_int(values.get("mfa_operator_count"))
    repository_digest = _digest(values.get("repository_digest"))
    config_digest = _digest(values.get("config_digest"))
    installed_digest = _digest(values.get("installed_guard_digest"))
    if None in (
        reviewed_at,
        expires_at,
        accepted,
        mfa,
        repository_digest,
        config_digest,
        installed_digest,
    ):
        errors.append(BLOCKER_ACCESS_STATE_INVALID)
    if reviewed_at is not None and expires_at is not None and expires_at <= reviewed_at:
        errors.append(BLOCKER_ACCESS_STATE_INVALID)
    for field in _REVIEW_FIELDS:
        if values.get(field) != REQUIRED_REVIEW_STATE:
            errors.append(BLOCKER_ACCESS_STATE_INVALID)

    return AccessGovernanceEvidence(
        state_available=available,
        state_readable=readable,
        state_valid=not errors,
        reviewed_at=reviewed_at,
        expires_at=expires_at,
        accepted_operator_count=accepted,
        mfa_operator_count=mfa,
        repository_digest=repository_digest,
        config_digest=config_digest,
        installed_guard_digest=installed_digest,
        revocation_review=values.get("revocation_review"),
        credential_rotation_review=values.get("credential_rotation_review"),
        audit_review=values.get("audit_review"),
        file_errors=tuple(dict.fromkeys(errors)),
    )


def access_governance_blockers(
    evidence: AccessGovernanceEvidence,
    *,
    environ: Mapping[str, str] | None = None,
    now: int | None = None,
) -> tuple[str, ...]:
    """Return fail-closed blocker codes for a live access-governance claim."""

    if not evidence.state_available or not evidence.state_readable:
        return (BLOCKER_ACCESS_STATE_UNAVAILABLE,)
    blockers: list[str] = list(evidence.file_errors)
    if not evidence.state_valid:
        blockers.append(BLOCKER_ACCESS_STATE_INVALID)
    current = int(__import__("time").time()) if now is None else now
    if evidence.expires_at is None or evidence.expires_at <= current:
        blockers.append(BLOCKER_ACCESS_STATE_STALE)
    if evidence.reviewed_at is None or evidence.reviewed_at > current:
        blockers.append(BLOCKER_ACCESS_STATE_INVALID)
    if evidence.accepted_operator_count is None or evidence.accepted_operator_count < MINIMUM_ACCEPTED_OPERATORS:
        blockers.append(BLOCKER_ACCEPTED_OPERATORS_BELOW_MINIMUM)
    if evidence.mfa_operator_count is None or evidence.mfa_operator_count < MINIMUM_MFA_OPERATORS:
        blockers.append(BLOCKER_MFA_OPERATORS_BELOW_MINIMUM)
    if (
        evidence.accepted_operator_count is not None
        and evidence.mfa_operator_count is not None
        and evidence.mfa_operator_count < evidence.accepted_operator_count
    ):
        blockers.append(BLOCKER_MFA_OPERATORS_BELOW_MINIMUM)
    digests = (
        evidence.repository_digest,
        evidence.config_digest,
        evidence.installed_guard_digest,
    )
    if any(digest is None for digest in digests) or len(set(digests)) != 1:
        blockers.append(BLOCKER_DIGEST_MISMATCH)
    environment = os.environ if environ is None else environ
    expected_digest = environment.get("GRAF_PRODUCT_ANALYTICS_ACCESS_GOVERNANCE_EXPECTED_DIGEST")
    if expected_digest is not None and (
        _digest(expected_digest) is None or any(digest != expected_digest for digest in digests)
    ):
        blockers.append(BLOCKER_DIGEST_MISMATCH)
    if evidence.revocation_review != REQUIRED_REVIEW_STATE:
        blockers.append(BLOCKER_REVOCATION_REVIEW_MISSING)
    if evidence.credential_rotation_review != REQUIRED_REVIEW_STATE:
        blockers.append(BLOCKER_ROTATION_REVIEW_MISSING)
    if evidence.audit_review != REQUIRED_REVIEW_STATE:
        blockers.append(BLOCKER_AUDIT_REVIEW_MISSING)
    return tuple(dict.fromkeys(blockers))


__all__ = [
    "ACCESS_GOVERNANCE_STATE_DIR_ENV",
    "ACCESS_GOVERNANCE_STATE_FILE_ENV",
    "AccessGovernanceEvidence",
    "BLOCKER_ACCESS_STATE_INVALID",
    "BLOCKER_ACCESS_STATE_STALE",
    "BLOCKER_ACCESS_STATE_UNAVAILABLE",
    "BLOCKER_ACCEPTED_OPERATORS_BELOW_MINIMUM",
    "BLOCKER_AUDIT_REVIEW_MISSING",
    "BLOCKER_DIGEST_MISMATCH",
    "BLOCKER_MFA_OPERATORS_BELOW_MINIMUM",
    "BLOCKER_REVOCATION_REVIEW_MISSING",
    "BLOCKER_ROTATION_REVIEW_MISSING",
    "access_governance_blockers",
    "access_governance_state_file_path",
    "read_access_governance_state",
]
