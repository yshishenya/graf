#!/usr/bin/env python3
"""Publish the exact PR source SHA into the pull-request body in the only safe order.

GitHub re-runs the required checks whenever a pull-request body changes.  That
run does not execute the code lane again: it only reuses the proof produced by
the run for the same head SHA.  Editing the body *before* that proof finishes
leaves the pull request in a state the check can never accept, because no code
run is scheduled for it any more, and the only way out is another commit.

This helper enforces the safe order:

1. resolve the current head SHA of the pull request;
2. wait until the code proof for that exact SHA has completed;
3. only then write the exact SHA into the body.

It talks to the REST API directly because ``gh pr edit`` fails on this
repository with the retired Projects (classic) GraphQL field.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SHA_LINE = re.compile(r"(?m)^- Exact source SHA: `[0-9a-f]{40}`$")
PLACEHOLDER_SHA_LINE = re.compile(r"(?m)^- Exact source SHA:.*$")
CODE_PROOF_CHECK = "governance-fast"


def gh(arguments: list[str]) -> str:
    result = subprocess.run(
        ["gh", *arguments], text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip() or "gh failed"
        raise SystemExit(f"error: {message}")
    return result.stdout


def api(path: str) -> object:
    return json.loads(gh(["api", path]))


def pull_request(repository: str, number: str) -> dict:
    return api(f"repos/{repository}/pulls/{number}")


def check_runs(repository: str, sha: str, name: str) -> list[dict]:
    payload = api(f"repos/{repository}/commits/{sha}/check-runs?per_page=100")
    return [run for run in payload.get("check_runs", []) if run.get("name") == name]


def wait_for_code_proof(
    repository: str, sha: str, wait_seconds: int, poll_seconds: int = 20
) -> str:
    """Return the conclusion once the code proof for this SHA has completed.

    A proof that has not been requested yet is not a proof: the body must not
    change until the run exists and has finished, otherwise the body-change run
    has nothing to reuse.
    """
    deadline = time.monotonic() + wait_seconds
    while True:
        runs = check_runs(repository, sha, CODE_PROOF_CHECK)
        completed = [run for run in runs if run.get("status") == "completed"]
        if completed:
            return str(completed[-1].get("conclusion"))
        if time.monotonic() >= deadline:
            return "missing"
        time.sleep(poll_seconds)


def render(body: str, sha: str) -> str:
    if SHA_LINE.search(body):
        return SHA_LINE.sub(f"- Exact source SHA: `{sha}`", body)
    if PLACEHOLDER_SHA_LINE.search(body):
        return PLACEHOLDER_SHA_LINE.sub(f"- Exact source SHA: `{sha}`", body)
    raise SystemExit("error: pull-request body has no '- Exact source SHA:' line")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("number", help="pull-request number")
    parser.add_argument("--repository", default="yshishenya/graf")
    parser.add_argument("--wait-seconds", type=int, default=2400)
    parser.add_argument("--poll-seconds", type=int, default=20)
    parser.add_argument(
        "--body-file",
        help="read the replacement body from this file instead of the current body",
    )
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()

    request = pull_request(arguments.repository, arguments.number)
    sha = str(request["head"]["sha"])
    body = (
        Path(arguments.body_file).read_text(encoding="utf-8")
        if arguments.body_file
        else str(request.get("body") or "")
    )
    print(f"pr_metadata=resolved pr={arguments.number} head_sha={sha}")

    conclusion = wait_for_code_proof(
        arguments.repository, sha, arguments.wait_seconds, arguments.poll_seconds
    )
    print(f"pr_metadata=code_proof sha={sha} conclusion={conclusion}")
    if conclusion != "success":
        print(
            "error: the code proof for this exact SHA is not successful yet; "
            "updating the body now would leave the pull request unable to pass. "
            "Fix the failing check first.",
            file=sys.stderr,
        )
        return 1

    updated = render(body, sha)
    if updated == body:
        print(f"pr_metadata=unchanged sha={sha}")
        return 0
    if arguments.dry_run:
        print(f"pr_metadata=dry_run would set sha={sha}")
        return 0

    with tempfile.NamedTemporaryFile(
        "w", suffix=".md", encoding="utf-8", delete=False
    ) as handle:
        handle.write(updated)
        body_path = handle.name
    try:
        gh(
            [
                "api",
                "-X",
                "PATCH",
                f"repos/{arguments.repository}/pulls/{arguments.number}",
                "-F",
                f"body=@{body_path}",
                "--jq",
                ".number",
            ]
        )
    finally:
        Path(body_path).unlink(missing_ok=True)
    print(f"pr_metadata=updated pr={arguments.number} sha={sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
