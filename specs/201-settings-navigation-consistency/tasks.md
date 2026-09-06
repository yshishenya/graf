# Tasks: Единая информационная архитектура меню GRAF

## Phase 1 — Contract

- [X] T001 Read shared cabinet/profile/theme/logout flow and installed Krisp IA.
- [X] T002 [US1] Update rendered browser/embedded menu contract tests in `apps/server/tests/unit/test_cabinet_web_shell.py`.
- [X] T003 [US2] Update disabled submenu/accessibility assertions in `apps/server/tests/contract/test_settings_ui_contract.py`.

## Phase 2 — Menu implementation

- [X] T004 [US1] Implement exact menu order, account/settings links, appearance form and native/browser quit states in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html`.
- [X] T005 [US2] Add minimal menu, separator, disabled-control and theme-picker narrow-layout styles in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.
- [X] T006 [US1] Extend existing account-preferences theme handling for menu auto-save in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.

## Phase 3 — Embedded lifecycle

- [X] T007 [US3] Add allowlisted embedded quit bridge and lifecycle validation in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`.
- [X] T008 [US3] Add `EmbeddedCabinetQuitBridge` contract tests in `apps/macos/Shared/Tests/EmbeddedCabinetQuitBridgeTests.swift`.

## Phase 4 — Validation and closeout

- [X] T009 Update `spec.md`, `plan.md`, `research.md`, `checklists/ux.md`, `CHANGELOG.md` and record clean-room/risk lane.
- [X] T010 Run focused pytest and native tests; run disposable-Postgres settings-flow tests.
- [X] T011 Run `infra/scripts/ci-local.sh --fast`, inspect wide/narrow rendered output and review final diff for secrets/scope drift.

## Dependencies

T001 → T002/T003 → T004/T005/T006 → T007/T008 → T009 → T010 → T011
