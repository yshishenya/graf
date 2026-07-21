# Feature Specification: Desktop Upload Queue And Resilient Upload Behavior

**Feature Branch**: `014-desktop-upload-queue`

**Created**: 2026-06-11

**Status**: Historical desktop upload queue; custody behavior is superseded by 042/057

**Input**: User description: "Implement desktop upload queue and resilient upload behavior for local recordings"

## Clarifications

### Session 2026-06-11

- Q: What is the retry and retention boundary for queued desktop uploads? -> A: Use the existing local buffer retention policy as the automatic retry window; after expiry the item becomes manual-only/blocked and local artifacts are still retained until explicit purge or owner policy terminalization.
- Q: Which upload path is allowed for the desktop client? -> A: Use only the `012-server-ingest-foundation` server-mediated ingest API; the desktop must not receive object storage credentials, signed URLs, MediaScribe credentials, or direct third-party upload paths.
- Q: How are local artifact track roles mapped to backend ingest roles? -> A: Local `local_mic` maps to backend `microphone`, local `remote_speaker`/system-audio incoming maps to backend `system`, and `manifest.json` maps to backend `manifest`.
- Q: What is the UX scope for this feature? -> A: Add a compact native macOS queue/status surface inside the existing recording control area; do not introduce a product-wide redesign.
- Q: How should production bearer auth be handled for live desktop smoke? -> A: The desktop uploader may send `Authorization: Bearer ...` from ephemeral environment variable `TWO_BRAIN_REC_UPLOAD_BEARER_TOKEN`; the token must not be read from UserDefaults, persisted in queue state, logged, copied into diagnostics, or committed to documentation/evidence.
- Q: Should full provider authorization be included in this upload queue feature? -> A: No. Track full provider login, first-party session/device tokens, secure storage, refresh, and re-auth as `028-provider-auth-session`; `014` only keeps an env-only bearer bridge for internal production smoke.

## Actors and User Goals *(mandatory)*

- **Local Owner**: wants reliable transfer of local meetings to owned infrastructure without risking silent data loss.
- **MacOS User (Owner/Operator)**: wants clear, truthful upload status and recovery controls from the recording list.
- **Security/Privacy Owner**: needs explicit ownership boundaries and auditable lifecycle states across upload, retention, and deletion.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Auto-queue Completed Recordings for Upload (Priority: P1)

As a local owner, I want every completed recording package to be queued automatically so that no finished meeting disappears when I close or restart the app.

**Why this priority**: Without durable queueing, the capture-to-cloud path is unreliable and cannot be considered ready for owner-controlled retention.

**Independent Test**: Record one local meeting, stop it, then restart the app. Confirm the package appears in queue automatically within one UI refresh cycle and is not deleted.

**Acceptance Scenarios**:

1. **Given** capture finalization succeeds, **when** the app starts or the package is finalized, **then** a queue item is created with the same package identity used by local recording truth.
2. **Given** the app relaunches before upload completes, **when** local queue state loads, **then** the item remains visible with a non-terminal upload truth state.

---

### User Story 2 - Expose Truthful Upload State and Retry Progress (Priority: P1)

As a meeting owner, I want to see truthful upload states (for example: queued, uploading, retrying, uploaded, degraded, failed, blocked) so I can decide whether data is safe, delayed, or needs action.

**Why this priority**: Correct truth is required to avoid false assumptions about retention and deletion responsibilities.

**Independent Test**: Simulate a transient network failure during upload. Validate the queue item transitions through recoverable states and preserves local files until terminal truth is known.

**Acceptance Scenarios**:

1. **Given** upload starts, **when** connectivity drops, **then** status moves to a recoverable failure state and queue metadata records the reason.
2. **Given** connectivity restores, **when** retries are allowed, **then** status moves to retrying/uploading and remains visible during progress.
3. **Given** final server confirmation is not complete, **when** retry window is not exhausted, **then** item remains non-terminal with explicit next action.

---

### User Story 3 - Resume Without Duplication (Priority: P1)

As a user with large recordings, I want interrupted transfers to resume from known progress so uploads do not restart from zero and do not double-apply accepted data.

**Why this priority**: Long meetings are common; full restarts increase cost and increase duplicate-processing risk.

**Independent Test**: Interrupt a long upload, then resume. Verify only missing parts continue and one repeated chunk does not create duplicate acceptance.

**Acceptance Scenarios**:

1. **Given** partial upload evidence exists, **when** upload resumes, **then** the queue continues from missing portions only.
2. **Given** the server reports already accepted evidence, **when** client retries, **then** state remains progress-preserving and does not produce duplicated finalization.
3. **Given** retry limit is reached, **when** policy says manual intervention is required, **then** status becomes recoverable-blocked with visible manual recovery action.

---

### User Story 4 - Preserve Local Data Through Recovery Windows (Priority: P2)

As an owner, I want local files kept while upload truth is unknown so failures do not cause hidden data loss.

**Why this priority**: Upload truth directly affects deletion truth and legal/data-accountability expectations.

**Independent Test**: Keep a meeting offline until retry window expires and verify local files persist until terminal or explicit user decision.

**Acceptance Scenarios**:

1. **Given** upload remains recoverable for hours, **when** user closes/reopens app, **then** local package artifacts are still available and linked to queue entry.
2. **Given** user chooses to stop automatic retry, **when** explicit terminalization is chosen, **then** local artifacts are retained per retention policy and truth state records that choice.

---

### User Story 5 - Preserve Ownership and Security Boundaries (Priority: P2)

As a security owner, I want queue behavior to stay inside owner-controlled boundaries so no third-party audio upload path or secret exposure is introduced from the desktop queue.

**Why this priority**: This is a constitutional boundary for this project.

**Independent Test**: Review local logs/diagnostics and confirm no direct STT credentials or direct third-party upload keys are required in desktop upload behavior.

**Acceptance Scenarios**:

1. **Given** a queue upload runs, **when** diagnostics are exported, **then** they include upload truth and queue reasons but no secrets.
2. **Given** queue flow completes, **when** transcript readiness appears in other systems, **then** queue claims success only after local upload truth reaches terminal accepted state.

## Edge Cases and Failure States *(mandatory)*

- No network at startup.
- Network drops during upload and recovers later.
- Authentication/session expires mid-run.
- One track succeeds and a second required track fails repeatedly.
- Backend reports missing accepted byte ranges that do not match local manifest evidence.
- Manifest missing fields, malformed schema, or checksum mismatch.
- Duplicate finalize/race events on same queue item.
- Local clock drift changes file ordering.
- Retention threshold reached while item is still in recoverable state.
- Local disk quota exhaustion.
- App crash during upload initialization.
- Manual “stop retry” action while upload worker is active.

Failure states must be visible as one of:
- recoverable retryable (user can wait or manually retry),
- recoverable blocked (policy or validation gate),
- terminal failed (cannot continue automatically),
- terminal completed (fully accepted),
- terminal deleted (explicitly terminalized by user/retention policy).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST automatically create one queue item for each finalized local meeting package that contains required local capture artifacts, without requiring manual action.
- **FR-002**: Queue items MUST preserve package identity through local capture, queue state, and eventual server sync state to prevent item duplication or cross-item mixing.
- **FR-003**: The desktop queue MUST expose at least these truthful states: queued, uploading, retrying, uploaded, degraded, failed, blocked, and terminal-deleted.
- **FR-004**: Queue truth MUST become visible within 30 seconds of package finalization or app start for pending local work.
- **FR-005**: Queue state MUST survive app restart and OS interruption for non-terminal items.
- **FR-006**: Upload retries MUST be persistent, bounded by the local buffer retention policy, and recoverable, with visible reason codes for failure causes.
- **FR-007**: The app MUST avoid marking items as uploaded unless required tracks are accepted by server-side truth.
- **FR-008**: On transient errors, the queue MUST move into recoverable retry flow instead of terminal delete/degrade unless policy explicitly forbids retry.
- **FR-009**: On repeated recoverable failures, the app MUST preserve local package artifacts until explicit terminal decision or expiry policy.
- **FR-010**: The queue MUST provide one manual recovery action per item (retry/stop/recover) without requiring app restart.
- **FR-011**: The app MUST support idempotent handling of repeated attempts for the same package identity.
- **FR-012**: The queue UI MUST preserve required truth for multi-track packages and mark per-item track completeness.
- **FR-013**: The app MUST classify failure reasons into at least: network, auth/session, server validation, schema incompatibility, local resource, and storage quota classes.
- **FR-014**: The app MUST produce no direct upload to third-party STT service from the desktop uploader path.
- **FR-015**: The app MUST never purge local artifacts while upload truth is pending, retrying, or degraded.
- **FR-016**: The app MUST record queue outcomes in deletion/accounting artifacts without leaking secrets or raw credentials.
- **FR-017**: The queue must not alter capture stop/start behavior, visible capture indicator, or one-action stop semantics.
- **FR-018**: Queue behavior MUST be independent of assisted auto-start and driver routing; these remain separate feature scopes.
- **FR-019**: The app MUST keep a deterministic ordering for queue visibility updates and never regress terminal truth to a recoverable state.
- **FR-020**: The queue workflow MUST leave clear evidence whether an item is retryable automatically, manual-only, or terminal.
- **FR-021**: The desktop uploader MUST map local recording roles to backend ingest roles as follows: `local_mic` to `microphone`, `remote_speaker`/system-audio incoming to `system`, and `manifest.json` to `manifest`.
- **FR-022**: The queue UI MUST fit inside the existing native macOS recording control surface and show status, reason, progress, and one relevant next action without requiring a product-wide redesign.
- **FR-023**: When production ingest requires bearer authentication, the desktop uploader MUST attach `Authorization: Bearer ...` from ephemeral process environment only and MUST NOT persist, log, display, or include the bearer token in diagnostics, queue metadata, or Spec Kit evidence.

### Key Entities *(include if feature involves data)*

- **UploadQueueItem**: Durable local record per finished meeting package (package/session identity, state, failure reasons, retry counters, retention deadline).
- **UploadItemState**: User-facing truth state and terminality classification.
- **RetryRecord**: Logged recovery attempts with timestamps, attempts, backoff phase, and final result.
- **ArtifactCompletenessProfile**: Local track and manifest validation snapshot used for queue entry validity.
- **ServerTruthFingerprint**: Read-only canonical evidence of what the server has accepted for this package.
- **RetentionDecision**: Linkage to local retention policy outcome and eventual local purge/closure state.

## Out of Scope *(mandatory)*

- Full Temporal workflow orchestration for transcription, note generation, or review surfaces.
- Meeting transcription UI, search, and dashboard integration.
- Direct uploader integration with third-party STT providers.
- Assisted start/meeting auto-detect behavior changes.
- Virtual audio driver routing and installer/repair workflows.
- Server-side retention execution and external delete propagation.
- UI brand redesign or major design-system migration.
- Full provider authentication/session/device-token management; tracked separately in `028-provider-auth-session`.

## Dependencies *(mandatory)*

- Existing stable local artifact format and capture truth from `010` and `020`.
- Backend ingest/session/metadata path from `012-server-ingest-foundation` and its acceptance contracts.
- Local identity/session context needed for queue association and auth refresh handling.
- Existing local retention and deletion accounting hooks for lifecycle consistency.
- No additional external infrastructure dependencies beyond approved owner-controlled ingest path.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid finalized local recordings appear in upload queue within 30 seconds on stable platforms.
- **SC-002**: 100% of queue items in recoverable states reappear after app restart.
- **SC-003**: At least 95% of transient network-related interruptions recover automatically within 2 minutes after connectivity restores.
- **SC-004**: 99% of non-schema failures avoid duplicate terminal success states after repeated retries.
- **SC-005**: 100% of non-terminal items keep required local artifacts present until terminal decision.
- **SC-006**: 100% of terminal items include auditable terminal reason and retryability status.
- **SC-007**: 95% of users in recovery scenarios can identify whether an item is retryable and what next action to take from queue UI.
- **SC-008**: 0 queue outcomes with secrets, upload tokens, or credentials in diagnostics traces.
- **SC-009**: 100% of completed uploads have consistency between queue state and captured track completeness for required tracks.
- **SC-010**: 0 regressions in visible capture indicator and one-action stop behavior due to queue activity.

## Assumptions

- Network instability is expected and queue design favors safety and persistence over immediate success.
- Retention policy already exists and defines maximum retention windows for local artifacts.
- Authentication/session refresh flow is externalized and provides meaningful expiry/retry signals.
- Backend accepts partial-progress-aware upload behavior as designed for MVP.
- `012-server-ingest-foundation` status and contracts are the single allowed server upload path for this slice.
- Automatic retry stops at the local buffer retention deadline, but terminal deletion/purge still requires explicit policy evidence.
- `028-provider-auth-session` will supersede the internal env-only bearer bridge before user-facing production rollout.
