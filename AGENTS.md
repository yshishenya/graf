# Agent Operating Guide

This repository uses GitHub Spec Kit for spec-driven development. All product and implementation work must follow the Spec Kit flow unless the user explicitly asks for a one-off investigation or emergency fix.

Spec Kit is installed locally with:

- CLI: `specify 0.8.14`
- Default integration: `codex`
- Codex skills mode: `.agents/skills/speckit-*`
- Project state: `.specify/`

## Project Context

Product: `2brain Rec`, a self-hosted Krisp-category meeting capture and transcription product with a macOS virtual audio driver.

Primary baseline document:

- `docs/prd-voice-layer-final.md`

Treat `docs/prd-voice-layer-final.md` as the product baseline until a Spec Kit feature spec supersedes a specific slice of it.

## Spec Kit Command Style

This repo was initialized with Codex skills mode. Use skill names in conversation:

- `$speckit-constitution`
- `$speckit-specify`
- `$speckit-clarify`
- `$speckit-plan`
- `$speckit-checklist`
- `$speckit-tasks`
- `$speckit-analyze`
- `$speckit-implement`
- `$speckit-taskstoissues`

The upstream Spec Kit docs often show slash commands such as `/speckit.specify`; in this repo, use the equivalent Codex skill name above.

## Required Development Flow

### 0. Constitution

Run `$speckit-constitution` before real feature work if `.specify/memory/constitution.md` still contains template placeholders or if project principles need to change.

The constitution must encode non-negotiable project rules from the PRD:

- driver-first macOS MVP;
- visible capture indicator;
- no silent or invisible recording;
- owner-controlled storage and explicit egress policy;
- MediaScribe and Langfuse boundaries;
- deletion truthfulness;
- security/privacy gates;
- clean-room UI and brand-distance rules.

Do not dilute constitution rules inside feature specs, plans, or tasks. If a feature conflicts with the constitution, update the feature or explicitly amend the constitution first.

### 1. Specify

Use `$speckit-specify` for every feature, architectural slice, or significant change.

The spec must describe what and why, not implementation details. It should include:

- actors and user goals;
- user stories with priorities;
- functional requirements;
- measurable success criteria;
- edge cases and failure states;
- explicit out-of-scope items;
- dependencies and assumptions.

Spec files live under `specs/<number>-<short-name>/spec.md`. The active feature path is stored locally in `.specify/feature.json`; this file is intentionally ignored because it is per-worktree state.

### 2. Clarify

Use `$speckit-clarify` before planning unless the feature is trivial and already unambiguous.

Clarification is mandatory when the feature touches:

- recording start/stop behavior;
- audio driver or routing;
- local buffering;
- upload/retry semantics;
- MediaScribe, Langfuse, MinIO, Postgres, Temporal, or Docker;
- auth, sessions, devices, permissions, audit, retention, deletion, or privacy;
- UX for tray/widget/onboarding/delete/admin states.

The command asks up to 5 targeted questions and writes accepted answers back into `spec.md`.

### 3. Plan

Use `$speckit-plan` after the spec is clear.

The plan must:

- run the constitution check;
- resolve technical unknowns in `research.md`;
- define the implementation approach in `plan.md`;
- create `data-model.md` where data is involved;
- create `contracts/` for APIs, protocols, driver IPC, or UI contracts;
- create `quickstart.md` with validation scenarios;
- update this `AGENTS.md` plan reference between the Spec Kit markers.

Planning must stop if constitution gates fail or important clarifications remain unresolved.

<!-- SPECKIT START -->
Current Spec Kit plan: `specs/004-real-bidirectional-passthrough/plan.md`

Active feature: `004-real-bidirectional-passthrough`

Use the plan, research, data model, contracts, and quickstart in
`specs/004-real-bidirectional-passthrough/` as the authoritative context for
macOS real bidirectional passthrough planning until a later Spec Kit feature
supersedes this slice.
<!-- SPECKIT END -->

### 4. Checklist

Use `$speckit-checklist` after planning for high-risk areas. These checklists are "unit tests for English": they validate the quality of requirements, not the implementation.

Default checklist set for this project:

- `security.md` for auth, secrets, egress, audit, retention, deletion, diagnostics.
- `driver.md` for macOS virtual audio, installer, permissions, passthrough, QA matrix.
- `ux.md` for tray/widget, onboarding, accessibility, theme, deletion UX, brand distance.
- `infra.md` for Docker, Temporal, MinIO, Postgres, MediaScribe, Langfuse, backup/restore.

Checklist items should ask whether requirements are complete, clear, measurable, consistent, and traceable. Avoid implementation-test wording like "verify the button works."

### 5. Tasks

Use `$speckit-tasks` only after `spec.md`, `plan.md`, and supporting design artifacts are ready.

Generated `tasks.md` must be dependency ordered and organized by independently testable user story. Every task must use the required format:

```text
- [ ] T001 [P] [US1] Description with exact file path
```

Rules:

- setup and foundational tasks come before user story tasks;
- test tasks appear before implementation tasks when tests are requested or risk warrants TDD;
- parallel markers `[P]` are used only for tasks that touch different files and have no dependency on incomplete work;
- each user story must have independent validation criteria;
- task descriptions must include concrete paths.

### 6. Analyze

Use `$speckit-analyze` after `$speckit-tasks` and before `$speckit-implement`.

This is a read-only consistency gate across:

- `spec.md`;
- `plan.md`;
- `tasks.md`;
- `.specify/memory/constitution.md`.

Do not implement while analyze reports critical issues. Resolve critical and high findings by updating the relevant spec, plan, or tasks before proceeding.

### 7. Implement

Use `$speckit-implement` only after:

- checklists are complete or the user explicitly accepts the risk of proceeding;
- analyze has no critical blockers;
- tasks are generated and reviewed.

Implementation rules:

- read `tasks.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, and constitution before changing code;
- execute tasks phase by phase;
- mark completed tasks as `[X]` in `tasks.md`;
- respect task dependencies and `[P]` markers;
- run validation from `quickstart.md` and any tests introduced by the plan;
- do not silently broaden scope beyond the active spec.

### 8. Optional GitHub Issue Sync

Use `$speckit-taskstoissues` only when:

- `tasks.md` exists;
- the repository remote is a GitHub URL;
- the user explicitly wants GitHub issues created.

Never create issues in a repository that does not match the configured git remote.

## Optional Commands For Quality And Validation

Spec Kit optional commands are part of our standard quality loop:

- `$speckit-clarify`: run before `$speckit-plan` to remove ambiguity. Mandatory for high-risk privacy, driver, backend, infra, and UX work.
- `$speckit-checklist`: run after `$speckit-plan` to create requirement-quality checklists. Use it for security, driver, UX, infra, and any area where requirements must be audited before coding.
- `$speckit-analyze`: run after `$speckit-tasks` and before `$speckit-implement` to detect inconsistency, missing coverage, ambiguity, duplication, and constitution conflicts.

Recommended full command sequence:

```text
$speckit-constitution
$speckit-specify
$speckit-clarify
$speckit-plan
$speckit-checklist
$speckit-tasks
$speckit-analyze
$speckit-implement
```

For very small documentation-only changes, the user may explicitly skip to direct editing, but code/product implementation must use the full sequence.

## Git And Hooks

The Spec Kit git extension is installed in `.specify/extensions/git/`.

Behavior:

- before `$speckit-specify`, the git hook creates a feature branch;
- before/after many commands, optional git commit hooks may be offered;
- auto-commit is disabled by default unless configured in `.specify/extensions/git/git-config.yml`;
- this repo may enable auto-commit for completed Spec Kit documentation artifacts
  such as constitution, specification, clarification, plan, checklist, tasks, and
  analysis outputs.

Agent rules:

- auto-commit may run only for user-approved Spec Kit hooks that produce
  documentation artifacts;
- do not auto-commit implementation code, generated build outputs, secrets, or
  unrelated working tree changes;
- for implementation changes, commit only after explicit user approval and
  validation;
- never reset or discard user changes;
- use feature branches created by Spec Kit for feature work;
- preserve generated Spec Kit artifacts in review.

## Repository Hygiene

Do not commit secrets. Never write actual credentials, API keys, tokens, signed URLs, or passwords into specs, plans, tasks, logs, or diagnostics.

Spec Kit project files expected in git:

- `.specify/`
- `.agents/skills/speckit-*`
- `AGENTS.md`
- `specs/` once features are created

Keep generated build/cache/secret files out of git through `.gitignore`.

## Product-Specific Gates

Any feature touching `2brain Rec` capture, transcription, storage, or AI must preserve these gates:

- macOS driver-first MVP; no no-driver fallback.
- Capture and driver implementation is platform-native by default: macOS feature slice
  uses macOS-native languages and APIs, with future platforms handled by separate
  native stacks and separate architecture decisions.
- Manual start/stop remains available.
- Assisted auto-start is internal-MVP only unless customer policy explicitly enables it.
- Active capture must always have a visible local indicator and one-action stop.
- Desktop app never sends audio directly to MediaScribe and never stores MediaScribe credentials.
- Langfuse traces are metadata-only by default.
- Deletion copy must not promise universal erasure outside `2brain Rec` control.
- MediaScribe, Langfuse, backups, local buffers, Temporal payloads, and diagnostics must be represented in deletion truth.
- UI must be clean-room and pass brand-distance review.

## Useful Local Commands

```sh
specify --version
specify integration list
specify extension list
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
```
