# Feature Specification: Low-Resource Reliable macOS Audio

**Feature Branch**: `006-low-resource-audio`

**Created**: 2026-06-01

**Status**: Draft

**Input**: User description: "Minimize macOS audio resource usage while preserving reliable virtual microphone and speaker passthrough. The solution must avoid Core Audio hangs, avoid blocking the UI, avoid always holding physical microphone/speaker when idle, recover safely after coreaudiod restart, and provide validation gates before replacing the currently working app-launch passthrough behavior."

## Clarifications

### Session 2026-06-01

- Q: Should low-resource mode remain validation/internal until extended acceptance, or become default after local automated gates pass? → A: Low-resource mode becomes the default after local automated gates pass.
- Q: What is the maximum allowed automatic passthrough activation window before the system must stop waiting and report blocked/fallback? → A: 3 seconds.
- Q: Should low-resource behavior mean blocking/releasing routes aggressively, or keeping a lightweight always-published virtual layer with physical routing only when a stream needs it? → A: Keep a lightweight always-published virtual layer; never block or mute a default-selected virtual route just to save resources.
- Q: Should recording be owned by the driver or by the application software above the driver? → A: The driver owns virtual device publication and routing only; application software owns recording and transcription triggers.
- Q: Should active-stream detection rely on audio energy/silence or explicit client IO state? → A: Use explicit client IO state; natural silence must not be treated as idle.

## Current Baseline And Scope Decision

The accepted current baseline is the non-recording app-launch passthrough stabilized during feature `005-macos-passthrough-release-hardening`: when the route is active, browser and meeting apps can hear and be heard without pressing `Run Check`, and recording/transcription/upload are not started. Feature `006-low-resource-audio` replaces only the route lifecycle/resource strategy, not the product boundary around recording.

Clean-room Krisp observation shows a split model: a native HAL driver publishes virtual devices and tracks client IO, while the app/native media layer chooses physical working devices, owns processing graphs, and decides whether recording/transcription features run. 2brain Rec will follow the same architectural principle without copying proprietary implementation: driver owns virtual device publication, fail-closed routing, and realtime-safe IO; application software owns physical-device orchestration, diagnostics, recovery, and future recording/transcription triggers.

The selected MVP behavior for 2brain Rec is visible fail-closed virtual devices, not surprise device hiding. Existing app-health code or older plans that hide devices when the app heartbeat is stale must be treated as a conflict to resolve during planning. Hiding devices may be revisited later only behind separate acceptance gates, because stale browser selections and user trust become harder when virtual devices disappear.

The current implementation already has useful pieces: HAL virtual microphone/speaker publication, explicit driver `StartIO`/`StopIO` running-state evidence, shared-memory audio handoff, heartbeat-based fail-closed behavior, and self-routing guards. The implementation is not yet accepted for this feature because app-side Core Audio setup can still happen through synchronous startup paths, physical AudioUnit setup/enumeration may block common audio surfaces, and the product does not yet have exhaustive validation proving low-resource startup cannot reintroduce silence, distortion, hangs, or "works only after Run Check" behavior.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Keep Audio Reliable With A Lightweight Virtual Layer (Priority: P1)

As a macOS meeting user, I want 2brain Rec virtual microphone and speaker to stay continuously available as a lightweight routing layer, while heavy physical passthrough work runs only when an audio stream needs it and recording/transcription runs only when application software explicitly triggers it, so that my Mac stays responsive without losing sound.

**Why this priority**: The current always-ready passthrough is reliable, but it may keep more physical audio work active than needed. The next step must reduce idle load without muting a default-selected virtual speaker, breaking a virtual microphone, or reintroducing silent audio failures.

**Independent Test**: Set 2brain Rec virtual devices as the selected devices, open 2brain Rec with no active browser or meeting audio stream, observe a lightweight idle state without sustained heavy routing work or recording, then start a browser/meeting audio check and confirm audio flows automatically without pressing `Run Check`.

**Acceptance Scenarios**:

1. **Given** 2brain Rec virtual devices are published, **When** no client is actively streaming through them, **Then** the system remains in a lightweight idle state while the virtual devices stay visible and safe.
2. **Given** 2brain Rec Speaker is selected as a system or app output, **When** audio is played through it, **Then** the user continues hearing sound through the chosen physical output and the system must not mute the route just to save resources.
3. **Given** the app is in lightweight idle state, **When** a browser or meeting app starts using 2brain Rec Microphone or 2brain Rec Speaker, **Then** passthrough becomes ready automatically without a manual readiness button.
4. **Given** passthrough becomes ready automatically, **When** the user joins a browser or Telemost-style call, **Then** the user can hear and be heard with no remote-to-mic loopback and no hidden recording.
5. **Given** audio is flowing through the virtual devices, **When** no application-level recording trigger is active, **Then** the driver routes audio only and does not create meeting recordings, transcripts, uploads, or transcription jobs.
6. **Given** a client stream is open but naturally silent, **When** the idle detector evaluates the route, **Then** the stream remains active and is not downgraded to idle solely because audio energy is low.

---

### User Story 2 - Prevent Core Audio And UI Hangs (Priority: P1)

As a user, I want 2brain Rec and common audio settings surfaces to remain responsive even when Core Audio is restarting, slow, or unhealthy, so that a driver problem never freezes browser, meeting, or system audio settings.

**Why this priority**: Recent validation showed that physical audio setup and Core Audio enumeration can block. Resource optimization is not acceptable if it increases hang risk.

**Independent Test**: Restart Core Audio, open 2brain Rec, macOS Sound settings, browser audio settings, Zoom, and Telemost surfaces; verify they remain responsive and blocked audio setup is reported truthfully rather than freezing.

**Acceptance Scenarios**:

1. **Given** Core Audio has just restarted, **When** 2brain Rec opens, **Then** the UI remains responsive and does not perform an unbounded blocking audio startup on the main UI path.
2. **Given** a physical audio setup attempt is slow or blocked, **When** the 3-second bounded startup window expires, **Then** 2brain Rec shows a stale/blocked state and provides a safe retry path.
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

### User Story 4 - Promote Low-Resource Mode After Local Gates Pass (Priority: P2)

As a tester, I want low-resource mode to become the default after it passes local automated audio, no-hang, CPU, and recovery gates, so that users benefit from lower resource usage without waiting for a longer manual acceptance phase.

**Why this priority**: The current behavior works for the user, but the product goal is to minimize resource usage. Promotion is acceptable after local automated gates pass, while failed gates must preserve the working default.

**Independent Test**: Run low-resource mode through local browser/meeting, no-hang, runtime, CPU, and recovery gates; promote it to default only when every P1 local gate passes.

**Acceptance Scenarios**:

1. **Given** low-resource mode passes all local P1 gates, **When** the app is installed for normal local testing, **Then** low-resource mode becomes the default behavior.
2. **Given** low-resource mode is enabled for validation, **When** any P1 audio or no-hang gate fails, **Then** the mode remains blocked and the working default is preserved.
3. **Given** low-resource mode is promoted, **When** future validation finds a P1 regression, **Then** the product can fall back to the previous working app-launch passthrough without reinstalling the driver.

---

### User Story 5 - Keep The App/Driver Boundary Observable And Reversible (Priority: P1)

As an engineer and tester, I want the route to be explained by separate evidence for driver publication, client IO activity, and app bridge health, so that a visible virtual device is never mistaken for a working live route and a failed bridge never records, blocks, or loops audio silently.

**Why this priority**: Previous failures were confusing because devices could be visible while live passthrough was not actually ready, and because manual readiness checks could accidentally activate the route. The product needs explicit state planes before resource optimization becomes default.

**Independent Test**: Inspect diagnostics after idle, active stream, app quit, stale heartbeat, Core Audio restart, and self-routing attempts; verify each state records publication, client IO/running, app bridge heartbeat/readiness, and recording state separately.

**Acceptance Scenarios**:

1. **Given** the driver publishes virtual devices, **When** the app bridge heartbeat is stale, **Then** diagnostics show publication separately from live-route readiness and audio fails closed without recording.
2. **Given** a browser opens a silent microphone stream, **When** the route evaluates activity, **Then** client IO state keeps the route active even if audio samples are near zero.
3. **Given** the app accidentally selects a 2brain Rec virtual device, known virtual device, aggregate device, or multi-output device as a physical working device, **When** the route validates devices, **Then** the route is refused, repaired, or explicitly marked not release-ready.
4. **Given** low-resource mode is promoted, **When** validation later detects a P1 route regression, **Then** the app can revert to the previous working route lifecycle without reinstalling the HAL driver.

---

### Edge Cases

- Core Audio is restarted immediately before opening 2brain Rec.
- Core Audio device enumeration is slow, blocked, or overloaded.
- A browser opens audio settings while passthrough is idle-safe or starting.
- A meeting app opens only one of the virtual devices.
- A client briefly opens and closes a virtual device during startup.
- Physical mic or speaker is unavailable, muted, busy, Bluetooth-routed, or replaced by aggregate/multi-output devices.
- The route has natural silence while a client stream is still active.
- The selected physical working device is accidentally one of 2brain Rec's own virtual devices.
- The selected physical working device is another virtual, aggregate, multi-output, or chained audio device that can create loops, latency, or unsupported routing.
- The app heartbeat becomes stale while a browser still has 2brain Rec Speaker selected as output.
- The app exits while virtual devices remain selected as system defaults.
- The driver is loaded but app bridge setup fails before physical devices are ready.
- The app is quit while a startup attempt is slow or blocked.
- A future recording trigger subscribes to routed audio while passthrough is already active.
- Diagnostics contain policy or fixture strings that look like forbidden fields but are not secrets.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST reduce idle resource usage by keeping an always-published lightweight virtual layer and avoiding sustained heavy physical passthrough or processing work when no client stream needs it.
- **FR-002**: The system MUST keep 2brain Rec virtual microphone and speaker visible and fail-closed while idle, without muting or blocking a default-selected virtual speaker route that is actively receiving audio.
- **FR-003**: The system MUST reactivate passthrough automatically when a supported browser or meeting client uses the virtual devices, without requiring `Run Check`.
- **FR-004**: The system MUST NOT use an unbounded blocking startup path that can freeze the app UI or common audio settings surfaces.
- **FR-005**: The system MUST bound slow or blocked audio setup attempts to 3 seconds and show a truthful stale/blocked state when readiness cannot be proven.
- **FR-006**: The system MUST avoid running Core Audio enumeration and physical audio startup concurrently in a way that can deadlock common audio surfaces.
- **FR-007**: The system MUST promote low-resource mode to the default after all local P1 automated gates pass, and MUST preserve fallback to the current working app-launch passthrough if any P1 gate fails.
- **FR-008**: The system MUST record metadata-only evidence for lightweight idle behavior, automatic reactivation, no-hang behavior, CPU behavior, route recovery, and fallback decisions.
- **FR-009**: The system MUST recover safely after `coreaudiod` restart, sleep/wake, physical device changes, and stale browser device selections before showing ready.
- **FR-010**: The audio driver MUST NOT own meeting recording, transcription, upload, MediaScribe, Langfuse, analytics, or external network egress; those responsibilities belong to application software and remain outside this feature unless a later recording feature explicitly supersedes this boundary.
- **FR-011**: The system MUST distinguish idle-safe, starting, ready, stale, blocked, failed, and retry states in UI and diagnostics.
- **FR-012**: Diagnostics and validation artifacts MUST NOT contain raw audio, transcript text, meeting content, credentials, tokens, signed URLs, or passwords.
- **FR-013**: The validation pipeline MUST include a regression guard proving that low-resource behavior does not reintroduce the previous "works only after Run Check" failure.
- **FR-014**: The validation pipeline MUST include a regression guard proving that startup cannot leave Core Audio or the app stuck in an unbounded starting state.
- **FR-015**: The system MUST allow audio routing to function independently from recording state, so browser/meeting audio can work when recording is off and recording can later subscribe through application-controlled triggers.
- **FR-016**: The system MUST detect active virtual-device use from explicit client IO state, not from audio energy alone, so natural silence does not stop or downgrade an active route.
- **FR-017**: The system MUST prevent self-loop routing where 2brain Rec selects its own virtual microphone or speaker as the physical working input/output.
- **FR-018**: The system MUST model route truth as separate evidence planes: virtual device publication, explicit client IO/running state, app bridge heartbeat/readiness, physical working device validity, and recording trigger state.
- **FR-019**: The app MUST NOT perform physical Core Audio device setup, AudioUnit binding, or device enumeration through an unbounded UI/main-path operation; every such operation must be bounded, cancellable or isolated, and report blocked within 3 seconds.
- **FR-020**: HAL driver IO callbacks MUST remain realtime-safe: no file IO, logging, allocation, lock waits, blocking IPC, wall-clock calls, network calls, process launches, or UI work in callback paths.
- **FR-021**: The driver/app handoff MUST fail closed when app bridge health is missing or stale, and MUST NOT wait inside driver IO for app process health, diagnostics, permissions, or route orchestration.
- **FR-022**: Missing or stale app bridge heartbeat MUST downgrade live-route readiness and zero/drop audio safely, but MUST NOT imply that recording has started or that a visible virtual device is live-ready.
- **FR-023**: The default MVP behavior MUST keep installed 2brain Rec virtual devices visible and fail-closed; hiding/removing public virtual devices due to app heartbeat, app exit, or idle state is out of default scope unless a later gate explicitly accepts that behavior.
- **FR-024**: The system MUST reject 2brain Rec virtual devices as physical working devices and MUST mark other virtual, aggregate, or multi-output working-device configurations as unsupported/not release-ready unless explicit validation accepts them.
- **FR-025**: The system MUST maintain clean-room separation from Krisp: use only public documentation, installed-component observation, logs, strings, and behavior-level inference; do not copy proprietary code, assets, identifiers, UI text, protocols, or protected implementation details.
- **FR-026**: The validation pipeline MUST compare low-resource behavior against the accepted 005 app-launch baseline for audio usability, no-loopback, no-hang surfaces, CPU, recovery, and fallback.
- **FR-027**: If 2brain Rec Speaker is selected as system or app output and an active client stream exists, the route MUST deliver audio to a valid physical output whenever app bridge health is good; resource saving MUST NOT intentionally mute or drop that route.

### Key Entities *(include if feature involves data)*

- **Audio Resource State**: The current readiness/resource mode: idle-safe, starting, ready, stale, blocked, failed, or retrying.
- **Client Activity Evidence**: Metadata-only signal that a supported app is actively using one or both virtual devices, based on explicit IO/client state rather than audio energy alone.
- **Route Truth Planes**: Separate metadata-only facts for device publication, active client IO, app bridge heartbeat/readiness, physical working device validity, and recording trigger state.
- **Startup Attempt Evidence**: Metadata-only record of startup timing, outcome, blocker reason, and whether fallback preserved the working default.
- **Lightweight Idle Evidence**: Metadata-only proof that the virtual layer remained published while heavy physical passthrough or processing work was not sustained without an active stream.
- **Recording Trigger Boundary**: The explicit ownership boundary where application software, not the driver, decides whether audio flowing through the virtual layer should be recorded or sent into a later transcription pipeline.
- **Recovery Evidence**: Metadata-only proof for `coreaudiod` restart, sleep/wake, device-change, and stale-client transitions.

### Constitutional Requirements *(mandatory for 2brain Rec)*

- **Capture/Driver Impact**: This feature directly changes macOS driver/audio routing readiness, passthrough lifecycle, degraded states, and recovery. It must preserve driver-first MVP behavior, fail-closed audio, no-loopback gates, application-owned recording triggers, and measurable no-hang/CPU/recovery criteria.
- **Visible Control Impact**: This feature must not start recording or transcription. It may change readiness/status states, but the user must always see whether passthrough is idle-safe, starting, ready, stale, blocked, or failed.
- **Data Boundary Impact**: This feature is local-only. It must not add MediaScribe upload, Langfuse traces, LLM calls, analytics, server upload, storage, or external network egress.
- **Secrets Impact**: No credentials, tokens, signed URLs, passwords, or live credential paths may be stored in client state, diagnostics, logs, screenshots, or evidence artifacts.
- **Retention/Deletion Impact**: This feature must not create meeting-content artifacts, raw audio, transcripts, or server-side deletion obligations. Validation evidence is metadata-only.
- **Audit Impact**: The system must preserve auditability for lightweight idle behavior, automatic reactivation, startup timeout/blocking, stale/degraded transitions, fallback, and recovery.
- **UX/Brand/Accessibility Impact**: Any UI state changes must use original 2brain Rec language, be keyboard reachable, not rely on color alone, and remain brand-distinct from Krisp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With no active virtual-device stream, 2brain Rec remains in a lightweight idle state with virtual devices visible, fail-closed, and no sustained heavy physical passthrough or processing work.
- **SC-002**: From idle-safe state, a supported browser or meeting client can activate both microphone and speaker passthrough without pressing `Run Check`.
- **SC-003**: macOS Sound settings, Chrome, Opera, Zoom, and Telemost audio surfaces open within 5 seconds while low-resource mode is installed or record a blocked failure without hanging.
- **SC-004**: No startup attempt can leave the app UI or validation command blocked beyond 3 seconds.
- **SC-005**: During idle and no-call windows, `coreaudiod` does not sustain CPU above 10% for more than 30 consecutive seconds.
- **SC-006**: After `coreaudiod` restart, sleep/wake, or physical device change, ready UI is cleared within 5 seconds and restored only after valid route evidence.
- **SC-007**: Low-resource mode passes the same browser/meeting smoke matrix as the current working default: user is heard, user hears, no remote-to-mic loopback, and no hidden recording.
- **SC-008**: If all local P1 automated gates pass, low-resource mode becomes default; if any P1 gate fails, the current working app-launch passthrough remains the default and low-resource mode is marked blocked/not accepted.
- **SC-009**: Diagnostics redaction validation finds no raw audio, transcript text, credentials, tokens, signed URLs, passwords, or meeting content outside deliberate policy/fixture strings.
- **SC-010**: Audio routing works with recording off, and validation evidence shows that the driver did not create recordings, transcripts, uploads, or transcription jobs.
- **SC-011**: A silent-but-open browser/meeting stream remains classified as active, while a genuinely closed stream can return to lightweight idle.
- **SC-012**: Validation proves 2brain Rec refuses or repairs configurations where its physical working input/output is one of its own virtual devices.
- **SC-013**: Diagnostics for every readiness check include separate evidence for publication, client IO/running state, app bridge heartbeat/readiness, physical working device validity, and recording trigger state.
- **SC-014**: Realtime-safety validation finds no blocking operations, logging, allocation, file IO, wall-clock, IPC wait, process launch, network call, or UI dependency in HAL IO callbacks.
- **SC-015**: A simulated slow physical AudioUnit setup or Core Audio enumeration attempt resolves to ready, blocked, failed, or fallback within 3 seconds and never leaves UI, validation, browser, meeting, or system settings surfaces hanging.
- **SC-016**: Virtual devices remain visible and fail-closed by default across app idle, app exit, stale heartbeat, and Core Audio restart unless a later accepted feature explicitly changes public visibility behavior.
- **SC-017**: A local fallback switch can restore the accepted 005 app-launch route lifecycle without reinstalling the HAL driver.
- **SC-018**: Validation evidence explicitly records current implementation gaps before promotion, including synchronous app-side startup risk, physical Core Audio setup risk, heartbeat/publication policy conflicts, self-routing protection, and no-Run-Check regression coverage.

## Assumptions

- The current accepted baseline is the working app-launch non-recording passthrough from feature `005-macos-passthrough-release-hardening`.
- Low-resource mode may become the local default after automated P1 gates pass; longer manual acceptance can still add confidence but is not required for local default promotion.
- Local recording, transcription, upload, retention, deletion, server workflows, MediaScribe, and Langfuse remain out of scope.
- The target validation environment is Apple Silicon macOS with the local package installed in `/Applications`.
- Chrome, Opera, Zoom, macOS Sound settings, and Yandex Telemost remain the primary no-hang/browser-meeting validation surfaces.
