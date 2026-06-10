# Tasks: Provider-Neutral Federated Auth Foundation

**Input**: Design documents from `specs/013-federated-auth-foundation/`

**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/`

**Tests**: High-risk auth flow. Unit, contract, and integration tests are required for each user story.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 [P] Create dedicated auth feature directory scaffold in `apps/server/src/twobrain_rec_server/auth/providers/` and `apps/server/src/twobrain_rec_server/api/`
- [X] T002 Create server-side provider adapter package structure in `apps/server/src/twobrain_rec_server/auth/providers/base.py`, `apps/server/src/twobrain_rec_server/auth/providers/yandex.py`, `apps/server/src/twobrain_rec_server/auth/providers/vk.py`, `apps/server/src/twobrain_rec_server/auth/providers/telegram.py`, and `apps/server/src/twobrain_rec_server/auth/providers/__init__.py`
- [X] T003 Create reusable auth service entry points in `apps/server/src/twobrain_rec_server/auth/callbacks.py`, `apps/server/src/twobrain_rec_server/auth/sessions.py`, `apps/server/src/twobrain_rec_server/auth/links.py`, and `apps/server/src/twobrain_rec_server/auth/__init__.py`
- [X] T004 Add auth test scaffolding directories `apps/server/tests/contract/` and `apps/server/tests/integration/` helper modules for fake providers in `apps/server/tests/fakes/auth_providers.py`
- [X] T005 Capture unresolved dependencies and follow-up notes in `specs/013-federated-auth-foundation/checklists/security.md`, `specs/013-federated-auth-foundation/checklists/infra.md`, and `specs/013-federated-auth-foundation/checklists/ux.md`
- [X] T006 Update `docs/current-product-status.md` and `docs/prd-voice-layer-final.md` status block for 013 feature ownership and boundaries before code start

---

## Phase 2: Foundational (Blocking Prerequisites)

**Critical**: No user story work should begin until phase 2 is complete.

- [X] T007 Extend auth request context to carry auth-session identity while preserving legacy headers in `apps/server/src/twobrain_rec_server/auth/context.py`
- [X] T008 [P] Extend device context to include session-bound trust signals in `apps/server/src/twobrain_rec_server/auth/context.py`
- [X] T009 Extend bearer/session dependency behavior with graceful fallback to legacy header-based auth in `apps/server/src/twobrain_rec_server/auth/dependencies.py`
- [X] T010 [P] Add provider auth settings and OAuth callback URLs in `apps/server/src/twobrain_rec_server/config.py` and `apps/server/.env.example`
- [X] T011 Add provider credential source fields (env file paths + safe placeholders) in `apps/server/src/twobrain_rec_server/config.py`
- [X] T012 Add RU-local policy and provider allow-list model wiring in `apps/server/src/twobrain_rec_server/db/models/federated_auth.py`
- [X] T013 Add new auth entities in `apps/server/src/twobrain_rec_server/db/models/federated_auth.py`: `external_identities`, `workspace_auth_policies`, `auth_sessions`, `auth_session_device_bindings`, `workspace_provider_link_states`, `auth_callback_states`, `workspace_consent_copy`
- [X] T014 Export new auth entities from `apps/server/src/twobrain_rec_server/db/models/__init__.py`
- [X] T015 Add migration for 013 auth schema in `apps/server/src/twobrain_rec_server/db/migrations/versions/0003_federated_auth_foundation.py`
- [X] T016 Add callback state and session security helpers (single-use state hashing, expiry, nonce generation) in `apps/server/src/twobrain_rec_server/auth/sessions.py`
- [X] T017 Add canonical auth audit model and events in `apps/server/src/twobrain_rec_server/auth/audit.py`
- [X] T018 Expand redaction policy for auth-related fields in `apps/server/src/twobrain_rec_server/observability/redaction.py`
- [X] T019 [P] Add failure code constants and deterministic problem mapping in `apps/server/src/twobrain_rec_server/api/problems.py` and `apps/server/src/twobrain_rec_server/api/auth.py`
- [X] T020 Add reusable provider policy service utilities in `apps/server/src/twobrain_rec_server/auth/policy.py`
- [X] T021 Add auth provider fixture setup helpers in `apps/server/tests/fakes/auth_providers.py`

---

## Phase 3: User Story 1 - One-Click Auth in Russian Workspace (Priority: P1) 🎯 MVP

**Goal**: Open one provider flow and return a workspace-bound auth session in under two minutes.

**Independent Test**: Anonymous participant starts Yandex/VK/Telegram flow and receives active `AuthSession` + valid `/auth/me` state with workspace policy applied.

### Tests for User Story 1

- [X] T022 [P] [US1] Add contract tests for `/api/v1/auth/providers` and `/api/v1/auth/providers/{provider}/start` in `apps/server/tests/contract/test_auth_contracts.py`
- [X] T023 [P] [US1] Add callback contract tests for success, unavailable, and denied states in `apps/server/tests/contract/test_auth_contracts.py`
- [X] T024 [US1] Add integration happy-path test with provider adapter stubs in `apps/server/tests/contract/test_auth_contracts.py`

### Implementation for User Story 1

- [X] T025 [P] [US1] Implement provider registry and adapter interface in `apps/server/src/twobrain_rec_server/auth/providers/base.py`
- [X] T026 [P] [US1] Implement Yandex adapter in `apps/server/src/twobrain_rec_server/auth/providers/yandex.py`
- [X] T027 [P] [US1] Implement VK adapter in `apps/server/src/twobrain_rec_server/auth/providers/vk.py`
- [X] T028 [P] [US1] Implement Telegram adapter in `apps/server/src/twobrain_rec_server/auth/providers/telegram.py`
- [X] T029 [US1] Implement `/api/v1/auth/providers` and `/api/v1/auth/providers/{provider}/start` in `apps/server/src/twobrain_rec_server/api/auth.py`
- [X] T030 [US1] Implement callback start-to-session exchange (`/api/v1/auth/callback/{provider}`) in `apps/server/src/twobrain_rec_server/api/auth.py` and `apps/server/src/twobrain_rec_server/auth/callbacks.py`
- [X] T031 [US1] Implement provider subject normalization, external identity upsert, and user bootstrap in `apps/server/src/twobrain_rec_server/auth/callbacks.py`
- [X] T032 [US1] Implement session issuance/rotation + cookie/header transport helpers in `apps/server/src/twobrain_rec_server/auth/sessions.py`
- [X] T033 [US1] Wire provider endpoints into app router in `apps/server/src/twobrain_rec_server/main.py`

**Checkpoint**: One provider login flow establishes stable internal user + session.

---

## Phase 4: User Story 2 - Duplicate Provider Identity Merge (Priority: P1)

**Goal**: Link second provider identity to same internal user through confirmation and verified-match flow.

**Independent Test**: A user links VK to an existing Yandex session with confirmed email/phone without creating a second internal user.

### Tests for User Story 2

- [X] T034 [P] [US2] Add contract tests for `/api/v1/auth/link` success/confirm/reject flows in `apps/server/tests/contract/test_auth_contracts.py`
- [X] T035 [P] [US2] Add integration tests for verified-match and conflict cases in `apps/server/tests/contract/test_auth_contracts.py`

### Implementation for User Story 2

- [X] T036 [P] [US2] Implement link candidate matching and conflict detection service in `apps/server/src/twobrain_rec_server/auth/links.py`
- [X] T037 [US2] Implement explicit confirmation path and state machine in `apps/server/src/twobrain_rec_server/auth/links.py`
- [X] T038 [US2] Add `/api/v1/auth/link` endpoint in `apps/server/src/twobrain_rec_server/api/auth.py`
- [X] T039 [US2] Ensure linked provider list and linkage state are reflected in `apps/server/src/twobrain_rec_server/api/auth.py` response for `/api/v1/auth/me`
- [X] T040 [US2] Add auth audit records for link outcomes in `apps/server/src/twobrain_rec_server/auth/audit.py`

**Checkpoint**: Manual and auto-match linking paths work without silent account merge.

---

## Phase 5: User Story 3 - Device Registration and Session Continuity (Priority: P1)

**Goal**: Register/revoke trusted devices and require valid bindings for protected routes.

**Independent Test**: A registered device starts uploads; revoked device is blocked from protected endpoints in one request cycle.

### Tests for User Story 3

- [X] T041 [P] [US3] Add contract tests for `/api/v1/auth/devices/register` and `/api/v1/auth/devices/{device_id}/revoke` in `apps/server/tests/contract/test_auth_contracts.py`
- [X] T042 [US3] Add integration tests for revoked-device denial in `apps/server/tests/contract/test_auth_contracts.py`

### Implementation for User Story 3

- [X] T043 [P] [US3] Extend `RegisteredDevice` and `AuthSessionDeviceBinding` fields in `apps/server/src/twobrain_rec_server/db/models/identity.py` and `apps/server/src/twobrain_rec_server/db/models/federated_auth.py`
- [X] T044 [US3] Implement `AuthSessionDeviceBinding` persistence and status transitions in `apps/server/src/twobrain_rec_server/auth/sessions.py`
- [X] T045 [US3] Implement `/api/v1/auth/devices/register` in `apps/server/src/twobrain_rec_server/api/auth.py`
- [X] T046 [US3] Implement `/api/v1/auth/devices/{device_id}/revoke` in `apps/server/src/twobrain_rec_server/api/auth.py`
- [X] T047 [US3] Update tenant authorization checks to block revoked/quarantined bindings in `apps/server/src/twobrain_rec_server/auth/dependencies.py` and `apps/server/src/twobrain_rec_server/ingest/authorization.py`

**Checkpoint**: Device trust lifecycle is enforced before session-protected API actions.

---

## Phase 6: User Story 4 - Workspace Policy + RU Residency (Priority: P2)

**Goal**: Workspace can control enabled providers and RU data handling policy.

**Independent Test**: Changing workspace policy hides disabled providers and updates `/auth/providers` + `/auth/me` behavior immediately.

### Tests for User Story 4

- [X] T048 [P] [US4] Add contract tests for policy filtering in `apps/server/tests/contract/test_auth_contracts.py`
- [X] T049 [US4] Add integration test covering require_ru_local behavior in `apps/server/tests/contract/test_auth_contracts.py`

### Implementation for User Story 4

- [X] T050 [P] [US4] Implement policy read API in `apps/server/src/twobrain_rec_server/api/auth.py`
- [X] T051 [US4] Implement admin policy mutation endpoint with validation in `apps/server/src/twobrain_rec_server/api/auth.py`
- [X] T052 [US4] Implement policy cache/service with defaults and drift-safe writes in `apps/server/src/twobrain_rec_server/auth/policy.py`
- [X] T053 [US4] Ensure provider list and policy checks consume workspace policy in `apps/server/src/twobrain_rec_server/api/auth.py`
- [X] T054 [US4] Add RU-residency enforcement guards on external identity/session writes in `apps/server/src/twobrain_rec_server/auth/sessions.py`

**Checkpoint**: Disabled providers never appear for workspace; RU policy gates auth writes.

---

## Phase 7: User Story 5 - Failure and Recovery Visibility (Priority: P2)

**Goal**: Deterministic callback/device/link failures with explicit recovery hints.

**Independent Test**: Invalid state, reused callback, unavailable provider, and link-conflict all return stable problem codes and create audit evidence.

### Tests for User Story 5

- [X] T055 [P] [US5] Add contract tests for deterministic codes in `apps/server/tests/contract/test_auth_contracts.py`
- [X] T056 [US5] Add integration tests for tampered/reused state and denial recovery in `apps/server/tests/contract/test_auth_contracts.py`

### Implementation for User Story 5

- [X] T057 [P] [US5] Implement callback anti-replay and expiry validation in `apps/server/src/twobrain_rec_server/auth/callbacks.py`
- [X] T058 [US5] Add explicit problem detail mapping for all auth failure codes in `apps/server/src/twobrain_rec_server/auth/callbacks.py` and `apps/server/src/twobrain_rec_server/api/auth.py`
- [X] T059 [US5] Implement failure-state transitions in `apps/server/src/twobrain_rec_server/auth/links.py`
- [X] T060 [US5] Add deterministic audit events for all auth errors in `apps/server/src/twobrain_rec_server/auth/audit.py`

**Checkpoint**: Every failure path is recoverable and recorded.

---

## Phase 8: User Story 6 - Consent and Audit Transparency (Priority: P3)

**Goal**: Expose deterministic consent copy and server-side auditability without raw token leaks.

**Independent Test**: `/api/v1/auth/me` reports policy/provider state, and audit log contains redacted entries without raw claims/tokens.

### Tests for User Story 6

- [X] T061 [P] [US6] Add contract tests for `/api/v1/auth/me` and consent payload in `apps/server/tests/contract/test_auth_contracts.py`
- [X] T062 [US6] Add redaction and event-content assertions in `apps/server/tests/contract/test_auth_contracts.py`

### Implementation for User Story 6

- [X] T063 [P] [US6] Implement workspace consent copy model and admin read path in `apps/server/src/twobrain_rec_server/db/models/federated_auth.py` and `apps/server/src/twobrain_rec_server/api/auth.py`
- [X] T064 [US6] Add `/api/v1/auth/me` response shaping (linked providers, devices, policy summary) in `apps/server/src/twobrain_rec_server/api/auth.py`
- [X] T065 [US6] Finalize redaction policy for provider fields and auth metadata in `apps/server/src/twobrain_rec_server/observability/redaction.py`
- [X] T066 [US6] Update quickstart and policy runbook with RU/privacy checks in `specs/013-federated-auth-foundation/quickstart.md`

---

## Phase 9: Polish & Cross-Cutting Concerns

- [X] T067 [P] Run `$speckit-checklist` follow-up review for all generated checklists and mark resolved items in `specs/013-federated-auth-foundation/checklists/security.md`
- [X] T068 [P] Run checklist follow-up in `specs/013-federated-auth-foundation/checklists/infra.md`
- [X] T069 [P] Run checklist follow-up in `specs/013-federated-auth-foundation/checklists/ux.md`
- [X] T070 [P] Add/refresh auth migration + integration test evidence in `specs/013-federated-auth-foundation/quickstart.md`
- [X] T071 [P] Run `bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` and record output in `specs/013-federated-auth-foundation/quickstart.md`
- [X] T072 [P] Run `$speckit-analyze` and address any P1/P2 blocking findings before implementation work begins
- [X] T073 Run quick backend contract and focused smoke commands in `specs/013-federated-auth-foundation/quickstart.md`
- [X] T074 [P] Update `docs/github-issue-canon.md` links or references if any new issue labels/areas are introduced

---

## Phase 10: Task-to-Issue Handoff

- [X] T075 [P] Convert completed tasks into GitHub issues with Spec Kit issue canon sections and labels using `gh issue create` or the `speckit-taskstoissues` flow

---

## Phase 11: Review Remediation - Auth Security, Residency, and Handoff Gaps

**Goal**: Close review blockers before feature 013 can be treated as production-ready.

**Independent Test**: Forged provider callbacks, unauthorized workspace enrollment, raw audit metadata, RU-local policy drift, read-side writes, and admin device revoke behavior all have deterministic tests and fixed implementation.

### Tests for Review Remediation

- [X] T076 [P] [US1] Add provider callback verification tests for forged OAuth code rejection and Telegram signature validation in `apps/server/tests/contract/test_auth_contracts.py` and `apps/server/tests/fakes/auth_providers.py` (#498)
- [X] T078 [P] [US1] Add workspace enrollment abuse tests requiring membership, invite, or allowlist before callback creates a workspace member in `apps/server/tests/contract/test_auth_contracts.py` (#500)
- [X] T080 [P] [US4] Add RU-local write-boundary tests for auth/session/device/audit write paths in `apps/server/tests/contract/test_auth_contracts.py` and `apps/server/tests/unit/test_config_validation.py` (#502)
- [X] T082 [P] [US6] Add audit redaction tests proving raw `state_nonce`, provider code, and device public identifiers are not persisted in `AuthAuditEvent.metadata_json` in `apps/server/tests/contract/test_auth_contracts.py` (#504)
- [X] T084 [P] [US4] Add no-write regression tests for `GET /api/v1/auth/providers` and `GET /api/v1/auth/policy` in `apps/server/tests/contract/test_auth_contracts.py` (#506)
- [X] T086 [P] [US3] Add workspace owner/admin device revoke authorization tests in `apps/server/tests/contract/test_auth_contracts.py` (#508)
- [X] T088 [P] [US6] Add review evidence and task-to-issue/Linear mapping evidence for remediation tasks in `specs/013-federated-auth-foundation/quickstart.md` (#510)

### Implementation for Review Remediation

- [X] T077 [US1] Replace callback subject stubs with provider verification boundaries and fail-closed production guards in `apps/server/src/twobrain_rec_server/auth/providers/base.py`, `apps/server/src/twobrain_rec_server/auth/providers/yandex.py`, `apps/server/src/twobrain_rec_server/auth/providers/vk.py`, `apps/server/src/twobrain_rec_server/auth/providers/telegram.py`, and `apps/server/src/twobrain_rec_server/auth/callbacks.py` (#499)
- [X] T079 [US1] Enforce workspace enrollment gate before callback creates or attaches `WorkspaceMembership` in `apps/server/src/twobrain_rec_server/auth/callbacks.py`, `apps/server/src/twobrain_rec_server/auth/policy.py`, `apps/server/src/twobrain_rec_server/db/models/federated_auth.py`, and `apps/server/src/twobrain_rec_server/db/migrations/versions/0003_federated_auth_foundation.py` (#501)
- [X] T081 [US4] Implement RU-local auth write guard or deployment attestation check in `apps/server/src/twobrain_rec_server/auth/policy.py`, `apps/server/src/twobrain_rec_server/auth/sessions.py`, `apps/server/src/twobrain_rec_server/auth/callbacks.py`, `apps/server/src/twobrain_rec_server/auth/audit.py`, and `apps/server/src/twobrain_rec_server/config.py` (#503)
- [X] T083 [US6] Hash and minimize auth audit metadata in `apps/server/src/twobrain_rec_server/auth/audit.py`, `apps/server/src/twobrain_rec_server/api/auth.py`, and `apps/server/src/twobrain_rec_server/auth/callbacks.py` (#505)
- [X] T085 [US4] Split auth policy read from consent and policy persistence so GET endpoints are side-effect-safe in `apps/server/src/twobrain_rec_server/auth/policy.py` and `apps/server/src/twobrain_rec_server/api/auth.py` (#507)
- [X] T087 [US3] Allow workspace owner/admin device revoke or narrow the contract explicitly in `apps/server/src/twobrain_rec_server/api/auth.py` and `specs/013-federated-auth-foundation/contracts/openapi-auth-contract.md` (#509)
- [X] T089 [P] Separate Spec Kit tooling and Linear-sync changes from auth runtime review in `.specify/extensions.yml`, `.specify/extensions/linear-sync/`, and `.specify/extensions/git/` (#511)

**Checkpoint**: Feature 013 cannot be marked release-ready until all Phase 11 tasks are complete, mapped to GitHub/Linear, and validated.
