# Feature Specification: Desktop Upload Custody Architecture

**Feature Branch**: `codex/086-desktop-upload-custody-architecture`

**Created**: 2026-07-03

**Status**: Read-only architecture audit complete; implementation planning remains separate

**Input**: User direction after 072/085 architecture refresh: stop chasing
small cabinet helper splits and move to the highest product-value architecture
node. First stage is read-only: map desktop upload custody, local purge,
support incident, and server ingest boundaries before any code refactor.

## Clarifications

### Session 2026-07-03

- Lane: significant architecture / high-risk read-only audit. This slice may
  create Spec Kit and audit documentation only; it must not change Swift,
  Python, schemas, dependency declarations, migrations, generated release
  files, or production state.
- Optimization goal: improve product architecture by reducing real custody and
  trust-boundary complexity. Do not split code merely to create more files.
- Ponytail rule: prefer deletion/simplification only with caller, runtime,
  entrypoint, validation, and rollback evidence. No `delete now` change is
  approved by this first stage.
- Scope: map the desktop local package to upload queue to server ingest to
  custody projection to deletion/local purge to support incident flow.
- Release rule: no production deploy and no release packaging for 086 unless a
  later explicit request opens a release/deploy lane.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See The Upload Custody Flow (Priority: P1)

A maintainer can understand how a completed local recording moves through the
desktop upload queue, server ingest, custody projection, local purge, and
support incident surfaces without reading every large Swift and Python file.

**Why this priority**: This flow owns the handoff from local recording truth to
server custody. If it is unclear, refactors can break upload retry, deletion
truth, or support evidence.

**Independent Test**: Review the 086 audit docs and confirm that each stage of
the flow names the owning component, exchanged state, trust boundary, existing
test evidence, and known uncertainty.

**Acceptance Scenarios**:

1. **Given** the current desktop upload files and server ingest/local purge
   endpoints, **When** the architecture map is reviewed, **Then** the reviewer
   can trace the flow from local package discovery to server review readiness.
2. **Given** a local purge acknowledgement or support incident touches meeting
   content lifecycle, **When** the map describes it, **Then** the map states the
   metadata-only and deletion-truth boundaries before any refactor plan.
3. **Given** a large file appears to be a split target, **When** it is included
   in the map, **Then** the map distinguishes product-critical responsibility
   from incidental helper code.

---

### User Story 2 - Decide What To Split Or Keep (Priority: P1)

A maintainer can see which upload-custody responsibilities are safe candidates
for later small PRs, which must stay together for now, and which require a
separate Spec Kit slice before code changes.

**Why this priority**: The goal is optimization, not just code movement. Some
large code is legitimate custody or safety logic; moving it without a boundary
plan can make the product less reliable.

**Independent Test**: Review the findings and batch roadmap and confirm each
item is classified as `delete now`, `split soon`, `keep intentionally`, or
`risky / needs spec` with validation gates.

**Acceptance Scenarios**:

1. **Given** a helper, model, or DTO appears unused or oversized, **When** it is
   classified, **Then** the classification includes caller evidence and why it
   is or is not safe to delete.
2. **Given** upload queue, client, custody projection, local purge, or support
   responsibilities overlap, **When** a future split is proposed, **Then** the
   proposal names exactly one responsibility boundary and excludes behavior
   changes.
3. **Given** a proposed change touches deletion, support evidence, auth/device,
   server ingest, or capture package truth, **When** it enters the roadmap,
   **Then** the item is marked high-risk and includes focused validation before
   implementation.

---

### User Story 3 - Prepare Small Safe Refactor Batches (Priority: P1)

A maintainer can choose the next implementation PR from a roadmap that improves
reviewability while preserving upload, deletion, and support behavior.

**Why this priority**: The useful output is a sequence of small PRs with stop
conditions, not a rewrite of desktop upload.

**Independent Test**: Review the roadmap and confirm each batch has scope,
excluded surfaces, expected diff shape, validation gates, and rollback or stop
conditions.

**Acceptance Scenarios**:

1. **Given** the roadmap recommends a split, **When** the batch is read alone,
   **Then** it can be implemented and reviewed without also changing server
   ingest behavior, deletion behavior, or support reporting.
2. **Given** a batch would require API contract changes, **When** it is
   reviewed, **Then** it is deferred to a separate slice or includes explicit
   server contract checks.
3. **Given** a batch would reduce code, **When** it is selected, **Then** it has
   proof that removal does not weaken support, deletion, or retry evidence.

### Edge Cases

- A Swift type appears unused by static search but is encoded/decoded as part
  of queue persistence, support incident payloads, or API DTOs.
- A server endpoint appears unrelated to upload but participates in deletion
  local purge acknowledgement or support incident reporting.
- A refactor could change retry timing, idempotency keys, missing-range retry,
  local artifact deletion, or support report metadata.
- A diagnostic/support payload could accidentally include private local paths,
  tokens, signed URLs, transcript text, or raw audio metadata.
- A desktop-only change could still break a server contract if DTO shape,
  status vocabulary, or local purge acknowledgement semantics move.
- Full dynamic validation may require Swift tests and server contract checks,
  but this first stage stops at documentation and roadmap evidence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST record the lane as significant architecture /
  high-risk read-only audit and MUST prohibit runtime code changes, dependency
  changes, migrations, file deletion, and production deploy in stage one.
- **FR-002**: The feature MUST use `specs/086-desktop-upload-custody-architecture/`
  as the active Spec Kit slice and MUST NOT mix 086 artifacts with 071 release
  or earlier cabinet refactor slices.
- **FR-003**: The audit MUST map the flow from completed local recording
  package to desktop queue state, server upload/ingest, custody projection,
  local purge acknowledgement, support incident reporting, and cabinet/review
  visibility.
- **FR-004**: The audit MUST inspect the desktop upload queue service, upload
  client, custody projection, support incident UI/action surface, local purge
  DTOs, server ingest routes, deletion local purge routes, support incident
  server routes, and existing tests.
- **FR-005**: The audit MUST classify findings as `delete now`, `split soon`,
  `keep intentionally`, or `risky / needs spec`.
- **FR-006**: Any `delete now` candidate MUST include static caller evidence,
  runtime/entrypoint evidence, contract evidence, focused validation, and a
  rollback plan before any later deletion PR.
- **FR-007**: Any `split soon` candidate MUST define one smaller responsibility
  boundary, excluded behavior, expected diff shape, and validation gates.
- **FR-008**: Any `keep intentionally` item MUST explain the product, contract,
  persistence, support, deletion, or safety reason it stays.
- **FR-009**: Any `risky / needs spec` item MUST name the trust boundary and
  the separate slice or clarification required before implementation.
- **FR-010**: The roadmap MUST prioritize product-value optimization over file
  count reduction and MUST explicitly reject split-only work that does not
  reduce custody, deletion, support, or review risk.
- **FR-011**: The roadmap MUST name checks needed before each future refactor
  batch, including Swift tests, upload queue tests, local purge acknowledgement
  tests, support redaction checks, server ingest contract checks, and no-secret
  evidence scans where applicable.
- **FR-012**: The feature MUST preserve the boundaries that desktop never sends
  audio directly to MediaScribe, desktop never stores MediaScribe credentials,
  support evidence is metadata-only, and deletion wording remains truthful
  about what 2brain Rec controls.
- **FR-013**: The feature MUST produce `spec.md`, `plan.md`, `research.md`,
  `data-model.md`, `contracts/`, `quickstart.md`, `tasks.md`, audit docs, and a
  refactor roadmap before implementation is considered.
- **FR-014**: The final output MUST answer plainly what is healthy, what hurts,
  what can be safely deleted, what needs separate PRs, and what validation is
  required before each batch.

### Key Entities

- **Local Recording Package**: The completed local artifact set that the desktop
  app discovers, validates, and queues for upload.
- **Desktop Upload Queue Item**: The persisted desktop state for upload,
  retry, custody, support incident, and local purge decisions.
- **Desktop Upload Client Contract**: The desktop-to-server request/response
  surface for meeting creation, upload sessions, missing ranges, finalization,
  reconciliation, local purge tasks, and support incidents.
- **Custody Projection**: The user-facing and support-facing interpretation of
  whether local, server, processing, deletion, or support action owns the next
  step.
- **Local Purge Task**: The server-created deletion lifecycle task that the
  desktop acknowledges with metadata-only local deletion truth.
- **Support Incident Report**: A metadata-only support payload for custody and
  upload failures.
- **Refactor Batch**: A future behavior-preserving PR with one boundary, clear
  exclusions, required checks, and rollback conditions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of required upload-custody stages in FR-003 have an audit
  section with owner, state, trust boundary, existing evidence, and limits.
- **SC-002**: 100% of findings use one of the four required classifications
  and include validation or an explicit reason validation is deferred.
- **SC-003**: The roadmap contains only small PR batches, and each batch names
  scope, exclusions, checks, and stop conditions.
- **SC-004**: No product/runtime code files, dependency declarations, lockfiles,
  migrations, generated release files, or production state are changed by this
  first-stage audit.
- **SC-005**: The audit evidence contains no raw audio, transcript text,
  credentials, tokens, signed URLs, private local paths, or private meeting
  content.
- **SC-006**: The final report clearly distinguishes proven evidence from
  inference and answers the five plain-language architecture questions.

## Assumptions

- The 085 architecture refresh is the current priority input for this slice.
- Existing repository tools are enough for the first-stage evidence map; no new
  audit dependency is needed.
- Future implementation PRs may run Swift and server tests, but 086 stage one
  itself remains documentation and analysis only.
- GitHub issue sync and production deploy are out of scope unless explicitly
  requested later.
