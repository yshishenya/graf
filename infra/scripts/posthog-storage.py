#!/usr/bin/env python3
"""Allocated analytics storage. Reads metadata only, never event/meeting contents.

Run on the host as infrastructure operator. Docker/catalog output and paths stay
in memory. Receipts contain only classes, counts, hashes, byte sizes and time.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import fcntl
import fnmatch
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time

CLASSES = (
    "relational", "events", "object_storage", "queue_cache", "broker",
    "coordination", "runtime_auxiliary", "graf_analytics_tables", "backup_artifacts",
)
VOLUME_CLASSES = {
    "postgres-data": "relational", "clickhouse-data": "events",
    "objectstorage": "object_storage", "seaweedfs": "object_storage",
    "posthog-media": "object_storage", "redis*-data": "queue_cache",
    "kafka-data": "broker", "redpanda-data": "broker",
    "zookeeper-*": "coordination", "caddy-*": "runtime_auxiliary",
}


class Incomplete(Exception):
    """Code-only error: private command/path details must not reach output."""


def command(*args: str) -> str:
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL, timeout=30)
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        raise Incomplete("metadata_probe_failed") from exc


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def records(path: Path) -> list[list[str]]:
    return [line.split() for raw in path.read_text().splitlines()
            if (line := raw.partition("#")[0].strip())]


def atomic_json(path: Path, value: dict) -> None:
    descriptor, name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(value, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, 0o640)
        os.replace(name, path)
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def filesystem(path: Path) -> dict:
    info = path.stat()
    fs = os.statvfs(path)
    total = fs.f_blocks * fs.f_frsize
    available = fs.f_bavail * fs.f_frsize
    if total <= 0 or available < 0 or available > total:
        raise Incomplete("filesystem_unverified")
    return {"identity": digest([info.st_dev, getattr(fs, "f_fsid", info.st_dev)]),
            "total_bytes": total, "available_bytes": available}


def allocated(roots: list[tuple[str, Path]]) -> tuple[dict[str, int], list[Path]]:
    """Count allocated blocks once; reject cross-class aliases/overlap and links."""
    normalized: list[tuple[str, Path]] = []
    for category, path in sorted(roots, key=lambda item: len(item[1].parts)):
        if category not in CLASSES or path.is_symlink():
            raise Incomplete("unclassified_or_linked_root")
        path = path.resolve(strict=True)
        covered = False
        for prior_class, prior in normalized:
            if path == prior or prior in path.parents:
                if category != prior_class:
                    raise Incomplete("storage_classes_overlap")
                covered = True
        if not covered:
            normalized.append((category, path))
    amounts = dict.fromkeys(CLASSES, 0)
    seen: dict[tuple[int, int], str] = {}
    for category, root in normalized:
        root_device = root.stat().st_dev
        pending = [root]
        while pending:
            path = pending.pop()
            info = path.lstat()
            if info.st_dev != root_device:
                raise Incomplete("unresolved_link_or_nested_filesystem")
            if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)):
                raise Incomplete("unsupported_storage_object")
            identity = info.st_dev, info.st_ino
            if identity in seen:
                if seen[identity] != category:
                    raise Incomplete("storage_classes_overlap")
                continue
            seen[identity] = category
            amounts[category] += info.st_blocks * 512
            if stat.S_ISLNK(info.st_mode):
                try:
                    target = path.resolve(strict=True)
                except (OSError, RuntimeError) as exc:
                    raise Incomplete("unresolved_storage_link") from exc
                owners = {owner for owner, known in normalized if target == known or known in target.parents}
                if owners != {category}:
                    raise Incomplete("storage_link_outside_classified_roots")
                # Every known root is walked separately. Count the link's blocks
                # here; its target is already covered, including ClickHouse store.
                continue
            if stat.S_ISDIR(info.st_mode):
                pending.extend(path.iterdir())
    return amounts, [path for _, path in normalized]


def runtime_roots(directory: Path, project: str) -> tuple[list[tuple[str, Path]], str]:
    rows = records(directory / "storage-mounts.txt")
    rules = {(service, destination): category for service, destination, category in rows}
    if len(rules) != len(rows) or any(c not in CLASSES for c in rules.values()):
        raise Incomplete("mount_inventory_invalid")
    ids = command("docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={project}").split()
    if not ids:
        raise Incomplete("analytics_runtime_missing")
    containers = json.loads(command("docker", "inspect", *ids))
    roots = []
    scope = []
    mounted_volumes = set()
    for container in containers:
        service = container["Config"]["Labels"]["com.docker.compose.service"]
        for mount in container["Mounts"]:
            category = rules.get((service, mount["Destination"]))
            if category is None or mount["Type"] not in ("bind", "volume"):
                raise Incomplete("runtime_mount_unclassified")
            roots.append((category, Path(mount["Source"])))
            scope.append([service, mount["Destination"], category, digest(mount["Source"])])
            if mount["Type"] == "volume":
                mounted_volumes.add(mount["Name"])
    # Detached named/project-labelled volumes still consume analytics storage.
    names = set(command("docker", "volume", "ls", "-q").split())
    labelled = set(command("docker", "volume", "ls", "-q", "--filter",
                           f"label=com.docker.compose.project={project}").split())
    inventory = [row[0] for row in records(directory / "backup-volumes.txt")]
    patterns = [p.replace("graf-posthog_", project + "_", 1) for p in inventory]
    for pattern in patterns:
        matches = [name for name in names if fnmatch.fnmatchcase(name, pattern.rstrip("?"))]
        if not matches and not pattern.endswith("?"):
            raise Incomplete("required_volume_missing")
    for name in sorted((labelled | {n for n in names if n.startswith(project + "_")}) - mounted_volumes):
        suffix = name.removeprefix(project + "_")
        classes = {value for pattern, value in VOLUME_CLASSES.items() if fnmatch.fnmatchcase(suffix, pattern)}
        if len(classes) != 1 or not any(fnmatch.fnmatchcase(name, p.rstrip("?")) for p in patterns):
            raise Incomplete("detached_volume_unclassified")
        category = classes.pop()
        volume = json.loads(command("docker", "volume", "inspect", name))[0]
        roots.append((category, Path(volume["Mountpoint"])))
        scope.append(["detached", digest(name), category])
    if not {"relational", "events"}.issubset({c for c, _ in roots}):
        raise Incomplete("required_storage_class_missing")
    return roots, digest([rows, inventory, sorted({tuple(row) for row in scope})])


def graf_relation_roots(directory: Path) -> tuple[list[tuple[str, Path]], str, int, list[str]]:
    inventory = [row[0] for row in records(directory / "storage-relations.txt")]
    if not inventory or any(not re.fullmatch(r"public\.[a-z_]+\??", name) for name in inventory):
        raise Incomplete("relation_inventory_invalid")
    ids = command("docker", "ps", "-q", "--filter", "label=com.docker.compose.service=rec-postgres").split()
    if len(ids) != 1:
        raise Incomplete("graf_database_ambiguous")
    container = json.loads(command("docker", "inspect", ids[0]))[0]
    names = ",".join("'" + n.rstrip("?") + "'" for n in inventory)
    query = f"""WITH RECURSIVE owned(oid) AS (
      SELECT to_regclass(name)::oid FROM unnest(ARRAY[{names}]) name WHERE to_regclass(name) IS NOT NULL
      UNION SELECT dependency.oid FROM owned o JOIN LATERAL (
        SELECT indexrelid AS oid FROM pg_index WHERE indrelid=o.oid
        UNION SELECT reltoastrelid FROM pg_class WHERE oid=o.oid AND reltoastrelid<>0
        UNION SELECT inhrelid FROM pg_inherits WHERE inhparent=o.oid
      ) dependency ON true
    ) SELECT json_build_object('data_directory',current_setting('data_directory'),
      'present',(SELECT json_agg(name) FROM unnest(ARRAY[{names}]) name WHERE to_regclass(name) IS NOT NULL),
      'files',(SELECT json_agg(pg_relation_filepath(oid)) FROM owned WHERE pg_relation_filepath(oid) IS NOT NULL));"""
    metadata = json.loads(command("docker", "exec", ids[0], "psql", "-U", "twobrain_rec", "-d", "twobrain_rec", "-tAqc", query))
    present = set(metadata["present"] or [])
    if any(n not in present for n in inventory if not n.endswith("?")):
        raise Incomplete("graf_relation_missing")
    data = Path(metadata["data_directory"])
    mounts = [m for m in container["Mounts"] if Path(m["Destination"]) == data or Path(m["Destination"]) in data.parents]
    if len(mounts) != 1:
        raise Incomplete("graf_database_mount_unverified")
    mount = mounts[0]
    base = Path(mount["Source"]) / data.relative_to(mount["Destination"])
    roots = []
    for relative in metadata["files"] or []:
        # Tablespaces/symlinks require review; never fall back to product DB size.
        if not re.fullmatch(r"base/\d+/\d+", relative):
            raise Incomplete("relation_path_unverified")
        path = base / relative
        family = re.compile(re.escape(path.name) + r"(?:_(?:fsm|vm|init))?(?:\.\d+)?")
        files = [p for p in path.parent.iterdir() if family.fullmatch(p.name)]
        if path not in files:
            raise Incomplete("relation_file_missing")
        roots.extend(("graf_analytics_tables", p) for p in files)
    absent = [name.rstrip("?") for name in inventory if name.endswith("?") and name.rstrip("?") not in present]
    return roots, digest([inventory, sorted(present)]), len(present), absent


def event_count(project: str, start: int, end: int) -> int:
    ids = command("docker", "ps", "-q", "--filter", f"label=com.docker.compose.project={project}",
                  "--filter", "label=com.docker.compose.service=clickhouse").split()
    table = os.environ.get("GRAF_POSTHOG_GUARD_EVENTS_TABLE", "events")
    if len(ids) != 1 or not re.fullmatch(r"[a-zA-Z_][a-zA-Z_0-9]*(?:\.[a-zA-Z_][a-zA-Z_0-9]*)?", table):
        raise Incomplete("event_count_unverified")
    # Counts only; do not select properties, identities or event contents.
    value = command("docker", "exec", ids[0], "clickhouse-client", "--query",
                    f"SELECT count() FROM {table} WHERE timestamp >= toDateTime({start}) "
                    f"AND timestamp < toDateTime({end})").strip()
    if not value.isascii() or not value.isdecimal():
        raise Incomplete("event_count_unverified")
    return int(value)


def measured_growth(sample: dict, anchor: dict, now: int) -> tuple[dict, dict]:
    if not isinstance(anchor, dict):
        return {"result": "incomplete", "reason": "growth_anchor_invalid"}, {}
    if anchor.get("inventory_version") != sample["inventory_version"]:
        return {"result": "pending", "reason": "two_comparable_samples_required"}, sample
    epoch = anchor.get("recorded_at_epoch")
    if type(epoch) is not int or epoch <= 0:
        return {"result": "incomplete", "reason": "growth_anchor_invalid"}, anchor
    if not isinstance(anchor.get("classes"), dict) or any(type(anchor["classes"].get(c)) is not int or anchor["classes"][c] < 0 for c in CLASSES):
        return {"result": "incomplete", "reason": "growth_anchor_invalid"}, anchor
    elapsed = now - epoch
    if elapsed < 0:
        return {"result": "incomplete", "reason": "growth_anchor_future"}, anchor
    previous = anchor.get("last_growth")
    if previous is not None:
        if (not isinstance(previous, dict)
                or previous.get("result") not in ("measured", "decrease_requires_review")
                or previous.get("end_epoch") != epoch
                or type(previous.get("interval_seconds")) is not int
                or previous["interval_seconds"] < 86400
                or not isinstance(previous.get("bytes_per_day"), dict)
                or any(type(previous["bytes_per_day"].get(c)) not in (int, float)
                       or not math.isfinite(previous["bytes_per_day"][c]) for c in CLASSES)):
            return {"result": "incomplete", "reason": "growth_anchor_invalid"}, anchor
    if elapsed < max(86400, sample.get("window_hours", 24) * 3600):
        return anchor.get("last_growth", {"result": "pending", "reason": "interval_under_24h"}), anchor
    rates = {c: (sample["classes"][c] - anchor["classes"][c]) * 86400 / elapsed for c in CLASSES}
    result = {"result": "measured" if all(rate >= 0 for rate in rates.values()) else "decrease_requires_review",
              "start_epoch": anchor["recorded_at_epoch"], "end_epoch": now, "interval_seconds": elapsed,
              "bytes_per_day": rates,
              "live_bytes_per_day": sum(rate for c, rate in rates.items() if c != "backup_artifacts"),
              "archive_bytes_per_day": rates["backup_artifacts"]}
    return result, {**sample, "last_growth": result}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--window-hours", type=int, default=24)
    args = parser.parse_args()
    os.umask(0o077)
    state = Path(os.environ.get("GRAF_POSTHOG_STORAGE_STATE_FILE", str(Path(os.environ.get("GRAF_POSTHOG_STORAGE_STATE_DIR", "/var/lib/graf-posthog-storage")) / "storage-growth-state")))
    if args.status:
        print(state.read_text() if state.is_file() else "storage_growth_state=missing")
        return 0
    state.parent.mkdir(parents=True, exist_ok=True)
    # ponytail: one host-wide lock; split only if multiple stacks require it.
    with (state.parent / "storage.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        sample = {"storage_sample_version": 2, "result": "incomplete", "reasons": []}
        measured_paths = []
        try:
            if args.window_hours <= 0:
                raise Incomplete("window_hours_invalid")
            directory = Path(os.environ.get("GRAF_POSTHOG_STORAGE_INVENTORY_DIR", str(Path(__file__).resolve().parents[1] / "posthog")))
            roots, mount_version = runtime_roots(directory, os.environ.get("GRAF_POSTHOG_PROJECT", "graf-posthog"))
            graf_roots, relation_version, present, absent = graf_relation_roots(directory)
            backup = Path(os.environ.get("GRAF_POSTHOG_BACKUP_DIR", "/var/backups/graf-posthog"))
            if not backup.is_dir():
                raise Incomplete("backup_storage_unverified")
            roots += graf_roots + [("backup_artifacts", backup)]
            measured_paths = [path for _, path in roots]
            amounts, measured_paths = allocated(roots)
            sample.update(result="complete", classes=amounts, analytics_storage_bytes=sum(amounts.values()),
                          class_status={c: "present" if c in {category for category, _ in roots}
                                        else "not_present_in_reviewed_runtime" for c in CLASSES},
                          graf_relations_present=present,
                          graf_relations_not_present=absent,
                          inventory_version=digest([mount_version, relation_version]))
        except (Incomplete, OSError, ValueError, KeyError, TypeError) as exc:
            sample["reasons"].append(str(exc) if isinstance(exc, Incomplete) else "storage_probe_incomplete")
        # A failed size probe cannot erase a separately known low-space signal.
        resources: dict[str, dict] = {}
        device_resources: dict[int, str] = {}
        app_path = Path(os.environ.get("GRAF_APP_DIR", "/opt/projects/2brain-rec"))
        analytics_path = Path(os.environ.get("GRAF_POSTHOG_ANALYTICS_PATH", str(app_path)))
        for role, path in [("analytics", p) for p in measured_paths + [analytics_path]] + [("host", app_path)]:
            try:
                device = path.stat().st_dev
                if device not in device_resources:
                    fs = filesystem(path)
                    resources[fs["identity"]] = {**fs, "roles": []}
                    device_resources[device] = fs["identity"]
                resource = resources[device_resources[device]]
                if role not in resource["roles"]:
                    resource["roles"].append(role)
            except (Incomplete, OSError):
                sample["result"] = "incomplete"
                sample["reasons"].append("filesystem_unverified")
        sample["filesystems"] = list(resources.values())
        sample["recorded_at_epoch"] = int(time.time())
        sample["recorded_at"] = datetime.fromtimestamp(sample["recorded_at_epoch"], UTC).isoformat()
        sample["window_hours"] = args.window_hours
        anchor_path = state.parent / "storage-growth-anchor.json"
        growth = {"result": "incomplete"}
        if sample["result"] == "complete":
            try:
                anchor = json.loads(anchor_path.read_text()) if anchor_path.is_file() else {}
                growth, anchor = measured_growth(sample, anchor, sample["recorded_at_epoch"])
                if growth.get("end_epoch") == sample["recorded_at_epoch"]:
                    try:
                        growth["events_in_window"] = event_count(
                            os.environ.get("GRAF_POSTHOG_PROJECT", "graf-posthog"),
                            growth["start_epoch"], growth["end_epoch"])
                    except Incomplete:
                        growth["events_in_window"] = None
                    anchor["last_growth"] = growth
                atomic_json(anchor_path, anchor)
            except (OSError, ValueError, KeyError, TypeError):
                growth = {"result": "incomplete", "reason": "growth_state_unverified"}
        sample["growth"] = growth
        atomic_json(state.with_suffix(".json"), sample)
        free_percent = min((100 * fs["available_bytes"] / fs["total_bytes"]
                            for fs in resources.values() if "analytics" in fs["roles"]), default="unknown")
        lines = ["storage_sample_version=2", f"recorded_at_epoch={sample['recorded_at_epoch']}",
                 f"storage_result={sample['result']}", f"inventory_version={sample.get('inventory_version', 'unknown')}",
                 f"analytics_storage_bytes={sample.get('analytics_storage_bytes', 'unknown')}",
                 f"storage_growth_result={growth['result']}", "content_policy=metadata_only_allocated_blocks"]
        for category, size in sample.get("classes", {}).items():
            rate = growth.get("bytes_per_day", {}).get(category, "unknown")
            count = growth.get("events_in_window")
            measured = growth["result"] == "measured"
            per_thousand = ((rate * growth["interval_seconds"] / 86400) * 1000 / count
                            if measured and type(count) is int and count > 0 else "unknown")
            twelve = size + rate * 365 if measured else "unknown"
            thirty_six = size + rate * 1095 if measured else "unknown"
            ninety = size + rate * 90 if measured else "unknown"
            hours = growth.get("interval_seconds", 0) / 3600 if "interval_seconds" in growth else "unknown"
            present = sample["class_status"][category] == "present"
            lines.append(f"storage_class={category} absolute_bytes={size if present else 'not_present'} "
                         f"presence={sample['class_status'][category]} bytes_per_day={rate} "
                         f"window_hours={hours} events_in_window={count if count is not None else 'unknown'} "
                         f"bytes_per_1000_events={per_thousand} projected_bytes_12_months={twelve} "
                         f"projected_bytes_36_months={thirty_six} projected_bytes_90_days={ninety} "
                         f"recorded_at={sample['recorded_at']} analytics_disk_free_percent={free_percent} "
                         f"growth_basis={'previous_sample' if measured else growth['result']}")
        for fs in resources.values():
            lines.append(f"filesystem={fs['identity']} roles={','.join(sorted(fs['roles']))} "
                         f"filesystem_total_bytes={fs['total_bytes']} filesystem_free_bytes={fs['available_bytes']}")
        for reason in sample["reasons"]:
            lines.append(f"reason={reason}")
        descriptor, name = tempfile.mkstemp(prefix=state.name + ".", dir=state.parent)
        try:
            with os.fdopen(descriptor, "w") as stream:
                stream.write("\n".join(lines) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(name, 0o640)
            os.replace(name, state)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        print("\n".join(lines))
        return 0 if sample["result"] == "complete" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OSError:
        print("storage_result=incomplete\nreason=storage_state_unavailable")
        raise SystemExit(1)
