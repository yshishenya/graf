# Spec Kit GitHub Issue Canon Extension

Spec Kit extension that installs and enforces a canonical GitHub Issue format
around `$speckit-taskstoissues`.

It is designed to be upstream-clean:

- no patches to `github/spec-kit`;
- no edits to globally installed `$HOME/.agents/skills/speckit-*`;
- reusable across repositories through `specify extension add --from ...`;
- automatic lifecycle integration through `before_taskstoissues` and
  `after_taskstoissues` hooks.

## What It Installs

Project files:

- `docs/github-issue-canon.md`
- `.github/ISSUE_TEMPLATE/config.yml`
- `.github/ISSUE_TEMPLATE/spec-kit-work-item.yml`
- an `AGENTS.md` rule block when `AGENTS.md` exists

GitHub labels:

- `feature:<number>`
- `priority:P0` / `priority:P1` / `priority:P2` / `priority:P3`
- `area:*`
- `gate:*`
- `type:*`
- `needs-triage`

Spec Kit commands:

- `$speckit-github-issue-canon-ensure`
- `$speckit-github-issue-canon-validate`
- `$speckit-github-issue-canon-normalize`

Hooks:

- `before_taskstoissues`: ensure canon files and labels exist
- `after_taskstoissues`: validate created/open Spec Kit issues

## Install

From a project initialized with Spec Kit:

```sh
specify extension add github-issue-canon \
  --from https://github.com/yshishenya/spec-kit-ext-github-issue-canon/archive/refs/heads/main.zip
```

For local development:

```sh
specify extension add github-issue-canon \
  --dev /path/to/spec-kit-ext-github-issue-canon
```

## Automatic Bootstrap

Add this extension install step to your personal `speckit-bootstrap` wrapper
after the core `git` and `agent-context` extensions are installed:

```sh
specify extension add github-issue-canon \
  --from https://github.com/yshishenya/spec-kit-ext-github-issue-canon/archive/refs/heads/main.zip
```

This repository includes no upstream Spec Kit changes.

## Validation

```sh
python3 scripts/ensure_issue_canon.py
python3 scripts/validate_issue_canon.py
```

The scripts are intended to run from a Spec Kit project after the extension has
been installed under `.specify/extensions/github-issue-canon`.
