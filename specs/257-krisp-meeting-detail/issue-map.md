# Карта задач F257 и GitHub

Дата: 2026-09-08. Репозиторий: `yshishenya/graf`; remote проверен. Общая задача: [#6794](https://github.com/yshishenya/graf/issues/6794). Источник выполнения — [tasks.md](tasks.md).

Перед созданием проверены открытые и закрытые issues по feature:257, номеру257 в заголовке и пути фичи в body. Найдена только общая задача T000; совпадений владельцев T001–T010 не было. После создания повторно получены все11 записей:10 уникальных владельцев задач и одна общая задача.

| Task | Issue | Состояние GitHub |
|---|---|---|
| T001 | [#6797](https://github.com/yshishenya/graf/issues/6797) | OPEN |
| T002 | [#6798](https://github.com/yshishenya/graf/issues/6798) | OPEN |
| T003 | [#6800](https://github.com/yshishenya/graf/issues/6800) | OPEN |
| T004 | [#6801](https://github.com/yshishenya/graf/issues/6801) | OPEN |
| T005 | [#6803](https://github.com/yshishenya/graf/issues/6803) | OPEN |
| T006 | [#6804](https://github.com/yshishenya/graf/issues/6804) | OPEN |
| T007 | [#6806](https://github.com/yshishenya/graf/issues/6806) | OPEN |
| T008 | [#6808](https://github.com/yshishenya/graf/issues/6808) | OPEN |
| T009 | [#6809](https://github.com/yshishenya/graf/issues/6809) | OPEN |
| T010 | [#6810](https://github.com/yshishenya/graf/issues/6810) | OPEN |

Все10 задач получили canonical title,9 разделов, feature/priority/area/gate/type labels, критерии проверки, границы, ссылки на spec/plan/tasks и общую задачу. Реализация опубликована в черновике [PR #6826](https://github.com/yshishenya/graf/pull/6826); текущие доказательства — [validation/closeout.md](validation/closeout.md).

T001–T008 выполнены; их issues остаются OPEN до проверки закрытия на текущем PR SHA через `validate-issue-closeout.py` и русского поясняющего комментария. Старый PASS GitHub не распространяется на новые коммиты. T009/T010 не завершены: после разблокировки нативная приёмка источника/сворачивания остаётся PARTIAL, формальная граница SC-003, итоговая сверка и актуальный governance-fast ещё требуются. Карта OPEN не означает отсутствия выполненной реализации; автоматическое закрытие в PR не запрошено.

Mandatory ensure выполнен успешно без изменения общих файлов проекта. Итог validate и независимого принятия записывается в [readiness.md](readiness.md).
