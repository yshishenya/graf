# Research: Cabinet Runtime Truth

## Decision 1: Configuration Is Not Health

**Decision**: Treat `DesktopCabinetConfiguration` as static routing metadata
only. It may select cabinet mode, but it must not drive green/success health UI.

**Rationale**: The user-reported failure happened because a configured cabinet
URL was presented like a healthy server/session. A URL can remain configured
while the server is restarting, the session is expired, or the login page is the
only reachable page.

**Alternatives considered**:

- Keep configuration-driven copy but soften labels: rejected because it still
  leaves icons/color disconnected from runtime truth.
- Add a separate background health poller: deferred because the embedded
  navigation already produces the failure/auth signals needed for this slice.

## Decision 2: Share Embedded Runtime State With The Native Shell

**Decision**: Let `DesktopCabinetWorkspaceView` accept an optional
`Binding<DesktopCabinetState>`. When present, WebKit navigation outcomes update
the shared state used by the native shell.

**Rationale**: The shell and embedded cabinet should not infer state
independently. A single state source prevents the shell from showing green while
the embedded view has already learned that the server is offline or auth is
required.

**Alternatives considered**:

- Keep state private inside the workspace view: rejected because the native
  shell cannot react to runtime failures.
- Add a global observable service: rejected as unnecessary for one local view
  hierarchy and higher risk for a small hardening slice.

## Decision 3: Route Kind Determines Successful Finished State

**Decision**: A successfully loaded meeting list or meeting detail route maps to
`ready`. A successfully loaded login or sign-up route maps to `expiredSession`.
Unsupported or blocked route kinds do not map to ready.

**Rationale**: HTTP success alone is not enough. A login page can return `200`
while proving that the owner is not in the review surface.

**Alternatives considered**:

- Use HTTP status only: rejected because redirects/login pages can be successful
  HTTP responses.
- Parse page body for login markers: rejected because route policy already has
  a safer, content-free route classification.

## Decision 4: Verify Web Cabinet Without Capturing Private Content

**Decision**: Use fixture-backed server tests and browser/runtime checks that
record only metadata-safe facts: status class, visible state labels, overflow
count, and availability booleans.

**Rationale**: MVP evidence must prove user-visible parity without committing
meeting content, transcript text, audio, screenshots with private data, or
signed URLs.

**Alternatives considered**:

- Use real private meeting screenshots: rejected by privacy and evidence rules.
- Skip web checks because code is macOS-only: rejected because the user asked to
  recheck both the app and web cabinet.
