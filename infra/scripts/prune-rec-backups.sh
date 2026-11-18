#!/usr/bin/env sh
set -eu

# Remove only GRAF-owned dated backup directories older than the configured
# age. Dry-run is the default. Production enablement is an operator action.

exec python3 - "$@" <<'PY'
from __future__ import annotations

import argparse
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

NAME_FORMAT = "%Y%m%dT%H%M%SZ"
DEFAULT_ROOT = "/opt/projects/2brain-rec/backups"


def fail(message: str, code: int = 2) -> int:
    print(f"prune_result=failed\nreason={message}", file=sys.stderr)
    return code


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prune GRAF backup directories")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Report only (default)")
    mode.add_argument("--execute", action="store_true", help="Delete eligible directories")
    parser.add_argument(
        "--older-than-days",
        type=int,
        default=30,
        help="Delete directories older than this many days (default 30)",
    )
    parser.add_argument(
        "--backup-root",
        default=os.environ.get("TWOBRAIN_BACKUP_ROOT", DEFAULT_ROOT),
        help="Backup root containing dated directories",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.older_than_days < 1:
        return fail("invalid_older_than_days")
    root = Path(args.backup_root)
    if not root.is_absolute():
        return fail("backup_root_must_be_absolute")
    if root.is_symlink():
        return fail("backup_root_symlink")
    try:
        root = root.resolve(strict=True)
    except OSError:
        return fail("backup_root_missing")
    if not root.is_dir() or root.is_symlink():
        return fail("backup_root_not_directory")

    candidates: list[Path] = []
    skipped = 0
    # A dated directory is GRAF-owned only when the backup contract is
    # present. A foreign directory with a timestamp-shaped name must never be
    # deleted.
    required_owned_files = (
        "postgres.dump",
        "schema.sql",
        "inventory.jsonl",
        "checksums.sha256",
    )
    required_owned_dir = "minio-objects"
    try:
        entries = list(root.iterdir())
    except OSError:
        return fail("backup_root_unreadable")

    parsed: list[tuple[datetime, Path, bool]] = []
    for entry in entries:
        if entry.is_symlink() or not entry.is_dir():
            skipped += 1
            continue
        try:
            stamp = datetime.strptime(entry.name, NAME_FORMAT).replace(tzinfo=timezone.utc)
        except ValueError:
            skipped += 1
            continue
        if entry.name != stamp.strftime(NAME_FORMAT):
            skipped += 1
            continue
        owned = all((entry / name).is_file() for name in required_owned_files) and (
            entry / required_owned_dir
        ).is_dir()
        parsed.append((stamp, entry, owned))

    if not parsed:
        print("prune_result=pass")
        print("candidate_count=0")
        print("deleted_count=0")
        print(f"skipped_count={skipped}")
        print("reason=no_candidates")
        return 0

    # Keep both the newest directory overall and the newest verified backup.
    # A failed newest backup must not cause the last good backup to be pruned.
    parsed.sort(key=lambda item: item[0], reverse=True)
    newest_overall = parsed[0][1]
    newest_owned = next((entry for _, entry, owned in parsed if owned), None)
    now = datetime.now(timezone.utc)
    for stamp, entry, owned in parsed:
        if not owned:
            skipped += 1
            continue
        if entry == newest_overall or entry == newest_owned:
            skipped += 1
            continue
        age_days = (now - stamp).total_seconds() / 86_400
        if age_days <= args.older_than_days:
            skipped += 1
            continue
        candidates.append(entry)

    print(f"candidate_count={len(candidates)}")
    for entry in candidates:
        # Metadata-only output: a basename is enough to identify the candidate.
        print(f"candidate={entry.name}")

    if not args.execute:
        print("prune_result=dry_run")
        print("deleted_count=0")
        print(f"skipped_count={skipped}")
        return 0

    deleted = 0
    failed = 0
    for entry in candidates:
        try:
            # Re-check immediately before deletion to close a symlink swap.
            if entry.is_symlink() or not entry.is_dir() or entry.parent != root:
                skipped += 1
                continue
            shutil.rmtree(entry)
            deleted += 1
        except OSError:
            failed += 1

    print(f"deleted_count={deleted}")
    print(f"skipped_count={skipped}")
    if failed:
        print("prune_result=partial_failure")
        print(f"failed_count={failed}")
        return 3
    print("prune_result=pass")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
PY
