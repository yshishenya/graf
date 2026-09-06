# Tasks F242

Source of truth: spec.md / plan.md. Owner: Codex, umbrella #6566.

## Phase 1: Regression baseline

- [X] T001 Добавить failing проверки FR-001–006 в apps/server/tests/unit/test_cabinet_audit_fixes.py и существующие contract tests до правок реализации.
  (Issue #6579)

## Phase 2: Independently testable user stories

- [X] T002 [US1] Сохранить профиль и остальные настройки при autosave темы в apps/server/src/twobrain_rec_server/cabinet/web_routes/{settings,billing,deletion,desktop,fair_use,referrals}.py, deletion_rendering.py и templates/cabinet/components/sections.html; проверить partial/full/invalid/stale forms и sibling routes.
  (Issue #6572)
- [X] T003 [US2] Добавить явное native trial подтверждение и честные предварительные/фактические даты в apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py и templates/cabinet/{components/sections,pages/billing_overview_content,pages/billing_plans_content}.html; не менять trial policy/guards.
  (Issue #6569)
- [X] T004 [US3] Исправить помощь и читаемые объёмы в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_history_content.html и cabinet/web_routes/billing.py; проверить email/no-email/empty и границы decimal units.
  (Issue #6570)
- [X] T005 [US4] Убрать повтор pending copy в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html, сохранить runtime hooks/live/recovery и проверить связанные unit/contract tests.
  (Issue #6571)

## Phase 3: Validation and handoff

- [X] T006 Проверить high-risk-product lane по specs/242-cabinet-audit-fixes/quickstart.md, выполнить browser QA, correctness/Ponytail review и converge; записать metadata-only evidence и changes/unreleased/F242.yaml, подготовить PR с exact-SHA governance-fast и issue evidence.
  (Issue #6580)

## GitHub ownership

T001 → #6579; T002 → #6572; T003 → #6569; T004 → #6570; T005 → #6571; T006 → #6580. Umbrella #6566. Issue canon ensure/validate выполнены до implementation. Задачи закрываются с отдельными evidence comments после проверки окончательного SHA; umbrella остаётся открытым до отдельного завершения фичи после merge.

## Dependencies and validation

T001 → T002 → T003 → T004 → T005 → T006. Общие templates/routes не правятся параллельно. US1–US4 имеют отдельные acceptance checks из spec. Reviewer-owned checklists не являются implementation tasks. Commit после validation/approval; merge/release/deploy вне scope.

Implementation evidence: [validation.md](validation.md). T001–T006 выполнены. PR #6582 опубликован; governance-fast PASS на `f2c3429e4cf88593b569e8091f080f6a79ecb4fa`, run 33995851709. Документационный коммит с этой записью требует нового exact-SHA gate; окончательная связка SHA/run фиксируется в PR и comments, без самоссылочного коммита. Merge/release/deploy не выполнялись.
