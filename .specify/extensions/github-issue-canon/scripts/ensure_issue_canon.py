#!/usr/bin/env python3
from __future__ import annotations

from issue_canon_common import (
    copy_template,
    current_feature,
    ensure_agents_block,
    ensure_labels,
    extension_root,
    repo_root,
    repo_slug,
)


MANAGED_MARKER = "<!-- managed-by: github-issue-canon -->"
CANON_TEMPLATE = "docs/agent-guidance/github-issue-canon.md"
CANON_PATH = "docs/agent-guidance/github-issue-canon.md"


def migrate_legacy_canon(root, ext):
    legacy = root / "docs" / "github-issue-canon.md"
    current = root / "docs" / "agent-guidance" / "github-issue-canon.md"
    if not legacy.exists() or legacy.is_symlink():
        return None
    text = legacy.read_text(encoding="utf-8", errors="ignore")
    if "# GitHub Issue Canon" not in text or "$speckit-taskstoissues" not in text:
        return None
    if not current.exists():
        current.parent.mkdir(parents=True, exist_ok=True)
        legacy.replace(current)
        return "moved docs/github-issue-canon.md to docs/agent-guidance/github-issue-canon.md"
    current_text = current.read_text(encoding="utf-8", errors="ignore")
    if text == current_text or MANAGED_MARKER in text:
        legacy.unlink()
        return "removed docs/github-issue-canon.md"
    print(
        "github-issue-canon: retained docs/github-issue-canon.md because it has custom content; "
        "merge it into docs/agent-guidance/github-issue-canon.md manually"
    )
    return None


def refresh_managed_canon(ext, root):
    current = root / CANON_PATH
    template = ext / "templates" / CANON_TEMPLATE
    if not current.exists():
        if copy_template(ext, CANON_TEMPLATE, root, CANON_PATH):
            return CANON_PATH
        return None
    current_text = current.read_text(encoding="utf-8", errors="ignore")
    if MANAGED_MARKER not in current_text:
        if "# GitHub Issue Canon" in current_text and "$speckit-taskstoissues" in current_text:
            print(
                "github-issue-canon: retained docs/agent-guidance/github-issue-canon.md "
                "because it has no managed marker"
            )
        return None
    template_text = template.read_text(encoding="utf-8")
    if current_text == template_text:
        return None
    current.write_text(template_text, encoding="utf-8")
    return CANON_PATH


def refresh_canon_template(ext, root):
    changed = []
    legacy_result = migrate_legacy_canon(root, ext)
    if legacy_result:
        changed.append(legacy_result)
    canon_result = refresh_managed_canon(ext, root)
    if canon_result:
        changed.append(canon_result)
    return changed


def main() -> int:
    root = repo_root()
    ext = extension_root(root)
    slug = repo_slug(root)
    feature = current_feature(root)

    changed = []
    changed.extend(refresh_canon_template(ext, root))
    if copy_template(ext, "github/ISSUE_TEMPLATE/config.yml", root, ".github/ISSUE_TEMPLATE/config.yml"):
        changed.append(".github/ISSUE_TEMPLATE/config.yml")
    if copy_template(ext, "github/ISSUE_TEMPLATE/spec-kit-work-item.yml", root, ".github/ISSUE_TEMPLATE/spec-kit-work-item.yml"):
        changed.append(".github/ISSUE_TEMPLATE/spec-kit-work-item.yml")
    if copy_template(ext, "github/pull_request_template.md", root, ".github/pull_request_template.md"):
        changed.append(".github/pull_request_template.md")
    if ensure_agents_block(root):
        changed.append("AGENTS.md")

    ensure_labels(slug, feature)

    print("github-issue-canon: ensured files and labels")
    if changed:
        print("github-issue-canon: changed files:")
        for path in changed:
            print(f"  - {path}")
    if feature:
        print(f"github-issue-canon: active/default feature label feature:{feature}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
