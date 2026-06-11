# Agent Operating Guide

This repository uses GitHub Spec Kit for spec-driven development. All product and implementation work must follow the Spec Kit flow unless the user explicitly asks for a one-off investigation or emergency fix.

Spec Kit is installed locally with:

- CLI: `specify` (check the current version with `specify --version`)
- Default integration: `codex`
- Codex skills mode: global skills under `$HOME/.agents/skills/speckit-*`
- Agent context extension: `.specify/extensions/agent-context/`
- Project state: `.specify/`

## Project Context

Product: `2brain Rec`, a self-hosted meeting capture and transcription product
with a macOS system-audio-first MVP. The virtual audio driver is parked as
future advanced-routing work until it has separate safety evidence.

Primary baseline document:

- `docs/prd-voice-layer-final.md`

Treat `docs/prd-voice-layer-final.md` as the product baseline until a Spec Kit feature spec supersedes a specific slice of it.

Current implementation status after merged feature slices:

- `docs/current-product-status.md`

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

- system-audio-first macOS MVP;
- virtual-driver routing is not required for MVP acceptance;
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
- system audio, microphone capture, audio driver, or routing;
- local buffering;
- upload/retry semantics;
- MediaScribe, Langfuse, MinIO, Postgres, Temporal, or Docker;
- auth, sessions, devices, permissions, audit, retention, deletion, or privacy;
- UX for tray/widget/onboarding/delete/admin states.

The command asks up to 5 targeted questions and writes accepted answers back into `spec.md`.

For clean-gate behavior, treat `clarify` as iterative when quality feedback exists:

- If `clarify` finds unresolved ambiguity, re-run `clarify` after the user provides answers and before the next transition to plan/checklist/analyze.

### 3. Plan

Use `$speckit-plan` after the spec is clear.

The plan must:

- run the constitution check;
- resolve technical unknowns in `research.md`;
- define the implementation approach in `plan.md`;
- create `data-model.md` where data is involved;
- create `contracts/` for APIs, capture/session protocols, future driver IPC,
  or UI contracts;
- create `quickstart.md` with validation scenarios;
- update this `AGENTS.md` plan reference between the Spec Kit markers.

Planning must stop if constitution gates fail or important clarifications remain unresolved.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
at specs/030-mvp-experience-design-system/plan.md
<!-- SPECKIT END -->

### 4. Checklist

Use `$speckit-checklist` after planning for high-risk areas. These checklists are "unit tests for English": they validate the quality of requirements, not the implementation.

Default checklist set for this project:

- `security.md` for auth, secrets, egress, audit, retention, deletion, diagnostics.
- `audio-capture.md` for macOS system audio, microphone permissions, track
  truth, performance, and QA matrix.
- `driver.md` only when a feature touches future macOS virtual audio,
  installer, passthrough, repair, or driver QA.
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

Mandatory quality re-check loop:

- Run `$speckit-analyze`.
- If analysis returns critical findings, unresolved high findings, or explicit clarification gaps, update `spec.md`, `plan.md`, or `tasks.md`.
- Re-run `$speckit-clarify` when ambiguity is the root cause, then re-run `$speckit-checklist` for affected areas.
- Re-run `$speckit-analyze`.
- Repeat until one full pass produces no unresolved critical issues and no blocking clarification requests.
- `implement` is blocked until this loop is clean.

This loop is not fully automatable today because `$speckit-clarify` depends on user decisions and domain answers. We can automate only the deterministic re-run cadence and commit checkpoints, but human confirmation remains mandatory.

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

### 8. Required GitHub Issue Sync

Use `$speckit-taskstoissues` for every implementation feature slice after planning and analysis:

- the repository remote is a GitHub URL;
- `tasks.md` exists with executable tasks;
- the implementation stage is not skipped by explicit user instruction.

Never create issues in a repository that does not match the configured git remote.

All GitHub issues created for this repository, whether manually, through
`$speckit-taskstoissues`, or through direct `gh issue create`, must follow the
project issue canon in `docs/github-issue-canon.md`.

Required issue title format:

```text
[<feature>][<priority>][<area>] <imperative outcome>
```

Required issue body sections, in order:

- `Summary`
- `Context`
- `Problem`
- `Confirmed Findings`
- `Scope`
- `Acceptance Criteria`
- `Validation Required`
- `Implementation Notes`
- `Links`

Spec Kit issue sync must preserve traceability to feature number, task IDs,
validation evidence, and closure criteria. Use labels as structured metadata:
`feature:<number>`, `priority:P0`-`priority:P3`, `area:<name>`,
`gate:<name>`, and `type:<name>`. Do not patch globally installed Spec Kit
skills to enforce this; they may be overwritten by Spec Kit updates. Keep the
canonical rule in project-owned files: `AGENTS.md`,
`docs/github-issue-canon.md`, and `.github/ISSUE_TEMPLATE/`.


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
$speckit-taskstoissues
$speckit-implement
```

For very small documentation-only changes, the user may explicitly skip to direct editing, but code/product implementation must use the full sequence.

Mandatory commit checkpoints for this repo:

- `$speckit-constitution` -> create a commit for constitution updates
- `$speckit-specify` -> create a commit for `spec.md` changes
- `$speckit-clarify` -> create a commit for `spec.md` clarification output
- `$speckit-plan` -> create a commit for `plan.md`/supporting artifacts
- `$speckit-checklist` -> create a commit for checklist files
- `$speckit-tasks` -> create a commit for `tasks.md`
- `$speckit-analyze` -> create a commit for analyze output
- `$speckit-taskstoissues` -> create a commit for created/updated issue links and labels
- `$speckit-implement` -> commits are only for explicit implementation slices, only after approval and validation

## 9. Versioning And Changelog

This repo uses Semantic Versioning (`MAJOR.MINOR.PATCH`) for release tags.

- `MAJOR` — breaking behavioral or API compatibility changes.
- `MINOR` — new user-visible capabilities or reversible architecture additions with backward compatibility.
- `PATCH` — bug fixes, reliability work, documentation, and operational quality improvements.

Changelog rule:

- maintain `CHANGELOG.md` in the repository root.
- every implemented feature slice that changes behavior, architecture, UX, QA expectations,
  or release-readiness must be recorded in `CHANGELOG.md` before merge.
- keep entries grouped by:
  - `Added`
  - `Changed`
  - `Fixed`
  - `Security`
  - `Docs`
  - `Ops`
- follow Keep a Changelog style:
  - `## [Unreleased]`
  - release headings by version (`## [x.y.z] - YYYY-MM-DD`)
  - include feature/task references (`feature:XYZ`, issue IDs, task IDs) in bullets.

Release gate for this repo:

- for pre-release evidence, update `CHANGELOG.md` in `[Unreleased]`.
- for release, run `./scripts/prepare-release.sh <bump>` to move `[Unreleased]`
  entries into a version section, set `vX.Y.Z` tag in Git, and push tags with
  the release branch.
- `release` tag format: `vMAJOR.MINOR.PATCH`.

Release workflow commands:

```sh
./scripts/prepare-release.sh patch|minor|major
git add CHANGELOG.md
git commit -m "chore: prepare release vX.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin HEAD --tags
```

## Git And Hooks

The Spec Kit git extension is installed in `.specify/extensions/git/`.

Behavior:

- before `$speckit-specify`, the git hook creates a feature branch;
- before/after many commands, auto-commit hooks are controlled by
  `.specify/extensions/git/git-config.yml`;
- in this repo, auto-commit is enabled for these post-commands by default:
  `after_constitution`, `after_specify`, `after_clarify`, `after_plan`,
  `after_checklist`, `after_tasks`, `after_analyze`, and `after_taskstoissues`.

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
- `AGENTS.md`
- `specs/` once features are created

Codex skill files are installed globally by the current Spec Kit bootstrap and
are not expected to be committed under repo-local `.agents/skills/`.

Keep generated build/cache/secret files out of git through `.gitignore`.

## Product-Specific Gates

Any feature touching `2brain Rec` capture, transcription, storage, or AI must preserve these gates:

- macOS system-audio-first MVP; virtual-driver routing is not required for MVP
  recording acceptance.
- Capture-critical implementation is platform-native by default: macOS feature
  slices use macOS-native languages and APIs, with future platforms handled by
  separate native stacks and separate architecture decisions.
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
specify version
specify self check
specify integration list
specify extension list
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
./scripts/prepare-release.sh patch
```

<!-- SPECKIT LINEAR START -->
## Правила работы с Linear

Используй Linear как ежедневную доску проекта для Spec Kit-фич, если доступна
интеграция Linear или API-ключи.

Обязательный поток:

- После `$speckit-tasks` убедись, что каждая исполняемая задача может быть
  связана с внешним issue.
- После `$speckit-taskstoissues` автоматически синхронизируй фичу в Linear через
  `$speckit-linear-sync` или проектный скрипт синхронизации Linear, если он
  доступен.
- Не создавай вручную дубли Linear issues. Сначала импортируй или сопоставь
  существующие задачи по номеру фичи, task ID, ссылке на GitHub issue и
  заголовку.
- `tasks.md` остается источником правды по реализации. Linear используется как
  рабочая доска для статуса, приоритета, цикла, владельца, комментариев,
  блокеров и общего трекинга проекта.
- Когда задача отмечена `[X]` в `tasks.md`, закрой или переведи в Done
  соответствующие GitHub и Linear issues, затем добавь короткий комментарий с
  доказательством выполнения.
- Если Linear показывает задачу как Done, но в `tasks.md` она еще открыта, не
  отмечай ее выполненной молча. Сначала проверь реализацию и evidence.
- Используй Linear projects для feature slices, cycles для рабочих периодов,
  labels для feature/task/area/gate metadata, priorities для срочности user
  stories, relations для блокировок и comments для коротких статус-апдейтов.
- Называй Linear projects с контекстом продукта и фичи, например
  `2brain Rec / 013 Federated Auth Foundation`, чтобы задачи разных продуктов
  не смешивались на одной доске.
- Если автоматизация Linear недоступна, зафиксируй отсутствие синхронизации как
  blocker или follow-up, а не создавай неотслеживаемую работу.

Правила языка и понятности:

- Все GitHub issues, Linear issues, комментарии к issues, комментарии в Linear,
  project updates и sync notes по умолчанию должны быть написаны на русском.
- Пиши простым и понятным языком, чтобы текст был ясен не только техническим
  специалистам, но и обычным участникам проекта.
- Предпочитай короткие предложения, конкретный результат и понятные критерии
  приемки.
- Избегай лишнего жаргона, внутренних сокращений и деталей реализации, если они
  не нужны исполнителю для безопасной работы.
- Блокеры объясняй как простые факты: что заблокировано, почему заблокировано и
  какое точное решение или действие разблокирует работу.
<!-- SPECKIT LINEAR END -->
