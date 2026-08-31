#!/usr/bin/env python3
"""Validate an immutable release-train provenance manifest."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
SAFE_RE = re.compile(r"^[A-Za-z0-9._:/-]+$")
REFERENCE_RE = re.compile(r"^[A-Za-z0-9._:-]{1,512}$")
DECISIONS = {"pending", "go", "no-go"}
ALLOWED = {
    "schema_version", "train_id", "created_at", "operator", "source_sha", "base_sha",
    "synthetic_merge_sha", "included_prs", "feature_ids", "merge_group_ids", "pr_receipts",
    "merge_group_receipts", "changelog_digest", "authoritative_full_ci_receipt", "decision",
    "rollback_target",
}


def _sha(value: Any, key: str, errors: list[str], *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        errors.append(f"{key} must be a full 40-character SHA")
        return None
    return value.lower()


def _list(value: Any, key: str, errors: list[str], *, positive: bool = False) -> list[Any] | None:
    if not isinstance(value, list) or not value:
        errors.append(f"{key} must be a non-empty list")
        return None
    if positive and any(isinstance(item, bool) or not isinstance(item, int) or item < 1 for item in value):
        errors.append(f"{key} must contain positive integers")
    if len(set(json.dumps(item, sort_keys=True) for item in value)) != len(value):
        errors.append(f"{key} must not contain duplicates")
    return value


def validate(data: dict[str, Any]) -> list[str]:
    if not isinstance(data, dict):
        return ["train manifest must be a JSON object"]
    required = ("schema_version", "train_id", "source_sha", "base_sha", "synthetic_merge_sha", "included_prs", "feature_ids", "merge_group_ids", "pr_receipts", "merge_group_receipts", "changelog_digest", "authoritative_full_ci_receipt", "decision", "rollback_target")
    errors = [f"missing {key}" for key in required if key not in data]
    errors.extend(f"unsupported manifest field: {key}" for key in sorted(set(data) - ALLOWED))
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if "created_at" in data:
        if not isinstance(data["created_at"], str) or not data["created_at"].strip():
            errors.append("created_at must be a non-empty timestamp")
        else:
            try:
                parsed = dt.datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
                if parsed.tzinfo is None or parsed.utcoffset() is None:
                    errors.append("created_at must include a timezone")
            except ValueError:
                errors.append("created_at must be an RFC3339 timestamp")
    if "operator" in data and (not isinstance(data["operator"], str) or not data["operator"].strip() or len(data["operator"]) > 160):
        errors.append("operator must be a bounded non-empty string")
    train_id = data.get("train_id")
    if not isinstance(train_id, str) or not re.fullmatch(r"train-[A-Za-z0-9._:-]{1,128}", train_id):
        errors.append("train_id is invalid")
    source = _sha(data.get("source_sha"), "source_sha", errors)
    base = _sha(data.get("base_sha"), "base_sha", errors)
    synthetic = _sha(data.get("synthetic_merge_sha"), "synthetic_merge_sha", errors)
    if source and synthetic and source == synthetic:
        errors.append("source_sha must remain distinct from synthetic_merge_sha")
    _list(data.get("included_prs"), "included_prs", errors, positive=True)
    features = _list(data.get("feature_ids"), "feature_ids", errors)
    if features is not None and any(not isinstance(item, str) or not re.fullmatch(r"[0-9]{3,}", item) for item in features):
        errors.append("feature_ids must contain numeric strings")
    for key in ("merge_group_ids", "pr_receipts", "merge_group_receipts"):
        value = data.get(key)
        if not isinstance(value, list):
            errors.append(f"{key} must be a list")
        elif len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            errors.append(f"{key} must not contain duplicates")
        for index, item in enumerate(value or []):
            if isinstance(item, str):
                if not REFERENCE_RE.fullmatch(item):
                    errors.append(f"{key}[{index}] is not a safe metadata reference")
            elif isinstance(item, dict):
                allowed_ref = {"run_id", "receipt_digest", "target_sha", "status", "pull_request_numbers", "merge_group_id"}
                errors.extend(f"{key}[{index}] contains unsupported field: {field}" for field in sorted(set(item) - allowed_ref))
                if not isinstance(item.get("run_id"), str) or not REFERENCE_RE.fullmatch(item["run_id"]):
                    errors.append(f"{key}[{index}].run_id is invalid")
                if not isinstance(item.get("receipt_digest"), str) or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", item["receipt_digest"]):
                    errors.append(f"{key}[{index}].receipt_digest is invalid")
                _sha(item.get("target_sha"), f"{key}[{index}].target_sha", errors)
            else:
                errors.append(f"{key}[{index}] must be a safe reference or object")
    digest = data.get("changelog_digest")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        errors.append("changelog_digest must be sha256:<64 hex>")
    receipt = data.get("authoritative_full_ci_receipt")
    if receipt is not None and not isinstance(receipt, dict):
        errors.append("authoritative_full_ci_receipt must be a structured reference object or null")
    if isinstance(receipt, dict):
        allowed_full = {"run_id", "receipt_digest", "target_sha", "status", "lane"}
        errors.extend(f"authoritative_full_ci_receipt contains unsupported field: {field}" for field in sorted(set(receipt) - allowed_full))
        if not isinstance(receipt.get("run_id"), str) or not REFERENCE_RE.fullmatch(receipt["run_id"]):
            errors.append("authoritative_full_ci_receipt.run_id is invalid")
        if not isinstance(receipt.get("receipt_digest"), str) or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", receipt["receipt_digest"]):
            errors.append("authoritative_full_ci_receipt.receipt_digest is invalid")
        receipt_target = _sha(receipt.get("target_sha"), "authoritative_full_ci_receipt.target_sha", errors)
        if source and receipt_target and source != receipt_target:
            errors.append("authoritative_full_ci_receipt target_sha must match source_sha")
        if receipt.get("status") != "passed":
            errors.append("authoritative_full_ci_receipt.status must be passed")
        if "lane" in receipt and receipt.get("lane") != "full":
            errors.append("authoritative_full_ci_receipt.lane must be full")
    decision = data.get("decision")
    if decision not in DECISIONS:
        errors.append("decision must be pending, go or no-go")
    rollback = data.get("rollback_target")
    if not isinstance(rollback, str) or not rollback.strip() or not re.fullmatch(r"[A-Za-z0-9._:-]{1,200}", rollback):
        errors.append("rollback_target must be a bounded tag, SHA or release identifier")
    if decision == "go" and not isinstance(receipt, dict):
        errors.append("decision=go requires a structured authoritative_full_ci_receipt")
    def scan(value: Any, path: str = "manifest") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                scan(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                scan(child, f"{path}[{index}]")
        elif isinstance(value, str) and ("/Users/" in value or "/home/" in value or "/private/var/" in value or "BEGIN PRIVATE KEY" in value or "signed-url" in value.lower()):
            errors.append(f"manifest contains private content in {path}")
    scan(data)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path, nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        sha = "a" * 40
        good = {"schema_version": 1, "train_id": "train-1", "source_sha": sha, "base_sha": "b" * 40, "synthetic_merge_sha": "c" * 40, "included_prs": [1, 2, 3], "feature_ids": ["216", "227"], "merge_group_ids": ["mg-1"], "pr_receipts": ["pr-1"], "merge_group_receipts": ["mg-1"], "changelog_digest": "sha256:" + "d" * 64, "authoritative_full_ci_receipt": {"run_id": "full-1", "receipt_digest": "sha256:" + "f" * 64, "target_sha": sha, "status": "passed", "lane": "full"}, "decision": "go", "rollback_target": "e" * 40}
        assert validate(good) == []
        assert validate(dict(good, source_sha=good["synthetic_merge_sha"]))
        assert validate(dict(good, decision="go", authoritative_full_ci_receipt=None))
        assert validate(dict(good, authoritative_full_ci_receipt="full-1"))
        print("release-train self-test: OK")
        return 0
    if args.manifest is None:
        parser.error("manifest is required unless --self-test is used")
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"release-train: ERROR: {exc}", file=sys.stderr)
        return 1
    errors = validate(data)
    for error in errors:
        print(f"release-train: ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print("release-train: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
