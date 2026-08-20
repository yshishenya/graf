# Tasks: Стабильное подключение email в приложении

**Input**: Design documents from `specs/176-fix-email-link-route/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/embedded-navigation.md`, `quickstart.md`,
`checklists/requirements.md`, `checklists/security.md`, `checklists/ux.md`

**Risk lane**: `high-risk-feature`. Auth/navigation regression checks,
metadata-safe evidence, independent reviews and release integrity are mandatory.

## Phase 1: Regression contract

- [X] T001 [US1] Add a failing POST-to-GET replay regression plus stable GET and redirect-route assertions in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift` (FR-001–FR-004, FR-010; SC-001–SC-003)

**Checkpoint**: The focused test reproduces the production class of failure
without a real email, code, token, nonce or account identifier.

---

## Phase 2: User Stories 1 and 2 — сохранить экран кода и recovery (Priority: P1/P2)

**Goal**: Mutating embedded forms remain WebKit-owned; direct email-link
responses keep code/resend/back available until an explicit user action.

**Independent Test**: Run `DesktopCabinetWorkspaceTests`; settings email-link
POST is not trackable, direct start/verify responses remain transient, and an
ordinary final GET is trackable.

- [X] T002 [US1] [US2] Extend the existing request-identity predicate and its shared `trackPendingRoute` call in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` without changing auth/session/header behavior (FR-001–FR-008, FR-010–FR-011; SC-001–SC-003, SC-005)

---

## Phase 3: User Stories 2 and 3 — recovery и parity (Priority: P2)

### Recovery response contract

- [X] T003 [US2] Add focused 4xx/5xx email-link form-document regressions in `apps/macos/Shared/Tests/DesktopCabinetConfigurationTests.swift` and narrowly preserve those responses in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetNavigationResponsePolicy.swift` (FR-005–FR-008, FR-011; SC-004)

**Goal**: Server endpoints remain POST-only, desktop header reinjection remains
GET-only, and safe final document navigation still tracks normally.

**Independent Test**: Run the focused macOS policy tests and server account
contract test from `quickstart.md`.

- [X] T004 [US3] Run focused unchanged-contract checks for `apps/macos/Shared/Tests/DesktopCabinetNavigationRequestPolicyTests.swift` and `apps/server/tests/contract/test_account_routes.py`; change production files only if a check proves an in-scope regression (FR-007–FR-010; SC-004)

---

## Phase 4: Closeout and hotfix release

- [X] T005 [P] Add a simple Russian user-facing note to `CHANGELOG.md` and record metadata-only focused evidence in `specs/176-fix-email-link-route/evidence.md` (SC-001–SC-005)
- [ ] T006 Run correctness, auth/security, embedded UX and Ponytail reviews; fix actionable findings, rerun focused checks, run `infra/scripts/ci-local.sh --fast` once, then reconcile tasks/issues/evidence before commit, PR, merge and the approved signed/notarized production hotfix (FR-001–FR-011; SC-001–SC-005)

## Dependencies and execution order

- T001 must fail before T002 and pass after it.
- T002 and T003 both depend on T001's regression contract; they touch different
  policy owners and may then proceed independently.
- T004 depends on T002–T003.
- T005 may be drafted after focused checks while T004 evidence is collected.
- T006 starts only after T001–T005 pass and includes the release/deploy gate.

## Implementation strategy

1. Prove the replay class with one focused XCTest.
2. Reuse the existing predicate; add no new state machine, dependency or server fallback.
3. Validate the unchanged server and desktop-header contracts.
4. Run focused checks during iteration and one fast repository gate before PR.
5. Run full release checks only at the production hotfix boundary.
