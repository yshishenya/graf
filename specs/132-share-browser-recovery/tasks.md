# Tasks: Понятное состояние приглашения в браузере

**Input**: Design documents from `/specs/132-share-browser-recovery/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/browser-invitation-errors.md`, `quickstart.md`, security and UX
checklists

**Risk lane**: `high-risk-feature`; tests precede implementation and full local
CI is required before PR/closeout.

## Phase 1: Setup

**Purpose**: Reuse the existing invitation, cabinet and Problem Details paths.
No new dependency, service, migration or deployment topology is needed.

## Phase 2: Foundational test coverage

**Purpose**: Capture the browser/API response boundary before changing shared
error handling.

- [X] T001 [US1] Add contract assertions for HTML invitation-unavailable
  responses, safe copy, no raw token/state/content and private caching in
  `apps/server/tests/contract/test_browser_problem_responses.py`.
- [X] T002 [US2] Add contract assertions for explicit JSON, missing `Accept`,
  generic `Accept: */*` on invitation paths and the existing explicit-HTML
  protected `/meetings` browser navigation in
  `apps/server/tests/contract/test_browser_problem_responses.py`.
- [X] T003 [US1] Extend the external invitation integration matrix with valid
  first entry, replay, expired/revoked state and no-side-effect assertions in
  `apps/server/tests/integration/test_recording_share_public_link.py`.

**Checkpoint**: Tests describe the current defect and the required safe
browser/API split before runtime implementation.

## Phase 3: User Story 1 — Получатель видит понятный результат (Priority: P1)

**Goal**: Valid first entry remains unchanged; replayed or unavailable browser
invitation requests show a safe HTML page instead of a JSON file.

**Independent Test**: Run T001 and T003 in the focused PostgreSQL matrix and
verify HTML content type, safe unavailable copy and unchanged first-entry
result.

### Implementation for User Story 1

- [X] T004 [US1] Add the safe invitation-unavailable cabinet renderer and reuse
  the existing invitation template in
  `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and
  `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/share_invitation_content.html`.
- [X] T005 [US1] Route invalid, replayed, expired, revoked and recipient-
  mismatched browser invitation failures through the existing cabinet HTML
  response conventions in `apps/server/src/twobrain_rec_server/api/problems.py`,
  without changing invitation state transitions.

**Checkpoint**: A second browser submission no longer downloads JSON and cannot
create or broaden access.

## Phase 4: User Story 2 — API и защита совместимы (Priority: P1)

**Goal**: Explicit JSON callers keep Problem Details while email/browser
invitation navigation without a usable session follows the intended HTML GRAF
behavior.

**Independent Test**: Run T002 plus the focused API/auth checks and compare
status, content type and JSON fields for explicit API requests.

### Implementation for User Story 2

- [X] T006 [US2] Preserve the current Problem Details JSON path for explicit
  JSON requests, keep explicit-HTML protected browser navigation on the
  existing login redirect, and scope missing or generic `Accept` handling to
  invitation paths in `apps/server/src/twobrain_rec_server/api/problems.py`.
- [X] T007 [US2] Extend the contract assertions for auth/replay/RLS-safe
  boundaries and invitation page wording in
  `apps/server/tests/contract/test_recording_share_invitation_contract.py` and
  `apps/server/tests/contract/test_recording_share_ui_contract.py`.

**Checkpoint**: Browser and API consumers receive their intended format while
  exact-recipient, CSRF, session, grant, expiry, revoke and RLS protections are
  unchanged.

## Phase 5: Polish and validation

- [X] T008 [P] Update the Russian `[Unreleased]` `Fixed` entry in
  `CHANGELOG.md` and record the selected high-risk validation lane and evidence
  links in `specs/132-share-browser-recovery/quickstart.md`.
- [ ] T009 Run the focused quickstart, `git diff --check`, Python compile and
  targeted Ruff; then run `infra/scripts/ci-local.sh` and record metadata-only
  results in `specs/132-share-browser-recovery/quickstart.md`.
- [ ] T010 Reconcile task/issue/PR evidence and run the required Ponytail/code
  review before implementation closeout; keep production deployment behind the
  separate release approval gate.

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1**: No code setup is required.
- **Phase 2**: Starts immediately and blocks implementation until T001–T003
  capture the intended behavior.
- **Phase 3**: Depends on Phase 2; T004 precedes T005 where the renderer is
  consumed by shared error handling.
- **Phase 4**: Depends on T005 and extends the same response boundary.
- **Phase 5**: Depends on all implementation tasks and focused validation.

### User Story Dependencies

- **User Story 1 (P1)**: Independent after foundational tests; delivers the MVP
  browser recovery behavior.
- **User Story 2 (P1)**: Uses the same shared error boundary and must be
  validated with US1; it cannot weaken US1's one-time auth behavior.

### Parallel Opportunities

- T001 and T003 can be prepared in parallel only if they do not edit the same
  test file; T002 must follow T001 because both extend
  `test_browser_problem_responses.py`.
- T008 can run in parallel with final source review after implementation.

## Implementation Strategy

1. Write the regression tests first and confirm the current replay path exposes
   the JSON response.
2. Add one safe cabinet error surface and the narrowest response negotiation
   change.
3. Validate US1 independently, then validate API compatibility and browser
   login behavior for US2.
4. Run the full repository gate before requesting PR/merge or release work.

## Notes

- `[P]` is used only when tasks touch different files and have no dependency on
  incomplete work.
- No migration, dependency, email-count change or token replay exception is
  allowed by this slice.
