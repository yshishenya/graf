# Spec Kit Flow

Classify the risk and validation lane before changing files. Significant and
high-risk product/code work follows Spec Kit. Low-risk direct work is allowed
only when the lane rules below say scoped validation is enough.

## Risk And Validation Lanes

Use the first lane that fully fits the work. If classification is uncertain,
move down to the stricter lane.

| Lane | Fits When | Required Process | Minimum Validation |
|------|-----------|------------------|--------------------|
| Read-only investigation | No file changes, no external state changes | No Spec Kit artifacts | Report inspected sources and confidence/limits |
| Docs-only / mechanical | Comments, typos, links, docs wording, or template text with no product/runtime behavior change | Direct edit; no new spec or issue unless part of an active slice | Markdown/template review; run a focused check if one exists |
| Tiny low-risk code | Narrow code edit with no shared behavior, no data contract change, and no high-risk domain | Direct edit; record lane and rationale | Focused test/lint for touched path; add one small check for non-trivial logic |
| Active Spec Kit slice | Work belongs to an existing `specs/<feature>/` and `tasks.md` | Use the existing spec, plan, quickstart, and tasks; do not create a duplicate slice | Focused quickstart/tests during development; `infra/scripts/ci-local.sh --fast` at closeout/PR; one `--full` on the exact release candidate |
| Significant feature / architecture | New feature, architecture, cross-module contract, or user-visible workflow | Full Spec Kit sequence below | Quickstart plus `infra/scripts/ci-local.sh --fast` before closeout/PR; one `--full` on the exact release candidate |
| High-risk product area | Capture, auth, privacy, storage, AI, deletion, diagnostics, deployment, high-risk UX, or reference-fidelity work | Full Spec Kit with mandatory clarify/checklist/analyze | Domain gates, quickstart and `infra/scripts/ci-local.sh --fast` before closeout; one `--full` on the exact release candidate; deploy gate only for release |
| Release / production deploy | Version, release, production rollout, smoke, rollback, or deployment evidence | Release guidance and explicit user approval | `cd-remote.sh --dry-run`; `--execute` only when release gate is met |

Direct lanes never bypass product gates. Escalate to a full Spec Kit lane when
the change touches:

- recording start/stop, system audio, microphone, routing, buffering, or upload
  retry behavior;
- auth, sessions, devices, permissions, audit, retention, deletion, privacy, or
  secrets;
- MediaScribe, Langfuse, MinIO, Postgres, Temporal, Docker, deployment, backup,
  restore, rollback, or public health checks;
- tray, widget, onboarding, delete, admin, accessibility, localization,
  unavailable/degraded states, or reference-fidelity UX;
- public API contracts, migrations, shared helpers, security boundaries, or
  behavior used by multiple feature slices;
- process and governance surfaces such as `AGENTS.md`, constitution,
  `docs/agent-guidance/`, Spec Kit templates, PR templates, release policy, or
  bootstrap/extension tooling, unless the edit is strictly typo/link-only.

For pull requests, record the lane, what was checked, and why broader gates were
not required.

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
$speckit-converge
validation/release gates
```

Use the Codex skill names above. Upstream docs may show slash commands such as
`/speckit.specify`; this repository uses `$speckit-*` skills.

This ordered list is the canonical significant/high-risk GRAF path. The
upstream six-step `Full SDD Cycle` is a useful generic subset, but MUST NOT be
treated as a complete GRAF workflow for significant/high-risk work because it
does not own project checklist review, issue sync, convergence, or GRAF
validation/release gates.

## 0. Constitution

Run `$speckit-constitution` before real feature work if
`.specify/memory/constitution.md` still contains placeholders or if project
principles need to change.

Do not dilute constitution rules inside specs, plans, or tasks. If a feature
conflicts with the constitution, update the feature or explicitly amend the
constitution first.

## 1. Specify

Use `$speckit-specify` for every new feature, architectural slice, significant
change, or high-risk change. Do not create a duplicate spec for direct low-risk
work or for implementation that already belongs to an active Spec Kit slice.

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
- system audio, microphone capture, or audio routing;
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
- record the selected risk/validation lane and release gate;
- resolve technical unknowns in `research.md`;
- define the implementation approach in `plan.md`;
- create `data-model.md` where data is involved;
- create `contracts/` for APIs, capture/session protocols, or UI contracts;
- create `quickstart.md` with validation scenarios;
- keep the root `AGENTS.md` stable; active feature routing belongs only to the
  ignored per-worktree `.specify/feature.json` pointer and the explicit
  prerequisite command output.

Planning stops when constitution gates fail or important clarifications remain
unresolved.

If the agent-context hook must be invoked directly, use the Python environment
from the installed `specify` shebang rather than system Python:

```sh
specify_bin="$(command -v specify)"
specify_shebang="$(sed -n '1s/^#!//p' "$specify_bin")"
PATH="$(dirname "$specify_shebang"):$PATH" \
  .specify/extensions/agent-context/scripts/bash/update-agent-context.sh \
  specs/<number>-<slug>/plan.md
```

The bootstrap already applies this runtime fallback. Do not install PyYAML
globally to make the hook work.

## 4. Checklist

Use `$speckit-checklist` after planning for high-risk areas. Checklists are
"unit tests for English": they validate requirements, not implementation.

Default checklist set:

- `security.md` for auth, secrets, egress, audit, retention, deletion,
  diagnostics.
- `audio-capture.md` for macOS system audio, microphone permissions, track
  truth, performance, and QA matrix.
- `advanced-routing.md` only when a newly approved feature introduces a
  distinct audio-routing architecture, packaging model, or privileged boundary.
- `ux.md` for tray/widget, onboarding, accessibility, theme, deletion UX, and
  reference fidelity and asset provenance.
- `infra.md` for Docker, Temporal, MinIO, Postgres, MediaScribe, Langfuse,
  backup, and restore.

Checklist items should ask whether requirements are complete, clear,
measurable, consistent, and traceable. Avoid implementation-test wording like
"verify the button works."

Custom checklist checkbox state is reviewer-owned. Generation leaves new items
unchecked; a reviewer records the result. Implementation MUST read that state
as a gate and MUST NOT mark reviewer checklist items complete itself.

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
- final validation tasks must name the lane from `plan.md`/`quickstart.md`;
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
- Repeat until the feature's declared analyze threshold passes. When a feature
  does not declare a stricter threshold, the default is no unresolved critical
  or high issues and no blocking clarification requests. Feature 183 explicitly
  requires `CRITICAL 0 · HIGH 0 · MEDIUM 0`.

`$speckit-implement` is blocked until this loop is clean.

## 7. GitHub Issue Sync

Use `$speckit-taskstoissues` for every implementation feature slice after
planning and analysis when:

- the repository remote is a GitHub URL;
- `tasks.md` exists with executable tasks;
- implementation is not explicitly skipped by the user.

Do not create GitHub issues for read-only, docs-only, or tiny low-risk direct
lanes unless the user explicitly asks for tracking.

Never create issues in a repository that does not match the configured git
remote. Follow `docs/agent-guidance/tracker-policy.md` and
`docs/agent-guidance/github-issue-canon.md`.

## 8. Implement

Use `$speckit-implement` only after:

- high-risk checklists are complete; non-high-risk checklist gaps may proceed
  only with recorded user risk acceptance;
- analyze meets the feature's declared threshold (or the default zero
  critical/high threshold when none is declared);
- tasks are generated and reviewed;
- GitHub issue sync is complete when implementation is in scope.

Implementation rules:

- read `tasks.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`,
  `quickstart.md`, and constitution before changing code;
- execute tasks phase by phase;
- mark completed tasks as `[X]` only after implementation and validation;
- respect dependencies and `[P]` markers;
- run validation from `quickstart.md` and any tests introduced by the plan;
- record the selected risk/validation lane and evidence before calling work done;
- do not silently broaden scope beyond the active spec.

Implementation closeout rules:

- reconcile every completed `tasks.md` item with its GitHub issue before
  calling the slice done;
- ensure the PR body uses `Fixes`, `Closes`, or `Resolves` only for issues fully
  satisfied by the PR;
- use `Refs` or `Part of` for partial or related work;
- add a detailed Russian closure comment to every fully closed issue before
  closing it, or immediately after merge when GitHub auto-close already closed
  it;
- leave issues open when acceptance criteria, validation evidence, or scope
  remain incomplete, and add a Russian status comment explaining what is still
  missing.

## 9. Converge And Validate

Run `$speckit-converge` after implementation and focused validation. Convergence
is append-only: add any newly discovered work to `tasks.md`, execute it, and
repeat convergence until no mandatory task remains. Only then run the declared
repository and release gates. The upstream six-step workflow ending at
implementation does not satisfy this closeout.

## Commit Checkpoints

Spec Kit documentation stages may use explicitly approved documentation
commits, but auto-commit hooks are disabled by default:

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
