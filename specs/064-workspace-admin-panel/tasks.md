# Tasks: Workspace Admin Panel

**Input**: Design documents from `specs/064-workspace-admin-panel/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Included because this is a high-risk admin/auth/privacy/deletion/Postgres/RLS feature.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks in the same phase when dependencies are satisfied.
- **[Story]**: Maps to a user story from `spec.md`.
- Every task includes an exact repository path.

## Phase 1: Setup (Shared Structure)

**Purpose**: Create the smallest admin package surface needed for later story work.

- [X] T001 Create `apps/server/src/twobrain_rec_server/admin/__init__.py`, `apps/server/src/twobrain_rec_server/admin/web.py`, `apps/server/src/twobrain_rec_server/api/admin.py`, `apps/server/src/twobrain_rec_server/admin/templates.py`, and `apps/server/src/twobrain_rec_server/admin/static/admin/admin.css`
- [X] T002 Create the admin template root with `apps/server/src/twobrain_rec_server/admin/templates/admin/base.html`; page templates are added by each user-story task under `apps/server/src/twobrain_rec_server/admin/templates/admin/`
- [X] T003 Register the admin API/web routers and admin static mount in `apps/server/src/twobrain_rec_server/main.py`
- [X] T004 [P] Create admin fixture helpers in `apps/server/tests/fixtures/admin.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared data, permission, audit, and safety primitives required by all stories.

**Critical**: No user story work should start until this phase is complete.

### Tests for Foundation

- [X] T005 [P] Add RLS and migration inventory contract coverage for admin tables in `apps/server/tests/contract/test_admin_rls_contract.py`
- [X] T006 [P] Add no-secret/no-content contract coverage for admin HTML/API/audit evidence in `apps/server/tests/contract/test_admin_no_secret_content_egress.py`
- [X] T007 [P] Add admin permission unit coverage for Owner/Admin/Member, cross-workspace, last-owner, and audit-unavailable decisions in `apps/server/tests/unit/test_admin_permissions.py`

### Implementation for Foundation

- [X] T008 Add `WorkspaceInvitation`, `WorkspaceQuotaPolicy`, `WorkspaceUsageDaily`, `UserUsageDaily`, and `AdminAuditEvent` models in `apps/server/src/twobrain_rec_server/db/models/admin.py`
- [X] T009 Export admin models from `apps/server/src/twobrain_rec_server/db/models/__init__.py`
- [X] T010 Add migration `apps/server/src/twobrain_rec_server/db/migrations/versions/0013_workspace_admin_panel.py` with admin tables, indexes, constraints, and RLS policies
- [X] T011 Implement shared admin permission decisions in `apps/server/src/twobrain_rec_server/admin/permissions.py`
- [X] T012 Implement metadata-only admin audit writer and fail-closed helpers in `apps/server/src/twobrain_rec_server/admin/audit.py`
- [X] T013 Implement shared admin template response helpers in `apps/server/src/twobrain_rec_server/admin/templates.py`
- [X] T014 Update RLS table inventory expectations in `apps/server/tests/fixtures/rls.py`

**Checkpoint**: Foundation ready; user story implementation can start.

---

## Phase 3: User Story 1 - Open Workspace Admin Overview (Priority: P1) MVP

**Goal**: Owner/Admin can open a workspace-scoped overview; Member and unauthenticated users are denied without admin data exposure.

**Independent Test**: Sign in as Owner, Admin, Member, and unauthenticated actor; only Owner/Admin see overview cards for their workspace.

### Tests for User Story 1

- [X] T015 [P] [US1] Add overview API contract tests in `apps/server/tests/contract/test_admin_api_contract.py`, browser admin route contract tests in `apps/server/tests/contract/test_admin_browser_contract.py`, and desktop admin handoff route-policy coverage in `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`
- [X] T016 [P] [US1] Add overview workspace access integration tests in `apps/server/tests/integration/test_admin_workspace_access.py`
- [X] T017 [P] [US1] Add overview navigation and shell unit tests in `apps/server/tests/unit/test_admin_overview_view_models.py`

### Implementation for User Story 1

- [X] T018 [US1] Implement overview queries for user counts, usage summary, file summary, metric freshness, and recent audit in `apps/server/src/twobrain_rec_server/admin/queries.py`
- [X] T019 [US1] Implement overview view models and navigation model in `apps/server/src/twobrain_rec_server/admin/view_models.py`
- [X] T020 [US1] Implement `GET /api/v1/admin/overview` in `apps/server/src/twobrain_rec_server/api/admin.py`
- [X] T021 [US1] Implement `/admin` browser route, access-denied behavior, and desktop handoff/blocking policy in `apps/server/src/twobrain_rec_server/admin/web.py` and `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`
- [X] T022 [US1] Implement overview template in `apps/server/src/twobrain_rec_server/admin/templates/admin/overview.html`
- [X] T023 [US1] Add overview styles for tables/cards/compact width in `apps/server/src/twobrain_rec_server/admin/static/admin/admin.css`

**Checkpoint**: User Story 1 is independently testable as the admin overview MVP.

---

## Phase 4: User Story 2 - Manage Workspace Users (Priority: P1)

**Goal**: Owner/Admin can review users, create/revoke invitations, manage allowed role/status changes, and inspect user detail with audit.

**Independent Test**: Create and complete an invite through allowed provider login; prove Admin can manage Members only and last Owner cannot be removed/downgraded/deactivated.

### Tests for User Story 2

- [X] T024 [P] [US2] Add invitation and membership contract tests in `apps/server/tests/contract/test_admin_api_contract.py`
- [X] T025 [P] [US2] Add user management integration tests in `apps/server/tests/integration/test_admin_user_management.py`
- [X] T026 [P] [US2] Add invitation state unit tests in `apps/server/tests/unit/test_admin_invitations.py`

### Implementation for User Story 2

- [X] T027 [US2] Implement invitation create/revoke/complete state logic in `apps/server/src/twobrain_rec_server/admin/invitations.py`
- [X] T028 [US2] Implement user list/detail and membership mutation queries in `apps/server/src/twobrain_rec_server/admin/users.py`
- [X] T029 [US2] Add user and invitation endpoints to `apps/server/src/twobrain_rec_server/api/admin.py`
- [X] T030 [US2] Integrate invitation completion with allowed provider login in `apps/server/src/twobrain_rec_server/auth/callbacks.py`
- [X] T031 [US2] Add users, user detail, invitation, and membership view models in `apps/server/src/twobrain_rec_server/admin/view_models.py`
- [X] T032 [US2] Implement users list and user detail routes in `apps/server/src/twobrain_rec_server/admin/web.py`
- [X] T033 [US2] Implement users templates in `apps/server/src/twobrain_rec_server/admin/templates/admin/users.html` and `apps/server/src/twobrain_rec_server/admin/templates/admin/user_detail.html`

**Checkpoint**: User Story 2 is independently testable after foundation and US1 navigation.

---

## Phase 5: User Story 3 - Govern User Files (Priority: P2)

**Goal**: Owner/Admin can find workspace files/meetings, open review, download/export allowed artifacts, and request whole-meeting deletion with truthful unavailable states.

**Independent Test**: Admin accesses a non-owned same-workspace meeting, cross-workspace access is denied, unavailable lifecycle states are truthful, and sensitive actions write metadata-only audit.

### Tests for User Story 3

- [X] T034 [P] [US3] Add admin file API contract tests in `apps/server/tests/contract/test_admin_api_contract.py`
- [X] T035 [P] [US3] Add admin file governance integration tests in `apps/server/tests/integration/test_admin_file_governance.py`
- [X] T036 [P] [US3] Add file access decision unit tests in `apps/server/tests/unit/test_admin_file_access.py`

### Implementation for User Story 3

- [X] T037 [US3] Implement admin file access decisions and cabinet/deletion service adapters in `apps/server/src/twobrain_rec_server/admin/files.py`
- [X] T038 [US3] Add files, review-access, download, export, deletion-request, and deletion-report endpoints to `apps/server/src/twobrain_rec_server/api/admin.py`
- [X] T039 [US3] Add file list/detail/deletion view models in `apps/server/src/twobrain_rec_server/admin/view_models.py`
- [X] T040 [US3] Implement file list/detail/deletion browser routes in `apps/server/src/twobrain_rec_server/admin/web.py`
- [X] T041 [US3] Implement file templates in `apps/server/src/twobrain_rec_server/admin/templates/admin/files.html` and `apps/server/src/twobrain_rec_server/admin/templates/admin/file_detail.html`

**Checkpoint**: User Story 3 is independently testable with seeded file/deletion fixtures.

---

## Phase 6: User Story 4 - Monitor Usage And Quotas (Priority: P2)

**Goal**: Owner/Admin can see read-only usage, quota policy state, top consumers, freshness, and quota risk without billing or limit editing.

**Independent Test**: Seed usage/quota data and prove totals reconcile to source-backed counts, missing policy is explicit, and no billing/editing controls appear.

### Tests for User Story 4

- [X] T042 [P] [US4] Add usage and quota unit tests in `apps/server/tests/unit/test_admin_usage_metrics.py`
- [X] T043 [P] [US4] Add usage and quota integration tests in `apps/server/tests/integration/test_admin_usage_metrics.py`

### Implementation for User Story 4

- [X] T044 [US4] Implement usage rollup and quota-risk logic in `apps/server/src/twobrain_rec_server/admin/usage.py`
- [X] T045 [US4] Add usage and quota-policy endpoints to `apps/server/src/twobrain_rec_server/api/admin.py`
- [X] T046 [US4] Add balance/usage view models in `apps/server/src/twobrain_rec_server/admin/view_models.py`
- [X] T047 [US4] Implement `/admin/balance` browser route in `apps/server/src/twobrain_rec_server/admin/web.py`
- [X] T048 [US4] Implement balance template in `apps/server/src/twobrain_rec_server/admin/templates/admin/balance.html`

**Checkpoint**: User Story 4 is independently testable with source-backed usage fixtures.

---

## Phase 7: User Story 5 - Analyze Product Metrics And Audit (Priority: P3)

**Goal**: Owner/Admin can inspect source-backed product metrics and one product audit journal with metadata-only details.

**Independent Test**: Seed known metric/audit events and prove displayed metrics have definitions/freshness/drill-down while audit filters stay metadata-only.

### Tests for User Story 5

- [X] T049 [P] [US5] Add metrics and audit contract tests in `apps/server/tests/contract/test_admin_api_contract.py`
- [X] T050 [P] [US5] Add audit journal integration tests in `apps/server/tests/integration/test_admin_audit_journal.py`
- [X] T051 [P] [US5] Add audit and metric view model unit tests in `apps/server/tests/unit/test_admin_audit_view_models.py`

### Implementation for User Story 5

- [X] T052 [US5] Implement source-backed metric definitions, freshness, and drill-down models in `apps/server/src/twobrain_rec_server/admin/metrics.py`
- [X] T053 [US5] Implement normalized product audit journal readers in `apps/server/src/twobrain_rec_server/admin/audit.py`
- [X] T054 [US5] Add metrics and audit endpoints to `apps/server/src/twobrain_rec_server/api/admin.py`
- [X] T055 [US5] Add metrics and audit view models in `apps/server/src/twobrain_rec_server/admin/view_models.py`
- [X] T056 [US5] Implement `/admin/metrics` and `/admin/audit` browser routes in `apps/server/src/twobrain_rec_server/admin/web.py`
- [X] T057 [US5] Implement metrics and audit templates in `apps/server/src/twobrain_rec_server/admin/templates/admin/metrics.html` and `apps/server/src/twobrain_rec_server/admin/templates/admin/audit.html`

**Checkpoint**: User Story 5 is independently testable with seeded metric and audit events.

---

## Phase 8: Polish And Cross-Cutting Validation

**Purpose**: Finish the high-risk slice without broadening v1 scope.

- [X] T058 [P] Run and check all 35 items in `specs/064-workspace-admin-panel/checklists/admin-risk.md`
- [X] T059 [P] Add Russian-first label, keyboard navigation, compact-width, destructive confirmation, and SC-008 workflow validation coverage in `apps/server/tests/contract/test_admin_browser_contract.py`
- [X] T060 [P] Update `[Unreleased]` in `CHANGELOG.md` for admin architecture, UX, QA, and operations changes
- [X] T061 Run the focused suite from `specs/064-workspace-admin-panel/quickstart.md`
- [X] T062 Run the canonical local gate `infra/scripts/ci-local.sh`
- [X] T063 Record validation evidence and remaining limitations in `specs/064-workspace-admin-panel/quickstart.md`

---

## Dependencies And Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 US1**: Depends on Phase 2.
- **Phase 4 US2**: Depends on Phase 2 and should reuse US1 navigation/shell when available.
- **Phase 5 US3**: Depends on Phase 2; can proceed after US1 shell is available.
- **Phase 6 US4**: Depends on Phase 2; can proceed after US1 shell is available.
- **Phase 7 US5**: Depends on Phase 2; benefits from US4 usage sources but remains independently testable with seeded data.
- **Phase 8 Polish**: Depends on completed target user stories.

### User Story Dependencies

- **US1 (P1)**: First MVP checkpoint after foundation.
- **US2 (P1)**: Same priority as US1; can be implemented after foundation, but uses the admin shell from US1 for browser navigation.
- **US3 (P2)**: Can be implemented after foundation and admin shell.
- **US4 (P2)**: Can be implemented after foundation and admin shell.
- **US5 (P3)**: Can be implemented after foundation; audit journal benefits from events created by US2-US4.

### Within Each User Story

- Tests come before implementation.
- Models and migrations come before services.
- Services come before API/web routes.
- Routes come before templates only when templates need concrete view models.
- Each story checkpoint should pass before expanding to the next story.

---

## Parallel Execution Examples

### User Story 1

```text
Task: T015 contract tests in apps/server/tests/contract/test_admin_api_contract.py, apps/server/tests/contract/test_admin_browser_contract.py, and apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift
Task: T016 integration tests in apps/server/tests/integration/test_admin_workspace_access.py
Task: T017 unit tests in apps/server/tests/unit/test_admin_overview_view_models.py
```

### User Story 2

```text
Task: T024 contract tests in apps/server/tests/contract/test_admin_api_contract.py
Task: T025 integration tests in apps/server/tests/integration/test_admin_user_management.py
Task: T026 unit tests in apps/server/tests/unit/test_admin_invitations.py
```

### User Story 3

```text
Task: T034 contract tests in apps/server/tests/contract/test_admin_api_contract.py
Task: T035 integration tests in apps/server/tests/integration/test_admin_file_governance.py
Task: T036 unit tests in apps/server/tests/unit/test_admin_file_access.py
```

### User Story 4

```text
Task: T042 unit tests in apps/server/tests/unit/test_admin_usage_metrics.py
Task: T043 integration tests in apps/server/tests/integration/test_admin_usage_metrics.py
```

### User Story 5

```text
Task: T049 contract tests in apps/server/tests/contract/test_admin_api_contract.py
Task: T050 integration tests in apps/server/tests/integration/test_admin_audit_journal.py
Task: T051 unit tests in apps/server/tests/unit/test_admin_audit_view_models.py
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1 overview).
3. Stop and validate the admin overview independently.

### Full V1

1. Complete US1 and US2 for the P1 admin core.
2. Add US3 and US4 for files and operational balance.
3. Add US5 for product metrics and audit.
4. Run Phase 8 before implementation closeout.
5. Workflow next steps before implementation are `$speckit-analyze`, then `$speckit-taskstoissues` after analyze is clean.

### Ponytail Guardrail

- Reuse existing auth, cabinet egress, deletion, RLS, and template patterns before adding new helpers.
- Do not add support, Analyst, billing, external log export, bulk actions, quota editing, or desktop-embedded admin UI.
- Add only the models and services required by the active story.
