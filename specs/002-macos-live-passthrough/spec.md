# Feature Specification: macOS Live Audio Passthrough Foundation

**Feature Branch**: `002-macos-live-passthrough`

**Created**: 2026-05-31

**Status**: Historical passthrough foundation; superseded by later route/capture slices

**Input**: User description: "Continue macOS development after the publication proof: implement real live audio passthrough and capture readiness so 2brain Rec becomes usable for calls, not only visible in macOS."

**Implementation Slice Note**: During implementation, this feature was narrowed
to the safe foundation required before release-ready passthrough: private app
I/O, fail-closed public devices, readiness-blocking UI, diagnostics, evidence
models, lifecycle gates, and synthetic validation. Real browser-call readiness
and release-ready bidirectional audio movement are intentionally deferred to the
next Spec Kit feature so the product does not claim `ready` from incomplete
evidence.

## Clarifications

### Session 2026-05-31

- Q: How should the app prove the speaker path during readiness check? → A: Use a short audible test sound after the user explicitly presses `Run Check`.
- Q: How should the app prove the microphone path during readiness check? → A: Ask the user to speak or tap the microphone for about 3 seconds during `Run Check`.
- Q: May readiness checks save audio evidence during development? → A: Development builds may temporarily save short local debug clips for verification, but release builds must disable and clean this behavior before acceptance.
- Q: When should live passthrough become active? → A: After a successful `Run Check`, passthrough remains active for calls until the user disables it, the app exits, selected devices change, or the route becomes degraded; recording must not start automatically.
- Q: Where should the active audio route indicator be visible? → A: For now, show `Audio route active` in the macOS menu bar and in the main app window, distinct from the stronger recording indicator.
- Q: What latency standard should live passthrough meet? → A: Use a clean-room Krisp-like near-zero perceived-latency target; supported built-in and wired routes become degraded above 30 ms added 2brain Rec route latency.
- Q: How should Bluetooth and AirPods-class routes be treated? → A: Use a clean-room Krisp-like managed-route policy: built-in and wired routes are strict release-quality paths, while Bluetooth and AirPods-class routes are supported only with profile detection, warning/degraded states, and separate pilot acceptance.
- Q: Should the architecture include a private app I/O transport like Krisp? → A: Yes; use public `2brain Rec Microphone` and `2brain Rec Speaker` devices for meeting apps, plus a private app I/O transport between the HAL driver and desktop audio engine.
- Q: How should public devices behave when private app I/O or the desktop audio engine is gone? → A: Use Krisp-like fail-closed behavior: stop claiming ready immediately, make public devices hidden or unavailable when app I/O is gone, and show/recover them only after the desktop audio engine restores the route.
- Q: Should 2brain Rec manage system/default audio devices like Krisp? → A: Use Krisp-like guided device management only after explicit user action, with visible route-active state, reversible setup, working-device tracking, volume mapping, and recovery assistance.
- Q: What loopback leakage standard should virtual microphone output meet? → A: Use Krisp-like AEC/reference-stream separation; release-ready built-in and wired routes must keep remote speaker leakage in the virtual microphone at least 45 dB below speaker reference and not intelligible.
- Q: When should an expected local or remote track count as missing or silent? → A: Use Krisp-like stream-health monitoring: natural user silence is not a failure by itself; an expected route becomes degraded when it is not capturable or has no valid frames for a full 3-second health interval, while longer non-critical audio-quality warnings use a 30-second observation window.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prove Call-Ready Audio Routes (Priority: P1)

As an internal macOS user, I want 2brain Rec to keep publication-only devices
separate from call readiness, so that the app does not say it is ready until a
later real-route check proves the selected microphone and speaker paths.

**Why this priority**: Device publication is already proven, but the product is
not useful until real bidirectional audio movement is proven. This foundation
story keeps the current `not ready for calls yet` state truthful and prepares
the evidence gates that a later feature must satisfy.

**Independent Test**: Can be tested by installing the current macOS build,
selecting physical input/output devices, running the readiness check, and
confirming the app blocks ready when only publication or scaffolded route
evidence exists.

**Acceptance Scenarios**:

1. **Given** both 2brain Rec virtual devices are visible and physical devices are
   selected, **When** the user runs the readiness check, **Then** the app plays a
   short audible test sound, asks the user to speak or tap the microphone for
   about 3 seconds, and keeps ready blocked until a later real-route feature
   accepts microphone and speaker audio movement evidence.
2. **Given** the physical microphone is muted, unavailable, or silent, **When**
   the user runs the readiness check, **Then** the app reports microphone path
   failure and does not show ready.
3. **Given** the physical speaker path is unavailable or muted, **When** the user
   runs the readiness check, **Then** the app reports speaker path failure and
   does not show ready.
4. **Given** only virtual-device visibility is confirmed, **When** no real audio
   movement has been proven, **Then** the app continues to show not ready.
5. **Given** readiness has not yet been accepted by a real-route feature,
   **When** the user joins a browser call before starting capture, **Then** this
   foundation slice does not claim browser-call readiness.
6. **Given** the user explicitly enables or runs route setup, **When** 2brain
   Rec needs the meeting app or macOS default route to use 2brain Rec devices,
   **Then** the app may guide or apply the change visibly, track the selected
   physical working devices, and provide a reversible recovery path.

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
3. **Given** remote speaker audio is present and the local user is silent,
   **When** the virtual microphone output is evaluated in this foundation slice,
   **Then** synthetic leakage policy and release evidence requirements are
   recorded; real browser-meeting leakage acceptance remains blocked until live
   route movement is accepted.
4. **Given** the desktop app or backend-facing workflow is degraded, **When** the
   meeting continues, **Then** live call audio remains usable or the app tells
   the user to stop using the route before audio loss occurs.
5. **Given** a real passthrough check fails during a call, **When** the app
   detects the failure, **Then** it shows a visible degraded state and a safe
   recovery path instead of claiming ready.
6. **Given** a supported built-in or wired route is active, **When** 2brain Rec
   added route latency exceeds 30 ms, **Then** the app marks the route degraded
   and blocks release readiness instead of claiming the Krisp-like latency
   target.
7. **Given** private app I/O or the desktop audio engine exits, crashes, or is
   otherwise unavailable, **When** the HAL driver detects the loss, **Then** the
   route fails closed by stopping ready claims and making public devices hidden
   or unavailable until the app engine recovers and revalidates the route.

---

### User Story 3 - Produce Separate Track Evidence (Priority: P2)

As the product owner, I want evidence that local microphone audio and remote
speaker audio are captured as separate, aligned tracks, so that the next backend
and transcription slices can rely on clean source separation.

**Why this priority**: Backend transcription quality depends on track separation,
but readiness and live call safety must come first.

**Independent Test**: Can be tested by producing synthetic/local track evidence
and confirming diagnostics/finalization models can represent presence,
separation, alignment, dropout state, missing frames, and ordinary silence.

**Acceptance Scenarios**:

1. **Given** the user records a controlled meeting, **When** local and remote
   audio are both present, **Then** the session records separate local and remote
   track evidence.
2. **Given** an expected local or remote route is active during readiness, a
   pilot stimulus, or capture, **When** the route is not capturable or has no
   valid frames for a full 3-second health interval, **Then** the app marks that
   track route degraded instead of presenting a complete capture.
3. **Given** the local user is naturally silent while valid input frames continue
   to arrive, **When** capture health is evaluated, **Then** the app does not
   mark the local track degraded solely because speech is absent.
4. **Given** a 30-minute pilot call completes, **When** track evidence is
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
4. **Given** a Bluetooth or AirPods-class device is selected, **When** the route
   uses a profile with materially worse latency, dropout rate, valid-frame
   continuity, profile stability, or one-sided audio, **Then** the app applies
   the managed-route policy by showing warning or degraded state instead of
   treating the route as equivalent to built-in or wired devices.

### Edge Cases

- The user selects a 2brain Rec virtual device as its own physical source or
  output.
- A physical microphone or speaker is visible but silent, muted, permission
  blocked, or unavailable to the current user.
- A meeting target changes audio devices after readiness passes.
- macOS or a meeting app changes the default microphone or speaker after the
  user has enabled the 2brain Rec route.
- A browser restarts or drops remote audio while capture is active.
- Bluetooth or AirPods-class devices switch between high-quality output and
  call-oriented input/output profiles.
- Bluetooth or AirPods-class routes add latency, dropped frames, profile
  switches, or one-sided audio outside 2brain Rec control even when the 2brain
  Rec route itself is functioning.
- The app restarts while the virtual devices remain selected in a meeting.
- Private app I/O or the desktop audio engine exits while a meeting app still
  has 2brain Rec devices selected.
- The user starts readiness checks while another app is already using the
  selected physical devices.
- Audio movement becomes delayed, distorted, one-sided, or intermittently
  missing during a long call.
- A user is naturally silent while the selected input route continues to deliver
  valid frames.
- A selected stream client remains present but stops delivering valid frames or
  repeatedly produces empty buffers.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST distinguish virtual-device visibility from real
  call readiness in all user-facing states.
- **FR-002**: The system MUST define and enforce the evidence gate requiring
  selected physical microphone audio to reach the virtual microphone path before
  any future ready state can be shown.
- **FR-003**: The system MUST define and enforce the evidence gate requiring
  virtual speaker audio to reach the selected physical speaker path before any
  future ready state can be shown.
- **FR-004**: The system MUST keep remote speaker audio out of the virtual
  microphone path.
- **FR-004a**: The system MUST separate meeting-facing virtual devices from
  internal audio transport by using public `2brain Rec Microphone` and
  `2brain Rec Speaker` devices for meeting apps plus a private app I/O transport
  between the HAL driver and desktop audio engine.
- **FR-004b**: Public 2brain Rec virtual devices MUST fail closed when private
  app I/O or the desktop audio engine is unavailable: they MUST stop claiming
  ready, become hidden or unavailable to meeting apps, and return only after the
  app engine recovers and revalidates the route.
- **FR-004c**: The system MUST use Krisp-like AEC/reference-stream separation:
  speaker audio MUST be available as a reference stream for echo and leakage
  monitoring, and release-ready built-in or wired routes MUST keep remote speaker
  leakage in the virtual microphone at least 45 dB below the speaker reference
  and not intelligible.
- **FR-005**: The system MUST block ready when either physical path is missing,
  silent, muted, self-routed, disconnected, or otherwise unproven.
- **FR-006**: The system MUST provide a user-triggered readiness check that is
  safe to run before a call, does not start hidden recording, uses a short
  audible test sound after the user explicitly starts the check, and asks the
  user to speak or tap the microphone for about 3 seconds to prove the physical
  microphone path.
- **FR-006a**: The system MAY manage or restore 2brain Rec microphone and
  speaker selection using Krisp-like guided device management only after explicit
  user action such as `Run Check`, `Enable route`, or an accepted recovery
  prompt.
- **FR-006b**: Guided device management MUST remain visible and reversible,
  track the selected physical working microphone and speaker, distinguish 2brain
  Rec virtual devices from physical devices, and avoid changing system or
  meeting audio routes silently in the background.
- **FR-006c**: When guided device management maps volume or mute state between a
  physical working device and a 2brain Rec virtual device, the app MUST keep the
  user-visible route state accurate and MUST NOT use volume or mute changes as a
  hidden recording or capture signal.
- **FR-007**: The system MUST add local outage and degradation gates so live
  microphone and speaker passthrough can remain independent from backend,
  upload, or transcription workflows in the later real-route feature.
- **FR-007a**: The system MUST model active non-recording passthrough separately
  from recording so a later successful readiness check can keep call routing
  active without starting capture.
- **FR-008**: The system MUST surface a degraded state when live passthrough is
  no longer proven during a call.
- **FR-008a**: Live passthrough MUST target clean-room Krisp-like near-zero
  perceived latency, use bounded low-latency buffering, and mark supported
  built-in or wired routes degraded when added 2brain Rec route latency exceeds
  30 ms.
- **FR-008b**: Bluetooth and AirPods-class routes MUST follow a clean-room
  Krisp-like managed-route policy: detect profile changes, distinguish them from
  built-in and wired release-quality routes, record profile class and
  bidirectional input/output availability, and show warning or degraded states
  when the profile switches mid-call, either direction stops delivering valid
  frames for a full 3-second health interval, dropped frames exceed the
  Bluetooth pilot threshold, or measured latency evidence fails the separate
  Bluetooth pilot acceptance criteria.
- **FR-009**: The system MUST provide a one-action way to stop active capture
  from a visible local surface whenever capture is active.
- **FR-009a**: The system MUST show active non-recording passthrough as
  `Audio route active` in the macOS menu bar and main app window, visually and
  semantically distinct from `Recording`.
- **FR-010**: The system MUST define local and remote track evidence separately
  for use when audio-recording mode becomes active.
- **FR-011**: The system MUST mark capture degraded when an expected local or
  remote track is not capturable or has no valid frames for a full 3-second
  health interval, repeatedly produces empty buffers during expected active
  stimulus, exceeds dropout thresholds, or loses continuity.
- **FR-011a**: Ordinary user silence with valid input frames MUST NOT by itself
  mark capture degraded.
- **FR-011b**: The system MUST maintain Krisp-like stream-health evidence for
  each expected track, including capturability status, captured/stored/retrieved
  or processed frame counts, dropped frame counts, empty-buffer events, and last
  valid frame timing.
- **FR-012**: The system MUST expose enough timing and dropout information for
  the app to explain alignment and continuity health to the user or operator.
- **FR-013**: The system MUST require readiness to be rechecked after physical
  device disconnect, output route change, Bluetooth profile change, or meeting
  target device change.
- **FR-014**: The system MUST provide actionable diagnostics for microphone path,
  speaker path, loopback rejection, track separation, and device-change failures.
- **FR-015**: Diagnostics MUST NOT include raw audio, transcript text,
  credentials, tokens, signed URLs, or hidden recording artifacts by default.
- **FR-015a**: Development builds MAY temporarily save short local debug clips
  from explicit readiness checks for verification, but these clips MUST be
  visibly marked as development-only, stored locally, excluded from diagnostic
  export by default, and disabled plus removed before release acceptance.
- **FR-016**: Browser meeting validation evidence MUST list Chrome, Opera,
  Yandex Browser, and Yandex Telemost-in-browser as blocked/not accepted until a
  later feature proves real browser-call passthrough.
- **FR-017**: The feature MUST NOT introduce a no-driver fallback, silent
  recording, invisible capture, or direct desktop-to-MediaScribe upload.
- **FR-018**: The system MUST keep the existing publication proof valid while
  adding real route readiness.

### Key Entities

- **Readiness Check**: A user-visible verification attempt for microphone path,
  speaker path, self-routing, loopback rejection, and current device state.
- **Active Audio Route**: A ready, non-recording state where 2brain Rec
  passthrough is active for calls but no meeting audio is being saved.
- **Audio Route Evidence**: The result that proves or rejects real movement on a
  specific microphone or speaker path.
- **Private App I/O Transport**: An internal, non-user-selectable audio path
  between the HAL driver and desktop audio engine used for live passthrough,
  processing, capture evidence, and route health without exposing extra meeting
  devices.
- **Capture Track Evidence**: The local record that a local or remote track was
  present, separate, aligned, and continuous enough to trust.
- **Stream Health Evidence**: Per-track capturability and continuity metadata
  used to distinguish ordinary user silence from route failure, empty buffers,
  dropped frames, or missing valid audio frames.
- **Development Debug Clip**: A temporary local audio snippet created only by an
  explicit development readiness check to verify the audio path before release.
- **Degraded Audio State**: A visible state explaining why the app is not safe to
  use for calls or why an active capture is incomplete.
- **Device Change Event**: A route-affecting change that invalidates prior
  readiness and requires recheck.

### Constitutional Requirements *(mandatory for 2brain Rec)*

- **Capture/Driver Impact**: This feature directly touches macOS audio routing,
  passthrough foundations, capture readiness gates, degraded states, and
  diagnostics. It must block ready when only publication is proven, keep the
  driver-first model, and defer release-ready audio movement to the next feature.
  The public virtual devices must remain meeting-facing surfaces, while internal
  audio movement uses private app I/O transport rather than extra user-selectable
  meeting devices.
- **Visible Control Impact**: The feature must not start hidden recording during
  readiness checks or active audio route use. Active non-recording passthrough
  must be visible in the menu bar and main window as route activity, not as
  recording. Any active capture must keep visible local indication and
  one-action stop.
- **Data Boundary Impact**: The feature is local macOS audio readiness and local
  capture evidence only. It must not add MediaScribe upload, Langfuse traces, LLM
  calls, external analytics, or new network egress.
- **Secrets Impact**: The feature must not store or expose credentials. Any
  diagnostic bundle must preserve redaction for credentials, tokens, signed URLs,
  raw audio, and transcript text.
- **Retention/Deletion Impact**: The feature may create local capture and
  diagnostic metadata. Development builds may also create temporary local debug
  clips from explicit checks. Any created artifact must be registered as
  app-managed local data, clearly marked, and eligible for local cleanup and the
  existing local deletion/reporting rules.
- **Audit Impact**: Readiness pass/fail, capture start/stop, degraded state,
  guided device-management actions, device-change invalidation, and diagnostic
  export must be auditable without storing raw audio or transcripts in audit
  payloads.
- **UX/Brand/Accessibility Impact**: UI changes must use original 2brain Rec
  language, accessible non-color-only states, localization-safe copy, and clear
  brand distance from Krisp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a fresh local install, an internal user sees both virtual
  devices published while the app remains `not ready for calls yet` until real
  microphone and speaker path checks are implemented and accepted by a later
  feature.
- **SC-001a**: Publication-only readiness checks never show ready; they record
  explicit failure reasons and recovery actions.
- **SC-001b**: Active non-recording passthrough has a distinct model and UI copy
  from recording, but release acceptance remains blocked until real route
  movement is proven.
- **SC-001c**: After explicit user approval, guided device management can set or
  restore the required 2brain Rec route and can reverse the change without
  leaving the user unsure which physical microphone and speaker are active.
- **SC-002**: Supported browser meeting validation is recorded as blocked/not
  accepted for this foundation slice, with the required future matrix preserved.
- **SC-002a**: Supported built-in and wired pilot routes keep added 2brain Rec
  route latency at or below 30 ms during live passthrough; any route above that
  threshold is visibly degraded and is not release-ready.
- **SC-002b**: Killing or crashing the desktop audio engine during an active
  route makes public 2brain Rec devices hidden or unavailable within 5 seconds;
  relaunching the app restores the devices only after route recovery and
  revalidation.
- **SC-003**: Synthetic remote-to-mic leakage validation records the `<= -45 dB`
  policy, while real browser-meeting leakage remains blocked/not accepted.
- **SC-004**: Local and remote track evidence models can represent alignment,
  dropout, missing valid frames, and ordinary silence without storing raw audio.
- **SC-004a**: During readiness and controlled pilot stimulus, an expected route
  that stops delivering valid frames is marked degraded within 3 seconds, while
  a naturally silent user with valid input frames is not marked degraded solely
  because no speech is detected.
- **SC-004b**: Non-critical audio-quality warnings use a 30-second observation
  window before warning the user, while hard route or capturability failures
  still fail within the 3-second health interval.
- **SC-005**: Wired/built-in and Bluetooth/AirPods-class dropout thresholds are
  represented in policy and evidence, but physical pilot acceptance remains
  blocked/not accepted until real route movement exists.
- **SC-005a**: Bluetooth and AirPods-class pilot evidence is recorded as a
  separate managed-route gate and must not be marked equivalent to built-in or
  wired release-quality routes in this foundation slice.
- **SC-006**: A 5-minute backend or network outage does not interrupt live call
  passthrough.
- **SC-007**: Device disconnect or route change invalidates readiness within 5
  seconds and gives the user a visible recovery state.
- **SC-008**: Diagnostic output for route failures contains actionable status
  categories and contains no raw audio, transcript text, credentials, tokens, or
  signed URLs by default.
- **SC-009**: Before release acceptance, development debug clips are disabled by
  default and no local debug audio remains after running the cleanup path.

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
