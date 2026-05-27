# Feature Specification: macOS Virtual Audio Driver MVP

**Feature Branch**: `001-macos-audio-driver`

**Created**: 2026-05-27

**Status**: Draft

**Input**: User description: "macOS virtual audio driver MVP"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete Driver Setup And Route Verification (Priority: P1)

As an internal team user on macOS, I want to install 2brain Rec and verify that
`2brain Rec Microphone` and `2brain Rec Speaker` are correctly routed before a
meeting, so that I know capture is ready and live call audio will still pass
through normally.

**Why this priority**: The product cannot enter private alpha unless users can
install the virtual audio layer, see both virtual devices, select physical
input/output devices, and verify both mic and speaker routes without guessing.

**Independent Test**: Can be fully tested by installing on a supported Mac,
selecting a physical microphone and physical output, completing route
verification, and confirming the app reaches `ready` only after both paths are
validated.

**Acceptance Scenarios**:

1. **Given** a supported Mac with no existing 2brain Rec driver, **When** the
   user completes installation and grants required permissions, **Then** both
   virtual devices appear in macOS audio settings and onboarding continues to
   route verification.
2. **Given** the virtual microphone is not selected by the meeting target,
   **When** the user runs route verification, **Then** the app shows a specific
   virtual microphone routing failure and does not show fully ready.
3. **Given** the virtual speaker is not receiving remote audio, **When** the
   user runs route verification, **Then** the app shows a specific speaker route
   failure and does not show fully ready.
4. **Given** both mic and speaker routes are verified, **When** onboarding
   completes, **Then** the app shows `ready` with mic and speaker route status.

---

### User Story 2 - Capture Separate Tracks Without Breaking The Call (Priority: P1)

As a user in a supported browser meeting, I want 2brain Rec to capture my local
microphone and remote meeting audio as separate tracks while I continue hearing
and speaking normally, so that the eventual transcript can distinguish my speech
from remote participant audio.

**Why this priority**: Separate local/remote capture and passthrough integrity
are the core product risk. Without them, backend transcription and notes do not
matter.

**Independent Test**: Can be tested with a supported browser meeting by selecting
`2brain Rec Microphone` and `2brain Rec Speaker`, recording for 30 minutes, and
confirming local mic and remote speaker tracks are present, aligned, and free of
remote-to-mic loopback.

**Acceptance Scenarios**:

1. **Given** a meeting target uses both 2brain Rec virtual devices, **When** the
   user starts audio-recording mode, **Then** local mic audio and remote speaker
   audio are captured as separate tracks.
2. **Given** remote participants speak while the user is silent, **When** the
   recording is inspected, **Then** remote audio is present only on the remote
   speaker track and not fed into the virtual microphone path.
3. **Given** the network or server is unavailable during an active call,
   **When** capture continues locally, **Then** live audio passthrough remains
   usable and the app shows buffered/degraded state instead of stopping
   passthrough.
4. **Given** the user records a 60-minute call, **When** the recording completes,
   **Then** local and remote track timestamps remain aligned within the accepted
   threshold.

---

### User Story 3 - Recover From Driver, Permission, And Device Failures (Priority: P2)

As a user, I want clear recovery steps when the driver, permissions, physical
devices, or routes fail, so that I can repair capture readiness without losing
call audio or believing the system is ready when it is not.

**Why this priority**: Driver products fail in many ordinary ways. The MVP must
make failure states explicit and recoverable before daily internal use.

**Independent Test**: Can be tested by revoking permissions, switching physical
devices, restarting the app, restarting the meeting target, and confirming each
state produces a specific visible diagnosis and recovery path.

**Acceptance Scenarios**:

1. **Given** microphone permission is denied or revoked, **When** the user opens
   Audio Health, **Then** the app identifies the permission problem and shows a
   guided recovery action.
2. **Given** a physical microphone or speaker changes mid-session, **When** the
   route becomes invalid, **Then** the app updates state to degraded or error
   and does not silently drop audio.
3. **Given** the virtual audio component needs repair or update, **When** the
   user opens driver status, **Then** the app shows install, repair, update, or
   uninstall actions appropriate to the state.
4. **Given** the app restarts during a capture session, **When** it returns,
   **Then** it preserves or truthfully reports local capture/buffer state and
   does not claim completion for missing or unfinalized audio.

---

### User Story 4 - Uninstall Cleanly And Restore User Confidence (Priority: P3)

As a user, I want uninstall and rollback to remove 2brain Rec virtual devices
and avoid leaving my system audio in a confusing state, so that I can safely
recover from a failed install or stop using the alpha.

**Why this priority**: Clean uninstall is necessary for trust and for internal
alpha recovery, but it can follow core install/capture validation.

**Independent Test**: Can be tested by installing, selecting virtual devices,
uninstalling, and confirming virtual devices and related startup/background
artifacts are removed or clearly reported as requiring manual OS-level cleanup.

**Acceptance Scenarios**:

1. **Given** 2brain Rec is installed, **When** the user uninstalls it, **Then**
   virtual devices and app-managed background artifacts are removed where the OS
   permits.
2. **Given** the prior physical microphone and speaker can be restored, **When**
   uninstall completes, **Then** the app attempts restoration and reports the
   result.
3. **Given** uninstall cannot remove an OS-managed artifact automatically,
   **When** cleanup finishes, **Then** the user sees a clear manual remediation
   step rather than a false success message.

### Edge Cases

- Install completes but macOS requires restart before virtual devices appear.
- Required permission is denied during onboarding, after onboarding, or
  mid-session.
- The selected physical microphone is silent, muted, noisy, disconnected, or
  changes sample behavior during capture.
- The selected physical output is unavailable, muted, switched to Bluetooth, or
  changes profile mid-session.
- The user selects a 2brain Rec virtual device as its own physical source or
  output.
- The browser/meeting target restarts or switches audio devices mid-session.
- The desktop app restarts while audio is buffered locally.
- The server or network is unavailable for at least 5 minutes.
- Local disk reaches warning, critical, or reserve thresholds during capture.
- The driver install, update, repair, rollback, or uninstall fails.
- A supported meeting target produces only one side of audio.
- A 30-minute or 60-minute call has dropout, clock drift, or track misalignment.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose exactly two MVP virtual audio devices named
  `2brain Rec Microphone` and `2brain Rec Speaker`.
- **FR-002**: `2brain Rec Microphone` MUST send selected physical microphone
  audio to meeting targets and MUST NOT include remote participant audio.
- **FR-003**: `2brain Rec Speaker` MUST receive remote meeting audio, route it
  to the selected physical output, and mirror it for capture.
- **FR-004**: The system MUST block or clearly reject virtual-device self-routing
  where a 2brain Rec virtual device is selected as its own source or output.
- **FR-005**: The system MUST verify both local microphone route and remote
  speaker route before showing fully ready.
- **FR-006**: The system MUST distinguish driver failure, routing failure,
  permission failure, physical device failure, server failure, and network
  failure in user-visible states.
- **FR-007**: The system MUST capture local mic and remote speaker audio as
  separate tracks in audio-recording mode.
- **FR-008**: The system MUST support transcript-only mode with the same route
  validation requirements as audio-recording mode.
- **FR-009**: The system MUST continue live audio passthrough when upload,
  transcription, server connectivity, or network connectivity fails.
- **FR-010**: The system MUST buffer capture locally in encrypted form when
  upload cannot complete.
- **FR-011**: The system MUST show warning before local buffering reaches the
  point where capture is at risk.
- **FR-012**: The system MUST stop new capture or mark capture degraded before
  data loss if local buffer limits or disk reserve would be violated.
- **FR-013**: The system MUST never silently drop audio.
- **FR-014**: The system MUST add dropout markers when audio discontinuities are
  detected.
- **FR-015**: The system MUST provide visible local capture indication whenever
  recording or transcript-only capture is active.
- **FR-016**: The system MUST provide one-action stop from a local visible
  surface during active capture.
- **FR-017**: The system MUST support manual start, pause/resume, and stop when
  workspace policy permits recording.
- **FR-018**: The system MUST represent assisted auto-start only as a
  policy-gated internal MVP capability and MUST keep manual start/stop
  available.
- **FR-019**: Assisted auto-start MUST NOT trigger from arbitrary system audio,
  media playback, notification sounds, music, videos, or non-approved apps.
- **FR-020**: The system MUST show `detecting` rather than starting capture when
  meeting-like activity is uncertain.
- **FR-021**: The system MUST record trigger evidence and policy snapshot for
  assisted auto-start sessions.
- **FR-022**: The system MUST provide Audio Health diagnostics for physical mic,
  physical output, virtual mic, virtual speaker, route graph, live meters,
  route verification, driver status, permissions, test recording, and test
  playback.
- **FR-023**: The system MUST provide install, update, repair, rollback, and
  uninstall flows with explicit user-visible outcomes.
- **FR-024**: Updates MUST NOT interrupt an active call; if an update is needed
  during active capture, it MUST defer or require explicit safe timing.
- **FR-025**: Uninstall MUST remove app-managed virtual devices and background
  artifacts where the OS permits and MUST report any remaining manual cleanup.
- **FR-026**: The system MUST attempt to restore the previous physical
  microphone and speaker after uninstall where the OS permits.
- **FR-027**: The system MUST produce diagnostics for install, route, driver,
  permission, capture, and uninstall failures without including raw audio,
  transcript text, credentials, tokens, or signed URLs by default.
- **FR-028**: The system MUST mark any recording with missing required tracks as
  degraded and MUST make the missing path visible before finalization.
- **FR-029**: The system MUST preserve enough track timing metadata to align mic
  and remote tracks for playback and later transcription.
- **FR-030**: The system MUST support official MVP validation on Apple Silicon
  Macs with macOS 14.5 and the latest stable macOS at release-candidate time.
- **FR-031**: The system MUST treat Intel Mac support as unsupported for MVP
  unless a later release decision adds it to the full QA matrix.
- **FR-032**: The system MUST label unsupported or unverified meeting targets as
  best-effort rather than officially supported.

### Key Entities *(include if feature involves data)*

- **Virtual Audio Device**: A user-selectable audio endpoint exposed by 2brain
  Rec. Key attributes include name, direction, availability state, version
  compatibility, and route validation state.
- **Physical Audio Device**: A user-selected microphone or output device. Key
  attributes include display name, direction, availability, active/inactive
  signal state, muted/silent/noisy state, and last verification result.
- **Route Verification**: A readiness check that proves the mic path and remote
  speaker path are both usable. Key attributes include path, status, failure
  reason, timestamp, and recovery action.
- **Capture Session**: A local capture attempt for audio-recording or
  transcript-only mode. Key attributes include mode, source app if detected,
  start trigger, policy snapshot, track states, buffer state, and visible
  indicator state.
- **Audio Track**: A captured stream such as local mic or remote speaker. Key
  attributes include track role, continuity state, timing metadata, dropout
  markers, and finalization state.
- **Local Buffer Item**: Encrypted local capture data awaiting upload or purge.
  Key attributes include meeting/session association, size, age, retention
  deadline, upload state, and purge state.
- **Driver Health Report**: A diagnostic summary of install, permissions,
  version, route, passthrough, and recovery status. It must not contain raw
  audio or secrets by default.

### Constitutional Requirements *(mandatory for 2brain Rec)*

- **Capture/Driver Impact**: This feature directly defines the macOS driver MVP.
  It requires separate local mic and remote speaker tracks, no remote-to-mic
  loopback, local passthrough during upload/server failure, explicit degraded
  states, installer/update/uninstall recovery, and Phase 0 approval of driver
  decisions before coding.
- **Visible Control Impact**: This feature touches capture state, onboarding,
  tray/widget, Audio Health, manual start/stop, and assisted auto-start. It
  requires persistent visible active-capture indication, one-action stop,
  manual control, no invisible recording, and `detecting` state when auto-start
  confidence is uncertain.
- **Data Boundary Impact**: This feature creates local capture data and upload
  readiness, but the desktop app must not send audio directly to MediaScribe.
  Audio must go through the self-hosted 2brain Rec ingest path once backend
  upload is available.
- **Secrets Impact**: This feature touches device/auth/upload readiness only at
  the boundary. It must not store MediaScribe credentials and must keep
  diagnostics free of credentials, tokens, signed URLs, raw audio, and
  transcript text by default.
- **Retention/Deletion Impact**: Local buffer items created by this feature must
  have retention deadlines, upload states, purge states, and deletion reporting
  hooks. A server purge must not be represented as local purge unless the
  desktop acknowledges purge or the local expiry window passes.
- **Audit Impact**: The feature must define audit-relevant events for driver
  installed, updated, repaired, uninstalled, permission changed, route verified,
  capture started, capture stopped, assisted auto-start triggered, local buffer
  entered, upload failed, and local purge acknowledged.
- **UX/Brand/Accessibility Impact**: This feature changes onboarding, Audio
  Health, tray/widget state, and capture indicators. It requires accessible
  state labels, non-color cues, keyboard-reachable stop, localization-safe
  labels, and clean-room 2brain Rec UI rather than Krisp imitation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 90% of internal pilot users can complete install,
  permissions, mic route verification, and speaker route verification without
  engineering assistance on supported Macs.
- **SC-002**: Fully ready state is never shown unless both mic and speaker routes
  have passed verification in the current setup.
- **SC-003**: In supported wired-audio 60-minute calls, local mic and remote
  speaker tracks remain aligned within 100 ms.
- **SC-004**: In supported wired-audio 60-minute calls, dropped frames remain
  below 0.1%.
- **SC-005**: In supported Bluetooth 60-minute calls, dropped frames remain
  below 0.5% or the unsupported/limited profile condition is documented
  in-product before capture.
- **SC-006**: A 5-minute network or server outage during active capture does not
  interrupt live mic or speaker passthrough.
- **SC-007**: Active capture state is identifiable without opening the desktop
  app and can be stopped in one interaction from a local visible surface.
- **SC-008**: No private-alpha release candidate ships with unresolved
  virtual-device install, passthrough, recording integrity, invisible-recording,
  uninstall, or rollback P0 defects.
- **SC-009**: Diagnostics generated from driver or route failures contain no raw
  audio, transcript text, credentials, tokens, or signed URLs by default.
- **SC-010**: The app blocks or marks capture degraded before local buffer limits
  or disk reserve conditions can cause silent audio loss.

## Assumptions

- MVP platform is macOS on Apple Silicon.
- Minimum supported macOS version is 14.5, with latest stable macOS also covered
  at release-candidate time.
- Official MVP meeting targets are browser-based meetings in Chrome, Opera, and
  Yandex Browser, plus Yandex Telemost in browser after QA.
- Other apps that can select `2brain Rec Microphone` and `2brain Rec Speaker`
  may work but are best-effort unless added to the QA matrix.
- The desktop app will authenticate to the 2brain Rec server in a later or
  adjacent feature; this feature defines local driver/capture readiness and
  local buffer behavior.
- MediaScribe submission is out of scope for the desktop driver feature because
  desktop clients must upload to 2brain Rec server-side ingest first.
- Screen/video recording, bot mode, live transcription, Windows support, and
  noise suppression are out of scope for this feature.
