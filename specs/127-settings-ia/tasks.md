# Tasks: единая архитектура настроек

**Input**: Design documents from `/specs/127-settings-ia/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/settings-ui.md`, `quickstart.md`

**Risk lane**: high-risk UX/auth/privacy boundary. Tests are required before
implementation and repository CI is required before closeout.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish failing, focused checks for the new settings contract.

- [X] T001 [P] Add settings route/HTML contract tests in `apps/server/tests/contract/test_settings_ui_contract.py` covering overview target, category paths, semantic headings, scope labels and no-secret output.
- [X] T002 [P] Add account settings projection unit tests in `apps/server/tests/unit/test_settings_view_models.py` covering provider/device masking, status labels and current-device state.
- [X] T003 [P] Add browser and embedded settings flow tests in `apps/server/tests/integration/test_settings_ia_flow.py` covering overview, category routes, empty states and fixed return paths.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish one route and navigation contract before moving existing
settings surfaces into categories.

- [X] T004 Update `apps/server/tests/unit/test_cabinet_navigation_model.py` to assert browser and embedded global settings links target `/settings` and `/desktop/settings`.
- [X] T005 Add route and CSRF assertions for settings mutations in `apps/server/tests/contract/test_settings_ui_contract.py`, including workspace, provider-link, calendar and device actions.
- [X] T006 Add the fixed browser/embedded category route map and settings navigation view model in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`.
- [X] T007 Register the dedicated settings router in `apps/server/src/twobrain_rec_server/cabinet/web.py` and remove only the duplicated root settings handlers/imports from `apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py` and `apps/server/src/twobrain_rec_server/cabinet/web_routes/desktop.py`.

**Checkpoint**: Shared route ownership and global navigation are ready; no user
story page work starts before focused contract tests can resolve the new paths.

---

## Phase 3: User Story 1 - Найти нужную настройку (Priority: P1) 🎯 MVP

**Goal**: Open settings from the global menu, see a useful overview and reach
every supported category in browser and embedded desktop modes.

**Independent Test**: Run `test_settings_ui_contract.py` and
`test_settings_ia_flow.py` for overview, six canonical paths, semantic headings
and legacy calendar/provider links.

### Tests for User Story 1

- [X] T008 [US1] Make the new route tests fail first for overview/category navigation in `apps/server/tests/integration/test_settings_ia_flow.py`.

### Implementation for User Story 1

- [X] T009 [US1] Implement browser and embedded settings route handlers in `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py` with fixed overview/recording/summaries/workspace/account paths and no arbitrary redirect target.
- [X] T010 [US1] Add the shared settings inner navigation macro in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/settings_navigation.html` and pass its route context through `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/rendering_shared.py`.
- [X] T011 [US1] Replace the flat root cards with the overview/category entry layout in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_content.html`, including supported-category descriptions, scope labels and intentional unavailable/empty copy.
- [X] T012 [US1] Add shared semantic page title and settings layout styles in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`, preserving responsive embedded behavior and visible focus.
- [X] T013 [US1] Update `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/provider_link_settings.html` to use the shared settings navigation and canonical back links.

**Checkpoint**: Global settings entry and category discovery are independently
usable without knowing deep URLs.

---

## Phase 4: User Story 2 - Понять область действия и безопасно изменить настройку (Priority: P1)

**Goal**: Make scope, role, authorization, save/error states and safe auth data
visible before a user changes a setting.

**Independent Test**: Render owner/member, empty and failure fixtures; confirm
scope labels, disabled explanations, preserved values, CSRF and no-secret output.

### Tests for User Story 2

- [X] T014 [US2] Add owner/member, empty account and device-revoke contract scenarios in `apps/server/tests/contract/test_settings_ui_contract.py`.
- [X] T015 [US2] Add query/view-model tests for current-user/current-workspace filtering in `apps/server/tests/unit/test_settings_view_models.py`.

### Implementation for User Story 2

- [X] T016 [US2] Add safe account provider/device presentation models and bounded current-user queries in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/queries.py`.
- [X] T017 [US2] Implement account/security route context and device result handling in `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py`, reusing the existing authorization/audit path from `apps/server/src/twobrain_rec_server/api/auth.py`.
- [X] T018 [US2] Add the account/security page with linked-provider status, safe device metadata, confirmed revoke action and empty/unavailable states in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html`.
- [X] T019 [US2] Return provider-link confirmation to the account category and keep callback/error states safe in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/web_routes/provider_links.py`.
- [X] T020 [US2] Add dirty/save/error status hooks for grouped settings forms in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` and mark affected calendar forms in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`.
- [X] T021 [US2] Add fixed desktop/browser return aliases and scope-aware result copy for workspace activation and invitations in `apps/server/src/twobrain_rec_server/cabinet/web_routes/spaces.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_workspace_content.html`.

**Checkpoint**: Account, workspace and calendar mutations communicate scope and
recover without leaking or discarding sensitive/input data.

---

## Phase 5: User Story 3 - Управлять существующими категориями настроек (Priority: P1)

**Goal**: Give summaries, workspace/team and calendars their own coherent pages
while preserving existing domain contracts.

**Independent Test**: Open each category from the overview, exercise existing
summary/workspace/calendar actions, and confirm legacy routes still work.

### Tests for User Story 3

- [X] T022 [P] [US3] Add summary category render assertions for built-in/default versus personal formats in `apps/server/tests/contract/test_summary_template_ui_contract.py`.
- [X] T023 [P] [US3] Extend calendar settings contract coverage for shared navigation, semantic conflict information and form state hooks in `apps/server/tests/contract/test_calendar_settings_contract.py`.
- [X] T024 [P] [US3] Add workspace category render and return-path assertions in `apps/server/tests/contract/test_provider_link_settings_contract.py`.

### Implementation for User Story 3

- [X] T025 [US3] Move the existing summary template surface into `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_summaries_content.html` and render it from the summaries route without changing `/api/v1/cabinet/summary-templates` contracts.
- [X] T026 [US3] Move active-workspace and join-offer sections into `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_workspace_content.html` with translated roles, empty states and explicit owner scope.
- [X] T027 [US3] Keep the existing calendar information order and add settings category context, semantic headings and non-actionable conflict copy in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`.
- [X] T028 [US3] Update provider-link confirmation rendering to use category-level account context and safe recovery copy in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/provider_link_settings.html`.
- [X] T029 [US3] Reconcile `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py` and `apps/server/src/twobrain_rec_server/cabinet/web_routes/spaces.py` so existing result query strings return to the correct category in browser and desktop modes.

**Checkpoint**: Existing settings behavior is separated by user intent without
new provider, summary, calendar or workspace persistence behavior.

---

## Phase 6: User Story 4 - Понять, где находятся настройки записи (Priority: P2)

**Goal**: Make native recording scope discoverable without moving capture policy
into the web.

**Independent Test**: Open the recording category in browser and desktop modes;
confirm the handoff is honest, native-only and does not expose a global record
toggle or removed routing option.

- [X] T030 [US4] Add recording handoff route/render contract coverage in `apps/server/tests/contract/test_settings_ui_contract.py` and `apps/server/tests/integration/test_settings_ia_flow.py`.
- [X] T031 [US4] Add the native recording handoff page in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_recording_content.html` and wire it through `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py` and `apps/server/src/twobrain_rec_server/cabinet/rendering.py`.
- [X] T032 [US4] Review the existing native copy contract in `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift` and add/update only a source-level regression assertion if the web handoff wording requires it; do not change capture behavior.

**Checkpoint**: Recording discoverability is improved while capture remains
native, visible and target-scoped.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validate the complete high-risk UX slice and record release-ready
evidence.

- [X] T033 [P] Add opener-focus restoration and Escape/close regression assertions for calendar provider dialogs in `apps/server/tests/contract/test_calendar_settings_contract.py` and `apps/server/tests/contract/test_settings_ui_contract.py`.
- [X] T034 [P] Refine responsive settings layout, scope badges, status/error states and reduced-motion/focus styles in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.
- [X] T035 [P] Update `CHANGELOG.md` with the Russian settings IA/accessibility and compatibility entry under `[Unreleased]`.
- [X] T036 Run the focused commands from `specs/127-settings-ia/quickstart.md`, including `git diff --check`, and mark validated tasks `[X]` only after evidence is captured in the worktree.
- [X] T037 Run `infra/scripts/ci-local.sh` for the selected high-risk UX lane and record pass/fail evidence in the final handoff without committing private meeting content.

## Phase 8: Post-release embedded parity correction

**Purpose**: Close the discovered gap between the server-rendered embedded
settings IA and the macOS webview route allowlist.

- [X] T038 [US1] Allow the canonical `/desktop/settings` overview, category and
  existing settings mutation routes in
  `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`, keep
  desktop-header reinjection and protected-history behavior intact, and add
  focused route-policy tests in
  `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`,
  `apps/macos/Shared/Tests/DesktopCabinetNavigationRequestPolicyTests.swift`
  and `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`.
- [X] T039 Validate the embedded settings path in the installed macOS client,
  run the focused Swift tests and `infra/scripts/ci-local.sh`, then record the
  release/deploy evidence without changing native capture behavior.

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 creates failing focused checks and can start immediately.
- Phase 2 depends on Phase 1 and blocks all category implementation.
- US1 depends on Phase 2 and is the MVP for discoverability.
- US2 depends on US1's shared route/context contract because account/workspace
  pages use the common settings navigation.
- US3 depends on US1 and the shared mutation-state hooks from US2.
- US4 depends on US1 only and can be developed in parallel with US2/US3 after
  the shared shell exists.
- Polish depends on the desired user stories and all focused tests.

### User Story Dependencies

- **US1 (P1)**: No story dependency after foundational route/navigation work.
- **US2 (P1)**: Depends on US1 common shell; independently tests account/workspace
  scope and safe mutation behavior.
- **US3 (P1)**: Depends on US1 shell and US2 form-state contract; domain APIs
  remain independent.
- **US4 (P2)**: Depends only on US1 route map; no capture dependency.
- **T038** depends on the completed server-side route map and is required before
  the embedded parity smoke in **T039**.

### Parallel Opportunities

- T001, T002 and T003 can run in parallel because they create separate test files.
- T022, T023 and T024 can run in parallel after the common shell exists.
- T033, T034 and T035 can run in parallel after category behavior stabilizes.
- US4 can proceed in parallel with US2/US3 after T010/T011 are complete.

## Parallel Example: User Story 3

```text
T022: summary UI contract in apps/server/tests/contract/test_summary_template_ui_contract.py
T023: calendar UI contract in apps/server/tests/contract/test_calendar_settings_contract.py
T024: workspace/provider contract in apps/server/tests/contract/test_provider_link_settings_contract.py
```

## Implementation Strategy

### MVP First (US1)

1. Complete T001–T007 and confirm the failing tests describe the new contract.
2. Complete T009–T013.
3. Validate overview and category discovery independently with the focused
   quickstart scenarios before adding account/calendar polish.

### Incremental Delivery

1. Add US2 scope/auth safety and validate owner/member/empty/failure states.
2. Add US3 category-specific surfaces and preserve legacy routes.
3. Add US4 native recording handoff.
4. Run cross-cutting accessibility, changelog and repository validation.

### Notes

- `[P]` means different files and no dependency on an incomplete task.
- Every task includes an exact repository path and is traceable to a story or
  cross-cutting gate.
- Implementation commits require explicit user approval after validation.
