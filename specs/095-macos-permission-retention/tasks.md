# Tasks: macOS Permission Retention And Relaunch Reliability

**Input**: Design documents from `/specs/095-macos-permission-retention/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Required because this is a high-risk macOS permissions,
installer/signing, and desktop UX feature.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing. Phase 1 release requires both P1 stories: US1 and
US2.

**Planning note**: A local exploratory hotfix for termination modal dismissal
exists in the worktree. Treat this task list as the source of truth; mark tasks
`[X]` only after reconciling that diff with this spec and recording validation
evidence.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: Which user story the task maps to
- Every task includes exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm context and prepare shared evidence surfaces.

- [X] T001 Review `specs/095-macos-permission-retention/spec.md`, `specs/095-macos-permission-retention/plan.md`, `specs/095-macos-permission-retention/research.md`, `specs/095-macos-permission-retention/data-model.md`, `specs/095-macos-permission-retention/contracts/macos-app-identity-contract.md`, `specs/095-macos-permission-retention/contracts/local-signing-runbook.md`, `specs/095-macos-permission-retention/contracts/termination-relaunch-contract.md`, and `specs/095-macos-permission-retention/quickstart.md`
- [X] T002 [P] Review current installer signing behavior in `apps/macos/Installer/Scripts/build-local-installer.sh` and `apps/macos/Installer/README.md`
- [X] T003 [P] Review current app lifecycle and permission onboarding behavior in `apps/macos/RecApp/App/TwoBrainRecApp.swift`, `apps/macos/RecApp/Sources/Capture/DesktopPermissionOnboardingView.swift`, and `apps/macos/RecApp/Sources/Capture/SystemAudioPermissionGate.swift`
- [X] T004 [P] Review current permission and installer tests in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`, `apps/macos/Shared/Tests/SystemAudioPermissionGateTests.swift`, `apps/macos/Shared/Tests/SystemAudioPermissionUXTests.swift`, and `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift`
- [X] T005 [P] Create or refresh implementation evidence in `specs/095-macos-permission-retention/validation/implementation-evidence.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared signing classification, evidence, and script guardrails
needed before user story validation.

**Critical**: No user story can be accepted until this phase is complete.

- [X] T006 [P] Add signing classification and local-self-signed policy tests in `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift`
- [X] T007 [P] Add app identity source assertions for bundle id, permission usage strings, and non-driver default package scope in `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift`
- [X] T008 Implement explicit local self-signed app signing allow flag in `apps/macos/Installer/Scripts/build-local-installer.sh`
- [X] T009 Preserve strict default signing behavior and release-like Apple identity checks in `apps/macos/Installer/Scripts/build-local-installer.sh`
- [X] T010 Update local signing and public release boundary docs in `apps/macos/Installer/README.md`
- [X] T011 Add metadata-only signing evidence fields to `specs/095-macos-permission-retention/validation/implementation-evidence.md`
- [X] T012 Run shell syntax checks for `apps/macos/Installer/Scripts/build-local-installer.sh` and `apps/macos/Installer/Scripts/install-user-app.sh`

**Checkpoint**: Local signing policy is explicit, test-covered, and cannot be
mistaken for public Developer ID/notarization readiness.

---

## Phase 3: User Story 1 - Keep Permissions Across Reinstall (Priority: P1)

**Goal**: A user who already granted permissions can reinstall a same-identity
GRAF build without granting microphone and Screen/System Audio again.

**Independent Test**: Install a stable signed local package, grant permissions
once, reinstall another package signed by the same identity, launch the app,
and confirm permissions remain granted and no permission modal appears.

### Tests for User Story 1

- [X] T013 [P] [US1] Add permission-retention source/contract assertions in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`
- [X] T014 [P] [US1] Add granted-permission no-onboarding regression coverage in `apps/macos/Shared/Tests/SystemAudioPermissionUXTests.swift`
- [X] T015 [P] [US1] Add metadata-safe install identity validation coverage in `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift`

### Implementation for User Story 1

- [X] T016 [US1] Ensure `apps/macos/Installer/Scripts/build-local-installer.sh` signs `apps/macos/RecApp/.build/GRAF.app` with a stable explicit local identity when `GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING=1`
- [X] T017 [US1] Add or update local permission-retention validation helper in `apps/macos/Scripts/validate-macos-permission-retention.sh`
- [X] T018 [US1] Ensure `apps/macos/RecApp/App/TwoBrainRecApp.swift` suppresses permission onboarding when both permissions are granted on app appear
- [X] T019 [US1] Record first install, permission grant, reinstall, app identity, TCC summary, and no-modal evidence in `specs/095-macos-permission-retention/validation/implementation-evidence.md`

**Checkpoint**: Permission continuity is proven for the same-Mac local
self-signed path or explicitly blocked with a concrete reason.

---

## Phase 4: User Story 2 - Let macOS Quit And Relaunch The App (Priority: P1)

**Goal**: Permission onboarding and other desktop prompts cannot block macOS
quit/relaunch.

**Independent Test**: Open or simulate permission onboarding, ask GRAF to quit,
and confirm sheets/prompts are dismissed and the app replies within 10 seconds.

### Tests for User Story 2

- [X] T020 [P] [US2] Add termination modal dismissal assertions in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`
- [X] T021 [P] [US2] Add meeting-detection prompt clearing assertion for termination in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`

### Implementation for User Story 2

- [X] T022 [US2] Clear permission onboarding state, permission request state, and meeting-detection prompt state on termination notification in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T023 [US2] Dismiss attached AppKit sheets before termination cleanup notification in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T024 [US2] Record installed-app quit/relaunch evidence with and without permission modal state in `specs/095-macos-permission-retention/validation/implementation-evidence.md`

**Checkpoint**: macOS can close GRAF even when permission UI was visible.

---

## Phase 5: User Story 3 - Build Free Local Signed Packages Safely (Priority: P2)

**Goal**: The owner can use a free local signing path without confusing it with
public notarized distribution.

**Independent Test**: Run local signing preflight, build with the explicit
local flag, inspect app signature, and confirm docs/status state local-only
scope.

### Tests for User Story 3

- [X] T025 [P] [US3] Add README/source assertions for local-only signing wording in `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift`
- [X] T026 [P] [US3] Add public-release boundary assertions for Developer ID/notarization wording in `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift`

### Implementation for User Story 3

- [X] T027 [US3] Document local self-signed identity creation/reuse, preservation, and drift limits in `apps/macos/Installer/README.md`
- [X] T028 [US3] Document Developer ID Application, Developer ID Installer, notarization, and stapling as future release prerequisites in `apps/macos/Installer/README.md`
- [X] T029 [US3] Update `[Unreleased]` in `CHANGELOG.md` for feature `095-macos-permission-retention`

**Checkpoint**: The free path is usable and truthfully scoped to local owner
validation.

---

## Phase 6: User Story 4 - Keep Permission UX Truthful (Priority: P2)

**Goal**: Permission recovery UI appears only when useful and stays truthful
for missing permissions and signing drift.

**Independent Test**: Run granted/missing/restricted/signing-drift scenarios and
confirm UI, logs, and evidence use the right state labels.

### Tests for User Story 4

- [X] T030 [P] [US4] Add permission copy and recovery-state assertions in `apps/macos/Shared/Tests/SystemAudioPermissionUXTests.swift`
- [X] T031 [P] [US4] Add source assertions that permission onboarding does not request permissions during termination in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`

### Implementation for User Story 4

- [X] T032 [US4] Adjust permission onboarding copy or state labels if needed in `apps/macos/RecApp/Sources/Capture/DesktopPermissionOnboardingView.swift`
- [X] T033 [US4] Record permission matrix and signing-drift limitations in `specs/095-macos-permission-retention/validation/implementation-evidence.md`

**Checkpoint**: Permission UX is quiet when ready, specific when blocked, and
honest when signing drift requires a regrant.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Close validation, documentation, and Spec Kit evidence.

- [X] T034 [P] Run focused Swift tests from `specs/095-macos-permission-retention/quickstart.md`
- [X] T035 [P] Run static spec/forbidden-content scans from `specs/095-macos-permission-retention/quickstart.md`
- [X] T036 Run package build, reinstall, permission-retention, and quit/relaunch scenarios from `specs/095-macos-permission-retention/quickstart.md`
- [X] T037 Run `infra/scripts/ci-local.sh` and record result in `specs/095-macos-permission-retention/validation/implementation-evidence.md`
- [X] T038 Review `specs/095-macos-permission-retention/checklists/requirements.md`, `specs/095-macos-permission-retention/checklists/audio-capture.md`, `specs/095-macos-permission-retention/checklists/ux.md`, and `specs/095-macos-permission-retention/checklists/installer-signing.md` against final implementation
- [X] T039 Record high-risk validation lane, no-deploy boundary, local-only signing boundary, and public-release blockers in `specs/095-macos-permission-retention/validation/implementation-evidence.md`
- [X] T040 Mark completed tasks `[X]` only after implementation and validation evidence pass in `specs/095-macos-permission-retention/tasks.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1; blocks all user stories.
- **US1 and US2**: Depend on Phase 2. Both are P1 and required before closeout.
- **US3 and US4**: Depend on Phase 2; can proceed after P1 work starts but
  must be complete before release/readiness claims.
- **Phase 7 Polish**: Depends on desired user stories and must run before
  closeout.

### User Story Dependencies

- **US1**: Can start after Phase 2.
- **US2**: Can start after Phase 2 and can be worked independently from the
  installer-signing changes.
- **US3**: Depends on Phase 2 signing policy decisions.
- **US4**: Depends on current permission UX review and can be implemented in
  parallel with US1/US2 if file edits are coordinated.

### Parallel Opportunities

- T002-T005 can run in parallel.
- T006-T007 can run in parallel before T008-T012.
- Test tasks inside each user story can run in parallel.
- US1 installer/script work and US2 app lifecycle work touch different primary
  files and can be implemented in parallel after Phase 2.
- Documentation tasks T027-T029 can run in parallel after local signing policy
  is decided.

## Parallel Example: US2

```text
Task: T020 Add termination modal dismissal assertions in apps/macos/Shared/Tests/AppControlAccessibilityTests.swift
Task: T021 Add meeting-detection prompt clearing assertion in apps/macos/Shared/Tests/AppControlAccessibilityTests.swift
```

## Implementation Strategy

### MVP First (P1 Stories)

1. Complete setup and foundational signing guardrails.
2. Complete US1 permission retention validation.
3. Complete US2 termination/relaunch modal handling.
4. Stop and validate focused tests plus reinstall/quit quickstart scenarios.

### Full Feature Closeout

1. Complete US3 local signing runbook and public release boundary.
2. Complete US4 permission UX truth matrix.
3. Run quickstart, forbidden-content scan, and `infra/scripts/ci-local.sh`.
4. Update tasks and evidence only after validation passes.
