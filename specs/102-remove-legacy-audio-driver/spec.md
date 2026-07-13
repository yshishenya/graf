# Feature Specification: Remove Legacy Separate Audio Driver

**Feature Branch**: `102-remove-legacy-audio-driver`

**Created**: 2026-07-13

**Status**: Locally validated; pending commit and PR review

**Input**: User description: "Полностью и очень аккуратно вычистить из кода всё, что связано с отдельным audio driver: продукт уже перешёл на другой путь, а driver стал legacy."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ship Only The System-Audio-First Product (Priority: P1)

As a GRAF user, I need the macOS app and installer to contain only the accepted
system-audio-first capture path so that setup and recording do not expose,
install, start, repair, or depend on obsolete virtual audio devices.

**Why this priority**: The separate driver is no longer part of the product
architecture. Leaving executable or installable remnants creates misleading
setup states and can reintroduce the Core Audio failures that caused the pivot.

**Independent Test**: Build the desktop app and default installer from a clean
checkout, inspect their contents, launch the app, and confirm there is no driver
bundle, virtual-device setup, driver repair action, shared bridge startup, or
driver-dependent readiness state.

**Acceptance Scenarios**:

1. **Given** a clean checkout, **When** the macOS app and installer are built,
   **Then** no separate audio-driver component or virtual-device payload is
   produced or packaged.
2. **Given** the app launches normally, **When** the user opens capture and
   settings surfaces, **Then** no driver install, repair, virtual-device, or
   passthrough controls are shown or started.
3. **Given** the obsolete driver is absent, **When** the user starts a normal
   recording, **Then** capture readiness does not depend on a driver, shared
   audio bridge, or virtual-device state.

---

### User Story 2 - Preserve Accepted Recording Truth (Priority: P1)

As a GRAF user, I need manual system-audio-first recording to keep working after
legacy removal so that microphone and incoming audio, visible capture state,
one-action stop, and the accepted local recording package remain unchanged.

**Why this priority**: Deleting legacy code is acceptable only if it cannot
damage the product's current capture path or make recording evidence less
truthful.

**Independent Test**: Run the accepted system-audio-first permission, capture,
artifact, stop, and diagnostic checks with the legacy driver surface absent.

**Acceptance Scenarios**:

1. **Given** microphone and screen/system-audio permissions are granted,
   **When** the user records a controlled session, **Then** the accepted
   microphone, incoming-audio, and manifest artifacts are produced without a
   virtual device.
2. **Given** recording is active, **When** the user views local controls,
   **Then** capture remains visibly active and can be stopped in one action.
3. **Given** a required permission or capture source is unavailable, **When**
   recording is requested, **Then** the existing blocked or degraded truth is
   preserved without suggesting driver repair.
4. **Given** old driver-specific routing state is gone, **When** current
   recording eligibility is evaluated, **Then** only current system-audio-first
   prerequisites can block or allow recording.

---

### User Story 3 - Leave No Active Legacy Maintenance Surface (Priority: P1)

As a maintainer, I need obsolete driver code, bridge code, build hooks, installer
branches, runtime orchestration, product models, tests, and active documentation
removed or reconciled so that future work cannot accidentally maintain or
revive two competing audio architectures.

**Why this priority**: Partial deletion leaves dead dependencies, stale CI
commands, misleading diagnostics, and compatibility branches that continue to
cost review and can silently affect runtime behavior.

**Independent Test**: Run a repository-wide retirement inventory with an
explicit allowlist limited to historical evidence and negative architecture
guards; every non-allowlisted driver reference must be absent or justified as a
current system-audio-first concept.

**Acceptance Scenarios**:

1. **Given** the feature is complete, **When** source, build, packaging,
   runtime, test, and active-documentation surfaces are searched, **Then** no
   executable legacy driver path remains.
2. **Given** a test or validator existed only for the old driver path, **When**
   the test suite is reviewed, **Then** that artifact is removed rather than
   kept as an un-runnable check.
3. **Given** a current safety check still protects the system-audio-first path,
   **When** legacy files are removed, **Then** the safety intent is retained in
   a smaller architecture guard rather than deleted with the legacy code.
4. **Given** active product documentation previously said the driver was
   parked, **When** the feature closes, **Then** it truthfully says the legacy
   implementation was removed and any future advanced routing must start as a
   new approved design.

---

### User Story 4 - Handle Existing Local Proof Installations Safely (Priority: P2)

As an operator or developer who previously installed a proof driver, I need a
truthful cleanup path so that source removal is not confused with removal of an
already installed system component.

**Why this priority**: Repository cleanup does not automatically change an
existing Mac. Silent assumptions here could leave stale virtual devices loaded
even though new builds no longer contain them.

**Independent Test**: Inspect a machine with and without known legacy proof
components and confirm the feature reports the distinction, supplies a bounded
cleanup instruction where needed, and does not perform unapproved privileged
system mutation during normal build or validation.

**Acceptance Scenarios**:

1. **Given** no legacy proof component is installed, **When** the new app or
   installer is used, **Then** no driver cleanup action is attempted or shown.
2. **Given** a known local proof component remains installed, **When** cleanup
   guidance is followed deliberately, **Then** only the known legacy component
   is removed and current app data is preserved.
3. **Given** automated validation runs, **When** it inspects local state,
   **Then** it does not install, remove, or restart privileged audio services
   without explicit approval.

### Edge Cases

- Current code uses generic Core Audio APIs for microphone selection or meeting
  detection even though it does not use the separate driver.
- A type contains both obsolete driver fields and current system-audio capture
  fields.
- Old local recording or diagnostic data contains driver-era fields that are no
  longer written.
- A test name mentions a driver but actually protects the current no-driver
  architecture.
- Installer scripts serve both the current app package and the obsolete driver
  package.
- A developer Mac still has one of several historical proof bundle names
  installed.
- Historical Spec Kit artifacts link to code paths that are intentionally
  removed by this feature.
- Generated build output or ignored local files contain driver names but are not
  repository source.
- A repository-wide search finds unrelated uses of the word "driver" such as
  browser, database, or device drivers.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The repository MUST remove the separate macOS audio-driver source
  tree and all production or proof build targets that compile it.
- **FR-002**: The macOS package graph MUST remove shared-memory and bridge-only
  targets, dependencies, and source files that exist solely for the separate
  driver.
- **FR-003**: The desktop app MUST NOT create, open, monitor, or write a local
  driver audio bridge after this feature.
- **FR-004**: The desktop app MUST NOT start or maintain a legacy passthrough or
  virtual-device route engine after this feature.
- **FR-005**: User-facing app surfaces MUST NOT show driver installation,
  repair, virtual-device, or legacy passthrough states or actions.
- **FR-006**: Default and optional installer flows MUST NOT build, package,
  install, update, repair, roll back, or advertise a separate audio-driver
  component.
- **FR-007**: Driver-only validation scripts, proof probes, fixtures, QA gates,
  and tests MUST be removed from active execution surfaces.
- **FR-008**: Safety checks that prove normal recording has no driver dependency
  MUST remain as a small negative architecture guard with an explicit historical
  reference allowlist.
- **FR-009**: The accepted native microphone and screen/system-audio capture
  path MUST remain buildable and behaviorally unchanged.
- **FR-010**: Manual start and stop, persistent visible capture state,
  one-action stop, permission truth, dual-track artifact truth, and
  metadata-only diagnostics MUST remain intact.
- **FR-011**: Recording eligibility MUST NOT depend on obsolete driver,
  virtual-device, shared-memory, or passthrough state.
- **FR-012**: Generic Core Audio usage that serves current microphone capture,
  device selection, or metadata-only meeting detection MUST NOT be removed only
  because it shares terminology with the legacy driver.
- **FR-013**: Active product, architecture, setup, and validation documentation
  MUST describe the legacy driver implementation as removed, not parked or
  available.
- **FR-014**: Historical specs and negative evidence MUST remain available for
  audit unless a link or statement incorrectly presents them as current
  executable guidance.
- **FR-015**: Any future advanced-routing implementation MUST require a new
  approved Spec Kit slice and MUST NOT be represented as recoverable by toggling
  the removed legacy code back on.
- **FR-016**: Existing local proof installations MUST be distinguished from
  repository source state; privileged cleanup MUST be deliberate, narrowly
  scoped, and never run as a side effect of build or test commands.
- **FR-017**: The change MUST introduce no new runtime dependency or replacement
  abstraction for the deleted driver path.
- **FR-018**: The feature MUST update the unreleased changelog and the active
  architecture finding that previously classified the driver surface as
  intentionally parked.
- **FR-019**: Validation artifacts MUST remain metadata-only and MUST NOT contain
  raw audio, transcript text, meeting content, credentials, tokens, signed URLs,
  passwords, or live user paths.
- **FR-020**: Removal MUST be dependency-driven: a file or symbol that still has
  a current non-driver caller may be changed or retained only after that caller
  and its current product role are explicitly classified.
- **FR-021**: Previously saved current recording manifests containing a retired
  capture failure value MUST remain readable and fail closed, while new
  manifests MUST NOT emit the retired value.

### Key Entities

- **Legacy Driver Surface**: The source, bridge, route orchestration, packaging,
  UI, model, diagnostics, test, and documentation paths that exist only for the
  separate virtual audio driver.
- **Current Capture Surface**: The native microphone and screen/system-audio
  implementation, recording controls, local artifact writer, and truthful
  diagnostics that remain supported.
- **Historical Evidence**: Prior specs, ADR context, proof reports, and failure
  records retained for audit but excluded from current build and execution.
- **Retirement Allowlist**: The small reviewed set of historical or negative
  guard references permitted to name the removed architecture after cleanup.
- **Local Proof Installation**: A previously installed system component that is
  outside git and therefore requires a deliberate separate cleanup action.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Clean builds produce zero separate audio-driver bundles, packages,
  shared-memory bridge targets, or virtual-device proof executables.
- **SC-002**: App launch and normal capture execute zero legacy driver,
  passthrough-engine, shared-memory, install, repair, or virtual-device paths.
- **SC-003**: The reviewed retirement inventory has zero unexplained active
  references after applying its historical/negative-guard allowlist.
- **SC-004**: One hundred percent of accepted system-audio-first focused tests,
  package tests, architecture guards, and repository local CI pass after
  removal.
- **SC-005**: The default installer contains one current desktop application
  component and zero separate audio-driver components or choices.
- **SC-006**: Existing manual recording, permission, visible-state, stop,
  dual-track artifact, and diagnostic acceptance scenarios show no regression.
- **SC-007**: The final repository diff deletes more executable legacy code than
  it adds and introduces zero new production dependencies.
- **SC-008**: Active product and architecture sources contain zero statements
  that present the removed legacy driver as a current parked implementation.
- **SC-009**: Build and test commands perform zero unapproved installs,
  uninstalls, privileged file changes, or Core Audio service restarts.

## Assumptions

- The separate audio driver was never accepted as part of the production MVP;
  current production recording uses native system-audio-first capture.
- Historical Spec Kit artifacts and negative failure evidence are audit history,
  not executable product surface, and should not be deleted wholesale.
- Generic Core Audio device and ownership observation used by current capture or
  meeting detection is not the separate driver and remains in scope to keep.
- Previously installed proof components may exist on developer machines even
  after their source is removed; this feature documents and validates a
  deliberate cleanup path but does not mutate the host during normal tests.
- Backward-read compatibility for any persisted driver-era metadata is retained
  only if repository evidence proves current supported data depends on it.
- No production deployment or privileged local uninstall is authorized by this
  implementation request.

## Out Of Scope

- Designing a replacement virtual-device or advanced-routing architecture.
- Rewriting current system-audio-first capture, microphone capture, meeting
  detection, recording storage, upload, transcription, or server behavior.
- Deleting historical specs or negative evidence solely because their source
  paths no longer exist.
- Installing or removing system components on the current Mac without a
  separate explicit action.
- Production deployment, release publication, or remote fleet mutation.
