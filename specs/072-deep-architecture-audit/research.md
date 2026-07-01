# Research: Deep Architecture Audit

## Scope Decision

**Decision**: Run 072 from a clean disposable worktree based on fresh
`origin/master`, not from the stale canonical checkout branch.

**Rationale**: The canonical checkout exists at
`/Users/yshishenya/Documents/crisp`, but its active branch has no live upstream.
The user allowed either the canonical checkout or a clean worktree from fresh
`origin/master`. A clean worktree avoids stale branch state and prevents 071 or
other local work from bleeding into 072.

**Alternatives considered**:

- Use `/Users/yshishenya/Documents/crisp` directly: rejected because its current
  branch is stale even though the worktree is clean.
- Use the starting Codex worktree: rejected because the request explicitly
  required canonical checkout or clean fresh worktree.

## Audit Shape Decision

**Decision**: Produce documentation artifacts only in the first 072 stage:
`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`,
`quickstart.md`, `tasks.md`, and audit docs under `audit/`.

**Rationale**: The user explicitly asked for no code changes, no deletion, and
no production deploy in stage one. This keeps the audit reviewable and lets
later refactors be independently validated.

**Alternatives considered**:

- Create a graphing tool or generated dependency database: rejected for stage
  one because existing `rg`, AST parsing, Swift package inspection, and script
  inspection are enough.
- Start refactoring obvious large files immediately: rejected because size alone
  is not caller/runtime evidence.

## Evidence Collection Decision

**Decision**: Use existing repository surfaces and lightweight static analysis
for evidence: file inventory, line counts, AST import roots, Swift Package
targets, script call references, Docker/Compose entrypoints, product docs,
ADRs, and Spec Kit artifacts.

**Rationale**: Ponytail prefers the smallest sufficient path. The current
evidence need is to classify risks and plan validation, not to prove changed
runtime behavior.

**Alternatives considered**:

- Add third-party dependency graph tooling: rejected unless a future slice shows
  local tools cannot answer a specific question.
- Run production smoke/deploy: rejected by the 072 release gate.

## Dependency Interpretation Decision

**Decision**: Treat dependencies with no direct source import as
`keep intentionally` until runtime role evidence disproves them.

**Rationale**: Some Python dependencies are runtime adapters or CLI/runtime
launch requirements rather than direct imports. Examples include `asyncpg`
for SQLAlchemy Postgres URLs, `uvicorn[standard]` for the container command,
`python-multipart` for FastAPI form/file parsing, `aiosqlite` for test
database URLs, and `ruff` for local CI.

**Alternatives considered**:

- Mark zero-import dependencies as delete candidates: rejected because it would
  create false-positive cleanup risk.

## Refactor Roadmap Decision

**Decision**: Future work is grouped into small PR batches by boundary, not by
global architecture rewrite.

**Rationale**: The product has safety-critical boundaries around capture,
privacy, deletion, auth, MediaScribe, Temporal, and deploy. Small batches let
each PR carry focused evidence and rollback reasoning.

**Alternatives considered**:

- One large architecture PR: rejected because it would mix unrelated risks and
  make validation weak.
- Delete-first cleanup: rejected because the first stage must not delete code
  and because apparent dead code may encode safety or deployment contracts.

## 071 Separation Decision

**Decision**: 072 may read current repository state but must not treat 071
classification, release notes, or branch context as 072 evidence unless the
fact is revalidated in this slice.

**Rationale**: The user explicitly said not to mix 072 with release 071.

**Alternatives considered**:

- Reuse 071 audit output wholesale: rejected because it would weaken 072's
  evidence map and confuse release boundaries.

