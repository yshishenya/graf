#!/usr/bin/env python3
"""Fail-closed reviewer-owned Spec Kit checklist gate.

This command deliberately does not decide whether a requirement is satisfied. An
independent reviewer (or a trusted adapter that launches one) writes the custom
checklist markers, a deterministic canonical report, and a separate invocation
result. This command verifies their identity, evidence, freshness, and write
allow-list before an implementation agent may continue.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
REPORT_NAME = "review-report.json"
RESULT_SCHEMA_VERSION = 1
RESULT_DEFAULT = Path(".dev/spec-kit/reviewer-result.json")
BUILTIN_CHECKLIST = "requirements.md"
RESERVED_REPORTS = {"review-report.md", REPORT_NAME}
CHECKBOX_RE = re.compile(r"^\s*-\s+\[([ xX])\]\s+(?:(CHK\d+)\s+)?(.+?)\s*$")
CHECKBOX_LINE_RE = re.compile(r"^(?P<prefix>\s*-\s+\[)[ xX](?P<suffix>\].*?)(?P<newline>\r?\n)?$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
OWNERSHIP_RE = re.compile(
    r"(?:review\s+ownership|\bownership\b)[^\n]{0,180}reviewer-owned",
    re.IGNORECASE,
)
BUILTIN_RE = re.compile(
    r"^\s*(?:[-*]\s+)?(?:\*\*)?built[- ]in\s+"
    r"(?:specification\s+quality\s+)?(?:checklist|lifecycle)"
    r"(?:\*\*)?\b|"
    r"^\s*(?:[-*]\s+)?(?:\*\*)?встроенн\w*\s+"
    r"(?:провер\w*|чеклист\w*)",
    re.IGNORECASE | re.MULTILINE,
)
SECRET_RE = re.compile(
    r"(?:password|passwd|token|api[_ -]?key|secret|private[_ -]?key)\s*[:=]"
    r"|BEGIN [A-Z ]*PRIVATE KEY|/Users/[^/]+/Library/Keychains",
    re.IGNORECASE,
)


def fail(message: str) -> "NoReturn":
    raise ValueError(message)


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def root_relative(root: Path, path: Path) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes repository root: {path}") from exc
    if path.is_symlink():
        raise ValueError(f"symlink is not an allowed checklist/report path: {path}")
    return relative.as_posix()


def safe_relative_path(value: str) -> bool:
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts and "" not in path.parts


def git_sha(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False
    )
    if result.returncode or not SHA_RE.fullmatch(result.stdout.strip().lower()):
        fail("cannot resolve a full 40-character target SHA")
    return result.stdout.strip().lower()


def resolve_feature(root: Path, value: str) -> Path:
    candidate = (root / value).resolve()
    try:
        relative = candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("feature directory escapes repository root") from exc
    if not relative.parts or candidate.name == "":
        fail("feature directory is invalid")
    if not candidate.is_dir() or candidate.is_symlink():
        fail(f"feature directory is missing or symlinked: {value}")
    return candidate


def classify_checklist(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        fail(f"cannot read checklist {path}: {exc}")
    reviewer_owned = bool(OWNERSHIP_RE.search(text))
    explicit_builtin = bool(BUILTIN_RE.search(text))
    # requirements.md has a separate specify/clarify lifecycle by convention.
    # A custom requirements.md is accepted only when it explicitly declares
    # reviewer ownership and does not also claim the built-in lifecycle.
    built_in = explicit_builtin or (path.name == BUILTIN_CHECKLIST and not reviewer_owned)
    if reviewer_owned and explicit_builtin:
        fail(f"checklist has conflicting built-in and reviewer ownership: {path}")
    if reviewer_owned:
        return "reviewer-owned"
    if built_in:
        return "built-in"
    fail(
        f"checklist ownership is missing or ambiguous: {path}; add an explicit "
        "Review Ownership/Ownership marker with reviewer-owned"
    )


def custom_checklists(root: Path, feature: Path) -> list[Path]:
    directory = feature / "checklists"
    if not directory.exists():
        return []
    if directory.is_symlink() or not directory.is_dir():
        fail(f"checklists directory is not a real directory: {directory}")
    paths: list[Path] = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if path.suffix.lower() != ".md":
            continue
        if path.is_symlink() or not path.is_file():
            fail(f"checklist is not a regular file: {path}")
        if path.name in RESERVED_REPORTS:
            continue
        ownership = classify_checklist(path)
        if ownership == "reviewer-owned":
            paths.append(path)
        elif path.name == BUILTIN_CHECKLIST:
            # requirements.md may be reviewer-owned in older/custom slices, but
            # an unowned or explicitly built-in file is never silently promoted.
            continue
    return paths


def parse_items(root: Path, path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    fenced = False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        fail(f"cannot read checklist {path}: {exc}")
    for number, line in enumerate(lines, start=1):
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = CHECKBOX_RE.match(line)
        if not match:
            continue
        marker, item_id, text = match.groups()
        if not item_id:
            fail(f"checklist item has no CHK identifier: {root_relative(root, path)}:{number}")
        if item_id in seen:
            fail(f"duplicate checklist item identifier {item_id}")
        seen.add(item_id)
        items.append(
            {
                "id": item_id,
                "checked": marker.lower() == "x",
                "text": text.strip(),
                "text_sha256": digest_bytes(text.strip().encode("utf-8")),
                "checklist_path": root_relative(root, path),
                "line": number,
            }
        )
    if not items:
        fail(f"reviewer-owned checklist has no identified checkbox items: {path}")
    return items


def input_paths(root: Path, feature: Path) -> list[Path]:
    paths = [feature / "spec.md", feature / "plan.md", feature / "tasks.md"]
    for name in ("quickstart.md", "research.md", "data-model.md"):
        candidate = feature / name
        if candidate.is_file():
            paths.append(candidate)
    paths.extend(
        [
            root / ".specify/memory/constitution.md",
            root / "AGENTS.md",
            root / "docs/agent-guidance/spec-kit-flow.md",
        ]
    )
    return sorted({path.resolve() for path in paths}, key=lambda item: root_relative(root, item))


def file_digest(root: Path, path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        fail(f"review input is missing or symlinked: {root_relative(root, path)}")
    return {"path": root_relative(root, path), "sha256": digest_bytes(path.read_bytes())}


def expected_inputs(root: Path, feature: Path) -> list[dict[str, str]]:
    return [file_digest(root, path) for path in input_paths(root, feature)]


def expected_items(root: Path, paths: list[Path]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        for item in parse_items(root, path):
            if item["id"] in seen:
                fail(f"duplicate checklist item identifier {item['id']}")
            seen.add(item["id"])
            items.append(item)
    return sorted(items, key=lambda item: (item["checklist_path"], item["line"], item["id"]))


def relative_feature(root: Path, feature: Path) -> str:
    return root_relative(root, feature)


def validate_evidence(
    evidence: Any, *, root: Path, feature: Path, target_sha: str, item_id: str
) -> None:
    if not isinstance(evidence, list) or not evidence:
        fail(f"checked item {item_id} must have evidence")
    for entry in evidence:
        if not isinstance(entry, dict):
            fail(f"evidence for {item_id} must be an object")
        source_sha = entry.get("source_sha")
        if source_sha != target_sha:
            fail(f"evidence for {item_id} is not bound to target SHA")
        if "path" in entry:
            path_value = entry.get("path")
            if not isinstance(path_value, str) or not safe_relative_path(path_value):
                fail(f"evidence path for {item_id} is unsafe")
            path = (root / path_value).resolve()
            try:
                path.relative_to(root.resolve())
            except ValueError as exc:
                raise ValueError(f"evidence path for {item_id} escapes root") from exc
            if path.is_symlink() or not path.is_file():
                fail(f"evidence path for {item_id} is missing or symlinked")
            start = entry.get("line_start")
            end = entry.get("line_end", start)
            if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
                fail(f"evidence path for {item_id} needs a valid line range")
        elif "command" in entry:
            command = entry.get("command")
            if not isinstance(command, str) or not command.strip() or SECRET_RE.search(command):
                fail(f"evidence command for {item_id} is invalid or contains sensitive data")
            if entry.get("exit_code") != 0 or not DIGEST_RE.fullmatch(str(entry.get("artifact_sha256", ""))):
                fail(f"evidence command for {item_id} needs exit_code=0 and artifact_sha256")
        else:
            fail(f"evidence for {item_id} needs path or command")


def canonical_without_digest(report: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in report.items() if key != "report_digest"}


def validate_report(
    root: Path, feature: Path, target_sha: str, report_path: Path, result_path: Path | None
) -> dict[str, Any]:
    paths = custom_checklists(root, feature)
    if not paths:
        if result_path is not None and result_path.exists():
            fail("review result exists although no reviewer-owned checklist is required")
        return {"status": "not_required", "checklists": []}
    expected = expected_items(root, paths)
    if report_path != feature / REPORT_NAME:
        fail(f"canonical report must be {root_relative(root, feature / REPORT_NAME)}")
    if report_path.is_symlink() or not report_path.is_file():
        fail("canonical reviewer report is missing or symlinked")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"canonical reviewer report is invalid: {exc}")
    if not isinstance(report, dict) or report.get("schema_version") != SCHEMA_VERSION:
        fail("canonical reviewer report has unsupported schema_version")
    required = {
        "schema_version", "feature_dir", "target_sha", "input_digests", "checklist_paths",
        "items", "totals", "verdict", "report_digest",
    }
    if set(report) != required:
        fail("canonical reviewer report fields are not exact")
    if report["feature_dir"] != relative_feature(root, feature) or report["target_sha"] != target_sha:
        fail("canonical reviewer report identity does not match current target")
    expected_paths = [root_relative(root, path) for path in paths]
    if report["checklist_paths"] != expected_paths:
        fail("canonical reviewer report checklist paths are not deterministic")
    if report["input_digests"] != expected_inputs(root, feature):
        fail("canonical reviewer report input digests are stale or incomplete")
    if report["report_digest"] != digest_bytes(json_bytes(canonical_without_digest(report))):
        fail("canonical reviewer report digest mismatch")
    reported_items = report["items"]
    if not isinstance(reported_items, list):
        fail("canonical reviewer report items must be a list")
    expected_by_id = {item["id"]: item for item in expected}
    seen: set[str] = set()
    checked = unchecked = 0
    for item in reported_items:
        if not isinstance(item, dict) or set(item) != {
            "id", "checklist_path", "line", "text_sha256", "status", "evidence_refs", "reason"
        }:
            fail("canonical reviewer report item fields are invalid")
        item_id = item["id"]
        if item_id in seen or item_id not in expected_by_id:
            fail(f"unknown or duplicate reviewer item {item_id}")
        seen.add(item_id)
        baseline = expected_by_id[item_id]
        if item["checklist_path"] != baseline["checklist_path"] or item["line"] != baseline["line"]:
            fail(f"reviewer item location changed for {item_id}")
        if item["text_sha256"] != baseline["text_sha256"]:
            fail(f"reviewer item text changed for {item_id}")
        if item["status"] == "checked":
            checked += 1
            validate_evidence(item["evidence_refs"], root=root, feature=feature, target_sha=target_sha, item_id=item_id)
            if item["reason"]:
                fail(f"checked item {item_id} must not carry a reason")
        elif item["status"] == "unchecked":
            unchecked += 1
            if not isinstance(item["reason"], str) or not item["reason"].strip():
                fail(f"unchecked item {item_id} needs a reason")
            if item["evidence_refs"]:
                validate_evidence(item["evidence_refs"], root=root, feature=feature, target_sha=target_sha, item_id=item_id)
        else:
            fail(f"invalid reviewer item status {item.get('status')!r}")
    if seen != set(expected_by_id):
        fail("canonical reviewer report is missing checklist items")
    totals = {"total": len(expected), "checked": checked, "unchecked": unchecked}
    if report["totals"] != totals:
        fail("canonical reviewer report totals mismatch")
    expected_verdict = "PASS" if unchecked == 0 else "FAIL"
    if report["verdict"] != expected_verdict:
        fail("canonical reviewer report verdict mismatch")
    if result_path is None or not result_path.is_file() or result_path.is_symlink():
        fail("reviewer invocation result is missing or symlinked")
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"reviewer invocation result is invalid: {exc}")
    validate_result(root, feature, target_sha, result, report_path)
    if result["status"] != "PASS" or report["verdict"] != "PASS":
        fail("reviewer gate is not a full PASS")
    for marker in expected:
        report_item = next(item for item in reported_items if item["id"] == marker["id"])
        marker_status = "checked" if marker["checked"] else "unchecked"
        if report_item["status"] != marker_status:
            fail(f"reviewer report disagrees with checklist marker {marker['id']}")
    return {"status": "PASS", "checklists": expected_paths, "totals": totals}


def validate_result(root: Path, feature: Path, target_sha: str, result: Any, report_path: Path) -> None:
    if not isinstance(result, dict):
        fail("reviewer invocation result must be an object")
    fields = {
        "schema_version", "status", "orchestrator_id", "reviewer_id", "target_sha", "feature_dir",
        "report_path", "exit_code", "timed_out", "checklist_paths", "totals",
    }
    if set(result) != fields or result["schema_version"] != RESULT_SCHEMA_VERSION:
        fail("reviewer invocation result fields are invalid")
    if not isinstance(result["orchestrator_id"], str) or not result["orchestrator_id"]:
        fail("reviewer orchestrator_id is missing")
    if not isinstance(result["reviewer_id"], str) or not result["reviewer_id"]:
        fail("reviewer reviewer_id is missing")
    if result["orchestrator_id"] == result["reviewer_id"]:
        fail("reviewer and orchestrator identities must be distinct")
    if result["target_sha"] != target_sha or result["feature_dir"] != relative_feature(root, feature):
        fail("reviewer invocation result identity is stale")
    if result["report_path"] != root_relative(root, report_path):
        fail("reviewer invocation report path mismatch")
    if result["exit_code"] != 0 or result["timed_out"] is not False:
        fail("reviewer invocation did not finish successfully")
    if result["status"] not in {"PASS", "FAIL"}:
        fail("reviewer invocation status is invalid")
    if not isinstance(result["checklist_paths"], list) or result["checklist_paths"] != sorted(result["checklist_paths"]):
        fail("reviewer invocation checklist paths are not sorted")
    if not isinstance(result["totals"], dict):
        fail("reviewer invocation totals are invalid")


def snapshot_tree(root: Path) -> dict[str, str]:
    candidates: set[Path] = set()
    for command in (
        ["git", "ls-files", "-z"],
        ["git", "ls-files", "-z", "--others", "--exclude-standard"],
    ):
        result = subprocess.run(command, cwd=root, capture_output=True, check=False)
        if result.returncode:
            fail("cannot snapshot repository before reviewer invocation")
        candidates.update(root / value for value in result.stdout.decode().split("\0") if value)
    snapshot: dict[str, str] = {}
    for path in candidates:
        if path.is_symlink() or not path.is_file():
            snapshot[root_relative(root, path)] = "<non-regular>"
        else:
            snapshot[root_relative(root, path)] = digest_bytes(path.read_bytes())
    return snapshot


def run_reviewer(
    root: Path, feature: Path, target_sha: str, result_path: Path, orchestrator_id: str,
    timeout_seconds: int, reviewer_command: list[str], report_path: Path,
) -> int:
    paths = custom_checklists(root, feature)
    if not paths:
        print(json.dumps({"status": "not_required", "checklists": []}, ensure_ascii=False, sort_keys=True))
        return 0
    before = snapshot_tree(root)
    allowed = {root_relative(root, path) for path in paths}
    allowed.add(root_relative(root, report_path))
    allowed.add(root_relative(root, result_path))
    env = {
        **os.environ,
        "GRAF_REVIEW_FEATURE_DIR": relative_feature(root, feature),
        "GRAF_REVIEW_TARGET_SHA": target_sha,
        "GRAF_REVIEW_REPORT": root_relative(root, report_path),
        "GRAF_REVIEW_RESULT": root_relative(root, result_path),
        "GRAF_REVIEW_ORCHESTRATOR_ID": orchestrator_id,
    }
    try:
        completed = subprocess.run(
            reviewer_command, cwd=root, env=env, text=True, timeout=timeout_seconds, check=False
        )
    except subprocess.TimeoutExpired:
        fail("reviewer invocation timed out")
    if completed.returncode != 0:
        fail(f"reviewer invocation failed with exit code {completed.returncode}")
    after = snapshot_tree(root)
    changed = {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
    outside = sorted(changed - allowed)
    if outside:
        fail("reviewer changed files outside allow-list: " + ", ".join(outside))
    result = validate_report(root, feature, target_sha, report_path, result_path)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--feature-dir", required=True)
    parser.add_argument("--target-sha")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--orchestrator-id")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("reviewer_command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        feature = resolve_feature(root, args.feature_dir)
        target_sha = (args.target_sha or git_sha(root)).lower()
        if not SHA_RE.fullmatch(target_sha):
            fail("target SHA must be exactly 40 lowercase hexadecimal characters")
        report_path = (args.report or feature / REPORT_NAME)
        if not report_path.is_absolute():
            report_path = (root / report_path).resolve()
        result_path = args.result
        if result_path is not None and not result_path.is_absolute():
            result_path = (root / result_path).resolve()
        if args.run:
            if not args.orchestrator_id:
                fail("--orchestrator-id is required with --run")
            if args.timeout_seconds < 1:
                fail("--timeout-seconds must be positive")
            command = args.reviewer_command
            if command and command[0] == "--":
                command = command[1:]
            if not command:
                fail("reviewer command is required with --run")
            if result_path is None:
                fail("--result is required with --run")
            return run_reviewer(root, feature, target_sha, result_path, args.orchestrator_id, args.timeout_seconds, command, report_path)
        result = validate_report(root, feature, target_sha, report_path, result_path)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"review-checklists: ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
