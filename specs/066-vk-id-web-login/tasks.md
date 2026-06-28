# Tasks: VK ID Web Login

**Input**: Design documents from `specs/066-vk-id-web-login/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: High-risk auth/web login path. Focused integration, contract, and unit tests are required.

## Phase 1: Browser Action Contract

- [X] T001 [P] [US1] Update browser login/sign-up tests so enabled VK renders as an active link and no longer shows `скоро` in `apps/server/tests/integration/test_web_owner_session_context.py`
- [X] T002 [P] [US1] Add VK browser start redirect assertions in `apps/server/tests/integration/test_web_owner_session_context.py`
- [X] T003 [P] [US2] Add disabled-VK and unsupported-provider browser fallback assertions in `apps/server/tests/integration/test_web_owner_session_context.py`
- [X] T004 [P] [US3] Add VK callback public-base and client-id regression coverage in `apps/server/tests/contract/test_auth_contracts.py`
- [X] T005 [P] [US3] Add production VK secret validation coverage in `apps/server/tests/unit/test_config_validation.py`

## Phase 2: Minimal Implementation

- [X] T006 [US1] Enable VK as an active browser provider while leaving Telegram disabled in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T007 [US1] Allow `/login/vk/start` to use the existing provider start flow in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T008 [US3] Use provider-specific client IDs for browser provider start redirects in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T009 [US3] Mount VK client secret only into `rec-api` and expose `TWOBRAIN_VK_CLIENT_ID` in `infra/docker-compose.yml`
- [X] T010 [US3] Document VK production secret variables in `infra/env/rec.production.env.example`

## Phase 3: Documentation and Validation

- [X] T011 Update `[Unreleased]` in `CHANGELOG.md`
- [X] T012 Run focused quickstart validation commands from `specs/066-vk-id-web-login/quickstart.md`
- [X] T013 Run `infra/scripts/ci-local.sh` before closeout or document the exact blocker
- [X] T014 If production credentials are available, configure server `.env`/secret and run deploy dry-run/execute gates from `docs/agent-guidance/release-and-validation.md`

## Dependencies & Execution Order

- Phase 1 tests define the contract before implementation.
- T006 and T007 can proceed after T001-T003.
- T008-T010 can proceed after T004-T005.
- Phase 3 waits for implementation and focused validation.

## Parallel Opportunities

- T001-T005 touch separate test concerns and can be prepared in parallel.
- T009-T010 can run in parallel with browser code after T004-T005 define the config contract.

## Independent Test Criteria

- **US1**: `/login` and `/sign-up` show VK as an active link, and `/login/vk/start?next=/meetings` redirects to VK authorization.
- **US2**: Disabled VK and unsupported Telegram routes fail closed with email fallback and no provider internals.
- **US3**: VK start uses VK client ID and public callback URL, while production secret wiring fails closed when the configured secret is absent or empty.

## Implementation Strategy

Deliver US1 first, then failure handling and production secret wiring. Do not deploy until VK credentials are present on the server.
