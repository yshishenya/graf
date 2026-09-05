# Tasks F242

Source of truth: spec.md / plan.md. Owner: Codex, umbrella #6566.

## Phase 1: Regression baseline

- [X] T001 Добавить failing проверки FR-001–006 в apps/server/tests/unit/test_cabinet_audit_fixes.py и существующие contract tests до правок реализации.

## Phase 2: Independently testable user stories

- [X] T002 [US1] Сохранить профиль и остальные настройки при autosave темы в apps/server/src/twobrain_rec_server/cabinet/web_routes/{settings,billing,deletion,desktop,fair_use,referrals}.py, deletion_rendering.py и templates/cabinet/components/sections.html; проверить partial/full/invalid/stale forms и sibling routes.
- [X] T003 [US2] Добавить явное native trial подтверждение и честные предварительные/фактические даты в apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py и templates/cabinet/{components/sections,pages/billing_overview_content,pages/billing_plans_content}.html; не менять trial policy/guards.
- [X] T004 [US3] Исправить помощь и читаемые объёмы в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_history_content.html и cabinet/web_routes/billing.py; проверить email/no-email/empty и границы decimal units.
- [X] T005 [US4] Убрать повтор pending copy в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html, сохранить runtime hooks/live/recovery и проверить связанные unit/contract tests.

## Phase 3: Validation and handoff

- [ ] T006 Проверить high-risk-product lane по specs/242-cabinet-audit-fixes/quickstart.md, выполнить browser QA, correctness/Ponytail review и converge; записать metadata-only evidence и changes/unreleased/F242.yaml, подготовить PR с exact-SHA governance-fast и issue evidence.

## GitHub ownership

T001 → #6579; T002 → #6572; T003 → #6569; T004 → #6570; T005 → #6571; T006 → #6580. Все OPEN, umbrella #6566. Issue canon ensure/validate выполнены до implementation.

## Dependencies and validation

T001 → T002 → T003 → T004 → T005 → T006. Общие templates/routes не правятся параллельно. US1–US4 имеют отдельные acceptance checks из spec. Reviewer-owned checklists не являются implementation tasks. Commit после validation/approval; merge/release/deploy вне scope.

Implementation evidence: [validation.md](validation.md). T001–T005 проверены; post-validation approval на commit/push получен. T006 остаётся открыт до публикации PR и exact-SHA GitHub gate. Открытые issues не объявлены закрытыми до этого шага.
