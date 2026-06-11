# Feature Specification: Desktop Upload Queue and Resilient Upload Behavior for Local Recordings

**Feature Branch**: `027-desktop-upload-resilience`

**Created**: 2026-06-11

**Status**: Draft

**Input**: User description: "Desktop upload queue and resilient upload behavior for local recordings"

## Actors and User Goals *(mandatory)*

- **Local Meeting Owner**: needs predictable upload completion for local recordings they control.
- **MacOS Operator**: needs clear, truthful upload state to act without guessing whether local data is safe.
- **Security/Privacy Owner**: needs egress and lifecycle evidence for upload reliability and deletion truth.
- **Support/Operations Owner**: needs reproducible indicators for retry, blocking, and terminal failure states.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatically queue every finalized local recording (Priority: P1)

As a local owner, I want every completed local recording package to appear in an upload queue so no finished meeting is silently lost.

**Why this priority**: Without durable queueing, capture-to-upload is unreliable and cannot be trusted as a backup path for owner-controlled processing.

**Independent Test**: Create one local recording, stop it, then close and reopen the app. Verify the recording appears in the upload queue automatically without manual action.

**Acceptance Scenarios**:

1. **Given** capture finalization succeeds, **when** the recording is marked complete, **then** a queue item is created for that package identity.
2. **Given** the app restarts before upload completes, **when** local state loads, **then** the non-terminal item remains visible in the queue.

---

### User Story 2 - Expose resilient upload truth during failures (Priority: P1)

As an operator, I want to see upload states that distinguish recoverable from terminal problems so I can decide when to wait, retry, or take manual action.

**Why this priority**: Reliable operation depends on truthful state, not hidden failure states.

**Independent Test**: Simulate interrupted network connectivity during upload and confirm state transitions stay recoverable and visible instead of disappearing.

**Acceptance Scenarios**:

1. **Given** upload is in progress, **when** a transient failure happens, **then** the item moves to a recoverable retry state and retains reason metadata.
2. **Given** connectivity is restored, **when** retry conditions are met, **then** the item returns to an active upload/recovery path and remains visible.
3. **Given** retry is no longer possible automatically, **when** conditions require human action, **then** the item indicates manual recovery is required.

---

### User Story 3 - Preserve data during recovery windows (Priority: P1)

As a local owner, I want recording files to remain available while upload truth is unresolved so a transient failure does not cause silent deletion.

**Why this priority**: Deletion decisions depend on upload truth; local data must not disappear while truth is uncertain.

**Independent Test**: Leave an item in retryable state through app restarts and verify local artifacts remain available.

**Acceptance Scenarios**:

1. **Given** upload is retrying or degraded, **when** the app restarts, **then** both queue entry and source artifacts are still discoverable.
2. **Given** an item transitions to terminal failure, **when** user takes explicit action, **then** retention decision and terminalization are visible and auditable.

---

### User Story 4 - Avoid duplicate acceptance on repeated failures (Priority: P2)

As a meeting owner, I want repeated transfer attempts not to create duplicate finalized items so my storage and evidence remain consistent.

**Why this priority**: Duplicate completion creates trust and operational ambiguity across retention and deletion.

**Independent Test**: Simulate repeated partial failures and resume attempts for one package; verify no duplicate terminal completion is created.

**Acceptance Scenarios**:

1. **Given** a transfer is retried, **when** the same package is processed multiple times, **then** it is treated as one queue identity.
2. **Given** server evidence accepts prior segments, **when** new attempts occur, **then** upload does not mark the package as newly duplicated completed.

---

### User Story 5 - Keep upload logic aligned with platform and security gates (Priority: P2)

As a security owner, I want upload behavior to stay inside owner-controlled boundaries and not introduce new secret paths.

**Why this priority**: This product’s trust model depends on strict ownership, transparency, and boundary safety.

**Independent Test**: Validate upload traces and diagnostics for evidence boundaries and absence of unexpected third-party credentials.

**Acceptance Scenarios**:

1. **Given** uploads run through local queue, **when** diagnostics are exported, **then** traces show upload state and failure reasons without raw credentials.
2. **Given** local capture indicator remains active, **when** upload work progresses, **then** visible capture control is unchanged and one-action stop remains available.

## Edge Cases and Failure States *(mandatory)*

- No network during startup.
- Network drop and restore while items are active.
- Authentication/session expiration during upload.
- Repeated schema or manifest mismatch across retries.
- Partial acceptance evidence exists and queue resumes from missing parts.
- Local disk quota exhaustion while retaining recoverable items.
- Manual retry action while background retry loop is already active.
- App crash during queue state mutation.
- Two upload pathways processing same package identity.
- Retention deadline reached while item still needs upload truth.

Failure classification must be explicit in queue state:

- recoverable retrying,
- recoverable blocked (manual action required),
- terminal failed,
- terminal completed,
- terminal deleted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST create a queue item for each finalized local recording package automatically.
- **FR-002**: Every queue item MUST preserve package identity so the same recording is represented once across restarts.
- **FR-003**: Queue visibility MUST include truthful status for pending, uploading, retrying, degraded, failed, blocked, completed, and terminal deleted states.
- **FR-004**: New non-terminal items MUST appear in queue state within 30 seconds of finalization or app launch.
- **FR-005**: Queue state for non-terminal items MUST survive app restart and OS interruption.
- **FR-006**: Retry behavior MUST be persistent, bounded, and explicit about reason categories.
- **FR-007**: The app MUST not report terminal completed without sufficient evidence that required package content has been accepted.
- **FR-008**: Recoverable failures MUST not silently drop or delete local artifacts while recovery remains possible.
- **FR-009**: The queue MUST provide a user-visible manual recovery action for blocked recoverable items.
- **FR-010**: The app MUST tolerate duplicate in-flight attempts for the same package without duplicate terminalization.
- **FR-011**: The queue must retain one authoritative truth for required tracks and required acceptance checks.
- **FR-012**: The app MUST classify failures into at least: connectivity, permission/session, schema/manifest mismatch, storage constraints, and remote validation classes.
- **FR-013**: The app MUST keep local data discoverable while upload truth remains non-terminal.
- **FR-014**: The queue workflow MUST emit deletion/accounting evidence for successful completion, blocked terminal states, and local retention outcomes.
- **FR-015**: Queue design MUST not introduce direct audio upload from desktop directly to third-party STT services.
- **FR-016**: Queue behavior MUST not alter manual start/stop capture rules or visible capture indicator semantics.
- **FR-017**: Queue scheduling and state transitions MUST never regress a terminal truth into a non-terminal truth.
- **FR-018**: The system MUST keep visible evidence of whether a blocked state is temporary versus permanently terminal.

### Key Entities *(include if feature involves data)*

- **UploadQueueItem**: Durable representation of one local meeting package in upload workflow.
- **UploadState**: Truth model for visible queue states and terminality.
- **RetryOutcome**: Evidence of retry attempts, failure categories, and recovery outcomes.
- **LocalArtifactLink**: Trace that links queue item to local package files and required tracks.
- **UploadTruthReceipt**: Read-only indicator of what external systems have accepted for the package.
- **RetentionDecision**: Record of terminalization choice, policy decision, and deletion evidence.

## Out of Scope *(mandatory)*

- Server-side transcription algorithm changes.
- Meeting transcription UI and search UX changes.
- Virtual audio routing and driver installer/repair workflows.
- New authentication method design.
- Full rebuild of backend storage layout.
- Global redesign of desktop branding and shell.

## Dependencies *(mandatory)*

- Existing local recording finalization and package identity contracts.
- Existing queue persistence and retention/deletion accounting foundations.
- Existing approved ingest path and acceptance contract with owner-controlled infrastructure.
- Existing diagnostics redaction and secret-disclosure controls.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid finalized local recordings create a queue item within 30 seconds.
- **SC-002**: 100% of non-terminal queue items reappear with the same identity after app restart.
- **SC-003**: 95% of transient connectivity failures recover into active upload state without manual intervention within 2 minutes of restoration.
- **SC-004**: 99% of retried recovery sessions avoid duplicate terminal success for the same queue identity.
- **SC-005**: 100% of retrying/degraded non-terminal items keep required local files until explicit terminal decision.
- **SC-006**: 100% of terminal outcomes include a visible terminality reason and next-step category.
- **SC-007**: 90% of operators in recovery drills can identify recoverable vs blocked states from queue UI without support.
- **SC-008**: 0% of queue terminal outcomes or diagnostics include raw credentials, upload tokens, or secret material.
- **SC-009**: 0% of completed queue items are marked terminal when required tracks are not accepted.
- **SC-010**: No regression in visible capture indicator and one-action stop behavior during queue recovery activity.

## Assumptions

- Upload acceptance is based on owner-controlled ingest path and existing package validity semantics.
- Recovery windows and retry limits are aligned with owner retention and governance policy.
- Backend accepts progress-aware recovery behavior for large local recordings.
- Existing diagnostics/log policy excludes secrets and content by default.
- Local storage capacity and deletion policy define maximum safe retention during prolonged recovery windows.
