#!/usr/bin/env python3
"""Evaluate the collector's metadata. No probes, mutations or payload reads."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import time

CLASSES = {
    "relational", "events", "object_storage", "queue_cache", "broker",
    "coordination", "runtime_auxiliary", "graf_analytics_tables", "backup_artifacts",
}
INITIAL_CEILING = 128 * 1024**3
REVIEW_DEADLINE = int(datetime(2026, 11, 21, tzinfo=UTC).timestamp())


def sha(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def nonnegative(value: object) -> bool:
    return type(value) is int and value >= 0


def evaluate(sample: object, budget: object, *, now: int, config_version: str) -> dict:
    """Incomplete sizes cannot hide a separately verified low-space signal."""
    sample = sample if isinstance(sample, dict) else {}
    budget = budget if isinstance(budget, dict) else {}
    epoch = sample.get("recorded_at_epoch")
    fresh = type(epoch) is int and epoch > 0 and 0 <= now - epoch < 120
    inventory = sample.get("inventory_version")
    classes = sample.get("classes")
    amount = sample.get("analytics_storage_bytes")
    size_verified = (
        fresh and type(sample.get("storage_sample_version")) is int
        and sample.get("storage_sample_version") == 2
        and sample.get("result") == "complete" and sha(inventory)
        and isinstance(classes, dict) and set(classes) == CLASSES
        and all(nonnegative(value) for value in classes.values())
        and nonnegative(amount) and sum(classes.values()) == amount
        and sample.get("reasons") == []
    )
    complete = size_verified
    analytics_reasons, host_reasons, disable_reasons = [], [], []
    resources = []
    seen = set()
    filesystems = sample.get("filesystems")
    if not isinstance(filesystems, list) or not filesystems:
        filesystems = []
        complete = False
    for fs in filesystems:
        if not isinstance(fs, dict):
            complete = False
            continue
        identity, total, available, roles = (
            fs.get("identity"), fs.get("total_bytes"), fs.get("available_bytes"), fs.get("roles")
        )
        valid = (
            sha(identity) and nonnegative(total) and total > 0
            and nonnegative(available) and available <= total
            and isinstance(roles, list) and bool(roles)
            and all(role in ("analytics", "host") for role in roles)
            and len(set(roles)) == len(roles)
        )
        if not valid:
            complete = False
            continue
        if identity in seen:
            complete = False
        else:
            seen.add(identity)
            resources.append({"identity": identity, "total_bytes": total,
                              "available_bytes": available, "roles": roles})
        if fresh and "analytics" in roles and 100 * available < 20 * total:
            analytics_reasons.append("analytics_storage")
            disable_reasons.append("analytics_storage")
        if fresh and "host" in roles and 100 * available < 10 * total:
            host_reasons.append("host_disk")
    if {role for fs in resources for role in fs["roles"]} != {"analytics", "host"}:
        complete = False
    accepted_at, deadline, limit = (
        budget.get("accepted_at_epoch"), budget.get("review_deadline_epoch"),
        budget.get("analytics_budget_bytes"),
    )
    accepted = (
        type(budget.get("budget_state_version")) is int
        and budget.get("budget_state_version") == 1 and budget.get("status") == "accepted"
        and budget.get("role") == "infra_operator" and sha(budget.get("budget_version"))
        and sha(inventory) and budget.get("inventory_version") == inventory
        and sha(config_version) and budget.get("config_version") == config_version
        and sha(budget.get("t097_evidence_sha256"))
        and type(accepted_at) is int and 0 < accepted_at <= now
        and type(deadline) is int and now < deadline <= REVIEW_DEADLINE
        and nonnegative(limit) and 0 < limit <= INITIAL_CEILING
    )
    # The ceiling protects the disk even while operator acceptance is pending.
    protection_limit = limit if accepted else INITIAL_CEILING
    if size_verified and amount >= protection_limit:
        analytics_reasons.append("analytics_storage_budget")
        disable_reasons.append("analytics_storage_budget")
    if not complete:
        analytics_reasons.append("capacity_input_unverified")
    if not accepted:
        analytics_reasons.append("capacity_budget_unverified")
    return {
        "capacity_state_version": 1, "recorded_at_epoch": now,
        "sample_epoch": epoch if type(epoch) is int else None,
        "inventory_version": inventory if sha(inventory) else "unknown",
        "budget_version": budget.get("budget_version") if accepted else "unknown",
        "input_verified": bool(complete), "budget_accepted": bool(accepted),
        "capacity_ready": bool(complete and accepted and not disable_reasons),
        "analytics_storage_bytes": amount if size_verified else None,
        "analytics_budget_bytes": limit if accepted else None,
        "filesystems": resources if fresh else [],
        "analytics_reasons": sorted(set(analytics_reasons)),
        "host_reasons": sorted(set(host_reasons)),
        "disable_reasons": sorted(set(disable_reasons)),
    }


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError, UnicodeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--budget", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(read_json(args.sample), read_json(args.budget), now=int(time.time()),
                      config_version=os.environ.get("GRAF_POSTHOG_GUARD_CONFIG_VERSION", ""))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["capacity_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
