#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


REQUIRED_SECTIONS = [
    "## Кратко",
    "## Контекст",
    "## Проблема",
    "## Проверенные факты",
    "## Границы задачи",
    "## Критерии приемки",
    "## Что проверить перед закрытием",
    "## Заметки по реализации",
    "## Ссылки",
]


DEFAULT_LABELS = {
    "needs-triage": ("ededed", "Needs initial classification against the issue canon"),
    "priority:P0": ("b60205", "Critical blocker: correctness, security, privacy, or data loss"),
    "priority:P1": ("d93f0b", "High priority blocker before PR or deployment readiness"),
    "priority:P2": ("fbca04", "Medium priority follow-up or hardening"),
    "priority:P3": ("0e8a16", "Low priority polish or cleanup"),
    "gate:pr-blocker": ("b60205", "Must be resolved before PR-ready claim"),
    "gate:deployment-blocker": ("d93f0b", "Must be resolved before deployment-plan or production readiness claim"),
    "type:bug": ("d73a4a", "Confirmed defect or incorrect behavior"),
    "type:hardening": ("fbca04", "Hardening, safety, privacy, durability, or operational robustness"),
    "type:docs": ("0075ca", "Documentation/status/runbook issue"),
    "type:test-gap": ("0e8a16", "Missing, weak, or misleading validation coverage"),
    "type:feature": ("a2eeef", "New capability or feature work"),
}

DEFAULT_AREAS = {
    "auth": ("5319e7", "Authentication, authorization, tenant, user, and device boundaries"),
    "contract": ("0366d6", "OpenAPI, API contracts, schemas, Problem responses"),
    "docs": ("0075ca", "Documentation, quickstart, status, PRD, runbook"),
    "infra": ("0052cc", "Docker, compose, runtime, migrations, deployment infrastructure"),
    "ingest": ("1d76db", "Server ingest API, lifecycle, finalize, and status"),
    "macos": ("c2e0c6", "macOS app, driver, audio routing, native capture"),
    "observability": ("0b7285", "Logging, tracing, metrics, diagnostics, redaction"),
    "security": ("ee0701", "Security, privacy, redaction, secrets, audit"),
    "storage": ("006b75", "Object storage, MinIO, artifact persistence"),
    "tests": ("0e8a16", "Test coverage, test fakes, validation proof gates"),
    "ux": ("d4c5f9", "User experience, interaction, copy, accessibility"),
}

TITLE_FORMAT = "[<feature>][<priority>][<area>] T###: <русский результат>"
TITLE_RE = re.compile(
    r"^\[(?P<feature>\d{3})\]\[(?P<priority>P[0-3])\]\[(?P<area>[^\]]+)\] "
    r"(?P<task>T\d{3}): (?P<outcome>.+)"
)
LEGACY_TITLE_RE = re.compile(
    r"^\[(?P<feature>\d{3})\]\[(?P<priority>P[0-3])\]\[(?P<area>[^\]]+)\] "
    r"(?P<outcome>.+)"
)
TASK_RE = re.compile(r"\bT\d{3}\b")


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def run_with_retry(
    cmd: list[str],
    cwd: Path | None = None,
    attempts: int = 3,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    last_result: subprocess.CompletedProcess[str] | None = None
    for attempt in range(attempts):
        last_result = subprocess.run(
            cmd,
            cwd=cwd,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if last_result.returncode == 0:
            return last_result
        if attempt + 1 < attempts:
            time.sleep(1.5 * (attempt + 1))
    if check and last_result is not None:
        raise subprocess.CalledProcessError(
            last_result.returncode,
            cmd,
            output=last_result.stdout,
            stderr=last_result.stderr,
        )
    assert last_result is not None
    return last_result


def repo_root() -> Path:
    result = run(["git", "rev-parse", "--show-toplevel"])
    return Path(result.stdout.strip())


def extension_root(root: Path) -> Path:
    path = root / ".specify" / "extensions" / "github-issue-canon"
    if not path.exists():
        raise SystemExit(f"github-issue-canon extension not installed at {path}")
    return path


def repo_slug(root: Path) -> str:
    remote = run(["git", "config", "--get", "remote.origin.url"], cwd=root).stdout.strip()
    if not remote:
        raise SystemExit("git remote.origin.url is not set")
    if remote.startswith("git@github.com:"):
        slug = remote.removeprefix("git@github.com:").removesuffix(".git")
    elif "github.com/" in remote:
        slug = remote.split("github.com/", 1)[1].removesuffix(".git")
    else:
        raise SystemExit(f"remote is not a GitHub URL: {remote}")
    if "/" not in slug:
        raise SystemExit(f"could not parse GitHub owner/repo from remote: {remote}")
    return slug


def copy_template(ext: Path, rel_src: str, root: Path, rel_dst: str) -> bool:
    src = ext / "templates" / rel_src
    dst = root / rel_dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    content = src.read_text(encoding="utf-8")
    if dst.exists() and dst.read_text(encoding="utf-8") == content:
        return False
    dst.write_text(content, encoding="utf-8")
    return True


def ensure_agents_block(root: Path) -> bool:
    path = root / "AGENTS.md"
    if not path.exists():
        return False
    marker = "Все GitHub issues в этом репозитории"
    existing_marker = "All GitHub issues created for this repository"
    text = path.read_text(encoding="utf-8")
    legacy_path = "docs/github-issue-canon.md"
    canon_path = "docs/agent-guidance/github-issue-canon.md"
    if marker in text or existing_marker in text:
        updated = text.replace(legacy_path, canon_path)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            return True
        return False
    anchor = "Never create issues in a repository that does not match the configured git remote."
    block = f"""

Все GitHub issues в этом репозитории, созданные вручную, через
`$speckit-taskstoissues` или через прямой `gh issue create`, должны следовать
project issue canon в `{canon_path}`.

Обязательный формат title:

```text
[<feature>][<priority>][<area>] T###: <русский результат>
```

Обязательные секции issue body, в таком порядке:

- `Кратко`
- `Контекст`
- `Проблема`
- `Проверенные факты`
- `Границы задачи`
- `Критерии приемки`
- `Что проверить перед закрытием`
- `Заметки по реализации`
- `Ссылки`

Spec Kit issue sync должен сохранять связь с номером фичи, task ID,
validation evidence, PR и closure criteria. Используй labels как structured
metadata: `feature:<number>`, `priority:P0`-`priority:P3`, `area:<name>`,
`gate:<name>` и `type:<name>`.

PR description, issue comments, closure comments и sync notes пиши на русском
простым языком. `Fixes #...`, `Closes #...` и `Resolves #...` используй
только когда PR полностью закрывает issue; для частичной связи используй
`Refs #...` или `Part of #...`.

Перед закрытием issue добавь подробный русский closure comment: что закрыто,
почему это важно, как проверено, что не входит, какой PR и какой Spec Kit task
закрыты.
"""
    if anchor in text:
        text = text.replace(anchor, anchor + block, 1)
    else:
        text += "\n" + block.strip() + "\n"
    text = text.rstrip() + "\n"
    path.write_text(text, encoding="utf-8")
    return True


def list_existing_labels(slug: str) -> dict[str, tuple[str, str]]:
    result = run_with_retry([
        "gh",
        "label",
        "list",
        "--repo",
        slug,
        "--limit",
        "1000",
        "--json",
        "name,color,description",
    ])
    labels = json.loads(result.stdout)
    return {
        label["name"]: (
            str(label.get("color") or "").lower().lstrip("#"),
            str(label.get("description") or ""),
        )
        for label in labels
    }


def ensure_label(
    slug: str,
    name: str,
    color: str,
    description: str,
    existing: dict[str, tuple[str, str]],
) -> None:
    expected = (color.lower().lstrip("#"), description)
    current = existing.get(name)
    if current == expected:
        return
    if current is not None:
        edit = ["gh", "label", "edit", name, "--repo", slug, "--color", color, "--description", description]
        run_with_retry(edit, attempts=3)
        existing[name] = expected
        return

    create = ["gh", "label", "create", name, "--repo", slug, "--color", color, "--description", description]
    result = run_with_retry(create, check=False)
    if result.returncode == 0:
        existing[name] = expected
        return
    edit = ["gh", "label", "edit", name, "--repo", slug, "--color", color, "--description", description]
    run_with_retry(edit, attempts=3)
    existing[name] = expected


def ensure_labels(slug: str, feature: str | None = None) -> None:
    existing = list_existing_labels(slug)
    for name, (color, desc) in DEFAULT_LABELS.items():
        ensure_label(slug, name, color, desc, existing)
    for area, (color, desc) in DEFAULT_AREAS.items():
        ensure_label(slug, f"area:{area}", color, desc, existing)
    if feature:
        ensure_label(slug, f"feature:{feature}", "bfd4f2", f"Spec Kit feature {feature}", existing)


def current_feature(root: Path) -> str | None:
    feature_json = root / ".specify" / "feature.json"
    if feature_json.exists():
        try:
            data = json.loads(feature_json.read_text(encoding="utf-8"))
            branch = str(data.get("branch") or data.get("feature_branch") or "")
            match = re.search(r"(\d{3})", branch)
            if match:
                return match.group(1)
            spec_path = str(data.get("spec_path") or data.get("feature_dir") or "")
            match = re.search(r"specs/(\d{3})-", spec_path)
            if match:
                return match.group(1)
        except Exception:
            pass
    specs = root / "specs"
    if specs.exists():
        candidates = sorted(p.name[:3] for p in specs.iterdir() if p.is_dir() and re.match(r"\d{3}-", p.name))
        if candidates:
            return candidates[-1]
    return None


def list_open_issues(slug: str) -> list[dict]:
    result = run([
        "gh",
        "issue",
        "list",
        "--repo",
        slug,
        "--state",
        "open",
        "--limit",
        "300",
        "--json",
        "number,title,body,labels,state",
    ])
    return json.loads(result.stdout)


def label_names(issue: dict) -> set[str]:
    return {label["name"] for label in issue.get("labels", [])}


def is_speckit_issue(issue: dict) -> bool:
    labels = label_names(issue)
    body = issue.get("body") or ""
    title = issue.get("title") or ""
    return (
        any(name.startswith("feature:") for name in labels)
        or bool(TITLE_RE.match(title))
        or bool(LEGACY_TITLE_RE.match(title))
        or "Spec tasks:" in body
        or "Spec Kit" in body
        or TASK_RE.search(body) is not None
    )


def validate_issue(issue: dict) -> list[str]:
    errors: list[str] = []
    title = issue.get("title") or ""
    body = issue.get("body") or ""
    labels = label_names(issue)
    match = TITLE_RE.match(title)
    if not match:
        errors.append(f"title does not match {TITLE_FORMAT}")
    else:
        feature = match.group("feature")
        priority = match.group("priority")
        area_root = match.group("area").split("/", 1)[0]
        task = match.group("task")
        if f"feature:{feature}" not in labels:
            errors.append(f"missing label feature:{feature}")
        if f"priority:{priority}" not in labels:
            errors.append(f"missing label priority:{priority}")
        if f"area:{area_root}" not in labels and f"area:{match.group('area')}" not in labels:
            errors.append(f"missing area label for {match.group('area')}")
        if task not in body:
            errors.append(f"body context must include Spec tasks: {task}")
    if not any(name.startswith("type:") for name in labels):
        errors.append("missing type:* label")
    for section in REQUIRED_SECTIONS:
        if section not in body:
            errors.append(f"missing body section {section}")
    return errors


def git_add_paths(root: Path, paths: list[str]) -> None:
    existing = [p for p in paths if (root / p).exists()]
    if existing:
        run(["git", "add", *existing], cwd=root)
