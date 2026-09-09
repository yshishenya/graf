# Карта задач F257 и GitHub

Дата: 2026-09-09. Репозиторий: `yshishenya/graf`; remote проверен. Общая задача: [#6794](https://github.com/yshishenya/graf/issues/6794). Источник выполнения — [tasks.md](tasks.md).

Перед созданием проверены открытые и закрытые issues по feature:257, номеру257 в заголовке и пути фичи в body. Найдена только общая задача T000; совпадений владельцев T001–T010 не было. После создания повторно получены все11 записей:10 уникальных владельцев задач и одна общая задача.

| Task | Issue |
|---|---|
| T001 | [#6797](https://github.com/yshishenya/graf/issues/6797) |
| T002 | [#6798](https://github.com/yshishenya/graf/issues/6798) |
| T003 | [#6800](https://github.com/yshishenya/graf/issues/6800) |
| T004 | [#6801](https://github.com/yshishenya/graf/issues/6801) |
| T005 | [#6803](https://github.com/yshishenya/graf/issues/6803) |
| T006 | [#6804](https://github.com/yshishenya/graf/issues/6804) |
| T007 | [#6806](https://github.com/yshishenya/graf/issues/6806) |
| T008 | [#6808](https://github.com/yshishenya/graf/issues/6808) |
| T009 | [#6809](https://github.com/yshishenya/graf/issues/6809) |
| T010 | [#6810](https://github.com/yshishenya/graf/issues/6810) |

Все10 задач получили canonical title,9 разделов, feature/priority/area/gate/type labels, критерии проверки, границы, ссылки на spec/plan/tasks и общую задачу. Реализация опубликована в черновике [PR #6826](https://github.com/yshishenya/graf/pull/6826); текущие доказательства — [validation/closeout.md](validation/closeout.md).

Карта хранит уникальную связь задач с issues; текущее состояние GitHub доступно по каждой ссылке. Состояние реализации и приёмки — в tasks.md и validation/closeout.md. Закрытие каждой task issue выполняется после чтения актуальной записи, понятного русского closure comment и validate-issue-closeout.py с окончательным PR SHA и его GitHub governance-fast. Общая задача6794 остаётся открытой до merge: её live validator дополнительно требует merged PR. Снятие draft не является слиянием или выпуском.

Mandatory ensure выполнен успешно без изменения общих файлов проекта. Итог validate и независимого принятия записывается в [readiness.md](readiness.md).
