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
GITHUB_COMMAND_TIMEOUT_SECONDS = 30


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


def _github_ids(
    root: Path,
    *,
    exclude_issue: int | None = None,
    strict: bool = False,
    candidates: Iterable[int] | None = None,
) -> set[int]:
    """Read feature markers, using bounded exact searches when possible.

    The repository has thousands of historical issues, so a full pagination
    scan is intentionally retained only for offline suggestions/tests. Claims
    and allocation pass the one candidate they are about to reserve; those
    checks stay fast and avoid an unbounded GitHub API walk.
    """
    result: set[int] = set()
    try:
        remote = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=root, check=True, capture_output=True, text=True,
        ).stdout.strip()
        match = re.search(r"github\.com[:/]([^/ :]+/[^/ .]+?)(?:\.git)?$", remote)
        if not match:
            raise ValueError("remote.origin.url is not a GitHub repository")
        repo = match.group(1)
        if candidates is None:
            endpoint = f"repos/{repo}/issues?state=all&per_page=100"
            proc = subprocess.run(
                ["gh", "api", "--paginate", "--slurp", endpoint],
                cwd=root, check=True, capture_output=True, text=True,
                timeout=GITHUB_COMMAND_TIMEOUT_SECONDS,
            )
            pages = json.loads(proc.stdout or "[]")
        else:
            pages = []
            for candidate in sorted({int(value) for value in candidates if int(value) > 0}):
                marker = f"{candidate:03d}"
                for query in (
                    f'repo:{repo} in:title "[{marker}]"',
                    f'repo:{repo} label:"feature:{marker}"',
                    f'repo:{repo} in:body "Feature ID: F{marker}"',
                ):
                    proc = subprocess.run(
                        ["gh", "api", "-X", "GET", "search/issues", "-f", f"q={query}", "-f", "per_page=100"],
                        cwd=root, check=True, capture_output=True, text=True,
                        timeout=GITHUB_COMMAND_TIMEOUT_SECONDS,
                    )
                    pages.append(json.loads(proc.stdout or "{}"))
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError, ValueError) as exc:
        if strict:
            raise SystemExit(
                f"feature-claim: cannot inspect complete GitHub issue/PR history: {exc}; "
                "use --offline only for an explicitly offline draft"
            ) from exc
        return result
    rows = [row for page in pages if isinstance(page, list) for row in page]
    if candidates is not None:
        rows.extend(row for page in pages if isinstance(page, dict) for row in page.get("items", []) if isinstance(row, dict))
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
            ["gh", "issue", "view", str(issue_number), "--json", "number,title,body,state,labels"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=GITHUB_COMMAND_TIMEOUT_SECONDS,
        )
        row = json.loads(proc.stdout or "{}")
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise SystemExit(f"feature-claim: cannot validate GitHub umbrella issue #{issue_number}: {exc}") from exc
    if not isinstance(row, dict) or row.get("number") != issue_number:
        raise SystemExit(f"feature-claim: GitHub umbrella issue #{issue_number} was not found")
    if row.get("state") not in (None, "OPEN"):
        raise SystemExit(f"feature-claim: umbrella issue #{issue_number} is not open")
    labels = row.get("labels", [])
    label_names = {
        str(label.get("name", ""))
        for label in labels
        if isinstance(label, dict)
    }
    if f"feature:{feature_id}" not in label_names:
        raise SystemExit(
            f"feature-claim: umbrella issue #{issue_number} must have label feature:{feature_id}"
        )
    marker = str(feature_id)
    text = f"{row.get('title', '')}\n{row.get('body', '')}"
    linked = (
        re.search(rf"^\[{re.escape(marker)}\]", str(row.get("title", "")), re.MULTILINE)
        or re.search(rf"feature:(?:F)?{re.escape(marker)}\b", text, re.IGNORECASE)
        or re.search(rf"(?:Feature ID|feature_id)\s*:\s*`?F?{re.escape(marker)}\b", text, re.IGNORECASE)
    )
    if not linked:
        raise SystemExit(f"feature-claim: umbrella issue #{issue_number} is not linked to Feature {marker}")


def _create_github_umbrella(root: Path, feature_id: int, slug: str) -> int:
    """Create the one canonical reservation issue while the shared claim lock is held."""
    title = f"[{feature_id:03d}][P1][governance] T000: Реализовать фичу {slug}"
    body = f"""## Кратко

Зарезервировать Feature {feature_id:03d} и вести его работу через Spec Kit и GitHub.

## Контекст

- Фича: `{feature_id:03d}-{slug}`
- Приоритет: `P1`
- Область: `governance`
- Источник: автоматический feature bootstrap
- Гейт: blocks PR

## Проблема

Номер должен быть занят до создания branch/spec и не может повторно использоваться.

## Проверенные факты

- Номер проверен против локальных specs, Git refs, claims и GitHub history.
- Этот issue является umbrella reservation и source of truth для Feature {feature_id:03d}.

## Границы задачи

Входит:
- Реализация задачи в отдельной feature ветке и Spec Kit directory.

Не входит:
- Несвязанные изменения и массовое удаление legacy.

## Критерии приемки

- [ ] Feature ID присутствует в spec, branch, tasks, child issues и PR.
- [ ] Перед закрытием есть validation evidence и reviewer approval.

## Что проверить перед закрытием

- [ ] Spec Kit tasks и GitHub issue links.
- [ ] Exact SHA и выбранный validation lane.

## Заметки по реализации

Детальные требования находятся в `specs/{feature_id:03d}-{slug}/spec.md`.

## Ссылки

- Feature ID: `F{feature_id:03d}`
"""
    try:
        proc = subprocess.run(
            [
                "gh", "issue", "create", "--title", title, "--body", body,
                "--label", f"feature:{feature_id:03d},priority:P1,area:docs/governance,gate:pr-blocker,type:hardening",
            ],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=GITHUB_COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", "") or ""
        raise SystemExit(f"feature-claim: cannot create GitHub umbrella issue: {detail.strip() or exc}") from exc
    match = re.search(r"/(\d+)\s*$", proc.stdout.strip())
    if not match:
        raise SystemExit("feature-claim: gh did not return an issue URL")
    issue_number = int(match.group(1))
    _github_umbrella(root, issue_number, feature_id)
    return issue_number


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


def _write_active_pointer(
    root: Path,
    *,
    feature_id: int,
    branch: str,
    slug: str,
    owner: str,
    risk_lane: str,
    source_sha: str | None,
) -> None:
    """Persist the complete per-worktree context immediately after claiming."""
    if not source_sha or not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise SystemExit("feature-claim: cannot persist active pointer without the current HEAD SHA")
    pointer = root / ".specify" / "feature.json"
    pointer.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "feature_directory": f"specs/{feature_id:03d}-{slug}",
        "feature_id": f"{feature_id:03d}",
        "owner": owner,
        "risk_lane": risk_lane,
        "owned_paths": [f"specs/{feature_id:03d}-{slug}", ".specify"],
        "branch": branch,
        "source_sha": source_sha,
    }
    temporary = pointer.with_name(f".{pointer.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, pointer)
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


def _canonical_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _assert_clean_worktree(root: Path, allowed_paths: Iterable[str] = (".specify/feature.json",)) -> None:
    """Require a clean worktree, except for claim metadata we own.

    Claiming a feature atomically refreshes ``.specify/feature.json``.  Keep
    that exception in the default contract so callers (and test doubles) can
    use the one-argument form without accidentally weakening the dirty-tree
    gate for any other path.
    """
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=root, check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"feature-claim: cannot inspect worktree cleanliness: {exc}") from exc
    allowed = {str(Path(path)) for path in allowed_paths}
    dirty = [line for line in status.splitlines() if line[3:].strip().split(" -> ", 1)[-1] not in allowed]
    if dirty:
        raise SystemExit("feature-claim: worktree must be clean before claiming a feature")


def claim(root: Path, feature_id: int, *, issue_number: int | None, branch: str, slug: str, offline: bool,
          owner: str = "codex", risk_lane: str = "significant-feature") -> dict[str, object]:
    if feature_id <= 0:
        raise SystemExit("feature-claim: feature_id must be greater than zero")
    if not branch or not slug:
        raise SystemExit("feature-claim: branch and slug are required")
    if not owner.strip() or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._ -]{0,159}", owner):
        raise SystemExit("feature-claim: owner must be a bounded non-empty identity")
    if risk_lane not in {"tiny-low-risk", "active-spec-kit", "significant-feature", "high-risk-product", "release-deploy"}:
        raise SystemExit("feature-claim: risk_lane is invalid")
    branch_match = re.search(r"(?:^|/)(\d{3,})-([A-Za-z0-9][A-Za-z0-9-]*)$", branch)
    if not branch_match or int(branch_match.group(1)) != feature_id:
        raise SystemExit(f"feature-claim: branch must be bound to Feature {feature_id:03d}")
    if _canonical_slug(branch_match.group(2)) != _canonical_slug(slug):
        raise SystemExit("feature-claim: branch suffix must match the requested slug")
    _assert_clean_worktree(root)
    if not offline:
        if issue_number is None:
            raise SystemExit(
                "feature-claim: GitHub umbrella issue is required; use --offline only for draft mode"
            )
        # Validate the umbrella before collision checks so every online claim
        # is anchored to the same open, feature-labelled GitHub reservation.
        _github_umbrella(root, issue_number, feature_id)
    refs = _git_refs(root, strict=not offline)
    local_claims = _local_claim_records(root)
    requested_claim = {"issue_number": issue_number, "branch": branch, "slug": slug}
    existing_claim = local_claims.get(f"{feature_id:03d}")
    # A retry of the exact same claim is safe and must be idempotent.  A
    # different issue, branch or slug remains a collision and is rejected
    # before any shared state is written.
    same_local_claim = existing_claim == requested_claim
    draft_upgrade = (
        isinstance(existing_claim, dict)
        and existing_claim.get("issue_number") is None
        and issue_number is not None
        and existing_claim.get("branch") == branch
        and existing_claim.get("slug") == slug
    )
    occupied = _ids_from_specs(root) | _ids_from_refs(refs) | set(int(key) for key in local_claims)
    if not offline:
        occupied |= _github_ids(root, exclude_issue=issue_number, strict=True, candidates={feature_id})
    if feature_id in occupied and not (same_local_claim or draft_upgrade):
        conflicts = sorted(
            [f"spec/branch ref containing {feature_id:03d}"],
        )
        raise SystemExit(
            f"feature-claim: collision for {feature_id:03d}; inspect specs and refs ({', '.join(conflicts)})"
        )
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
            current = claims[key]
            if not (
                draft_upgrade
                and isinstance(current, dict)
                and current.get("issue_number") is None
                and current.get("branch") == branch
                and current.get("slug") == slug
            ):
                raise SystemExit(f"feature-claim: local claim already exists with different metadata for {key}")
        claims[key] = requested_claim
        _write_claims_atomic(claims_path, claims)
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    result = {
        "schema_version": 1,
        "feature_id": f"{feature_id:03d}",
        "issue_number": issue_number,
        "branch": branch,
        "slug": slug,
        "source_sha": _git_sha(root),
        "status": "draft" if offline else "reserved",
    }
    _write_active_pointer(
        root, feature_id=feature_id, branch=branch, slug=slug, owner=owner,
        risk_lane=risk_lane, source_sha=result["source_sha"],
    )
    return result


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
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Feature Claim Test"], cwd=root, check=True)
        subprocess.run(["git", "add", "specs"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
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
        # The pointer is intentionally an uncommitted per-worktree artifact;
        # this self-test exercises shared claim idempotency independently.
        (root / ".specify" / "feature.json").unlink()
        assert _local_claim_ids(root) == {216}
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
        (root / ".specify" / "feature.json").unlink()
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
    parser.add_argument("--owner", default=os.environ.get("GRAF_FEATURE_OWNER", "codex"))
    parser.add_argument("--risk-lane", default="significant-feature")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--allocate", action="store_true", help="atomically allocate a fresh ID and create its umbrella issue")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    root = args.root.resolve()
    if args.allocate:
        if not args.branch or not args.slug:
            raise SystemExit("feature-claim: --allocate requires --branch and --slug")
        if args.offline:
            raise SystemExit("feature-claim: --allocate cannot use --offline; use an explicit draft claim instead")
        _assert_clean_worktree(root)
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
            branch_match = re.search(r"(?:^|/)(\d{3,})-([A-Za-z0-9][A-Za-z0-9-]*)$", args.branch)
            if not branch_match:
                raise SystemExit("feature-claim: branch must end in <feature-id>-<slug>")
            requested_feature_id = int(branch_match.group(1))
            if args.issue_number is not None:
                _github_umbrella(root, args.issue_number, requested_feature_id)
            _validate_claims(claims, claims_path)
            refs = _git_refs(root, strict=True)
            # The caller creates the requested branch before invoking
            # ``--allocate``; that branch is the claim being made, not a
            # competing reservation.  Exclude its local and origin refs.
            refs = [
                ref for ref in refs
                if ref != args.branch and not ref.endswith(f"/{args.branch}")
            ]
            occupied = _ids_from_specs(root) | _ids_from_refs(refs) | set(int(key) for key in claims)
            # Probe only the next candidate.  GitHub issue history is large;
            # exact marker searches preserve freshness without a slow full scan.
            occupied |= _github_ids(
                root,
                exclude_issue=args.issue_number,
                strict=True,
                candidates={max(1, max(occupied, default=0) + 1)},
            )
            feature_id = _available_id(occupied, max(1, max(occupied, default=0) + 1))
            while _github_ids(root, strict=True, candidates={feature_id}):
                feature_id += 1
            if requested_feature_id != feature_id:
                raise SystemExit(
                    f"feature-claim: generated branch {args.branch!r} is not the next collision-free Feature {feature_id:03d}; retry bootstrap"
                )
            if _canonical_slug(branch_match.group(2)) != _canonical_slug(args.slug):
                raise SystemExit("feature-claim: branch suffix must match the requested slug")
            issue_number = args.issue_number or _create_github_umbrella(root, feature_id, args.slug)
            requested = {"issue_number": issue_number, "branch": args.branch, "slug": args.slug}
            claims[f"{feature_id:03d}"] = requested
            _write_claims_atomic(claims_path, claims)
            result = {
                "schema_version": 1, "feature_id": f"{feature_id:03d}",
                "issue_number": issue_number, "branch": args.branch, "slug": args.slug,
                "source_sha": _git_sha(root), "status": "reserved",
            }
            _write_active_pointer(
                root, feature_id=feature_id, branch=args.branch, slug=args.slug,
                owner=args.owner, risk_lane=args.risk_lane, source_sha=result["source_sha"],
            )
        output = json.dumps(result, ensure_ascii=False, sort_keys=True)
        print(output if args.json else f"feature-claim: {output}")
        return 0
    if args.feature_id is None:
        occupied = _ids_from_specs(root) | _ids_from_refs(_git_refs(root)) | _local_claim_ids(root)
        if not args.offline:
            # A suggested number is useful only when it includes the same
            # remote collision sources as an actual claim. Offline mode is
            # explicitly a draft and must be labelled as such.
            # Suggestions are advisory; keep them bounded to the next local
            # candidate instead of scanning the complete historical backlog.
            suggestion = _available_id(occupied, max(1, max(occupied, default=0) + 1))
            if _github_ids(root, candidates={suggestion}):
                suggestion += 1
            print(json.dumps({"next_available": f"{suggestion:03d}", "occupied_count": len(occupied), "mode": "github-checked"}))
            return 0
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
