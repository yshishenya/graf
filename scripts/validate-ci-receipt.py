#!/usr/bin/env python3
"""Validate the metadata-only CI receipt contract used by Feature 227."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
SAFE_RE = re.compile(r"^[A-Za-z0-9._:/-]+$")
STATUSES = {"passed", "failed", "cancelled", "superseded", "stale", "ambiguous"}
EVENTS = {"pull_request", "merge_group", "workflow_dispatch"}
ALLOWED = {
    "schema_version", "status", "event_name", "workflow", "run_id", "run_attempt",
    "workflow_url", "target_sha", "base_sha", "pull_request_numbers", "merge_group_id",
    "requested_sha", "observed_sha_start", "observed_sha_end", "final_cleanliness",
    "final_cleanliness_reason", "local_evidence_digest", "started_at", "finished_at",
    "reason", "conclusion", "concurrency_key", "cancellation_state", "supersession_state",
}


def _string(data: dict[str, Any], key: str, errors: list[str], *, url: bool = False) -> str | None:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or (url and not value.startswith("https://")):
        errors.append(f"missing or invalid {key}")
        return None
    if not url and not SAFE_RE.fullmatch(value):
        errors.append(f"invalid {key}")
    return value


def _sha(data: dict[str, Any], key: str, errors: list[str], *, nullable: bool = False) -> str | None:
    value = data.get(key)
    if nullable and value is None:
        return None
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        errors.append(f"{key} must be a full 40-character SHA")
        return None
    return value.lower()


def _timestamp(data: dict[str, Any], key: str, errors: list[str]) -> dt.datetime | None:
    value = _string(data, key, errors)
    if value is None:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{key} must be an RFC3339 timestamp")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
        errors.append(f"{key} must be UTC")
        return None
    return parsed


def validate(data: dict[str, Any]) -> list[str]:
    if not isinstance(data, dict):
        return ["receipt must be a JSON object"]
    required = (
        "schema_version", "status", "event_name", "workflow", "run_id", "run_attempt",
        "workflow_url", "target_sha", "base_sha", "pull_request_numbers", "merge_group_id",
        "requested_sha", "observed_sha_start", "observed_sha_end", "final_cleanliness",
        "local_evidence_digest", "started_at", "finished_at",
    )
    errors: list[str] = [f"missing {key}" for key in required if key not in data]
    errors.extend(f"unsupported receipt field: {key}" for key in sorted(set(data) - ALLOWED))
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    status = data.get("status")
    if status not in STATUSES:
        errors.append("invalid status")
    event = data.get("event_name")
    if event not in EVENTS:
        errors.append("invalid event_name")
    for key in ("workflow", "run_id"):
        _string(data, key, errors)
    if "concurrency_key" in data:
        _string(data, "concurrency_key", errors)
    _string(data, "workflow_url", errors, url=True)
    target = _sha(data, "target_sha", errors)
    requested = _sha(data, "requested_sha", errors)
    observed_start = _sha(data, "observed_sha_start", errors)
    observed_end = _sha(data, "observed_sha_end", errors)
    base = _sha(data, "base_sha", errors, nullable=True)
    if event in {"pull_request", "merge_group"} and base is None:
        errors.append("base_sha is required for PR and merge_group events")
    if status == "passed" and target and requested and target != requested:
        errors.append("target_sha and requested_sha mismatch")
    if status == "passed" and requested and observed_start and requested != observed_start:
        errors.append("requested_sha and observed_sha_start mismatch")
    if status == "passed" and requested and observed_end and requested != observed_end:
        errors.append("requested_sha and observed_sha_end mismatch")
    prs = data.get("pull_request_numbers")
    if not isinstance(prs, list) or any(isinstance(x, bool) or not isinstance(x, int) or x < 1 for x in prs) or len(set(prs)) != len(prs):
        errors.append("pull_request_numbers must contain unique positive integers")
    elif event == "pull_request" and len(prs) != 1:
        errors.append("pull_request events require exactly one pull request number")
    elif event == "merge_group" and not prs:
        errors.append("merge_group events require a complete PR mapping")
    elif event == "workflow_dispatch" and prs:
        errors.append("workflow_dispatch receipts cannot contain pull request numbers")
    group_id = data.get("merge_group_id")
    if event == "merge_group" and (not isinstance(group_id, str) or not group_id.strip()):
        errors.append("merge_group_id is required for merge_group events")
    elif isinstance(group_id, str) and not SAFE_RE.fullmatch(group_id):
        errors.append("merge_group_id is invalid")
    if event != "merge_group" and group_id is not None:
        errors.append("merge_group_id is only valid for merge_group events")
    attempt = data.get("run_attempt")
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
        errors.append("run_attempt must be a positive integer")
    cleanliness = data.get("final_cleanliness")
    if cleanliness not in {"pass", "fail", "stale", "ambiguous"}:
        errors.append("invalid final_cleanliness")
    digest = data.get("local_evidence_digest")
    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
        errors.append("local_evidence_digest must be sha256:<64 hex>")
    started = _timestamp(data, "started_at", errors)
    finished = _timestamp(data, "finished_at", errors)
    if started and finished and finished <= started:
        errors.append("finished_at must be after started_at")
    if status == "passed" and cleanliness != "pass":
        errors.append("passed receipt requires final_cleanliness=pass")
    if status == "passed" and target and observed_start and observed_end and not (target == observed_start == observed_end):
        errors.append("passed receipt requires matching target and observed SHAs")
    if status != "passed" and (not isinstance(data.get("reason"), str) or not data["reason"].strip()):
        errors.append("non-passed receipt requires reason")
    if data.get("conclusion") is not None and data.get("conclusion") != status:
        errors.append("conclusion must match status")
    if data.get("cancellation_state") not in {None, "none", "cancelled"}:
        errors.append("invalid cancellation_state")
    if data.get("supersession_state") not in {None, "none", "superseded"}:
        errors.append("invalid supersession_state")
    if status == "cancelled" and data.get("cancellation_state") != "cancelled":
        errors.append("cancelled receipt requires cancellation_state=cancelled")
    if status == "superseded" and data.get("supersession_state") != "superseded":
        errors.append("superseded receipt requires supersession_state=superseded")
    if status == "passed" and data.get("cancellation_state") == "cancelled":
        errors.append("passed receipt cannot have cancellation_state=cancelled")
    if status == "passed" and data.get("supersession_state") == "superseded":
        errors.append("passed receipt cannot have supersession_state=superseded")
    def scan(value: Any, path: str = "receipt") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if re.search(r"(?:raw[_ -]?audio|raw[_ -]?transcript|transcript[_ -]?text|private[_ -]?meeting)", str(key), re.IGNORECASE):
                    errors.append(f"receipt contains forbidden sensitive field: {path}.{key}")
                scan(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                scan(child, f"{path}[{index}]")
        elif isinstance(value, str) and ("/Users/" in value or "/home/" in value or "/private/var/" in value or "BEGIN PRIVATE KEY" in value or "signed-url" in value.lower()):
            errors.append(f"receipt contains private content in {path}")
    scan(data)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", type=Path, nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        sha = "a" * 40
        good = {"schema_version": 1, "status": "passed", "event_name": "pull_request", "workflow": "governance", "run_id": "run-1", "run_attempt": 1, "workflow_url": "https://github.com/o/r/actions/runs/1", "target_sha": sha, "base_sha": "b" * 40, "pull_request_numbers": [1], "merge_group_id": None, "requested_sha": sha, "observed_sha_start": sha, "observed_sha_end": sha, "final_cleanliness": "pass", "local_evidence_digest": "sha256:" + "c" * 64, "started_at": "2026-08-31T00:00:00Z", "finished_at": "2026-08-31T00:01:00Z", "conclusion": "passed", "cancellation_state": "none", "supersession_state": "none"}
        assert validate(good) == []
        assert validate(dict(good, observed_sha_end="d" * 40))
        assert validate(dict(good, status="cancelled", conclusion="cancelled", final_cleanliness="ambiguous", reason="cancelled", cancellation_state="cancelled")) == []
        print("ci-receipt self-test: OK")
        return 0
    if args.receipt is None:
        parser.error("receipt is required unless --self-test is used")
    try:
        data = json.loads(args.receipt.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ci-receipt: ERROR: {exc}", file=sys.stderr)
        return 1
    errors = validate(data)
    for error in errors:
        print(f"ci-receipt: ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print("ci-receipt: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
