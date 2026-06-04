# Feature Specification: Live Route Stability

**Feature Branch**: `019-live-route-stability`

**Created**: 2026-06-04

**Status**: Draft - ready for planning

**Input**: User description: "After a real meeting test, 2brain Rec audio periodically disappeared during the meeting. The user had to press Run Check repeatedly to hear remote participants again and to make the microphone work again. Create a detailed standalone Spec Kit feature for live route stability, separate from speaker-to-mic leakage, backend ingest, upload, and future product slices."

## Clarifications

### Session 2026-06-04

- Q: What long-duration validation window is required for acceptance? -> A: Use a two-level gate: 30-minute automated/development validation plus 75-minute manual/release validation that matches the real 2026-06-04 meeting length.
- Q: Should the feature focus on detecting broken audio quickly or preventing live audio from breaking in the first place? -> A: The primary goal is prevention: an active meeting route must not self-release, drop, or require recurring `Run Check`. Detection/degraded state is only a safety net for exceptional external failures, not the success path.
- Q: Should external route disruptions require a user action such as `Run Check`, or should the system repair automatically? -> A: The product requirement is automatic repair. User action must not be the normal recovery path. `Run Check` remains a manual diagnostic/development fallback, while supported external disruptions must be repaired automatically when possible and recorded as metadata-only evidence.
- Q: Which meeting targets are in the acceptance matrix for this feature? -> A: Chrome, Opera, Zoom, and Telemost are in scope for acceptance. Yandex Browser is not part of the `019` acceptance gate and remains a separate/not-accepted browser target until a later validation slice includes it.
- Q: What timeline difference between `mic.wav` and `incoming.wav` is acceptable? -> A: Up to 3 seconds is acceptable technical tolerance. More than 3 seconds and up to 10 seconds is degraded/warning and requires explicit evidence. More than 10 seconds is a feature failure. Differences measured in tens of seconds or minutes are route-stability bugs.
- Q: Which physical device classes are in scope for autorepair acceptance? -> A: Built-in, wired, and USB audio devices are in scope for `019` acceptance. Bluetooth and AirPods-class routes are explicitly deferred to product backlog and must be implemented in a later dedicated slice.
- Q: How should the user-facing UI behave after successful autorepair? -> A: Use Option B: do not interrupt the user during a successful autorepair, but write detailed metadata-only problem logs so QA/debug can reconstruct and reproduce the issue.
- Q: What recovery-time target should successful autorepair meet? -> A: Use a two-tier target: normal recoverable disruptions must recover within 2 seconds; OS/device-heavy recoverable disruptions must recover within 10 seconds after required OS/device conditions are available again. Slower recovery is degraded/failed evidence, not clean acceptance.
- Q: How is the physical mic/output selected for `019` if the user only selects 2brain Rec virtual devices in the meeting app? -> A: The meeting app selects `2brain Rec Microphone` and `2brain Rec Speaker`; 2brain Rec follows the current macOS system default physical input/output route. If macOS or the user changes the system default input/output to another built-in, wired, or USB route during a meeting, 2brain Rec must detect and follow that default-route change automatically without `Run Check`. Bluetooth/AirPods default routes remain deferred/not accepted for `019`.
- Q: Does `019` require the full meeting-target by physical-device-class cross-product for acceptance? -> A: Use Option B: every accepted meeting target must pass long-duration evidence, and every in-scope device class must pass long-duration evidence, but the full `4 targets × 3 device classes` cross-product is not required for `019` acceptance.

## Incident Context

This feature is a release-blocking stability slice for the macOS live audio route. It exists because a real meeting on 2026-06-04 showed that the already accepted short smoke behavior is not enough: during a long live meeting, routed audio periodically stopped, and manual `Run Check` was required to restore both remote audio playback and local microphone passthrough.

The saved local recording package is:

`/Users/yshishenya/Library/Application Support/2brain Rec/Recordings/20260604-091621-C705ED72-E352-4522-93F2-1219953177EE`

Observed metadata from that package:

- Session started at `2026-06-04T09:16:21Z` and stopped at `2026-06-04T10:29:34Z`.
- Manifest status is `degraded`.
- Manifest failure reason is `timeline_misaligned`.
- `mic.wav` is saved, mono PCM 16 kHz, approximately `4393.07` seconds.
- `incoming.wav` is saved, mono PCM 16 kHz, approximately `4240.88` seconds.
- Incoming/remote track is approximately `152.19` seconds shorter than the local mic track.
- `incoming.wav` is marked `timelineAligned: false` with `failureReason: timeline_misaligned`.
- `externalEgressStarted` is `false`; no upload, MediaScribe, transcription, or external processing started.

Observed route-engine evidence from local bridge logs:

- The live bridge repeatedly started successfully with the physical devices:
  - `Микрофон MacBook Pro`
  - `Динамики MacBook Pro`
- The live bridge repeatedly stopped after approximately `300` seconds.
- After each stop, the bridge was started again only after an explicit repair/recheck action.

The current working hypothesis is that a long-running meeting route can be misclassified as idle or otherwise released while the meeting is still active. The feature must prove or falsify that hypothesis during planning and implementation. The specification must not lock onto a single implementation fix until the plan has confirmed root cause with evidence.

## Relationship To Existing Specs

This feature supersedes only the long-duration stability gap left by earlier macOS audio slices. It does not replace their accepted foundations.

- `004-real-bidirectional-passthrough` established the real mic/speaker passthrough goal and live route readiness model.
- `005-macos-passthrough-release-hardening` established pre-recording stability gates, no-hang checks, CPU gates, stale/degraded/blocked states, and non-recording route UX.
- `006-low-resource-audio` made lightweight virtual routing the default and required automatic activation without normal `Run Check`.
- `007-capture-session-indicator` and `008-local-recording-persistence` established visible manual recording and local dual-track artifacts.
- `010-recording-artifact-format` established dual-track recording package truth and degraded timeline-alignment metadata.

This feature is narrower than those foundations: it is about keeping an already-valid live meeting route stable for the full duration of a real meeting and proving that the product does not regress into "works only after Run Check".

## Acceptance Target Matrix

The required acceptance targets for this feature are:

- Chrome
- Opera
- Zoom
- Telemost

Each target must be validated with:

- `2brain Rec Microphone` selected as the meeting input;
- `2brain Rec Speaker` selected as the meeting output;
- no recurring `Run Check`;
- no manual meeting-target device reselect;
- no app relaunch;
- no meeting settings reopen;
- live remote audio remains audible;
- local microphone passthrough remains usable;
- autorepair works for supported external disruptions where the target still
  uses the 2brain Rec virtual route;
- local recording artifact continuity is validated when recording is active;
- metadata-only evidence records accepted, blocked, and not-tested outcomes.

Yandex Browser is explicitly out of the `019` acceptance matrix. It may be
recorded as not tested/not accepted in release notes and handled by a later
browser-target validation slice.

## Device-Class Matrix

The required physical device classes for `019` acceptance are:

- built-in microphone/output;
- wired microphone/output or wired headset;
- USB audio microphone/output or USB headset/interface.

For each accepted meeting target, validation evidence must identify which
physical device class was used and whether the run was accepted, blocked, or
not tested.

Physical device choice follows the macOS system route. The user selects
`2brain Rec Microphone` and `2brain Rec Speaker` inside the meeting target; the
physical microphone/output that 2brain Rec uses is the current macOS system
default input/output route. `019` does not introduce a separate 2brain Rec
physical-device picker.

If the user changes macOS system sound settings during an active meeting, or
macOS changes the default route after device plug/unplug, 2brain Rec must detect
the default input/output change and follow the new route automatically when it
resolves to an accepted built-in, wired, or USB device class. This is treated as
a recoverable default-route change, not as a user action inside 2brain Rec.

The `019` planning step must define the exact validation matrix without hiding
coverage gaps. The minimum release gate is:

- each accepted meeting target has long-duration accepted evidence;
- each in-scope physical device class has long-duration accepted evidence;
- the full meeting-target by physical-device-class cross-product is not required
  for `019` acceptance;
- any target/device-class combination not run is explicitly marked not tested
  and cannot be claimed as release-ready for that combination.

Bluetooth and AirPods-class routes are not part of `019` acceptance. They are
not optional forever: they are product backlog because real users will expect
wireless headsets to work. They need a later dedicated slice because profile
switching, bidirectional headset mode, latency, reconnection, and route churn
create a different risk class than built-in/wired/USB devices.

Backlog item:

- **Bluetooth/AirPods Live Route Stability**: implement and validate
  long-duration route stability and autorepair for Bluetooth and AirPods-class
  devices after `019`, including profile switching, reconnect behavior,
  latency, route preservation, recording timeline integrity, and metadata-only
  evidence.

## Scope Boundary

In scope:

- Long-running live passthrough stability when a meeting app uses `2brain Rec Microphone` and `2brain Rec Speaker`.
- Remote-audio playback continuity through the current macOS default physical output.
- Local microphone passthrough continuity into the virtual microphone.
- Automatic repair of supported external disruptions without user action.
- Route state truth when passthrough is active, idle, stale, blocked, failed, repaired, or recovering.
- Manual `Run Check` behavior as a repair action only, not a normal recurring requirement during an active meeting.
- Metadata-only evidence for route starts, stops, idle/release decisions, stale transitions, recovery attempts, and recording-track continuity.
- Local recording artifact truth when route interruptions shorten or misalign the incoming track.
- Long-duration validation gates beyond short smoke tests.
- Built-in, wired, and USB physical device-class validation.

Out of scope:

- Speaker-to-mic acoustic leakage and echo policy; that belongs to `020-speaker-mic-leakage`.
- Meeting-app mute truth; that remains `009-respect-meeting-mute`.
- Assisted auto-recording and meeting detection; that remains `011-assisted-auto-recording`.
- Bluetooth and AirPods-class route stability and autorepair acceptance; these belong to a dedicated future Bluetooth/AirPods live-route slice.
- Federated auth, desktop upload queue, server ingest, MediaScribe processing, dashboard, sharing, retention, and deletion slices.
- Any direct desktop-to-MediaScribe call, MediaScribe credential handling, Langfuse content tracing, upload token handling, or external egress.
- Rebranding, landing pages, dashboard UI, and non-audio product surfaces.

## Autorepair Product Rule

Autorepair is a product requirement for this feature. During an active meeting,
2brain Rec must behave like a reliable audio device: the user should not need
to understand route state, reopen settings, or press `Run Check` to keep audio
working.

The system must separate three cases:

1. **Healthy active meeting route**: The route is working and the meeting target
   still uses the 2brain Rec virtual devices. The system must preserve the
   route. Autorepair should not churn, restart, or rebuild the route just
   because timers fire or audio is temporarily silent.
2. **Recoverable external disruption**: Something outside normal route
   operation changes, but the meeting can still continue. The system must
   restore the route automatically without user action.
3. **Non-recoverable external disruption**: A required external condition is no
   longer available, such as permission revoked, no physical microphone/output
   available, or the meeting client no longer using the virtual devices. The
   system must not pretend the route is healthy. It must record truthful
   blocked evidence. This is not a successful user scenario.

Supported recoverable external disruptions include:

- `coreaudiod` restart or HAL plug-in reload while the meeting target still has
  2brain Rec devices selected.
- Sleep/wake where macOS default input/output resolves again to accepted
  built-in, wired, or USB devices and permissions remain valid.
- Temporary macOS default physical input/output disappearance followed by return
  of an accepted built-in, wired, or USB default route.
- Physical input/output route refresh where macOS resolves the system default
  input/output route to an accepted built-in, wired, or USB device class.
- User-initiated macOS system default input/output change to another accepted
  built-in, wired, or USB device while the meeting target still uses 2brain Rec
  virtual devices.
- Browser or meeting app recreating the audio stream while retaining the 2brain
  Rec virtual route.
- Stale browser device identifiers that can be refreshed without user
  reconfiguration.
- App-side route engine restart where the driver and meeting target are still
  available.

Autorepair timing has two accepted tiers:

- **Normal recoverable disruptions**: route recovery must complete within `<= 2
  seconds`.
- **OS/device-heavy recoverable disruptions**: route recovery must complete
  within `<= 10 seconds` after the required OS/device condition becomes
  available again.

Recovery slower than `10 seconds` must be recorded as degraded or failed
evidence and cannot count as clean acceptance. Non-recoverable states must be
blocked truthfully instead of being measured as slow recovery.

Non-recoverable conditions include:

- microphone permission revoked or unavailable;
- no accepted physical microphone is available;
- no accepted physical output is available;
- the meeting target is no longer using the 2brain Rec virtual devices;
- the user intentionally changed meeting audio devices away from 2brain Rec;
- macOS system default input/output resolves to a device class outside `019`
  acceptance, such as Bluetooth or AirPods-class route;
- the route would require 2brain Rec to choose a physical microphone or output
  independently of macOS system default behavior;
- the OS, browser, or meeting target refuses to reopen the required stream.

Non-recoverable conditions must be logged as blocked evidence. They are not
accepted successful user scenarios, but they must not trigger infinite repair
loops or false healthy state.

Autorepair must not be used to hide self-inflicted drops. If 2brain Rec released
or stopped a healthy active route because of idle policy, timer behavior,
misread silence, stale cached state, or app housekeeping, that is a stability
bug, not an acceptable repair case.

Successful autorepair must not interrupt the meeting user with a required
action or distracting modal. The ordinary user-facing behavior is quiet recovery
plus truthful passive status/history evidence. Detailed repair evidence must be
written to metadata-only diagnostics so QA and engineering can reconstruct what
happened and reproduce the route problem without raw audio or meeting content.

Autorepair must not:

- start recording, transcription, upload, MediaScribe processing, Langfuse
  tracing, analytics, or external egress;
- require the user to press `Run Check` during normal recovery;
- override macOS system default input/output with a different physical
  microphone or output selected by 2brain Rec;
- mark a route ready without fresh evidence after recovery;
- loop forever trying to repair a non-recoverable state;
- mask artifact degradation or timeline loss.

`Run Check` remains available as a manual diagnostic/development fallback, but
it is not the product recovery path for this feature. Any accepted validation
run that needs `Run Check` to restore ordinary meeting audio fails this feature.

## Timeline Integrity Rule

This feature must preserve the relationship between the local microphone track
and the incoming/remote speaker track during local recording.

Small differences can happen because recording paths do not start and stop at
exactly the same instant, because buffers are flushed at slightly different
times, or because audio is resampled and written in chunks. These small
differences are acceptable only within the defined tolerance.

Timeline alignment thresholds:

- **Accepted**: `mic.wav` and `incoming.wav` differ by `<= 3 seconds`.
- **Degraded / warning**: the tracks differ by `> 3 seconds` and `<= 10
  seconds`; the manifest and diagnostics must explain the likely reason.
- **Failed for this feature**: the tracks differ by `> 10 seconds`.
- **Clear route-stability bug**: the tracks differ by tens of seconds or
  minutes, such as the 2026-06-04 incident where incoming audio was shorter by
  approximately `152` seconds.

If the route remains healthy for the full accepted validation window, the
recording package must finish in the accepted alignment band. If it does not,
the feature is not accepted even if live audio seemed usable during the call.

## Logging And Evidence Contract

This feature requires structured, metadata-only logging. The purpose is to make
future live-route failures diagnosable without raw audio, meeting text,
transcripts, credentials, tokens, signed URLs, passwords, or meeting content.

Logging must answer these questions:

- Did the route start, and why?
- Which meeting target was active?
- Which virtual devices were in use?
- Which physical microphone and output were selected?
- Did 2brain Rec preserve the route, release it, stop it, repair it, or block
  it?
- If the route changed, what triggered the change?
- Was the trigger self-inflicted or external?
- Did autorepair run?
- Did autorepair require any user action?
- Did autorepair follow the current macOS system default input/output route?
- Did local recording remain timeline-aligned?

Required event families:

- **Route lifecycle**: route armed, started, active, preserved, stopped,
  released, stale, blocked, failed, recovered.
- **Client activity**: virtual microphone client opened/closed, virtual speaker
  client opened/closed, both-route active, single-side active, browser stream
  recreated.
- **Idle/release decisions**: keep-active decision, release decision, release
  denied because meeting client is still active, unknown state preserved.
- **Autorepair**: repair started, repair attempt, repair succeeded, repair
  blocked, repair failed, retry budget exhausted.
- **External disruption**: `coreaudiod` restart, HAL reload, sleep/wake,
  physical device disappeared, physical device returned, physical route
  changed, macOS default input/output changed, browser stale device ID,
  permission revoked.
- **Recording timeline**: recording started, route gap during recording,
  recording stopped, track durations, timeline alignment band, manifest
  readiness.
- **User action audit**: `Run Check` pressed, meeting-target device manually
  reselected, app relaunched, meeting settings reopened. Accepted validation
  runs must show none of these actions were required.

Successful autorepair evidence must be detailed enough for debug
reproduction. It must record the trigger category, route state before/after,
meeting target label, virtual-client state, resolved physical-device identity,
resolved device class, macOS default-route value before/after, frame-continuity summary,
timing window, attempt count, elapsed
repair time, default-route-following decision, final route outcome, and
recording alignment status when recording is active. It must remain
metadata-only and must not include raw audio, transcript text, meeting content,
credentials, tokens, signed URLs, passwords, or live credential paths.

Each event must include, when available:

- event name;
- timestamp;
- session id or route session id;
- meeting target label from the accepted matrix;
- route state before and after the event;
- trigger category;
- resolved macOS default physical input/output identifiers and safe display names;
- macOS default input/output route before and after recovery;
- virtual client state for microphone and speaker;
- whether recording was active;
- whether autorepair was running;
- autorepair attempt number and outcome;
- whether user action was required;
- metadata-only frame continuity summary;
- metadata-only track duration/alignment summary when recording is active.

Logging must be local-first. Any future export must pass the existing
diagnostic redaction rules before leaving the machine.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Keep A Live Meeting Audible And Speakable (Priority: P1)

As a macOS meeting user, I want the selected 2brain Rec virtual microphone and speaker to keep working for the entire meeting, so that I do not lose remote participants or my own microphone during a call.

**Why this priority**: If live audio disappears during a meeting, the product fails at its primary driver-first routing promise. Recording and transcription quality also become untrustworthy because source tracks can lose time.

**Independent Test**: Join a controlled long-running meeting with `2brain Rec Microphone` and `2brain Rec Speaker` selected, keep the call active for 30 minutes in automated/development validation and 75 minutes in manual/release validation, and verify that the user can hear remote audio and the remote side can hear local speech without pressing `Run Check`.

**Acceptance Scenarios**:

1. **Given** a supported meeting target is using both 2brain Rec virtual devices and live route readiness has passed, **When** the meeting remains active for the accepted long-duration window, **Then** remote audio remains audible and local microphone passthrough remains usable without recurring manual recheck.
2. **Given** the user is naturally silent for part of the meeting, **When** the route evaluates activity, **Then** the active meeting route remains active and is not released solely because local microphone audio energy is low.
3. **Given** the remote participants are silent for part of the meeting, **When** the route evaluates activity, **Then** the active meeting route remains active and is not released solely because remote speaker audio energy is low.
4. **Given** one side of the meeting is temporarily quiet, **When** audio resumes, **Then** audio resumes through the existing live route without requiring `Run Check`.

---

### User Story 2 - Repair External Disruptions Automatically (Priority: P1)

As a user, I want 2brain Rec to repair supported external audio disruptions by itself, so that I do not need to understand audio routing or press `Run Check` during a meeting.

**Why this priority**: The observed incident required repeated `Run Check` actions. That is a product-level failure. The product should behave like a stable audio device with automatic recovery, not like a fragile manual bridge.

**Independent Test**: During a controlled long meeting, do not press `Run Check`; verify the route remains stable. Then trigger supported external disruptions such as `coreaudiod` restart, sleep/wake, physical device reconnection, and browser stream recreation; verify 2brain Rec restores the route automatically when the meeting target still uses the virtual devices.

**Acceptance Scenarios**:

1. **Given** a meeting route is active and healthy, **When** the long-duration validation runs, **Then** no periodic `Run Check` is required to keep audio flowing.
2. **Given** a supported external audio disruption occurs and the meeting target still uses 2brain Rec virtual devices, **When** recovery is safe, **Then** 2brain Rec restores mic and speaker passthrough automatically without requiring user action.
3. **Given** automatic recovery cannot complete because the physical device, permission, or meeting client is no longer available, **When** the route cannot be restored, **Then** 2brain Rec records the blocked reason truthfully without pretending the route is healthy.
4. **Given** the user presses `Run Check`, **When** the route is already healthy or auto-repair is in progress, **Then** `Run Check` behaves as a diagnostic/recheck fallback and not as the primary recovery mechanism.
5. **Given** autorepair succeeds after a recoverable disruption, **When** the meeting continues, **Then** both remote audio and local microphone passthrough continue without requiring the user to reselect meeting-target devices.
6. **Given** autorepair is attempted repeatedly for the same non-recoverable condition, **When** the retry budget is exhausted, **Then** the system stops repair churn, records blocked evidence, and does not misreport the route as healthy.

---

### User Story 3 - Preserve Incoming Track Timeline During Recording (Priority: P1)

As a user who records a meeting, I want the remote/incoming track to stay aligned with the local microphone track for the full recording, so that transcription and review do not lose or shift remote participant speech.

**Why this priority**: The 2026-06-04 artifact shows a degraded recording package where `incoming.wav` is shorter than `mic.wav` by about `152` seconds. Even if the user notices live audio loss, the saved artifact must truthfully detect and help diagnose that loss.

**Independent Test**: Record a controlled long-running meeting through the 2brain Rec route and verify that `mic.wav`, `incoming.wav`, and `manifest.json` remain timeline-aligned within the accepted tolerance, or that any interruption is marked with precise evidence.

**Acceptance Scenarios**:

1. **Given** local recording is active during a stable long meeting, **When** the recording stops, **Then** local mic and incoming tracks are saved and timeline-aligned within the accepted tolerance.
2. **Given** the incoming route stops receiving valid frames during a recording, **When** the recording stops, **Then** the manifest reports degraded truth and identifies the route interruption category rather than only a generic timeline mismatch.
3. **Given** the route recovers after a short interruption, **When** the final artifact is produced, **Then** the manifest preserves enough metadata to distinguish a recovered route gap from a continuous recording.

---

### User Story 4 - Prevent Self-Inflicted Route Drops (Priority: P1)

As a user in a meeting, I want 2brain Rec to avoid releasing, stopping, or rebuilding a healthy active route, so that audio does not disappear because of its own idle/recovery policy.

**Why this priority**: The observed incident looks like the route was stopped while the meeting was still active. The product should behave like a stable audio device, not like a route that periodically needs manual repair.

**Independent Test**: Run long-duration meetings and controlled client-activity scenarios. Verify that no healthy active meeting route is released by idle policy, stale cached state, periodic timers, app-side housekeeping, or false silence classification.

**Acceptance Scenarios**:

1. **Given** a supported meeting target still has an active virtual-device client, **When** idle/release policy evaluates the route, **Then** the route is kept active and audio continues.
2. **Given** the meeting is active but one side is silent, **When** timers or health checks run, **Then** silence does not cause route release, restart, or manual repair requirement.
3. **Given** a real external event such as `coreaudiod` restart or physical-device removal occurs, **When** audio cannot be preserved, **Then** the system fails truthfully and exposes repair state, but this is treated as an exceptional failure path rather than the normal success path.

---

### User Story 5 - Produce Metadata-Only Evidence For Root Cause (Priority: P2)

As an engineer or QA owner, I want metadata-only evidence that explains route starts, stops, release decisions, frame continuity, and recovery, so that future long-call failures can be diagnosed without raw meeting content.

**Why this priority**: The current incident required correlating a degraded manifest and bridge logs. Future debugging should not depend on manual log archaeology.

**Independent Test**: Run long-duration and induced-failure validation, then inspect metadata-only evidence showing route lifecycle, health windows, frame counters, recovery attempts, and final artifact alignment without raw audio, transcript text, meeting content, credentials, tokens, or signed URLs.

**Acceptance Scenarios**:

1. **Given** a live route starts, **When** diagnostics are exported, **Then** evidence records route start reason, macOS default physical input/output, virtual client state, readiness source, and timestamp.
2. **Given** the route is released, stopped, marked stale, or repaired, **When** diagnostics are exported, **Then** evidence records the decision reason, health counters, affected path, and whether user action was required.
3. **Given** a recording artifact is degraded, **When** diagnostics are exported, **Then** evidence links the artifact degradation category to route lifecycle facts without including meeting audio or content.
4. **Given** autorepair runs, **When** diagnostics are exported, **Then** evidence records trigger category, recovery attempt count, outcome, elapsed recovery time, macOS default-route before/after values, and whether the meeting target remained on the virtual route.

### Edge Cases

- The meeting is long-running and includes multiple naturally silent intervals.
- Only the virtual microphone is active for a while.
- Only the virtual speaker is active for a while.
- A browser or meeting app briefly closes and reopens Core Audio client I/O during device settings, prejoin, sleep/wake, tab refresh, or network reconnection.
- `coreaudiod` restarts during an active meeting.
- The desktop app is restarted while the meeting app still has the virtual devices selected.
- The Mac sleeps and wakes during or shortly before a meeting.
- The physical microphone or output device changes while the meeting route is active.
- The macOS default physical input/output disappears briefly and returns.
- macOS system default input/output changes to another accepted built-in,
  wired, or USB route during an active meeting.
- macOS system default input/output changes to Bluetooth or AirPods-class
  during an active meeting; this is deferred/not accepted for `019`.
- Bluetooth profile changes occur while virtual devices remain selected; this
  is deferred from `019` acceptance and must be handled by the future
  Bluetooth/AirPods route-stability slice.
- Bluetooth or AirPods-class devices are used; this must be recorded as
  backlog/not accepted for `019`, not as accepted release evidence.
- The route is healthy but local or remote participants are silent.
- The meeting app keeps stale device IDs after driver/app/Core Audio restart.
- The browser or meeting app recreates its audio stream without the user leaving the meeting.
- Autorepair succeeds while recording is active.
- Autorepair cannot complete because microphone permission was revoked.
- Autorepair cannot complete because the meeting target is no longer using the
  2brain Rec virtual devices.
- Autorepair cannot complete because following macOS system default would
  resolve to a device class outside `019` acceptance.
- The route is active without recording.
- Recording is active and one track loses continuity.
- Backend, upload, MediaScribe, Langfuse, and network services are unavailable.
- Validation evidence contains policy/fixture strings that look like forbidden fields but are not secrets.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST keep a live meeting route active for the accepted long-duration window when a supported meeting target is using both `2brain Rec Microphone` and `2brain Rec Speaker`.
- **FR-002**: The system MUST NOT require recurring user-triggered `Run Check` actions to maintain or recover an otherwise recoverable active meeting route.
- **FR-003**: The system MUST treat `Run Check` as a manual diagnostic/development fallback, not as the normal keepalive or recovery mechanism for active meetings.
- **FR-004**: The system MUST distinguish active client use from audio energy so natural silence does not release or downgrade an active route.
- **FR-005**: The system MUST distinguish a genuinely closed virtual-device client from a temporarily quiet or silent active meeting.
- **FR-006**: The system MUST prevent its own idle policy, route lifecycle timers, app housekeeping, and false silence classification from stopping a healthy active microphone path.
- **FR-007**: The system MUST prevent its own idle policy, route lifecycle timers, app housekeeping, and false silence classification from stopping a healthy active incoming/speaker path.
- **FR-008**: The system MUST preserve truthful route state across app restart, `coreaudiod` restart, sleep/wake, physical-device changes, browser stale device selections, and transient meeting-client I/O changes.
- **FR-009**: The system MUST NOT present a live route as ready when freshness, frame-continuity, app-health, or selected-device evidence is stale.
- **FR-010**: The system MUST preserve a healthy active meeting route as the default behavior and MUST automatically repair supported external disruptions when the meeting target still uses the 2brain Rec virtual route.
- **FR-011**: The system MUST record metadata-only evidence for route start, active state, release/stop decision, stale transition, frame continuity loss, automatic recovery, user-triggered repair, and final outcome.
- **FR-012**: The system MUST capture enough metadata to explain whether a live route stop was caused by idle/release policy, app heartbeat loss, client I/O closure, Core Audio restart, physical-device change, browser stale selection, explicit user stop, or unknown failure.
- **FR-013**: The system MUST keep live passthrough independent from backend availability, upload status, MediaScribe, Langfuse, network state, and server processing.
- **FR-014**: The system MUST NOT start recording, transcription, upload, MediaScribe processing, Langfuse content tracing, analytics, or external egress as part of live route stability validation.
- **FR-015**: When local recording is active, the system MUST preserve mic and incoming track timeline alignment within the accepted tolerance during stable long meetings.
- **FR-016**: When local recording is active and route continuity is lost, the final manifest MUST report degraded truth with a route-interruption category precise enough for recovery and QA review.
- **FR-017**: The system MUST retain manual one-action stop and visible capture indicators for recording states; live route stability work MUST NOT dilute recording visibility or control.
- **FR-018**: User-facing status MUST distinguish routing-only live passthrough from active recording and from assisted recording.
- **FR-019**: Diagnostics, logs, validation evidence, and artifact manifests MUST NOT include raw audio, transcript text, meeting content, credentials, tokens, signed URLs, passwords, or live credential paths.
- **FR-020**: Long-duration validation MUST include both live audibility/speakability evidence and saved artifact continuity evidence across a 30-minute automated/development gate and a 75-minute manual/release gate.
- **FR-021**: Short smoke validation MUST NOT be sufficient to accept this feature; acceptance requires the dedicated 30-minute and 75-minute stability gates.
- **FR-022**: Any route release or idle policy that can stop an active meeting route MUST be guarded by evidence proving that the meeting client truly stopped using the virtual route.
- **FR-023**: If the system cannot prove that the meeting client truly closed the virtual route, it MUST preserve the active meeting route and MUST NOT release it to save resources.
- **FR-024**: The system MUST preserve automatic fallback or repair capability so a stability regression can be mitigated without reinstalling the HAL driver or requiring normal user action during a meeting.
- **FR-025**: The feature MUST provide release notes or QA evidence that explicitly state which meeting targets, duration windows, and device classes were accepted, blocked, or not tested.
- **FR-026**: Autorepair MUST preserve the macOS system default input/output route model and MUST refresh its resolved physical route when macOS default input/output changes.
- **FR-027**: Autorepair MUST follow macOS system default physical input/output routing and MUST NOT choose an independent physical microphone or output when the meeting target is using 2brain Rec virtual devices.
- **FR-028**: Autorepair MUST verify fresh route evidence before reporting the route healthy after recovery.
- **FR-029**: Autorepair MUST stop retry churn for non-recoverable states and record blocked evidence instead of looping indefinitely.
- **FR-030**: Autorepair MUST be safe while recording is active: it must not hide timeline gaps, corrupt track alignment, stop the visible recording indicator, or remove one-action stop.
- **FR-031**: Autorepair MUST be validated separately for at least `coreaudiod` restart, sleep/wake, temporary physical-device disappearance/return, browser stream recreation, and app-side route engine restart.
- **FR-032**: Any accepted repair path MUST require no normal user action: no `Run Check`, no meeting settings reopen, no manual meeting-target device reselect, and no app relaunch.
- **FR-033**: The system MUST classify recording timeline alignment as accepted when track duration difference is `<= 3 seconds`, degraded/warning when it is `> 3 seconds` and `<= 10 seconds`, and failed for this feature when it is `> 10 seconds`.
- **FR-034**: The system MUST treat any track duration difference measured in tens of seconds or minutes as a route-stability bug unless a separate accepted spec explicitly explains another cause.
- **FR-035**: The system MUST produce structured metadata-only logs for route lifecycle, client activity, idle/release decisions, autorepair, external disruptions, recording timeline integrity, and user action audit.
- **FR-036**: Logging MUST include enough correlation identifiers to connect a live route session, autorepair attempts, and the final local recording manifest without exposing meeting content.
- **FR-037**: Accepted validation evidence MUST prove that no normal user action was required by checking the user-action audit event family.
- **FR-038**: Autorepair MUST classify non-recoverable states separately from recoverable external disruptions and MUST NOT count non-recoverable blocked evidence as successful acceptance.
- **FR-039**: Autorepair MUST NOT perform independent privacy-relevant physical-device selection; physical route changes may be followed only when they come from macOS system default behavior and resolve to a device class accepted by `019`.
- **FR-040**: If the meeting target intentionally or externally stops using the 2brain Rec virtual devices, the system MUST NOT pretend the route is still active.
- **FR-041**: `019` acceptance MUST cover built-in, wired, and USB physical device classes for live route stability and autorepair evidence.
- **FR-042**: Bluetooth and AirPods-class devices MUST be recorded as product backlog/not accepted for `019`, not silently treated as release-ready.
- **FR-043**: The future Bluetooth/AirPods slice MUST include profile switching, reconnect behavior, latency, route preservation, recording timeline integrity, and autorepair evidence before wireless headset routes can be release-ready.
- **FR-044**: Successful autorepair MUST NOT interrupt the user with a required action or modal during an active meeting; it MUST leave truthful passive status/history evidence.
- **FR-045**: Successful autorepair MUST write detailed metadata-only debug evidence sufficient for QA/engineering to reconstruct and reproduce the route problem without raw audio or meeting content.
- **FR-046**: Normal recoverable disruptions MUST complete autorepair within `<= 2 seconds`.
- **FR-047**: OS/device-heavy recoverable disruptions MUST complete autorepair within `<= 10 seconds` after required OS/device conditions become available again.
- **FR-048**: Recovery slower than `10 seconds` MUST be recorded as degraded or failed evidence and MUST NOT count as clean acceptance.
- **FR-049**: If macOS system default input/output changes during an active meeting, 2brain Rec MAY follow that system default route only when the resolved physical device class is accepted for `019`; Bluetooth and AirPods-class resolutions MUST be logged as deferred/not accepted.
- **FR-050**: User-initiated macOS system default input/output changes to accepted built-in, wired, or USB routes MUST be detected and followed automatically without `Run Check` while the meeting target still uses the 2brain Rec virtual devices.
- **FR-051**: `019` acceptance MUST cover every accepted meeting target and every in-scope physical device class with long-duration evidence, but MUST NOT require the full `4 targets × 3 device classes` cross-product unless a later release-hardening gate explicitly adds that scope.

### Key Entities

- **Live Route Session**: A non-recording audio-routing session where meeting apps use 2brain Rec virtual devices for local microphone and remote speaker paths.
- **Route Health Window**: The bounded interval over which frame continuity, client activity, and app-health evidence are evaluated before state changes.
- **Client Activity Evidence**: Metadata proving whether a meeting target is actively using one or both virtual devices, independent of audio energy.
- **Frame Continuity Evidence**: Metadata counters and timing facts showing whether mic and incoming/speaker paths continue delivering valid frames.
- **Route Release Decision**: Metadata explaining why the route was released, stopped, kept active, marked stale, or repaired.
- **Recovery Attempt**: A metadata-only record of automatic or user-triggered effort to restore a route, including outcome and whether user action was required.
- **Autorepair Trigger**: A metadata-only category describing why automatic repair started, such as Core Audio restart, sleep/wake, device returned, browser stream recreated, stale device ID refresh, app route engine restarted, or unknown external disruption.
- **Autorepair Outcome**: A metadata-only result describing whether repair preserved the route, restored the route, blocked as non-recoverable, or failed without claiming healthy state.
- **Non-Recoverable Route Condition**: A condition where automatic repair cannot safely restore the meeting route because of missing permission, missing devices, missing meeting-client use of virtual devices, macOS default route resolving outside `019` acceptance, or a need for 2brain Rec to choose a physical device independently of macOS default behavior.
- **Recording Timeline Integrity Evidence**: Metadata connecting route continuity to `mic.wav`, `incoming.wav`, and manifest alignment without storing raw content in diagnostics.
- **Degraded Artifact Reason**: A precise saved-artifact category that distinguishes timeline mismatch caused by route interruption from other artifact failures.
- **Route Evidence Event**: A structured metadata-only log event describing route lifecycle, client activity, idle/release, autorepair, external disruption, timeline integrity, or user action audit.
- **Timeline Alignment Band**: The classification of track duration difference as accepted (`<= 3 seconds`), degraded/warning (`> 3` and `<= 10 seconds`), or failed (`> 10 seconds`).
- **Device-Class Acceptance Matrix**: The release evidence table that separates built-in, wired, USB, Bluetooth, AirPods-class, accepted, blocked, failed, and not-tested route outcomes.
- **macOS System Default Route**: The current macOS default physical input/output route that 2brain Rec follows while meeting apps use the 2brain Rec virtual microphone and speaker.
- **Deferred Bluetooth/AirPods Route Stability Slice**: The future product backlog item that must prove wireless headset route stability before Bluetooth or AirPods-class routes can be release-ready.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In accepted meeting targets, a long-running call completes the 30-minute automated/development gate and the 75-minute manual/release gate with no recurring `Run Check` required to preserve both remote audibility and local microphone passthrough.
- **SC-002**: During accepted long-duration validation, route evidence shows zero unexpected route releases while the meeting client remains active.
- **SC-003**: During accepted long-duration validation with local recording active, `mic.wav` and `incoming.wav` remain aligned within the accepted tolerance. Diagnostic or failed validation runs may record a precise route-interruption degradation reason, but degraded recording evidence cannot count as clean acceptance.
- **SC-004**: During accepted long-duration validation, 2brain Rec causes zero self-inflicted microphone-path drops, releases, restarts, or recurring manual repair requirements.
- **SC-005**: During accepted long-duration validation, 2brain Rec causes zero self-inflicted incoming/speaker-path drops, releases, restarts, or recurring manual repair requirements.
- **SC-006**: Natural silence in either local or remote audio does not cause active route release in 100% of silence-window validation cases.
- **SC-007**: `Run Check`, when used as a manual diagnostic/development fallback outside clean acceptance runs, repairs or truthfully fails induced stale/failed/blocked route states in 100% of manual repair validation cases.
- **SC-007a**: Supported external disruptions are automatically repaired without user action in 100% of accepted auto-repair validation cases where the physical devices, permissions, and meeting client remain available.
- **SC-007b**: Accepted autorepair validation requires zero user actions: no `Run Check`, no manual meeting-target device reselect, no app relaunch, and no meeting settings reopen.
- **SC-007c**: Autorepair reports healthy only after fresh route evidence in 100% of accepted recovery cases.
- **SC-007d**: Autorepair creates no recording, upload, transcription, MediaScribe, Langfuse, analytics, or external egress in 100% of accepted recovery cases.
- **SC-008**: App restart, `coreaudiod` restart, sleep/wake, physical-device change, and stale browser device-ID scenarios clear false-ready state within the applicable `<= 2 seconds` or `<= 10 seconds` autorepair target and recover only after fresh evidence.
- **SC-009**: Diagnostics for every accepted validation run include route start, route stop/release decision, frame-continuity summary, recovery outcome, and final artifact alignment status.
- **SC-010**: Diagnostics redaction validation finds no raw audio, transcript text, meeting content, credentials, tokens, signed URLs, passwords, or live credential paths outside deliberate policy/fixture strings.
- **SC-011**: Live route remains functional with backend, upload, MediaScribe, Langfuse, and network services unavailable in 100% of local offline validation cases.
- **SC-012**: Feature acceptance evidence explicitly lists accepted, blocked, and not-tested meeting targets, the 30-minute and 75-minute duration windows, physical device classes, and operating conditions.
- **SC-012a**: Chrome, Opera, Zoom, and Telemost each must have accepted evidence for the 30-minute development gate and the 75-minute release gate before this feature is considered accepted. Blocked, failed, or not-tested evidence is useful diagnostics but does not satisfy target acceptance.
- **SC-013**: Autorepair evidence explicitly lists trigger category, attempt count, elapsed recovery time, macOS default-route before/after values, route outcome, and final artifact alignment status for every accepted recovery run.
- **SC-014**: Stable long-duration recording acceptance requires `mic.wav` and `incoming.wav` duration difference `<= 3 seconds` in 100% of accepted target runs.
- **SC-015**: Any run with track duration difference `> 3 seconds` and `<= 10 seconds` is marked degraded/warning with explicit cause evidence and cannot be counted as clean acceptance.
- **SC-016**: Any run with track duration difference `> 10 seconds` fails this feature's timeline integrity gate.
- **SC-017**: Logging validation proves every accepted run includes route lifecycle, client activity, idle/release decision, autorepair, recording timeline, and user-action audit event families.
- **SC-018**: Non-recoverable route conditions are logged as blocked without infinite retry loops and without reporting healthy route state in 100% of blocked validation cases.
- **SC-019**: Built-in, wired, and USB device classes each have accepted long-duration evidence before `019` is considered accepted. Blocked, failed, or not-tested evidence is useful diagnostics but does not satisfy device-class acceptance.
- **SC-020**: Bluetooth and AirPods-class device routes are listed in the product backlog with a dedicated future-slice requirement and are not counted as accepted in `019`.
- **SC-021**: Release evidence distinguishes full target/device-class combinations that were accepted from combinations that were not tested, so `019` does not imply wireless or untested combination support.
- **SC-022**: In 100% of successful autorepair validation runs, the user is not required to act and no disruptive modal is shown, while passive status/history and detailed metadata-only debug evidence are recorded.
- **SC-023**: Normal recoverable disruption validation meets the `<= 2 seconds` recovery target in 100% of clean accepted cases.
- **SC-024**: OS/device-heavy recoverable disruption validation meets the `<= 10 seconds` recovery target, measured after required OS/device conditions are available again, in 100% of clean accepted cases.
- **SC-025**: In 100% of clean accepted macOS default-route change validation runs, 2brain Rec follows the new built-in, wired, or USB system default route automatically without meeting settings reopen, app relaunch, or `Run Check`.
- **SC-026**: Release evidence shows long-duration acceptance for Chrome, Opera, Zoom, and Telemost, plus separate long-duration acceptance for built-in, wired, and USB device classes; any untested target/device-class combinations are listed as not tested and are not claimed release-ready.

## Constitutional Requirements

- **Driver-First Capture Integrity**: This feature directly affects the macOS virtual audio route. It must preserve driver-first MVP behavior, separate local microphone and remote speaker paths, live passthrough, no-loopback gates, and truthful degraded state.
- **Visible Consent And User Control**: This feature must not start hidden recording or invisible capture. If recording is active, existing visible indicator and one-action stop requirements remain mandatory.
- **Data Boundary And Secret Discipline**: This feature is local audio-route stability only. It must not add external egress, MediaScribe calls, Langfuse content traces, upload tokens, or desktop-held server credentials.
- **Deletion Truth And Lifecycle Accounting**: This feature must not create new meeting-content artifacts beyond existing local recording packages. Any metadata evidence must remain deletion-accountable and content-free.
- **Spec-Driven Delivery With Testable Gates**: Because this feature touches audio routing, local buffering, recording artifacts, diagnostics, and privacy-sensitive failure states, `$speckit-clarify`, `$speckit-plan`, driver/security/UX checklists, `$speckit-tasks`, `$speckit-analyze`, and validation evidence are mandatory before implementation is considered accepted.

## Assumptions

- The target platform is Apple Silicon macOS using the existing 2brain Rec virtual microphone and speaker.
- The primary incident source is the 2026-06-04 real meeting recording package and associated route logs.
- The live incident is treated as a route stability problem, not as speaker-to-mic acoustic leakage.
- Existing short smoke acceptance for Chrome, Opera, Zoom, and Telemost remains useful context but is not sufficient for this feature.
- `Run Check` remains available as a repair/recheck action.
- Backend ingest and upload work may continue in parallel but is not required for this feature.
- Device-class matrix is clarified for `019`: built-in, wired, and USB are in scope; Bluetooth/AirPods are product backlog for a later slice.
