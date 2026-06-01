# Feature Specification: Low-Resource Reliable macOS Audio

**Feature Branch**: `006-low-resource-audio`

**Created**: 2026-06-01

**Status**: Draft

**Input**: User description: "Minimize macOS audio resource usage while preserving reliable virtual microphone and speaker passthrough. The solution must avoid Core Audio hangs, avoid blocking the UI, avoid always holding physical microphone/speaker when idle, recover safely after coreaudiod restart, and provide validation gates before replacing the currently working app-launch passthrough behavior."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Keep Audio Reliable While Reducing Idle Load (Priority: P1)

As a macOS meeting user, I want 2brain Rec to keep the virtual microphone and speaker reliable without holding physical microphone and speaker resources when no app is using the virtual devices, so that my Mac stays responsive and battery/resource usage remains low.

**Why this priority**: The current always-ready passthrough is reliable, but it keeps physical audio resources active. The next step must reduce idle load without reintroducing silent audio failures.

**Independent Test**: Open 2brain Rec with no browser or meeting app using the virtual devices, observe an idle-safe state with no sustained physical mic/speaker assertions, then start a browser/meeting audio check and confirm audio becomes ready without pressing `Run Check`.

**Acceptance Scenarios**:

1. **Given** 2brain Rec is open and no client is using the virtual devices, **When** the idle grace window expires, **Then** physical mic/speaker resources are released while the virtual devices remain visible and safe.
2. **Given** the app is in idle-safe state, **When** a browser or meeting app starts using 2brain Rec Microphone or 2brain Rec Speaker, **Then** passthrough becomes ready automatically without a manual readiness button.
3. **Given** passthrough becomes ready automatically, **When** the user joins a browser or Telemost-style call, **Then** the user can hear and be heard with no remote-to-mic loopback and no hidden recording.

---

### User Story 2 - Prevent Core Audio And UI Hangs (Priority: P1)

As a user, I want 2brain Rec and common audio settings surfaces to remain responsive even when Core Audio is restarting, slow, or unhealthy, so that a driver problem never freezes browser, meeting, or system audio settings.

**Why this priority**: Recent validation showed that physical audio setup and Core Audio enumeration can block. Resource optimization is not acceptable if it increases hang risk.

**Independent Test**: Restart Core Audio, open 2brain Rec, macOS Sound settings, browser audio settings, Zoom, and Telemost surfaces; verify they remain responsive and blocked audio setup is reported truthfully rather than freezing.

**Acceptance Scenarios**:

1. **Given** Core Audio has just restarted, **When** 2brain Rec opens, **Then** the UI remains responsive and does not perform an unbounded blocking audio startup on the main UI path.
2. **Given** a physical audio setup attempt is slow or blocked, **When** the bounded startup window expires, **Then** 2brain Rec shows a stale/blocked state and provides a safe retry path.
3. **Given** a no-hang target opens while 2brain Rec is installed, **When** the target enumerates audio devices, **Then** the target becomes usable within the release threshold or the failure is recorded as blocked, not passed.

---

### User Story 3 - Recover Safely Across System Transitions (Priority: P1)

As a user, I want 2brain Rec to recover safely after `coreaudiod` restart, sleep/wake, device changes, and stale browser device selections, so that audio does not silently remain broken or overloaded.

**Why this priority**: Low-resource mode must make state transitions more careful, not more fragile.

**Independent Test**: Trigger `coreaudiod` restart, sleep/wake, physical input/output changes, and stale browser device IDs; verify the app moves through idle, stale, blocked, and ready states truthfully and recovers only after valid route evidence.

**Acceptance Scenarios**:

1. **Given** passthrough is ready, **When** `coreaudiod` restarts, **Then** the app clears ready state quickly and does not attempt unsafe startup until Core Audio is stable.
2. **Given** the app is idle-safe, **When** the Mac sleeps and wakes, **Then** virtual devices remain visible or a repair/recheck state is shown without hidden recording or stale ready UI.
3. **Given** a browser has stale virtual device IDs selected, **When** the route is reactivated, **Then** the user receives a truthful ready, stale, or blocked state within the release threshold.

---

### User Story 4 - Preserve The Current Working Path Until Replacement Is Proven (Priority: P2)

As a tester, I want low-resource mode to be gated behind explicit validation until it proves equal or better reliability than the current working app-launch passthrough, so that we do not regress working microphone and speaker behavior.

**Why this priority**: The current behavior works for the user. Optimization must be accepted only after it passes a stronger reliability matrix.

**Independent Test**: Run both current working passthrough and low-resource mode through the same browser/meeting, no-hang, runtime, CPU, and recovery gates; accept low-resource mode only if it meets or exceeds the baseline.

**Acceptance Scenarios**:

1. **Given** low-resource mode is not fully accepted, **When** the app is installed for normal local testing, **Then** the working app-launch passthrough remains the default.
2. **Given** low-resource mode is enabled for validation, **When** any P1 audio or no-hang gate fails, **Then** the mode remains blocked and the working default is preserved.
3. **Given** low-resource mode passes all required gates, **When** the project promotes it, **Then** the release evidence records baseline parity for audio usability, no-loopback, no-hang, CPU, and recovery.

### Edge Cases

- Core Audio is restarted immediately before opening 2brain Rec.
- Core Audio device enumeration is slow, blocked, or overloaded.
- A browser opens audio settings while passthrough is idle-safe or starting.
- A meeting app opens only one of the virtual devices.
- A client briefly opens and closes a virtual device during startup.
- Physical mic or speaker is unavailable, muted, busy, Bluetooth-routed, or replaced by aggregate/multi-output devices.
- The route becomes idle during natural silence.
- The app is quit while a startup attempt is slow or blocked.
- Diagnostics contain policy or fixture strings that look like forbidden fields but are not secrets.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST reduce idle resource usage by releasing physical mic/speaker resources when no virtual-device client is active for the accepted idle window.
- **FR-002**: The system MUST keep 2brain Rec virtual microphone and speaker visible and fail-closed while physical resources are released.
- **FR-003**: The system MUST reactivate passthrough automatically when a supported browser or meeting client uses the virtual devices, without requiring `Run Check`.
- **FR-004**: The system MUST NOT use an unbounded blocking startup path that can freeze the app UI or common audio settings surfaces.
- **FR-005**: The system MUST bound slow or blocked audio setup attempts and show a truthful stale/blocked state when readiness cannot be proven.
- **FR-006**: The system MUST avoid running Core Audio enumeration and physical audio startup concurrently in a way that can deadlock common audio surfaces.
- **FR-007**: The system MUST preserve the current working app-launch passthrough as the default until low-resource mode passes all P1 gates.
- **FR-008**: The system MUST record metadata-only evidence for idle release, automatic reactivation, no-hang behavior, CPU behavior, route recovery, and fallback decisions.
- **FR-009**: The system MUST recover safely after `coreaudiod` restart, sleep/wake, physical device changes, and stale browser device selections before showing ready.
- **FR-010**: The system MUST NOT start recording, transcription, upload, MediaScribe, Langfuse, analytics, or external network egress as part of this feature.
- **FR-011**: The system MUST distinguish idle-safe, starting, ready, stale, blocked, failed, and retry states in UI and diagnostics.
- **FR-012**: Diagnostics and validation artifacts MUST NOT contain raw audio, transcript text, meeting content, credentials, tokens, signed URLs, or passwords.
- **FR-013**: The validation pipeline MUST include a regression guard proving that low-resource behavior does not reintroduce the previous "works only after Run Check" failure.
- **FR-014**: The validation pipeline MUST include a regression guard proving that startup cannot leave Core Audio or the app stuck in an unbounded starting state.

### Key Entities *(include if feature involves data)*

- **Audio Resource State**: The current readiness/resource mode: idle-safe, starting, ready, stale, blocked, failed, or retrying.
- **Client Activity Evidence**: Metadata-only signal that a supported app is actively using one or both virtual devices.
- **Startup Attempt Evidence**: Metadata-only record of startup timing, outcome, blocker reason, and whether fallback preserved the working default.
- **Idle Release Evidence**: Metadata-only proof that physical resources were released after the idle window while virtual devices remained safe.
- **Recovery Evidence**: Metadata-only proof for `coreaudiod` restart, sleep/wake, device-change, and stale-client transitions.

### Constitutional Requirements *(mandatory for 2brain Rec)*

- **Capture/Driver Impact**: This feature directly changes macOS driver/audio routing readiness, passthrough lifecycle, degraded states, and recovery. It must preserve driver-first MVP behavior, fail-closed audio, no-loopback gates, and measurable no-hang/CPU/recovery criteria.
- **Visible Control Impact**: This feature must not start recording or transcription. It may change readiness/status states, but the user must always see whether passthrough is idle-safe, starting, ready, stale, blocked, or failed.
- **Data Boundary Impact**: This feature is local-only. It must not add MediaScribe upload, Langfuse traces, LLM calls, analytics, server upload, storage, or external network egress.
- **Secrets Impact**: No credentials, tokens, signed URLs, passwords, or live credential paths may be stored in client state, diagnostics, logs, screenshots, or evidence artifacts.
- **Retention/Deletion Impact**: This feature must not create meeting-content artifacts, raw audio, transcripts, or server-side deletion obligations. Validation evidence is metadata-only.
- **Audit Impact**: The system must preserve auditability for idle release, automatic reactivation, startup timeout/blocking, stale/degraded transitions, fallback, and recovery.
- **UX/Brand/Accessibility Impact**: Any UI state changes must use original 2brain Rec language, be keyboard reachable, not rely on color alone, and remain brand-distinct from Krisp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With no virtual-device client active, physical mic/speaker resources are released after the accepted idle window while virtual devices remain visible and fail-closed.
- **SC-002**: From idle-safe state, a supported browser or meeting client can activate both microphone and speaker passthrough without pressing `Run Check`.
- **SC-003**: macOS Sound settings, Chrome, Opera, Zoom, and Telemost audio surfaces open within 5 seconds while low-resource mode is installed or record a blocked failure without hanging.
- **SC-004**: No startup attempt can leave the app UI or validation command blocked beyond the accepted startup timeout.
- **SC-005**: During idle and no-call windows, `coreaudiod` does not sustain CPU above 10% for more than 30 consecutive seconds.
- **SC-006**: After `coreaudiod` restart, sleep/wake, or physical device change, ready UI is cleared within 5 seconds and restored only after valid route evidence.
- **SC-007**: Low-resource mode passes the same browser/meeting smoke matrix as the current working default: user is heard, user hears, no remote-to-mic loopback, and no hidden recording.
- **SC-008**: If any P1 gate fails, the current working app-launch passthrough remains the default and low-resource mode is marked blocked/not accepted.
- **SC-009**: Diagnostics redaction validation finds no raw audio, transcript text, credentials, tokens, signed URLs, passwords, or meeting content outside deliberate policy/fixture strings.

## Assumptions

- The current accepted baseline is the working app-launch non-recording passthrough from feature `005-macos-passthrough-release-hardening`.
- The first low-resource rollout may be internal/validation-only until it proves parity with the baseline.
- Local recording, transcription, upload, retention, deletion, server workflows, MediaScribe, and Langfuse remain out of scope.
- The target validation environment is Apple Silicon macOS with the local package installed in `/Applications`.
- Chrome, Opera, Zoom, macOS Sound settings, and Yandex Telemost remain the primary no-hang/browser-meeting validation surfaces.
