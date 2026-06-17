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


def remove_legacy_canon(root):
    legacy = root / "docs" / "github-issue-canon.md"
    current = root / "docs" / "agent-guidance" / "github-issue-canon.md"
    if not legacy.exists() or not current.exists() or legacy.is_symlink():
        return False
    text = legacy.read_text(encoding="utf-8", errors="ignore")
    if "# GitHub Issue Canon" not in text or "$speckit-taskstoissues" not in text:
        return False
    legacy.unlink()
    return True


def main() -> int:
    root = repo_root()
    ext = extension_root(root)
    slug = repo_slug(root)
    feature = current_feature(root)

    changed = []
    if copy_template(
        ext,
        "docs/agent-guidance/github-issue-canon.md",
        root,
        "docs/agent-guidance/github-issue-canon.md",
    ):
        changed.append("docs/agent-guidance/github-issue-canon.md")
    if remove_legacy_canon(root):
        changed.append("removed docs/github-issue-canon.md")
    if copy_template(ext, "github/ISSUE_TEMPLATE/config.yml", root, ".github/ISSUE_TEMPLATE/config.yml"):
        changed.append(".github/ISSUE_TEMPLATE/config.yml")
    if copy_template(ext, "github/ISSUE_TEMPLATE/spec-kit-work-item.yml", root, ".github/ISSUE_TEMPLATE/spec-kit-work-item.yml"):
        changed.append(".github/ISSUE_TEMPLATE/spec-kit-work-item.yml")
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
