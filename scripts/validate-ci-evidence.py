#!/usr/bin/env python3
"""Validate metadata-only CI evidence against one exact source SHA."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional


SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
DIGEST_RE = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$")
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9._:-]+$")
LANES = {"focused", "fast", "full"}
STATUSES = {"passed", "failed", "stale", "cancelled", "ambiguous"}
STALE_STATUSES = {"failed", "stale", "cancelled", "ambiguous"}
UTC_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]00:00)$"
)
ALLOWED_FIELDS = {
    "run_id", "lane", "requested_sha", "observed_sha_start", "observed_sha_end",
    "status", "started_at", "finished_at", "commands", "skipped_gates", "scope",
    "reason", "candidate_id", "authoritative_full", "authoritative", "component_shas",
    "artifact_digests",
}
PRIVATE_PATH_RE = re.compile(r"(?:/Users/|/home/|/private/var/|file://)", re.IGNORECASE)
CREDENTIAL_RE = re.compile(
    r"(?:api[_-]?key|secret|password|token|bearer|cookie|signed[-_ ]?url)"
    r"\s*[:=]\s*[^\s,;]{8,}|"
    r"(?:authorization\s*:\s*)?bearer\s+[^\s,;]{1,}",
    re.IGNORECASE,
)
SENSITIVE_FIELD_RE = re.compile(
    r"(?:raw[_ -]?transcript|transcript[_ -]?text|raw[_ -]?audio|private[_ -]?meeting)",
    re.IGNORECASE,
)


def _non_empty_string(data: dict[str, Any], key: str, errors: list[str]) -> Optional[str]:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"missing or invalid {key}")
        return None
    return value


def _sha(data: dict[str, Any], key: str, errors: list[str]) -> Optional[str]:
    value = _non_empty_string(data, key, errors)
    if value is not None and not SHA_RE.fullmatch(value):
        errors.append(f"invalid {key}: expected 40 hexadecimal characters")
    return value


def _utc_timestamp(data: dict[str, Any], key: str, errors: list[str]) -> Optional[dt.datetime]:
    value = _non_empty_string(data, key, errors)
    if value is None or not UTC_TIMESTAMP_RE.fullmatch(value):
        if value is not None:
            errors.append(f"{key} must be an RFC3339 UTC timestamp")
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{key} must be an RFC3339 UTC timestamp")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
        errors.append(f"{key} must be an RFC3339 UTC timestamp")
        return None
    return parsed


def _string_list(
    data: dict[str, Any], key: str, errors: list[str], *, non_empty: bool = False
) -> Optional[list[str]]:
    value = data.get(key)
    if not isinstance(value, list) or (non_empty and not value) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        errors.append(f"missing or invalid {key}: expected a list of non-empty strings")
        return None
    return value


def _artifact_digests(data: dict[str, Any], errors: list[str]) -> None:
    value = data.get("artifact_digests")
    if not isinstance(value, dict) or not value:
        errors.append("missing or invalid artifact_digests: expected a non-empty object")
        return
    for name, digest in value.items():
        if not isinstance(name, str) or not name.strip():
            errors.append("artifact_digests contains an invalid artifact name")
        elif not SAFE_ID_RE.fullmatch(name):
            errors.append(f"invalid artifact name for {name!r}")
        elif not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
            errors.append(f"invalid artifact digest for {name!r}")


def _metadata_only(data: dict[str, Any], errors: list[str]) -> None:
    """Reject unknown/private evidence before its digest becomes release proof."""
    unknown = sorted(set(data) - ALLOWED_FIELDS)
    errors.extend(f"unsupported evidence field: {key}" for key in unknown)

    def visit(value: Any, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                if SENSITIVE_FIELD_RE.search(str(child_key)):
                    errors.append(f"evidence contains forbidden sensitive field: {child_key}")
                visit(child_value, str(child_key))
        elif isinstance(value, list):
            for item in value:
                visit(item, key)
        elif isinstance(value, str):
            if PRIVATE_PATH_RE.search(value) or CREDENTIAL_RE.search(value):
                errors.append(f"evidence contains forbidden private or credential content in {key or 'value'}")
            if re.search(r"\b(?:raw audio|raw transcript|transcript text|private meeting content)\b", value, re.IGNORECASE):
                errors.append(f"evidence contains forbidden private content in {key or 'value'}")

    visit(data)


def validate(data: dict[str, Any]) -> list[str]:
    """Return actionable contract violations; an empty list means valid proof."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["evidence must be a JSON object"]
    _metadata_only(data, errors)

    run_id = _non_empty_string(data, "run_id", errors)
    if run_id is not None and not SAFE_ID_RE.fullmatch(run_id):
        errors.append("invalid run_id")
    lane = _non_empty_string(data, "lane", errors)
    if lane is not None and lane not in LANES:
        errors.append(f"invalid lane {lane!r}")

    requested = _sha(data, "requested_sha", errors)
    observed_start = _sha(data, "observed_sha_start", errors)
    observed_end = _sha(data, "observed_sha_end", errors)
    if requested and observed_start and requested.lower() != observed_start.lower():
        errors.append("requested/observed start SHA mismatch: evidence is stale")
    if requested and observed_end and requested.lower() != observed_end.lower():
        errors.append("requested/observed end SHA mismatch: evidence is stale")
    if observed_start and observed_end and observed_start.lower() != observed_end.lower():
        errors.append("observed start/end SHA mismatch: run changed during execution")

    status = _non_empty_string(data, "status", errors)
    if status is not None and status not in STATUSES:
        errors.append(f"invalid status {status!r}")
    if status in STALE_STATUSES:
        errors.append(f"status {status} cannot be release evidence")
    if status != "passed":
        _non_empty_string(data, "reason", errors)

    started_at = _utc_timestamp(data, "started_at", errors)
    finished_at = _utc_timestamp(data, "finished_at", errors)
    if started_at is not None and finished_at is not None and finished_at <= started_at:
        errors.append("finished_at must be after started_at")
    _string_list(data, "commands", errors, non_empty=True)
    skipped_gates = _string_list(data, "skipped_gates", errors)
    _non_empty_string(data, "scope", errors)
    _artifact_digests(data, errors)
    artifact_digests = data.get("artifact_digests")
    if isinstance(artifact_digests, dict) and "source-revision" in artifact_digests and observed_end:
        expected = "sha256:" + hashlib.sha256(observed_end.encode("ascii")).hexdigest()
        if artifact_digests.get("source-revision") != expected:
            errors.append("source-revision artifact digest does not match observed_sha_end")

    component_shas = data.get("component_shas")
    if lane == "full" and (not isinstance(component_shas, dict) or not component_shas):
        errors.append("full evidence requires a non-empty component_shas object")
    if component_shas is not None:
        if not isinstance(component_shas, dict) or not component_shas:
            errors.append("component_shas must be a non-empty object when present")
        elif requested:
            for component, component_sha in component_shas.items():
                if not isinstance(component, str) or not isinstance(component_sha, str):
                    errors.append("component_shas contains an invalid entry")
                elif not SHA_RE.fullmatch(component_sha):
                    errors.append(f"invalid component SHA for {component!r}")
                elif component_sha.lower() != requested.lower():
                    errors.append(f"component SHA mismatch for {component!r}")

    if lane == "full":
        candidate_id = _non_empty_string(data, "candidate_id", errors)
        if candidate_id is not None and not SAFE_ID_RE.fullmatch(candidate_id):
            errors.append("invalid candidate_id")
        if data.get("authoritative_full") is not True:
            errors.append("full evidence requires authoritative_full=true")
        if skipped_gates == []:
            pass
        elif skipped_gates is not None:
            errors.append("authoritative full evidence cannot skip gates")

    if "authoritative_full" in data and not isinstance(data["authoritative_full"], bool):
        errors.append("authoritative_full must be boolean")
    return errors


def self_test() -> int:
    sha = "a" * 40
    digest = "sha256:" + "b" * 64
    good = {
        "run_id": "run-1",
        "lane": "full",
        "requested_sha": sha,
        "observed_sha_start": sha,
        "observed_sha_end": sha,
        "status": "passed",
        "started_at": "2026-08-31T00:00:00Z",
        "finished_at": "2026-08-31T00:01:00Z",
        "commands": ["infra/scripts/ci-local.sh --full"],
        "artifact_digests": {"full-log": digest},
        "skipped_gates": [],
        "scope": "release candidate",
        "candidate_id": "rc-20260831T000000Z-aaaaaaaaaaaa",
        "authoritative_full": True,
        "component_shas": {"server": sha, "macos": sha},
    }
    assert validate(good) == []
    changed = dict(good, observed_sha_end="b" * 40)
    assert any("mismatch" in error for error in validate(changed))
    interrupted = dict(good, status="ambiguous", reason="runner interrupted")
    assert any("cannot be release" in error for error in validate(interrupted))
    component_mismatch = dict(good, component_shas={"server": "c" * 40})
    assert any("component SHA mismatch" in error for error in validate(component_mismatch))
    diagnostic = dict(good, authoritative_full=False)
    assert any("authoritative_full=true" in error for error in validate(diagnostic))
    print("ci-evidence self-test: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path, nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.evidence is None:
        parser.error("evidence path is required unless --self-test is used")
    try:
        loaded = json.loads(args.evidence.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ci-evidence: ERROR: {exc}", file=sys.stderr)
        return 1
    errors = validate(loaded)
    if errors:
        for error in errors:
            print(f"ci-evidence: ERROR: {error}", file=sys.stderr)
        return 1
    print("ci-evidence: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
