# Feature Specification: Code Optimization

**Feature Branch**: `codex/074-code-optimization`

**Created**: 2026-07-01

**Status**: Implemented cleanup batch; no deploy or product behavior change

**Input**: User description: "Наша цель не просто порезать код. Главная цель -
сделать его оптимальным, не раздуть, убрать мертвые функции и лишние строки,
доказательно оптимизировать продукт."

## Clarifications

### Session 2026-07-01

- Q: Is the goal file splitting or code optimization? -> A: The goal is product
  optimization: remove dead functions and unnecessary lines, shrink real runtime
  code, and avoid code growth.
- Q: Can code be deleted based on appearance? -> A: No. Every deletion needs
  caller/import/runtime evidence and validation.
- Q: Should this slice deploy to production? -> A: No production deploy without
  a separate request.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Remove Proven Dead Runtime Code (Priority: P1)

As the product owner, I want dead functions, unused helpers, stale wrappers, and
unneeded runtime lines removed only when there is direct evidence they are not
part of any active product flow, so that the codebase gets smaller without
breaking capture, cabinet, auth, deletion, processing, desktop, or deployment.

**Why this priority**: This corrects the 073 failure mode: moving code is not
optimization unless the runtime surface becomes smaller or simpler.

**Independent Test**: A deletion batch is accepted only when it shows caller,
import, route, script, or runtime evidence for every removed symbol and passes
the focused tests for the affected product surface.

**Acceptance Scenarios**:

1. **Given** a function or helper appears unused, **When** the cleanup batch is
   prepared, **Then** the batch records the searches and runtime entrypoints
   proving there are no active callers before removing it.
2. **Given** a candidate touches a high-risk boundary, **When** evidence is
   incomplete, **Then** the candidate is classified as "keep intentionally" or
   "risky / needs spec" instead of being removed.

---

### User Story 2 - Shrink Duplicate Or Redundant Code (Priority: P1)

As a maintainer, I want duplicate branches, redundant wrappers, and repeated
boilerplate shrunk in place when one existing pattern already covers the same
behavior, so that future changes are easier and the runtime code count does not
grow.

**Why this priority**: A smaller codebase is safer only when the same behavior
is expressed with fewer moving parts.

**Independent Test**: A shrink batch is accepted only when the before/after
behavior remains covered by existing or focused tests and the batch reports net
runtime line impact.

**Acceptance Scenarios**:

1. **Given** two blocks express the same behavior, **When** one can reuse an
   existing helper without changing the contract, **Then** the duplicate block is
   removed and the existing tests still pass.
2. **Given** a shrink would require a new abstraction with one caller, **When**
   the simpler local expression is available, **Then** the abstraction is not
   introduced.

---

### User Story 3 - Keep Cleanup Auditable And Small (Priority: P2)

As a reviewer, I want every cleanup batch to be small, measurable, and easy to
review, so that optimization does not become a risky rewrite.

**Why this priority**: Large cleanup diffs hide behavioral changes and make
regression review unreliable.

**Independent Test**: Each PR states what was removed or shrunk, what was
intentionally kept, what was not touched, and which checks prove safety.

**Acceptance Scenarios**:

1. **Given** a cleanup candidate cannot be proven safe in one small PR, **When**
   tasks are planned, **Then** it is split into a later batch or separate Spec Kit
   slice.
2. **Given** a PR changes runtime code, **When** it is ready for review, **Then**
   it reports net runtime LOC/dependency impact and validation evidence.

### Edge Cases

- A symbol is referenced dynamically by route registration, CLI import, shell
  script, migration, template, or macOS build configuration.
- A function has no direct Python caller but is used by tests as a contract or by
  external HTTP/API behavior.
- A dependency appears unused in source scans but is required by packaging,
  Docker, optional runtime integrations, or generated lock/constraints files.
- A cleanup candidate lives near auth/session, privacy, deletion/retention,
  capture, MediaScribe, Langfuse, MinIO, Postgres, Temporal, desktop WebView, or
  deploy boundaries.
- A proposed shrink reduces file count but increases runtime lines or creates a
  new one-off abstraction.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every deletion or shrink batch MUST start from a candidate list
  with evidence for each candidate's current callers, imports, routes, scripts,
  tests, templates, and runtime entrypoints.
- **FR-002**: The implementation MUST classify each candidate as `delete now`,
  `shrink now`, `keep intentionally`, or `risky / needs spec` before code is
  removed.
- **FR-003**: The implementation MUST NOT remove code based only on naming,
  apparent age, file size, or a single narrow search result.
- **FR-004**: The implementation MUST NOT move or split code unless the same
  batch also removes duplicate/dead runtime code or clearly reduces net runtime
  lines.
- **FR-005**: Each accepted batch MUST report net runtime line impact and
  dependency impact separately from Spec Kit documentation line impact.
- **FR-006**: Each accepted batch MUST preserve existing product behavior,
  security boundaries, validation, and user-visible copy unless a separate spec
  explicitly changes them.
- **FR-007**: Cleanup near high-risk boundaries MUST keep existing guardrails for
  auth/session/device, privacy, deletion/retention, MediaScribe, Langfuse,
  MinIO/Postgres/Temporal, capture, desktop WebView, and deploy paths.
- **FR-008**: Tests MUST NOT be weakened or deleted unless there is explicit
  evidence that the tested contract no longer exists and the product owner
  accepts that scope.
- **FR-009**: A candidate with incomplete evidence MUST be retained and recorded
  as intentional or risky instead of removed.
- **FR-010**: Production deploy MUST NOT be performed for this cleanup slice
  without a separate release/deploy request.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The first implementation PR has a net runtime code line delta of
  zero or lower, excluding Spec Kit/docs/checklist files.
- **SC-002**: The first implementation PR removes or shrinks at least one
  evidence-backed runtime candidate without adding a new dependency.
- **SC-003**: Every removed symbol in the first PR has recorded caller/import or
  runtime-entrypoint evidence in the audit notes or PR.
- **SC-004**: Focused tests for the touched surface pass, and the repository
  local gate passes before closeout when shared runtime code changed.
- **SC-005**: The PR explicitly lists any inspected candidates that were kept
  intentionally or deferred as risky.

## Assumptions

- This slice starts from fresh `origin/master` after 073 and later merged work.
- The initial implementation batch should be small and deletion-first, not a
  broad repo rewrite.
- Spec Kit artifacts are expected to add documentation lines; runtime LOC and
  dependency impact are the product optimization metrics.
- The active product behavior remains the source of truth. Cleanup does not
  change scope, deploy, retention, auth, capture, or support behavior.
