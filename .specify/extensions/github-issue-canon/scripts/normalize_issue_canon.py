#!/usr/bin/env python3
from __future__ import annotations

import re
import sys

from issue_canon_common import REQUIRED_SECTIONS, TITLE_RE, current_feature, is_speckit_issue, label_names, list_open_issues, repo_root, repo_slug, run


def infer_priority(body: str, title: str) -> str:
    match = re.search(r"\bP[0-3]\b", body + "\n" + title)
    return match.group(0) if match else "P1"


def infer_area(body: str, title: str) -> str:
    text = (title + "\n" + body).lower()
    candidates = [
        ("auth", ["auth", "tenant", "device", "permission"]),
        ("contract", ["openapi", "contract", "schema", "problem response"]),
        ("docs", ["quickstart", "docs", "documentation", "prd"]),
        ("infra", ["docker", "compose", "migration", "runtime", "readiness"]),
        ("storage", ["minio", "object", "storage", "artifact"]),
        ("tests", ["test", "pytest", "coverage", "fake"]),
        ("security", ["security", "privacy", "redaction", "audit"]),
        ("macos", ["macos", "driver", "audio"]),
        ("ux", ["ux", "ui", "accessibility"]),
        ("ingest", ["ingest", "upload", "finalize", "session", "range"]),
    ]
    for area, needles in candidates:
        if any(needle in text for needle in needles):
            return area
    return "ingest"


def infer_type(body: str, title: str) -> str:
    text = (title + "\n" + body).lower()
    if "test" in text or "coverage" in text:
        return "type:test-gap"
    if "docs" in text or "quickstart" in text or "documentation" in text:
        return "type:docs"
    if "hardening" in text or "security" in text or "privacy" in text:
        return "type:hardening"
    return "type:bug"


def canonical_title(issue: dict, default_feature: str | None) -> str:
    title = issue.get("title") or ""
    if TITLE_RE.match(title):
        return title
    body = issue.get("body") or ""
    feature = default_feature or "000"
    feature_match = re.search(r"(?:Feature:\s*`?|specs/)(\d{3})", body)
    if feature_match:
        feature = feature_match.group(1)
    priority = infer_priority(body, title)
    area = infer_area(body, title)
    cleaned = re.sub(r"^012 hackathon (remediation|additional):\s*", "", title, flags=re.I)
    cleaned = cleaned[:1].upper() + cleaned[1:] if cleaned else "Resolve Spec Kit issue"
    return f"[{feature}][{priority}][{area}] {cleaned}"


def extract_context_line(body: str, label: str) -> str | None:
    match = re.search(rf"^- {re.escape(label)}:\s*(.+)$", body, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def canonical_body(issue: dict, title: str) -> str:
    body = issue.get("body") or ""
    missing = [section for section in REQUIRED_SECTIONS if section not in body]
    if not missing:
        return body

    match = TITLE_RE.match(title)
    feature = match.group("feature") if match else "000"
    priority = match.group("priority") if match else infer_priority(body, title)
    area = match.group("area") if match else infer_area(body, title)
    tasks = extract_context_line(body, "Spec Kit tasks") or ", ".join(sorted(set(re.findall(r"\bT\d{3}\b", body)))) or "T000"
    source = extract_context_line(body, "Source") or "Spec Kit task-to-issue sync / review"
    gate = extract_context_line(body, "Gate") or ("blocks deployment" if "gate:deployment-blocker" in ",".join(label_names(issue)) else "blocks PR")

    summary = title
    if match:
        summary = title[match.end() :].strip()
    summary = summary[:1].upper() + summary[1:] if summary else "Resolve Spec Kit issue"

    prefix = ""
    if "## Summary" not in body:
        prefix += f"## Summary\n\n{summary}.\n\n"
    if "## Context" not in body:
        prefix += (
            "## Context\n\n"
            f"- Feature: `{feature}`\n"
            f"- Priority: `{priority}`\n"
            f"- Area: `{area}`\n"
            f"- Spec tasks: {tasks}\n"
            f"- Source: {source}\n"
            f"- Gate: {gate}\n"
            f"- Related issues:\n\n"
        )

    suffix = ""
    if "## Links" not in body:
        suffix = (
            "\n## Links\n\n"
            f"- Spec: `specs/{feature}-*/spec.md`\n"
            f"- Plan: `specs/{feature}-*/plan.md`\n"
            f"- Tasks: `specs/{feature}-*/tasks.md`\n"
            "- Related:\n"
        )

    return prefix + body.strip() + suffix


def main() -> int:
    root = repo_root()
    slug = repo_slug(root)
    default_feature = current_feature(root)
    numbers = {int(arg.lstrip("#")) for arg in sys.argv[1:] if arg.strip()}
    issues = [issue for issue in list_open_issues(slug) if is_speckit_issue(issue)]
    if numbers:
        issues = [issue for issue in issues if issue["number"] in numbers]

    changed = []
    for issue in issues:
        title = canonical_title(issue, default_feature)
        labels = label_names(issue)
        match = TITLE_RE.match(title)
        add_labels = set()
        if match:
            add_labels.add(f"feature:{match.group('feature')}")
            add_labels.add(f"priority:{match.group('priority')}")
            add_labels.add(f"area:{match.group('area').split('/', 1)[0]}")
        if not any(label.startswith("type:") for label in labels):
            add_labels.add(infer_type(issue.get("body") or "", issue.get("title") or ""))
        args = ["gh", "issue", "edit", str(issue["number"]), "--repo", slug]
        if title != issue.get("title"):
            args.extend(["--title", title])
        body = canonical_body(issue, title)
        if body != (issue.get("body") or ""):
            args.extend(["--body", body])
        new_labels = sorted(add_labels - labels)
        if new_labels:
            args.extend(["--add-label", ",".join(new_labels)])
        if len(args) > 5:
            run(args)
            changed.append(issue["number"])

    if changed:
        print("github-issue-canon: normalized issues " + ", ".join(f"#{n}" for n in changed))
    else:
        print("github-issue-canon: no issue normalization needed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
