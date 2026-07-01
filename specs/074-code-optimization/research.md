# Research: Code Optimization

## Decision 1: Deletion-first, not split-first

**Decision**: Count optimization by runtime LOC/dependency reduction and
behavior preservation, not by smaller individual files.

**Rationale**: PR #2571 made one file smaller but increased runtime Python LOC.
That improved local readability but did not satisfy the product owner's
optimization goal.

**Alternatives considered**:

- Continue splitting large files: rejected because it can increase total runtime
  code and review overhead.
- Rewrite large modules: rejected because it hides behavior changes in a broad
  diff.

## Decision 2: Evidence before deletion

**Decision**: Every removed candidate needs caller/import/runtime evidence.

**Rationale**: Crisp has dynamic entrypoints through routes, templates, scripts,
Docker, SwiftPM, tests, and production runtime configuration. A narrow static
scan is not enough.

**Alternatives considered**:

- Delete anything with no direct `rg` caller: rejected because routes, scripts,
  and packaging can reference symbols indirectly.
- Keep all suspicious code: rejected because it prevents real optimization.

## Decision 3: First batch must be small

**Decision**: The first 074 implementation batch must target one narrow surface
and finish with net runtime LOC delta <= 0.

**Rationale**: Small deletion batches are reviewable and make regressions easier
to isolate.

**Alternatives considered**:

- Repo-wide cleanup PR: rejected because it mixes unrelated risk surfaces.
- Docs-only audit: rejected because the user asked for product improvement, not
  only planning.

## Decision 4: No new cleanup dependency

**Decision**: Use existing tools, `rg`, project tests, and small stdlib scripts
for evidence gathering.

**Rationale**: Adding a dependency to remove code is the wrong direction unless
the repo already owns it.

**Alternatives considered**:

- Add a dead-code tool dependency: rejected for this slice; one-off stdlib
  scripts and direct evidence are enough.
