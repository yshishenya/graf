# Tasks: Web Cabinet HTMX Shell

**Input**: Design documents from `specs/058-web-cabinet-htmx-shell/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/cabinet-shell-contract.md`, `quickstart.md`
**Tests**: Required. The feature explicitly requires independently verifiable migration steps, compatibility checks, desktop route policy checks, CSRF checks, viewport checks, and metadata-safe evidence.
**Organization**: Tasks are grouped by user story and ordered so each completed story remains independently testable.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add only the minimal stable dependencies and file structure needed for server-rendered templates, local static assets, and validation.

- [X] T001 Add `jinja2>=3.1.6,<4` to `apps/server/pyproject.toml` and refresh `apps/server/uv.lock`
- [X] T002 Create cabinet template directories under `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/`
- [X] T003 Create cabinet static asset directory under `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/`
- [X] T004 Vendor `htmx.org` 2.0.10 into `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/htmx-2.0.10.min.js`
- [X] T005 [P] Add static asset exclusion guard coverage in `apps/server/tests/contract/test_cabinet_frontend_foundation_contract.py`
- [X] T006 [P] Add template package smoke coverage in `apps/server/tests/unit/test_cabinet_template_components.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the reusable rendering, component, CSRF, and static asset foundation before any page migration.

**CRITICAL**: No user story page migration should begin until this phase is complete.

- [X] T007 Implement Jinja environment creation and template response helpers in `apps/server/src/twobrain_rec_server/cabinet/templates.py`
- [X] T008 Register cabinet static asset serving in `apps/server/src/twobrain_rec_server/main.py`
- [X] T009 Create cabinet base layout template in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/base.html`
- [X] T010 Create primitive component macros in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/primitives.html`
- [X] T011 Create composed section macros in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html`
- [X] T012 Create centralized icon macro using the existing Lucide-style SVG vocabulary in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/icons.html`
- [X] T013 Move cabinet visual tokens and semantic component classes into `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T014 Create bounded component behavior script in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T015 Add session-bound CSRF token generation and validation in `apps/server/src/twobrain_rec_server/auth/csrf.py`
- [X] T016 Wire CSRF dependency helpers into `apps/server/src/twobrain_rec_server/auth/dependencies.py`
- [X] T017 [P] Add CSRF contract tests in `apps/server/tests/contract/test_cabinet_csrf_contract.py`
- [X] T018 [P] Add full-page versus HTMX fragment contract tests in `apps/server/tests/contract/test_cabinet_shell_response_contract.py`
- [X] T019 [P] Add component state fixture data in `apps/server/tests/fixtures/cabinet_components.py`
- [X] T020 Update `apps/server/tests/unit/test_cabinet_web_shell.py` to assert templates, static links, icon macro output, and no inline monolithic CSS

**Checkpoint**: Jinja rendering, local static assets, component macros, icon macro, and CSRF helpers exist with failing or passing focused tests before page migration.

---

## Phase 3: User Story 4 - Use The Fixed Cabinet UI Foundation (Priority: P1) MVP Foundation

**Goal**: Lock the selected foundation: server-rendered reusable templates, one static CSS/token layer, local HTMX 2.x, centralized Lucide-style icons, and no Tailwind/UI-kit/client-app pipeline.

**Independent Test**: Run foundation contract tests and inspect rendered fixture pages to prove the cabinet has local assets only and no frontend build pipeline.

### Tests for User Story 4

- [X] T021 [P] [US4] Add forbidden frontend dependency assertions in `apps/server/tests/contract/test_cabinet_frontend_foundation_contract.py`
- [X] T022 [P] [US4] Add static asset and license/source assertions for local HTMX in `apps/server/tests/contract/test_cabinet_static_assets_contract.py`
- [X] T023 [P] [US4] Add component token/radius/focus baseline assertions in `apps/server/tests/unit/test_cabinet_template_components.py`

### Implementation for User Story 4

- [X] T024 [US4] Remove the monolithic inline `CSS` ownership from `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T025 [US4] Link `cabinet.css`, `cabinet.js`, and `htmx-2.0.10.min.js` through `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/base.html`
- [X] T026 [US4] Replace page-local icon markup with the centralized icon macro in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/icons.html`
- [X] T027 [US4] Add the static source guard command to `specs/058-web-cabinet-htmx-shell/quickstart.md`
- [X] T028 [US4] Record final stable dependency evidence in `specs/058-web-cabinet-htmx-shell/research.md`

**Checkpoint**: The fixed UI foundation is in place and future tasks cannot choose Tailwind, a ready UI kit, a SPA framework, CDN assets, or a frontend build pipeline inside 058.

---

## Phase 4: User Story 3 - Build A Reusable Atomic Cabinet System (Priority: P1)

**Goal**: Build the small product-owned component catalog that future cabinet pages reuse instead of adding more page-local markup.

**Independent Test**: Render component fixtures for at least twelve primitives and six composed sections across normal, focus, disabled, loading, selected, destructive, error, empty, and overflow states.

### Tests for User Story 3

- [X] T029 [P] [US3] Add primitive component coverage in `apps/server/tests/unit/test_cabinet_template_components.py`
- [X] T030 [P] [US3] Add composed section coverage in `apps/server/tests/unit/test_cabinet_template_sections.py`
- [X] T031 [US3] Add long Russian label and overflow assertions in `apps/server/tests/unit/test_cabinet_template_components.py`
- [X] T032 [P] [US3] Add metadata-safe component fixture assertions in `apps/server/tests/contract/test_cabinet_no_secret_content_egress.py`

### Implementation for User Story 3

- [X] T033 [US3] Implement button, icon button, link, input, select/filter, checkbox, chip/badge, tab, tooltip, loader, text treatment, and status label macros in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/primitives.html`
- [X] T034 [US3] Implement sidebar navigation, workspace/account header, meeting row, selection toolbar, playback controls, detail side panel, confirmation dialog, status banner, empty state, unavailable state, and auth form macros in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html`
- [X] T035 [US3] Add responsive, focus, disabled, selected, destructive, error, loading, and overflow styles to `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T036 [US3] Move common meeting list/detail display values into reusable view-model helpers in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T037 [US3] Document the component catalog and extension rules in `specs/058-web-cabinet-htmx-shell/contracts/cabinet-shell-contract.md`

**Checkpoint**: Common cabinet UI is reusable before list/detail/deletion pages move to templates.

---

## Phase 5: User Story 1 - Use One Online Cabinet Shell (Priority: P1)

**Goal**: Browser and desktop embedded cabinet routes share one online shell, navigation model, account/workspace presentation, active route state, and main content region.

**Independent Test**: Authenticated browser and desktop embedded list/detail routes render the same canonical online navigation model without duplicated native product menu logic.

### Tests for User Story 1

- [X] T038 [P] [US1] Update meeting list shell assertions in `apps/server/tests/integration/test_cabinet_meeting_list.py`
- [X] T039 [P] [US1] Update meeting detail shell assertions in `apps/server/tests/integration/test_cabinet_meeting_detail.py`
- [X] T040 [P] [US1] Add desktop embedded shell assertions in `apps/server/tests/integration/test_cabinet_web_access_states.py`
- [X] T041 [P] [US1] Add navigation model unit tests in `apps/server/tests/unit/test_cabinet_navigation_model.py`

### Implementation for User Story 1

- [X] T042 [US1] Add cabinet navigation view models in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T043 [US1] Create meeting list page template in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meetings.html`
- [X] T044 [US1] Create meeting detail page template in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail.html`
- [X] T045 [US1] Create desktop embedded page variants in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/desktop_meetings.html`
- [X] T046 [US1] Refactor list and detail route handlers in `apps/server/src/twobrain_rec_server/cabinet/web.py` to return template responses
- [X] T047 [US1] Remove native product sidebar duplication from `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- [X] T048 [US1] Keep native capture controls and shell chrome outside WebView in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`

**Checkpoint**: Existing list/detail URLs still work and share a single online cabinet shell in browser and desktop embedded mode.

---

## Phase 6: User Story 2 - Keep Offline Recording Native (Priority: P1)

**Goal**: Desktop users can still record locally when server/WebView is offline, while stale online navigation is hidden or bounded.

**Independent Test**: Simulate offline, timeout, not-configured, auth-expired, malformed, active-recording, stopping, and upload-queue states; native Stop and local truth remain reachable outside WebView.

### Tests for User Story 2

- [X] T049 [P] [US2] Add offline and unavailable workspace tests in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`
- [X] T050 [P] [US2] Add active recording WebView-boundary tests in `apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift`
- [X] T051 [P] [US2] Add login-not-ready cabinet state tests in `apps/macos/Shared/Tests/DesktopCabinetConfigurationTests.swift`

### Implementation for User Story 2

- [X] T052 [US2] Update desktop cabinet state transitions in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetState.swift`
- [X] T053 [US2] Update unavailable/offline UI handling in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`
- [X] T054 [US2] Preserve active recording Stop and status focus outside WebView in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- [X] T055 [US2] Keep local upload queue truth outside online cabinet navigation in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`

**Checkpoint**: Offline desktop behavior is truthful and local recording remains independent of the WebView.

---

## Phase 7: User Story 6 - Preserve Security, Privacy, And Lifecycle Truth (Priority: P1)

**Goal**: Preserve authorization, lifecycle, deletion, anti-forgery, egress, and metadata-safe evidence boundaries while rendering moves to templates.

**Independent Test**: Unauthenticated, expired-session, unauthorized, cross-site unsafe action, deleted/deleting, denied, and blocked-route scenarios fail closed without private content exposure.

### Tests for User Story 6

- [X] T056 [P] [US6] Add unsafe action CSRF integration tests in `apps/server/tests/integration/test_cabinet_csrf.py`
- [X] T057 [P] [US6] Extend access and lifecycle state coverage in `apps/server/tests/integration/test_cabinet_web_access_states.py`
- [X] T058 [P] [US6] Extend no-secret egress coverage for rendered templates in `apps/server/tests/contract/test_cabinet_no_secret_content_egress.py`
- [X] T059 [P] [US6] Extend OpenAPI drift assertions in `apps/server/tests/contract/test_openapi_contract_drift.py`
- [X] T060 [P] [US6] Add exact desktop route-kind tests in `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`

### Implementation for User Story 6

- [X] T061 [US6] Enforce CSRF validation on unsafe cabinet routes in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T062 [US6] Add CSRF hidden fields and HTMX header wiring in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html`
- [X] T063 [US6] Keep template inputs already-authorized by route handlers in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T064 [US6] Preserve egress and deletion lifecycle decisions outside templates in `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- [X] T065 [US6] Replace substring route policy with exact route-kind classification in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`
- [X] T066 [US6] Update navigation request/response policy integration in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetNavigationRequestPolicy.swift`

**Checkpoint**: Rendering refactor does not weaken cookie-session, tenant, deletion, lifecycle, route-policy, or evidence boundaries.

---

## Phase 8: User Story 5 - Use Progressive Server-Owned Interactions (Priority: P2)

**Goal**: Add bounded HTMX enhancement for list filtering, sorting, region refresh, and delete feedback without introducing a client application.

**Independent Test**: With enhanced requests, only approved fragments update and set `Vary: HX-Request`; without enhancement scripts, read-only list/detail routes still work as full pages.

### Tests for User Story 5

- [X] T067 [P] [US5] Add HTMX list/filter/sort fragment tests in `apps/server/tests/integration/test_cabinet_hx_fragments.py`
- [X] T068 [P] [US5] Add full-page fallback tests for list/detail routes in `apps/server/tests/integration/test_cabinet_meeting_list.py`
- [X] T069 [P] [US5] Add delete feedback fragment tests in `apps/server/tests/integration/test_cabinet_hx_delete_feedback.py`

### Implementation for User Story 5

- [X] T070 [US5] Add list fragment template in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_list.html`
- [X] T071 [US5] Add detail fragment template in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_detail.html`
- [X] T072 [US5] Add deletion feedback fragment template in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/deletion_feedback.html`
- [X] T073 [US5] Implement HX request detection and `Vary: HX-Request` handling in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T074 [US5] Add bounded HTMX attributes to list/filter/delete controls in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meetings.html`
- [X] T075 [US5] Keep browser-side state ephemeral in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`

**Checkpoint**: Enhanced cabinet interactions are server-owned, bounded by region, and have full-page fallbacks.

---

## Phase 9: User Story 7 - Support Maintainable Delivery And Verification (Priority: P2)

**Goal**: Keep the migration reversible, evidence-backed, and safe for normal product development.

**Independent Test**: Run the quickstart checks and confirm each migration step has focused validation, safe evidence, and rollback/safe-stop notes.

### Tests for User Story 7

- [X] T076 [P] [US7] Add runtime HTML check script in `specs/058-web-cabinet-htmx-shell/evidence/cabinet_runtime_check.py`
- [X] T077 [P] [US7] Add metadata-safe runtime evidence tests in `apps/server/tests/contract/test_cabinet_runtime_evidence_contract.py`
- [X] T078 [P] [US7] Add compatibility smoke coverage for legacy render helpers in `apps/server/tests/unit/test_cabinet_web_shell.py`

### Implementation for User Story 7

- [X] T079 [US7] Add safe-stop and rollback notes to `specs/058-web-cabinet-htmx-shell/quickstart.md`
- [X] T080 [US7] Update feature status and validation evidence links in `docs/current-product-status.md`
- [X] T081 [US7] Add behavior and architecture entry to `CHANGELOG.md`
- [X] T082 [US7] Record targeted server check result in `specs/058-web-cabinet-htmx-shell/evidence/server-checks.md`
- [X] T083 [US7] Record `swift test --package-path apps/macos --filter DesktopCabinet` result in `specs/058-web-cabinet-htmx-shell/evidence/desktop-checks.md`
- [X] T084 [US7] Record `infra/scripts/ci-local.sh` result in `specs/058-web-cabinet-htmx-shell/evidence/ci-local.md`

**Checkpoint**: The feature is ready for review with local proof and metadata-safe evidence.

---

## Phase 10: Analyze Follow-Ups

**Purpose**: Close the two non-blocking gaps found by the post-task analysis pass.

- [X] T085 [P] Add safe output encoding and trusted HTML guard coverage in `apps/server/tests/unit/test_cabinet_template_components.py`
- [X] T086 [P] Record product/design brand-distance review evidence in `specs/058-web-cabinet-htmx-shell/evidence/brand-distance-review.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1 and blocks all user story work.
- **US4 Fixed UI Foundation**: First story phase after foundation because it locks the technical baseline.
- **US3 Atomic Components**: Depends on US4 because components need the fixed CSS/icon/template foundation.
- **US1 Online Shell**: Depends on US3 because list/detail/auth pages must reuse components.
- **US2 Offline Native Boundary**: Depends on US1 enough to know which sidebar/menu logic moved into WebView; macOS tests may start earlier.
- **US6 Security And Privacy**: Depends on Phase 2 and should be completed before broad HTMX mutation work.
- **US5 Progressive Interactions**: Depends on US1 and US6.
- **US7 Delivery Verification**: Depends on the desired implementation scope.

### User Story Dependencies

- **US4 (P1)**: Can start after Phase 2.
- **US3 (P1)**: Starts after US4.
- **US1 (P1)**: Starts after US3.
- **US2 (P1)**: Can start after Phase 2 for tests, but final implementation should align with US1.
- **US6 (P1)**: Can start after Phase 2; should complete before US5 unsafe interactions.
- **US5 (P2)**: Starts after US1 and US6.
- **US7 (P2)**: Runs after each selected milestone and at final review.

### MVP Scope

1. Complete Phase 1 and Phase 2.
2. Complete US4 and US3 to establish the UI foundation and component catalog.
3. Complete the list/auth subset of US1.
4. Complete the CSRF/access subset of US6 before any unsafe mutation enhancement.
5. Stop and validate before migrating meeting detail, deletion report, and macOS sidebar ownership.

---

## Parallel Opportunities

- Phase 1 tasks T005 and T006 can run while T001-T004 are prepared.
- Phase 2 tests T017-T020 can be written in parallel after T007-T016 are sketched.
- US3 tests T029-T032 can run in parallel because they touch distinct assertions and fixtures.
- US1 tests T038-T041 can run in parallel because list, detail, desktop embedded, and navigation model coverage are separate.
- US2 tests T049-T051 can run in parallel with server-side US1 template work.
- US6 tests T056-T060 can run in parallel before implementation begins.
- US5 tests T067-T069 can run in parallel after fragment contract shape is agreed.
- US7 evidence/documentation tasks T076-T081 can run after the first implemented milestone.

## Parallel Example: User Story 3

```text
Task: "T029 [P] [US3] Add primitive component coverage in apps/server/tests/unit/test_cabinet_template_components.py"
Task: "T030 [P] [US3] Add composed section coverage in apps/server/tests/unit/test_cabinet_template_sections.py"
Task: "T031 [P] [US3] Add long Russian label and overflow assertions in apps/server/tests/unit/test_cabinet_template_components.py"
Task: "T032 [P] [US3] Add metadata-safe component fixture assertions in apps/server/tests/contract/test_cabinet_no_secret_content_egress.py"
```

## Parallel Example: User Story 6

```text
Task: "T056 [P] [US6] Add unsafe action CSRF integration tests in apps/server/tests/integration/test_cabinet_csrf.py"
Task: "T057 [P] [US6] Extend access and lifecycle state coverage in apps/server/tests/integration/test_cabinet_web_access_states.py"
Task: "T058 [P] [US6] Extend no-secret egress coverage for rendered templates in apps/server/tests/contract/test_cabinet_no_secret_content_egress.py"
Task: "T060 [P] [US6] Add exact desktop route-kind tests in apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift"
```

## Implementation Strategy

### Incremental Slice Order

1. Establish the test/contract foundation before moving rendering.
2. Move CSS, icons, and component macros before migrating pages.
3. Migrate meeting list and auth/unavailable states first.
4. Migrate meeting detail and deletion report after list shell proof.
5. Tighten desktop route policy and native/WebView ownership while server shell exists.
6. Add HTMX fragment behavior only after CSRF and full-page fallbacks are proven.
7. Run quickstart checks and `infra/scripts/ci-local.sh` before review.

### Safety Rules

- Keep current URLs working throughout migration.
- Do not change JSON API operation IDs or response models in this feature.
- Do not put database access, tenant selection, authorization, deletion lifecycle, or egress decisions in templates.
- Do not commit private meeting content, raw transcript text, signed URLs, object keys, local paths, credentials, or screenshots containing private content.
- Do not introduce Tailwind, ready UI kits, SPA frameworks, CDN UI assets, component preview apps, design-system packages, or frontend build pipelines in 058.

---

## Phase 11: Convergence

- [X] T087 Move actual meeting list, meeting detail, deletion report, and shared shell composition out of `apps/server/src/twobrain_rec_server/cabinet/web.py` into Jinja page/fragment templates and cabinet component macros so `web.py` remains only the route/data boundary per plan: Structure Decision (partial)
- [X] T088 Add an enforceable trusted-HTML guard and regression tests that limit `Markup(...)` and Jinja `|safe` usage to reviewed component-owned icon/fragment boundaries per FR-035 (partial)
- [X] T089 Replace disabled list filter/sort icon placeholders with accessible server-backed filter/sort controls that support bounded HTMX region updates and normal GET full-page fallback per FR-009 (partial)
- [X] T090 Wire selected-row delete UI to server-owned HTMX deletion feedback or region refresh, with bounded failure copy and full-page fallback, instead of fetch-only client-side row removal per FR-009 (partial)

## Phase 12: Convergence

- [X] T091 Move login, signup, and email-code page composition from `apps/server/src/twobrain_rec_server/cabinet/web.py` into Jinja auth templates under `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/auth/` using the existing cabinet component vocabulary per FR-010 (partial)
- [X] T092 Move auth code-entry, auth transition, list selection/delete dialog, detail tab, and playback DOM behavior from inline `<script>` helpers in `apps/server/src/twobrain_rec_server/cabinet/web.py` into `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, with regression coverage that keeps `web.py` free of inline page scripts per plan: Structure Decision (partial)
