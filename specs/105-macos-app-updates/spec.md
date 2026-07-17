# Feature Specification: Safe macOS App Updates

**Feature Branch**: `105-macos-app-updates`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Implement a best-practice macOS application update system that preserves permissions, checks periodically, offers available updates, provides a Check for Updates menu item, and shows an availability badge in the left sidebar."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Safely Receive an Available Update (Priority: P1)

As a GRAF user, I want the application to notice a newer stable release and offer it without interrupting recording, so I can stay current without losing capture permissions or a meeting in progress.

**Why this priority**: A trustworthy discovery and installation path is the core user value. Any update path that interrupts capture, accepts an untrusted build, or causes macOS to treat GRAF as a different application is worse than no updater.

**Independent Test**: Publish a newer compatible release to a controlled update source, launch an older release-like build with previously granted microphone and Screen/System Audio permissions, and verify that GRAF offers and installs the update while preserving those permissions and the ability to record.

**Acceptance Scenarios**:

1. **Given** a supported Mac is online, no capture is active, and a newer stable release is available, **When** the periodic check becomes due, **Then** GRAF offers the update with its version and release notes without installing it silently.
2. **Given** a capture session is active or changing state, **When** a periodic check finds a newer release, **Then** GRAF records that the update is available but does not present an interrupting installation flow, quit, relaunch, pause, or stop capture.
3. **Given** an update was deferred during capture, **When** capture has ended and finalization is complete, **Then** GRAF offers the deferred update without requiring another network check.
4. **Given** the installed app already has microphone and Screen/System Audio permissions, **When** a valid update replaces it, **Then** macOS continues to recognize the updated build as the same GRAF application and does not request those permissions again.
5. **Given** an update archive, release description, or source cannot be trusted or validated, **When** installation is attempted, **Then** GRAF leaves the currently installed version intact and reports a safe, actionable failure.

---

### User Story 2 - Check for Updates Manually (Priority: P2)

As a GRAF user, I want a standard “Check for Updates…” command in the application menu so I can ask for the latest version at any time and receive an explicit result.

**Why this priority**: Manual checking provides control, supportability, and a recovery path when the periodic schedule has not yet run.

**Independent Test**: Invoke “Check for Updates…” once with no newer release and once with a newer release, then verify that both checks return a clear result and that an active recording is never interrupted.

**Acceptance Scenarios**:

1. **Given** GRAF is running, **When** the user chooses “Check for Updates…”, **Then** the application performs a user-initiated check and visibly reports whether an update is available, the app is current, or the check failed.
2. **Given** a recording is active, **When** the user chooses “Check for Updates…”, **Then** the application may report availability but makes clear that installation is deferred until recording and finalization finish.
3. **Given** the network is unavailable, **When** the user manually checks, **Then** GRAF reports a concise retryable error without changing capture or local recording state.

---

### User Story 3 - Notice the Update in the Left Sidebar (Priority: P3)

As a GRAF user, I want a small, accessible update marker in the left sidebar when a newer version is known, so I can notice it later without being repeatedly interrupted.

**Why this priority**: A persistent, low-noise reminder complements the initial offer and lets users defer safely.

**Independent Test**: Drive the update state from current to available and back to current, then verify the left-sidebar marker, its accessible description, and its action follow the state in both connected-cabinet and local-only modes.

**Acceptance Scenarios**:

1. **Given** a newer stable release is known, **When** the main window is visible, **Then** the left sidebar shows a visually distinct but non-alarming update marker with an accessible label.
2. **Given** the user activates the marker, **When** no capture is active, **Then** GRAF opens the same update offer used by the application menu.
3. **Given** the user activates the marker during capture, **When** the update offer opens, **Then** installation remains unavailable until capture and finalization finish.
4. **Given** GRAF is current or no trustworthy availability result exists, **When** the sidebar is rendered, **Then** no stale update marker is shown.

---

### User Story 4 - Publish a Trustworthy Update (Priority: P4)

As a release operator, I want one repeatable release path for signed application updates, release notes, and the update catalog so users are offered only authentic, compatible GRAF builds.

**Why this priority**: The client experience cannot be secure or reliable unless release artifacts are produced and validated consistently.

**Independent Test**: Produce two sequential release-like builds, publish the second through the documented update path, and prove the older build accepts the valid update while rejecting corrupted, downgraded, wrong-identity, and unsigned variants.

**Acceptance Scenarios**:

1. **Given** a release candidate has passed application and installer validation, **When** the operator prepares an update, **Then** the published catalog contains the release version, compatibility limits, release notes, artifact size, download location, and cryptographic proof.
2. **Given** the update is intended for public distribution, **When** it is published, **Then** the application bundle and all nested executable code satisfy the project’s signing, hardened-runtime, notarization, and trust checks.
3. **Given** a release artifact would change GRAF’s application identity or install an unsupported build, **When** release validation runs, **Then** publication stops before the catalog or public download is updated.

### Edge Cases

- The application starts offline, the update source times out, returns an invalid response, or becomes reachable later.
- A periodic check and a manual check are requested at nearly the same time.
- A newer release is discovered immediately before recording starts.
- Capture stops but recording finalization, local persistence, or termination cleanup is still in progress.
- The update downloads successfully but validation, extraction, replacement, or relaunch fails.
- The update is older than the installed build, targets an unsupported macOS version or architecture, or has a malformed version.
- The user defers or skips a release, then manually checks again.
- The update source reports no newer release after a previously available update was withdrawn.
- The application is running from a read-only, translocated, or otherwise non-updatable location.
- The connected cabinet is unavailable and GRAF is operating in local-only mode.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: GRAF MUST support one stable macOS update channel for the initial release of this feature.
- **FR-002**: GRAF MUST check for updates after launch when at least 24 hours have elapsed since the last completed scheduled check and MUST continue using the same interval while the app remains open.
- **FR-003**: Scheduled checks MUST NOT wake or launch GRAF while the application is closed.
- **FR-004**: Scheduled checks MUST be non-blocking and MUST NOT prevent the main window, local recording, recording stop, finalization, or upload recovery from working.
- **FR-005**: When a scheduled check discovers a newer compatible release and capture is idle, GRAF MUST offer the update with the release version, release notes, and clear choices to install or defer.
- **FR-006**: GRAF MUST NOT silently install an update; installation requires an explicit user choice.
- **FR-007**: GRAF MUST provide a standard “Check for Updates…” command in the GRAF application menu.
- **FR-008**: A manual check MUST visibly distinguish update available, already current, incompatible release, and retryable check failure outcomes.
- **FR-009**: GRAF MUST maintain a single coherent update state when scheduled, manual, sidebar, and already-running checks overlap.
- **FR-010**: GRAF MUST NOT begin application replacement, quit, relaunch, pause, or stop recording while capture is active, capture is transitioning, recording finalization is incomplete, or termination cleanup is pending.
- **FR-011**: An update discovered during protected capture work MUST remain available locally and be offered after the protected work completes without requiring another network check.
- **FR-012**: When a trustworthy newer release is known, GRAF MUST show a compact update marker in the left sidebar in connected-cabinet and local-only modes.
- **FR-013**: The update marker MUST expose an accessible label, keyboard-reachable action, hover/help text, and sufficient contrast without competing with recording controls.
- **FR-014**: Activating the update marker MUST open the same update offer as the application menu and MUST preserve all active-capture deferral rules.
- **FR-015**: GRAF MUST remove a stale update marker when the installed version becomes current, the published release is withdrawn, or the prior availability result is no longer trustworthy.
- **FR-016**: Updates MUST use HTTPS and independent cryptographic authenticity and integrity verification before executable content is installed.
- **FR-017**: GRAF MUST reject corrupted, unsigned, wrong-key, wrong-application-identity, downgraded, malformed, incompatible, or otherwise untrusted updates before replacing the installed application.
- **FR-018**: A failed update MUST leave the previously installed GRAF version launchable or restore it truthfully before reporting failure.
- **FR-019**: Every update MUST preserve the established application name, bundle identifier `pro.2brain.graf`, install location, signing lineage, designated requirement, permission usage descriptions, and supported architecture unless a separately approved migration explicitly supersedes them.
- **FR-020**: Release validation MUST prove that microphone and Screen/System Audio permissions remain granted across two sequential same-identity release-like updates on the validation Mac without resetting or editing the macOS privacy database.
- **FR-021**: Public update publication MUST require release-like application signing, hardened runtime, valid nested-code signatures, notarization, stapling where applicable, and Gatekeeper assessment before the update catalog is changed.
- **FR-022**: The update catalog MUST declare the machine-readable release version, user-visible version, minimum supported macOS version, Apple Silicon requirement, publication date, release notes, artifact URL, artifact length, and cryptographic proof.
- **FR-023**: Release tooling MUST stop before publication when versions are not strictly increasing or identity, signing, compatibility, archive, catalog, or trust validation fails.
- **FR-024**: Automatic update checks MUST NOT transmit raw audio, transcript text, meeting metadata, credentials, tokens, account identifiers, or a hardware/software profile beyond ordinary request metadata needed to retrieve the catalog.
- **FR-025**: Update diagnostics and logs MUST be metadata-only, bounded, and free of private release keys, signed URLs, raw update payloads, meeting content, and user identifiers.
- **FR-026**: Initial installation MUST remain available through the existing app-only installer, and normal install, update, rollback, repair, and uninstall paths MUST NOT add, revive, or mutate privileged audio components or Core Audio services.
- **FR-027**: GRAF builds without complete trusted update configuration MUST keep update installation disabled and present a truthful unavailable state instead of attempting an insecure fallback.
- **FR-028**: The first updater-enabled GRAF release MUST document that previously installed versions without this feature require one final manual installation before future in-app updates become available.

### Key Entities

- **Update State**: The current client-visible lifecycle state, including unavailable, idle, checking, current, available, deferred for capture, downloading, ready to install, installing, and failed.
- **Update Release**: A published stable release with version, compatibility, notes, artifact metadata, and trust proof.
- **Protected Capture Work**: Any active or transitioning capture, recording finalization, local persistence, or termination cleanup that prevents application replacement.
- **Update Marker**: The compact left-sidebar indicator derived from a trustworthy available or deferred update state.
- **Release Trust Identity**: The stable application and signing characteristics that macOS and the updater use to recognize authentic GRAF versions as the same application.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a connected supported Mac, a scheduled check exposes a newly published stable update within 24 hours without delaying application launch by more than 200 milliseconds.
- **SC-002**: Under nominal connectivity, 95% of manual update checks produce an available, current, incompatible, or retryable-error result within 10 seconds.
- **SC-003**: In validation, 100% of active-recording scenarios continue recording and retain one-action stop while an update is discovered, deferred, downloaded, or requested for installation.
- **SC-004**: After protected capture work finishes, a deferred update offer becomes available within 60 seconds without another catalog request.
- **SC-005**: The left-sidebar marker appears within 5 seconds of a trustworthy available result and disappears within 5 seconds after GRAF becomes current or the result is withdrawn.
- **SC-006**: Two sequential same-identity release-like updates preserve microphone and Screen/System Audio authorization on the validation Mac with zero privacy-database resets and zero permission re-prompts.
- **SC-007**: Corrupted, unsigned, wrong-key, wrong-identity, incompatible, and downgrade fixtures are rejected in every validation run, and the previously installed version remains launchable.
- **SC-008**: Every public update candidate passes bundle identity, nested signature, hardened runtime, notarization, Gatekeeper, catalog, artifact integrity, clean install, in-place update, rollback, and relaunch gates before publication.
- **SC-009**: Automated privacy checks find zero raw audio, transcript text, meeting metadata, credentials, tokens, private update keys, or user identifiers in update requests, logs, diagnostics, catalogs, and committed evidence.
- **SC-010**: Keyboard-only and VoiceOver checks can discover and invoke both “Check for Updates…” and the left-sidebar update marker without obscuring or displacing capture controls.

## Assumptions

- Stable releases are the only channel in scope; beta channels, mandatory updates, enterprise fleet rollout, and staged/phased rollout controls are deferred until there is a demonstrated need.
- Scheduled checking is enabled by default once per 24 hours, while automatic background download and silent installation remain disabled.
- The update source is publicly reachable over HTTPS and does not require embedding credentials or signed private URLs in the desktop app.
- The existing `GRAF.app` identity and app-only initial installer remain authoritative.
- Public release readiness depends on Apple Developer signing and notarization credentials that remain outside the repository and local evidence.
- The first release containing the updater is a bootstrap release: older builds cannot gain self-update capability until that release is installed manually once.
- Exact wording and placement of the sidebar marker follow the existing GRAF desktop design system and remain visually subordinate to recording state and one-action stop.
