#!/usr/bin/env python3
"""Set the exact source SHA evidence in a pull request body to one given SHA.

``pr-metadata`` requires the PR body to carry exactly one line of the form
``- Exact source SHA: `<40 hex>``` whose value equals the current head commit.
Every new commit therefore invalidates that line, and the failure looks like a
metadata problem even though the change itself is fine. This helper rewrites
just that one line so the value always matches the commit being published.

Only the dedicated evidence line is touched: an unrelated 40-character hex
string elsewhere in the body is never modified, and a body without the line is
reported instead of being rewritten silently.

Usage:
    python3 scripts/sync-pr-source-sha.py --body-file body.md --sha <40 hex>
    python3 scripts/sync-pr-source-sha.py --check --body-file body.md --sha <40 hex>
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

SHA_LINE_RE = re.compile(
    r"(^[ \t]*(?:[-*][ \t]*)?Exact source SHA\b[^\n:]*:[ \t]*`?)([0-9a-fA-F]{40})(`?[ \t]*$)",
    re.IGNORECASE | re.MULTILINE,
)
FULL_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def current_head_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def render(body: str, sha: str) -> str:
    """Return ``body`` with the exact source SHA evidence set to ``sha``.

    Raises ValueError when the body has no such line or more than one, because
    both cases need a human decision rather than a silent rewrite.
    """
    matches = list(SHA_LINE_RE.finditer(body))
    if not matches:
        raise ValueError(
            "PR body has no 'Exact source SHA' line; add it instead of guessing a location"
        )
    if len(matches) > 1:
        raise ValueError(
            f"PR body has {len(matches)} 'Exact source SHA' lines; exactly one is allowed"
        )
    match = matches[0]
    return body[: match.start()] + match.group(1) + sha + match.group(3) + body[match.end() :]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--body-file", type=Path, required=True)
    parser.add_argument("--sha", default=None, help="defaults to the current HEAD commit")
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    arguments = parser.parse_args()

    sha = arguments.sha or current_head_sha()
    if not FULL_SHA_RE.fullmatch(sha):
        print(f"source-sha: ERROR: '{sha}' is not a full 40-character git SHA", file=sys.stderr)
        return 2

    body = arguments.body_file.read_text(encoding="utf-8")
    try:
        updated = render(body, sha)
    except ValueError as error:
        print(f"source-sha: ERROR: {error}", file=sys.stderr)
        return 1

    if updated == body:
        print(f"source-sha: OK: body already carries {sha}")
        return 0
    if arguments.check:
        print("source-sha: ERROR: body carries a different exact source SHA", file=sys.stderr)
        return 1
    arguments.body_file.write_text(updated, encoding="utf-8")
    print(f"source-sha: updated to {sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
