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

- write GitHub issue titles, bodies, comments, status updates, closure comments,
  and sync notes in Russian by default;
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
- add a short Russian comment with the validation result before or while
  closing;
- if a GitHub issue is closed but `tasks.md` is still open, verify the
  implementation and evidence before marking the task complete.

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
