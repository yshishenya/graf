# Tasks: Access, Sharing, And Downloads

**Input**: Design documents from `specs/017-access-sharing-downloads/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Included before implementation because this feature touches auth, access, audit, artifact egress, and launch-readiness gates.

**Organization**: Tasks are grouped by user story so each increment can be independently implemented, validated, reviewed, and closed.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel when touching different files with no dependency on incomplete tasks.
- **[Story]**: Maps to the user stories in `spec.md`.
- Every task includes an exact repository path.

## Phase 1: Setup

**Purpose**: Add the feature scaffolding needed by all stories without changing behavior yet.

- [ ] T001 Create access policy module skeleton in `apps/server/src/twobrain_rec_server/cabinet/access.py`
- [ ] T002 [P] Create artifact egress module skeleton in `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- [ ] T003 [P] Create shared access/egress test fixtures in `apps/server/tests/fixtures/cabinet_access.py`

---

## Phase 2: Foundational

**Purpose**: Shared persistence, schemas, and redaction-safe audit plumbing that block all user stories.

- [ ] T004 Add meeting access, artifact policy, egress audit, and export package SQLAlchemy models in `apps/server/src/twobrain_rec_server/db/models/meeting_access.py`
- [ ] T005 Export meeting access models from `apps/server/src/twobrain_rec_server/db/models/__init__.py`
- [ ] T006 Create access/sharing/downloads migration in `apps/server/src/twobrain_rec_server/db/migrations/versions/0006_access_sharing_downloads.py`
- [ ] T007 Add access/share/artifact/export Pydantic schemas in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [ ] T008 Implement metadata-only egress audit persistence and redaction helpers in `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- [ ] T009 [P] Add migration/model coverage in `apps/server/tests/integration/test_access_sharing_downloads_migrations.py`
- [ ] T010 [P] Add schema no-secret contract coverage in `apps/server/tests/contract/test_access_sharing_no_secret_egress.py`

**Checkpoint**: Shared access/egress entities, schema contracts, and audit helper are ready before story work starts.

---

## Phase 3: User Story 1 - Govern Meeting Access (Priority: P1) MVP

**Goal**: Owners, team-visible reviewers, explicitly shared reviewers, and unrelated users see correct list/detail outcomes without content leaks.

**Independent Test**: Seed owner, team, shared, revoked, and unrelated users; validate list/detail access states and privacy-preserving denial.

### Tests for User Story 1

- [ ] T011 [P] [US1] Add access-state contract tests in `apps/server/tests/contract/test_access_sharing_downloads_contract.py`
- [ ] T012 [P] [US1] Add owner/team/shared/denied integration tests in `apps/server/tests/integration/test_meeting_access_policy.py`

### Implementation for User Story 1

- [ ] T013 [US1] Implement effective access decisions in `apps/server/src/twobrain_rec_server/cabinet/access.py`
- [ ] T014 [US1] Update cabinet list/detail queries to accept viewer context and filter by effective access in `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [ ] T015 [US1] Pass principal and device context through cabinet API routes in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [ ] T016 [US1] Map access states and governance labels into cabinet view models in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [ ] T017 [US1] Render owner/team/shared/denied access states in cabinet web routes in `apps/server/src/twobrain_rec_server/cabinet/web.py`

**Checkpoint**: User Story 1 is independently functional and protects list/detail access before sharing or egress is enabled.

---

## Phase 4: User Story 2 - Share A Login-Required Meeting Link (Priority: P1)

**Goal**: Owners/admins can grant and revoke login-required access for authenticated users, and recipients can open only while access remains active.

**Independent Test**: Grant access, open authenticated share link, revoke access, and verify the recipient loses access after refresh/retry with audit evidence.

### Tests for User Story 2

- [ ] T018 [P] [US2] Add share grant/revoke API contract tests in `apps/server/tests/contract/test_access_sharing_downloads_contract.py`
- [ ] T019 [P] [US2] Add share link integration tests in `apps/server/tests/integration/test_meeting_share_links.py`

### Implementation for User Story 2

- [ ] T020 [US2] Implement share grant, duplicate-access, revoke, and share-link resolution services in `apps/server/src/twobrain_rec_server/cabinet/access.py`
- [ ] T021 [US2] Add share grant, revoke, and login-required share-link routes in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [ ] T022 [US2] Add share panel state mapping for active grants, team visibility, public-link disabled state, and audit-failure state in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [ ] T023 [US2] Render share modal/drawer and login-required copy in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [ ] T024 [US2] Persist metadata-only share grant/revoke/open audit events before share state changes in `apps/server/src/twobrain_rec_server/cabinet/egress.py`

**Checkpoint**: User Story 2 is independently functional and all share actions are login-required, revocable, and audited.

---

## Phase 5: User Story 3 - Download Permitted Artifacts (Priority: P2)

**Goal**: Permitted reviewers can download only policy-allowed artifacts through server-mediated routes with direct-route re-checks and audit evidence.

**Independent Test**: Configure audio/transcript/summary policy combinations, attempt allowed and denied direct downloads, and verify safe UI states plus metadata-only audit.

### Tests for User Story 3

- [ ] T025 [P] [US3] Add download and no-secret contract tests in `apps/server/tests/contract/test_access_sharing_downloads_contract.py`
- [ ] T026 [P] [US3] Add artifact egress policy integration tests in `apps/server/tests/integration/test_artifact_egress_policy.py`
- [ ] T027 [P] [US3] Add artifact egress view-model and audit-fail-closed unit tests in `apps/server/tests/unit/test_artifact_egress_view_models.py`

### Implementation for User Story 3

- [ ] T028 [US3] Implement artifact policy resolution and lifecycle state decisions in `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- [ ] T029 [US3] Add server-mediated artifact download routes with authorization and audit-before-egress in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [ ] T030 [US3] Map audio/transcript/summary egress states into governance actions in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [ ] T031 [US3] Render download states, disabled reasons, and deletion-truth copy in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [ ] T032 [US3] Add direct-route denial and no-storage-key assertions to `apps/server/tests/contract/test_access_sharing_no_secret_egress.py`

**Checkpoint**: User Story 3 is independently functional and direct artifact egress cannot bypass current policy.

---

## Phase 6: User Story 4 - Export A Safe Meeting Package (Priority: P2)

**Goal**: Owners or permitted reviewers can create a policy-filtered meeting package that includes only allowed artifacts and records egress truth.

**Independent Test**: Request an allowed export, verify included/excluded artifact classes, deny policy-blocked packages, and confirm audit evidence.

### Tests for User Story 4

- [ ] T033 [P] [US4] Add export package contract tests in `apps/server/tests/contract/test_access_sharing_downloads_contract.py`
- [ ] T034 [P] [US4] Add export package integration tests in `apps/server/tests/integration/test_artifact_egress_policy.py`
- [ ] T035 [P] [US4] Add export manifest no-secret unit tests in `apps/server/tests/unit/test_artifact_egress_audit.py`

### Implementation for User Story 4

- [ ] T036 [US4] Implement policy-filtered export package builder and manifest generation in `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- [ ] T037 [US4] Add export create and export download routes with audit-before-egress in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [ ] T038 [US4] Map package export states and included/excluded artifact classes in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [ ] T039 [US4] Render export package states and post-egress deletion truth in `apps/server/src/twobrain_rec_server/cabinet/web.py`

**Checkpoint**: User Story 4 is independently functional and packages are policy-filtered, auditable, and no-secret.

---

## Phase 7: Polish & Cross-Cutting

**Purpose**: Evidence, documentation, release-readiness, and full validation across all stories.

- [ ] T040 [P] Update feature status and launch-readiness notes in `docs/current-product-status.md`
- [ ] T041 [P] Add Unreleased changelog entry for feature 017 in `CHANGELOG.md`
- [ ] T042 [P] Add sanitized screenshot/evidence index in `docs/evidence/017-access-sharing-downloads/README.md`
- [ ] T043 Run focused quickstart validation and record commands/results in `docs/evidence/017-access-sharing-downloads/README.md`
- [ ] T044 Run `./infra/scripts/ci-local.sh` and record the result in `docs/evidence/017-access-sharing-downloads/README.md`
- [ ] T045 Review tracked evidence for private content, credentials, signed URLs, object keys, and local paths in `docs/evidence/017-access-sharing-downloads/README.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on setup and blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on foundational access/schema/persistence.
- **User Story 2 (Phase 4)**: Depends on User Story 1 access decisions.
- **User Story 3 (Phase 5)**: Depends on User Story 1 access decisions and foundational egress audit.
- **User Story 4 (Phase 6)**: Depends on User Story 3 egress policy and audit behavior.
- **Polish (Phase 7)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 Govern Meeting Access**: MVP gate. Must complete before share/download/export.
- **US2 Share Login-Required Link**: Depends on US1 to avoid granting access around missing policy.
- **US3 Download Permitted Artifacts**: Depends on US1 and foundational audit.
- **US4 Export Safe Package**: Depends on US3 artifact policy and egress helpers.

### Parallel Opportunities

- T002 and T003 can run in parallel after T001.
- T009 and T010 can run in parallel with schema/model work after draft models exist.
- US1 tests T011 and T012 can run in parallel before US1 implementation.
- US2 tests T018 and T019 can run in parallel.
- US3 tests T025, T026, and T027 can run in parallel.
- US4 tests T033, T034, and T035 can run in parallel.
- Polish documentation tasks T040, T041, and T042 can run in parallel after implementation evidence exists.

## Parallel Examples

### User Story 1

```text
Task: "T011 [US1] Add access-state contract tests in apps/server/tests/contract/test_access_sharing_downloads_contract.py"
Task: "T012 [US1] Add owner/team/shared/denied integration tests in apps/server/tests/integration/test_meeting_access_policy.py"
```

### User Story 3

```text
Task: "T025 [US3] Add download and no-secret contract tests in apps/server/tests/contract/test_access_sharing_downloads_contract.py"
Task: "T026 [US3] Add artifact egress policy integration tests in apps/server/tests/integration/test_artifact_egress_policy.py"
Task: "T027 [US3] Add artifact egress view-model and audit-fail-closed unit tests in apps/server/tests/unit/test_artifact_egress_view_models.py"
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational phases.
2. Complete US1 access governance and validate list/detail denial behavior.
3. Complete US2 login-required sharing and validate grant/revoke/auth flow.
4. Stop for review if launch scope should exclude downloads/exports.

### Full 017 Scope

1. Complete US1 and US2 P1 collaboration gates.
2. Complete US3 downloads with server-mediated egress.
3. Complete US4 package export using the same policy/audit model.
4. Finish evidence, changelog, current status, focused validation, full local CI, and screenshot review.

### Quality Rules

- Tests for each story come before implementation and should fail before the story code is added.
- Do not start implementation while `$speckit-analyze` reports critical blockers.
- Do not broaden into public links, deletion execution, retention jobs, external invitations, or desktop-owned policy.
- Keep generated screenshots and evidence synthetic and no-secret.
