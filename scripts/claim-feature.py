#!/usr/bin/env python3
"""Deterministic Feature ID preflight for the GRAF/Spec Kit workflow.

The script does not pretend to reserve a number without a GitHub umbrella issue.
It validates a caller-supplied claim against local specs and Git refs and emits a
small metadata-only manifest. The GitHub issue remains the authoritative atomic
reservation record.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable


ID_RE = re.compile(r"(?:^|/)(\d{3,})-")


def _ids_from_specs(root: Path) -> set[int]:
    specs = root / "specs"
    if not specs.is_dir():
        return set()
    result: set[int] = set()
    for path in specs.iterdir():
        if path.is_dir():
            match = re.match(r"^(\d{3,})(?:-|$)", path.name)
            if match:
                result.add(int(match.group(1)))
    return result


def _git_refs(root: Path, *, strict: bool = False) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "for-each-ref", "--format=%(refname:short)"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        if strict:
            raise SystemExit(f"feature-claim: cannot inspect git refs: {exc}") from exc
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _ids_from_refs(refs: Iterable[str]) -> set[int]:
    result: set[int] = set()
    for ref in refs:
        for match in ID_RE.finditer(ref):
            result.add(int(match.group(1)))
    return result


def _github_ids(root: Path, *, exclude_issue: int | None = None, strict: bool = False) -> set[int]:
    """Read every visible issue/PR marker through the paginated GitHub API."""
    result: set[int] = set()
    try:
        remote = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=root, check=True, capture_output=True, text=True,
        ).stdout.strip()
        match = re.search(r"github\.com[:/]([^/ :]+/[^/ .]+?)(?:\.git)?$", remote)
        if not match:
            raise ValueError("remote.origin.url is not a GitHub repository")
        endpoint = f"repos/{match.group(1)}/issues?state=all&per_page=100"
        proc = subprocess.run(
            ["gh", "api", "--paginate", "--slurp", endpoint],
            cwd=root, check=True, capture_output=True, text=True,
        )
        pages = json.loads(proc.stdout or "[]")
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as exc:
        if strict:
            raise SystemExit(
                f"feature-claim: cannot inspect complete GitHub issue/PR history: {exc}; "
                "use --offline only for an explicitly offline draft"
            ) from exc
        return result
    rows = [row for page in pages if isinstance(page, list) for row in page]
    for row in rows:
        if exclude_issue is not None and row.get("number") == exclude_issue:
            continue
        labels = row.get("labels", []) if isinstance(row, dict) else []
        label_text = " ".join(str(item.get("name", "")) for item in labels if isinstance(item, dict))
        title = str(row.get("title", ""))
        body = str(row.get("body", ""))
        # Only consume explicit feature markers. Generic numbers in issue
        # bodies include timestamps, hashes and external IDs.
        result |= {int(value) for value in re.findall(r"^\[(\d{3,})\]", title)}
        result |= {int(value) for value in re.findall(r"feature:(\d{3,})\b", label_text, flags=re.IGNORECASE)}
        result |= {int(value) for value in re.findall(r"(?:Feature ID|feature_id)\s*:\s*`?F?(\d{3,})\b", body, flags=re.IGNORECASE)}
    return result


def _local_claim_ids(root: Path) -> set[int]:
    return {int(key) for key in _local_claim_records(root)}


def _local_claim_records(root: Path) -> dict[str, dict[str, object]]:
    claims_path = None
    try:
        git_dir = _git_common_dir(root)
        if not git_dir.is_absolute():
            git_dir = root / git_dir
        claims_path = git_dir / "feature-claims.json"
        if not claims_path.exists():
            return {}
        data = json.loads(claims_path.read_text(encoding="utf-8"))
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"feature-claim: cannot inspect shared claim state: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"feature-claim: shared claim state is corrupt: {claims_path}") from exc
    _validate_claims(data, claims_path)
    return data


def _validate_claims(data: object, claims_path: Path) -> None:
    if not isinstance(data, dict):
        raise SystemExit(f"feature-claim: shared claim state is corrupt: {claims_path}")
    for key, value in data.items():
        if (
            not re.fullmatch(r"\d{3,}", str(key))
            or not isinstance(value, dict)
            or set(value) != {"issue_number", "branch", "slug"}
            or not isinstance(value["branch"], str)
            or not value["branch"].strip()
            or not isinstance(value["slug"], str)
            or not value["slug"].strip()
        ):
            raise SystemExit(f"feature-claim: shared claim state is corrupt: {claims_path}")


def _github_umbrella(root: Path, issue_number: int, feature_id: int) -> None:
    """Require the supplied open issue to explicitly identify this feature."""
    try:
        proc = subprocess.run(
            ["gh", "issue", "view", str(issue_number), "--json", "number,title,body,state"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        row = json.loads(proc.stdout or "{}")
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise SystemExit(f"feature-claim: cannot validate GitHub umbrella issue #{issue_number}: {exc}") from exc
    if not isinstance(row, dict) or row.get("number") != issue_number:
        raise SystemExit(f"feature-claim: GitHub umbrella issue #{issue_number} was not found")
    if row.get("state") not in (None, "OPEN"):
        raise SystemExit(f"feature-claim: umbrella issue #{issue_number} is not open")
    marker = str(feature_id)
    text = f"{row.get('title', '')}\n{row.get('body', '')}"
    linked = (
        re.search(rf"^\[{re.escape(marker)}\]", str(row.get("title", "")), re.MULTILINE)
        or re.search(rf"feature:(?:F)?{re.escape(marker)}\b", text, re.IGNORECASE)
        or re.search(rf"(?:Feature ID|feature_id)\s*:\s*`?F?{re.escape(marker)}\b", text, re.IGNORECASE)
    )
    if not linked:
        raise SystemExit(f"feature-claim: umbrella issue #{issue_number} is not linked to Feature {marker}")


def _write_claims_atomic(path: Path, claims: dict[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _parse_ids(values: Iterable[str]) -> set[int]:
    result: set[int] = set()
    for value in values:
        for match in ID_RE.finditer(value):
            result.add(int(match.group(1)))
    return result


def _git_common_dir(root: Path) -> Path:
    """Resolve the shared Git metadata directory used by every worktree."""
    output = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return Path(output)


def _available_id(occupied: set[int], start: int) -> int:
    candidate = max(1, start)
    while candidate in occupied:
        candidate += 1
    return candidate


def claim(root: Path, feature_id: int, *, issue_number: int | None, branch: str, slug: str, offline: bool) -> dict[str, object]:
    refs = _git_refs(root, strict=not offline)
    local_claims = _local_claim_records(root)
    requested_claim = {"issue_number": issue_number, "branch": branch, "slug": slug}
    existing_claim = local_claims.get(f"{feature_id:03d}")
    # A retry of the exact same claim is safe and must be idempotent.  A
    # different issue, branch or slug remains a collision and is rejected
    # before any shared state is written.
    same_local_claim = existing_claim == requested_claim
    occupied = _ids_from_specs(root) | _ids_from_refs(refs) | set(int(key) for key in local_claims)
    if not offline:
        occupied |= _github_ids(root, exclude_issue=issue_number, strict=True)
    if feature_id in occupied and not same_local_claim:
        conflicts = sorted(
            [f"spec/branch ref containing {feature_id:03d}"],
        )
        raise SystemExit(
            f"feature-claim: collision for {feature_id:03d}; inspect specs and refs ({', '.join(conflicts)})"
        )
    if not offline and issue_number is None:
        raise SystemExit("feature-claim: GitHub umbrella issue is required; use --offline only for draft mode")
    if not branch or not slug:
        raise SystemExit("feature-claim: branch and slug are required")
    branch_match = re.search(r"(?:^|/)(\d{3,})-", branch)
    if not branch_match or int(branch_match.group(1)) != feature_id:
        raise SystemExit(f"feature-claim: branch must be bound to Feature {feature_id:03d}")
    if not offline:
        _github_umbrella(root, issue_number, feature_id)
    # Worktrees share this directory; the lock serializes claims across all of
    # them instead of creating one reservation file per worktree.
    git_dir = _git_common_dir(root)
    if not git_dir.is_absolute():
        git_dir = root / git_dir
    lock_path = git_dir / "feature-claim.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        claims_path = lock_path.with_name("feature-claims.json")
        try:
            claims = json.loads(claims_path.read_text(encoding="utf-8")) if claims_path.exists() else {}
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"feature-claim: shared claim state is corrupt: {claims_path}") from exc
        _validate_claims(claims, claims_path)
        key = f"{feature_id:03d}"
        if key in claims and claims[key] != requested_claim:
            raise SystemExit(f"feature-claim: local claim already exists with different metadata for {key}")
        claims[key] = requested_claim
        _write_claims_atomic(claims_path, claims)
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return {
        "schema_version": 1,
        "feature_id": f"{feature_id:03d}",
        "issue_number": issue_number,
        "branch": branch,
        "slug": slug,
        "source_sha": _git_sha(root),
        "status": "draft" if offline else "reserved",
    }


def _git_sha(root: Path) -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="graf-feature-claim-") as tmp:
        root = Path(tmp)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        (root / "specs" / "001-old").mkdir(parents=True)
        (root / "specs" / "001-old" / "spec.md").write_text("# old\n", encoding="utf-8")
        occupied = _ids_from_specs(root) | _ids_from_refs(["origin/codex/215-summary-auto-recovery", "origin/codex/1024-large-feature"])
        assert occupied == {1, 215, 1024}
        assert _available_id(occupied, 1) == 2
        assert _available_id(occupied, 215) == 216
        try:
            claim(root, 1, issue_number=None, branch="codex/001-x", slug="x", offline=True)
        except SystemExit as exc:
            assert "collision" in str(exc)
        else:
            raise AssertionError("occupied ID was accepted")
        draft = claim(root, 216, issue_number=None, branch="draft/216-x", slug="x", offline=True)
        assert draft["status"] == "draft"
        assert _local_claim_ids(root) == {216}
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Feature Claim Test"], cwd=root, check=True)
        subprocess.run(["git", "add", "specs"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
        linked = root.parent / "linked-worktree"
        subprocess.run(["git", "worktree", "add", "-q", str(linked), "HEAD"], cwd=root, check=True)
        try:
            claim(linked, 216, issue_number=None, branch="draft/216-y", slug="y", offline=True)
        except SystemExit as exc:
            assert "collision" in str(exc)
        else:
            raise AssertionError("linked worktree reused an existing claim")
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(linked)], cwd=root, check=True)
        retry = claim(root, 216, issue_number=None, branch="draft/216-x", slug="x", offline=True)
        assert retry["status"] == "draft"
        try:
            claim(root, 216, issue_number=None, branch="draft/216-other", slug="other", offline=True)
        except SystemExit as exc:
            assert "collision" in str(exc)
        else:
            raise AssertionError("conflicting claim metadata was accepted")
    print("feature-claim self-test: OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--feature-id", type=int)
    parser.add_argument("--issue-number", type=int)
    parser.add_argument("--branch", default="")
    parser.add_argument("--slug", default="")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    root = args.root.resolve()
    if args.feature_id is None:
        occupied = _ids_from_specs(root) | _ids_from_refs(_git_refs(root)) | _local_claim_ids(root)
        if not args.offline:
            # A suggested number is useful only when it includes the same
            # remote collision sources as an actual claim. Offline mode is
            # explicitly a draft and must be labelled as such.
            occupied |= _github_ids(root)
        next_id = _available_id(occupied, max(1, max(occupied, default=0) + 1))
        print(json.dumps({"next_available": f"{next_id:03d}", "occupied_count": len(occupied), "mode": "offline-draft" if args.offline else "github-checked"}))
        return 0
    try:
        result = claim(root, args.feature_id, issue_number=args.issue_number, branch=args.branch, slug=args.slug, offline=args.offline)
    except SystemExit:
        raise
    output = json.dumps(result, ensure_ascii=False, sort_keys=True)
    print(output if args.json else f"feature-claim: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
