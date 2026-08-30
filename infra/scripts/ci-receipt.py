#!/usr/bin/env python3
"""Create and validate local full-CI evidence for one exact Git worktree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

VERSION = 2
DEFAULT_MAX_AGE_SECONDS = 86_400
RUNNER_INPUTS = (
    "infra/scripts/ci-local.sh",
    "infra/scripts/ci-receipt.py",
    "apps/server/scripts/run_local_postgres_tests.sh",
)
DEPENDENCY_INPUTS = (
    "apps/server/uv.lock",
    "apps/macos/Package.resolved",
)
TEST_SURFACES = ("apps/server/tests", "apps/macos/Tests")
HEX_64 = re.compile(r"[0-9a-f]{64}\Z")
COMMON_FULL_STAGES = (
    "macOS legacy audio architecture guard",
    "server tests",
    "server lint",
    "python compile",
    "rls hardening validation boundary",
    "production compose config",
    "deployment evidence scan",
    "active CI documentation consistency",
)
DARWIN_FULL_STAGES = (
    "macOS Swift build",
    "macOS Swift tests",
    "macOS contract validation",
)


class ReceiptError(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def command(*args: str, cwd: Path | None = None, check: bool = True) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if check and result.returncode != 0:
        raise ReceiptError("snapshot_failed")
    return result.stdout.strip()


def repo_root() -> Path:
    return Path(command("git", "rev-parse", "--show-toplevel")).resolve()


def receipt_path(root: Path) -> Path:
    raw = Path(command("git", "rev-parse", "--git-path", "graf-ci/full-receipt.json", cwd=root))
    return raw if raw.is_absolute() else (root / raw).resolve()


def require_clean(root: Path) -> None:
    if command("git", "status", "--porcelain", "--untracked-files=all", cwd=root):
        raise ReceiptError("dirty_worktree")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hashed_inputs(root: Path, paths: tuple[str, ...]) -> dict[str, str]:
    result: dict[str, str] = {}
    for relative in paths:
        path = root / relative
        if not path.is_file():
            raise ReceiptError("snapshot_failed")
        result[relative] = sha256_file(path)
    return result


def test_surface_digest(root: Path) -> str:
    listed = command("git", "ls-files", "--", *TEST_SURFACES, cwd=root)
    digest = hashlib.sha256()
    for relative in sorted(filter(None, listed.splitlines())):
        path = root / relative
        if not path.is_file():
            raise ReceiptError("snapshot_failed")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def version_output(*args: str) -> str:
    try:
        output = command(*args, check=False)
    except OSError:
        return "unavailable"
    return " ".join(output.split()) or "unavailable"


def toolchain() -> dict[str, str]:
    return {
        "platform": " ".join(platform.platform().split()),
        "python3": version_output("python3", "--version"),
        "git": version_output("git", "--version"),
        "uv": version_output("uv", "--version"),
        "docker": version_output("docker", "--version"),
        "swift": version_output("swift", "--version"),
    }


def snapshot(root: Path) -> dict[str, object]:
    return {
        "commit_sha": command("git", "rev-parse", "HEAD", cwd=root),
        "tree_sha": command("git", "rev-parse", "HEAD^{tree}", cwd=root),
        "runner_inputs": hashed_inputs(root, RUNNER_INPUTS),
        "dependency_inputs": hashed_inputs(root, DEPENDENCY_INPUTS),
        "test_surface_digest": test_surface_digest(root),
        "toolchain": toolchain(),
    }


def required_full_stages() -> tuple[str, ...]:
    return COMMON_FULL_STAGES[:1] + (DARWIN_FULL_STAGES if platform.system() == "Darwin" else ()) + COMMON_FULL_STAGES[1:]


def stage_evidence(path: Path, started_at: int, now: int) -> tuple[str, ...]:
    if path.is_symlink() or not path.is_file():
        raise ReceiptError("evidence_invalid")
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or metadata.st_mode & 0o777 != 0o600:
        raise ReceiptError("evidence_invalid")
    if int(metadata.st_mtime) < started_at or int(metadata.st_mtime) > now:
        raise ReceiptError("evidence_invalid")
    try:
        rows = tuple(line.split("\t") for line in path.read_text(encoding="utf-8").splitlines())
    except (OSError, UnicodeError):
        raise ReceiptError("evidence_invalid") from None
    if any(len(row) != 2 or row[1] != "pass" for row in rows):
        raise ReceiptError("evidence_invalid")
    stages = tuple(row[0] for row in rows)
    if stages != required_full_stages():
        raise ReceiptError("evidence_invalid")
    return stages


def invalid(reason: str) -> int:
    print(f"ci_receipt_result=invalid reason={reason}")
    return 1


def create(args: argparse.Namespace) -> int:
    if args.started_at_epoch < 0 or args.collection_count < 1 or not HEX_64.fullmatch(args.collection_digest):
        raise ReceiptError("collection_invalid")
    root = repo_root()
    require_clean(root)
    now = int(time.time())
    completed_stages = stage_evidence(Path(args.evidence_file).resolve(), args.started_at_epoch, now)
    receipt = {
        "version": VERSION,
        "result": "pass",
        "created_at_epoch": now,
        "started_at_epoch": args.started_at_epoch,
        "duration_seconds": max(0, now - args.started_at_epoch),
        **snapshot(root),
        "server_collection_count": args.collection_count,
        "server_collection_digest": args.collection_digest,
        "completed_stages": completed_stages,
    }
    destination = receipt_path(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=destination.parent, prefix="full-receipt.", delete=False
    ) as temporary:
        json.dump(receipt, temporary, sort_keys=True, separators=(",", ":"))
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    os.chmod(temporary_path, 0o600)
    temporary_path.replace(destination)
    print(f"ci_receipt_result=created commit_sha={receipt['commit_sha']}")
    return 0


def validate(args: argparse.Namespace) -> int:
    root = repo_root()
    destination = receipt_path(root)
    if not destination.is_file():
        return invalid("missing")
    try:
        receipt = json.loads(destination.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return invalid("malformed")
    if not isinstance(receipt, dict):
        return invalid("malformed")
    if receipt.get("version") != VERSION:
        return invalid("unsupported_version")
    if receipt.get("result") != "pass":
        return invalid("not_pass")
    if receipt.get("completed_stages") != list(required_full_stages()):
        return invalid("evidence_invalid")
    count = receipt.get("server_collection_count")
    digest = receipt.get("server_collection_digest")
    if not isinstance(count, int) or count < 1 or not isinstance(digest, str) or not HEX_64.fullmatch(digest):
        return invalid("collection_invalid")
    created = receipt.get("created_at_epoch")
    started = receipt.get("started_at_epoch")
    duration = receipt.get("duration_seconds")
    now = int(time.time())
    if (
        not isinstance(created, int)
        or not isinstance(started, int)
        or not isinstance(duration, int)
        or started < 0
        or started > created
        or duration != created - started
        or created > now
    ):
        return invalid("malformed")
    if now - created > args.max_age_seconds:
        return invalid("stale")
    try:
        require_clean(root)
        current = snapshot(root)
    except ReceiptError as error:
        return invalid(error.reason)
    comparisons = (
        ("commit_sha", "commit_mismatch"),
        ("tree_sha", "tree_mismatch"),
        ("runner_inputs", "runner_mismatch"),
        ("dependency_inputs", "dependency_mismatch"),
        ("test_surface_digest", "test_surface_mismatch"),
        ("toolchain", "toolchain_mismatch"),
    )
    for field, reason in comparisons:
        if receipt.get(field) != current[field]:
            return invalid(reason)
    print(f"ci_receipt_result=valid commit_sha={receipt['commit_sha']}")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="command", required=True)
    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("--started-at-epoch", type=int, required=True)
    create_parser.add_argument("--collection-count", type=int, required=True)
    create_parser.add_argument("--collection-digest", required=True)
    create_parser.add_argument("--evidence-file", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument(
        "--max-age-seconds",
        type=int,
        default=int(os.environ.get("GRAF_FULL_CI_RECEIPT_MAX_AGE_SECONDS", DEFAULT_MAX_AGE_SECONDS)),
    )
    subparsers.add_parser("path")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "create":
            return create(args)
        if args.command == "validate":
            if args.max_age_seconds < 0:
                raise ReceiptError("malformed")
            return validate(args)
        print(receipt_path(repo_root()))
        return 0
    except ReceiptError as error:
        return invalid(error.reason)


if __name__ == "__main__":
    sys.exit(main())
