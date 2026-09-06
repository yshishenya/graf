# F238 — формат локальной записи

F238 — номер небольшого релизного продолжения F231, а не новая функция записи.
Этот каталог регистрирует существующий срез для release manifest. Продуктовый
код и требования здесь не дублируются и не меняются.

- Требования: [F231 spec](../231-local-recording-handoff/spec.md), применимые FR-001–005, FR-009, FR-013.
- План и источник задач: [F231 plan](../231-local-recording-handoff/plan.md),
  [tasks T007/T009](../231-local-recording-handoff/tasks.md).
- Ограничение: формат даты, распознавание автоматического технического названия
  и единая пиктограмма удаления. Пользовательские названия, права и действия
  сохраняются.
- Проверка: [review/convergence F238](../231-local-recording-handoff/F238-review-convergence.md),
  27 исполняемых примеров, 6 assertions и 17 XCTest PASS.
- PR: https://github.com/yshishenya/graf/pull/6504.
- GitHub gate: https://github.com/yshishenya/graf/actions/runs/33997905811,
  exact head `26e62110e8b2d4ac18ec61b69faff13388dbe8ac`, SUCCESS.
- После rebase merge: `107e7e692b896863f70ba632a101469d6f80e29a`.
- Issue: https://github.com/yshishenya/graf/issues/6392; umbrella F231 не
  закрывается этим срезом. Новые задачи реализации не создаются.

Регистрация каталога — docs-only metadata в общем release lane. Окончательные
Full CI, tag, публикация и production evidence принадлежат оператору выпуска.
