# Feature Specification: Meeting-App Mute Truth

**Feature Branch**: `022-meeting-mute-truth`

**Created**: 2026-06-04

**Status**: Implemented product-owned mute truth; third-party mute adapters remain unproven

**Input**: User asked to preserve the context from the old
`009-respect-meeting-mute` branch and then move the slice into implementation as
part of MVP readiness. The original issue was discovered during local recording
validation: when the user mutes the microphone inside a meeting application,
local microphone audio can still appear in the local recording. This is a
privacy and capture-truth concern. The clarified MVP strategy is to avoid
overclaiming third-party meeting-app mute support, provide a product-owned
privacy pause/stop control that can be proven locally, and mark meeting-app mute
truth as unproven unless a target-specific adapter supplies fresh evidence.

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
- Implementation decision: this feature may implement local product-owned
  privacy pause/truth behavior and UI limitation copy. It MUST NOT raw-merge the
  old branch or add upload, transcription, server, or third-party meeting-app API
  behavior.

## Clarifications

### Session 2026-06-16

- Q: What is the canonical MVP mute-truth source? -> A: Product-owned privacy pause/stop is canonical; third-party meeting-app mute is accepted only with a future target-specific adapter that provides fresh metadata-only evidence.
- Q: What happens for unsupported or unobservable meeting targets? -> A: Recording may continue only with an explicit unproven/degraded mute-truth state and limitation copy; the artifact MUST NOT be accepted or described as meeting-app-mute-respecting.
- Q: How are muted intervals represented in artifacts? -> A: Product-owned privacy pause intervals are silent/redacted local-mic segments with metadata-only evidence; unproven meeting-app mute intervals remain ordinary capture only under a degraded/unproven artifact truth state.
- Q: What user-facing copy is required when meeting-app mute truth is unavailable? -> A: "2brain cannot verify mute inside this meeting app. Use Pause or Stop in 2brain to keep local speech out of the recording."
- Q: What is the first QA target matrix? -> A: Validate product-owned Pause/Stop and limitation truth across Zoom native, Chrome/Telemost, and Opera/Telemost; mark Yandex Browser and generic/unknown targets unsupported or deferred until adapter evidence exists.

## Product Scope Boundary

This feature is about truthful local recording behavior around meeting-app mute
expectations and product-owned privacy controls during manual local recording in
targets such as Zoom, Chrome, Opera, Telemost, or another approved meeting
target.

For MVP, the canonical privacy truth source is product-owned `2brain Pause` or
`2brain Stop`, because those controls can be proven locally and preserved in
metadata. Third-party meeting-app mute state is not accepted by default. A
meeting-app mute interval may be called mute-respecting only after a future
target-specific adapter provides fresh metadata-only evidence for that target.

The product must not silently claim that local recordings are privacy-correct
for muted meeting intervals unless the system can prove the relevant mute truth
or safely degrade/block the claim. The current accepted local recording slices
(`007`, `008`, `010`) remain accepted for manual visible recording, local
artifact creation, and artifact format. They are not accepted as proof that
third-party meeting-app mute intent is respected.

## Clarifications Resolved Before Planning

The `$speckit-clarify 022` run resolved these points before `$speckit-plan`:

1. **Canonical mute truth source**: Product-owned `2brain Pause` and `2brain
   Stop` are the MVP source of privacy truth. Third-party meeting-app mute is
   unproven unless a future target-specific adapter supplies fresh
   metadata-only evidence.
2. **Unsupported target policy**: Unsupported or unobservable meeting targets
   may still be recorded manually, but the app and artifact must show
   `meeting_mute_unproven` or an equivalent degraded state and must not claim
   meeting-app-mute-respecting acceptance.
3. **Muted interval artifact truth**: Product-owned pause intervals are
   represented as silent/redacted local-mic segments with metadata-only segment
   evidence. Unproven third-party meeting-app mute intervals are not redacted by
   implication; they remain ordinary capture inside a degraded/unproven artifact
   truth state.
4. **User-facing limitation copy**: When meeting-app mute truth is unavailable,
   stale, contradictory, or unsupported, the app must say: "2brain cannot
   verify mute inside this meeting app. Use Pause or Stop in 2brain to keep
   local speech out of the recording."
5. **QA target matrix**: The first matrix validates product-owned Pause/Stop
   and limitation truth across Zoom native, Chrome/Telemost, and
   Opera/Telemost. Yandex Browser and generic/unknown targets are unsupported
   or deferred until adapter evidence exists.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Product Privacy Pause Is Not Recorded As Spoken Audio (Priority: P1)

As a user who manually records a meeting, I want speech made while I use
`2brain Pause` not to be saved as ordinary accepted local microphone audio, so
that I have a proven local privacy control even when third-party meeting-app
mute state cannot be verified.

**Why this priority**: This is a privacy and capture-truth blocker. A user who
mutes inside a meeting app reasonably expects privacy, but MVP cannot safely
prove every meeting app's internal mute state. The product must provide a
truthful local control and avoid overclaiming unverified app mute behavior.

**Independent Test**: Start a manual recording in a matrix target, observe the
limitation copy, activate `2brain Pause`, speak locally, resume, speak again,
stop recording, and inspect the local artifact. The product pause interval must
be silent/redacted from ordinary local microphone audio with metadata-only
segment evidence. If the user only mutes inside the meeting app without using
`2brain Pause`, the artifact must not be accepted or described as
meeting-app-mute-respecting.

**Acceptance Scenarios**:

1. **Given** the user is recording a matrix target, **When** the user activates
   `2brain Pause` and speaks locally, **Then** the saved local artifact does not
   contain that paused speech as ordinary accepted local mic audio.
2. **Given** the user resumes from `2brain Pause`, **When** the user speaks
   again, **Then** local mic capture may resume and the artifact records a
   metadata-only transition from paused to capturing.
3. **Given** the user relies only on third-party meeting-app mute and no adapter
   evidence is available, **When** finalizing the recording, **Then** the
   package is not accepted as meeting-app-mute-respecting and carries a
   truthful degraded/unproven state.

---

### User Story 2 - Fail Closed For Unproven Meeting-App Mute Claims (Priority: P1)

As a user or operator, I need unsupported or unobservable meeting-app mute
behavior to be clearly marked and excluded from mute-respecting acceptance, so
that 2brain Rec never silently overstates privacy protection.

**Why this priority**: Unknown mute truth is safer as a visible limitation than
as hidden capture. Silent local recording of speech that the user thought was
muted is worse than a blocked or degraded artifact.

**Independent Test**: Use a meeting target where app mute state is unavailable
or cannot be proven, attempt to record while muting inside the target, and
verify that the app limitation copy and artifact state do not claim
meeting-app-mute-respecting acceptance.

**Acceptance Scenarios**:

1. **Given** a meeting target lacks supported meeting-app mute truth, **When**
   the user starts or finalizes a recording, **Then** the system shows the
   limitation copy and marks the artifact `meeting_mute_unproven` or an
   equivalent degraded state instead of claiming mute-respecting acceptance.
2. **Given** mute truth becomes unavailable or stale during an active
   recording, **When** the system detects that loss of truth, **Then** it
   records metadata-only evidence and applies the clarified degraded/unproven
   claim behavior.
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
- Product-level pause/stop is confused with meeting-app mute; UI and metadata
  must keep the states separate.
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
- **FR-002**: The system MUST silence or redact local microphone audio for every
  active `2brain Pause` interval while preserving metadata-only segment
  evidence for the pause start, pause end, and resulting artifact truth state.
- **FR-003**: The feature MUST treat product-owned `2brain Pause` and `2brain
  Stop` as the canonical MVP privacy truth source; third-party meeting-app mute
  MUST remain unproven unless future target-specific adapter evidence exists.
- **FR-004**: The feature MUST distinguish meeting-app mute from macOS input
  mute, hardware mute, product pause, product stop, and route failure.
- **FR-005**: The feature MUST record metadata-only mute-truth evidence for
  acceptance, degradation, blocking, or unsupported-target decisions.
- **FR-006**: The feature MUST define a target support matrix for the first
  accepted release scope: Zoom native, Chrome/Telemost, and Opera/Telemost must
  validate `2brain Pause`/`2brain Stop` behavior and limitation copy; Yandex
  Browser and generic/unknown targets must be unsupported or deferred until
  adapter evidence exists.
- **FR-007**: Unsupported or unobservable targets MUST fail closed for
  meeting-app-mute-respecting claims and MUST NOT silently pass release
  validation as mute-respecting.
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
- **FR-014**: The app MUST display this limitation copy whenever meeting-app
  mute truth is unavailable, stale, contradictory, or unsupported: "2brain
  cannot verify mute inside this meeting app. Use Pause or Stop in 2brain to
  keep local speech out of the recording."

### Key Entities *(include if feature involves data)*

- **Mute Truth Evidence**: Metadata-only evidence describing mute state source,
  freshness, target, confidence, observed contradictions, and resulting
  acceptance/degradation decision.
- **Product Privacy Segment**: A local interval created by `2brain Pause` or
  `2brain Stop` that suppresses or ends local microphone capture and records
  metadata-only timing and reason evidence.
- **Mute Segment**: A local recording interval where meeting-app mute intent is
  known, unknown, stale, contradicted, or unsupported and therefore receives a
  specific artifact truth outcome.
- **Target Mute Capability**: Per target capability record describing whether
  meeting-app mute truth can be observed and accepted for that target.
- **Mute Truth Decision**: Final per-recording decision that states whether the
  artifact is mute-respecting, degraded, not accepted, unsupported, or deferred.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For Zoom native, Chrome/Telemost, and Opera/Telemost matrix runs,
  speech during active `2brain Pause` is absent from ordinary accepted local mic
  audio in 100% of acceptance test runs.
- **SC-002**: For every unsupported or unobservable target in the first matrix,
  the app shows limitation copy and marks meeting-app mute truth unproven or
  degraded 100% of the time rather than claiming mute-respecting acceptance.
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
- The correct MVP behavior is product-owned pause/stop plus truthful limitation
  and artifact state, not unproven third-party meeting-app mute integration.
- This slice is local recording truth only. Upload, transcription, server
  processing, dashboard, retention, deletion, and assisted auto-start are out of
  scope.

## Out Of Scope

- Adding live third-party meeting app mute integrations or target-specific mute
  adapters.
- Adding upload or server ingest behavior.
- Adding transcription, MediaScribe, dashboard, retention, deletion, sharing, or
  assisted recording behavior.
- Changing accepted behavior for features `007`, `008`, `010`, or `012` without
  a future explicit plan.
