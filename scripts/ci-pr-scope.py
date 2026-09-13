#!/usr/bin/env python3
"""Select PR work from the exact event, retaining conservative code/native gates."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def text_only(event: dict) -> bool:
    changes = event.get("changes")
    return (
        event.get("action") == "edited"
        and isinstance(changes, dict) and bool(changes)
        and set(changes) <= {"title", "body"}
        and all(isinstance(value, dict) and set(value) == {"from"}
                and (value["from"] is None or isinstance(value["from"], str))
                for value in changes.values())
    )


def native_required(paths: list[str]) -> bool:
    def independent(path: str) -> bool:
        if any(ord(char) < 32 for char in path):
            return False
        if (path in {"README.md", "CONTRIBUTING.md", "AGENTS.md", "CHANGELOG.md"}
                or (path.startswith(("docs/", "specs/")) and path.endswith(".md"))
                or re.fullmatch(r"changes/(?:unreleased|releases/v[^/]+)/F\d+\.yaml", path)):
            return True
        # Explicit independent server modules only; API, cabinet, shared and
        # newly introduced paths continue to exercise the desktop contracts.
        return (path.startswith("apps/server/src/twobrain_rec_server/billing/")
                or bool(re.fullmatch(r"apps/server/tests/(?:unit|integration|contract)/test_billing[^/]*\.py", path)))
    return not paths or not all(independent(path) for path in paths)


def resolve(event: dict, event_name: str) -> dict:
    spec = importlib.util.spec_from_file_location("ci_identity", Path(__file__).with_name("ci-event-identity.py"))
    identity = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(identity)
    result = identity.resolve(event, event_name=event_name)
    head, base = result["target_sha"], result["base_sha"]
    if subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() != head:
        raise ValueError("checkout differs from event head")
    paths = []
    if base is not None:
        paths = subprocess.check_output([
            "git", "diff", "--no-ext-diff", "--no-textconv", "--name-only", "--no-renames", "-z", f"{base}...{head}",
        ], stderr=subprocess.DEVNULL).decode("utf-8", errors="surrogateescape").split("\0")
        paths = [path for path in paths if path]
    result.update(
        text_only=event_name == "pull_request" and text_only(event),
        native_required=native_required(paths),
        paths_digest=hashlib.sha256("\0".join(paths).encode("utf-8", errors="surrogateescape")).hexdigest(),
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("event", type=Path)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    try:
        result = resolve(json.loads(args.event.read_text()), args.event_name)
        if args.result is not None:
            repository = os.environ.get("GITHUB_REPOSITORY", "")
            run_id, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "")
            if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository) or not all(re.fullmatch(r"[1-9]\d*", value) for value in (run_id, attempt)):
                raise ValueError("repository/run identity is required for evidence")
            result.update(repository=repository, run_id=int(run_id), run_attempt=int(attempt))
            with args.result.open("x", encoding="utf-8") as output:
                json.dump(result, output, sort_keys=True)
    except (OSError, ValueError, TypeError, RecursionError, subprocess.CalledProcessError):
        print("ci-pr-scope: cannot resolve exact event and diff", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
