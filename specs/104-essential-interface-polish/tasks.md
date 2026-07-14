# Tasks: Essential Interface Polish

**Input**: Design documents from `/specs/104-essential-interface-polish/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `visual-target.md`, `contracts/`, `quickstart.md`

**Tests**: Required. Feature 104 is a high-risk accessibility, brand-distance, diagnostics-presentation, deletion-affordance, and native capture-control slice. Story tests are written first and must fail for the intended reason before implementation.

**Organization**: Tasks are grouped by user story and use exact repository paths. `tasks.md` is the implementation source of truth; tasks are checked only after their named validation passes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: May proceed in parallel only because it touches different files and has no dependency on another incomplete task.
- **[Story]**: Maps the task to one of the prioritized stories in `spec.md`.

## Phase 1: Setup And Baseline

**Purpose**: Freeze current proof and protect unrelated worktree state before product code changes.

- [X] T001 Run the focused baseline server/macOS commands and record command, count, result, and known pre-existing failures in `specs/104-essential-interface-polish/quickstart.md`
- [X] T002 Confirm the selected Stitch project/screen and its `1280×760`/`1040×680` accessibility evidence against `specs/104-essential-interface-polish/visual-target.md`, capture metadata-safe before states for all applicable matrix rows outside git, and record only viewport/state identifiers in `specs/104-essential-interface-polish/quickstart.md`

---

## Phase 2: Foundational Boundary

**Purpose**: Reuse the established server/native ownership, HTMX, SwiftUI/AppKit, diagnostics, deletion, and token foundations.

No new framework, schema, API, storage entity, or shared abstraction is required. The existing boundary in `apps/server/src/twobrain_rec_server/cabinet/` and `apps/macos/RecApp/Sources/` is the foundation. User-story work starts only after T001–T002 establish safe baseline evidence.

**Checkpoint**: Baseline is reproducible, private screenshots remain outside git, and the four pre-existing unrelated worktree changes are preserved.

---

## Phase 3: User Story 1 — Сразу понимать главное (Priority: P1) 🎯 MVP

**Goal**: Turn the server-owned main workspace into a calm meeting-first screen with only working navigation, one search surface, contextual filter/sort/selection, one visible upload action, and no unsupported plan/calendar presentation.

**Independent Test**: At the default window, a reviewer identifies `Мои встречи`, search, upload, current list state, and the separate native recording action within five seconds; no disabled/future destination or inactive bulk action is visible.

### Tests for User Story 1

- [X] T003 [P] [US1] Add failing enabled-only sidebar, compact branding, no hard-coded plan/trial state, and no-placeholder assertions in `apps/server/tests/unit/test_cabinet_navigation_model.py` and `apps/server/tests/unit/test_cabinet_template_sections.py`
- [X] T004 [P] [US1] Add failing one-search, semantic filter/sort, active-reset, preserved meeting-result link, preserved short-debounce/50-row-limit, no-extra-request-control, no-calendar-block, no embedded app-download/onboarding duplicate, contextual-selection, and no-disabled-action assertions in `apps/server/tests/unit/test_cabinet_web_shell.py` and `apps/server/tests/integration/test_cabinet_meeting_list.py`

### Implementation for User Story 1

- [X] T005 [US1] Project only enabled `Мои встречи`/`Настройки` destinations, compact branding, and logout while removing unsupported account-plan copy in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html`
- [X] T006 [US1] Restructure the meeting header into one search, accessible filter/sort disclosures, active reset, upload, preserved primary result links, an installed-app empty state that reuses toolbar upload/native recording without download/onboarding duplicates, no unconditional calendar region, and a delete-only contextual bulk toolbar in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html`
- [X] T007 [US1] Reconcile selection-mode visibility, list replacement, select-all/clear state, disclosure state, and post-delete focus in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T008 [US1] Implement the compact sidebar, meeting-first toolbar, reading/selection modes, subtle selected state, and minimum-window layout without reserved calendar space in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T009 [US1] Run the US1 server tests and document independent five-second comprehension evidence in `specs/104-essential-interface-polish/quickstart.md`

**Checkpoint**: User Story 1 is independently useful with the current native capture surface unchanged.

---

## Phase 4: User Story 2 — Доверять записи и управлять ею без риска (Priority: P1)

**Goal**: Make native recording action-first and always truthful without a surprise workspace-width change, while preserving permission recovery, titlebar HUD, Pause/Resume, and one-action Stop.

**Independent Test**: Across ready, permission-required, detected-meeting, starting, recording, paused, stopping, local-saved, cabinet-unavailable, and actionable-failure states, the accessibility tree exposes the right status and next action; recording start leaves the meeting width stable and Stop remains one action in the rail/titlebar.

### Tests for User Story 2

- [X] T010 [P] [US2] Add failing compact-rail Start/Stop, stable inspector disclosure, target-size, accessible-label, and Reduce Motion contract assertions in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`
- [X] T011 [P] [US2] Add failing native-authority, no-auto-expand-on-recording, actionable-problem expansion, and persistent titlebar Stop assertions in `apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift`
- [X] T012 [P] [US2] Add failing ready/permission/detected-meeting/recording/paused/stopping/local-saved/meter-visibility state assertions in `apps/macos/Shared/Tests/CaptureControlTests.swift`

### Implementation for User Story 2

- [X] T013 [US2] Pass direct start/transition eligibility into the native shell without changing capture prerequisites in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T014 [US2] Implement the direct compact-rail Start/Stop control, 304–312 pt intentional inspector, stable recording width, simplified `Запись` header, actionable expansion, accessible targets, and reduced-motion behavior in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- [X] T015 [US2] Present concise readiness, permission, transition, pause/resume, local-save, recovery, secondary microphone settings, and active-only meters in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [X] T016 [US2] Run the US2 Swift tests plus synthetic permission, detected-meeting, Start/Pause/Resume/Stop, finalizing, local-save, cabinet-unavailable, and actionable-failure runtime states at both target sizes; record truth/Stop evidence in `specs/104-essential-interface-polish/quickstart.md`

**Checkpoint**: User Story 2 remains independently valid even when the cabinet is unavailable.

---

## Phase 5: User Story 3 — Видеть человеческий интерфейс без отладочной информации (Priority: P1)

**Goal**: Replace generated titles, English durations, pipeline wording, terminal 100% meters, telemetry, internal processing names, local paths, and report tooling with human outcome/next-action presentation while keeping internal diagnostics safe.

**Independent Test**: Synthetic ordinary/failure data produces zero raw IDs, paths, registry/service/status keys, telemetry counters, internal processing names, generic report/copy-report actions, or terminal 100% bars; underlying metadata-only diagnostics and support submission still exist.

### Tests for User Story 3

- [X] T017 [P] [US3] Add failing presentation-only generated-title cases with and without trustworthy time, manual-upload IDs, filenames, Russian durations, user states, and active-only progress in `apps/server/tests/unit/test_cabinet_view_models.py` and `apps/server/tests/integration/test_cabinet_meeting_list.py`
- [X] T018 [P] [US3] Add failing ordinary-screen forbidden-copy and metadata-safety assertions in `apps/server/tests/contract/test_cabinet_no_secret_content_egress.py` and `apps/macos/Shared/Tests/CaptureControlTests.swift`

### Implementation for User Story 3

- [X] T019 [US3] Add presentation-only human title, safe filename cleanup, Russian duration, and user-result helpers without mutating stored meetings in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T020 [US3] Map terminal upload/degraded/failure states and active progress to human list results in `apps/server/src/twobrain_rec_server/cabinet/queries.py` and `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T021 [US3] Remove ordinary rendering of telemetry health, Apple/WebRTC internals, local paths, idle meters, and unconditional upload-support summaries while preserving recovery inputs in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [X] T022 [US3] Remove permanent trust/diagnostics cards and make local custody/support contextual in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift` and `apps/macos/RecApp/Sources/Upload/DesktopSupportIncidentActionStrip.swift`
- [X] T023 [US3] Run the US3 server/macOS tests and forbidden-copy searches, then record zero-debug and diagnostic-keep-boundary evidence in `specs/104-essential-interface-polish/quickstart.md`

**Checkpoint**: Ordinary UI is human; internal metadata-only diagnostics, redaction, and support services remain intact.

---

## Phase 6: User Story 4 — Получить цельный, красивый и доступный GRAF (Priority: P2)

**Goal**: Harmonize server/native density, typography, spacing, color, focus, responsiveness, long text, increased contrast, and brand distance at every supported window size.

**Independent Test**: All layout-sensitive rows of the 16-state matrix have no overlap/horizontal scroll at `1040×680`, `1280×760`, and a wider window; keyboard/VoiceOver order and labels remain meaningful after responsive collapse; matched visual comparison against `visual-target.md` finds no copied reference expression.

### Tests for User Story 4

- [X] T024 [P] [US4] Add failing CSS/DOM contracts for focus, target sizes, compact wordmark fallback, responsive sidebar/toolbar label collapse with preserved accessible names, visible date/upload/native rail, contextual hover-focus parity, and reduced motion in `apps/server/tests/contract/test_cabinet_frontend_foundation_contract.py` and `apps/server/tests/contract/test_cabinet_static_assets_contract.py`
- [X] T025 [P] [US4] Add failing native typography/spacing/target/accessibility and stable-width contracts in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift` and `apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift`

### Implementation for User Story 4

- [X] T026 [US4] Consolidate the existing GRAF dark tokens, 8/12/16/24 spacing, typography, focus, control sizes, subtle borders/selection, compact sidebar breakpoint, and increased-contrast/reduced-motion states in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T027 [US4] Align native rail/inspector typography, spacing, surfaces, labels, target sizes, increased contrast, and reduced motion with existing GRAF tokens in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift` and `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [X] T028 [US4] Run all 16 states from `specs/104-essential-interface-polish/visual-target.md` through the full viewport, long-text, keyboard, accessibility-tree, and matched before/after matrix; iterate spacing/alignment/radius/focus defects in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` and `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- [X] T029 [US4] Record metadata-safe accessibility and clean-room/brand-distance outcomes without private screenshots in `specs/104-essential-interface-polish/quickstart.md`

**Checkpoint**: User Story 4 meets the visual contract without introducing a light-theme engine or reference copy.

---

## Phase 7: User Story 5 — Убрать лишнее без скрытых поломок (Priority: P2)

**Goal**: Delete only code/selectors/branches whose sole purpose was removed UI, preserve shared safety behavior, and prevent disabled/debug surface elements from returning.

**Independent Test**: Negative source/DOM contracts exclude every approved removed surface element; supported navigation, search/filter/sort, upload, selection/delete, recording, permission, custody, support, and diagnostics infrastructure still pass focused tests.

### Tests for User Story 5

- [X] T030 [P] [US5] Add negative source/DOM assertions for removed sidebar placeholders, hard-coded plan/trial copy, unconditional calendar region, embedded app-download/onboarding and saved/download placeholders, duplicate decorative tools, trust/diagnostics cards, and unconditional report actions in `apps/server/tests/unit/test_cabinet_web_shell.py` and `apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift`

### Implementation for User Story 5

- [X] T031 [US5] Remove dead branches, selectors, state paths, view fragments, and parameters proven to serve only removed UI while preserving shared diagnostics/support services in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`, `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`, and `apps/macos/RecApp/Sources/Upload/DesktopSupportIncidentActionStrip.swift`
- [X] T032 [US5] Run negative scans, focused regression suites, and a source-diff review proving no new polling, list request, network call, capture-thread work, or background service; document each deleted cluster and its preserved alternative/safety boundary in `specs/104-essential-interface-polish/research.md`

**Checkpoint**: Removed UI cannot return through another current entry point and no unrelated cleanup is included.

---

## Phase 8: Polish, Validation, And Closeout

**Purpose**: Prove the integrated high-risk slice, create explicitly approved scoped commits after validation, and prepare a reviewable handoff without deploying automatically.

- [X] T033 Update Russian behavior/UX notes for feature 104 in `CHANGELOG.md`
- [X] T034 Run every focused command and the release app build from `specs/104-essential-interface-polish/quickstart.md`, recording exact results in that file
- [X] T035 Run `infra/scripts/ci-local.sh` and record the full repository-gate result in `specs/104-essential-interface-polish/quickstart.md`
- [X] T036 Complete the final all-16-state same-viewport GRAF before/after, selected Stitch-target, Krisp clean-room, private-content, control-target, contrast, focus, and one-action Stop review; record only metadata-safe findings in `specs/104-essential-interface-polish/quickstart.md`
- [X] T037 Reconcile completed checkboxes, GitHub issue evidence/status, UX checklist, remaining limitations, scoped commit evidence, and the no-deploy boundary in `specs/104-essential-interface-polish/tasks.md` and `specs/104-essential-interface-polish/checklists/ux.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** has no dependencies and protects the baseline.
- **Foundational Boundary (Phase 2)** depends on T001–T002 and introduces no new infrastructure.
- **US1 and US2** may begin after Phase 2 because they primarily touch server and native owners respectively.
- **US3** begins after the relevant US1/US2 tests and presentation entry points exist because it refines both owners’ copy/state output.
- **US4** begins after US1–US3 behavior is stable so visual/accessibility work audits the final information hierarchy.
- **US5** follows US1–US4 so deletion is evidence-based.
- **Polish/closeout** follows all desired user stories.

### User Story Dependencies

- **US1 (P1)**: Independently testable server-owned main workspace.
- **US2 (P1)**: Independently testable native capture surface; cabinet may be offline.
- **US3 (P1)**: Depends on the visible presentation entry points in US1/US2 but has an independent forbidden-copy/keep-boundary test.
- **US4 (P2)**: Depends on final US1–US3 hierarchy; independently testable through the viewport/accessibility/brand-distance matrix.
- **US5 (P2)**: Depends on approved remove decisions; independently testable through negative contracts plus preserved-path regressions.

### Within Each User Story

1. Add the named failing tests.
2. Confirm they fail for the intended missing behavior, not environment damage.
3. Implement the smallest existing-pattern diff.
4. Run the story’s focused tests and independent scenario.
5. Mark tasks `[X]` only after evidence is recorded.

### Parallel Opportunities

- T003 and T004 can run in parallel.
- T010, T011, and T012 can run in parallel.
- T017 and T018 can run in parallel.
- T024 and T025 can run in parallel.
- After baseline, US1 server work and US2 native work can proceed in parallel only when separate contributors avoid shared spec/evidence files.

## Parallel Examples

### User Story 1

```text
T003: navigation/sidebar contract tests
T004: list-toolbar/selection integration tests
```

### User Story 2

```text
T010: native accessibility/rail contracts
T011: WebView/native-authority boundary contracts
T012: capture-state presentation contracts
```

### User Story 3

```text
T017: server title/status/progress presentation tests
T018: server/native forbidden-copy and metadata-safety tests
```

## Implementation Strategy

### MVP First

The smallest independently useful slice is US1 after baseline: remove disabled/double navigation and make the meeting workspace readable. Because the user requested a complete main-window polish and native capture remains a product gate, implementation should then complete US2 and US3 before presenting the result as feature-ready.

### Incremental Delivery

1. Baseline and ownership boundary.
2. US1 server meeting workspace.
3. US2 native capture control.
4. US3 human/debug-free presentation.
5. US4 visual/accessibility convergence.
6. US5 evidence-backed deletion.
7. Full validation and handoff.

## Notes

- The user authorized scoped feature commits after validation; no task authorizes production deployment, release publication, installer replacement, or inclusion of unrelated worktree changes.
- Private runtime screenshots stay outside git; only synthetic or metadata-safe evidence may be committed.
- The four initially unrelated visible changes in
  `.specify/templates/checklist-template.md`,
  `.specify/templates/plan-template.md`, `AGENTS.md`, and
  `docs/agent-guidance/ponytail-upstream.md` were traced to local snapshot
  `4081ef18` (`Codex worktree snapshot: archive-cleanup`), reviewed as valid
  managed-guidance updates, and isolated in commit `a8f835ac`; they are not
  feature-104 implementation code.
- The generated Spec Kit worktree overlay remains hidden with `skip-worktree`
  by the repository bootstrap contract and is intentionally excluded from the
  feature diff.
- Apply the Ponytail ladder: delete proven noise, reuse existing helpers/native semantics, add no dependency, and avoid broad refactors.
- Implementation commit: `10abb936` (`feat(interface): завершить полировку главного окна`).
- Final native-state correction commit: `8dd1c409`
  (`fix(interface): завершить native state polish фичи 104`).
- Integration with current `origin/master` preserves feature 098's safe
  calendar context while rendering `Ближайшие` only for a real authorized
  future recurring occurrence; focused crossover suites pass `168` server and
  `149` macOS tests, and the post-resolution full gate passes `642` Swift tests,
  `1427` server tests, `4` skips, and `ContractValidation: PASS`.
- Post-PR review removed the last dead navigation/CSS states, fixed accepted-
  media title cleanup, filter counting, and compact embedded filter access;
  the focused regression set passes `105` tests and final dead-state scans find
  no remaining selectors or model branches.
- Follow-up review aligned grouped status filters with every row state carrying
  the same user-facing label and removed the collapsed sidebar footer from the
  tab order; the focused regression set passes `72` tests. Raw support-report
  copy remains intentionally hidden under FR-007 while the safe submission and
  retry path stays available.
- The next automated review closed four cross-surface boundaries: compact start
  respects calendar record prompts, actionable custody is not limited to the
  meeting-owner role, authoritative titles remain unchanged, and search matches
  the visible humanized title. Focused checks pass `76` macOS and `58` server
  tests. The final full gate passes `642` macOS and `1430`
  server tests with `4` skips and `ContractValidation: PASS`.
- The third automated review closed four additional regression boundaries:
  successful bulk deletion no longer restores focus into a hidden selection
  toolbar; public API status filters remain exact while web labels retain their
  grouped behavior; SQL search prefilters stored fields before access/media
  projection and only admits bounded display-title fallbacks when relevant;
  retention warnings remain visible even when no immediate button is required.
  Focused checks pass `30` server and `76` macOS tests, and a Chromium DOM
  exercise confirms focus returns to the visible list heading.
- A pre-existing calendar manual-sync timing assertion failed two loaded full
  suites by `5–28 ms`; profiling showed that it timed a cold app/client before
  the settings page a user must open to reach the action. The test-only fix now
  models that entry point while preserving the original `<2s` requirement, and
  the final full repository gate is green.
- T016, T028, and T036 are closed by combined metadata-safe evidence: the real
  GRAF shell was exercised unlocked for onboarding, compact/expanded idle,
  offline, and retry; the final production capture views were exercised in an
  isolated unlocked native host for the synthetic capture-state matrix; browser
  states cover both exact embedded target widths; stable 308 pt inspector
  geometry and a large-window active pass cover the native size invariant.
