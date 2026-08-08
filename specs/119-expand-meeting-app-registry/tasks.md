# Tasks: Expanded Meeting App Registry

**Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md),
[data-model.md](./data-model.md), [target-catalog.md](./target-catalog.md),
[contracts/registry-expansion.md](./contracts/registry-expansion.md)

**Tests**: Required. This high-risk slice changes registry acceptance, detection
identity resolution, migration state, and settings UX.

**Current behavior owner**: Feature 124 restores and protects the runtime
consumer of this catalog. Do not replace the common list or its auto-record row
with a detect-only/diagnostic surface; the prompt countdown, automatic expiry
start, immediate start, skip, and target-scoped checkbox are covered there.

## Phase 1: Contract And Safety Foundation

- [X] T001 [P] Document the case-insensitive native identity and evidence-backed
  prompt invariant in `specs/119-expand-meeting-app-registry/contracts/registry-expansion.md`.
- [X] T002 [P] Add server tests for case-insensitive duplicate bundle rejection,
  all verified native targets being prompt-enabled, released-target preservation, and
  minimum catalog counts in `apps/server/tests/unit/test_meeting_detection_registry.py`.
- [X] T003 [P] Add Swift tests for mixed-case resolution, duplicate bundle
  rejection, and shared Telegram Desktop/Forkgram/64Gram identity in
  `apps/macos/Shared/Tests/MeetingTargetRegistryTests.swift`.

---

## Phase 2: User Story 1 — Recognize More Native Meeting Apps (P1)

**Independent test**: Every catalogued bundle ID resolves to exactly one known
target; every verified native target appears in the common list and can prompt
or auto-record after explicit user selection.

- [X] T004 [US1] Add case-insensitive cross-target bundle uniqueness validation
  and verified-identity prompt validation in `apps/server/src/twobrain_rec_server/meeting_detection/registry.py`.
- [X] T005 [US1] Add case-insensitive bundle resolution and duplicate identity
  validation in
  `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionModels.swift` and
  `apps/macos/Shared/Sources/MeetingDetection/MeetingTargetRegistry.swift`.
- [X] T006 [US1] Create the expanded immutable registry document with all 31
  released targets, 54 new native targets, 87 unique bundle IDs, Telegram
  shared-ID mapping, and prompt mode for every verified native identity in
  `apps/server/src/twobrain_rec_server/db/migrations/data/0030_meeting_target_registry.json`.
- [X] T007 [US1] Make the server registry tests consume and validate the new
  baseline without mutating migration 0019 history in
  `apps/server/tests/unit/test_meeting_detection_registry.py`.
- [ ] T008 [P2] [US1] [required_post_deploy] After enablement, record live start/end, idle/prejoin, applicable voice-message,
  prompt, visible-state, and Stop evidence per available current app build in
  `specs/119-expand-meeting-app-registry/live-validation.md`; validate resolution
  and policy for every resulting mode in
  `apps/macos/Shared/Tests/MeetingTargetRegistryTests.swift` and
  `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift`.

**Checkpoint**: US1 resolves the full native catalog, exposes all verified native
targets to prompt/user-selected auto-record, and rejects duplicate case-folded IDs.

---

## Phase 3: User Story 2 — Understand Actual Support (P1)

**Independent test**: Settings show one scrollable applications list alongside
Zoom and Telemost; all verified native targets have enabled auto-record controls
and “Выбрать все” selects the complete set.

- [X] T009 [P] [US2] Add source-contract tests for one common scrollable list,
  full target rendering, empty state, and “Выбрать все” coverage in
  `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`.
- [X] T010 [US2] Reuse the existing prompt target read model and row; add the
  minimum scrolling/accessibility change needed for the complete list in
  `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift`.
- [X] T011 [US2] Preserve target-scoped auto-record preference behavior and
  existing capture-control contracts in
  `apps/macos/Shared/Tests/CaptureControlV5Tests.swift`.

**Checkpoint**: The complete native list is visible beside Zoom and Telemost,
with identical controls and no engineering diagnostic section.

---

## Phase 4: User Story 3 — Cover Browser Systems Honestly (P2)

**Independent test**: Implemented first-party families resolve only with joined
metadata plus join intent; generic/unknown/browser-audio-only evidence is manual.

- [X] T012 [P] [US3] Add regression assertions that the documented browser
  backlog is not exported as live support and generic browser evidence remains
  fail-closed in `apps/macos/Shared/Tests/BrowserTargetEvidenceTests.swift`.
- [X] T013 [US3] Reconcile catalog wording and implemented resolver families in
  `specs/119-expand-meeting-app-registry/target-catalog.md` and
  `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionModels.swift`
  without adding speculative domains.

**Checkpoint**: Browser research breadth is documented, while runtime support
remains bounded to actually implemented service-family evidence.

---

## Phase 5: User Story 4 — Publish And Roll Back The Baseline (P2)

**Independent test**: Upgrade publishes only the new global baseline and
downgrade restores the previous global baseline without touching workspace rows.

- [X] T014 [P] [US4] Add migration upgrade/downgrade and workspace-precedence
  coverage in `apps/server/tests/integration/test_meeting_detection_migrations.py`.
- [X] T015 [US4] Implement migration-owned global publication and rollback in
  `apps/server/src/twobrain_rec_server/db/migrations/versions/0030_expand_meeting_target_registry.py`.
- [X] T016 [US4] Validate the new document through existing registry export,
  ETag, and last-good cache tests in
  `apps/server/tests/integration/test_meeting_detection_registry.py` and
  `apps/macos/Shared/Tests/MeetingTargetRegistryTests.swift`.

**Checkpoint**: Deployed databases can adopt and roll back the expansion; client
cache failure remains manual-safe.

---

## Phase 6: Documentation And Full Validation

- [X] T017 [P] Update exact support-mode counts, Telegram coverage, browser
  limitation, and post-enable live-QA boundary in `docs/current-product-status.md`.
- [X] T018 [P] Add an unreleased Russian behavior/QA note in `CHANGELOG.md`.
- [X] T019 Run the focused server/macOS commands in
  `specs/119-expand-meeting-app-registry/quickstart.md` and record results there.
- [X] T020 Run `infra/scripts/ci-local.sh`, resolve in-scope failures, and record
  full evidence in `specs/119-expand-meeting-app-registry/quickstart.md`.
- [X] T021 Reconcile completed tasks, catalog-derived counts, and no-secret scan
  evidence across `specs/119-expand-meeting-app-registry/tasks.md` and
  `specs/119-expand-meeting-app-registry/quickstart.md`.

## Dependencies

1. T001–T003 establish failing safety/contract tests.
2. T004–T007 complete the enablement part of US1; T008 is required post-deploy
   QA and does not block the breadth-first rollout requested by the user.
3. T009–T011 depend on the alias/read model from T005–T006.
4. T012–T013 are independent after T001 and may run beside US2.
5. T014 must fail before T015; T016 follows T015.
6. T017–T021 follow all user-story checkpoints.

## Parallel Opportunities

- T001, T002, and T003 target independent contract/server/Swift files.
- T009 and T012 target independent XCTest files after the shared model is stable.
- T014 can be prepared while T010 is implemented.
- T017 and T018 can be drafted together after generated counts are final.

## Implementation Strategy

Start with validator tests and the immutable JSON baseline. Deliver native
recognition first, then expose the existing registry through the settings view,
preserve browser fail-closed behavior, and finally add migration publication.
No new dependency or detector is introduced.
