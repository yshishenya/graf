# Tasks: Боковая навигация настроек

**Input**: [spec.md](spec.md), [plan.md](plan.md), [contracts/settings-ui-sidebar.md](contracts/settings-ui-sidebar.md)

## Phase 1: Contract and model

- [X] T001 [P1] Add browser/embedded grouped-sidebar assertions for all six canonical IDs, group order, href parity, selected state and `aria-current` in `apps/server/tests/contract/test_settings_ui_contract.py`.
- [X] T002 [P1] Add route-wide sidebar and active-parent assertions for browser/embedded category and calendar paths in `apps/server/tests/integration/test_settings_ia_flow.py`.
- [X] T003 [P1] Add presentation-only `group_label` metadata to `SettingsCategoryView` and the explicit definitions in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`.

## Phase 2: Sidebar implementation

- [X] T004 [P1] Render grouped semantic settings navigation while preserving ordinary links, active state, scope-safe content and existing browser/embedded hrefs in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/settings_navigation.html`.
- [X] T005 [P1] Replace horizontal settings navigation with a desktop inner rail/content grid and a narrow vertical layout, including wrapping labels, 44px targets and visible focus treatment, in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.
- [X] T006 [P1] Ensure calendar and provider-link settings roots participate in the shared settings rail layout without changing their full-shell or HTMX fragment behavior in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/provider_link_settings.html`.

## Phase 3: Boundary regression coverage

- [X] T007 [P1] Extend calendar/provider-link and cabinet-shell contract assertions to verify the inner settings landmark is present while global navigation, CSRF, safe-copy and fragment boundaries remain unchanged in `apps/server/tests/contract/test_calendar_settings_contract.py`, `apps/server/tests/contract/test_provider_link_settings_contract.py` and `apps/server/tests/unit/test_cabinet_web_shell.py`.
- [X] T008 [P2] Add source-level responsive/accessibility assertions for no horizontal-only settings navigation, visible group labels and focus/target styles in `apps/server/tests/contract/test_settings_ui_contract.py`.

## Phase 4: Validation and closeout

- [X] T009 [P1] Run the feature quickstart, focused settings test set and `git diff --check`; record evidence in the implementation handoff using `specs/135-settings-sidebar/quickstart.md`.
- [X] T010 [P1] Run `infra/scripts/ci-local.sh`, review the final diff for route/security/product-gate regressions, and update `CHANGELOG.md` under `[Unreleased]` with the sidebar UX change.

## Dependencies

- T001 and T003 define the contract/model before T004.
- T004 and T005 are the core implementation; T006 is needed for calendar parity.
- T007 and T008 validate the shared shell and responsive/a11y behavior after implementation.
- T009 precedes T010 and any commit/PR request.
