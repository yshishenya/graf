# Tasks: Safe macOS App Updates

**Input**: Design documents from `specs/105-macos-app-updates/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required by the high-risk validation lane. Write the focused test or contract first, confirm it fails for the missing behavior, then implement the corresponding task.

**Organization**: Tasks are grouped by user story so each user-visible slice remains independently testable. `tasks.md` is the implementation source of truth; GitHub issues mirror these tasks after analysis.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it changes different files and has no unmet dependency.
- **[Story]**: User story from `spec.md` (`US1`–`US4`).
- Every task names the exact repository paths it owns and its completion evidence.

## Phase 1: Setup (Pinned Updater Dependency)

**Purpose**: Add the one approved updater dependency without changing application behavior.

- [X] T001 Pin Sparkle `2.9.4` exactly in `apps/macos/Package.swift`, resolve `apps/macos/Package.resolved`, and prove `swift package resolve --package-path apps/macos` succeeds without adding another update or networking dependency.

---

## Phase 2: Foundational (Shared Trust, State, and Packaging)

**Purpose**: Establish the one updater state machine, capture gate, trusted configuration, and signed-bundle packaging contract that all user stories depend on.

**⚠️ CRITICAL**: No user-story implementation begins until these tasks pass focused tests.

- [X] T002 [P] Add failing-first unit coverage for trusted configuration, presentation derivation, overlapping checks, skipped/dismissed/withdrawn releases, stale-badge removal, and protected-work transitions in `apps/macos/Shared/Tests/AppUpdateControllerTests.swift`.
- [X] T003 Implement the `@MainActor` Sparkle-backed controller, fail-closed configuration preflight, single presentation state, gentle scheduled reminders, and one-shot relaunch deferral in `apps/macos/RecApp/Sources/Updates/AppUpdateController.swift` until T002 passes.
- [X] T004 [P] Add failing-first installer/update assertions to `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift`, then update `apps/macos/Installer/Scripts/build-local-installer.sh` to embed Sparkle, configure 86,400-second automatic checks with automatic install/download and profiling disabled only for complete trusted configuration, sign nested code before `GRAF.app`, and preserve `GRAF` / `pro.2brain.graf` identity.

**Checkpoint**: A local build either owns one configured, authenticated updater or truthfully disables updates; it never falls back to an unsigned path.

---

## Phase 3: User Story 1 — Safely Receive an Available Update (Priority: P1) 🎯 MVP

**Goal**: Discover and install a trustworthy stable update without interrupting capture, finalization, or permission identity.

**Independent Test**: From an older release-like build, discover a newer signed archive, defer installation during protected capture work, complete it afterward without a second catalog request, and verify the old app remains launchable after rejected fixtures.

- [X] T005 [US1] Add failing-first lifecycle coverage for active/paused capture, start/stop transitions, finalization, persistence, and termination cleanup in `apps/macos/Shared/Tests/AppUpdateControllerTests.swift`, then expose one derived protected-update-work signal from `apps/macos/RecApp/App/TwoBrainRecApp.swift` to `AppUpdateController`.
- [X] T006 [US1] Start and retain the updater from `AppLifecycleDelegate`, connect its presentation to the root SwiftUI environment, and release any postponed relaunch only after protected work becomes idle in `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [X] T007 [US1] Create `apps/macos/Scripts/validate-app-updates.sh` to fail closed on wrong bundle ID/name/version, absent embedded Sparkle code, incomplete trust keys, invalid nested signatures, architecture mismatch, downgrade/malformed appcast fixtures, or incompatible designated requirements; validate both configured and updater-disabled local builds.

**Checkpoint**: Scheduled discovery and an already-downloaded update cannot stop, pause, replace, quit, or relaunch GRAF while protected capture work exists.

---

## Phase 4: User Story 2 — Check for Updates Manually (Priority: P2)

**Goal**: Provide a standard, explicit manual update check with current, available, incompatible, unavailable, and retryable-failure outcomes.

**Independent Test**: Invoke `GRAF > Check for Updates…` against current, newer, offline, and updater-disabled fixtures while confirming capture state never changes.

- [X] T008 [US2] Add the standard `Check for Updates…` application-menu item, target/action wiring, keyboard and accessibility behavior, and truthful unavailable fallback in `apps/macos/RecApp/App/TwoBrainRecApp.swift`, with menu/controller assertions in `apps/macos/Shared/Tests/AppUpdateControllerTests.swift`.

**Checkpoint**: Manual checks always surface a result and share the same controller/capture gate as scheduled checks.

---

## Phase 5: User Story 3 — Notice the Update in the Left Sidebar (Priority: P3)

**Goal**: Show one accessible, low-noise update marker in connected-cabinet and local-only layouts and route it to the standard update offer.

**Independent Test**: Toggle trustworthy availability and verify the marker appears/disappears within the contract, is keyboard/VoiceOver reachable, is embedded-only on the web surface, and invokes the same native update action.

- [X] T009 [P] [US3] Add failing-first embedded-sidebar contracts in `apps/server/tests/unit/test_cabinet_template_sections.py` and `apps/server/tests/contract/test_cabinet_static_assets_contract.py`, then add the hidden embedded-only `data-graf-app-update` button to `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html` and its informational accessible styling to `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.
- [X] T010 [P] [US3] Add failing-first bridge coverage in `apps/macos/Shared/Tests/EmbeddedCabinetUpdateBridgeTests.swift`, then implement a fixed boolean show/hide script and the single `checkForUpdates` message action in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`.
- [X] T011 [US3] Thread update visibility/action through `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift` and `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`, including the native local-only marker, without displacing capture controls or exposing versions, URLs, or release data to the WebView.

**Checkpoint**: Connected and local-only modes derive the same badge from trustworthy native state and never render a stale or server-owned update signal.

---

## Phase 6: User Story 4 — Publish a Trustworthy Update (Priority: P4)

**Goal**: Produce a versioned signed `GRAF.app` archive and signed appcast through a repeatable fail-closed release helper while keeping secrets and publication outside implementation scope.

**Independent Test**: Prepare two strictly increasing same-identity builds, generate an archive/appcast with official Sparkle tools, accept the valid update, and reject corrupted, unsigned, wrong-key, downgrade, incompatible, and wrong-identity fixtures before publication.

- [X] T012 [US4] Add `apps/macos/Installer/Scripts/prepare-app-update.sh` to validate CalVer monotonicity, same-identity release inputs, HTTPS credential-free URLs, external Russian release notes, official Sparkle signing tools, exact archive length/signature, `arm64`, and macOS `14.5.0+`, writing only staged artifacts under `apps/macos/.build/updates/` and never publishing them.
- [X] T013 [P] [US4] Document bootstrap installation, external EdDSA key handling, Developer ID/nested signing, hardened runtime, notarization/stapling/Gatekeeper, staged appcast generation, rollback, two-update permission proof, and explicit publication approval in `apps/macos/Installer/README.md` and `qa/macos/release-candidate-checklist.md`.

**Checkpoint**: Release tooling creates inspectable staged artifacts only; it cannot mutate the public catalog or leak private signing material.

---

## Phase 7: Polish & Cross-Cutting Validation

**Purpose**: Close product documentation, traceability, privacy, accessibility, and repository-wide evidence.

- [X] T014 [P] Record updater behavior, bootstrap limitation, permission-identity contract, release-only activation gates, and no-privileged-audio-component scope in `CHANGELOG.md` and `docs/current-product-status.md`.
- [ ] T015 Execute `specs/105-macos-app-updates/quickstart.md` focused Swift/server/shell checks, inspect request/log fixtures for forbidden content, perform keyboard/VoiceOver review, and record only sanitized evidence in the relevant GitHub task issues; do not reset TCC or publish artifacts.
- [X] T016 Run `swift test --package-path apps/macos`, `apps/macos/Scripts/validate-app-updates.sh` for the built app, and `infra/scripts/ci-local.sh`; mark tasks complete only when all applicable gates pass and record any externally blocked Developer ID/notarization/two-update proof truthfully for release closeout.
- [ ] T017 [US1] Raise the default ScreenCaptureKit runtime start/stop deadlines to 120 seconds in `apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift`, update the source contract in `apps/macos/Shared/Tests/SystemAudioCaptureServiceTests.swift`, and prove from real installed-app evidence that a post-update start can exceed the former 60-second window and a stop completing near that boundary does not become a false `capture_failed` result before exercising the capture-deferred update smoke.
- [ ] T018 [US4] Add an opt-in production-provenance gate to `apps/macos/Installer/Scripts/prepare-app-update.sh`, cover it in `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift`, and document the clean remote-tagged commit, GitHub Release assets, archive/package-first, appcast-last, and public-checksum publication order in `apps/macos/Installer/README.md` and `qa/macos/release-candidate-checklist.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1** starts immediately.
- **Phase 2** depends on T001 and blocks all user stories.
- **US1 (Phase 3)** depends on T002–T004 and establishes the protected-work integration used by every trigger.
- **US2 (Phase 4)** depends on T003 and T006.
- **US3 (Phase 5)** depends on T003 and T006; T009 and T010 can run in parallel before T011.
- **US4 (Phase 6)** depends on T004 and T007 but can proceed independently of sidebar work.
- **Phase 7** depends on the intended user stories being complete; T015 precedes T016.

### User Story Dependencies

- **US1 (P1)**: Core MVP; independent after the foundation and required before final release validation.
- **US2 (P2)**: Reuses the controller and capture gate but is independently testable through the application menu.
- **US3 (P3)**: Reuses only the presentation/action boundary; connected and local-only renderers are independently contract-tested.
- **US4 (P4)**: Reuses the packaged app/trust validator and is independently testable against staged local artifacts; public publication remains out of scope.

### Within Each Story

- Add the focused test/contract first and observe the missing behavior fail.
- Implement the smallest native/Sparkle-backed change that makes it pass.
- Run the story’s independent test before moving to its checkpoint.
- Do not mark `[X]` until the named evidence exists.

## Parallel Opportunities

- T002 and T004 modify different test/packaging surfaces after T001.
- T009 and T010 are independent server and native bridge contracts.
- T013 and T014 are independent documentation surfaces after their implementation facts stabilize.
- No task may parallelize changes to `TwoBrainRecApp.swift`; T005, T006, and T008 remain ordered to avoid conflicting ownership.

## Parallel Example: User Story 3

```text
Task T009: server-rendered embedded sidebar slot and CSS contract
Task T010: native WKWebView boolean/action bridge contract
Then T011: connect both surfaces to the shared native update presentation
```

## Implementation Strategy

### MVP First

1. Complete T001–T004.
2. Complete T005–T007 for safe scheduled discovery and capture-aware installation.
3. Validate US1 independently before adding menu/sidebar presentation.

### Incremental Delivery

1. Foundation → trusted updater exists or fails closed.
2. US1 → safe scheduled update path.
3. US2 → explicit manual control.
4. US3 → persistent low-noise reminder.
5. US4 → staged release artifacts and operator contract.
6. Cross-cutting validation → repository CI and release-closeout handoff.

## Notes

- Selected lane: **high-risk Spec Kit feature** because this changes app replacement, signing identity, permissions, capture-adjacent relaunch, and public release trust.
- Sparkle owns download, validation, replacement, rollback, and standard update UI; GRAF owns only configuration preflight, capture deferral, and presentation bridging.
- No task authorizes commit, push, PR, tag, GitHub Release, production publication, deploy, Developer ID signing, notarization, or TCC mutation without the separately required approval.
