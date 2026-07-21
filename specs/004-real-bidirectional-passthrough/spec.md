# Feature Specification: macOS Real Bidirectional Passthrough

**Feature Branch**: `004-real-bidirectional-passthrough`

**Created**: 2026-05-31

**Status**: Historical bidirectional passthrough slice; not an active product path

**Input**: User description: "Implement real macOS bidirectional passthrough: selected physical microphone audio must feed 2brain Rec Microphone, audio sent to 2brain Rec Speaker must play through the selected physical output with minimal added latency, browser calls must remain usable through the virtual devices, no hidden recording may start, visible readiness and stop controls must remain, diagnostics must be metadata-only, private app I/O fail-closed behavior must remain, and implementation must preserve the KRISP-like driver-first routing model already documented."

## Current SDD Stabilization Decision *(2026-06-01)*

Independent code review of the first live-passthrough implementation found that
the feature is not ready for live acceptance. The default installed app may
publish the virtual devices in a fail-closed, non-running state for installer
and Core Audio publication proof, but this safe mode does not satisfy live
passthrough acceptance.

Before this feature can be accepted as implemented, the following stabilization
gates are mandatory:

- AudioUnit realtime callbacks must not allocate Swift arrays, format strings,
  call `Date`, write files, or perform diagnostics/logging on the audio render
  thread.
- The shared-memory ring-buffer contract must be explicit, tested in Swift and
  C++, and must not let a producer race the consumer by mutating the consumer
  read index without a documented safe protocol.
- Readiness must be based on authoritative live route evidence: bridge start
  state, fresh heartbeat, frame continuity, underrun/degraded counters, latency
  evidence, leakage evidence, and recovery state. Environment flags, device
  visibility, and physical default selection are not sufficient.
- UI lifecycle must not own live route startup, heartbeat ownership, or app-side
  AudioUnit orchestration.
- Synthetic fixtures may validate policy and contracts, but they must not be
  presented as physical/browser live audio acceptance evidence.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Speak Through 2brain Rec Microphone (Priority: P1)

As a macOS user, I want the microphone selected inside 2brain Rec to feed
`2brain Rec Microphone`, so that meeting apps can hear me when the virtual
microphone is selected.

**Why this priority**: Without physical microphone passthrough, the virtual
microphone is only a published device and cannot support real calls.

**Independent Test**: Select a physical microphone in 2brain Rec, select
`2brain Rec Microphone` in a browser meeting or Core Audio test target, speak
locally, and confirm the receiving target gets live microphone audio while the
app stays in visible non-recording route state.

**Acceptance Scenarios**:

1. **Given** the driver is installed, the app heartbeat is alive, and a physical
   microphone is selected, **When** the user enables live route readiness,
   **Then** local microphone audio is delivered to `2brain Rec Microphone`.
2. **Given** the selected physical microphone is muted, permission-blocked,
   silent, disconnected, or returns empty frames, **When** passthrough is
   evaluated, **Then** the app marks the microphone path failed or degraded and
   does not claim ready.
3. **Given** `2brain Rec Microphone` is selected as the physical input, **When**
   passthrough is evaluated, **Then** self-routing is rejected and no loop is
   created.

---

### User Story 2 - Hear 2brain Rec Speaker Through Physical Output (Priority: P1)

As a macOS user, I want audio sent to `2brain Rec Speaker` by the meeting app to
play through my selected physical output, so that remote participants remain
audible while I use 2brain Rec devices.

**Why this priority**: A virtual speaker that does not mirror remote audio to
the user makes browser calls unusable.

**Independent Test**: Select a physical speaker/headphones in 2brain Rec, select
`2brain Rec Speaker` in a browser meeting or Core Audio test target, play remote
speech or stimulus, and confirm the user hears it through the selected physical
output without routing it into the virtual microphone.

**Acceptance Scenarios**:

1. **Given** a physical output is selected, **When** a meeting app sends audio to
   `2brain Rec Speaker`, **Then** that audio is played through the selected
   physical output.
2. **Given** the physical output is disconnected, muted, permission-blocked, or
   unavailable, **When** passthrough is evaluated, **Then** the app marks the
   speaker path failed or degraded and shows a recovery action.
3. **Given** remote speaker audio is playing and local microphone is silent,
   **When** the route is measured, **Then** remote audio is not fed back into
   `2brain Rec Microphone` above the accepted leakage threshold.

---

### User Story 3 - Join Browser Calls With Both Virtual Devices (Priority: P1)

As a user in a supported browser meeting, I want to select `2brain Rec
Microphone` and `2brain Rec Speaker` and complete a real conversation, so that
2brain Rec can become the default meeting audio route.

**Why this priority**: Passing isolated mic and speaker tests is not enough; the
route must survive real browser call behavior and device selection semantics.

**Independent Test**: Join controlled Chrome, Opera, Yandex Browser, and Yandex
Telemost-in-browser calls with 2brain Rec devices selected, speak locally, play
remote speech, and record pass or blocked/not accepted evidence for each target.

**Acceptance Scenarios**:

1. **Given** Chrome selects `2brain Rec Microphone` and `2brain Rec Speaker`,
   **When** a controlled call runs, **Then** local speech and remote audio remain
   usable for the call without starting recording.
2. **Given** Opera, Yandex Browser, or Yandex Telemost-in-browser selects the
   same devices, **When** the controlled call runs, **Then** each target is
   recorded as passed or blocked/not accepted with concrete metadata-only
   evidence.
3. **Given** a browser keeps stale device IDs after app, driver, or `coreaudiod`
   restart, **When** the user rechecks the route, **Then** the app invalidates
   stale readiness and guides the user to reselect or recheck devices.

---

### User Story 4 - Fail Closed And Recover During Live Passthrough (Priority: P2)

As a user, I want live passthrough to stop safely when the desktop app or route
engine fails, and recover only after the route is valid again, so that meeting
apps do not silently use broken virtual devices.

**Why this priority**: Real-time audio can fail in ways that are worse than a
clear blocked state; the driver-first fail-closed model is a trust requirement.

**Independent Test**: Start a validated live route, kill the desktop app,
restart `coreaudiod`, disconnect/reconnect devices, and confirm public devices
become unavailable or stale within 5 seconds and recover only after app
heartbeat and route checks pass again.

**Acceptance Scenarios**:

1. **Given** live passthrough is active, **When** the app heartbeat disappears,
   **Then** public 2brain Rec devices become hidden or unavailable within 5
   seconds.
2. **Given** `coreaudiod` restarts or the HAL plug-in reloads, **When** the app
   is still available, **Then** the route is marked stale until live passthrough
   is revalidated.
3. **Given** a physical input/output changes while a browser target is using the
   virtual devices, **When** the change is detected, **Then** live route status
   becomes stale or degraded and the app shows a recovery action.

### Edge Cases

- The user selects a 2brain Rec virtual device as a physical working device.
- The physical microphone produces silence while the user is naturally quiet.
- The physical microphone has permission denied or is claimed exclusively by
  another app.
- The physical output is a multi-output or aggregate device.
- The physical output changes from built-in/wired to Bluetooth call profile.
- The browser keeps stale device IDs after driver reload.
- The app quits or crashes while a browser meeting still has the virtual devices
  selected.
- `coreaudiod` restarts while live passthrough is active.
- Backend, upload, transcription, or network services are unavailable.
- Remote audio is loud enough to challenge leakage and echo rejection.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST route selected physical microphone audio into
  `2brain Rec Microphone` when the app heartbeat is alive and the microphone
  path has passed readiness.
- **FR-002**: The system MUST route audio sent to `2brain Rec Speaker` into the
  selected physical output when the app heartbeat is alive and the speaker path
  has passed readiness.
- **FR-003**: The system MUST keep live passthrough disabled until both
  microphone and speaker path evidence pass.
- **FR-004**: The system MUST reject self-routing where a 2brain Rec virtual
  device is selected as a physical microphone or physical output.
- **FR-005**: The system MUST keep recording, upload, transcription,
  MediaScribe, Langfuse, and server workflows out of this feature.
- **FR-006**: The system MUST NOT start hidden recording, hidden capture, or
  transcript generation during passthrough readiness or live passthrough.
- **FR-007**: The app MUST show visible non-recording live route state whenever
  passthrough is active, distinct from recording and transcript-only states.
- **FR-008**: The driver MUST preserve private app I/O fail-closed behavior:
  stale or missing app heartbeat makes public virtual devices hidden or
  unavailable within 5 seconds.
- **FR-009**: The route MUST become stale within 5 seconds after physical
  device, output route, browser target device, app heartbeat, or `coreaudiod`
  change.
- **FR-010**: Built-in and wired routes MUST add no more than 30 ms of
  2brain Rec route latency when marked ready.
- **FR-011**: Remote speaker audio leakage into `2brain Rec Microphone` MUST
  remain at least 45 dB below speaker reference and not intelligible when marked
  ready.
- **FR-012**: Browser-call validation MUST record pass or blocked/not accepted
  evidence for Chrome, Opera, Yandex Browser, and Yandex Telemost-in-browser.
- **FR-013**: Backend, upload, transcription, and network failures MUST NOT
  interrupt live passthrough after readiness passes.
- **FR-014**: Diagnostics MUST include route state, selected device identifiers,
  failure category, recovery action, latency/leakage measurements, browser
  target status, and app heartbeat status without raw audio, transcript text,
  credentials, tokens, signed URLs, or meeting content.
- **FR-015**: Any temporary stimulus or debug audio used for development MUST be
  explicit, local, release-disabled by default, and excluded from diagnostics by
  default.
- **FR-016**: Bluetooth and AirPods-class routes MUST remain managed pilot routes
  unless separate evidence proves bidirectional profile stability, latency,
  leakage, and dropout behavior for the selected device.
- **FR-017**: The UI MUST provide a user-triggered recheck action whenever live
  passthrough is stale, degraded, failed, or blocked.
- **FR-018**: The feature MUST NOT add no-driver fallback, invisible recording,
  silent capture, direct desktop-to-MediaScribe upload, copied Krisp UI/copy, or
  new external network egress.

### Key Entities

- **Live Passthrough Session**: A non-recording live audio route between
  physical microphone/output and the two 2brain Rec virtual devices.
- **Microphone Passthrough Path**: The current physical microphone source,
  validity state, frame activity, route errors, and recovery action.
- **Speaker Passthrough Path**: The current virtual speaker input, selected
  physical output, playback state, route errors, and recovery action.
- **Passthrough Health Evidence**: Metadata-only latency, leakage, frame
  continuity, app heartbeat, stale state, and route transition evidence.
- **Browser Call Evidence**: Per-target metadata showing selected virtual
  devices, local speech usability, remote audio usability, pass/blocked status,
  and concrete failure reason.
- **Route Recovery Event**: A device, browser, app heartbeat, driver, or
  `coreaudiod` change that invalidates or restores live passthrough.

### Constitutional Requirements *(mandatory for 2brain Rec)*

- **Capture/Driver Impact**: This feature directly implements macOS live
  passthrough. It must remain driver-first, preserve the HAL virtual devices,
  preserve private app I/O fail-closed behavior, prevent loopback, and define
  measurable latency, leakage, stale-state, and recovery gates.
- **Visible Control Impact**: Passthrough readiness and active live route state
  must be visible and user-triggered. The feature must not start recording or
  transcription. If any capture surface is touched, one-action stop and visible
  active capture indicators must remain intact.
- **Data Boundary Impact**: This feature is local audio routing only. It must
  not add MediaScribe upload, Langfuse traces, LLM calls, analytics, server
  upload, storage, or external network egress.
- **Secrets Impact**: No credentials, tokens, signed URLs, passwords, or live
  credential paths may be stored in client state, diagnostics, logs, or evidence
  artifacts.
- **Retention/Deletion Impact**: Passthrough evidence and diagnostics are local
  metadata. Temporary development audio stimulus must be explicit, local,
  release-disabled by default, cleanable, and absent from default diagnostics.
- **Audit Impact**: Readiness check, passthrough start/stop, pass/fail,
  stale/degraded transitions, browser validation, private app I/O loss/recovery,
  and diagnostic export must be auditable without raw audio or transcript
  payloads.
- **UX/Brand/Accessibility Impact**: UI must use original 2brain Rec language,
  accessible non-color-only states, localization-safe copy, keyboard reachable
  controls, and brand-distance from Krisp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a fresh local install, selecting a physical microphone and
  `2brain Rec Microphone` in a controlled receiver delivers live local speech
  without starting recording.
- **SC-002**: In a fresh local install, audio sent to `2brain Rec Speaker`
  plays through the selected physical output without starting recording.
- **SC-003**: Built-in and wired ready routes add no more than 30 ms of
  2brain Rec route latency.
- **SC-004**: Remote speaker leakage into `2brain Rec Microphone` remains at
  least 45 dB below speaker reference and not intelligible on ready built-in and
  wired routes.
- **SC-005**: Killing the desktop app or route engine makes public virtual
  devices hidden or unavailable within 5 seconds, and relaunch restores them
  only after heartbeat and route revalidation.
- **SC-006**: `coreaudiod` restart marks live passthrough stale and recovers to
  ready only after revalidation.
- **SC-007**: Chrome, Opera, Yandex Browser, and Yandex Telemost-in-browser each
  have pass or blocked/not accepted metadata-only evidence for live
  bidirectional passthrough.
- **SC-008**: A 5-minute backend/network outage does not interrupt live
  passthrough after readiness passes.
- **SC-009**: Diagnostics for passthrough failures contain actionable status and
  no raw audio, transcript text, credentials, tokens, signed URLs, or meeting
  content.

## Assumptions

- Feature `003-live-route-readiness` is accepted and provides publication proof,
  private app I/O heartbeat, fail-closed behavior, live route readiness models,
  latency/leakage gates, diagnostics scaffolding, and browser evidence formats.
- The first release-quality route target is built-in or wired physical
  microphone/output on Apple Silicon macOS.
- Bluetooth and AirPods-class routes remain managed pilot routes unless selected
  explicitly for evidence collection.
- Browser validation can record a target as blocked/not accepted when the
  target cannot be safely validated in the current local environment.
- Recording, local buffering, upload, transcription, storage, MediaScribe,
  Langfuse, deletion, server workflows, and assisted auto-start of capture
  remain out of scope for this feature.
- The desktop app may automatically prepare the local non-recording passthrough
  route when opened so selected browser/meeting apps can use the virtual
  microphone and speaker without pressing `Run Check`. This startup behavior
  must not start recording, transcription, upload, or hidden capture; `Run Check`
  remains an explicit recheck/repair action.
