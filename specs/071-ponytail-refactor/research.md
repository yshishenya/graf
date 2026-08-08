# Research: Ponytail Refactor Audit

## Decision: Use Evidence-First Cleanup Batches

**Rationale**: The repository includes high-risk auth, capture, deletion, storage, diagnostics, deployment, and macOS code. A single repo-wide rewrite would make regressions hard to locate. Small batches allow focused validation and a clean stop point after each change.

**Alternatives considered**:
- One giant cleanup patch: rejected because it hides causal links between deletion and regression.
- Read-only audit only: rejected because the user asked to fix proven bloat.

## Decision: Treat Framework And Runtime Entrypoints As Used Until Proven Otherwise

**Rationale**: FastAPI route signatures, provider adapter method signatures, Alembic side-effect imports, Jinja templates, static assets, Docker commands, CLI dependencies, database drivers, and pytest plugins can be used without direct source imports.

**Alternatives considered**:
- Delete every unused static-analysis hit: rejected because it would break framework entrypoints and protocol contracts.
- Keep every suspicious item: rejected because proven unused parameters/dependencies can still be safely removed.

## Decision: Dependency Removal Requires Static And Runtime Evidence

**Rationale**: Direct import search is not enough for packages such as ASGI servers, form parsers, database drivers, pytest plugins, and Docker runtime components. Removal requires no direct usage, no known runtime/CLI role, lockfile update, and passing validation.

**Alternatives considered**:
- Trust import graph only: rejected as unsafe for this stack.
- Never remove dependencies: rejected because `structlog` has already been proven removable in Batch A.

## Decision: Keep Cabinet Presentation Split Separate From API/Service Refactors

**Rationale**: Previous backend review found `cabinet/web.py` is an oversized presentation layer while domain boundaries already exist in adjacent modules. A safe split should stay presentation-only and must not mix with API/service changes.

**Alternatives considered**:
- Split web, API, and service layers together: rejected as too broad for a cleanup batch.
- Ignore `cabinet/web.py`: rejected because it remains a clear maintainability target.

## Decision: Historical Specs And Evidence Are Read-Only By Default

**Rationale**: The repository stores product evidence, QA screenshots, and historical specs as proof artifacts. Deleting them as "bloat" can destroy auditability. They should only be removed with an explicit source-of-truth replacement or duplicate proof.

**Alternatives considered**:
- Delete old screenshots and evidence for size: rejected because product validation depends on historical evidence.
- Include evidence cleanup in every batch: rejected because it would distract from runtime code safety.

## Kickoff Worktree Separation: 2026-06-30

The 071-owned work at kickoff is the new `specs/071-ponytail-refactor/` feature directory, the `.specify/feature.json` pointer, the `AGENTS.md` SPECKIT pointer update to this plan, and the already-present Batch A server cleanup under `apps/server/`.

Keep these pre-existing or generated dirty paths separate from cleanup evidence unless a later task explicitly scopes them:

- `.specify/extensions/agent-context/agent-context-config.yml`
- `.specify/templates/plan-template.md`
- `.specify/templates/tasks-template.md`
- `.agents/skills/speckit-*/SKILL.md`

Current prerequisite proof:

```text
SPECIFY_FEATURE_DIRECTORY=specs/071-ponytail-refactor .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
=> {"FEATURE_DIR":"<repo-root>/specs/071-ponytail-refactor","AVAILABLE_DOCS":["research.md","data-model.md","contracts/","quickstart.md","tasks.md"]}
```
