# Tasks: Встроенные тарифы и оплата

## Phase 1: Setup

- [X] T001 Review embedded billing contract and current route callers in `specs/149-embedded-billing/` and `apps/macos/RecApp/Sources/Cabinet/`

## Phase 2: User Story 1 — billing inside GRAF

- [X] T002 [P] [US1] Update billing route ownership and reasons in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`
- [X] T003 [P] [US1] Include billing in desktop session-header navigation in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetNavigationRequestPolicy.swift`
- [X] T004 [US1] Remove billing branch that opens `NSWorkspace.shared` from `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`
- [X] T005 [P] [US1] Update route and state regression tests in `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift` and `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`

## Phase 3: User Story 2 — safe payment provider navigation

- [X] T006 [US2] Add a narrow client-side HTTPS YooKassa allowlist check for checkout navigation in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`
- [X] T007 [P] [US2] Add focused provider and no-browser regression tests in `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`

## Phase 4: Polish and validation

- [X] T008 [P] Update `CHANGELOG.md` and release evidence notes for the embedded billing behavior.
- [X] T009 Run quickstart, focused tests, `infra/scripts/ci-local.sh --fast`, and record the selected high-risk validation lane.
