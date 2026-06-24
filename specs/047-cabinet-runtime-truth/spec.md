# Feature Specification: Cabinet Runtime Truth

**Feature Branch**: `047-cabinet-runtime-truth`

**Created**: 2026-06-24

**Status**: Draft

**Input**: User description: "After a server restart the macOS app looked like everything was OK, then later said I was not logged into the cabinet; pressing login showed the server was down. This must not happen. Make the app and web cabinet truthful, recheck both surfaces carefully, and preserve MVP readiness."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See Honest Cabinet Health In The Desktop Shell (Priority: P1)

As a meeting owner using the macOS app, I want the native shell to distinguish "cabinet configured" from "cabinet actually reachable and authenticated" so that I do not trust a stale green status when the server is down or still being checked.

**Why this priority**: A false "OK" state breaks trust in the MVP more than a visible temporary outage. The app can keep recording locally, but it must not imply the server/cabinet is healthy without runtime proof.

**Independent Test**: Start the macOS cabinet workspace with a configured cabinet and simulate loading, ready, offline, timeout, and expired-session states. The shell may show success only after a ready meeting route; loading is neutral, offline/timeout is unavailable, and expired session asks for login without claiming server health.

**Acceptance Scenarios**:

1. **Given** the cabinet base URL is configured, **When** the embedded cabinet is still loading, **Then** the native shell says the cabinet is being checked and shows no green success indicator.
2. **Given** the embedded cabinet hits a network failure, timeout, or 5xx response, **When** the shell updates, **Then** it shows that the server is unavailable while local recording remains available.
3. **Given** the embedded cabinet reaches an authenticated meeting list or detail route, **When** loading completes, **Then** the shell may show the cabinet as available.

---

### User Story 2 - Treat Login Pages As Auth Required, Not Ready (Priority: P1)

As a meeting owner whose session expired, I want a loaded login page to be presented as "needs login" rather than "cabinet ready" so that I know the next action and do not confuse auth failure with a working review state.

**Why this priority**: Login routes can return successful HTTP responses. If the desktop shell treats any successful page load as ready, the app can show exactly the false state reported by the user.

**Independent Test**: Classify finished embedded cabinet routes by route kind. Meeting list and detail routes become ready; login and sign-up routes become expired-session/auth-required; blocked or unsupported routes do not become ready.

**Acceptance Scenarios**:

1. **Given** the session is expired and the server returns the login page, **When** the embedded page finishes loading, **Then** the desktop cabinet state is "needs login" rather than "ready".
2. **Given** the server is unavailable while the user tries to log in, **When** navigation fails, **Then** the app shows server unavailable rather than a normal logged-out state.
3. **Given** an unsupported embedded route finishes or is blocked by policy, **When** the shell updates, **Then** it does not show a green cabinet-ready state.

---

### User Story 3 - Recheck Web Cabinet And Desktop Embedded Parity (Priority: P1)

As the product owner, I want the web cabinet and the embedded desktop cabinet to show the same safe meeting review truth so that the MVP does not contradict itself across surfaces.

**Why this priority**: The desktop app embeds server-owned review. The MVP is not credible if the web route and embedded route disagree on login, unavailable, processing, ready, playback, or transcript states.

**Independent Test**: Run fixture-backed web cabinet checks and desktop embedded route checks for ready, processing, failed, unavailable, and auth-required states. Compare visible state labels, blocked/unavailable copy, transcript/playback availability, and overflow/accessibility basics.

**Acceptance Scenarios**:

1. **Given** the same authorized processed meeting is opened in web and desktop embedded review, **When** both pages render, **Then** status, transcript availability, diarization availability, and playback availability match.
2. **Given** the cabinet is unavailable or auth is required, **When** the desktop app renders its shell and embedded area, **Then** the native shell and embedded state agree on the problem.
3. **Given** a mobile-width or desktop-width cabinet view, **When** the page renders, **Then** status text does not overlap or overflow and does not expose private data.

---

### User Story 4 - Preserve Local Recording Safety During Cabinet Failures (Priority: P1)

As a meeting owner, I want local Record/Stop and upload-truth controls to remain visible and truthful when the cabinet is unavailable so that an outage does not hide capture controls or imply a lost recording.

**Why this priority**: Cabinet availability is not the same as local capture safety. During server downtime, the app must clearly keep local recording and queued upload truth separate from review availability.

**Independent Test**: For every cabinet state, verify the native shell still satisfies the active-recording invariant: visible record state, visible stop path, upload truth, and no focus trap in the embedded web surface.

**Acceptance Scenarios**:

1. **Given** an active recording and the cabinet becomes unavailable, **When** the shell updates, **Then** Stop remains one action away.
2. **Given** uploads are queued while the server is unavailable, **When** the user opens the app, **Then** upload/local state remains visible separately from cabinet status.
3. **Given** the cabinet is not configured, **When** the app opens, **Then** local recording mode remains available without pretending the server is healthy.

### Edge Cases

- Server restarts while the embedded cabinet was previously ready.
- Server returns `401`, `403`, `404`, `5xx`, timeout, or a successful login page.
- WebKit cancels navigation because the app reloads a request with desktop headers.
- User clicks a login link while the server is actually down.
- Desktop app is launched from a packaged default cabinet URL with no user-specific auth headers.
- Web cabinet fixture shows ready playback/transcript while the desktop shell has not yet confirmed runtime readiness.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The desktop shell MUST NOT use cabinet configuration alone as proof that the server, session, or cabinet review surface is healthy.
- **FR-002**: The desktop shell MUST show neutral "checking" state until a runtime cabinet navigation result proves a healthier or failed state.
- **FR-003**: The desktop shell MUST show server-unavailable truth for network failures, timeouts, and server-side unavailable responses, while preserving local recording availability.
- **FR-004**: The desktop shell MUST show auth-required truth for login and sign-up routes, even when those routes load successfully.
- **FR-005**: The desktop shell MUST show green/success cabinet status only after an allowed authenticated meeting list or meeting detail route finishes successfully.
- **FR-006**: The embedded cabinet and native shell MUST share the same cabinet runtime state source so a navigation failure can update shell copy, icon, and tone.
- **FR-007**: The desktop app MUST preserve visible native Record/Stop/upload-truth controls for every cabinet runtime state.
- **FR-008**: Web cabinet and desktop embedded review MUST remain parity-checked for ready, processing, failed, unavailable, and auth-required states.
- **FR-009**: Status, diagnostics, browser evidence, logs, and committed evidence MUST remain metadata-only and must not include raw audio, transcript text, credentials, signed URLs, private local paths, or private meeting content.
- **FR-010**: Release notes and user-facing change descriptions for this slice MUST be simple Russian and must not mix languages.

### Key Entities

- **Cabinet Configuration**: The locally known base URL and desktop metadata headers. It proves only that the app knows where to load the cabinet.
- **Cabinet Runtime State**: The current user-safe state of the embedded cabinet: not configured, loading, ready, offline, timeout, expired session, denied, not found, malformed, or blocked route.
- **Native Shell Status Presentation**: The copy, icon, and tone shown in the macOS native shell for the current cabinet runtime state.
- **Review Surface Parity Case**: A web or embedded desktop route state used to compare visible cabinet truth across browser and desktop contexts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of tested configured-but-loading cabinet cases show a neutral checking state and no green success indicator.
- **SC-002**: 100% of tested offline, timeout, and server-error cabinet cases show server-unavailable shell truth while local recording controls remain available.
- **SC-003**: 100% of tested login and sign-up finished routes map to auth-required state, not ready.
- **SC-004**: 100% of tested ready states require successful meeting list or meeting detail route classification.
- **SC-005**: Focused macOS cabinet tests and full macOS package tests pass with the new runtime state model.
- **SC-006**: Web cabinet runtime checks cover desktop and embedded routes for ready and unavailable states with no visible overflow and no private evidence.
- **SC-007**: Production health checks after implementation report current server availability truth separately from desktop shell runtime truth.

## Assumptions

- This slice hardens cabinet state truth and MVP surface verification; it does not change recording capture, upload eligibility, MediaScribe processing, playback mixing, or AEC/noise suppression.
- The existing server-owned cabinet remains the source of meeting review content.
- The desktop app may keep local recording available during server downtime.
- If the server is down, the product should say so plainly rather than converting the situation into a normal logged-out state.
