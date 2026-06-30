# Feature Specification: Ponytail Refactor Audit

**Feature Branch**: `codex/071-ponytail-refactor`

**Created**: 2026-06-30

**Status**: Draft

**Input**: User description: "071 - go through all code line by line with Ponytail, check redundancy, then safely remove unused bloat without breaking anything. Study every line and dependency and produce a refactor plan."

## Clarifications

### Session 2026-06-30

- Default scope: the audit covers repository code, scripts, tests, and declared dependencies; generated evidence, historical specs, release artifacts, binary assets, and product screenshots are read only unless a file is proven to be a duplicate or obsolete by an existing source-of-truth reference.
- Safety rule: no refactor batch may change user-visible behavior, auth/security boundaries, capture/deletion/privacy guarantees, deployment semantics, or data contracts unless a dedicated task, focused validation, and rollback note exist.
- Dependency rule: a dependency may be removed only when static usage, runtime/CLI role, lockfile, and focused validation all show it is unused.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preserve A Safe Cleanup Baseline (Priority: P1)

A maintainer reviews a small already-validated cleanup batch and can see exactly what was removed, why it was safe, and which gates proved behavior still works.

**Why this priority**: The repository already has a small Ponytail cleanup diff. Capturing it as a bounded baseline prevents a large audit from mixing proven cleanup with speculative edits.

**Independent Test**: Can be tested by reviewing the cleanup diff and running the documented validation commands; the batch delivers value even if later audit batches are deferred.

**Acceptance Scenarios**:

1. **Given** the current 071 cleanup diff exists, **When** the maintainer reviews the batch, **Then** every changed file has a deletion or simplification rationale and no unrelated Spec Kit/template noise is included.
2. **Given** the cleanup batch removes a dependency or parameter, **When** validation is reviewed, **Then** the result includes dependency evidence, focused tests, and repository gates.

---

### User Story 2 - Audit Dependencies And Dead Code Before Editing (Priority: P2)

A maintainer receives a repo-wide Ponytail audit that separates proven removal candidates from items that only look unused because they are entrypoints, framework hooks, compatibility paths, or safety tests.

**Why this priority**: Blind deletion across auth, capture, storage, deployment, and macOS code can break critical behavior. The audit must prove each candidate before a patch is made.

**Independent Test**: Can be tested by running the audit commands and confirming each candidate records source evidence, caller evidence, and a validation lane before implementation.

**Acceptance Scenarios**:

1. **Given** a declared dependency has no direct import, **When** the audit classifies it, **Then** CLI, plugin, framework, driver, and runtime-only usage are checked before any removal is proposed.
2. **Given** a function parameter is unused by local code, **When** the audit classifies it, **Then** route, adapter, protocol, template, migration, and framework signature roles are checked before deletion.
3. **Given** a large file or module appears bloated, **When** the audit reports it, **Then** the report distinguishes "safe to delete now" from "needs a dedicated split plan".

---

### User Story 3 - Execute Small Refactor Batches With Proof (Priority: P3)

A maintainer applies one cleanup batch at a time and can stop after any batch with the repository in a validated state.

**Why this priority**: Incremental batches keep the blast radius small and make regressions easy to locate.

**Independent Test**: Can be tested by applying a single batch, running focused validation, then running the repository gate before marking the batch complete.

**Acceptance Scenarios**:

1. **Given** a candidate is approved for removal, **When** the batch is implemented, **Then** only the minimal files necessary for that removal are changed.
2. **Given** a batch touches server code, **When** validation runs, **Then** focused tests and `infra/scripts/ci-local.sh` pass before completion.
3. **Given** a batch touches macOS code, **When** validation runs, **Then** focused Swift tests and `swift test --package-path apps/macos` pass before completion.

### Edge Cases

- A file is referenced only by a shell script, Docker entrypoint, template include, migration side effect, package manifest, or binary/resource loader.
- A test looks redundant but is the only coverage for privacy, deletion truth, capture visibility, auth, or deployment hardening.
- A dependency is not imported directly because it is a database driver, ASGI/CLI entrypoint, FastAPI parser dependency, test plugin, or Docker runtime component.
- A large module is maintainable only through a dedicated split plan rather than a same-batch deletion.
- Existing dirty worktree files are unrelated to 071 and must not be reverted, restaged, or silently mixed into cleanup evidence.
- A cleanup candidate is valid locally but has no focused test; the batch must add or identify the smallest existing runnable check before completion.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST classify the work as a significant/high-risk cleanup lane and preserve the stricter Spec Kit gates before implementation.
- **FR-002**: The feature MUST maintain an audit inventory of code files, scripts, tests, dependencies, entrypoints, and declared package targets before additional cleanup patches are made.
- **FR-003**: The feature MUST record a deletion or simplification rationale for every changed runtime, test, script, dependency, or documentation artifact.
- **FR-004**: The feature MUST keep unrelated dirty worktree changes separate from 071 cleanup batches and must not revert user or generated changes that are outside the batch.
- **FR-005**: The feature MUST require at least two independent evidence signals before deleting a dependency or file: source/caller evidence and validation evidence.
- **FR-006**: The feature MUST preserve auth, session, permission, audit, retention, deletion, privacy, diagnostics, capture, upload, storage, deployment, and UI accessibility gates.
- **FR-007**: The feature MUST treat framework entrypoints, protocol signatures, adapter contracts, migration side-effect imports, template includes, static assets, CLI commands, and Docker service references as in use unless proven otherwise.
- **FR-008**: The feature MUST execute cleanup in independently reviewable batches that can pass validation before the next batch starts.
- **FR-009**: The feature MUST use Ponytail criteria to prefer deletion, existing helpers, standard library/native features, and already-installed dependencies over new abstractions or new packages.
- **FR-010**: The feature MUST NOT add new runtime dependencies, broad abstractions, new architecture layers, or speculative configuration as part of cleanup.
- **FR-011**: The feature MUST keep large architectural splits, such as cabinet presentation decomposition, separate from API/service refactors unless a later task explicitly scopes that work.
- **FR-012**: The feature MUST update lockfiles when dependencies change and prove the lockfile update is limited to the dependency decision.
- **FR-013**: The feature MUST run focused validation for each touched domain and the repository validation gate before calling a batch complete.
- **FR-014**: The feature MUST leave an explicit "not removed" note for high-risk candidates that appear unused but are retained because their safety evidence is insufficient.

### Key Entities

- **Audit Candidate**: A potential deletion or simplification with location, tag, evidence, risk domain, decision, and validation requirement.
- **Cleanup Batch**: A small set of related changes that can be reviewed and validated independently.
- **Dependency Record**: A declared package, tool, runtime image, or package target with usage evidence and a keep/remove decision.
- **Validation Evidence**: Focused and repository-level commands proving a batch did not break behavior.
- **Retained Candidate Note**: A recorded decision explaining why a suspicious item was not removed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of cleanup changes in a completed batch have an associated audit rationale and validation command.
- **SC-002**: 100% of removed dependencies have direct usage evidence, runtime/CLI exception review, lockfile update, and passing validation.
- **SC-003**: Every completed server-touching batch passes focused tests for changed domains and `infra/scripts/ci-local.sh`.
- **SC-004**: Every completed macOS-touching batch passes focused Swift validation and full `swift test --package-path apps/macos`.
- **SC-005**: No completed batch changes user-facing behavior, security/privacy posture, capture/deletion truth, deployment semantics, or data contracts without an explicit dedicated task and validation note.
- **SC-006**: The final closeout lists all retained high-risk candidates and explains why they were not removed.

## Assumptions

- Batch A is the existing small server cleanup already present in the worktree and already validated; later work will keep it reviewable as its own batch.
- The audit prioritizes source code, scripts, tests, and dependencies over historical evidence assets and generated screenshots.
- The repository's canonical local gate remains `infra/scripts/ci-local.sh`.
- Production deploy is out of scope for this cleanup slice.
- Git commits require explicit user approval after validation.
