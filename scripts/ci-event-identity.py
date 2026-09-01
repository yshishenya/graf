#!/usr/bin/env python3
"""Resolve a GitHub CI event to one exact, auditable target identity."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,256}$")


class IdentityError(ValueError):
    """Raised when an event cannot be resolved without guessing."""


def _sha(value: Any, field: str, *, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise IdentityError(f"{field} must be a full 40-character SHA")
    return value.lower()


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise IdentityError(f"{field} must be a positive integer")
    return value


def _same_value(left: Any, right: Any, field: str) -> Any:
    """Reject duplicate payload representations that disagree."""
    if left is not None and right is not None and left != right:
        raise IdentityError(f"conflicting values for {field}")
    return left if left is not None else right


def resolve(event: dict[str, Any], *, event_name: str | None = None) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise IdentityError("event must be a JSON object")
    payload_name = event.get("event_name")
    if payload_name is not None and (not isinstance(payload_name, str) or not payload_name.strip()):
        raise IdentityError("event.event_name must be a non-empty string when present")
    if event_name and payload_name and event_name != payload_name:
        raise IdentityError("event_name argument conflicts with event.event_name")
    name = event_name or str(payload_name or "").strip()
    if name not in {"pull_request", "merge_group", "workflow_dispatch"}:
        raise IdentityError("event_name must be pull_request, merge_group or workflow_dispatch")

    if name == "pull_request":
        pull = event.get("pull_request")
        if not isinstance(pull, dict):
            raise IdentityError("pull_request payload is required")
        head = pull.get("head")
        base = pull.get("base")
        if not isinstance(head, dict) or not isinstance(base, dict):
            raise IdentityError("pull_request head and base payloads are required")
        target_sha = _sha(head.get("sha"), "pull_request.head.sha")
        base_sha = _sha(base.get("sha"), "pull_request.base.sha")
        number_value = _same_value(event.get("number"), pull.get("number"), "pull_request.number")
        number = _positive_int(number_value, "pull_request.number")
        return {
            "schema_version": 1,
            "event_name": name,
            "target_sha": target_sha,
            "base_sha": base_sha,
            "pull_request_numbers": [number],
            "merge_group_id": None,
            "concurrency_key": f"pr-{number}",
        }

    if name == "merge_group":
        # GitHub's event payload nests these values under ``merge_group``;
        # normalized fixtures may keep them at the root.  Accept both only
        # when duplicate representations agree.
        group = event.get("merge_group")
        if group is None:
            group = {}
        if not isinstance(group, dict):
            raise IdentityError("merge_group payload must be an object")
        target_value = _same_value(event.get("head_sha"), group.get("head_sha"), "merge_group.head_sha")
        base_value = _same_value(event.get("base_sha"), group.get("base_sha"), "merge_group.base_sha")
        target_sha = _sha(target_value, "merge_group.head_sha")
        base_sha = _sha(base_value, "merge_group.base_sha")
        group_id = _same_value(
            _same_value(event.get("id"), event.get("merge_group_id"), "merge_group.id"),
            group.get("id"),
            "merge_group.id",
        )
        if group_id is None:
            # GitHub's checks_requested merge_group payload omits an ID.  The
            # head SHA is the stable event identity; membership is resolved
            # separately against GitHub's associated-PR API.
            group_id = f"mg-{target_sha[:12]}"
        if not isinstance(group_id, str) or not group_id.strip():
            raise IdentityError("merge_group.id is required")
        group_id = group_id.strip()
        if not SAFE_ID_RE.fullmatch(group_id):
            raise IdentityError("merge_group.id contains unsafe characters")
        rows = event.get("pull_requests")
        nested_rows = group.get("pull_requests")
        if rows is not None and nested_rows is not None and rows != nested_rows:
            raise IdentityError("conflicting values for merge_group.pull_requests")
        rows = rows if rows is not None else nested_rows
        root_numbers = event.get("pull_request_numbers")
        nested_numbers = group.get("pull_request_numbers")
        if root_numbers is not None and nested_numbers is not None and root_numbers != nested_numbers:
            raise IdentityError("conflicting values for merge_group.pull_request_numbers")
        if rows is None:
            rows = root_numbers if root_numbers is not None else nested_numbers
        if rows is None:
            # Real GitHub payloads do not include PR membership. The workflow
            # must fill this from the authoritative associated-PR API before
            # emitting a terminal receipt.
            numbers = []
        elif not isinstance(rows, list) or not rows:
            raise IdentityError("merge_group.pull_requests mapping is required when present")
        else:
            numbers = []
            for row in rows:
                if isinstance(row, dict):
                    value = row.get("number")
                else:
                    value = row
                numbers.append(_positive_int(value, "merge_group.pull_requests.number"))
            if len(set(numbers)) != len(numbers):
                raise IdentityError("merge_group.pull_requests contains duplicate PR numbers")
        return {
            "schema_version": 1,
            "event_name": name,
            "target_sha": target_sha,
            "base_sha": base_sha,
            "pull_request_numbers": numbers,
            "merge_group_id": group_id,
            "concurrency_key": f"merge-group-{group_id}",
        }

    inputs = event.get("inputs")
    if not isinstance(inputs, dict):
        raise IdentityError("workflow_dispatch.inputs is required")
    target_value = inputs.get("target_sha")
    requested_value = inputs.get("requested_sha")
    if target_value is not None and requested_value is not None and target_value != requested_value:
        raise IdentityError("workflow_dispatch target_sha and requested_sha must match")
    if target_value is None:
        target_value = requested_value
    target_field = "workflow_dispatch.inputs.target_sha" if inputs.get("target_sha") is not None else "workflow_dispatch.inputs.requested_sha"
    target_sha = _sha(target_value, target_field)
    return {
        "schema_version": 1,
        "event_name": name,
        "target_sha": target_sha,
        "base_sha": None,
        "pull_request_numbers": [],
        "merge_group_id": None,
        "concurrency_key": f"manual-{target_sha}",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("event", type=Path, nargs="?")
    parser.add_argument("--event-name")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        sha = "a" * 40
        assert resolve({"pull_request": {"head": {"sha": sha}, "base": {"sha": "b" * 40}}, "number": 7}, event_name="pull_request")["concurrency_key"] == "pr-7"
        assert resolve({"head_sha": sha, "base_sha": "b" * 40, "id": "mg-1", "pull_requests": [{"number": 7}]}, event_name="merge_group")["merge_group_id"] == "mg-1"
        assert resolve({"inputs": {"target_sha": sha}}, event_name="workflow_dispatch")["base_sha"] is None
        for bad in ({}, {"inputs": {}}, {"head_sha": sha, "base_sha": "b" * 40, "id": "x", "pull_requests": []}):
            try:
                resolve(bad, event_name="workflow_dispatch" if "inputs" in bad else "merge_group")
            except IdentityError:
                pass
            else:
                raise AssertionError("malformed event was accepted")
        print("ci-event-identity self-test: OK")
        return 0
    if args.event is None:
        parser.error("event is required unless --self-test is used")
    try:
        payload = json.loads(args.event.read_text(encoding="utf-8"))
        result = resolve(payload, event_name=args.event_name)
    except (OSError, UnicodeError, json.JSONDecodeError, IdentityError) as exc:
        print(f"ci-event-identity: ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
