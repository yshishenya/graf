# GitHub issues и closeout: Feature 123

`tasks.md` остаётся источником правды по реализации. Эти ссылки связывают
исполняемые задачи с созданными GitHub issues; закрытие issues выполняется
после принятия PR и публикации релиза, когда evidence можно приложить к
closure-комментарию.

| Task | GitHub issue | Результат | Состояние |
|---|---|---|---|
| T001 | [#4254](https://github.com/yshishenya/crisp/issues/4254) | Зафиксированы выбранный вариант и risk lane | Open — ждёт PR |
| T002 | [#4255](https://github.com/yshishenya/crisp/issues/4255) | Зафиксированы границы данных и authority map | Open — ждёт PR |
| T003 | [#4256](https://github.com/yshishenya/crisp/issues/4256) | Закреплён контракт компактного меню | Open — ждёт PR |
| T004 | [#4257](https://github.com/yshishenya/crisp/issues/4257) | Закреплён keyboard/focus контракт | Open — ждёт PR |
| T005 | [#4258](https://github.com/yshishenya/crisp/issues/4258) | Обновлены meeting-detail интеграционные ожидания | Open — ждёт PR |
| T006 | [#4259](https://github.com/yshishenya/crisp/issues/4259) | Собрано компактное меню на существующих действиях | Open — ждёт PR |
| T007 | [#4260](https://github.com/yshishenya/crisp/issues/4260) | Сохранена server capability truth и фильтрация | Open — ждёт PR |
| T008 | [#4261](https://github.com/yshishenya/crisp/issues/4261) | Оформлено выбранное меню GRAF | Open — ждёт PR |
| T009 | [#4262](https://github.com/yshishenya/crisp/issues/4262) | Добавлено полное клавиатурное управление | Open — ждёт PR |
| T010 | [#4263](https://github.com/yshishenya/crisp/issues/4263) | Сведения вынесены в отдельный диалог | Open — ждёт PR |
| T011 | [#4264](https://github.com/yshishenya/crisp/issues/4264) | Диалог сведений получил focus trap и close states | Open — ждёт PR |
| T012 | [#4265](https://github.com/yshishenya/crisp/issues/4265) | Диалог сведений адаптивен и поддерживает темы | Open — ждёт PR |
| T013 | [#4266](https://github.com/yshishenya/crisp/issues/4266) | Сохранено безопасное удаление и его server contract | Open — ждёт PR |
| T014 | [#4267](https://github.com/yshishenya/crisp/issues/4267) | Возвращается фокус к видимому триггеру | Open — ждёт PR |
| T015 | [#4268](https://github.com/yshishenya/crisp/issues/4268) | Переиспользованы доступные иконки GRAF | Open — ждёт PR |
| T016 | [#4269](https://github.com/yshishenya/crisp/issues/4269) | Покрыты capability и browser/embedded parity | Open — ждёт PR |
| T017 | [#4270](https://github.com/yshishenya/crisp/issues/4270) | Пройдена keyboard/zoom/theme/contrast матрица | Open — ждёт PR |
| T018 | [#4271](https://github.com/yshishenya/crisp/issues/4271) | Визуальный QA завершён: `final result: passed` | Open — ждёт PR |
| T019 | [#4272](https://github.com/yshishenya/crisp/issues/4272) | Обновлён пользовательский changelog | Open — ждёт PR |
| T020 | [#4273](https://github.com/yshishenya/crisp/issues/4273) | Пройдены focused closeout checks | Open — ждёт PR |
| T021 | [#4274](https://github.com/yshishenya/crisp/issues/4274) | Пройден полный локальный CI, evidence записан | Open — ждёт PR |
| T022 | [#4275](https://github.com/yshishenya/crisp/issues/4275) | Ponytail review завершён без лишней сложности | Open — ждёт PR |
| T023 | [#4276](https://github.com/yshishenya/crisp/issues/4276) | Mapping и PR evidence подготовлены | Open — ждёт принятия PR |

## Validation and release evidence

- Risk/validation lane: **significant/high-risk feature**.
- Focused suite: `88 passed, 2 warnings`.
- Canonical local gate: `infra/scripts/ci-local.sh` — `ci_local_result=pass`;
  Swift 608 tests, server `2193 passed, 1 skipped` (parallel), strict
  `41 passed, 1 skipped`, lint/compile/compose/evidence checks passed.
- Local postgres RLS probe intentionally reports `blocked`, because production
  truth is not probed from the isolated local environment. Remote release gate
  remains mandatory.
- Design QA: [design-qa.md](design-qa.md), `final result: passed`; comparison
  captures are synthetic and metadata-safe.
- PR: [#4278](https://github.com/yshishenya/crisp/pull/4278), commit
  `6010cee80c8b29cbf68922356a02d3615ec888ac`.
- Release/deploy: `infra/scripts/cd-remote.sh --dry-run` completed and listed
  the clean-worktree, pinned-SHA, backup/restore, secret, migration, worker,
  smoke and rollback gates. `--execute` was intentionally not run from this
  feature branch; it requires PR merge, release tag preparation and explicit
  approval.

## Closeout rule

After the PR is accepted, post one Russian closure comment per completed issue
with the relevant evidence, and close #4254–#4276 together only when the
release/rollback evidence is available. Do not claim production availability
before that gate.
