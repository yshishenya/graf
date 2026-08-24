# Tasks: Надёжная навигация кабинета

**Input**: Design documents from `/specs/198-fix-cabinet-navigation/`
**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/cabinet-navigation.md`, `quickstart.md`

## Phase 1: Setup

- [X] T001 Review the shared navigation controller and focused test surface in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` and `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift` against the feature contract.

---

## Phase 2: Foundational Tests

- [X] T002 [US1] Add focused regression coverage for duplicate current URLs and distinct back/forward candidate selection in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`.

**Checkpoint**: The new regression test expresses the failing duplicate-history
behavior before the controller implementation changes.

---

## Phase 3: User Story 1 - Вернуться на предыдущий экран (Priority: P1)

**Goal**: «Назад» skips current-URL duplicates while retaining route and session
boundaries.

**Independent Test**: The duplicate-history and existing safe fallback tests pass
and the installed-app calendar/billing smoke returns to a different URL.

### Implementation

- [X] T003 [US1] Update back history selection to ignore the current URL while preserving safe route, unsafe ledger, meeting-review, session-expiry, and fallback checks in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`.

**Checkpoint**: «Назад» never performs a no-op on a duplicate history item.

---

## Phase 4: User Story 2 - Вернуться вперёд после возврата (Priority: P1)

**Goal**: «Вперёд» selects the nearest safe distinct forward item and is
enabled only when that target exists.

**Independent Test**: The focused duplicate-history test passes and the
installed-app sequence A → B → Назад → Вперёд returns to B.

### Implementation

- [X] T004 [US2] Add shared forward history selection that skips duplicate current URLs, use the selected `WKBackForwardListItem` for navigation, and derive `canGoForward` from that target in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`.

**Checkpoint**: «Вперёд» is active after a valid back transition and never
launches an empty or duplicate transition.

---

## Phase 5: User Story 3 - Предсказуемо использовать остальные кнопки (Priority: P2)

**Goal**: The shared titlebar strip remains consistent and truthful across all
cabinet sections, with Home, Reload, loading, and accessibility behavior intact.

**Independent Test**: The quickstart route matrix and stable accessibility
identifier assertions pass for all four controls.

### Implementation and validation

- [X] T005 [US3] Preserve and extend focused assertions for Home, Reload, loading state, and stable navigation accessibility identifiers in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`.
- [X] T006 [US3] Record the user-facing navigation fix under `[Unreleased]` in `CHANGELOG.md`.

---

## Phase 6: Polish & Cross-Cutting Validation

- [X] T007 Run the feature scenarios and installed-GRAF smoke matrix from `specs/198-fix-cabinet-navigation/quickstart.md`, recording metadata-only results.
- [X] T008 Run `swift build --package-path apps/macos`, `swift test --package-path apps/macos --filter DesktopCabinetWorkspaceTests`, and `infra/scripts/ci-local.sh --fast`; record the selected `high-risk-feature` lane and results in closeout evidence.

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (T001) is a read-only review and precedes test work.
- Foundational tests (T002) precede the implementation tasks.
- User Story 1 (T003) precedes User Story 2 (T004) because both modify the same controller and the forward target reuses the distinct-history rule.
- User Story 3 (T005–T006) follows the behavior fix; validation (T007–T008) is last.

### Parallel Opportunities

- None for the controller implementation: T003 and T004 share one source file.
- T006 can be prepared independently after the behavior scope is confirmed, but it must be finalized with the implementation.
- T007 and T008 are separate validation commands but should be run sequentially when collecting evidence so the exact result and worktree state remain clear.

## Implementation Strategy

1. Complete T001 and write the failing focused regression in T002.
2. Implement the smallest shared back selection change in T003.
3. Reuse that rule for forward target selection and `go(to:)` in T004.
4. Preserve the existing titlebar surface, add only missing focused assertions,
   and update the changelog in T005–T006.
5. Run the route matrix, focused build/tests, and fast lane in T007–T008.

**MVP scope**: T001–T004 deliver the P1 navigation fix; T005–T008 are required
for the shared UX closeout and selected high-risk validation lane.
