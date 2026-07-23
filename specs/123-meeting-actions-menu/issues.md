# GitHub issues и closeout: Feature 123

`tasks.md` остаётся источником правды по реализации. Эти ссылки связывают
исполняемые задачи с созданными GitHub issues. Реализация принята PR #4278,
релиз подготовлен PR #4279, опубликован как `v2026.07.23.2` и выкачен в
production; closure-комментарии содержат тот же проверяемый evidence.

| Task | GitHub issue | Результат | Состояние |
|---|---|---|---|
| T001 | [#4254](https://github.com/yshishenya/crisp/issues/4254) | Зафиксированы выбранный вариант и risk lane | Closed — PR #4278, релиз `v2026.07.23.2` |
| T002 | [#4255](https://github.com/yshishenya/crisp/issues/4255) | Зафиксированы границы данных и authority map | Closed — PR #4278, релиз `v2026.07.23.2` |
| T003 | [#4256](https://github.com/yshishenya/crisp/issues/4256) | Закреплён контракт компактного меню | Closed — PR #4278, релиз `v2026.07.23.2` |
| T004 | [#4257](https://github.com/yshishenya/crisp/issues/4257) | Закреплён keyboard/focus контракт | Closed — PR #4278, релиз `v2026.07.23.2` |
| T005 | [#4258](https://github.com/yshishenya/crisp/issues/4258) | Обновлены meeting-detail интеграционные ожидания | Closed — PR #4278, релиз `v2026.07.23.2` |
| T006 | [#4259](https://github.com/yshishenya/crisp/issues/4259) | Собрано компактное меню на существующих действиях | Closed — PR #4278, релиз `v2026.07.23.2` |
| T007 | [#4260](https://github.com/yshishenya/crisp/issues/4260) | Сохранена server capability truth и фильтрация | Closed — PR #4278, релиз `v2026.07.23.2` |
| T008 | [#4261](https://github.com/yshishenya/crisp/issues/4261) | Оформлено выбранное меню GRAF | Closed — PR #4278, релиз `v2026.07.23.2` |
| T009 | [#4262](https://github.com/yshishenya/crisp/issues/4262) | Добавлено полное клавиатурное управление | Closed — PR #4278, релиз `v2026.07.23.2` |
| T010 | [#4263](https://github.com/yshishenya/crisp/issues/4263) | Сведения вынесены в отдельный диалог | Closed — PR #4278, релиз `v2026.07.23.2` |
| T011 | [#4264](https://github.com/yshishenya/crisp/issues/4264) | Диалог сведений получил focus trap и close states | Closed — PR #4278, релиз `v2026.07.23.2` |
| T012 | [#4265](https://github.com/yshishenya/crisp/issues/4265) | Диалог сведений адаптивен и поддерживает темы | Closed — PR #4278, релиз `v2026.07.23.2` |
| T013 | [#4266](https://github.com/yshishenya/crisp/issues/4266) | Сохранено безопасное удаление и его server contract | Closed — PR #4278, релиз `v2026.07.23.2` |
| T014 | [#4267](https://github.com/yshishenya/crisp/issues/4267) | Возвращается фокус к видимому триггеру | Closed — PR #4278, релиз `v2026.07.23.2` |
| T015 | [#4268](https://github.com/yshishenya/crisp/issues/4268) | Переиспользованы доступные иконки GRAF | Closed — PR #4278, релиз `v2026.07.23.2` |
| T016 | [#4269](https://github.com/yshishenya/crisp/issues/4269) | Покрыты capability и browser/embedded parity | Closed — PR #4278, релиз `v2026.07.23.2` |
| T017 | [#4270](https://github.com/yshishenya/crisp/issues/4270) | Пройдена keyboard/zoom/theme/contrast матрица | Closed — PR #4278, релиз `v2026.07.23.2` |
| T018 | [#4271](https://github.com/yshishenya/crisp/issues/4271) | Визуальный QA завершён: `final result: passed` | Closed — PR #4278, релиз `v2026.07.23.2` |
| T019 | [#4272](https://github.com/yshishenya/crisp/issues/4272) | Обновлён пользовательский changelog | Closed — PR #4278, релиз `v2026.07.23.2` |
| T020 | [#4273](https://github.com/yshishenya/crisp/issues/4273) | Пройдены focused closeout checks | Closed — PR #4278, релиз `v2026.07.23.2` |
| T021 | [#4274](https://github.com/yshishenya/crisp/issues/4274) | Пройден полный локальный CI, evidence записан | Closed — PR #4278, релиз `v2026.07.23.2` |
| T022 | [#4275](https://github.com/yshishenya/crisp/issues/4275) | Ponytail review завершён без лишней сложности | Closed — PR #4278, релиз `v2026.07.23.2` |
| T023 | [#4276](https://github.com/yshishenya/crisp/issues/4276) | Mapping и PR evidence подготовлены | Closed — PR #4278, релиз `v2026.07.23.2` |

## Validation and release evidence

- Risk/validation lane: **significant/high-risk feature**.
- Focused suite: `88 passed, 2 warnings`.
- Canonical local gate: `infra/scripts/ci-local.sh` — `ci_local_result=pass`;
  Swift 608 tests, server `2193 passed, 1 skipped` (implementation run),
  strict `41 passed, 1 skipped`, lint/compile/compose/evidence checks passed.
- Production execute повторно прогнал локальный CI перед SSH: server `2200
  passed, 1 skipped, 11 warnings` (parallel), strict `41 passed, 1 skipped`,
  lint/compile/compose/evidence checks passed.
- Local postgres RLS probe intentionally reports `blocked`, because production
  truth is not probed from the isolated local environment. Remote disposable
  `postgres_test` RLS hardening validation passed; live production RLS probe
  в этом receipt не выполнялся (`live_production_probe=not_attempted`).
- Design QA: [design-qa.md](design-qa.md), `final result: passed`; comparison
  captures are synthetic and metadata-safe.
- PR: [#4278](https://github.com/yshishenya/crisp/pull/4278), merge commit
  `151e906dba1099bffc4b9029d918b1a054ac93ce`.
- Release preparation: [#4279](https://github.com/yshishenya/crisp/pull/4279),
  merge commit `376bc07ba2a7b4fe8ded628afe5e4265c79231db`.
- Release: [v2026.07.23.2](https://github.com/yshishenya/crisp/releases/tag/v2026.07.23.2),
  annotated tag points to `376bc07ba2a7b4fe8ded628afe5e4265c79231db`.
- Production deploy: `infra/scripts/cd-remote.sh --dry-run` and
  `--execute --branch codex/deploy-v202607232` passed. Receipt: `deploy_result=pass`,
  `deployed_sha=376bc07ba2a7b4fe8ded628afe5e4265c79231db`,
  `readiness_verdict=infra_smoke_ready`, smoke `pass`, cleanup `pass`,
  automatic dispatch `pass`; backup reference
  `/opt/projects/2brain-rec/backups/20260723T020318Z`.

## Closeout rule

All implementation tasks are accepted, the release is published and the
production receipt is available. Post one Russian closure comment per issue
with the relevant evidence, then close #4254–#4276. Do not extend this
closeout to unrelated issues or claim live RLS probing beyond the receipt.
