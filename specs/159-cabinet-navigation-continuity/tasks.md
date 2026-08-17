# Tasks: Непрерывная навигация кабинета

**Input**: Design documents from `specs/159-cabinet-navigation-continuity/`

**Risk lane**: `high-risk-feature`. Shared shell, profile presentation and
auth-adjacent UI require contract-first tests, security/UX checklists, focused
validation and `infra/scripts/ci-local.sh --fast` before closeout.

**Issue sync**: T001–T015 already have open canonical GitHub issues #5235–#5249;
do not create duplicate issues.

## Phase 1: Contract baseline

**Purpose**: Freeze behavior before changing the shared shell. Contract tasks are
independent where they touch different test files.

- [ ] T001 [P] [US1] Зафиксировать единый toggle, truthful action label, `aria-expanded`, `aria-controls`, focus retention и две последовательные активации в `apps/server/tests/unit/test_cabinet_web_shell.py` и `apps/server/tests/contract/test_cabinet_static_assets_contract.py`.
- [ ] T002 [P] [US1] Зафиксировать ненулевой gap между search icon и текстом, decorative pointer behavior и narrow/loading/disabled/focus states в `apps/server/tests/unit/test_cabinet_web_shell.py` и `apps/server/tests/contract/test_cabinet_static_assets_contract.py`.
- [ ] T003 [P] [US3] Закрепить unknown-email rejection, explicit signup, invitation/provider, email-code, expired-session и `/sign-up` compatibility в `apps/server/tests/contract/test_account_routes.py` и `apps/server/tests/integration/test_web_owner_session_context.py`.
- [ ] T004 [P] [US1] Закрепить ровно один browser `/download` sidebar CTA, ноль embedded sidebar CTA и accessible keyboard contract в `apps/server/tests/unit/test_cabinet_web_shell.py`.
- [ ] T005 [P] [US1] Закрепить safe profile projection, long/missing data, Escape/outside close, focus return и существующий CSRF logout в `apps/server/tests/unit/test_cabinet_web_shell.py` и `apps/server/tests/contract/test_cabinet_static_assets_contract.py`.
- [ ] T006 [P] [US2] Закрепить одну settings rail, canonical «К встречам», selected `aria-current`, все category/calendar routes, browser/embedded parity и отсутствие nested rail в `apps/server/tests/unit/test_cabinet_web_shell.py` и `apps/server/tests/integration/test_settings_ia_flow.py`.

**Checkpoint**: Contract tests name every acceptance boundary before runtime
markup/CSS/JS changes.

## Phase 2: User Story 1 — стабильный кабинет (Priority: P1)

**Goal**: Make the shared shell understandable and idempotent without changing
route ownership or server authorization.

**Independent Test**: T001, T002, T004 and T005 pass; the synthetic browser/
embedded matrix shows stable toggle, search spacing, surface-aware CTA and safe
profile menu.

- [ ] T007 [US1] Обновить общий toggle markup и guarded initialization в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html` и `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, сохранив active navigation, stable hit target и focus return.
- [ ] T008 [US1] Исправить существующий search spacing/pointer CSS contract без нового компонента или JS state в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.
- [ ] T009 [US3] Привести login copy/CTA к проверенному auth contract в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/auth/login.html`, сохранив `/sign-up`, invitation/provider/email-code callers и unchanged backend semantics.
- [ ] T010 [US1] Добавить один web-only `/download` CTA в нижнюю часть shared sidebar, убрать competing settings-recording CTA и сохранить embedded native updater в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_recording_content.html` и `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.
- [ ] T011 [US1] Передать существующую safe `AccountSettingsSurface.profile` проекцию в guarded profile menu с wrapping, Escape/outside close, focus return и existing logout form в `apps/server/src/twobrain_rec_server/cabinet/rendering_shared.py`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` и `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.

**Checkpoint**: Shared shell scenarios are independently demonstrable in web and
embedded render checks.

## Phase 3: User Story 2 — одна rail в настройках (Priority: P1)

**Goal**: Replace competing global/inner settings navigation with one clear
primary rail while preserving all existing categories, forms and routes.

**Independent Test**: T006 passes for every settings/category/calendar route in
browser and embedded modes at desktop and narrow viewport sizes.

- [ ] T012 [US2] Перенести существующие category links в primary sidebar, скрыть nested settings navigation из visual/accessibility tree, добавить canonical «К встречам» и сохранить active category в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/shell.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/settings_navigation.html` и `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.

**Checkpoint**: Every existing settings destination remains reachable with one
visible accessible rail and no horizontal overflow.

## Phase 4: Review and validation

**Purpose**: Close root-cause review findings and prove browser/embedded parity.

- [ ] T013 [US1] Выполнить focused pytest selectors из `specs/159-cabinet-navigation-continuity/quickstart.md`, `node --check` для `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` и добавить минимальные regression assertions для каждого найденного root cause.
- [ ] T014 [US1] Провести auth/privacy/accessibility/localization/clean-room review изменённых путей и зафиксировать findings/result в `specs/159-cabinet-navigation-continuity/analysis.md`; исправить каждый actionable finding.
- [ ] T015 [US1] Пройти synthetic visual matrix browser/embedded для light/dark, keyboard, narrow и reduced-motion и запустить `infra/scripts/ci-local.sh --fast`; записать exact SHA, result и environment limitations в `specs/159-cabinet-navigation-continuity/quickstart.md`.

## Dependencies & Execution Order

### Phase dependencies

- Contract baseline (T001–T006) has no runtime dependency and can run in
  parallel by test file, but same-file edits must be serialized.
- User Story 1 implementation (T007–T011) depends on its matching contracts;
  T009 is auth-copy-only and must not change auth routes.
- User Story 2 implementation (T012) starts after T007, T008, T010 and T011
  because it shares the sidebar/templates/CSS surface.
- Review/validation (T013–T015) runs sequentially after T012.

### Parallel opportunities

- T001–T006 can be split by test ownership before implementation.
- After their contracts pass, T007, T008, T009 and T010 can proceed separately;
  T011 shares shell JS/template files and follows T007.

### Issue mapping

| Task | Existing issue |
|---|---:|
| T001 | #5235 |
| T002 | #5236 |
| T003 | #5237 |
| T004 | #5238 |
| T005 | #5239 |
| T006 | #5240 |
| T007 | #5241 |
| T008 | #5242 |
| T009 | #5243 |
| T010 | #5244 |
| T011 | #5245 |
| T012 | #5246 |
| T013 | #5247 |
| T014 | #5248 |
| T015 | #5249 |

## Implementation strategy

1. Contract-first: make existing issue acceptance criteria executable without
   introducing new state or dependencies.
2. MVP: ship one coherent shared shell (T007–T011), then settings mode (T012).
3. Closeout: run focused checks, review, synthetic matrix and fast lane once;
   leave production, release and native Feature 160 work out of scope.
