# Tasks: Universal Cabinet Sidebar

**Input**: Design documents from `/specs/069-universal-sidebar/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/sidebar-shell-contract.md](./contracts/sidebar-shell-contract.md), [quickstart.md](./quickstart.md)

**Tests**: Tests are required because the selected lane is significant-feature / architecture and the feature changes shared user-facing cabinet layout, accessibility, embedded behavior, and fragment contracts.

**Organization**: Tasks are grouped by independently testable user story. Complete US1 first as the MVP, then US2, then US3.

## Pre-Implementation Notes

- 2026-06-28 before `apps/server` edits: working tree already had modified `AGENTS.md` from the active Spec Kit plan pointer and modified macOS files from the earlier native SwiftUI product sidebar cleanup (`apps/macos/RecApp/App/TwoBrainRecApp.swift`, `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`, and related `apps/macos/Shared/Tests/*` files). Preserve these changes and do not treat them as new server sidebar implementation churn.

## Phase 1: Setup

**Purpose**: Establish the active feature artifacts and baseline checks.

- [X] T001 Review the active 069 artifacts in specs/069-universal-sidebar/spec.md, specs/069-universal-sidebar/plan.md, specs/069-universal-sidebar/research.md, specs/069-universal-sidebar/data-model.md, specs/069-universal-sidebar/contracts/sidebar-shell-contract.md, and specs/069-universal-sidebar/quickstart.md
- [X] T002 Record the pre-existing unrelated dirty file state in specs/069-universal-sidebar/tasks.md before editing apps/server files, including AGENTS.md and apps/macos files

---

## Phase 2: Foundational

**Purpose**: Create the shared shell contract before page-specific user stories.

- [X] T003 [P] Add shared sidebar shell macro coverage in apps/server/tests/unit/test_cabinet_template_sections.py
- [X] T004 [P] Add shell contract assertions for one primary sidebar, navigation landmark label, exactly one current active destination, disabled state, and footer in apps/server/tests/unit/test_cabinet_web_shell.py
- [X] T005 Add the shared cabinet shell/sidebar macro in apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html
- [X] T006 Route _page_shell through the shared shell contract in apps/server/src/twobrain_rec_server/cabinet/rendering.py

**Checkpoint**: Shared shell contract exists and can be rendered without changing page content.

---

## Phase 3: User Story 1 - Consistent Cabinet Navigation (Priority: P1) MVP

**Goal**: Full browser cabinet pages share one sidebar structure while page content remains page-owned.

**Independent Test**: Render meetings list, meeting detail, deletion report, settings, and calendar settings full pages and verify one consistent sidebar contract with the correct active destination.

### Tests for User Story 1

- [X] T007 [P] [US1] Add browser full-page sidebar consistency tests for meetings, detail, deletion report, settings, calendar settings, and exactly one current destination in apps/server/tests/unit/test_cabinet_web_shell.py
- [X] T008 [P] [US1] Add route-level browser sidebar assertions for meeting list/detail in apps/server/tests/integration/test_cabinet_meeting_list.py and apps/server/tests/integration/test_cabinet_meeting_detail.py
- [X] T009 [P] [US1] Add browser calendar settings sidebar assertions in apps/server/tests/contract/test_calendar_settings_contract.py

### Implementation for User Story 1

- [X] T010 [US1] Replace page-owned sidebar markup in apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meetings.html with the shared shell contract
- [X] T011 [US1] Replace page-owned sidebar markup in apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/calendar_settings.html with the shared shell contract
- [X] T012 [US1] Preserve content-only includes for apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html, apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html, apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/deletion_report_content.html, and apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_content.html
- [X] T013 [US1] Run the US1 focused tests from apps/server/tests/unit/test_cabinet_template_sections.py, apps/server/tests/unit/test_cabinet_web_shell.py, apps/server/tests/integration/test_cabinet_meeting_list.py, apps/server/tests/integration/test_cabinet_meeting_detail.py, and apps/server/tests/contract/test_calendar_settings_contract.py

**Checkpoint**: Browser cabinet pages share one sidebar contract.

---

## Phase 4: User Story 2 - Same Navigation In Desktop Embedded App (Priority: P2)

**Goal**: Desktop embedded cabinet uses the same product navigation contract and no native desktop product sidebar.

**Independent Test**: Render desktop embedded meetings and settings routes and verify matching labels, adapted routes, compact rail contract, accessible names, and native boundary expectations.

### Tests for User Story 2

- [X] T014 [P] [US2] Add desktop embedded shared sidebar and compact rail assertions in apps/server/tests/unit/test_cabinet_web_shell.py
- [X] T015 [P] [US2] Add desktop embedded route assertions for meeting list/detail in apps/server/tests/integration/test_cabinet_meeting_list.py and apps/server/tests/integration/test_cabinet_meeting_detail.py
- [X] T016 [P] [US2] Add desktop embedded calendar settings assertions in apps/server/tests/contract/test_calendar_settings_contract.py
- [X] T017 [P] [US2] Preserve native product sidebar absence assertions in apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift

### Implementation for User Story 2

- [X] T018 [US2] Remove or keep absent native desktop product sidebar code in apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift and apps/macos/RecApp/App/TwoBrainRecApp.swift
- [X] T019 [US2] Ensure apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/desktop_meetings.html uses the shared shell contract without introducing separate embedded sidebar markup
- [X] T020 [US2] Preserve embedded route adaptation in apps/server/src/twobrain_rec_server/cabinet/view_models.py
- [X] T021 [US2] Preserve compact rail selectors and accessible toggle behavior in apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css and apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
- [X] T022 [US2] Run desktop embedded focused server tests and swift boundary test from specs/069-universal-sidebar/quickstart.md

**Checkpoint**: Desktop embedded cabinet navigation is web-owned and consistent with browser cabinet navigation.

---

## Phase 5: User Story 3 - Fragment Updates Do Not Duplicate Shell (Priority: P3)

**Goal**: Dynamic content updates preserve exactly one shared shell and one primary sidebar.

**Independent Test**: Request meeting list and settings fragments and verify responses contain content only, while full-page dynamic selection preserves one shell.

### Tests for User Story 3

- [X] T023 [P] [US3] Add fragment no-shell/no-sidebar assertions in apps/server/tests/integration/test_cabinet_hx_fragments.py
- [X] T024 [P] [US3] Add full-page dynamic selection shell-boundary assertions in apps/server/tests/unit/test_cabinet_web_shell.py

### Implementation for User Story 3

- [X] T025 [US3] Preserve fragment rendering paths in apps/server/src/twobrain_rec_server/cabinet/rendering.py so fragment helpers do not render the shared shell
- [X] T026 [US3] Preserve htmx selection and target boundaries in apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html and apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
- [X] T027 [US3] Run fragment focused tests from apps/server/tests/integration/test_cabinet_hx_fragments.py and apps/server/tests/unit/test_cabinet_web_shell.py

**Checkpoint**: Dynamic updates do not duplicate shell or sidebar.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and release-readiness notes.

- [X] T028 Update CHANGELOG.md under [Unreleased] for feature 069 shared cabinet sidebar architecture
- [X] T029 Run the full focused quickstart command in specs/069-universal-sidebar/quickstart.md
- [X] T030 Run infra/scripts/ci-local.sh before closeout/PR
- [X] T031 Record selected lane, validation evidence, and remaining limitations in specs/069-universal-sidebar/tasks.md

## Closeout Evidence

- Selected lane: significant-feature / architecture. Reason: shared user-facing cabinet layout, desktop embedded UX, accessibility state, fragment boundary, and native web/Swift ownership boundary changed.
- Spec review: repeated best-practice pass against Jinja template reuse, HTMX fragment targeting/selection, WAI navigation landmarks, MDN current-page state, and WCAG focus-visible guidance. Spec/contract/data model were tightened to require exactly one current enabled destination.
- Issue sync: `$speckit-taskstoissues` completed for T001-T031 using the project GitHub issue canon; `python3 .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py` passed with `github-issue-canon: OK (33 Spec Kit issue(s) checked)` before implementation.
- TDD proof: initial focused red tests failed for missing `sections.cabinet_shell` and disabled-active fallback; after implementation the same checks passed.
- Foundational validation: `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_cabinet_template_sections.py tests/unit/test_cabinet_navigation_model.py tests/unit/test_cabinet_web_shell.py` -> `34 passed, 1 warning`.
- US1 validation: `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_cabinet_template_sections.py tests/unit/test_cabinet_navigation_model.py tests/unit/test_cabinet_web_shell.py tests/integration/test_cabinet_meeting_list.py tests/integration/test_cabinet_meeting_detail.py tests/contract/test_calendar_settings_contract.py` -> `66 passed, 1 warning`; content-only template grep for shell/sidebar markers returned no matches.
- US2 validation: embedded server focused checks -> `8 passed, 1 warning`; rail CSS/JS checks -> `4 passed, 1 warning`; `swift test --package-path apps/macos --filter DesktopMeetingShellWebViewBoundaryTests --disable-swift-testing` -> `7 tests, 0 failures`; production macOS shell grep for removed native product sidebar symbols returned no matches.
- US3 validation: `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_cabinet_hx_fragments.py tests/unit/test_cabinet_web_shell.py::test_meeting_list_dynamic_selection_keeps_one_shell_boundary tests/contract/test_calendar_settings_contract.py::test_calendar_settings_hx_route_returns_fragment_without_shell` -> `7 passed, 1 warning`.
- Full focused quickstart: `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_cabinet_template_sections.py tests/unit/test_cabinet_navigation_model.py tests/unit/test_cabinet_web_shell.py tests/contract/test_cabinet_contract.py tests/contract/test_calendar_settings_contract.py tests/integration/test_cabinet_meeting_list.py tests/integration/test_cabinet_meeting_detail.py tests/integration/test_cabinet_hx_fragments.py` -> `79 passed, 1 warning`.
- Local CI: `infra/scripts/ci-local.sh` -> `ci_local_result=pass`; server tests `987 passed, 4 skipped, 148 warnings`; server lint passed; Python compile passed; deployment evidence scan passed. The RLS hardening sub-check reported `rls_validation_result=blocked` with `reason=postgres_test_database_required`, but the canonical local CI gate completed with pass.
- Remaining limitations: no production deploy or smoke was requested/run; no screenshot/manual browser QA was run in this implementation turn; admin/auth navigation remains intentionally out of scope; full macOS suite was not rerun here beyond the desktop shell boundary filter.

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 Setup has no dependencies.
- Phase 2 Foundational depends on Phase 1 and blocks all user stories.
- US1 depends on Phase 2 and is the MVP.
- US2 depends on Phase 2 and can proceed after or alongside US1 once shared shell tests are in place.
- US3 depends on Phase 2 and should run after US1 shell adoption to validate fragment boundaries.
- Phase 6 depends on selected user stories being complete.

### User Story Dependencies

- US1: independent after shared shell foundation.
- US2: independent after shared shell foundation, with native boundary validation.
- US3: independent after shared shell foundation, but most valuable after at least one full page uses the shared shell.

## Parallel Execution Examples

- T003, T004 can run in parallel because they touch different test files.
- T007, T008, T009 can run in parallel before US1 implementation.
- T014, T015, T016, T017 can run in parallel before US2 implementation.
- T023, T024 can run in parallel before US3 implementation.

## Implementation Strategy

1. Complete Phase 2 and US1 first to ship the MVP: browser cabinet pages use one shared sidebar contract.
2. Add US2 to prove desktop embedded parity and native product navigation boundary.
3. Add US3 to harden dynamic update behavior.
4. Run focused quickstart and repository closeout gate before PR.
