#!/usr/bin/env python3
"""Write one metadata-only, SHA-bound CI evidence record atomically."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--lane", choices=("focused", "fast", "full"), required=True)
    parser.add_argument("--requested-sha", required=True)
    parser.add_argument("--observed-sha-start", required=True)
    parser.add_argument("--observed-sha-end", required=True)
    parser.add_argument("--status", choices=("passed", "failed", "stale", "cancelled", "ambiguous"), required=True)
    parser.add_argument("--started-at", required=True)
    parser.add_argument("--finished-at", required=True)
    parser.add_argument("--command", action="append", default=[])
    parser.add_argument("--skipped-gate", action="append", default=[])
    parser.add_argument("--scope", required=True)
    parser.add_argument("--reason")
    parser.add_argument("--candidate-id")
    parser.add_argument("--authoritative-full", action="store_true")
    parser.add_argument("--component-sha", action="append", default=[], metavar="NAME=SHA")
    return parser


def _components(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"invalid --component-sha {value!r}: expected NAME=SHA")
        name, sha = value.split("=", 1)
        if not name or not sha or name in result:
            raise SystemExit(f"invalid --component-sha {value!r}")
        result[name] = sha
    return result


def emit(args: argparse.Namespace) -> dict[str, object]:
    evidence: dict[str, object] = {
        "run_id": args.run_id,
        "lane": args.lane,
        "requested_sha": args.requested_sha,
        "observed_sha_start": args.observed_sha_start,
        "observed_sha_end": args.observed_sha_end,
        "status": args.status,
        "started_at": args.started_at,
        "finished_at": args.finished_at,
        "commands": args.command or [f"infra/scripts/ci-local.sh --{args.lane}"],
        "skipped_gates": args.skipped_gate,
        "scope": args.scope,
        "artifact_digests": {
            "source-revision": "sha256:" + hashlib.sha256(args.observed_sha_end.encode("ascii")).hexdigest()
        },
    }
    components = _components(args.component_sha)
    if components:
        evidence["component_shas"] = components
    if args.candidate_id:
        evidence["candidate_id"] = args.candidate_id
    if args.authoritative_full:
        evidence["authoritative_full"] = True
    if args.reason:
        evidence["reason"] = args.reason
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(evidence, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return evidence


def main() -> int:
    args = _parser().parse_args()
    evidence = emit(args)
    print(json.dumps({"evidence_path": str(args.output), "status": evidence["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
