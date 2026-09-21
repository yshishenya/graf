#!/usr/bin/env python3
"""Collect the merged release train without serial GitHub round trips.

The release gate remains unchanged: every merged PR between the published base
and the exact source must have a successful governance-fast proof on its exact
head SHA.  Only the lookups are parallelized so a slow GitHub response for one
PR no longer holds the whole train behind it.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import sys
import time
from typing import Any, Callable


Command = Callable[[list[str]], tuple[int, str, str]]


def run_command(argv: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout, result.stderr


def retry_command(
    argv: list[str],
    *,
    command: Command = run_command,
    attempts: int = 5,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[str | None, str]:
    last_error = "command failed"
    for attempt in range(1, attempts + 1):
        code, stdout, stderr = command(argv)
        if code == 0:
            return stdout.strip(), ""
        last_error = (stderr or stdout or f"exit {code}").strip()
        if attempt < attempts:
            sleep(attempt * 3)
    return None, last_error


def json_command(
    argv: list[str],
    *,
    command: Command,
) -> tuple[Any | None, str]:
    output, error = retry_command(argv, command=command)
    if output is None:
        return None, error
    try:
        return json.loads(output), ""
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc}"


def is_ancestor(
    ancestor: str,
    descendant: str,
    *,
    command: Command,
) -> bool:
    code, _stdout, _stderr = command(["git", "merge-base", "--is-ancestor", ancestor, descendant])
    return code == 0


def candidate_rows(
    rows: list[dict[str, Any]],
    *,
    base_sha: str,
    source_sha: str,
    command: Command,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    candidates: list[dict[str, Any]] = []
    skips: list[dict[str, str]] = []
    for row in rows:
        number = str(row.get("number", ""))
        merge = row.get("mergeCommit") or {}
        merge_sha = merge.get("oid") if isinstance(merge, dict) else None
        if not merge_sha:
            skips.append({"number": number, "reason": "нет merge commit"})
            continue
        if not is_ancestor(merge_sha, source_sha, command=command):
            continue
        if is_ancestor(merge_sha, base_sha, command=command):
            continue
        head_sha = row.get("headRefOid")
        if not isinstance(head_sha, str) or not head_sha:
            skips.append({"number": number, "reason": "нет head SHA"})
            continue
        candidates.append({"number": number, "head_sha": head_sha})
    return candidates, skips


def check_candidate(
    candidate: dict[str, str],
    *,
    repository: str,
    command: Command,
) -> tuple[dict[str, str], dict[str, str] | None]:
    number = candidate["number"]
    head_sha = candidate["head_sha"]
    run_id, error = retry_command(
        [
            "gh",
            "api",
            f"repos/{repository}/commits/{head_sha}/check-runs?per_page=100",
            "--jq",
            '[.check_runs[]|select(.name=="governance-fast" and .conclusion=="success")]|sort_by(.id)|last|.id',
        ],
        command=command,
    )
    if not run_id or run_id == "null":
        return candidate, {
            "number": number,
            "reason": f"нет успешной проверки governance-fast на {head_sha[:12]} ({error or 'не найдена'})",
        }
    return {"number": number, "head_sha": head_sha, "run_id": run_id}, None


def collect(
    *,
    base_sha: str,
    source_sha: str,
    command: Command = run_command,
    workers: int = 8,
) -> dict[str, Any]:
    repository, error = retry_command(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        command=command,
    )
    if not repository:
        raise RuntimeError(f"не удалось определить репозиторий: {error}")
    rows, error = json_command(
        [
            "gh",
            "pr",
            "list",
            "--state",
            "merged",
            "--base",
            "master",
            "--limit",
            "50",
            "--json",
            "number,mergeCommit,headRefOid",
        ],
        command=command,
    )
    if not isinstance(rows, list):
        raise RuntimeError(f"не удалось получить список merged PR: {error}")
    candidates, skips = candidate_rows(rows, base_sha=base_sha, source_sha=source_sha, command=command)
    results: list[tuple[dict[str, str], dict[str, str] | None]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(workers, len(candidates) or 1))) as pool:
        futures = [
            pool.submit(check_candidate, candidate, repository=repository, command=command)
            for candidate in candidates
        ]
        for future in futures:
            results.append(future.result())
    selected: list[dict[str, str]] = []
    for result, skipped in results:
        if skipped:
            skips.append(skipped)
        elif "run_id" in result:
            selected.append(result)
    for skipped in skips:
        print(f"release: пул-реквест {skipped['number']} {skipped['reason']}; пропущен", file=sys.stderr)
    return {
        "repository": repository,
        "prs": [row["number"] for row in selected],
        "receipts": [f"pr-{row['number']}-governance-{row['run_id']}" for row in selected],
        "skips": skips,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    try:
        result = collect(base_sha=args.base_sha, source_sha=args.source_sha, workers=args.workers)
    except RuntimeError as exc:
        print(f"release: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
