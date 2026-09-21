"""Metadata-only operator receipts for the paid-traffic analytics surface.

The repository never contains provider identifiers, credentials, personal names or
provider payloads.  Operators can record only the bounded shape below outside
Git; this validator is used when the checked-in runtime status is read so a
future status cannot claim an applied operation without its receipt.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

OPERATOR_EVIDENCE_SCHEMA = "graf.analytics.operator-evidence.v1"
OPERATOR_RECEIPT_SCHEMA = "graf.analytics.operator-receipt.v1"

EVIDENCE_KINDS = ("dashboard", "rollback", "alert")
EVIDENCE_STATUSES = (
    "applied",
    "partially_applied",
    "ready_not_executed",
    "metadata_only_not_executed",
)
RECEIPT_STATUSES = ("applied", "partially_applied")
RUNTIME_STATUSES = (
    "applied",
    "partially_applied",
    "ready_not_executed",
    "metadata_only_not_executed",
)
OPERATOR_ROLES = (
    "analytics_operator",
    "infra_operator",
    "product_owner",
    "release_owner",
    "qa_reviewer",
    "privacy_reviewer",
    "security_reviewer",
)
RECEIPT_SCOPES = {
    "dashboard": "dashboard_definitions",
    "rollback": "provider_rollback",
    "alert": "alert_rules_and_channel",
}
REQUIRED_CHECKS = {
    "dashboard": ("definitions_applied", "freshness_verified", "empty_state_verified"),
    "rollback": ("switches_verified", "product_workflows_preserved", "measurement_gap_only"),
    "alert": ("rules_have_owner_roles", "channel_probe_verified", "delivery_deadline_verified"),
}
CHECK_NAMES = frozenset(
    name for names in REQUIRED_CHECKS.values() for name in names
)
UTC_TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")


class OperatorEvidenceValidationError(ValueError):
    """Raised when metadata-only operator evidence cannot be trusted."""


def _fail(path: str, reason: str) -> None:
    raise OperatorEvidenceValidationError(f"{path}: {reason}")


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], path: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if extra:
            details.append("extra=" + ",".join(extra))
        _fail(path, "keys are not bounded (" + "; ".join(details) + ")")


def _string(value: Any, path: str, allowed: tuple[str, ...] | None = None) -> str:
    if not isinstance(value, str) or not value:
        _fail(path, "must be a non-empty string")
    if allowed is not None and value not in allowed:
        _fail(path, "has an unsupported value")
    return value


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        _fail(path, "must be a boolean")
    return value


def _validate_receipt(receipt_value: Any, *, kind: str, path: str) -> None:
    receipt = _mapping(receipt_value, path)
    _exact_keys(
        receipt,
        {"schema", "kind", "status", "recorded_at", "operator_role", "scope", "result", "checks"},
        path,
    )
    if receipt.get("schema") != OPERATOR_RECEIPT_SCHEMA:
        _fail(f"{path}.schema", "unsupported receipt schema")
    if receipt.get("kind") != kind:
        _fail(f"{path}.kind", "must match the evidence kind")
    receipt_status = _string(receipt.get("status"), f"{path}.status", RECEIPT_STATUSES)
    recorded_at = _string(receipt.get("recorded_at"), f"{path}.recorded_at")
    if UTC_TIMESTAMP_RE.fullmatch(recorded_at) is None:
        _fail(f"{path}.recorded_at", "must be a UTC timestamp without a live identifier")
    _string(receipt.get("operator_role"), f"{path}.operator_role", OPERATOR_ROLES)
    if receipt.get("scope") != RECEIPT_SCOPES[kind]:
        _fail(f"{path}.scope", "does not match the evidence kind")
    result = _string(receipt.get("result"), f"{path}.result", ("pass", "partial"))
    checks = _mapping(receipt.get("checks"), f"{path}.checks")
    if not checks:
        _fail(f"{path}.checks", "must contain at least one bounded check")
    unknown_checks = set(checks) - CHECK_NAMES
    if unknown_checks:
        _fail(f"{path}.checks", "contains unsupported check names")
    for check_name, check_value in checks.items():
        _boolean(check_value, f"{path}.checks.{check_name}")

    required_checks = REQUIRED_CHECKS[kind]
    if receipt_status == "applied":
        if result != "pass":
            _fail(f"{path}.result", "an applied receipt must have result=pass")
        missing = [name for name in required_checks if checks.get(name) is not True]
        if missing:
            _fail(f"{path}.checks", "an applied receipt must pass: " + ",".join(missing))
    elif result != "partial":
        _fail(f"{path}.result", "a partially applied receipt must have result=partial")


def validate_operator_evidence(payload: Mapping[str, Any]) -> None:
    """Validate the bounded dashboard/rollback/alert evidence document.

    This intentionally does not accept a free-form reference, provider ID,
    secret, URL or person name.  A missing receipt is valid only for a status
    that truthfully says the operation is partial or not executed.
    """

    evidence = _mapping(payload, "operator_evidence")
    _exact_keys(evidence, {"schema", "mode", "receipts"}, "operator_evidence")
    if evidence.get("schema") != OPERATOR_EVIDENCE_SCHEMA:
        _fail("operator_evidence.schema", "unsupported evidence schema")
    if evidence.get("mode") != "metadata_only":
        _fail("operator_evidence.mode", "must be metadata_only")
    receipts = evidence.get("receipts")
    if not isinstance(receipts, list) or len(receipts) != len(EVIDENCE_KINDS):
        _fail("operator_evidence.receipts", "must contain exactly one entry per evidence kind")

    seen: set[str] = set()
    for index, entry_value in enumerate(receipts):
        path = f"operator_evidence.receipts[{index}]"
        entry = _mapping(entry_value, path)
        _exact_keys(entry, {"kind", "status", "receipt"}, path)
        kind = _string(entry.get("kind"), f"{path}.kind", EVIDENCE_KINDS)
        if kind in seen:
            _fail(f"{path}.kind", "duplicate evidence kind")
        seen.add(kind)
        status = _string(entry.get("status"), f"{path}.status", EVIDENCE_STATUSES)
        receipt = entry.get("receipt")
        if status in {"ready_not_executed", "metadata_only_not_executed"}:
            if receipt is not None:
                _fail(f"{path}.receipt", "must be null when the operation was not executed")
            continue
        if status == "applied" and receipt is None:
            _fail(f"{path}.receipt", "is required when status=applied")
        if receipt is not None:
            _validate_receipt(receipt, kind=kind, path=f"{path}.receipt")
            if receipt["status"] != status:
                _fail(f"{path}.receipt.status", "must match the evidence status")
        elif status == "partially_applied":
            # A partial state is the honest repository fallback while an operator
            # receipt is absent; it must never be treated as applied by the
            # runtime-status consistency check.
            continue
    if seen != set(EVIDENCE_KINDS):
        _fail("operator_evidence.receipts", "dashboard, rollback and alert entries are required")


def validate_runtime_status(payload: Mapping[str, Any]) -> None:
    """Validate runtime-status consistency, including applied receipt proof."""

    status = _mapping(payload, "runtime_status")
    runtime_status = _string(status.get("status"), "runtime_status.status", RUNTIME_STATUSES)
    if "operator_evidence" not in status:
        _fail("runtime_status.operator_evidence", "is required")
    validate_operator_evidence(status["operator_evidence"])

    evidence_entries = status["operator_evidence"]["receipts"]
    entry_statuses = {entry["kind"]: entry["status"] for entry in evidence_entries}
    if runtime_status == "applied":
        missing_receipts = [
            kind
            for kind, entry in ((item["kind"], item) for item in evidence_entries)
            if entry["status"] != "applied" or entry["receipt"] is None
        ]
        if missing_receipts:
            _fail(
                "runtime_status.status",
                "status=applied requires applied receipts for: " + ",".join(sorted(missing_receipts)),
            )
    elif all(value == "applied" for value in entry_statuses.values()):
        _fail("runtime_status.status", "all operator evidence is applied; status must be applied")
