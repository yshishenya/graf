# Tasks: Надёжное подключение способов входа

## Phase 1: Root cause and regression guards

- [x] T001 [P] [US1] Add failing shared auth-bootstrap context contract tests in `apps/server/tests/contract/test_auth_contracts.py`
- [x] T002 [P] [US1] Add failing exact app-role provider-link start RLS regression in `apps/server/tests/integration/test_rls_postgres_policies.py`
- [x] T003 [P] [US2] Add failing non-email initiating-provider merge preview cases in `apps/server/tests/contract/test_auth_contracts.py`
- [x] T004 [P] [US2] Add failing provider-aware merge page/result cases in `apps/server/tests/contract/test_account_merge_contract.py` and `apps/server/tests/contract/test_account_routes.py`
- [x] T005 [P] [US3] Add failing stale-proof restart/no-old-confirm cases in `apps/server/tests/contract/test_account_routes.py`

## Phase 2: Backend and RLS

- [x] T006 [US1] Add the shared bounded provider-link auth context helper in `apps/server/src/twobrain_rec_server/auth/provider_links.py`
- [x] T007 [US1] Apply the helper before callback-state creation in `apps/server/src/twobrain_rec_server/cabinet/web_routes/provider_links.py` and `apps/server/src/twobrain_rec_server/api/auth.py`
- [x] T008 [US2] Replace email-only cross-profile eligibility with exact active session/source-provider checks and provider-specific callback proof semantics in `apps/server/src/twobrain_rec_server/auth/provider_links.py`
- [x] T009 [US2] Enforce one safe personal root and active owner membership per side, block separately-owned corporate/unknown shapes, and transfer only classified workspace rows in `apps/server/src/twobrain_rec_server/auth/account_merge.py`
- [x] T023 [US2] Recheck semantic provider relations across exact callback, provider-link and source-identity proofs in `apps/server/src/twobrain_rec_server/auth/account_merge.py`
- [x] T024 [US1] Bind email login/signup completion to a per-attempt browser proof and store every six-digit email code as a purpose-separated server-keyed HMAC
- [x] T025 [US1] Prevent unbound API OAuth callbacks from installing browser sessions, add public OAuth rate limits and move blocking provider verification off the event loop
- [x] T026 [US4] Revoke provider-issued sessions and device bindings atomically when that provider is disconnected, including direct relogin recovery
- [x] T028 [US2] Accept email ownership only from an exact active verified `provider=email` identity in login, linking, merge execution and migration 0075
- [x] T029 [US1] Reject backslash, encoded authority, control and external redirect forms through one shared first-party path validator
- [x] T030 [US2] Bind the initiating provider session to the exact external identity through its claims fingerprint, including multiple same-provider identities

## Phase 3: UX/UI/IA/CX

- [x] T010 [US2] Derive proof-bound provider presentation and provider-aware post-merge result in `apps/server/src/twobrain_rec_server/cabinet/web_routes/account_merge.py`
- [x] T011 [US2] Pass provider-aware title, copy, CTA and restart inputs in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [x] T012 [US2] Render provider-aware merge/blocker/actions with one primary action in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/account_merge_content.html`
- [x] T013 [US3] Hide stale confirm and render fresh OAuth start or safe settings return in `apps/server/src/twobrain_rec_server/cabinet/web_routes/account_merge.py` and merge template
- [x] T014 [P] [US4] Replace internal preview/email-only settings copy in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html` and `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [x] T015 [P] [US2] Add provider-aware relogin success copy in `apps/server/src/twobrain_rec_server/cabinet/auth_rendering.py`
- [x] T031 [US3] Turn resolved blockers and stale previews into an immediate provider-aware restart instead of a failing confirm or terminal dead end

## Phase 4: Validation and closeout

- [x] T016 [P] Run focused contract/integration tests and Ruff from `specs/180-account-linking-reliability/quickstart.md`
- [x] T017 Run strict PostgreSQL app-role RLS regression and full focused account-linking matrix
- [x] T018 Run Product Design browser audit at wide/390 px and embedded route parity; record metadata-safe results in `specs/180-account-linking-reliability/design-qa.md`
- [x] T019 Run independent security/code/Ponytail review and close every P0-P2 finding
- [x] T020 Update `[Unreleased]` behavior notes in `CHANGELOG.md`
- [x] T021 Run `infra/scripts/ci-local.sh --fast` and record validation in `specs/180-account-linking-reliability/evidence.md`
- [x] T022 Reconcile tasks with GitHub issues #5476–#5480; keep them open until commit/PR evidence exists
- [x] T027 Re-run focused PostgreSQL, auth security regressions, independent reviews and fast CI after security remediation
