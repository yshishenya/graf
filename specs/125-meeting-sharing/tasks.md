# Tasks: Надёжный и безопасный обмен встречами

**Input**: [spec.md](spec.md), [scenarios.md](scenarios.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/meeting-sharing.md](contracts/meeting-sharing.md),
[quickstart.md](quickstart.md)

## Execution rules

- Выполнять задачи по порядку зависимостей и отмечать `[X]` только после
  реализации и проверки.
- Все данные тестов synthetic; реальные email, токены, transcript, audio и
  private contacts запрещены.
- External/public/contact/referral tasks с пометкой `GATE` нельзя включать или
  считать rollout-ready без независимого security/product approval. Текущий
  rollout разрешает только exact-email B2C; public/contact/referral остаются
  выключенными.

## Phase 1 — Setup

**Goal**: prepare the Feature 125 implementation surface and preserve existing
authorities.

- [X] T001 [P] Confirm Feature 125 artifacts and current implementation scope in `specs/125-meeting-sharing/plan.md`, `specs/125-meeting-sharing/research.md`, and `specs/125-meeting-sharing/quickstart.md`
- [X] T002 [P] Add the Feature 125 synthetic test module and fixture notes in `apps/server/tests/unit/test_meeting_sharing.py`
- [X] T003 [P] Add the Feature 125 contract test module for the share fragment and response shapes in `apps/server/tests/contract/test_meeting_sharing_contract.py`

## Phase 2 — Foundational safety and policy

**Goal**: establish server-side invariants before changing the modal.

- [X] T004 [P] Add unit coverage for bounded invitation expiry, accepted-grant expiry, scope/audience combinations, wildcard-safe search, and privacy-preserving errors in `apps/server/tests/unit/test_meeting_sharing.py`
- [X] T005 [P] Add contract coverage for token-safe headers, disabled capabilities, meeting-bound recipient search, and metadata-only projections in `apps/server/tests/contract/test_meeting_sharing_contract.py`
- [X] T006 Enforce external-invitation summary-only/view-only constraints and bounded expiry in `apps/server/src/twobrain_rec_server/cabinet/access.py`
- [X] T007 Propagate `MeetingShareInvitation.expires_at` to accepted `MeetingShareGrant.expires_at` and preserve revoke/deletion precedence in `apps/server/src/twobrain_rec_server/cabinet/access.py`
- [X] T008 Bind recipient search to `meeting_id` and actor `can_share`, escape wildcard input, and return a bounded privacy-safe result in `apps/server/src/twobrain_rec_server/cabinet/access.py` and `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [X] T009 Add request-time effective public abuse-gate verification to create/resolve paths without enabling public links in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [X] T010 Add raw bearer-token path redaction and share-page no-store/no-referrer/noindex response policy in `apps/server/src/twobrain_rec_server/observability/logging.py`, `apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py`, and `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [X] T011 Run focused foundational tests and record remaining external/public rollout blockers in `specs/125-meeting-sharing/checklists/security.md`

## Phase 3 — User Story 1: Поделиться без мёртвого действия (P1)

**Story goal**: the owner sees truthful capability state, can find an internal
recipient and receives a bounded next action instead of a generic dead-end.

**Independent test**: with external delivery disabled, Share makes no invitation
POST; with an active synthetic workspace identity, the owner creates a
summary-only grant and sees its access row and returned recipient-bound link.

- [X] T012 [P] [US1] Define capability/reason and recipient-source projections in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T013 [P] [US1] Add unit coverage for capability states and problem-code-to-copy mapping in `apps/server/tests/unit/test_meeting_sharing.py`
- [X] T014 [US1] Derive capability projection from runtime settings and meeting access in `apps/server/src/twobrain_rec_server/cabinet/access.py`
- [X] T015 [US1] Thread the same capability projection into browser, embedded and JSON review paths in `apps/server/src/twobrain_rec_server/cabinet/queries.py`, `apps/server/src/twobrain_rec_server/api/cabinet.py`, `apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py`, and `apps/server/src/twobrain_rec_server/cabinet/web_routes/desktop.py`
- [X] T016 [US1] Render truthful capability state, source hooks, explicit search action and accessible status regions in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_share.html`
- [X] T017 [US1] Replace generic failure handling with bounded problem-code copy, prevent disabled external POSTs, and keep typed values in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T018 [US1] Add source/status/blocked-state styling without changing the original GRAF visual language in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T019 [US1] Extend UI contract assertions for explicit open, capability visibility, no auto-open, no disabled request, source labels and Russian accessible names in `apps/server/tests/contract/test_recording_share_ui_contract.py`
- [X] T020 [US1] Run the independent User Story 1 quickstart and focused pytest matrix from `specs/125-meeting-sharing/quickstart.md`

## Phase 4 — User Story 3: Управлять доступом без матрицы разрешений (P1)

**Story goal**: the owner sees active grants, can copy a recipient-bound link,
rotate/revoke it and understands the summary-only default.

**Independent test**: create a synthetic internal grant, copy only the returned
recipient-bound URL, resolve it as the intended recipient, rotate/revoke/expire
it, and confirm the next server request is blocked.

- [X] T021 [P] [US3] Add integration coverage for recipient-bound copy-link, user-grant rotation, revoke, expiry and deletion races in `apps/server/tests/integration/test_meeting_share_links.py`
- [X] T022 [P] [US3] Add contract coverage for active-grant scope, lifecycle copy, returned URL handling and revoke controls in `apps/server/tests/contract/test_meeting_sharing_contract.py`
- [X] T023 [US3] Extend link rotation domain logic to preserve user audience/scope/expiry and audit the rotation in `apps/server/src/twobrain_rec_server/cabinet/access.py`
- [X] T024 [US3] Return correct recipient-bound URLs for user grants and preserve public/link gates in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [X] T025 [US3] Render active grant scope/expiry state and Copy link/Revoke controls in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_share.html`
- [X] T026 [US3] Implement returned-URL clipboard handling, optimistic-safe revoke, rotation status and focus-preserving lifecycle updates in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T027 [US3] Verify direct summary/transcript/playback/download/export routes recheck grant scope, expiry, revoke and deletion in `apps/server/tests/integration/test_meeting_share_links.py` and `apps/server/tests/contract/test_recording_share_invitation_contract.py`
- [X] T028 [US3] Run the independent User Story 3 quickstart and focused access/link test matrix from `specs/125-meeting-sharing/quickstart.md`

## Phase 5 — User Story 4: Найти человека из безопасных источников (P2)

**Story goal**: the owner gets bounded, source-labelled suggestions from the
workspace and current linked calendar roster without turning suggestions into
access or consent.

**Independent test**: a synthetic name/email/calendar match yields one active
GRAF identity with source labels; unknown/stale/declined/external contacts do
not produce an unauthorized identity or side effect.

- [X] T029 [P] [US4] Add unit/integration fixtures for workspace email identity, linked calendar roster, deduplication, stale state and declined/external attendee in `apps/server/tests/unit/test_meeting_sharing.py` and `apps/server/tests/integration/test_meeting_share_links.py`
- [X] T030 [US4] Add contract assertions for `user_id`, bounded email policy, `source`, `recipient_type`, `freshness` and maximum result count in `apps/server/tests/contract/test_meeting_sharing_contract.py`
- [X] T031 [US4] Query active workspace identities by safe display name/verified email and merge current authorized calendar matches deterministically in `apps/server/src/twobrain_rec_server/cabinet/access.py`
- [X] T032 [US4] Pass meeting context and principal through the recipient-search route and preserve privacy-safe empty/denied behavior in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [X] T033 [US4] Render calendar/workspace source and freshness labels without exposing unrelated participant email in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_share.html`
- [X] T034 [US4] Add keyboard and combobox behavior for source-labelled candidate rows with no implicit grant in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T035 [US4] Verify calendar candidate lookup creates zero grants, delivery records, recording-consent changes or content egress in `apps/server/tests/integration/test_meeting_share_links.py`
- [X] T036 [US4] Run the independent User Story 4 quickstart and privacy/accessibility matrix from `specs/125-meeting-sharing/quickstart.md`

## Phase 6 — User Story 2: Получатель и внешнее приглашение (P1, GATE)

**Story goal**: operate a safe exact-email invitation and recipient onboarding
path while keeping public/contact/referral extensions disabled.

**Independent test**: in a synthetic delivery environment, verify metadata-only
email, exact-address acceptance, bounded grant expiry, generic wrong-recipient
failure, one-step email auth with automatic personal-account bootstrap and no
automatic workspace membership.

- [X] T037 [P] [US2] Add contract tests for invitation lifecycle, exact verified address, safe email content and no workspace auto-join in `apps/server/tests/contract/test_recording_share_invitation_contract.py`
- [X] T038 [P] [US2] Add synthetic delivery state tests for pre-egress failure, provider-accepted `sent` and post-egress `outcome-unknown` in `apps/server/tests/integration/test_invitation_delivery_workflow.py`
- [X] T039 [US2] Add metadata-only recipient value copy and one-step sign-in CTA with automatic first-account bootstrap to `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/share_invitation_content.html`, `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and browser auth routes
- [X] T040 [US2] Add independent delivery idempotency, abuse/quota, token-scrubbing and deletion/revoke gate evidence before changing `share_external_invitations_enabled` in `specs/125-meeting-sharing/checklists/security.md` and `specs/125-meeting-sharing/quickstart.md`
- [X] T041 [US2] Enable bounded exact-email external delivery with server-side Postal/HMAC settings while keeping public links, contacts and referral attribution disabled in `docs/current-product-status.md`

## Phase 7 — User Story 5: Добровольное знакомство с GRAF (P2, GATE)

**Story goal**: prepare a value-led, consent-based referral path with bounded
attribution and no meeting-content tracking.

**Independent test**: synthetic invitation → summary view → CTA → verified
signup yields at most one attributed conversion and no new grant/account on
repeat opens or forwarding.

- [ ] T042 [P] [US5] Add a metadata-only event catalog and forbidden-field tests for share/referral funnel events in `apps/server/src/twobrain_rec_server/product_analytics/event_catalog.py` and `apps/server/tests/unit/test_public_analytics.py`
- [ ] T043 [P] [US5] Define opaque referral lifecycle, retention and deletion contract in `specs/125-meeting-sharing/data-model.md` and `specs/125-meeting-sharing/contracts/meeting-sharing.md`
- [ ] T044 [US5] Implement server-issued idempotent referral attribution only after product/privacy/legal/analytics approval in `apps/server/src/twobrain_rec_server/product_analytics/share_referrals.py` (GATE; no production code before approval)
- [ ] T045 [US5] Run synthetic funnel, replay, forwarding, self-referral, bot and rollback rehearsal before enabling attribution in `specs/125-meeting-sharing/quickstart.md` (GATE)

## Phase 8 — Address-book and provider extensions (P2, GATE)

**Goal**: preserve the native least-privilege design without building a hidden
server-side contact index.

- [ ] T046 [P] [US4] Add native macOS contact-picker integration contract and limited-selection handoff in `apps/macos/RecApp/Sources/Cabinet/ContactPickerBridge.swift` (GATE)
- [ ] T047 [P] [US4] Define Google People/Microsoft Graph delegated read-only scopes, cache TTL, disconnect purge and consent copy in `specs/125-meeting-sharing/research.md` and `specs/125-meeting-sharing/contracts/meeting-sharing.md`
- [ ] T048 [US4] Keep browser-only path typed-email based and add a negative test proving no full address-book sync is attempted in `apps/server/tests/contract/test_meeting_sharing_contract.py`

## Phase 9 — Polish and cross-cutting validation

- [X] T049 [P] Update behavior/UX/security notes in `CHANGELOG.md` in Russian with the actual delivered scope and gated limitations
- [X] T050 [P] Run product-design audit and clean-room review against the implemented Share modal in `specs/125-meeting-sharing/checklists/ux.md`
- [X] T051 [P] Run Ponytail review and remove unnecessary dependencies/abstractions while preserving authorization, accessibility and evidence gates in `specs/125-meeting-sharing/plan.md`
- [X] T052 Run the full Feature 125 quickstart, `git diff --check`, focused pytest and `infra/scripts/ci-local.sh`; attach synthetic evidence and keep public/contact/referral rollout disabled in `specs/125-meeting-sharing/quickstart.md`

## Phase 10 — Post-review hardening

- [X] T053 [P] Add a narrow `share_invitation_lookup` RLS context, migration indexes and PostgreSQL policy coverage in `apps/server/src/twobrain_rec_server/db/tenant_context.py`, `apps/server/src/twobrain_rec_server/db/migrations/versions/0036_share_invitation_auth_lookup.py`, and `apps/server/tests/contract/test_rls_policy_matrix_contract.py`
- [X] T054 [P] Add durable keyed auth-code rate limits, RLS inventory and regression coverage in `apps/server/src/twobrain_rec_server/auth/rate_limit.py`, `apps/server/src/twobrain_rec_server/db/migrations/versions/0037_auth_rate_limit_buckets.py`, and `apps/server/tests/integration/test_web_owner_session_context.py`
- [X] T055 [P] Close provider email-verification and callback/email-state race paths in `apps/server/src/twobrain_rec_server/auth/providers/base.py`, `apps/server/src/twobrain_rec_server/auth/callbacks.py`, `apps/server/src/twobrain_rec_server/auth/sessions.py`, and `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py`
- [X] T056 [P] Make Share load failures retryable, external invitation explicit, and recipient combobox keyboard-accessible in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_share.html`, and `apps/server/tests/contract/test_recording_share_ui_contract.py`
- [X] T057 [P] Add truthful B2B notification outcome and commit-before-Temporal delivery recovery in `apps/server/src/twobrain_rec_server/api/cabinet.py`, `apps/server/src/twobrain_rec_server/api/schemas.py`, and `apps/server/src/twobrain_rec_server/workflows/worker.py`
- [X] T058 [P] Show linked calendar candidates on initial empty search without creating grants or consent side effects in `apps/server/src/twobrain_rec_server/cabinet/access.py` and `apps/server/tests/integration/test_meeting_share_links.py`
- [X] T059 Run focused PostgreSQL/RLS/auth/Share checks, full `infra/scripts/ci-local.sh`, and repeat security, product, accessibility and Ponytail review; record only synthetic evidence in `specs/125-meeting-sharing/quickstart.md`

## Phase 11 — Production delivery hotfix

- [ ] T060 Attach `rec-processing-worker` to the external Postal network and add a Compose regression assertion in `infra/docker-compose.yml` and `apps/server/tests/integration/test_compose_hardening.py`; rerun the Feature 125 quickstart, repository gate and production smoke without sending a live test email

## Dependencies and execution order

```text
T001–T003
   ↓
T004–T011 (foundational safety)
   ↓
T012–T020 (US1)
   ↓
T021–T028 (US3)
   ↓
T029–T036 (US4 internal/calendar)
   ├── T037–T041 (US2 gated external invitation)
   ├── T042–T045 (US5 gated referral)
   └── T046–T048 (US4 gated address-book/provider)
   ↓
   T049–T052 (polish and repository gate)
   ↓
   T053–T060 (post-review hardening and production delivery hotfix)
```

Parallel examples:

- T004 and T005 can run in parallel because they touch separate test concerns.
- T012 and T013 can run in parallel after foundational policy decisions.
- T021 and T022 can run in parallel because one is integration coverage and one
  is contract coverage.
- T029/T030 can run in parallel before US4 implementation.
- T037/T038 and T042/T043 are independent gated design/test workstreams after
  foundational safety, but neither authorizes a rollout.

## Implementation strategy

1. Complete foundational safety and keep public/contact/referral flags false.
2. Deliver US1 internal summary-only Share as the MVP; validate independently.
3. Add US3 recipient-bound link/revoke/expiry management; validate independently.
4. Add US4 workspace/calendar suggestions without external identity leakage.
5. Enable only the exact-email portion of US2 after security, delivery,
   privacy, retention and deletion evidence; keep US5/address-book/provider
   extensions gated until their own approvals.
6. Update `CHANGELOG.md`, run clean-room/product-design/Ponytail review and the
   repository gate. No implementation commit or deploy is created without
   explicit user approval after validation.

## Requirement coverage map

| Requirement group | Covered by |
|---|---|
| FR-001–FR-005 capability, explicit Share, default summary/view | T012–T020 |
| FR-006–FR-010 identity input, bounded search, capability-gated delivery, invitation lifecycle | T004–T008, T012–T020, T037–T041 |
| FR-011–FR-017 scope, egress separation, access management, privacy errors | T006–T010, T021–T028, T037–T040 |
| FR-018–FR-023 audit, safe email, CTA/attribution, funnel and abuse limits | T005–T011, T037–T045 |
| FR-024–FR-027 calendar/contact sources and permission states | T029–T036, T046–T048 |
| FR-028 accessibility, parity and narrow viewport | T016–T020, T025–T026, T034–T036, T050 |
| FR-029–FR-035 gates, deletion, rollback, domain invariants and synthetic evidence | T004–T011, T021–T028, T037–T052 |
| FR-036–FR-038 participant share, auto-share and Shared with me | Spec/research/contract design; future gated implementation slice |
| FR-039–FR-041 pre-read, team access and channel/calendar distribution | Spec/data-model/contract design; future gated implementation slice |
| FR-042 metadata-only adoption analytics | T042–T045 plus the metadata-only adoption contract |
| SC-001–SC-005 capability, lifecycle, authorization and content safety | T004–T028, T037–T041, T052 |
| SC-006–SC-007 search latency and contact side-effect safety | T029–T036, T048, T052 |
| SC-008–SC-009 funnel idempotency and abuse limits | T038–T045, T052 |
| SC-010–SC-012 parity, rollback and owner comprehension | T019–T020, T028, T036, T040–T052 |
| SC-013–SC-016 meeting-bound search, bounded expiry, token hygiene and throttling | T004–T011, T021–T028, T037–T045, T052 |
| SC-017–SC-021 participant distribution, adoption and rollback | Spec/data-model/contract design; synthetic execution requires a later gated task slice |
