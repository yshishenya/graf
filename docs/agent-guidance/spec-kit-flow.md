# Spec Kit Flow

All product and implementation work follows Spec Kit unless the user explicitly
asks for a one-off investigation or emergency fix.

## Command Sequence

```text
$speckit-constitution
$speckit-specify
$speckit-clarify
$speckit-plan
$speckit-checklist
$speckit-tasks
$speckit-analyze
$speckit-taskstoissues
$speckit-implement
```

Use the Codex skill names above. Upstream docs may show slash commands such as
`/speckit.specify`; this repository uses `$speckit-*` skills.

## 0. Constitution

Run `$speckit-constitution` before real feature work if
`.specify/memory/constitution.md` still contains placeholders or if project
principles need to change.

Do not dilute constitution rules inside specs, plans, or tasks. If a feature
conflicts with the constitution, update the feature or explicitly amend the
constitution first.

## 1. Specify

Use `$speckit-specify` for every feature, architectural slice, or significant
change.

The spec must describe what and why, not implementation details. It should
include:

- actors and user goals;
- prioritized user stories;
- functional requirements;
- measurable success criteria;
- edge cases and failure states;
- explicit out-of-scope items;
- dependencies and assumptions.

Spec files live under `specs/<number>-<short-name>/spec.md`. The active feature
path is stored locally in `.specify/feature.json`; this file is per-worktree
state and is intentionally ignored.

## 2. Clarify

Use `$speckit-clarify` before planning unless the feature is trivial and already
unambiguous.

Clarification is mandatory when the feature touches:

- recording start/stop behavior;
- system audio, microphone capture, audio driver, or routing;
- local buffering;
- upload/retry semantics;
- MediaScribe, Langfuse, MinIO, Postgres, Temporal, or Docker;
- auth, sessions, devices, permissions, audit, retention, deletion, or privacy;
- tray, widget, onboarding, delete, admin, or other high-risk UX states.

If `clarify` finds unresolved ambiguity, re-run it after the user answers and
before moving to plan, checklist, tasks, analyze, or implementation.

## 3. Plan

Use `$speckit-plan` after the spec is clear.

The plan must:

- run the constitution check;
- resolve technical unknowns in `research.md`;
- define the implementation approach in `plan.md`;
- create `data-model.md` where data is involved;
- create `contracts/` for APIs, capture/session protocols, future driver IPC,
  or UI contracts;
- create `quickstart.md` with validation scenarios;
- update the root `AGENTS.md` plan reference between the Spec Kit markers.

Planning stops when constitution gates fail or important clarifications remain
unresolved.

## 4. Checklist

Use `$speckit-checklist` after planning for high-risk areas. Checklists are
"unit tests for English": they validate requirements, not implementation.

Default checklist set:

- `security.md` for auth, secrets, egress, audit, retention, deletion,
  diagnostics.
- `audio-capture.md` for macOS system audio, microphone permissions, track
  truth, performance, and QA matrix.
- `driver.md` only when a feature touches future macOS virtual audio,
  installer, passthrough, repair, or driver QA.
- `ux.md` for tray/widget, onboarding, accessibility, theme, deletion UX, and
  brand distance.
- `infra.md` for Docker, Temporal, MinIO, Postgres, MediaScribe, Langfuse,
  backup, and restore.

Checklist items should ask whether requirements are complete, clear,
measurable, consistent, and traceable. Avoid implementation-test wording like
"verify the button works."

## 5. Tasks

Use `$speckit-tasks` only after `spec.md`, `plan.md`, and supporting design
artifacts are ready.

Generated `tasks.md` must be dependency ordered and organized by independently
testable user story. Every task must use this format:

```text
- [ ] T001 [P] [US1] Description with exact file path
```

Rules:

- setup and foundational tasks come before user story tasks;
- test tasks appear before implementation tasks when tests are requested or risk
  warrants TDD;
- `[P]` is used only for tasks that touch different files and have no dependency
  on incomplete work;
- each user story has independent validation criteria;
- task descriptions include concrete paths.

## 6. Analyze

Use `$speckit-analyze` after `$speckit-tasks` and before
`$speckit-implement`.

Analyze is a read-only consistency gate across:

- `spec.md`;
- `plan.md`;
- `tasks.md`;
- `.specify/memory/constitution.md`.

Mandatory quality loop:

- Run `$speckit-analyze`.
- If it reports critical findings, unresolved high findings, or clarification
  gaps, update `spec.md`, `plan.md`, or `tasks.md`.
- Re-run `$speckit-clarify` when ambiguity is the root cause.
- Re-run `$speckit-checklist` for affected areas.
- Re-run `$speckit-analyze`.
- Repeat until one full pass has no unresolved critical issues and no blocking
  clarification requests.

`$speckit-implement` is blocked until this loop is clean.

## 7. GitHub Issue Sync

Use `$speckit-taskstoissues` for every implementation feature slice after
planning and analysis when:

- the repository remote is a GitHub URL;
- `tasks.md` exists with executable tasks;
- implementation is not explicitly skipped by the user.

Never create issues in a repository that does not match the configured git
remote. Follow `docs/agent-guidance/tracker-policy.md` and
`docs/agent-guidance/github-issue-canon.md`.

## 8. Implement

Use `$speckit-implement` only after:

- checklists are complete or the user explicitly accepts the risk of proceeding;
- analyze has no critical blockers;
- tasks are generated and reviewed;
- GitHub issue sync is complete when implementation is in scope.

Implementation rules:

- read `tasks.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`,
  `quickstart.md`, and constitution before changing code;
- execute tasks phase by phase;
- mark completed tasks as `[X]` only after implementation and validation;
- respect dependencies and `[P]` markers;
- run validation from `quickstart.md` and any tests introduced by the plan;
- do not silently broaden scope beyond the active spec.

## Commit Checkpoints

Spec Kit documentation stages may use user-approved auto-commit hooks:

- `$speckit-constitution` -> constitution updates
- `$speckit-specify` -> `spec.md`
- `$speckit-clarify` -> clarified `spec.md`
- `$speckit-plan` -> `plan.md` and supporting artifacts
- `$speckit-checklist` -> checklist files
- `$speckit-tasks` -> `tasks.md`
- `$speckit-analyze` -> analyze output
- `$speckit-taskstoissues` -> issue links and labels

Implementation code commits happen only after explicit user approval and
validation. Never auto-commit generated build outputs, secrets, unrelated
working tree changes, or user edits.
