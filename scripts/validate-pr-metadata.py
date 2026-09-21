#!/usr/bin/env python3
"""Validate the machine-checkable PR contract for a feature branch."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REQUIRED = (
    "## Feature identity",
    "## Как проверено",
    "## Risk / validation lane",
    "## Issues",
    "## Legacy Impact",
    "## Перед merge",
)
SECTION_RE = re.compile(r"^(## [^\n]+)[ \t]*\n([\s\S]*?)(?=^## |\Z)", re.MULTILINE)
SHA_RE = re.compile(
    r"^[ \t]*(?:[-*][ \t]*)?Exact source SHA\b[^\n:]*:[ \t]*`?([0-9a-fA-F]{40})`?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
CLASSIFICATION_RE = re.compile(
    r"^[ \t]*(?:[-*][ \t]*)?(?:\*\*)?Classification(?:\*\*)?"
    r"[ \t]*:[ \t]*[`']?(remove|retain-with-exception|untouched)[`']?"
    r"[ \t]*[.,;:!?]?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
ISSUE_LINK_RE = re.compile(
    r"\b(?:Refs|Part of|Fixes|Closes|Resolves)[ \t]+#(\d+)\b",
    re.IGNORECASE,
)
LANE_RE = re.compile(
    r"^[ \t]*(?:[-*][ \t]*)?Lane[ \t]*:[ \t]*(?!$|___|<[^>]+>)([^\n]+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
EVIDENCE_COMMAND_RE = re.compile(r"`[^`\n]+`", re.MULTILINE)
EVIDENCE_STATUS_RE = re.compile(
    r"\b(?:pass(?:ed)?|ok|fail(?:ed)?|blocked|skipped|not[ \t]+run|не[ \t]+запускал|не[ \t]+запущен)\b",
    re.IGNORECASE,
)
TITLE_PREFIX_RE = re.compile(r"^((?:\[F\d{3,}\])+)(?:\s|$)")
TITLE_FEATURE_RE = re.compile(r"\[F(\d{3,})\]")
FEATURE_ID_RE = re.compile(r"\bF(\d{3,})\b")


def _sections(body: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    for match in SECTION_RE.finditer(body):
        sections.setdefault(match.group(1), []).append(match.group(2))
    return sections


def _has_content(content: str) -> bool:
    return any(line.strip() not in {"", "-", "*", "_"} for line in content.splitlines())


def _expected_feature_ids(value: str) -> set[str]:
    return {match.group(1) for match in re.finditer(r"\bF?(\d{3,})\b", value)}


def _declared_feature_ids(body: str, sections: dict[str, list[str]]) -> set[str]:
    # Restrict the declaration to the dedicated identity section so that a
    # reference to another feature in release notes cannot change ownership.
    identity = "\n".join(
        sections.get("## Feature identity", []) + sections.get("## Feature IDs", [])
    )
    declared = set(FEATURE_ID_RE.findall(identity))
    if declared:
        return declared
    marker = re.search(r"Feature ID:\s*`?F?(\d{3,})", body)
    return {marker.group(1)} if marker else set()


def validate(
    body: str,
    feature_id: str,
    expected_sha: str | None = None,
    title: str | None = None,
    scoped: bool = False,
) -> list[str]:
    sections = _sections(body)
    errors: list[str] = []
    expected_feature_ids = _expected_feature_ids(feature_id)
    if not expected_feature_ids and not scoped:
        errors.append("expected Feature ID is required")
    title_match = TITLE_PREFIX_RE.match((title or "").strip())
    if not title_match and not scoped:
        errors.append("PR title must start with [F<feature-id>]")
    elif title_match and not scoped and not expected_feature_ids.issubset(set(TITLE_FEATURE_RE.findall(title_match.group(1)))):
        errors.append(
            f"PR title Feature ID mismatch: expected {sorted('F' + value for value in expected_feature_ids)}, got {title_match.group(1)}"
        )
    for section in REQUIRED:
        if section == "## Feature identity" and "## Feature IDs" in sections:
            continue
        if section not in sections:
            errors.append(f"missing PR section: {section}")
        elif len(sections[section]) > 1:
            errors.append(f"duplicate PR section: {section}")
        elif not _has_content(sections[section][0]):
            errors.append(f"empty PR section: {section}")
    declared_feature_ids = _declared_feature_ids(body, sections)
    identity = "\n".join(sections.get("## Feature identity", []) + sections.get("## Feature IDs", []))
    if scoped:
        if not re.search(r"Feature ID\s*:\s*`?scoped\b", identity, re.IGNORECASE):
            errors.append("scoped PR must declare Feature ID: scoped")
        if declared_feature_ids:
            errors.append("scoped PR must not declare concrete Feature IDs")
    elif not declared_feature_ids:
        errors.append("Feature ID is required in PR body")
    elif declared_feature_ids != expected_feature_ids:
        errors.append(
            "Feature ID mismatch: expected "
            + ", ".join(sorted("F" + value for value in expected_feature_ids))
            + ", got "
            + ", ".join(sorted("F" + value for value in declared_feature_ids))
        )
    umbrella_match = re.search(r"Umbrella issue:\s*`?#([1-9]\d*)\b", body)
    if not umbrella_match:
        errors.append("umbrella issue is required")
    sha_matches = SHA_RE.findall(body)
    if not sha_matches:
        errors.append("exact source SHA evidence is required")
    elif len(sha_matches) != 1:
        errors.append("exact source SHA evidence must contain exactly one SHA")
    elif expected_sha is not None:
        if not re.fullmatch(r"[0-9a-fA-F]{40}", expected_sha):
            errors.append("expected source SHA must be a full 40-character git SHA")
        elif sha_matches[0].lower() != expected_sha.lower():
            errors.append(
                f"exact source SHA mismatch: expected {expected_sha}, got {sha_matches[0]}"
            )
    if not re.search(r"Spec task IDs:\s*`?T\d{3,}", body):
        errors.append("at least one Spec task ID is required")
    issue_section = sections.get("## Issues", [])
    linked_issue_numbers = (
        [int(number) for number in ISSUE_LINK_RE.findall(issue_section[0])]
        if len(issue_section) == 1
        else []
    )
    if not linked_issue_numbers or not any(number > 0 for number in linked_issue_numbers):
        errors.append("at least one explicit issue linkage keyword is required")
    elif umbrella_match and int(umbrella_match.group(1)) not in linked_issue_numbers:
        errors.append("issue linkage must include the declared umbrella issue")
    risk_section = sections.get("## Risk / validation lane", [])
    if len(risk_section) == 1 and not LANE_RE.search(risk_section[0]):
        errors.append("concrete validation lane is required")
    evidence_section = sections.get("## Как проверено", [])
    if len(evidence_section) == 1 and (
        not EVIDENCE_COMMAND_RE.search(evidence_section[0])
        or not EVIDENCE_STATUS_RE.search(evidence_section[0])
    ):
        errors.append("concrete validation evidence is required")
    legacy_sections = sections.get("## Legacy Impact", [])
    legacy_section = legacy_sections[0] if len(legacy_sections) == 1 else ""
    classifications = CLASSIFICATION_RE.findall(legacy_section)
    if len(classifications) != 1:
        errors.append("Legacy Impact classification is required")
    return errors


def _pr_identity(value: object) -> tuple[int, str, str, str]:
    if not isinstance(value, dict):
        raise ValueError("PR must be an object")
    number, head, base = value.get("number"), value.get("head"), value.get("base")
    if type(number) is not int or number <= 0:
        raise ValueError("PR number must be a positive integer")
    if not isinstance(head, dict) or not isinstance(base, dict):
        raise ValueError("PR head/base must be objects")
    for sha in (head.get("sha"), base.get("sha")):
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
            raise ValueError("PR head/base must contain full SHAs")
    if not isinstance(base.get("ref"), str) or not base["ref"].strip():
        raise ValueError("PR base ref is required")
    return number, head["sha"].lower(), base["sha"].lower(), base["ref"]


def metadata_snapshot(pr: dict, repository: str) -> dict:
    """Project API data to identity and digests only; never persist PR text."""
    number, head, base, ref = _pr_identity(pr)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("invalid repository")
    repos = [pr[side].get("repo") for side in ("head", "base")]
    if not all(isinstance(repo, dict) and isinstance(repo.get("full_name"), str)
               and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo["full_name"]) for repo in repos):
        raise ValueError("PR repository identity is required")
    if repos[1]["full_name"] != repository:
        raise ValueError("PR base repository mismatch")
    if type(pr.get("merged")) is not bool or pr.get("state") not in {"open", "closed"}:
        raise ValueError("invalid PR state")
    if (pr["state"] == "closed") != pr["merged"]:
        raise ValueError("PR must be open or merged")
    merge = pr.get("merge_commit_sha")
    if merge is not None and (not isinstance(merge, str) or not re.fullmatch(r"[0-9a-f]{40}", merge)):
        raise ValueError("invalid merge SHA")
    if pr["merged"] and merge is None:
        raise ValueError("merged PR requires merge SHA")
    # GitHub computes an open PR's synthetic test merge asynchronously. Only
    # the real, immutable merge of a closed PR is part of source identity.
    if not pr["merged"]:
        merge = None
    if type(pr.get("commits")) is not int or not 1 <= pr["commits"] <= 1000:
        raise ValueError("invalid PR commit count")
    if not all(isinstance(pr.get(key), str) and pr[key].strip() for key in ("title", "body")):
        raise ValueError("current PR title/body must be nonempty strings")
    digest = hashlib.sha256(json.dumps([pr["title"], pr["body"]], ensure_ascii=True).encode()).hexdigest()
    return dict(repository=repository, pr_number=number, target_sha=head, api_base_sha=base,
                base_ref=ref, head_repository=repos[0]["full_name"], state=pr["state"],
                merged=pr["merged"], merge_commit_sha=merge, commits=pr["commits"], metadata_digest=digest)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL).decode("ascii").strip()


def checked_base(pr: dict) -> str:
    """Recover the actual checked base without trusting today's master."""
    _, head, base, _ = _pr_identity(pr)
    if not pr["merged"]:
        return base
    merge, count = pr["merge_commit_sha"], pr["commits"]

    def predecessor(sha: str, size: int) -> str:
        rows = _git("rev-list", "--parents", f"--max-count={size}", sha).splitlines()
        if len(rows) != size or any(len(row.split()) != 2 for row in rows):
            raise ValueError("merge/source range must be linear")
        for left, right in zip(rows, rows[1:]):
            if left.split()[1] != right.split()[0]:
                raise ValueError("merge/source range must be contiguous")
        return rows[-1].split()[1]

    def is_ancestor(ancestor: str, descendant: str) -> bool:
        return subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0

    merge_rows = _git("rev-list", "--parents", "--max-count=1", merge).split()
    if len(merge_rows) == 3:
        merge_parent, merge_head = merge_rows[1:]
        merge_tree = _git("rev-parse", f"{merge}^{{tree}}")
        head_tree = _git("rev-parse", f"{head}^{{tree}}")
        head_parents = _git("rev-list", "--parents", "--max-count=1", head).split()[1:]
        if (
            merge_tree == head_tree
            and merge_head == head
            and merge_parent in head_parents
            and int(_git("rev-list", "--count", f"{merge_parent}..{head}")) == count
        ):
            return merge_parent
        raise ValueError("merge/source range must be linear")
    merge_parent = predecessor(merge, 1)
    merge_tree = _git("rev-parse", f"{merge}^{{tree}}")
    head_tree = _git("rev-parse", f"{head}^{{tree}}")
    if merge_tree != head_tree:
        # GitHub can squash a PR whose target advanced after the PR branch was
        # cut.  The merge tree then contains both the reviewed PR and those
        # target commits.  Accept only the exact three-way merge result for the
        # immutable API base and the real merge parent; an edited tree fails.
        if not (is_ancestor(base, merge_parent) and is_ancestor(base, head)):
            raise ValueError("merged tree differs from checked PR head")
        if int(_git("rev-list", "--count", f"{base}..{head}")) != count:
            raise ValueError("merged PR commit count does not match checked base")
        try:
            expected_tree = _git("merge-tree", "--write-tree", merge_parent, head)
        except subprocess.CalledProcessError as exc:
            raise ValueError("merged tree cannot be reconstructed from checked base") from exc
        if not re.fullmatch(r"[0-9a-f]{40}", expected_tree) or expected_tree != merge_tree:
            raise ValueError("merged tree differs from checked PR merge result")
        return base

    # Squash preserves a linear target even when the PR incorporated master
    # with a merge commit. Its exact parent/count/tree bind the checked range.
    squash_base = predecessor(merge, 1)
    if (_git("merge-base", squash_base, head) == squash_base
            and int(_git("rev-list", "--count", f"{squash_base}..{head}")) == count):
        return squash_base
    source_base = predecessor(head, count)
    if predecessor(merge, count) == source_base:
        return source_base
    raise ValueError("merge is not an exact squash or linear rebase of the checked range")


def _validate_diff(current: dict, head: str, base: str) -> list[str]:
    paths = subprocess.check_output([
        "git", "diff", "--no-ext-diff", "--no-textconv", "--name-only", "--no-renames", "-z", f"{base}...{head}",
    ], stderr=subprocess.DEVNULL).decode("utf-8", errors="surrogateescape").split("\0")
    patterns = (
        re.compile(r"^specs/(\d{3,})-[^/]+/"),
        re.compile(r"^changes/(?:unreleased|releases/v[^/]+)/F(\d{3,})\.yaml\Z"),
    )
    features = sorted({match.group(1) for path in paths for pattern in patterns
                       if (match := pattern.match(path)) is not None})
    errors = validate(current["body"], ",".join(features), expected_sha=head,
                      title=current["title"], scoped=not features)
    return [error.split(": ", 1)[0] for error in errors]


def validate_trusted(event_path: Path, current_path: Path, *, policy: str, repository: str,
                     after_path: Path | None = None, result_path: Path | None = None) -> list[str]:
    try:
        if not re.fullmatch(r"[0-9a-f]{40}", policy) or _git("rev-parse", "HEAD") != policy:
            raise ValueError("checkout differs from trusted policy SHA")
        event, current = (json.loads(path.read_text(encoding="utf-8")) for path in (event_path, current_path))
        if not isinstance(event, dict) or event.get("repository", {}).get("full_name") != repository:
            raise ValueError("event repository mismatch")
        before = metadata_snapshot(current, repository)
        event_pr = event.get("pull_request")
        _pr_identity(event_pr)
        event_identity = metadata_snapshot({**event_pr, "title": current["title"], "body": current["body"]}, repository)
        if type(event.get("number")) is not int or event["number"] != before["pr_number"]:
            raise ValueError("event PR number mismatch")
        if any(before[key] != event_identity[key] for key in before if key != "metadata_digest"):
            raise ValueError("current PR identity differs from event")
        base = checked_base(current)
        errors = _validate_diff(current, before["target_sha"], base)
        if errors:
            return errors
        if after_path is not None:
            after = json.loads(after_path.read_text(encoding="utf-8"))
            if before != metadata_snapshot(after, repository):
                raise ValueError("PR changed during metadata validation")
        if result_path is not None:
            if after_path is None:
                raise ValueError("result requires two API snapshots")
            run_id, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "")
            if not all(re.fullmatch(r"[1-9]\d*", value) for value in (run_id, attempt)):
                raise ValueError("run identity is required")
            with result_path.open("x", encoding="utf-8") as output:
                json.dump(dict(before, schema_version=1, policy_sha=policy, base_sha=base,
                               run_id=int(run_id), run_attempt=int(attempt), result="pass"), output, sort_keys=True)
    except (OSError, UnicodeError, ValueError, TypeError, AttributeError, RecursionError, subprocess.CalledProcessError):
        return ["trusted PR identity, policy, metadata or snapshot validation failed"]
    return []


def validate_event(event_path: Path, current_path: Path) -> list[str]:
    try:
        event = json.loads(event_path.read_text(encoding="utf-8"))
        current = json.loads(current_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError):
        return ["cannot read event/current PR JSON"]
    try:
        if not isinstance(event, dict):
            raise ValueError("event must be an object")
        identity = _pr_identity(event.get("pull_request"))
        if type(event.get("number")) is not int or event["number"] != identity[0]:
            raise ValueError("event PR number mismatch")
        if _pr_identity(current) != identity:
            raise ValueError("current PR identity differs from event")
        if current.get("state") != "open":
            raise ValueError("current PR must be open")
        if not all(isinstance(current.get(key), str) and current[key].strip() for key in ("title", "body")):
            raise ValueError("current PR title/body must be nonempty strings")
    except ValueError as exc:
        return [str(exc)]
    _, head, base, _ = identity
    try:
        checkout = subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True,
        ).stdout.strip().decode("ascii")
        if checkout != head:
            return ["checkout HEAD differs from event PR head"]
        return _validate_diff(current, head, base)
    except (OSError, UnicodeError, subprocess.CalledProcessError):
        return ["cannot determine exact PR diff with shared history"]
    except ValueError:
        return ["invalid PR metadata values"]


def self_test() -> int:
    sha = "a" * 40
    title = "[F216] Перестроить процесс"
    body = """## Feature identity
- Feature ID: `F216`
- Umbrella issue: `#6090`
- Spec task IDs: `T042`

## Как проверено
- `pytest -q tests/governance`: passed
- Exact source SHA: {sha}

## Risk / validation lane
- Lane: significant-feature

## Issues
- Refs #6090

## Legacy Impact
- Classification: `untouched`

## Перед merge
- evidence recorded
""".format(sha=sha)
    assert validate(body, "216", expected_sha=sha, title=title) == []
    assert validate(body.replace("F216", "F215"), "216", title=title)
    assert validate(body.replace("F216", "F1024").replace("T042", "T1000"), "1024", title="[F1024] Перестроить процесс") == []
    assert validate(body, "216", expected_sha="b" * 40, title=title)
    assert validate(body.replace("Classification: `untouched`", "Classification: `remove` / `retain-with-exception` / `untouched`"), "216", title=title)
    assert validate(body.replace("## Issues\n- Refs #6090", "## Issues\n"), "216", title=title)
    assert validate(body.replace("Refs #6090", "Refs #___"), "216", title=title)
    assert validate(body.replace("Refs #6090", "Refs #999"), "216", title=title)
    assert validate(body, "216", title="Перестроить процесс")
    assert validate(body, "216", title="[F215] Перестроить процесс")
    print("pr-metadata self-test: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("body", type=Path, nargs="?")
    parser.add_argument("--feature-id")
    parser.add_argument("--expected-sha")
    parser.add_argument("--title")
    parser.add_argument("--scoped", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--event", type=Path)
    parser.add_argument("--current-pr", type=Path)
    parser.add_argument("--current-pr-after", type=Path)
    parser.add_argument("--trusted-policy-sha")
    parser.add_argument("--repository")
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    if any((args.current_pr_after, args.trusted_policy_sha, args.repository, args.result)):
        if not all((args.event, args.current_pr, args.trusted_policy_sha, args.repository)):
            parser.error("trusted mode requires event, current PR, policy SHA and repository")
        if args.result is not None and args.current_pr_after is None:
            parser.error("trusted result requires the second API snapshot")
    if args.event is not None or args.current_pr is not None:
        if args.event is None or args.current_pr is None:
            parser.error("--event and --current-pr are required together")
        if (args.body is not None or args.feature_id is not None or args.expected_sha is not None
                or args.title is not None or args.scoped or args.self_test):
            parser.error("event mode cannot be combined with body-file or self-test options")
        if args.trusted_policy_sha:
            errors = validate_trusted(args.event, args.current_pr, policy=args.trusted_policy_sha,
                                      repository=args.repository, after_path=args.current_pr_after, result_path=args.result)
        else:
            errors = validate_event(args.event, args.current_pr)
    else:
        if args.self_test:
            return self_test()
        if args.body is None:
            parser.error("body is required unless --self-test is used")
        if not args.feature_id:
            parser.error("--feature-id is required unless --self-test is used")
        if args.title is None:
            parser.error("--title is required unless --self-test is used")
        try:
            body = args.body.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"pr-metadata: ERROR: {exc}", file=sys.stderr)
            return 1
        errors = validate(body, args.feature_id, expected_sha=args.expected_sha, title=args.title, scoped=args.scoped)
    if errors:
        for error in errors:
            print(f"pr-metadata: ERROR: {error}", file=sys.stderr)
        return 1
    print("pr-metadata: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
