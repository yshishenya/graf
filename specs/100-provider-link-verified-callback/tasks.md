# Tasks: Provider Link Verified Callback

**Input**: Design documents from `specs/100-provider-link-verified-callback/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md, contracts/provider-link-api.md

**Tests**: Required. This is a high-risk auth/RLS feature; write focused failing tests before each matching implementation group and run the feature quickstart plus repository gate at closeout.

**Organization**: Tasks are grouped by user story so that each security property has a clear, independently testable receipt.

## Phase 1: Setup and requirements receipts

**Purpose**: Preserve the reviewed contract and establish the executable test surfaces.

- [ ] T001 Reconcile `specs/100-provider-link-verified-callback/checklists/security.md` against the final clarification, plan, data model, contract and quickstart; resolve or record every checklist item before code changes.
- [ ] T002 [P] Add provider-link API lifecycle/redaction contract coverage to `apps/server/tests/contract/test_auth_contracts.py` and `apps/server/tests/contract/test_provider_link_contracts.py`.
- [ ] T003 [P] Add browser/embedded Settings accessibility and safe-copy contract coverage to `apps/server/tests/contract/test_provider_link_settings_contract.py`.

---

## Phase 2: Foundational auth, schema and RLS boundary

**Purpose**: Complete the data/RLS boundary that every story depends on.

**⚠️ CRITICAL**: No provider-link callback or confirmation implementation begins before this phase is green.

- [X] T004 Extend `WorkspaceProviderLinkState` with server-owned callback/session/provider/candidate-display bindings and terminal-claim scrubbing helpers in `apps/server/src/twobrain_rec_server/db/models/federated_auth.py`.
- [X] T005 Add additive, reversible schema, indexes and exact callback-lookup RLS policy in `apps/server/src/twobrain_rec_server/db/migrations/versions/0024_provider_link_verified_callback.py`.
- [ ] T006 [P] Add PostgreSQL migration/RLS upgrade-downgrade and foreign-nonce isolation coverage in `apps/server/tests/integration/test_rls_postgres_policies.py` and `apps/server/tests/integration/test_rls_postgres_migrations.py`.
- [X] T007 Create link-intent lifecycle, exact-session authorization, expiry scrub and metadata-only audit service in `apps/server/src/twobrain_rec_server/auth/provider_links.py`.
- [X] T008 Add server-side callback-state lookup/dispatch boundary for a bound link state without changing ordinary login state behavior in `apps/server/src/twobrain_rec_server/auth/callbacks.py`.
- [X] T009 Add an idempotent maintenance-only expired-link scrub command and focused cleanup coverage in `apps/server/scripts/cleanup_expired_provider_links.py` and `apps/server/tests/integration/test_provider_link_cleanup.py`.

**Checkpoint**: The database permits only owner/session request access or exact callback nonce access; no candidate may survive terminal/expired processing.

---

## Phase 3: User Story 1 — Link a new provider safely (Priority: P1) 🎯 MVP

**Goal**: An authenticated member can start a provider flow, receive a server-verified pending candidate and explicitly attach it to the same account.

**Independent Test**: With a fake provider, start → callback → confirmation produces one identity for the original user and leaves the original session unchanged until confirmation.

### Tests for User Story 1

- [ ] T010 [P] [US1] Add authenticated start/callback/confirmation, no-preconfirm-identity/session mutation and same-user login-after-link tests in `apps/server/tests/contract/test_provider_link_contracts.py`.
- [ ] T011 [P] [US1] Add service-level verified-candidate lifecycle tests in `apps/server/tests/unit/test_provider_links.py`.

### Implementation for User Story 1

- [X] T012 [US1] Add CSRF-protected session-bound provider-link start and opaque confirmation endpoints, preserving deprecated `/api/v1/auth/link`, in `apps/server/src/twobrain_rec_server/api/auth.py`.
- [X] T013 [US1] Implement the dedicated verified link callback resolver and local safe confirmation redirect in `apps/server/src/twobrain_rec_server/auth/callbacks.py` and `apps/server/src/twobrain_rec_server/api/auth.py`.
- [X] T014 [US1] Implement same-user nested-transaction identity creation/reuse, terminal claim scrub and metadata-only lifecycle audit in `apps/server/src/twobrain_rec_server/auth/provider_links.py`.

**Checkpoint**: User Story 1 is independently functional with no client-provided identity proof and no premature session/identity mutation.

---

## Phase 4: User Story 2 — Reject raw-subject linking (Priority: P1)

**Goal**: Direct requests cannot create or influence a verified external identity.

**Independent Test**: A request containing forged provider subject/contact claims receives the existing safe error and cannot alter confirmation selection or database identity rows.

### Tests for User Story 2

- [ ] T015 [P] [US2] Extend forged-body, missing/opaque-intent and CSRF-negative cases in `apps/server/tests/contract/test_provider_link_contracts.py`.
- [X] T016 [P] [US2] Add rejected-event redaction assertions in `apps/server/tests/contract/test_auth_contracts.py`.

### Implementation for User Story 2

- [X] T017 [US2] Keep the deprecated direct link schema/route as a `409 provider_link_requires_verified_callback` compatibility guard and ensure confirmation ignores all non-identifier request input in `apps/server/src/twobrain_rec_server/api/auth.py`.
- [X] T018 [US2] Centralize safe provider-link audit metadata and fingerprints without raw claims, state, authorization codes or tokens in `apps/server/src/twobrain_rec_server/auth/provider_links.py` and `apps/server/src/twobrain_rec_server/auth/audit.py`.

**Checkpoint**: Every direct/raw subject path is a safe non-mutating rejection.

---

## Phase 5: User Story 3 — Preserve ordinary provider login/signup (Priority: P1)

**Goal**: Existing provider login, invitation and enrollment semantics stay unchanged.

**Independent Test**: Existing login callback tests retain their original user/session behavior while link callbacks never invoke that resolver's user/session creation branch.

### Tests for User Story 3

- [X] T019 [P] [US3] Expand normal-login versus link-callback dispatch regression coverage in `apps/server/tests/contract/test_auth_contracts.py`.
- [ ] T020 [P] [US3] Add disabled-provider and self-enrolment/invitation boundary coverage in `apps/server/tests/integration/test_provider_link_flow.py`.

### Implementation for User Story 3

- [X] T021 [US3] Preserve normal callback resolver and route response behavior while routing only bound link states to the dedicated resolver in `apps/server/src/twobrain_rec_server/api/auth.py` and `apps/server/src/twobrain_rec_server/auth/callbacks.py`.
- [X] T022 [US3] Recheck provider policy and active membership at link start, callback and confirmation without creating a membership or user in `apps/server/src/twobrain_rec_server/auth/provider_links.py`.

**Checkpoint**: Login/signup remains independently validated; link behavior cannot become an enrolment or account-switch path.

---

## Phase 6: User Story 4 — Handle conflicts without account merge (Priority: P1)

**Goal**: Existing same-user identities are idempotent and foreign identities conflict privately.

**Independent Test**: A new intent for the same user's identity yields one row; a foreign identity yields generic `409` with no ownership/contact disclosure and no ownership mutation.

### Tests for User Story 4

- [ ] T023 [P] [US4] Add same-user idempotence, competing confirm and foreign-owner conflict contract coverage in `apps/server/tests/contract/test_provider_link_contracts.py`.
- [ ] T024 [P] [US4] Add uniqueness-race and audit-safe-conflict integration coverage in `apps/server/tests/integration/test_provider_link_flow.py`.

### Implementation for User Story 4

- [X] T025 [US4] Convert `ExternalIdentity` uniqueness outcomes into idempotent same-user result or generic conflict without transfer/merge in `apps/server/src/twobrain_rec_server/auth/provider_links.py`.
- [X] T026 [US4] Render only safe provider/status conflict copy in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/provider_link_settings.html`.

**Checkpoint**: Conflict behavior is race-safe, private and leaves existing identities intact.

---

## Phase 7: User Story 5 — Deny expiry, replay and cross-session use (Priority: P1)

**Goal**: Reuse or scope mismatch cannot link an identity.

**Independent Test**: Expired, repeated, wrong-user, wrong-workspace and wrong-session callback/confirm attempts produce no identity mutation and scrub stale candidate claims.

### Tests for User Story 5

- [X] T027 [P] [US5] Add expiry, callback/confirm replay, wrong-user/workspace/session and multi-tab contract coverage in `apps/server/tests/contract/test_provider_link_contracts.py`.
- [X] T028 [P] [US5] Add real PostgreSQL zero-row cross-scope mutation and exact-session RLS coverage in `apps/server/tests/integration/test_rls_postgres_policies.py`.

### Implementation for User Story 5

- [X] T029 [US5] Enforce terminal-state, expiry, exact session/user/workspace and policy checks before confirmation; atomically scrub rejected/expired candidates in `apps/server/src/twobrain_rec_server/auth/provider_links.py`.
- [X] T030 [US5] Surface only safe cancelled, expired, replayed, disabled and conflict states through the browser/embedded routes in `apps/server/src/twobrain_rec_server/cabinet/web_routes/provider_links.py` and `apps/server/src/twobrain_rec_server/cabinet/web_routes/desktop.py`.

**Checkpoint**: Stale and cross-context state is unusable and no pending claim remains reachable after expiry.

---

## Phase 8: User Story 6 — Metadata-only audit and shared Settings UX (Priority: P2)

**Goal**: A user can complete the explicit confirmation in a safe accessible shared Settings surface; operators see useful non-sensitive lifecycle evidence.

**Independent Test**: Browser and embedded cabinet show provider-only state, labelled confirmation and safe status; lifecycle audit exposes only approved metadata.

### Tests for User Story 6

- [X] T031 [P] [US6] Add Settings browser/embedded parity, CSRF-negative, keyboard/focus and status accessibility coverage in `apps/server/tests/contract/test_provider_link_settings_contract.py` and `apps/server/tests/integration/test_provider_link_settings_flow.py`.
- [X] T032 [P] [US6] Add all lifecycle audit-redaction contract coverage in `apps/server/tests/contract/test_provider_link_contracts.py`.

### Implementation for User Story 6

- [X] T033 [US6] Add provider-link Settings query/view model and page/fragment rendering in `apps/server/src/twobrain_rec_server/cabinet/queries.py`, `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/rendering.py`.
- [X] T034 [US6] Add the browser Settings route, shared fragment/template and Settings entry without raw identity data in `apps/server/src/twobrain_rec_server/cabinet/web_routes/provider_links.py`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_content.html` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/provider_link_settings.html`.
- [X] T035 [US6] Add embedded desktop routing that reuses the server-owned Settings surface and current authenticated context in `apps/server/src/twobrain_rec_server/cabinet/web_routes/desktop.py`.

**Checkpoint**: Browser and embedded cabinet provide the same explicit safe flow without a native macOS implementation.

---

## Phase 9: Polish, closeout and release

**Purpose**: Complete cross-cutting evidence, tracker and production gates.

- [ ] T036 Re-run and check off `specs/100-provider-link-verified-callback/checklists/security.md` with final requirement links and no open gaps.
- [X] T037 [P] Update behavior/security/validation notes in `CHANGELOG.md` and `docs/current-product-status.md`.
- [X] T038 Run the focused quickstart test matrix and `infra/scripts/ci-local.sh`; record high-risk lane evidence in `specs/100-provider-link-verified-callback/quickstart.md` or PR evidence without secrets.
- [ ] T039 Run the required independent code/security and UX/QA review; resolve any Critical/High finding and record reviewed file/line evidence in the PR.
- [ ] T040 Prepare the CalVer release, run `infra/scripts/cd-remote.sh --dry-run`, deploy only under the existing approval, and collect metadata-only browser/embedded production smoke plus rollback evidence.

## Dependencies & Execution Order

- **Phase 1 → Phase 2**: Requirement and test surfaces must precede schema/RLS design.
- **Phase 2 → US1–US6**: The owner/session/callback-nonce boundary blocks all product behavior.
- **US1 → US2–US6**: A real verified flow is needed before its rejection, compatibility, conflict, expiry and UI variants.
- **US3–US5**: May be developed after US1 but each must pass before release because all are P1 authentication boundaries.
- **US6**: Depends on the confirmation state surface from US1/US4/US5.
- **Phase 9**: Depends on all selected stories and clean security checklist.

## Parallel Opportunities

- T002 and T003 touch separate contract surfaces.
- T004/T005 precede T006–T009; T006 and test-skeleton work can proceed independently after the migration shape is agreed.
- Each `[P]` test task in a user-story phase targets a distinct file/surface and can be developed in parallel after its prerequisites.
- T037 can proceed while final validation is being prepared, but it must reflect verified behavior only.

## Implementation Strategy

1. Land Phase 2 and US1 as the minimum secure callback-confirmation increment.
2. Complete US2–US5 before any release candidate: they are mandatory P1 trust-boundary properties, not optional polish.
3. Add US6 with the shared server-rendered Settings flow; do not build a duplicate native screen.
4. Run checklist/analyze/issue sync before code, then use focused TDD during implementation and the full high-risk release gate at closeout.
