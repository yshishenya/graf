#!/usr/bin/env python3
"""Verify merge-group PR membership against GitHub's authoritative PR API."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


class MappingError(ValueError):
    """Raised when the merge-group mapping cannot be proven."""


def _sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise MappingError(f"{field} must be a full 40-character SHA")
    return value.lower()


def _number_rows(rows: Any, field: str) -> list[int]:
    if not isinstance(rows, list) or not rows:
        raise MappingError(f"{field} must be a non-empty list")
    numbers: list[int] = []
    for row in rows:
        value = row.get("number") if isinstance(row, dict) else row
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise MappingError(f"{field} contains an invalid PR number")
        numbers.append(value)
    if len(set(numbers)) != len(numbers):
        raise MappingError(f"{field} contains duplicate PR numbers")
    return numbers


def _nested_sha(row: dict[str, Any], key: str) -> str | None:
    value = row.get(key)
    if value is not None:
        return _sha(value, f"authoritative pull request {key}")
    nested = row.get("head" if key == "head_sha" else "base")
    if isinstance(nested, dict) and nested.get("sha") is not None:
        return _sha(nested["sha"], f"authoritative pull request {key}")
    return None


def _authoritative_rows(response: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(response, dict):
        raise MappingError("authoritative GitHub API response must be an object")
    rows = response.get("pull_requests")
    if not isinstance(rows, list) or not rows:
        raise MappingError("authoritative GitHub API response has no complete pull_requests mapping")
    if not all(isinstance(row, dict) for row in rows):
        raise MappingError("authoritative pull_requests rows must be objects")
    return rows


def verify(
    identity: dict[str, Any],
    pull_requests: list[Any] | None,
    fetch: Callable[[int], dict[str, Any]],
    authoritative: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(identity, dict) or identity.get("event_name") != "merge_group":
        raise MappingError("merge-group identity is required")
    expected = identity.get("pull_request_numbers")
    if expected is not None:
        expected = _number_rows(expected, "identity pull_request_numbers")
    payload_numbers = _number_rows(pull_requests, "event mapping") if pull_requests else []

    # Real merge-group identities must be backed by the API response. The
    # legacy/minimal unit-test identity is kept compatible for callers that do
    # not yet carry SHA fields; the workflow identity always does.
    requires_authoritative = any(key in identity for key in ("target_sha", "base_sha", "merge_group_id"))
    if requires_authoritative and authoritative is None:
        raise MappingError("authoritative GitHub API mapping is required")

    authoritative_numbers: list[int] | None = None
    authoritative_rows: list[dict[str, Any]] = []
    if authoritative is not None:
        authoritative_rows = _authoritative_rows(authoritative)
        authoritative_numbers = _number_rows(authoritative_rows, "authoritative pull_requests")
        if expected is not None and set(authoritative_numbers) != set(expected):
            raise MappingError("authoritative API and identity PR mappings disagree")
        if payload_numbers and set(authoritative_numbers) != set(payload_numbers):
            raise MappingError("authoritative API and event PR mappings disagree")
        target_sha = identity.get("target_sha")
        response_target = authoritative.get("target_sha")
        if target_sha is not None:
            target_sha = _sha(target_sha, "identity target_sha")
            if response_target is None or _sha(response_target, "authoritative target_sha") != target_sha:
                raise MappingError("authoritative API target_sha does not match merge-group event")
        base_sha = identity.get("base_sha")
        response_base = authoritative.get("base_sha")
        if base_sha is not None:
            base_sha = _sha(base_sha, "identity base_sha")
            if response_base is None or _sha(response_base, "authoritative base_sha") != base_sha:
                raise MappingError("authoritative API base_sha does not match merge-group event")
        group_id = identity.get("merge_group_id")
        response_group = authoritative.get("merge_group_id", authoritative.get("id"))
        if group_id is not None and response_group != group_id:
            raise MappingError("authoritative API merge-group ID does not match event")
        for row in authoritative_rows:
            # The associated-PR endpoint must return the complete PR object,
            # including both SHAs. This prevents a number-only response from
            # being mistaken for proof of provenance.
            if _nested_sha(row, "head_sha") is None or _nested_sha(row, "base_sha") is None:
                raise MappingError("authoritative PR mapping must include head and base SHA")

    resolved_numbers = authoritative_numbers or expected
    if resolved_numbers is None:
        raise MappingError("identity or authoritative API must contain a complete PR mapping")
    if payload_numbers and set(payload_numbers) != set(resolved_numbers):
        raise MappingError("event and resolved identity PR mappings disagree")
    verified: list[int] = []
    for number in resolved_numbers:
        try:
            value = fetch(number)
        except Exception as exc:  # pragma: no cover - adapter boundary
            raise MappingError(f"GitHub API lookup failed for PR {number}") from exc
        if not isinstance(value, dict) or value.get("number") != number:
            raise MappingError(f"GitHub API returned no matching PR {number}")
        if value.get("state") != "open":
            raise MappingError(f"PR {number} is not open in the authoritative API")
        if authoritative_rows:
            row = next(item for item in authoritative_rows if item["number"] == number)
            detail_head = value.get("head", {}).get("sha") if isinstance(value.get("head"), dict) else value.get("head_sha")
            detail_base = value.get("base", {}).get("sha") if isinstance(value.get("base"), dict) else value.get("base_sha")
            row_head = _nested_sha(row, "head_sha")
            row_base = _nested_sha(row, "base_sha")
            if detail_head is not None and _sha(detail_head, f"PR {number} head_sha") != row_head:
                raise MappingError(f"authoritative API PR {number} head SHA disagrees")
            if detail_base is not None and _sha(detail_base, f"PR {number} base_sha") != row_base:
                raise MappingError(f"authoritative API PR {number} base SHA disagrees")
        verified.append(number)
    result: dict[str, Any] = {"verified": True, "pull_request_numbers": verified}
    for key in ("merge_group_id", "target_sha", "base_sha"):
        if key in identity and identity[key] is not None:
            result[key] = identity[key]
    if authoritative is not None:
        result["mapping_source"] = "github-api:associated-pull-requests"
    return result


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MappingError(f"invalid JSON {path}") from exc
    if not isinstance(value, dict):
        raise MappingError(f"expected JSON object: {path}")
    return value


def _load_authoritative_pages(value: Any, *, target_sha: str, base_sha: str, merge_group_id: str | None) -> dict[str, Any]:
    """Normalize ``gh api --paginate --slurp`` output into a checked contract."""
    pages: list[Any]
    if isinstance(value, list) and all(isinstance(page, list) for page in value):
        pages = value
    elif isinstance(value, list):
        pages = [value]
    else:
        raise MappingError("associated-PR GitHub API response must be a JSON array")
    rows: list[Any] = []
    for page in pages:
        rows.extend(page)
    return {
        "merge_group_id": merge_group_id,
        "target_sha": target_sha,
        "base_sha": base_sha,
        "pull_requests": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", type=Path)
    parser.add_argument("--event", type=Path)
    parser.add_argument("--repository")
    parser.add_argument(
        "--authoritative-response",
        type=Path,
        help="offline JSON fixture in the shape returned by gh api --paginate --slurp",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        identity = {"event_name": "merge_group", "pull_request_numbers": [7, 8]}
        assert verify(identity, [{"number": 7}, {"number": 8}], lambda n: {"number": n, "state": "open"})["verified"]
        try:
            verify(identity, [{"number": 7}], lambda n: {"number": n, "state": "open"})
        except MappingError:
            pass
        else:
            raise AssertionError("incomplete mapping was accepted")
        print("merge-group-mapping self-test: OK")
        return 0
    if args.identity is None or args.event is None or not args.repository:
        parser.error("--identity, --event and --repository are required unless --self-test is used")
    try:
        identity = _load(args.identity)
        event = _load(args.event)
        group = event.get("merge_group")
        if not isinstance(group, dict):
            group = event
        rows = group.get("pull_requests")
        if rows is not None and not isinstance(rows, list):
            raise MappingError("merge_group.pull_requests must be a list when present")

        def fetch(number: int) -> dict[str, Any]:
            result = subprocess.run(
                ["gh", "api", f"repos/{args.repository}/pulls/{number}"],
                check=True, capture_output=True, text=True,
            )
            value = json.loads(result.stdout)
            if not isinstance(value, dict):
                raise MappingError("GitHub API response must be an object")
            return value

        if args.authoritative_response is not None:
            authoritative_raw = json.loads(args.authoritative_response.read_text(encoding="utf-8"))
        else:
            target_sha = identity.get("target_sha")
            base_sha = identity.get("base_sha")
            group_id = identity.get("merge_group_id")
            if not isinstance(target_sha, str) or not isinstance(base_sha, str):
                raise MappingError("merge-group identity must include target_sha and base_sha")
            command = [
                "gh", "api", "--paginate", "--slurp",
                "-H", "Accept: application/vnd.github+json",
                f"repos/{args.repository}/commits/{target_sha}/pulls",
            ]
            api_result = subprocess.run(command, check=True, capture_output=True, text=True)
            authoritative_raw = json.loads(api_result.stdout)
            authoritative_raw = _load_authoritative_pages(
                authoritative_raw,
                target_sha=target_sha,
                base_sha=base_sha,
                merge_group_id=group_id if isinstance(group_id, str) else None,
            )
        if isinstance(authoritative_raw, list):
            authoritative = _load_authoritative_pages(
                authoritative_raw,
                target_sha=identity.get("target_sha"),
                base_sha=identity.get("base_sha"),
                merge_group_id=identity.get("merge_group_id"),
            )
        elif isinstance(authoritative_raw, dict):
            authoritative = authoritative_raw
        else:
            raise MappingError("authoritative response must be an object or JSON array")
        result = verify(identity, rows, fetch, authoritative)
    except (MappingError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"merge-group-mapping: ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
