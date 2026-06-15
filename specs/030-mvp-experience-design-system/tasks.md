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

- [X] T001 Create design artifact index in `specs/030-mvp-experience-design-system/design/README.md`
- [X] T002 [P] Create observation evidence template in `specs/030-mvp-experience-design-system/design/evidence/observation-template.md`
- [X] T003 [P] Create screen spec template in `specs/030-mvp-experience-design-system/design/templates/screen-spec-template.md`
- [X] T004 [P] Create prototype evidence template in `specs/030-mvp-experience-design-system/design/templates/prototype-evidence-template.md`
- [X] T005 Create visual asset inventory placeholder in `specs/030-mvp-experience-design-system/design/visual/asset-inventory.md`

---

## Phase 2: Foundational

**Purpose**: Shared product maps and source evidence that block all user-story design work.

**Critical**: No user-story artifact should be accepted until the foundation maps exist.

- [X] T006 [P] Document current implemented product baseline in `specs/030-mvp-experience-design-system/design/evidence/current-product-inventory.md`
- [X] T007 [P] Document clean-room Krisp observation scope and forbidden-copy boundaries in `specs/030-mvp-experience-design-system/design/evidence/krisp-cleanroom-observation.md`
- [X] T008 [P] Document current desktop app/tray observation findings in `specs/030-mvp-experience-design-system/design/evidence/desktop-app-observation.md`
- [X] T009 [P] Document current web cabinet/account observation findings in `specs/030-mvp-experience-design-system/design/evidence/web-cabinet-observation.md`
- [X] T010 Create first-launch surface map in `specs/030-mvp-experience-design-system/design/launch-scope-map.md`
- [X] T011 Create owner value loop map in `specs/030-mvp-experience-design-system/design/owner-value-loop.md`
- [X] T012 Create route visibility matrix in `specs/030-mvp-experience-design-system/design/route-visibility-matrix.md`
- [X] T013 Create cross-surface status state matrix in `specs/030-mvp-experience-design-system/design/status-state-matrix.md`
- [X] T014 Create design validation evidence log in `specs/030-mvp-experience-design-system/design/validation-evidence.md`

**Checkpoint**: Foundation maps and observation evidence are ready for independent story work.

---

## Phase 3: User Story 1 - Launchable MVP Product Shape (Priority: P1)

**Goal**: Define what the first launch actually includes, what is already implemented, and what remains deferred or out of scope.

**Independent Test**: A reviewer can explain "what ships in MVP" and "what remains after MVP" from the scope map without reading implementation specs.

- [X] T015 [US1] Classify accepted foundations, first-launch gaps, deferred items, and out-of-scope items in `specs/030-mvp-experience-design-system/design/launch-scope-map.md`
- [X] T016 [US1] Map `014` desktop upload, `015` processing, `028` auth/session, and `029` account-linking dependencies in `specs/030-mvp-experience-design-system/design/launch-scope-map.md`
- [X] T017 [US1] Define first-launch surface taxonomy for native desktop, embedded cabinet, browser cabinet, handoff entry, and deferred surfaces in `specs/030-mvp-experience-design-system/design/launch-scope-map.md`
- [X] T018 [US1] Document MVP user promise and non-promise copy boundaries in `specs/030-mvp-experience-design-system/design/owner-value-loop.md`
- [X] T019 [US1] Validate US1 acceptance evidence in `specs/030-mvp-experience-design-system/design/validation-evidence.md`

**Checkpoint**: User Story 1 is independently reviewable.

---

## Phase 4: User Story 2 - Native Desktop Trust Shell (Priority: P1)

**Goal**: Design the macOS shell that owns capture-critical truth, local status, upload truth, and safe entry to the embedded server cabinet.

**Independent Test**: Active recording, Stop, local artifact truth, upload queue truth, permission recovery, and server/account status remain visible and locally authoritative across all desktop states.

- [X] T020 [P] [US2] Specify desktop home/ready screen in `specs/030-mvp-experience-design-system/design/screens/desktop-home-ready.md`
- [X] T021 [P] [US2] Specify active recording and one-action Stop screen in `specs/030-mvp-experience-design-system/design/screens/desktop-active-recording.md`
- [X] T022 [P] [US2] Specify permission-blocked and recovery screen in `specs/030-mvp-experience-design-system/design/screens/desktop-permission-recovery.md`
- [X] T023 [P] [US2] Specify local saved, local-only, queued, uploading, and failed upload states in `specs/030-mvp-experience-design-system/design/screens/desktop-upload-queue.md`
- [X] T024 [P] [US2] Specify server/account offline, signed-out, stale-policy, and blocked states in `specs/030-mvp-experience-design-system/design/screens/desktop-account-status.md`
- [X] T025 [P] [US2] Specify embedded cabinet entry and native boundary rules in `specs/030-mvp-experience-design-system/design/screens/desktop-embedded-cabinet-entry.md`
- [X] T026 [US2] Define desktop tray/menu bar behavior and compact status rules in `specs/030-mvp-experience-design-system/design/screens/desktop-tray-status.md`
- [X] T027 [US2] Update route visibility matrix with every desktop native and embedded cabinet entry in `specs/030-mvp-experience-design-system/design/route-visibility-matrix.md`
- [X] T028 [US2] Validate US2 capture-boundary evidence in `specs/030-mvp-experience-design-system/design/validation-evidence.md`

**Checkpoint**: User Story 2 is independently reviewable.

---

## Phase 5: User Story 3 - Server Web Cabinet And Meeting Review (Priority: P1)

**Goal**: Design the web cabinet and meeting review surface that make recordings and uploaded media useful after processing.

**Independent Test**: A user can upload or open a meeting, understand processing progress, and review transcript, playback context, summary, decisions, action items, provenance, degraded state, deletion, and access state.

- [X] T029 [P] [US3] Specify browser cabinet information architecture in `specs/030-mvp-experience-design-system/design/screens/web-cabinet-ia.md`
- [X] T030 [P] [US3] Specify empty meeting list and recent meetings screen in `specs/030-mvp-experience-design-system/design/screens/web-meetings-list.md`
- [X] T031 [P] [US3] Specify manual media upload flow for audio and common video/meeting files in `specs/030-mvp-experience-design-system/design/screens/web-manual-upload.md`
- [X] T032 [P] [US3] Specify upload, audio extraction, transcription, transcript-ready, and notes-ready status states in `specs/030-mvp-experience-design-system/design/screens/web-processing-status.md`
- [X] T033 [P] [US3] Specify complete meeting review surface in `specs/030-mvp-experience-design-system/design/screens/web-meeting-review-complete.md`
- [X] T034 [P] [US3] Specify partial, degraded, failed, deleted, and access-denied meeting review states in `specs/030-mvp-experience-design-system/design/screens/web-meeting-review-exceptions.md`
- [X] T035 [US3] Update status state matrix with upload, processing, review, deletion, and access labels in `specs/030-mvp-experience-design-system/design/status-state-matrix.md`
- [X] T036 [US3] Define source and track provenance copy for desktop recordings and manual uploads in `specs/030-mvp-experience-design-system/design/source-track-provenance.md`
- [X] T037 [US3] Validate US3 meeting-review evidence in `specs/030-mvp-experience-design-system/design/validation-evidence.md`

**Checkpoint**: User Story 3 is independently reviewable.

---

## Phase 6: User Story 4 - Cross-Platform UI Contracts And Boundaries (Priority: P2)

**Goal**: Define shared states, terminology, and design-system contracts that support macOS now and future native desktop platforms later.

**Independent Test**: Desktop and web use the same user meaning for status and cabinet routes while capture-critical controls remain native per platform.

- [X] T038 [P] [US4] Define shared product terminology and status naming in `specs/030-mvp-experience-design-system/design/system/terminology.md`
- [X] T039 [P] [US4] Define design token roles for typography, spacing, color, elevation, density, and motion in `specs/030-mvp-experience-design-system/design/system/tokens.md`
- [X] T040 [P] [US4] Define component inventory for desktop, embedded cabinet, and web cabinet surfaces in `specs/030-mvp-experience-design-system/design/system/components.md`
- [X] T041 [P] [US4] Define localization matrix for Russian and English recording/upload/processing/auth/deletion/policy copy in `specs/030-mvp-experience-design-system/design/system/localization-matrix.md`
- [X] T042 [P] [US4] Define accessibility requirements for keyboard, focus, screen reader labels, contrast, non-color cues, and overflow in `specs/030-mvp-experience-design-system/design/system/accessibility.md`
- [X] T043 [US4] Update route visibility matrix with future platform reuse notes in `specs/030-mvp-experience-design-system/design/route-visibility-matrix.md`
- [X] T044 [US4] Validate US4 cross-platform contract evidence in `specs/030-mvp-experience-design-system/design/validation-evidence.md`

**Checkpoint**: User Story 4 is independently reviewable.

---

## Phase 7: User Story 5 - Clean-Room Visual Direction And Brand-Distance Gate (Priority: P2)

**Goal**: Produce a modern 2026 visual direction and prototype handoff that is category-aware but original to 2brain Rec.

**Independent Test**: Reviewers can inspect visual direction, static screens, clickable paths, and brand-distance evidence without copied Krisp UI, copy, icons, assets, screenshots, or proprietary behavior.

- [X] T045 [P] [US5] Define visual direction principles, tone, density, and light/dark theme rules in `specs/030-mvp-experience-design-system/design/visual/visual-direction.md`
- [X] T046 [P] [US5] Define iconography and component expression rules in `specs/030-mvp-experience-design-system/design/visual/iconography-and-expression.md`
- [X] T047 [US5] Create static visual pack inventory for key desktop and web screens in `specs/030-mvp-experience-design-system/design/visual/static-visual-pack.md`
- [X] T048 [US5] Record Figma prototype file/link, frames, component status, and access constraints in `specs/030-mvp-experience-design-system/design/prototype/figma-handoff.md`
- [X] T049 [US5] Record StitchFlow fallback readiness, project metadata expectations, export paths, and warnings in `specs/030-mvp-experience-design-system/design/prototype/stitchflow-fallback.md`
- [X] T050 [US5] Define clickable prototype path map for the twelve required owner value loop paths in `specs/030-mvp-experience-design-system/design/prototype/clickable-paths.md`
- [X] T051 [US5] Create brand-distance review evidence against Krisp category patterns and forbidden copied elements in `specs/030-mvp-experience-design-system/design/visual/brand-distance-review.md`
- [X] T052 [US5] Create visual QA evidence for contrast, text overflow, compact layouts, and non-color cues in `specs/030-mvp-experience-design-system/design/visual/visual-qa.md`
- [X] T053 [US5] Validate US5 prototype and brand-distance evidence in `specs/030-mvp-experience-design-system/design/validation-evidence.md`

**Checkpoint**: User Story 5 is independently reviewable.

---

## Phase 8: User Story 6 - Implementation-Ready Experience Backlog (Priority: P2)

**Goal**: Turn the design work into follow-up implementation slices and validation gates.

**Independent Test**: Each launch-critical gap maps to a follow-up Spec Kit candidate with dependencies, acceptance gates, and validation evidence.

- [X] T054 [P] [US6] Create launch backlog map for dashboard review, access/sharing, retention/deletion, desktop shell polish, web cabinet, and design-system implementation in `specs/030-mvp-experience-design-system/design/backlog/launch-backlog-map.md`
- [X] T055 [P] [US6] Create follow-up feature candidate list with proposed numbers, dependencies, and acceptance gates in `specs/030-mvp-experience-design-system/design/backlog/follow-up-feature-candidates.md`
- [X] T056 [P] [US6] Create implementation handoff summary for macOS native work in `specs/030-mvp-experience-design-system/design/backlog/macos-handoff.md`
- [X] T057 [P] [US6] Create implementation handoff summary for server/web cabinet work in `specs/030-mvp-experience-design-system/design/backlog/web-cabinet-handoff.md`
- [X] T058 [US6] Map each artifact to future task families and acceptance gates in `specs/030-mvp-experience-design-system/design/backlog/launch-backlog-map.md`
- [X] T059 [US6] Validate US6 backlog evidence in `specs/030-mvp-experience-design-system/design/validation-evidence.md`

**Checkpoint**: User Story 6 is independently reviewable.

---

## Final Phase: Polish & Cross-Cutting Validation

**Purpose**: Ensure the complete design slice is ready for analyze, implementation review, and downstream execution.

- [X] T060 Create consolidated screen inventory from all desktop, embedded, and web screen specs in `specs/030-mvp-experience-design-system/design/screen-inventory.md`
- [X] T061 Create consolidated user flow map for record, upload, processing, review, degraded, deletion, access, and browser handoff paths in `specs/030-mvp-experience-design-system/design/user-flows.md`
- [X] T062 Create design QA checklist for route/status/prototype/accessibility/brand-distance acceptance in `specs/030-mvp-experience-design-system/design/qa-checklist.md`
- [X] T063 Create final prototype source decision and accepted clickable-artifact evidence in `specs/030-mvp-experience-design-system/design/prototype/prototype-source-decision.md`
- [X] T064 Create reviewer readiness scorecard for MVP scope comprehension in `specs/030-mvp-experience-design-system/design/reviewer-readiness-scorecard.md`
- [X] T065 Run quickstart validation and record results in `specs/030-mvp-experience-design-system/design/validation-evidence.md`
- [X] T066 Update prototype handoff contract references from final design artifacts in `specs/030-mvp-experience-design-system/contracts/prototype-handoff-contract.md`
- [X] T067 Update route visibility contract references from final matrix decisions in `specs/030-mvp-experience-design-system/contracts/route-visibility-contract.md`
- [X] T068 Update cross-surface status contract references from final state matrix decisions in `specs/030-mvp-experience-design-system/contracts/cross-surface-status-contract.md`
- [X] T069 Update current product status summary for this design-readiness slice in `docs/current-product-status.md`
- [X] T070 Update changelog entry for feature `030` in `CHANGELOG.md`

## Post-Review Addendum: V5 Full-Flow Critics Fixes

**Purpose**: Record and close the post-task stakeholder critique that 14 frames
were not enough and that every screen, menu, button family, and full MVP flow
needed a stronger Figma handoff.

- [X] T071 [US5] Create initial v5 full-flow Figma page before the v5.1 shell/product boundary expansion in `specs/030-mvp-experience-design-system/design/prototype/figma-handoff.md`
- [X] T072 [US5] Record five-round critics review, fixes, and completion audit in `specs/030-mvp-experience-design-system/design/reviews/v5-full-flow-critics-2026-06-11/findings-and-fixes.md`
- [X] T073 [US5] Capture final v5 desktop/web/review/speaker/share/export/delete screenshots in `specs/030-mvp-experience-design-system/design/reviews/v5-full-flow-critics-2026-06-11/screenshots/`
- [X] T074 [US5] Expand v5 prototype reactions for buttons, top bar, menu controller, and sidebar navigation in `specs/030-mvp-experience-design-system/design/prototype/clickable-paths.md`
- [X] T075 [US5] Update Figma handoff, visual QA, static pack, prototype source decision, and validation evidence for v5/v5.1 reaction coverage and layout QA in `specs/030-mvp-experience-design-system/design/`
- [X] T076 [US5] Record selected free UI kit and template references in `specs/030-mvp-experience-design-system/design/visual/asset-inventory.md`
- [X] T077 [US5] Update prototype handoff contract and implementation plan with then-current v5 coverage evidence in `specs/030-mvp-experience-design-system/contracts/prototype-handoff-contract.md` and `specs/030-mvp-experience-design-system/plan.md`
- [X] T078 [US6] Update product status and changelog with then-current v5 full-flow design handoff evidence in `docs/current-product-status.md` and `CHANGELOG.md`

## Post-Review Addendum: Multiplatform Shell And Embedded Product UI

**Purpose**: Record the follow-up stakeholder decision that variable product UI
must come from web/backend across macOS, Windows, and Linux desktop shells, and
that speaker assignment must be available in desktop as embedded server-owned UI.

- [X] T079 [US4] Promote platform desktop shell versus server-owned product UI boundary into `specs/030-mvp-experience-design-system/spec.md` and `specs/030-mvp-experience-design-system/plan.md`
- [X] T080 [US4] Add embedded product UI route/API/bridge contract in `specs/030-mvp-experience-design-system/contracts/embedded-product-ui-contract.md`
- [X] T081 [US4] Update route visibility, screen specs, component inventory, terminology, localization, and status matrix for desktop embedded speaker assignment in `specs/030-mvp-experience-design-system/design/`
- [X] T082 [US5] Add Figma proof frames `V5 34 - Desktop embedded speaker assignment` and `V5 35 - Active recording with embedded review` to show native shell boundaries and active Stop over embedded web in `specs/030-mvp-experience-design-system/design/prototype/figma-handoff.md`
- [X] T083 [US5] Capture final screenshots for `V5 34` and `V5 35` in `specs/030-mvp-experience-design-system/design/reviews/v5-full-flow-critics-2026-06-11/screenshots/`
- [X] T084 [US5] Run final Figma audit after the shell/product UI patch and update `figma-handoff.md`, `visual-qa.md`, `validation-evidence.md`, and `findings-and-fixes.md`
- [X] T085 [US6] Integrate five-critic findings and rerun repository hygiene checks in `specs/030-mvp-experience-design-system/design/reviews/v5-full-flow-critics-2026-06-11/findings-and-fixes.md`

## Post-Review Addendum: V8 Clean Russian Handoff Candidate

**Purpose**: Record the follow-up stakeholder critique that V5-V7 still had
uneven button sizing, weak IA, technical wording, sparse layouts, incomplete
settings, unclear first-run/auth/permission flow, and insufficient desktop/web
alignment. V8 supersedes the earlier prototype lineage for implementation
review, while final stakeholder visual approval remains open.

- [X] T086 [US5] Create the active V8 clean Russian Figma page and record it in `specs/030-mvp-experience-design-system/design/prototype/figma-handoff.md`
- [X] T087 [US5] Rebuild V8 around compact provider sign-in, guided macOS permissions, desktop meeting workspace, auto-detected meeting prompt, menu-bar/header recording state, inline upload/processing, transcript review, speaker lanes, settings/theme, web list/detail, governance, light proof, and component QA in `specs/030-mvp-experience-design-system/design/reviews/v8-clean-ru-2026-06-15/figma-v8-qa.md`
- [X] T088 [US5] Run whole-page V8 Figma API QA for overflow, button heights, chip heights, technical-copy leaks, placeholder artifacts, and screenshot-reviewed fixes in `specs/030-mvp-experience-design-system/design/reviews/v8-clean-ru-2026-06-15/figma-v8-qa.md`
- [X] T089 [US5] Run V8 clickable prototype QA for all owner-value-loop routes and record reaction graph evidence in `specs/030-mvp-experience-design-system/design/prototype/clickable-paths.md`
- [X] T090 [US5] Run five-critic V8 screen audit across product-flow, IA, visual/UI, platform, and content/trust lenses in `specs/030-mvp-experience-design-system/design/reviews/v8-clean-ru-2026-06-15/five-critic-screen-audit.md`
- [X] T091 [US6] Create stakeholder visual approval pack with direct Figma links, click-through script, per-screen accept/reject criteria, and decision template in `specs/030-mvp-experience-design-system/design/reviews/v8-clean-ru-2026-06-15/stakeholder-visual-approval-pack.md`
- [X] T092 [US6] Update active handoff references from V5/V7 to V8 in `specs/030-mvp-experience-design-system/plan.md`, `specs/030-mvp-experience-design-system/contracts/prototype-handoff-contract.md`, `specs/030-mvp-experience-design-system/contracts/route-visibility-contract.md`, and `specs/030-mvp-experience-design-system/contracts/cross-surface-status-contract.md`
- [ ] T093 [US5] Record final stakeholder visual approval of V8 in `specs/030-mvp-experience-design-system/design/qa-checklist.md` and `specs/030-mvp-experience-design-system/design/validation-evidence.md`

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
- Screen inventory, user flows, route matrix, status matrix, component inventory,
  visual direction, static visual pack, clickable prototype evidence, and QA
  checklist exist as reviewable artifacts.
- `quickstart.md` validation evidence exists.
- Route/status/prototype contracts reference final design artifacts.
- No production capture/auth/MediaScribe/deletion code is changed by this feature.
