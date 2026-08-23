# Tasks: Единый ввод одноразового кода

## Phase 1: Contract coverage

- [X] T001 [P] [US1] Update shared auth rendering contracts in `apps/server/tests/contract/test_account_merge_contract.py`, `apps/server/tests/contract/test_account_routes.py`, and `apps/server/tests/integration/test_web_owner_session_context.py` for six slots and the existing hidden `code` field.
- [X] T002 [P] [US1] Add static and DOM behavior checks for the six-slot component in `apps/server/tests/contract/test_cabinet_static_assets_contract.py`.

## Phase 2: Shared implementation

- [X] T003 [US1] Render six accessible slots, the hidden `code` field, and a no-JavaScript fallback in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/auth/email_code.html`.
- [X] T004 [US2] Implement digit distribution, paste/autofill, keyboard navigation, incomplete-submit guard, hidden-field sync, and one-shot auto-submit in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.
- [X] T005 [US1] Replace the rectangular code input styles with one responsive near-square slot contract shared by browser and embedded desktop in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.

## Phase 3: Validation and closeout

- [X] T006 [US1] Confirm all five inventory flows still render their route-specific actions and shared slot structure; confirm macOS only embeds the server cabinet and has no second OTP implementation.
- [X] T007 [US2] Run the feature quickstart focused tests and `infra/scripts/ci-local.sh --fast`; record the selected high-risk validation lane and results without committing.
- [X] T008 [US1] Update `CHANGELOG.md` under `[Unreleased]` with the user-visible OTP consistency change.
