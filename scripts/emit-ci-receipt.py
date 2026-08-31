#!/usr/bin/env python3
"""Create one metadata-only CI receipt from resolved identity and local evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return value


def _write_once(value: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, output)
    except FileExistsError as exc:
        raise SystemExit(f"refusing to overwrite existing receipt {output}") from exc
    finally:
        try:
            os.unlink(temporary)
        except OSError:
            pass


def build(identity: dict[str, Any], evidence: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    status = evidence.get("status")
    if status not in {"passed", "failed", "stale", "cancelled", "ambiguous"}:
        raise SystemExit("evidence status is invalid")
    final_cleanliness = {
        "passed": "pass",
        "failed": "fail",
        "stale": "stale",
        "cancelled": "ambiguous",
        "ambiguous": "ambiguous",
    }[status]
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "status": status,
        "event_name": identity.get("event_name"),
        "workflow": args.workflow,
        "run_id": args.run_id,
        "run_attempt": args.run_attempt,
        "workflow_url": args.workflow_url,
        "target_sha": identity.get("target_sha"),
        "base_sha": identity.get("base_sha"),
        "pull_request_numbers": identity.get("pull_request_numbers", []),
        "merge_group_id": identity.get("merge_group_id"),
        "requested_sha": evidence.get("requested_sha"),
        "observed_sha_start": evidence.get("observed_sha_start"),
        "observed_sha_end": evidence.get("observed_sha_end"),
        "final_cleanliness": final_cleanliness,
        "local_evidence_digest": "sha256:" + hashlib.sha256(args.evidence.read_bytes()).hexdigest(),
        "started_at": evidence.get("started_at"),
        "finished_at": evidence.get("finished_at"),
        "conclusion": status,
        "concurrency_key": identity.get("concurrency_key"),
        "cancellation_state": "cancelled" if status == "cancelled" else "none",
        "supersession_state": "superseded" if status == "superseded" else "none",
    }
    if evidence.get("reason"):
        receipt["reason"] = evidence["reason"]
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    parser.add_argument("--workflow-url", required=True)
    args = parser.parse_args()
    receipt = build(_load(args.identity), _load(args.evidence), args)
    _write_once(receipt, args.output)
    print(json.dumps({"receipt_path": str(args.output), "status": receipt["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
