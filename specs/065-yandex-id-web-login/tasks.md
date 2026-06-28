# Tasks: Yandex ID Web Login

**Input**: Design documents from `specs/065-yandex-id-web-login/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: High-risk auth/web login path. Focused integration, contract, and unit tests are required.

## Phase 1: Browser Action Contract

- [X] T001 [P] [US1] Update browser login/sign-up tests so enabled Yandex renders as an active link and no longer shows `скоро` in `apps/server/tests/integration/test_web_owner_session_context.py`
- [X] T002 [P] [US2] Add disabled-provider and unsupported-provider browser fallback assertions in `apps/server/tests/integration/test_web_owner_session_context.py`
- [X] T003 [P] [US3] Add callback URL public-base regression coverage in `apps/server/tests/contract/test_auth_contracts.py`

## Phase 2: Minimal Implementation

- [X] T004 [US1] Extend provider rendering data with provider id, active href, and disabled state in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T005 [US1] Replace disabled provider spans with active links for enabled Yandex while keeping other providers disabled in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/auth/login.html` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/auth/signup.html`
- [X] T006 [US1] Implement `/login/yandex/start` as a redirect into the existing provider start flow in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T007 [US2] Map browser provider start failures to bounded login-page errors without exposing provider details in `apps/server/src/twobrain_rec_server/cabinet/web.py` and `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T008 [US3] Make auth callback URL construction use `TWOBRAIN_AUTH_BASE_URL` when configured in `apps/server/src/twobrain_rec_server/api/auth.py`

## Phase 3: Documentation and Validation

- [X] T009 Update 065 quickstart validation evidence in `specs/065-yandex-id-web-login/quickstart.md`
- [X] T010 Run focused validation from quickstart and mark passing tasks only after evidence is recorded
- [X] T011 Run `infra/scripts/ci-local.sh` before closeout or document the exact blocker
