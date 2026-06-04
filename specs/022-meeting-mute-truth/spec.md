# Feature Specification: Meeting-App Mute Truth

**Feature Branch**: `022-meeting-mute-truth`

**Created**: 2026-06-04

**Status**: Backlog Draft - no implementation authorized

**Input**: User asked to preserve the context from the old
`009-respect-meeting-mute` branch as a future backlog slice. The original issue
was discovered during local recording validation: when the user mutes the
microphone inside a meeting application, local microphone audio can still appear
in the local recording. This is a privacy and capture-truth concern, but the
slice must not move to implementation until clarification and planning decide
the canonical mute-truth strategy.

## Backlog Transfer Record

This feature supersedes the old draft branch `009-respect-meeting-mute` as the
canonical backlog record for meeting-app mute truth.

- Source branch: `009-respect-meeting-mute`
- Source commit: `603f457 docs: Track meeting mute recording issue`
- Backlog issue: https://github.com/yshishenya/crisp/issues/137
- Source files:
  - `specs/009-respect-meeting-mute/spec.md`
  - `specs/009-respect-meeting-mute/checklists/requirements.md`
  - `qa/macos/local-recording-persistence.md`
  - `qa/macos/release-candidate-checklist.md`
- Git hygiene decision: do not raw-merge `009-respect-meeting-mute` into
  `master`. The branch was created before later merged work and a raw merge can
  reintroduce stale tree state. This `022` slice preserves the useful product
  context without carrying obsolete branch history.
- Implementation decision: no code, route behavior, recording behavior, upload
  behavior, transcription behavior, or UI behavior is authorized by this
  backlog transfer.

## Product Scope Boundary

This feature is about truthful local recording behavior when the user mutes
inside a meeting app such as Zoom, Chrome, Opera, Telemost, or another approved
meeting target.

The product must not silently claim that local recordings are privacy-correct
for muted meeting intervals unless the system can prove the relevant mute truth
or safely degrade/block the recording. The current accepted local recording
slices (`007`, `008`, `010`) remain accepted for manual visible recording,
local artifact creation, and artifact format. They are not accepted as proof
that meeting-app mute intent is respected.

## Clarifications Required Before Planning

The next `$speckit-clarify 022` run must resolve these points before
`$speckit-plan`:

1. **Canonical mute truth source**: Decide whether MVP relies on app-specific
   mute state, post-mute routed app audio, meeting target integration,
   operating-system route evidence, user-controlled product mute/pause, or a
   fail-closed unsupported-target policy.
2. **Unsupported target policy**: Decide whether unsupported meeting targets
   block recording, degrade/not-accept the local mic track, require explicit
   user acknowledgement, or remain out of accepted release scope.
3. **Muted interval artifact truth**: Decide whether a known muted interval is
   represented as silence, redacted segment, omitted local-mic interval,
   degraded track, separate evidence segment, or failed/not-accepted package.
4. **User-facing limitation copy**: Decide what the app says when meeting-app
   mute truth is unavailable, stale, contradictory, or unsupported.
5. **QA target matrix**: Decide which targets are in the first acceptance
   matrix and which are explicitly deferred.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Muted Meeting Mic Is Not Recorded As Spoken Audio (Priority: P1)

As a user who manually records a meeting, I want speech made while I am muted
inside the meeting app not to be saved as ordinary accepted local microphone
audio, so that the local artifact does not violate my meeting mute intent.

**Why this priority**: This is a privacy and capture-truth blocker. A user who
mutes inside a meeting app reasonably expects that muted local speech will not
be treated as normal captured meeting speech.

**Independent Test**: Start a manual recording in a supported meeting target,
mute the microphone inside the meeting app, speak locally, unmute, speak again,
stop recording, and inspect the local artifact. The muted interval must be
silenced, redacted, degraded, blocked, or otherwise not accepted as ordinary
local microphone speech according to the clarified policy.

**Acceptance Scenarios**:

1. **Given** the user is recording a supported meeting target and the meeting
   app mute state is known, **When** the user speaks while muted in that app,
   **Then** the saved local artifact does not contain that muted speech as
   ordinary accepted local mic audio.
2. **Given** the user unmutes in the meeting app and mute truth remains known,
   **When** the user speaks again, **Then** local mic capture may resume only
   according to the clarified acceptance policy and artifact truth model.
3. **Given** mute evidence contradicts captured audio, **When** finalizing the
   recording, **Then** the package is not accepted as mute-respecting without a
   truthful degraded/failed state.

---

### User Story 2 - Fail Closed When Mute Truth Is Unavailable (Priority: P1)

As a user or operator, I need unsupported or unobservable meeting mute behavior
to be blocked, degraded, or clearly marked, so that 2brain Rec never silently
overstates privacy protection.

**Why this priority**: Unknown mute truth is safer as a visible limitation than
as hidden capture. Silent local recording of speech that the user thought was
muted is worse than a blocked or degraded artifact.

**Independent Test**: Use a meeting target where app mute state is unavailable
or cannot be proven, attempt to record while muting inside the target, and
verify that the app and artifact state do not claim mute-respecting acceptance.

**Acceptance Scenarios**:

1. **Given** a meeting target lacks supported mute truth, **When** the user
   starts or finalizes a recording that requires mute-respecting acceptance,
   **Then** the system blocks recording, degrades the local mic track, marks the
   artifact not accepted, or otherwise follows the clarified fail-closed policy.
2. **Given** mute truth becomes unavailable or stale during an active
   recording, **When** the system detects that loss of truth, **Then** it
   records metadata-only evidence and applies the clarified degraded or blocked
   behavior.
3. **Given** the target is outside the accepted QA matrix, **When** release
   validation runs, **Then** the result is explicitly `not accepted`,
   `unsupported`, or `deferred`, not a silent pass.

---

### User Story 3 - Preserve Existing Capture Safety Boundaries (Priority: P1)

As the product owner, I need the mute-truth fix to preserve visible capture,
one-action stop, local-only artifact boundaries, metadata-only diagnostics, and
no new egress, so that privacy work does not weaken already accepted recording
gates.

**Why this priority**: The feature touches recording truth and can accidentally
weaken constitution gates around visible capture, local control, diagnostics,
and content boundaries.

**Independent Test**: Re-run the existing `007`, `008`, and `010` validation
gates after the mute-truth behavior is specified and implemented. Confirm that
manual recording visibility, stop control, artifact structure, role mapping,
diagnostic redaction, and no-egress constraints still pass.

**Acceptance Scenarios**:

1. **Given** mute-truth handling is active, **When** recording starts and stops,
   **Then** the persistent local visible indicator and one-action stop remain
   available.
2. **Given** diagnostics include mute-truth evidence, **When** diagnostics are
   exported, **Then** they contain metadata-only evidence and exclude raw audio,
   transcript text, meeting content, credentials, tokens, signed URLs,
   passwords, and live secret paths.
3. **Given** this slice is implemented, **When** upload, transcription,
   retention, deletion, dashboard, or assisted recording behavior is inspected,
   **Then** no new behavior in those areas is introduced by this feature.

---

### User Story 4 - Provide QA With Target-Specific Mute Truth Evidence (Priority: P2)

As QA, I need a target matrix and metadata-only evidence for mute truth, so that
the team can distinguish supported targets, unsupported targets, stale evidence,
hardware mute, macOS input mute, product pause, and meeting-app mute.

**Why this priority**: Meeting apps and browsers differ. A single generic
“mute works” claim is not enough for release acceptance.

**Independent Test**: Run a manual or automated target matrix across the agreed
targets and verify that each target records accepted, unsupported, deferred, or
degraded mute-truth status with metadata-only proof.

**Acceptance Scenarios**:

1. **Given** the QA matrix includes a target, **When** mute truth is tested,
   **Then** the target has an explicit status and evidence source.
2. **Given** hardware mute, macOS input mute, product pause, and meeting-app
   mute are different states, **When** evidence is recorded, **Then** those
   states are not conflated.
3. **Given** the target matrix is incomplete, **When** release readiness is
   reviewed, **Then** incomplete rows block or defer mute-respecting acceptance.

## Edge Cases

- The meeting app continues reading the microphone while muted but suppresses
  network transmission internally.
- The meeting app stops reading the microphone while muted.
- Browser targets differ across Chrome, Opera, Yandex Browser, and Telemost.
- Zoom native app exposes mute differently from browser targets.
- The user starts recording while already muted in the meeting app.
- The user rapidly mutes/unmutes during active recording.
- The user uses hardware microphone mute.
- The user mutes macOS input level instead of the meeting app.
- Product-level pause/stop is confused with meeting-app mute.
- Mute-state evidence is stale, unavailable, delayed, or contradictory.
- Remote audio leakage into the local mic track is present at the same time as
  mute-state ambiguity.
- The artifact is uploaded later through server ingest; server-side surfaces
  must not overstate mute correctness if local artifact metadata says
  degraded, unsupported, or unproven.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST NOT claim mute-respecting local recording
  acceptance when meeting-app mute intent is unknown, stale, unsupported, or
  contradicted by evidence.
- **FR-002**: The system MUST prevent, silence, segment, degrade, block, or mark
  not accepted any local mic artifact interval where the user is muted in the
  meeting app and mute truth is available.
- **FR-003**: The feature MUST define the canonical source of mute truth before
  planning and implementation begin.
- **FR-004**: The feature MUST distinguish meeting-app mute from macOS input
  mute, hardware mute, product pause, product stop, and route failure.
- **FR-005**: The feature MUST record metadata-only mute-truth evidence for
  acceptance, degradation, blocking, or unsupported-target decisions.
- **FR-006**: The feature MUST define a target support matrix for the first
  accepted release scope.
- **FR-007**: Unsupported targets MUST fail closed according to the clarified
  policy and MUST NOT silently pass release validation as mute-respecting.
- **FR-008**: Existing visible recording indicator and one-action stop behavior
  from feature `007` MUST remain intact.
- **FR-009**: Existing local artifact persistence and truthful
  saved/degraded/failed states from feature `008` MUST remain intact.
- **FR-010**: Existing artifact role mapping and metadata-only diagnostics from
  feature `010` MUST remain intact.
- **FR-011**: This feature MUST NOT add upload, server ingest, MediaScribe,
  Langfuse, dashboard, retention, deletion, sharing, download, or assisted
  auto-recording behavior.
- **FR-012**: Diagnostics and logs MUST exclude raw audio, transcript text,
  meeting content, credentials, tokens, signed URLs, passwords, and live secret
  paths.
- **FR-013**: Product and QA documentation MUST explicitly state which local
  recording claims are accepted, unsupported, deferred, or degraded with
  respect to meeting-app mute truth.

### Key Entities *(include if feature involves data)*

- **Mute Truth Evidence**: Metadata-only evidence describing mute state source,
  freshness, target, confidence, observed contradictions, and resulting
  acceptance/degradation decision.
- **Mute Segment**: A local recording interval where meeting-app mute intent is
  known, unknown, stale, contradicted, or unsupported and therefore receives a
  specific artifact truth outcome.
- **Target Mute Capability**: Per target capability record describing whether
  meeting-app mute truth can be observed and accepted for that target.
- **Mute Truth Decision**: Final per-recording decision that states whether the
  artifact is mute-respecting, degraded, not accepted, unsupported, or deferred.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every supported target in the first acceptance matrix, speech
  during a known meeting-app muted interval is absent from ordinary accepted
  local mic audio in 100% of acceptance test runs.
- **SC-002**: For every unsupported or unobservable target in the first matrix,
  the app blocks, degrades, or marks the artifact not accepted 100% of the time
  rather than claiming mute-respecting acceptance.
- **SC-003**: Existing `007`, `008`, and `010` validation gates still pass after
  this feature is implemented.
- **SC-004**: Mute-truth diagnostics contain no raw audio, transcript text,
  meeting content, credentials, tokens, signed URLs, passwords, or live secret
  paths in automated redaction checks.
- **SC-005**: Release readiness documentation lists each target as accepted,
  unsupported, deferred, or degraded for meeting-app mute truth.

## Assumptions

- Current local recording can capture app-owned microphone audio independently
  of what a meeting app transmits to remote participants.
- Generic Core Audio device state is not enough to prove meeting-app mute
  intent for every target.
- The correct MVP behavior may be target-specific, may require blocking or
  degrading unsupported targets, and may require policy decisions before code.
- This backlog slice is local recording truth only. Upload, transcription,
  server processing, dashboard, retention, deletion, and assisted auto-start are
  out of scope.

## Out Of Scope

- Implementing the mute-truth behavior.
- Adding live meeting app integrations.
- Adding upload or server ingest behavior.
- Adding transcription, MediaScribe, dashboard, retention, deletion, sharing, or
  assisted recording behavior.
- Changing accepted behavior for features `007`, `008`, `010`, or `012` without
  a future explicit plan.
