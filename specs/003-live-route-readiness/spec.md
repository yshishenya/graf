# Feature Specification: macOS Live Route Readiness

**Feature Branch**: `003-live-route-readiness`

**Created**: 2026-05-31

**Status**: Historical route-readiness slice; superseded by later capture architecture

**Input**: User description: "Implement real macOS bidirectional audio route readiness for 2brain Rec: prove physical microphone audio reaches 2brain Rec Microphone, prove 2brain Rec Speaker reaches the selected physical output, keep app not ready until both paths pass, preserve private app I/O fail-closed behavior, measure built-in/wired added latency <=30 ms, enforce remote-to-mic leakage <= -45 dB, and produce browser-call evidence for Chrome, Opera, Yandex Browser, and Yandex Telemost without starting hidden recording."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pass Real Route Readiness (Priority: P1)

As an internal macOS user, I want 2brain Rec to prove that my selected physical
microphone reaches the meeting-facing virtual microphone and that the
meeting-facing virtual speaker reaches my selected physical output, so that the
app shows ready only when a real call route can work.

**Why this priority**: The foundation slice can publish devices and fail closed,
but the product is still not usable for calls until both live audio paths are
proven.

**Independent Test**: Install the current macOS build, select physical
input/output devices, run the user-triggered readiness check, and confirm the app
shows ready only after both microphone and speaker path evidence pass.

**Acceptance Scenarios**:

1. **Given** both 2brain Rec virtual devices are visible and a physical
   microphone/output are selected, **When** the user runs the readiness check,
   **Then** the app proves microphone movement and speaker movement before
   showing ready.
2. **Given** the microphone path is muted, unavailable, self-routed, or silent
   without valid frames, **When** the user runs the readiness check, **Then** the
   app reports microphone failure and keeps ready blocked.
3. **Given** the speaker path is unavailable, muted, self-routed, or inaudible,
   **When** the user runs the readiness check, **Then** the app reports speaker
   failure and keeps ready blocked.
4. **Given** only virtual-device publication is proven, **When** readiness is
   evaluated, **Then** the app keeps `not ready for calls yet`.

---

### User Story 2 - Keep Browser Call Audio Usable (Priority: P1)

As a user in a supported browser meeting, I want to speak and hear remote audio
through 2brain Rec devices after readiness passes, so that joining a call does
not require switching away from the virtual devices.

**Why this priority**: Passing readiness is only valuable if the selected browser
can actually use the route for live conversation.

**Independent Test**: Join each supported browser target with 2brain Rec
microphone and speaker selected, speak locally, play remote speech, and confirm
live call audio remains usable without starting recording.

**Acceptance Scenarios**:

1. **Given** readiness has passed, **When** Chrome uses `2brain Rec Microphone`
   and `2brain Rec Speaker`, **Then** the user can speak and hear remote audio
   for a controlled call.
2. **Given** readiness has passed, **When** Opera, Yandex Browser, or Yandex
   Telemost-in-browser uses the same route, **Then** the route either passes with
   evidence or is explicitly recorded as blocked/not accepted for that target.
3. **Given** private app I/O or the desktop audio engine exits during route use,
   **When** the driver detects heartbeat loss, **Then** public devices fail
   closed within 5 seconds and return only after app recovery and route
   revalidation.
4. **Given** backend, upload, transcription, or network workflow is unavailable,
   **When** live route readiness is active, **Then** live call audio remains
   usable or the app visibly degrades before audio loss.

---

### User Story 3 - Enforce Leakage And Latency Gates (Priority: P1)

As the product owner, I want release-ready built-in and wired routes to meet
strict leakage and latency thresholds, so that 2brain Rec does not introduce
feedback, echo, or distracting delay.

**Why this priority**: A route that technically passes audio but leaks remote
speaker audio into the microphone or adds perceptible delay is not call-ready.

**Independent Test**: Run controlled stimulus on built-in and wired routes,
measure added route latency and remote-to-mic leakage, and confirm release
readiness is blocked when thresholds fail.

**Acceptance Scenarios**:

1. **Given** a built-in or wired route is active, **When** added 2brain Rec route
   latency is measured, **Then** the route passes only when added latency is at
   or below 30 ms.
2. **Given** remote speaker audio is present and the local user is silent,
   **When** virtual microphone output is measured against the speaker reference,
   **Then** remote speaker leakage remains at least 45 dB below reference and is
   not intelligible.
3. **Given** latency or leakage exceeds the threshold, **When** the app updates
   route health, **Then** it marks the route degraded and blocks release-ready
   status.

---

### User Story 4 - Invalidate And Recover Routes (Priority: P2)

As a user, I want 2brain Rec to invalidate readiness when devices or meeting
targets change, so that I do not keep using a stale route after macOS or the
browser changes audio paths.

**Why this priority**: Real calls involve route changes, Bluetooth profile
switches, browser restarts, and device reconnects; stale ready states are unsafe.

**Independent Test**: Pass readiness, change physical devices, switch browser
devices, disconnect output, or switch a Bluetooth profile, and confirm readiness
invalidates within 5 seconds with a clear recovery action.

**Acceptance Scenarios**:

1. **Given** readiness has passed, **When** the physical microphone or output
   changes, **Then** readiness becomes stale within 5 seconds.
2. **Given** readiness has passed, **When** a supported browser changes its
   selected microphone or speaker, **Then** readiness becomes stale and the app
   asks for recheck.
3. **Given** a Bluetooth or AirPods-class route is selected, **When** the route
   profile changes or one direction stops delivering valid frames, **Then** the
   app shows warning/degraded state instead of treating it as built-in/wired
   parity.

### Edge Cases

- The user selects `2brain Rec Microphone` or `2brain Rec Speaker` as a physical
  working device.
- The physical microphone is visible but muted, permission-blocked, silent, or
  delivering empty buffers.
- The physical output is visible but muted, disconnected, or routed to an
  aggregate/multi-output device.
- A browser keeps stale device IDs after the app or driver restarts.
- `coreaudiod` restarts while the app is open.
- The desktop app exits while a meeting target still has 2brain Rec devices
  selected.
- Remote speech is loud enough to challenge leakage rejection while the local
  microphone is silent.
- Bluetooth devices switch between output-only and call-oriented profiles.
- The user naturally stays silent while valid microphone frames continue.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST keep `not ready for calls yet` until both
  microphone and speaker live route evidence pass.
- **FR-002**: The system MUST prove selected physical microphone audio reaches
  `2brain Rec Microphone` before showing ready.
- **FR-003**: The system MUST prove audio sent to `2brain Rec Speaker` reaches
  the selected physical output before showing ready.
- **FR-004**: The readiness check MUST be explicitly user-triggered and MUST NOT
  start recording or hidden capture.
- **FR-005**: The app MUST distinguish publication, checking, ready, stale,
  degraded, and failed states in user-facing copy and diagnostics.
- **FR-006**: The route MUST reject self-routing where a 2brain Rec virtual
  device is selected as a physical working device.
- **FR-007**: Built-in and wired routes MUST be marked degraded when added
  2brain Rec route latency exceeds 30 ms.
- **FR-008**: Built-in and wired routes MUST be marked degraded when remote
  speaker leakage into the virtual microphone is less than 45 dB below the
  speaker reference or is intelligible.
- **FR-009**: Aggregate and multi-output speaker routes MUST be recorded as
  managed/blocked unless the selected physical output path can be measured with
  the same speaker evidence, latency, and leakage criteria as a direct built-in
  or wired route.
- **FR-010**: Browser-call validation MUST record evidence for Chrome, Opera,
  Yandex Browser, and Yandex Telemost-in-browser before release readiness.
- **FR-011**: Private app I/O fail-closed behavior MUST remain active during
  route readiness and browser-call validation.
- **FR-012**: Backend, upload, transcription, and network failure MUST NOT be
  allowed to interrupt live call passthrough after readiness passes.
- **FR-013**: Readiness MUST become stale within 5 seconds after physical device,
  output route, Bluetooth profile, app heartbeat, or browser target device
  changes.
- **FR-014**: Bluetooth and AirPods-class routes MUST remain managed pilot routes
  with profile, dropout, one-sided-audio, valid-frame, and measured-latency
  evidence; they MUST NOT be treated as built-in/wired release-quality routes.
- **FR-015**: Diagnostics MUST include route status, failure category, recovery
  action, latency/leakage measurements, and browser target evidence without raw
  audio, transcript text, credentials, tokens, or signed URLs.
- **FR-016**: Browser target evidence MUST be metadata-only by default and MUST
  NOT include raw audio, transcript text, credentials, tokens, signed URLs, or
  meeting content.
- **FR-017**: Active non-recording route state MUST be visible and distinct from
  recording; active capture, when later enabled, MUST still have one-action stop.
- **FR-018**: The feature MUST NOT add no-driver fallback, invisible recording,
  silent capture, direct desktop-to-MediaScribe upload, or new network egress.

### Key Entities

- **Live Route Readiness Result**: The current pass/fail/stale/degraded evidence
  for microphone and speaker paths.
- **Microphone Path Evidence**: Proof that selected physical microphone audio
  reaches the meeting-facing virtual microphone path.
- **Speaker Path Evidence**: Proof that audio sent to the meeting-facing virtual
  speaker reaches the selected physical output.
- **Browser Target Evidence**: Per-browser proof that live call audio is usable
  through 2brain Rec devices.
- **Leakage Measurement**: Comparison between remote speaker reference and
  virtual microphone output.
- **Latency Measurement**: Added 2brain Rec route latency for the selected route.
- **Route Invalidation Event**: A physical, browser, app, or profile change that
  makes prior readiness stale.

### Constitutional Requirements *(mandatory for 2brain Rec)*

- **Capture/Driver Impact**: This feature directly touches macOS audio routing,
  private app I/O, passthrough, degraded states, and driver readiness. It must
  remain driver-first, preserve fail-closed public devices, prevent loopback, and
  define measurable latency/leakage/recovery gates.
- **Visible Control Impact**: Readiness checks and active route state must be
  visible and user-triggered. The feature must not start recording, must not
  create invisible capture, and must preserve one-action stop for any active
  capture surface touched by this work.
- **Data Boundary Impact**: This feature is local macOS route readiness only. It
  must not add MediaScribe upload, Langfuse traces, LLM calls, analytics, or new
  network egress.
- **Secrets Impact**: No credentials, tokens, signed URLs, passwords, or live
  credential paths may be stored in client state, diagnostics, logs, or evidence
  artifacts.
- **Retention/Deletion Impact**: Route evidence and diagnostics are local
  app-managed metadata. Any temporary development audio stimulus or debug clip
  must remain explicit, local, release-disabled by default, and cleanable.
- **Audit Impact**: Readiness check start/end, route pass/fail, stale/degraded
  transitions, browser validation, private app I/O loss/recovery, and diagnostic
  export must be auditable without raw audio or transcript payloads.
- **UX/Brand/Accessibility Impact**: UI must use original 2brain Rec language,
  accessible non-color-only states, localization-safe copy, keyboard reachable
  controls, and brand-distance from Krisp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a fresh local install, the app moves from `not ready for calls
  yet` to ready only after both microphone and speaker live route evidence pass.
- **SC-002**: Publication-only evidence never produces ready state in app UI,
  diagnostics, or release checklist.
- **SC-003**: On built-in and wired routes, added 2brain Rec latency is at or
  below 30 ms when marked release-ready.
- **SC-004**: On built-in and wired routes, remote speaker leakage into the
  virtual microphone is at least 45 dB below speaker reference and is not
  intelligible when marked release-ready.
- **SC-005**: Killing the desktop audio engine makes public 2brain Rec devices
  hidden or unavailable within 5 seconds, and relaunch restores them only after
  route recovery and revalidation.
- **SC-006**: Chrome, Opera, Yandex Browser, and Yandex Telemost-in-browser each
  have pass or blocked/not accepted evidence before release readiness.
- **SC-007**: A 5-minute backend/network outage does not interrupt live call
  passthrough after readiness passes.
- **SC-008**: Physical device, browser target, or Bluetooth profile changes make
  readiness stale within 5 seconds and show a recovery action.
- **SC-009**: Diagnostic output for readiness failures contains actionable
  status and no raw audio, transcript text, credentials, tokens, or signed URLs.

## Assumptions

- Feature `002-macos-live-passthrough` is the foundation baseline and already
  provides publication proof, private app I/O heartbeat, fail-closed behavior,
  route-state models, diagnostics scaffolding, and synthetic harnesses.
- The first release-ready route target is built-in or wired physical
  microphone/output on Apple Silicon macOS.
- Bluetooth and AirPods-class routes remain managed pilot routes and do not
  block built-in/wired readiness unless selected by the user.
- Browser validation can record a target as blocked/not accepted when the
  browser cannot be safely validated in the current environment.
- Backend upload, transcription, storage, MediaScribe, Langfuse, server deletion,
  and assisted auto-start remain out of scope.
