# Tasks: MVP Product Experience And Design System

**Input**: Design documents from `/specs/030-mvp-experience-design-system/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `checklists/`

**Tests**: This feature is design/product-readiness work. Validation tasks are included because the spec requires route/status/prototype/brand-distance review; no production code tests are authorized by this slice.

**Organization**: Tasks are grouped by user story so each design increment can be reviewed independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no dependency on incomplete tasks.
- **[Story]**: Maps to user stories in `spec.md`.
- Every task includes an exact repository file path for traceability.

---

## Phase 1: Setup

**Purpose**: Create the local design workspace and evidence structure for this feature.

- [ ] T001 Create design artifact index in `specs/030-mvp-experience-design-system/design/README.md`
- [ ] T002 [P] Create observation evidence template in `specs/030-mvp-experience-design-system/design/evidence/observation-template.md`
- [ ] T003 [P] Create screen spec template in `specs/030-mvp-experience-design-system/design/templates/screen-spec-template.md`
- [ ] T004 [P] Create prototype evidence template in `specs/030-mvp-experience-design-system/design/templates/prototype-evidence-template.md`
- [ ] T005 Create visual asset inventory placeholder in `specs/030-mvp-experience-design-system/design/visual/asset-inventory.md`

---

## Phase 2: Foundational

**Purpose**: Shared product maps and source evidence that block all user-story design work.

**Critical**: No user-story artifact should be accepted until the foundation maps exist.

- [ ] T006 [P] Document current implemented product baseline in `specs/030-mvp-experience-design-system/design/evidence/current-product-inventory.md`
- [ ] T007 [P] Document clean-room Krisp observation scope and forbidden-copy boundaries in `specs/030-mvp-experience-design-system/design/evidence/krisp-cleanroom-observation.md`
- [ ] T008 [P] Document current desktop app/tray observation findings in `specs/030-mvp-experience-design-system/design/evidence/desktop-app-observation.md`
- [ ] T009 [P] Document current web cabinet/account observation findings in `specs/030-mvp-experience-design-system/design/evidence/web-cabinet-observation.md`
- [ ] T010 Create first-launch surface map in `specs/030-mvp-experience-design-system/design/launch-scope-map.md`
- [ ] T011 Create owner value loop map in `specs/030-mvp-experience-design-system/design/owner-value-loop.md`
- [ ] T012 Create route visibility matrix in `specs/030-mvp-experience-design-system/design/route-visibility-matrix.md`
- [ ] T013 Create cross-surface status state matrix in `specs/030-mvp-experience-design-system/design/status-state-matrix.md`
- [ ] T014 Create design validation evidence log in `specs/030-mvp-experience-design-system/design/validation-evidence.md`

**Checkpoint**: Foundation maps and observation evidence are ready for independent story work.

---

## Phase 3: User Story 1 - Launchable MVP Product Shape (Priority: P1)

**Goal**: Define what the first launch actually includes, what is already implemented, and what remains deferred or out of scope.

**Independent Test**: A reviewer can explain "what ships in MVP" and "what remains after MVP" from the scope map without reading implementation specs.

- [ ] T015 [US1] Classify accepted foundations, first-launch gaps, deferred items, and out-of-scope items in `specs/030-mvp-experience-design-system/design/launch-scope-map.md`
- [ ] T016 [US1] Map `014` desktop upload, `015` processing, `028` auth/session, and `029` account-linking dependencies in `specs/030-mvp-experience-design-system/design/launch-scope-map.md`
- [ ] T017 [US1] Define first-launch surface taxonomy for native desktop, embedded cabinet, browser cabinet, handoff entry, and deferred surfaces in `specs/030-mvp-experience-design-system/design/launch-scope-map.md`
- [ ] T018 [US1] Document MVP user promise and non-promise copy boundaries in `specs/030-mvp-experience-design-system/design/owner-value-loop.md`
- [ ] T019 [US1] Validate US1 acceptance evidence in `specs/030-mvp-experience-design-system/design/validation-evidence.md`

**Checkpoint**: User Story 1 is independently reviewable.

---

## Phase 4: User Story 2 - Native Desktop Trust Shell (Priority: P1)

**Goal**: Design the macOS shell that owns capture-critical truth, local status, upload truth, and safe entry to the embedded server cabinet.

**Independent Test**: Active recording, Stop, local artifact truth, upload queue truth, permission recovery, and server/account status remain visible and locally authoritative across all desktop states.

- [ ] T020 [P] [US2] Specify desktop home/ready screen in `specs/030-mvp-experience-design-system/design/screens/desktop-home-ready.md`
- [ ] T021 [P] [US2] Specify active recording and one-action Stop screen in `specs/030-mvp-experience-design-system/design/screens/desktop-active-recording.md`
- [ ] T022 [P] [US2] Specify permission-blocked and recovery screen in `specs/030-mvp-experience-design-system/design/screens/desktop-permission-recovery.md`
- [ ] T023 [P] [US2] Specify local saved, local-only, queued, uploading, and failed upload states in `specs/030-mvp-experience-design-system/design/screens/desktop-upload-queue.md`
- [ ] T024 [P] [US2] Specify server/account offline, signed-out, stale-policy, and blocked states in `specs/030-mvp-experience-design-system/design/screens/desktop-account-status.md`
- [ ] T025 [P] [US2] Specify embedded cabinet entry and native boundary rules in `specs/030-mvp-experience-design-system/design/screens/desktop-embedded-cabinet-entry.md`
- [ ] T026 [US2] Define desktop tray/menu bar behavior and compact status rules in `specs/030-mvp-experience-design-system/design/screens/desktop-tray-status.md`
- [ ] T027 [US2] Update route visibility matrix with every desktop native and embedded cabinet entry in `specs/030-mvp-experience-design-system/design/route-visibility-matrix.md`
- [ ] T028 [US2] Validate US2 capture-boundary evidence in `specs/030-mvp-experience-design-system/design/validation-evidence.md`

**Checkpoint**: User Story 2 is independently reviewable.

---

## Phase 5: User Story 3 - Server Web Cabinet And Meeting Review (Priority: P1)

**Goal**: Design the web cabinet and meeting review surface that make recordings and uploaded media useful after processing.

**Independent Test**: A user can upload or open a meeting, understand processing progress, and review transcript, playback context, summary, decisions, action items, provenance, degraded state, deletion, and access state.

- [ ] T029 [P] [US3] Specify browser cabinet information architecture in `specs/030-mvp-experience-design-system/design/screens/web-cabinet-ia.md`
- [ ] T030 [P] [US3] Specify empty meeting list and recent meetings screen in `specs/030-mvp-experience-design-system/design/screens/web-meetings-list.md`
- [ ] T031 [P] [US3] Specify manual media upload flow for audio and common video/meeting files in `specs/030-mvp-experience-design-system/design/screens/web-manual-upload.md`
- [ ] T032 [P] [US3] Specify upload, audio extraction, transcription, transcript-ready, and notes-ready status states in `specs/030-mvp-experience-design-system/design/screens/web-processing-status.md`
- [ ] T033 [P] [US3] Specify complete meeting review surface in `specs/030-mvp-experience-design-system/design/screens/web-meeting-review-complete.md`
- [ ] T034 [P] [US3] Specify partial, degraded, failed, deleted, and access-denied meeting review states in `specs/030-mvp-experience-design-system/design/screens/web-meeting-review-exceptions.md`
- [ ] T035 [US3] Update status state matrix with upload, processing, review, deletion, and access labels in `specs/030-mvp-experience-design-system/design/status-state-matrix.md`
- [ ] T036 [US3] Define source and track provenance copy for desktop recordings and manual uploads in `specs/030-mvp-experience-design-system/design/source-track-provenance.md`
- [ ] T037 [US3] Validate US3 meeting-review evidence in `specs/030-mvp-experience-design-system/design/validation-evidence.md`

**Checkpoint**: User Story 3 is independently reviewable.

---

## Phase 6: User Story 4 - Cross-Platform UI Contracts And Boundaries (Priority: P2)

**Goal**: Define shared states, terminology, and design-system contracts that support macOS now and future native desktop platforms later.

**Independent Test**: Desktop and web use the same user meaning for status and cabinet routes while capture-critical controls remain native per platform.

- [ ] T038 [P] [US4] Define shared product terminology and status naming in `specs/030-mvp-experience-design-system/design/system/terminology.md`
- [ ] T039 [P] [US4] Define design token roles for typography, spacing, color, elevation, density, and motion in `specs/030-mvp-experience-design-system/design/system/tokens.md`
- [ ] T040 [P] [US4] Define component inventory for desktop, embedded cabinet, and web cabinet surfaces in `specs/030-mvp-experience-design-system/design/system/components.md`
- [ ] T041 [P] [US4] Define localization matrix for Russian and English recording/upload/processing/auth/deletion/policy copy in `specs/030-mvp-experience-design-system/design/system/localization-matrix.md`
- [ ] T042 [P] [US4] Define accessibility requirements for keyboard, focus, screen reader labels, contrast, non-color cues, and overflow in `specs/030-mvp-experience-design-system/design/system/accessibility.md`
- [ ] T043 [US4] Update route visibility matrix with future platform reuse notes in `specs/030-mvp-experience-design-system/design/route-visibility-matrix.md`
- [ ] T044 [US4] Validate US4 cross-platform contract evidence in `specs/030-mvp-experience-design-system/design/validation-evidence.md`

**Checkpoint**: User Story 4 is independently reviewable.

---

## Phase 7: User Story 5 - Clean-Room Visual Direction And Brand-Distance Gate (Priority: P2)

**Goal**: Produce a modern 2026 visual direction and prototype handoff that is category-aware but original to 2brain Rec.

**Independent Test**: Reviewers can inspect visual direction, static screens, clickable paths, and brand-distance evidence without copied Krisp UI, copy, icons, assets, screenshots, or proprietary behavior.

- [ ] T045 [P] [US5] Define visual direction principles, tone, density, and light/dark theme rules in `specs/030-mvp-experience-design-system/design/visual/visual-direction.md`
- [ ] T046 [P] [US5] Define iconography and component expression rules in `specs/030-mvp-experience-design-system/design/visual/iconography-and-expression.md`
- [ ] T047 [US5] Create static visual pack inventory for key desktop and web screens in `specs/030-mvp-experience-design-system/design/visual/static-visual-pack.md`
- [ ] T048 [US5] Record Figma prototype file/link, frames, component status, and access constraints in `specs/030-mvp-experience-design-system/design/prototype/figma-handoff.md`
- [ ] T049 [US5] Record StitchFlow fallback readiness, project metadata expectations, export paths, and warnings in `specs/030-mvp-experience-design-system/design/prototype/stitchflow-fallback.md`
- [ ] T050 [US5] Define clickable prototype path map for the twelve required owner value loop paths in `specs/030-mvp-experience-design-system/design/prototype/clickable-paths.md`
- [ ] T051 [US5] Create brand-distance review evidence against Krisp category patterns and forbidden copied elements in `specs/030-mvp-experience-design-system/design/visual/brand-distance-review.md`
- [ ] T052 [US5] Create visual QA evidence for contrast, text overflow, compact layouts, and non-color cues in `specs/030-mvp-experience-design-system/design/visual/visual-qa.md`
- [ ] T053 [US5] Validate US5 prototype and brand-distance evidence in `specs/030-mvp-experience-design-system/design/validation-evidence.md`

**Checkpoint**: User Story 5 is independently reviewable.

---

## Phase 8: User Story 6 - Implementation-Ready Experience Backlog (Priority: P2)

**Goal**: Turn the design work into follow-up implementation slices and validation gates.

**Independent Test**: Each launch-critical gap maps to a follow-up Spec Kit candidate with dependencies, acceptance gates, and validation evidence.

- [ ] T054 [P] [US6] Create launch backlog map for dashboard review, access/sharing, retention/deletion, desktop shell polish, web cabinet, and design-system implementation in `specs/030-mvp-experience-design-system/design/backlog/launch-backlog-map.md`
- [ ] T055 [P] [US6] Create follow-up feature candidate list with proposed numbers, dependencies, and acceptance gates in `specs/030-mvp-experience-design-system/design/backlog/follow-up-feature-candidates.md`
- [ ] T056 [P] [US6] Create implementation handoff summary for macOS native work in `specs/030-mvp-experience-design-system/design/backlog/macos-handoff.md`
- [ ] T057 [P] [US6] Create implementation handoff summary for server/web cabinet work in `specs/030-mvp-experience-design-system/design/backlog/web-cabinet-handoff.md`
- [ ] T058 [US6] Map each artifact to future task families and acceptance gates in `specs/030-mvp-experience-design-system/design/backlog/launch-backlog-map.md`
- [ ] T059 [US6] Validate US6 backlog evidence in `specs/030-mvp-experience-design-system/design/validation-evidence.md`

**Checkpoint**: User Story 6 is independently reviewable.

---

## Final Phase: Polish & Cross-Cutting Validation

**Purpose**: Ensure the complete design slice is ready for analyze, implementation review, and downstream execution.

- [ ] T060 Run quickstart validation and record results in `specs/030-mvp-experience-design-system/design/validation-evidence.md`
- [ ] T061 Update prototype handoff contract references from final design artifacts in `specs/030-mvp-experience-design-system/contracts/prototype-handoff-contract.md`
- [ ] T062 Update route visibility contract references from final matrix decisions in `specs/030-mvp-experience-design-system/contracts/route-visibility-contract.md`
- [ ] T063 Update cross-surface status contract references from final state matrix decisions in `specs/030-mvp-experience-design-system/contracts/cross-surface-status-contract.md`
- [ ] T064 Update current product status summary for this design-readiness slice in `docs/current-product-status.md`
- [ ] T065 Update changelog entry for feature `030` in `CHANGELOG.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories.
- **US1, US2, US3 (P1)**: Depend on Foundational. They can proceed in parallel after T006-T014, but the recommended MVP design path is US1 -> US2 -> US3.
- **US4, US5, US6 (P2)**: Depend on Foundational and benefit from US1-US3 outputs. US4 and US5 can proceed in parallel after route/status matrices exist. US6 should run after US1-US5 are substantially complete.
- **Final Phase**: Depends on all selected user stories being complete.

### User Story Dependencies

- **US1**: No dependency on other user stories after Foundational.
- **US2**: Uses foundational route/status matrices; can run independently of US3.
- **US3**: Uses foundational route/status matrices; can run independently of US2 but must reconcile status labels with US2 before final validation.
- **US4**: Depends on US2/US3 state terminology being available for final consistency.
- **US5**: Depends on US2/US3 screen specs for static visual pack and clickable prototype.
- **US6**: Depends on outputs from US1-US5.

### Parallel Opportunities

- T002-T005 can run in parallel.
- T006-T009 can run in parallel.
- T020-T025 can run in parallel after T010-T014.
- T029-T034 can run in parallel after T010-T014.
- T038-T042 can run in parallel after T012-T013.
- T054-T057 can run in parallel after US1-US5 evidence exists.

---

## Parallel Example: Desktop And Web Screens

```text
Task: T020 [US2] Specify desktop home/ready screen in specs/030-mvp-experience-design-system/design/screens/desktop-home-ready.md
Task: T021 [US2] Specify active recording and one-action Stop screen in specs/030-mvp-experience-design-system/design/screens/desktop-active-recording.md
Task: T030 [US3] Specify empty meeting list and recent meetings screen in specs/030-mvp-experience-design-system/design/screens/web-meetings-list.md
Task: T031 [US3] Specify manual media upload flow for audio and common video/meeting files in specs/030-mvp-experience-design-system/design/screens/web-manual-upload.md
```

---

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational phases.
2. Complete US1 to freeze launch scope and owner value loop.
3. Complete US2 and US3 to prove the app/web owner value loop.
4. Stop and validate route/status consistency before visual prototype work.

### Design Prototype Completion

1. Complete US4 for shared terminology and design-system rules.
2. Complete US5 with Figma preferred; use StitchFlow fallback only if Figma access/tooling blocks delivery.
3. Complete US6 to convert design outputs into follow-up feature candidates.
4. Complete Final Phase and run `quickstart.md` evidence.

### Completion Criteria

- Every task is marked `[x]`.
- Every domain checklist remains fully checked.
- `quickstart.md` validation evidence exists.
- Route/status/prototype contracts reference final design artifacts.
- No production capture/auth/MediaScribe/deletion code is changed by this feature.
