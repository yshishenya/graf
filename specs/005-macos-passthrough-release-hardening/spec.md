# Feature Specification: macOS Passthrough Release Hardening

**Feature Branch**: `005-macos-passthrough-release-hardening`

**Created**: 2026-06-01

**Status**: Draft

**Input**: User description: "After accepting real bidirectional passthrough, harden the macOS audio layer before adding recording. Keep the current non-recording passthrough behavior, but prioritize automated and low-manual validation now: CPU/no-hang behavior, device-change recovery, `coreaudiod` restart recovery, sleep/wake behavior, installer repair/update/uninstall regression, diagnostics redaction, and UX clarity that passthrough is active while recording is not. Defer full long-duration/manual call acceptance until recording exists, so the team can verify the audio path from recorded evidence. Recording, transcription, upload, MediaScribe, Langfuse, and new server workflows remain out of scope for this slice."

## Clarifications

### Session 2026-06-01

- Q: Should full manual long-duration call checks be required before recording exists? → A: No. Defer full long-duration/manual replay acceptance until local recording exists; this slice should focus on automated and low-manual pre-recording hardening.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prove Pre-Recording Stability Gates (Priority: P1)

As a macOS user, I want the installed driver and app to remain stable while common audio surfaces enumerate and use the virtual devices, so that we can safely proceed to recording without dragging known driver instability forward.

**Why this priority**: The previous feature proved the route works manually. Before adding recording, the product must prove the driver does not hang Core Audio or common audio settings surfaces.

**Independent Test**: Install the local package, open 2brain Rec normally, run runtime probes, open common audio settings surfaces, and record CPU/no-hang and route-state evidence without requiring a long manual meeting.

**Acceptance Scenarios**:

1. **Given** the installed app has auto-started non-recording passthrough, **When** runtime and no-hang checks run, **Then** both virtual devices remain visible/alive, public running state remains safe until a client opens them, and no recording/transcription/upload starts.
2. **Given** no meeting app is actively using the virtual devices, **When** 2brain Rec remains open for the idle stability window, **Then** `coreaudiod` does not sustain high CPU and common audio surfaces remain responsive.
3. **Given** a short browser smoke check is performed without recording, **When** the user confirms audio still works, **Then** the result is recorded as smoke evidence only, not final long-duration release acceptance.

---

### User Story 2 - Prove Core Audio And App Surfaces Do Not Hang (Priority: P1)

As a user, I want Zoom, browser audio settings, Telemost, and macOS Sound settings to open normally while the driver is installed and passthrough is active, so that the virtual driver does not destabilize common audio surfaces.

**Why this priority**: The prior debugging cycle exposed hangs around Core Audio enumeration and bridge startup. Release readiness requires explicit no-hang evidence.

**Independent Test**: With the driver installed and the app open, launch macOS Sound settings, Chrome meeting device settings, Opera meeting device settings, Zoom audio settings, and Telemost audio settings; verify they open within a bounded time and `coreaudiod` does not sustain high CPU.

**Acceptance Scenarios**:

1. **Given** 2brain Rec is open and passthrough is ready, **When** macOS Sound settings are opened, **Then** the settings UI becomes usable within 5 seconds.
2. **Given** 2brain Rec devices are selected in a browser or Zoom settings surface, **When** the user opens or changes audio settings, **Then** the target app does not hang and the route state remains truthful.
3. **Given** no meeting app is actively using the virtual devices, **When** the app remains open for 10 minutes, **Then** `coreaudiod` does not sustain CPU above 10% for more than 30 consecutive seconds.

---

### User Story 3 - Recover From Route And System Changes (Priority: P1)

As a user, I want 2brain Rec to fail clearly and recover safely when devices change, `coreaudiod` restarts, or the Mac sleeps and wakes, so that a meeting never silently uses a broken audio route.

**Why this priority**: Driver-first audio can fail through OS and hardware transitions. The release gate must prove fail-closed and recovery behavior beyond the happy path.

**Independent Test**: During validated passthrough, disconnect or switch physical input/output, restart `coreaudiod`, and run sleep/wake checks; record stale/degraded/ready transitions and user recovery actions.

**Acceptance Scenarios**:

1. **Given** passthrough is active, **When** the physical microphone or output changes, **Then** the route becomes stale or degraded within 5 seconds and requires revalidation or automatic safe recovery before showing ready.
2. **Given** passthrough is active, **When** `coreaudiod` restarts, **Then** the app detects the change, does not leave stale ready UI visible, and recovers only after app heartbeat and device visibility are valid again.
3. **Given** the Mac sleeps and wakes with 2brain Rec installed, **When** the user returns to a browser call or audio settings, **Then** devices remain visible or a clear repair/recheck path is shown without hidden recording.

---

### User Story 4 - Trust Installer And Repair Flows After Passthrough (Priority: P2)

As a user or tester, I want install, update, repair, rollback, uninstall, and reinstall flows to remain safe after the live passthrough work, so that the driver can be tested repeatedly without leaving broken Core Audio state.

**Why this priority**: Release hardening is not only live audio. A driver product must install, recover, and uninstall cleanly.

**Independent Test**: Build the local package, install it, run passthrough checks, perform repair/update/uninstall/reinstall/rollback scenarios, restart `coreaudiod` where required, and confirm device publication and app readiness match the documented state.

**Acceptance Scenarios**:

1. **Given** the local package is installed, **When** repair or update is run, **Then** 2brain Rec devices return to visible/alive state and passthrough can become ready without manual file cleanup.
2. **Given** uninstall is run, **When** `coreaudiod` refreshes, **Then** 2brain Rec virtual devices disappear and no stale HAL bundle remains active.
3. **Given** rollback or reinstall is run after a failed update, **When** the app opens, **Then** it reports either ready or a truthful repair action without hanging Core Audio.

---

### User Story 5 - Show Truthful Non-Recording UX And Diagnostics (Priority: P2)

As a user, I want the app to clearly say that passthrough is active but recording is not, and I want diagnostics to be safe to share, so that testers understand what is happening without exposing meeting content.

**Why this priority**: The product must preserve visible control and no-surprise recording. Hardening must make the accepted route understandable and supportable.

**Independent Test**: Open the app in ready, stale, degraded, failed, and repair states; verify the visible copy distinguishes passthrough from recording, recovery actions are clear, and diagnostic artifacts contain metadata only.

**Acceptance Scenarios**:

1. **Given** passthrough is active and no recording is active, **When** the user views the app, **Then** the UI says the audio route is ready/active and does not imply recording or transcription has started.
2. **Given** the route is stale, degraded, failed, or blocked, **When** the user views recovery guidance, **Then** the app presents the next action without claiming the route is safe.
3. **Given** diagnostics are exported or scanned, **When** release validation runs, **Then** no raw audio, transcript text, credentials, tokens, signed URLs, or meeting content are present.

---

### User Story 6 - Define Recording-Assisted Acceptance For The Next Slice (Priority: P3)

As a tester, I want the future full manual audio acceptance matrix to be defined now but not required in this pre-recording slice, so that we do not spend time on fragile manual checks that recording will make easier and more reliable.

**Why this priority**: Full long-duration verification is more valuable after local recording exists, because testers can replay evidence and inspect channel separation, distortion, dropouts, and loopback.

**Independent Test**: Review the generated follow-up acceptance checklist and confirm it explicitly waits for recording support before requiring long-duration call replay evidence.

**Acceptance Scenarios**:

1. **Given** recording is not yet implemented, **When** release-hardening tasks are generated, **Then** long-duration call replay acceptance is marked as a future gate rather than a blocker for this slice.
2. **Given** the next recording slice is planned, **When** it defines validation gates, **Then** it can reuse the future acceptance checklist for recorded mic path, speaker path, no-loopback, distortion, and dropout evidence.

### Edge Cases

- Browser or Zoom settings enumerate Core Audio devices while the app is still starting its bridge.
- The user opens the app immediately after install before `coreaudiod` has finished publishing devices.
- A short smoke call includes natural silence, device mute, loud remote audio, and intermittent network outage.
- Full long-duration call replay evidence is requested before recording exists.
- The physical microphone/output is unplugged, muted, changed to Bluetooth, or replaced by an aggregate/multi-output device.
- `coreaudiod` restarts while a browser still has stale virtual device IDs selected.
- The Mac sleeps or wakes while the driver is installed and the app is open.
- Repair/update/uninstall is attempted while a meeting app still has 2brain Rec devices selected.
- Diagnostics contain policy text or fixture strings that look like forbidden fields but are not live secrets.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a pre-recording release-hardening validation path that does not require long-duration manual call replay evidence.
- **FR-002**: The system MUST record short smoke evidence for local speech usability, remote audio usability, no remote-to-mic loopback observations, route state, CPU/no-hang behavior, and whether recording/transcription/upload remained inactive.
- **FR-003**: The system MUST verify that macOS Sound settings, Chrome audio settings, Opera audio settings, Zoom audio settings, and Telemost audio settings open without hanging while the driver is installed and the app is open.
- **FR-004**: The system MUST detect and document sustained `coreaudiod` CPU above the release threshold as a blocking release-hardening failure.
- **FR-005**: The system MUST verify physical microphone change, physical output change, aggregate/multi-output route, Bluetooth route, and stale browser device-ID behavior as passed, blocked, or not accepted with metadata-only evidence.
- **FR-006**: The system MUST verify `coreaudiod` restart recovery after install and during/after passthrough readiness.
- **FR-007**: The system MUST verify sleep/wake behavior for installed driver publication, app readiness, and safe stale/recheck state.
- **FR-008**: The system MUST verify install, update, repair, rollback, uninstall, and reinstall flows after passthrough implementation changes.
- **FR-009**: The system MUST keep automatic startup limited to local non-recording passthrough and MUST NOT start recording, transcription, upload, MediaScribe, Langfuse, or server workflows.
- **FR-010**: The UI MUST distinguish non-recording passthrough active/ready state from recording, transcript-only, and capture-active states.
- **FR-011**: The UI MUST show truthful stale, degraded, failed, blocked, repair, and recheck states without presenting device visibility alone as proof of live audio readiness.
- **FR-012**: Diagnostics and release evidence MUST contain route metadata only and MUST NOT contain raw audio, transcript text, credentials, tokens, signed URLs, or meeting content.
- **FR-013**: Release-hardening evidence MUST preserve the browser target matrix and mark unsupported or skipped targets as blocked/not accepted rather than passed.
- **FR-014**: The validation pipeline MUST include repeatable commands or checklists for build, runtime probe, no-hang, short smoke, recovery, installer, diagnostics, and UX gates.
- **FR-015**: The feature MUST NOT add new supported platforms, no-driver fallback, copied Krisp UI/copy, external network egress, or customer-facing recording automation.
- **FR-016**: The system MUST define long-duration recording-assisted acceptance as a future gate that depends on local recording support.

### Key Entities

- **Release Hardening Run**: A dated validation attempt covering build, installed runtime, no-hang, short smoke, recovery, installer, diagnostics, and UX gates.
- **Short Smoke Evidence**: Metadata-only evidence for target app, selected devices, route state transitions, user-observed audio usability, no-loopback observation, CPU observations, and blockers.
- **Core Audio Stability Evidence**: Metadata-only proof that common audio settings surfaces open and `coreaudiod` remains within release thresholds.
- **Route Recovery Evidence**: Metadata-only proof for device changes, `coreaudiod` restart, sleep/wake, stale state, and recovery path.
- **Installer Lifecycle Evidence**: Metadata-only proof for install, repair, update, rollback, uninstall, and reinstall behavior.
- **UX Readiness Evidence**: Screenshots or notes showing ready, active, stale, degraded, failed, repair, and non-recording states without meeting content.
- **Future Recording-Assisted Acceptance Checklist**: A deferred checklist for long-duration call replay, channel separation, distortion, dropout, and no-loopback verification after local recording exists.

### Constitutional Requirements *(mandatory for 2brain Rec)*

- **Capture/Driver Impact**: This feature directly hardens macOS driver, audio routing, passthrough, installer, degraded states, and recovery behavior. It must preserve the driver-first MVP, private app I/O fail-closed model, no-loopback gate, and measurable latency/no-hang/recovery criteria.
- **Visible Control Impact**: This feature changes readiness and status clarity but must not start recording or transcription. Non-recording passthrough must remain visible, and any future recording start/stop surface remains out of scope.
- **Data Boundary Impact**: This feature is local validation and metadata-only evidence. It must not add MediaScribe upload, Langfuse traces, LLM calls, analytics, server upload, storage, or external network egress.
- **Secrets Impact**: No credentials, tokens, signed URLs, passwords, or live credential paths may be stored in client state, diagnostics, logs, screenshots, or evidence artifacts.
- **Retention/Deletion Impact**: Release-hardening evidence is local metadata and screenshots/notes only. It must not create meeting-content artifacts, raw audio, transcripts, or server-side deletion obligations. Future recording-assisted acceptance belongs to a separate recording slice with its own retention/deletion rules.
- **Audit Impact**: Hardening must preserve auditability for readiness checks, passthrough start/stop, stale/degraded transitions, app I/O loss/recovery, installer lifecycle, and diagnostic export without content payloads.
- **UX/Brand/Accessibility Impact**: Any UI changes must use original 2brain Rec language, avoid Krisp-like copy/layout, be keyboard reachable, not rely on color alone, and use localization-safe status text.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The installed app completes pre-recording hardening checks without requiring long-duration manual call replay evidence and without starting recording, transcription, upload, or external egress.
- **SC-002**: During no-call idle with the installed app open, `coreaudiod` does not sustain CPU above 10% for more than 30 consecutive seconds.
- **SC-003**: macOS Sound settings and selected browser/meeting audio settings surfaces open within 5 seconds while the driver is installed and app is open.
- **SC-004**: Physical input/output changes and `coreaudiod` restart mark the route stale/degraded/blocked within 5 seconds or recover to ready only after valid route evidence.
- **SC-005**: Sleep/wake validation records either ready recovery or a truthful stale/repair state without hanging common audio surfaces.
- **SC-006**: Install, update, repair, rollback, uninstall, and reinstall evidence records passed or blocked/not accepted outcomes without manual hidden cleanup.
- **SC-007**: Diagnostics redaction validation finds no raw audio, transcript text, credentials, tokens, signed URLs, or meeting content outside deliberate policy/fixture strings.
- **SC-008**: Ready/active UI copy explicitly communicates non-recording passthrough and does not imply recording/transcription/capture has started.
- **SC-009**: All pre-recording release-hardening gates are represented in Spec Kit tasks and quickstart validation before implementation is accepted.
- **SC-010**: A future recording-assisted long-duration acceptance checklist exists and is explicitly marked as blocked until local recording support is available.

## Assumptions

- Feature `004-real-bidirectional-passthrough` is merged and accepted as the baseline for real local non-recording passthrough.
- The target release-hardening environment is Apple Silicon macOS with the local package installed in `/Applications`.
- Chrome, Opera, Zoom, macOS Sound settings, and Yandex Telemost are the primary no-hang/audio-settings surfaces for this slice; Yandex Browser may remain skipped/not accepted if explicitly documented.
- Built-in and wired physical input/output are release-quality targets; Bluetooth and AirPods-class devices remain managed pilot routes unless separately proven.
- Manual tester confirmation is acceptable for short smoke audio usability and no-loopback observations in this slice.
- Full long-duration call replay, distortion, dropout, channel-separation, and no-loopback proof is deferred until recording support exists, because recording will make the evidence easier to verify and less subjective.
- Recording, local buffering, upload, transcription, storage, MediaScribe, Langfuse, deletion, server workflows, customer policy, and assisted auto-start of capture remain out of scope.
