#!/usr/bin/env python3
"""Evaluate collector metadata and durably latch analytics protection incidents."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import hashlib
import math
import os
from pathlib import Path
import re
import runpy
import time
import uuid

CLASSES = {
    "relational", "events", "object_storage", "queue_cache", "broker",
    "coordination", "runtime_auxiliary", "graf_analytics_tables", "backup_artifacts",
}
INITIAL_CEILING = 128 * 1024**3
REVIEW_DEADLINE = int(datetime(2026, 11, 21, tzinfo=UTC).timestamp())
DISABLED_ENV = dict.fromkeys((
    "TWOBRAIN_PRODUCT_ANALYTICS_ENABLED",
    "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_ENABLED",
    "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_WEB_DIRECT_ENABLED",
    "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_DESKTOP_DIRECT_ENABLED",
    "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_AUTOCAPTURE_ENABLED",
    "TWOBRAIN_PRODUCT_ANALYTICS_REPLAY_ENABLED",
    "TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_ALL_PAGES_ENABLED",
    "TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OFFLINE_ENABLED",
), "false") | {
    "TWOBRAIN_PRODUCT_ANALYTICS_PROVIDER_MODE": "disabled",
    "TWOBRAIN_PRODUCT_ANALYTICS_VALIDATION_MODE": "disabled",
}
PROTECTION_STATES = {"observed", "protection_requested", "blocked_dry_run",
                     "not_enabled", "apply_failed", "protected"}


def transition(path: Path, reasons: list[str], action: str, *, now: int,
               runtime_env: object = None, scope: str = "posthog") -> str:
    """Caller holds guard.lock. Persist the incident before changing switches."""
    if scope not in ("posthog", "graf-local"):
        raise ValueError("protection_state_unverified")
    try:
        info = path.lstat()
        import stat
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("protection_state_unverified")
        exists = True
    except FileNotFoundError:
        exists = False
    state = read_json(path) if exists else {
        "protection_state_version": 2, "measurement_scope": scope, "status": "observed", "reasons": [], "recorded_at_epoch": now,
    }
    if (not isinstance(state, dict) or type(state.get("protection_state_version")) is not int
            or state.get("protection_state_version") != 2
            or state.get("measurement_scope") != scope
            or not isinstance(state.get("status"), str)
            or state.get("status") not in PROTECTION_STATES
            or not isinstance(state.get("reasons"), list)
            or any(not isinstance(code, str) or not re.fullmatch(r"[a-z_]+", code)
                   for code in state["reasons"] + reasons)
            or (state["status"] == "observed" and state["reasons"])):
        raise ValueError("protection_state_unverified")
    if state["status"] != "observed" and (
        not isinstance(state.get("incident_id"), str)
        or re.fullmatch(r"[a-f0-9]{32}", state["incident_id"]) is None
    ):
        raise ValueError("protection_state_unverified")
    if state["status"] == "protected" and not sha(state.get("applied_config_sha256")):
        raise ValueError("protection_state_unverified")
    if action == "status":
        if not exists:
            writer = runpy.run_path(str(Path(__file__).with_name("posthog-storage.py")))["atomic_json"]
            writer(path, state)
        return state["status"]
    if action not in PROTECTION_STATES - {"observed"}:
        raise ValueError("protection_action_invalid")
    if action == "protected":
        # Inspect only running container Config.Env, never print its values.
        if not isinstance(runtime_env, list) or not all(isinstance(v, str) for v in runtime_env):
            raise ValueError("protection_readback_unverified")
        entries = [value.partition("=") for value in runtime_env]
        if any(len([row for row in entries if row[0] == key]) != 1
               or next((row[2] for row in entries if row[0] == key), None) != value
               for key, value in DISABLED_ENV.items()):
            raise ValueError("protection_readback_unverified")
    if state["status"] == "observed":
        if action != "protection_requested" or not reasons:
            raise ValueError("protection_request_required")
        state["incident_id"] = uuid.uuid4().hex
        state["started_at_epoch"] = now
    # A successful incident remains latched, including after symptoms disappear.
    if state["status"] != "protected":
        state["status"] = action
    state["reasons"] = sorted(set(state["reasons"] + reasons))
    state["recorded_at_epoch"] = now
    if state["status"] == "protected":
        state["applied_config_sha256"] = hashlib.sha256(
            json.dumps(DISABLED_ENV, sort_keys=True).encode()).hexdigest()
    # Reuse the collector's durable writer rather than introduce another one.
    writer = runpy.run_path(str(Path(__file__).with_name("posthog-storage.py")))["atomic_json"]
    writer(path, state)
    return state["status"]


def restore(path: Path, receipt: object, sample: object, budget: object, runtime_env: object,
            *, now: int, config_version: str, scope: str = "posthog") -> str:
    """Manual Restoration only. The timer never calls this entry point."""
    path.lstat()  # Missing/linked/old state is never a new restoration incident.
    transition(path, [], "status", now=now, scope=scope)
    state = read_json(path)
    decision = evaluate(sample, budget, now=now, config_version=config_version, expected_scope=scope)
    if (not isinstance(state, dict) or state.get("status") not in PROTECTION_STATES - {"observed"}
            or not isinstance(receipt, dict) or type(receipt.get("restore_receipt_version")) is not int
            or receipt.get("restore_receipt_version") != 2
            or receipt.get("measurement_scope") != scope
            or receipt.get("incident_id") != state.get("incident_id")
            or not isinstance(state.get("incident_id"), str)
            or re.fullmatch(r"[a-f0-9]{32}", state["incident_id"]) is None
            or receipt.get("role") != "infra_operator"
            or receipt.get("config_version") != config_version
            or receipt.get("budget_version") != decision["budget_version"]
            or not decision["capacity_ready"]):
        raise ValueError("restoration_unverified")
    approved, expiry, started = (receipt.get("approved_at_epoch"), receipt.get("expires_at_epoch"),
                                 state.get("started_at_epoch"))
    if (type(approved) is not int or type(expiry) is not int or type(started) is not int
            or not 0 < started <= approved <= now < expiry <= budget["review_deadline_epoch"]):
        raise ValueError("restoration_unverified")
    proofs = receipt.get("proofs")
    required = {"growth_review", "expansion_review", "runtime_review", "basis_consent_review"}
    required |= {"provider_smoke", "page_validation"} if scope == "posthog" else {"local_measurement_review"}
    if not isinstance(proofs, dict) or not required.issubset(proofs) or any(not sha(proofs[p]) for p in required):
        raise ValueError("restoration_unverified")
    growth = sample.get("growth", {})
    rates = growth.get("bytes_per_day") if isinstance(growth, dict) else None
    if (not isinstance(rates, dict) or set(rates) != CLASSES or growth.get("result") != "measured"
            or any(type(rate) not in (int, float) or not math.isfinite(rate) or rate < 0 for rate in rates.values())
            or type(growth.get("interval_seconds")) is not int or growth["interval_seconds"] < 86400
            or type(growth.get("end_epoch")) is not int or not 0 < growth["end_epoch"] <= now
            or sum(rates.values()) > 536870912
            or sample["analytics_storage_bytes"] + sum(rates.values()) * 90 >= budget["analytics_budget_bytes"]):
        raise ValueError("restoration_unverified")
    if not isinstance(runtime_env, list) or not all(isinstance(v, str) for v in runtime_env):
        raise ValueError("restoration_readback_unverified")
    entries = [v.partition("=") for v in runtime_env]
    if any(sum(row[0] == key for row in entries) != 1 for key in DISABLED_ENV):
        raise ValueError("restoration_readback_unverified")
    effective = {row[0]: row[2] for row in entries if row[0] in DISABLED_ENV}
    digest = hashlib.sha256(json.dumps(effective, sort_keys=True).encode()).hexdigest()
    if receipt.get("runtime_env_sha256") != digest:
        raise ValueError("restoration_readback_unverified")
    writer = runpy.run_path(str(Path(__file__).with_name("posthog-storage.py")))["atomic_json"]
    writer(path, {"protection_state_version": 2, "measurement_scope": scope, "status": "observed", "reasons": [],
                  "recorded_at_epoch": now, "closed_incident_id": state["incident_id"],
                  "restoration_receipt_sha256": hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest(),
                  "applied_config_sha256": digest})
    return "observed"


def sha(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def nonnegative(value: object) -> bool:
    return type(value) is int and value >= 0


def evaluate(sample: object, budget: object, *, now: int, config_version: str,
             expected_scope: str = "posthog") -> dict:
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
        and sample.get("storage_sample_version") == 3
        and expected_scope in ("posthog", "graf-local")
        and sample.get("measurement_scope") == expected_scope
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
        "capacity_state_version": 1, "measurement_scope": expected_scope, "recorded_at_epoch": now,
        "sample_epoch": epoch if type(epoch) is int else None,
        "inventory_version": inventory if sha(inventory) else "unknown",
        "budget_version": budget.get("budget_version") if accepted else "unknown",
        "input_verified": bool(complete), "budget_accepted": bool(accepted),
        "capacity_ready": bool(complete and accepted and not disable_reasons),
        "analytics_storage_bytes": amount if size_verified else None,
        "analytics_budget_bytes": limit if accepted else None,
        "budget_deadline_epoch": deadline if accepted else None,
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
    parser.add_argument("--scope", choices=("posthog", "graf-local"), default="posthog")
    parser.add_argument("--sample", type=Path)
    parser.add_argument("--budget", type=Path)
    parser.add_argument("--shell", action="store_true")
    parser.add_argument("--protection-state", type=Path)
    parser.add_argument("--protection-action", default="status")
    parser.add_argument("--reasons", default="")
    parser.add_argument("--restore-receipt", type=Path)
    args = parser.parse_args()
    if args.protection_state is not None:
        import sys
        try:
            if args.restore_receipt is not None:
                if args.sample is None or args.budget is None:
                    raise ValueError("restoration_unverified")
                # Serialize manual restoration with the same guard lock.
                import fcntl
                with (args.protection_state.parent / "guard.lock").open("a") as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    print(restore(args.protection_state, read_json(args.restore_receipt),
                                  read_json(args.sample), read_json(args.budget), json.load(sys.stdin),
                                  now=int(time.time()),
                                  config_version=os.environ.get("GRAF_POSTHOG_GUARD_CONFIG_VERSION", ""), scope=args.scope))
                return 0
            runtime = json.load(sys.stdin) if args.protection_action == "protected" else None
            print(transition(args.protection_state, [c for c in args.reasons.split(",") if c],
                             args.protection_action, now=int(time.time()), runtime_env=runtime, scope=args.scope))
            return 0
        except (OSError, ValueError, TypeError):
            print("protection_state_unverified")
            return 1
    if args.sample is None or args.budget is None:
        parser.error("--sample and --budget are required for capacity evaluation")
    result = evaluate(read_json(args.sample), read_json(args.budget), now=int(time.time()),
                      config_version=os.environ.get("GRAF_POSTHOG_GUARD_CONFIG_VERSION", ""), expected_scope=args.scope)
    if args.shell:
        for key in ("capacity_ready", "input_verified", "budget_accepted", "sample_epoch",
                    "inventory_version", "budget_version", "analytics_storage_bytes", "analytics_budget_bytes",
                    "budget_deadline_epoch"):
            value = result[key]
            print(f"{key}={str(value).lower() if value is not None else 'unknown'}")
        for key in ("analytics_reasons", "host_reasons", "disable_reasons"):
            print(f"{key}={','.join(result[key])}")
        print("filesystems=" + json.dumps(result["filesystems"], sort_keys=True, separators=(",", ":")))
        for role in ("analytics", "host"):
            values = [100 * fs["available_bytes"] / fs["total_bytes"]
                      for fs in result["filesystems"] if role in fs["roles"]]
            print(f"{role}_free_percent={min(values) if values else 'unknown'}")
    else:
        print(json.dumps(result, sort_keys=True))
    return 0 if result["capacity_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
