# Tracker Policy

## Active Tracking Model

`tasks.md` is the implementation source of truth. GitHub issues are the external
tracker for execution, review, PR links, status comments, closure comments, and
validation evidence.

Use `$speckit-taskstoissues` after planning and analyze for every implementation
feature slice when a GitHub remote and executable `tasks.md` exist.

## GitHub Issue Rules

All GitHub issues created manually, through `$speckit-taskstoissues`, or through
direct `gh issue create` must follow:

- `docs/agent-guidance/github-issue-canon.md`
- `.github/ISSUE_TEMPLATE/spec-kit-work-item.yml`

Language rules:

- write GitHub issue titles, bodies, PR descriptions, comments, status updates,
  closure comments, and sync notes in Russian by default;
- use simple language understandable to non-technical teammates;
- describe blockers as concrete facts: what is blocked, why it is blocked, and
  what exact action unblocks it.

Duplicate prevention:

- search existing issues by feature number, task ID, issue URL, title, and
  labels before creating new issues;
- never create issues in a repository that does not match the configured git
  remote.

Closure rules:

- when a task is marked `[X]` in `tasks.md`, close the corresponding GitHub
  issue only after validation evidence is checked;
- add a detailed Russian closure comment before closing; it must explain what
  changed, why it matters, how it was checked, what is out of scope, and which
  PR and Spec Kit task it closes;
- if GitHub auto-closes an issue after merge, add the detailed closure comment
  immediately after merge if it is missing;
- if a GitHub issue is closed but `tasks.md` is still open, verify the
  implementation and evidence before marking the task complete.

PR rules:

- use the repository pull request template when it exists;
- use `Fixes #123`, `Closes #123`, or `Resolves #123` only when the PR fully
  satisfies every acceptance criterion for that issue;
- use `Refs #123` or `Part of #123` when the PR is partial, preparatory, or
  related but not sufficient to close the issue;
- when a PR closes multiple issues, list every closing keyword explicitly in the
  PR body;
- do not rely on GitHub auto-close when a PR targets a non-default branch.

## Linear Is Retired

Linear is not part of the active Spec Kit workflow for this repository.

Rules:

- do not install, run, or restore Linear sync;
- do not create Linear issues or projects;
- do not treat missing Linear issues, Linear comments, Linear project sync, or
  Linear usage-limit failures as blockers;
- do not add new Linear links to current specs, tasks, plans, issues, or
  status docs;
- old Linear references inside historical feature evidence are archival only,
  not active instructions.

`.specify/linear.yml` is not active project state. If it reappears from an old
worktree or branch, treat it as retired workflow residue and remove it unless
the user explicitly reintroduces Linear.
