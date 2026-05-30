# Feature Specification: macOS Live Audio Passthrough

**Feature Branch**: `002-macos-live-passthrough`

**Created**: 2026-05-31

**Status**: Draft

**Input**: User description: "Continue macOS development after the publication proof: implement real live audio passthrough and capture readiness so 2brain Rec becomes usable for calls, not only visible in macOS."

## Clarifications

### Session 2026-05-31

- Q: How should the app prove the speaker path during readiness check? → A: Use a short audible test sound after the user explicitly presses `Run Check`.
- Q: How should the app prove the microphone path during readiness check? → A: Ask the user to speak or tap the microphone for about 3 seconds during `Run Check`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prove Call-Ready Audio Routes (Priority: P1)

As an internal macOS user, I want 2brain Rec to prove that my selected physical
microphone reaches the meeting through `2brain Rec Microphone` and that meeting
audio reaches my selected physical speaker through `2brain Rec Speaker`, so that
the app only says it is ready when a real call can work.

**Why this priority**: Device publication is already proven, but the product is
not useful until real bidirectional audio movement is proven. This story turns
the current `not ready for calls yet` state into a trustworthy ready state.

**Independent Test**: Can be tested by installing the current macOS build,
selecting physical input/output devices, running the readiness check, and
confirming the app reaches ready only after both real audio paths are detected.

**Acceptance Scenarios**:

1. **Given** both 2brain Rec virtual devices are visible and physical devices are
   selected, **When** the user runs the readiness check, **Then** the app plays a
   short audible test sound, asks the user to speak or tap the microphone for
   about 3 seconds, and proves microphone and speaker audio movement before
   showing ready.
2. **Given** the physical microphone is muted, unavailable, or silent, **When**
   the user runs the readiness check, **Then** the app reports microphone path
   failure and does not show ready.
3. **Given** the physical speaker path is unavailable or muted, **When** the user
   runs the readiness check, **Then** the app reports speaker path failure and
   does not show ready.
4. **Given** only virtual-device visibility is confirmed, **When** no real audio
   movement has been proven, **Then** the app continues to show not ready.

---

### User Story 2 - Preserve Live Call Audio During Capture (Priority: P1)

As a user in a supported browser meeting, I want to keep hearing and speaking
normally while 2brain Rec captures local and remote audio, so that recording does
not break the call.

**Why this priority**: The primary product promise fails if passthrough causes
silence, feedback, delay, or one-sided audio during a meeting.

**Independent Test**: Can be tested in one supported browser meeting by using
both 2brain Rec virtual devices, speaking locally, playing remote audio, and
confirming live call audio stays usable while capture is active.

**Acceptance Scenarios**:

1. **Given** a supported browser meeting uses both 2brain Rec virtual devices,
   **When** the user starts capture after readiness passes, **Then** the user can
   speak and hear remote audio without changing meeting audio devices.
2. **Given** remote participants speak while the local user is silent, **When**
   capture is active, **Then** remote audio is not fed into the virtual
   microphone path.
3. **Given** the desktop app or backend-facing workflow is degraded, **When** the
   meeting continues, **Then** live call audio remains usable or the app tells
   the user to stop using the route before audio loss occurs.
4. **Given** a real passthrough check fails during a call, **When** the app
   detects the failure, **Then** it shows a visible degraded state and a safe
   recovery path instead of claiming ready.

---

### User Story 3 - Produce Separate Track Evidence (Priority: P2)

As the product owner, I want evidence that local microphone audio and remote
speaker audio are captured as separate, aligned tracks, so that the next backend
and transcription slices can rely on clean source separation.

**Why this priority**: Backend transcription quality depends on track separation,
but readiness and live call safety must come first.

**Independent Test**: Can be tested by recording a short controlled meeting and
inspecting the resulting local/remote track evidence for presence, separation,
alignment, and dropout state.

**Acceptance Scenarios**:

1. **Given** the user records a controlled meeting, **When** local and remote
   audio are both present, **Then** the session records separate local and remote
   track evidence.
2. **Given** one audio side is missing during capture, **When** the session is
   finalized, **Then** the app marks the session degraded instead of presenting a
   complete capture.
3. **Given** a 30-minute pilot call completes, **When** track evidence is
   reviewed, **Then** local/remote timing remains within the accepted alignment
   threshold and dropout status is visible.

---

### User Story 4 - Recover From Audio Route Changes (Priority: P2)

As a user, I want 2brain Rec to react clearly when devices disconnect, Bluetooth
profiles switch, or macOS routes change, so that I can recover without guessing
why a call stopped working.

**Why this priority**: Real-world macOS audio routes change often, especially
with Bluetooth and AirPods-class devices. The MVP must fail visibly and
recoverably.

**Independent Test**: Can be tested by passing readiness, disconnecting or
switching the physical input/output device, and confirming the app changes state
and guides recovery before claiming ready again.

**Acceptance Scenarios**:

1. **Given** readiness has passed, **When** the selected physical microphone is
   disconnected, **Then** the app marks microphone route degraded and blocks
   ready until rechecked.
2. **Given** readiness has passed, **When** the selected physical output changes,
   **Then** the app marks speaker route degraded and blocks ready until
   rechecked.
3. **Given** a Bluetooth or AirPods-class device changes profile, **When** the
   route no longer satisfies the supported call path, **Then** the app reports
   the profile problem and offers a safe recovery action.

### Edge Cases

- The user selects a 2brain Rec virtual device as its own physical source or
  output.
- A physical microphone or speaker is visible but silent, muted, permission
  blocked, or unavailable to the current user.
- A meeting target changes audio devices after readiness passes.
- A browser restarts or drops remote audio while capture is active.
- Bluetooth or AirPods-class devices switch between high-quality output and
  call-oriented input/output profiles.
- The app restarts while the virtual devices remain selected in a meeting.
- The user starts readiness checks while another app is already using the
  selected physical devices.
- Audio movement becomes delayed, distorted, one-sided, or intermittently
  missing during a long call.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST distinguish virtual-device visibility from real
  call readiness in all user-facing states.
- **FR-002**: The system MUST prove selected physical microphone audio reaches
  the virtual microphone path before showing ready.
- **FR-003**: The system MUST prove virtual speaker audio reaches the selected
  physical speaker path before showing ready.
- **FR-004**: The system MUST keep remote speaker audio out of the virtual
  microphone path.
- **FR-005**: The system MUST block ready when either physical path is missing,
  silent, muted, self-routed, disconnected, or otherwise unproven.
- **FR-006**: The system MUST provide a user-triggered readiness check that is
  safe to run before a call, does not start hidden recording, uses a short
  audible test sound after the user explicitly starts the check, and asks the
  user to speak or tap the microphone for about 3 seconds to prove the physical
  microphone path.
- **FR-007**: The system MUST keep live microphone and speaker passthrough usable
  during capture when backend, upload, or transcription workflows are unavailable.
- **FR-008**: The system MUST surface a degraded state when live passthrough is
  no longer proven during a call.
- **FR-009**: The system MUST provide a one-action way to stop active capture
  from a visible local surface whenever capture is active.
- **FR-010**: The system MUST register local and remote track evidence separately
  when audio-recording mode is active.
- **FR-011**: The system MUST mark capture degraded when an expected local or
  remote track is missing, silent beyond the accepted threshold, or loses
  continuity.
- **FR-012**: The system MUST expose enough timing and dropout information for
  the app to explain alignment and continuity health to the user or operator.
- **FR-013**: The system MUST require readiness to be rechecked after physical
  device disconnect, output route change, Bluetooth profile change, or meeting
  target device change.
- **FR-014**: The system MUST provide actionable diagnostics for microphone path,
  speaker path, loopback rejection, track separation, and device-change failures.
- **FR-015**: Diagnostics MUST NOT include raw audio, transcript text,
  credentials, tokens, signed URLs, or hidden recording artifacts by default.
- **FR-016**: Browser meeting validation MUST include Chrome, Opera, Yandex
  Browser, and Yandex Telemost-in-browser before the feature is considered
  release-ready.
- **FR-017**: The feature MUST NOT introduce a no-driver fallback, silent
  recording, invisible capture, or direct desktop-to-MediaScribe upload.
- **FR-018**: The system MUST keep the existing publication proof valid while
  adding real route readiness.

### Key Entities

- **Readiness Check**: A user-visible verification attempt for microphone path,
  speaker path, self-routing, loopback rejection, and current device state.
- **Audio Route Evidence**: The result that proves or rejects real movement on a
  specific microphone or speaker path.
- **Capture Track Evidence**: The local record that a local or remote track was
  present, separate, aligned, and continuous enough to trust.
- **Degraded Audio State**: A visible state explaining why the app is not safe to
  use for calls or why an active capture is incomplete.
- **Device Change Event**: A route-affecting change that invalidates prior
  readiness and requires recheck.

### Constitutional Requirements *(mandatory for 2brain Rec)*

- **Capture/Driver Impact**: This feature directly touches macOS audio routing,
  passthrough, capture readiness, degraded states, and diagnostics. It must prove
  real audio movement before ready, keep the driver-first model, and block
  release when only publication is proven.
- **Visible Control Impact**: The feature must not start hidden recording during
  readiness checks. Any active capture must keep visible local indication and
  one-action stop.
- **Data Boundary Impact**: The feature is local macOS audio readiness and local
  capture evidence only. It must not add MediaScribe upload, Langfuse traces, LLM
  calls, external analytics, or new network egress.
- **Secrets Impact**: The feature must not store or expose credentials. Any
  diagnostic bundle must preserve redaction for credentials, tokens, signed URLs,
  raw audio, and transcript text.
- **Retention/Deletion Impact**: The feature may create local capture and
  diagnostic metadata. Any created artifact must be registered as app-managed
  local data and be eligible for the existing local deletion/reporting rules.
- **Audit Impact**: Readiness pass/fail, capture start/stop, degraded state,
  device-change invalidation, and diagnostic export must be auditable without
  storing raw audio or transcripts in audit payloads.
- **UX/Brand/Accessibility Impact**: UI changes must use original 2brain Rec
  language, accessible non-color-only states, localization-safe copy, and clear
  brand distance from Krisp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a fresh local install, an internal user can move from
  `not ready for calls yet` to ready only after microphone and speaker path
  checks both pass.
- **SC-002**: In a supported browser meeting, the user can speak and hear remote
  audio for at least 30 minutes while 2brain Rec devices remain selected.
- **SC-003**: Remote meeting audio remains absent from the virtual microphone
  path at or below the accepted loopback threshold.
- **SC-004**: Local and remote track evidence stays aligned within 100 ms during
  a 30-minute wired or built-in-device pilot call.
- **SC-005**: Wired or built-in-device pilot calls stay below 0.1% dropped audio
  frames; Bluetooth and AirPods-class pilot calls stay below 0.5% dropped audio
  frames.
- **SC-006**: A 5-minute backend or network outage does not interrupt live call
  passthrough.
- **SC-007**: Device disconnect or route change invalidates readiness within 5
  seconds and gives the user a visible recovery state.
- **SC-008**: Diagnostic output for route failures contains actionable status
  categories and contains no raw audio, transcript text, credentials, tokens, or
  signed URLs by default.

## Assumptions

- The previous macOS publication proof remains the baseline: both virtual
  devices can already be installed and seen by macOS.
- This feature targets the same internal macOS pilot audience and device matrix
  as the publication slice.
- Readiness checks are manual/user-triggered for this feature; assisted
  auto-start remains out of scope.
- Backend transcription, upload, MinIO storage, server deletion, and MediaScribe
  integration remain out of scope for this feature.
- The first passing release candidate may support only the approved browser
  meeting targets listed in the existing macOS QA matrix.
