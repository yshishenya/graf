# F280 — сверка внешнего трекера

Дата: 2026-09-30. Результат `$speckit-taskstoissues closeout`: **implementation ready; tracker pending**.

Перед каждым сообщением заново прочитаны живые title/body/state/comments. Принадлежность установлена по каноническому заголовку, полю Spec tasks и точному пути `specs/280-payment-clarity/tasks.md`; umbrella содержит F280. Исходные критерии не заменялись. После записи каждое сообщение перечитано, его содержание и сохранение OPEN подтверждены.

В 13 существующих issues добавлено по одному русскому сообщению о локальном результате и незавершенной приемке. Дубликатов сообщений и новых issues нет. **Закрыто 0, ранее закрытых 0, осталось открытыми 13**: #7366 и #7368–#7379.

| Issue / задача | Проверенное сообщение | Почему остается открытой |
| --- | --- | --- |
| [#7366](https://github.com/yshishenya/graf/issues/7366) / T000 | [Статус](https://github.com/yshishenya/graf/issues/7366#issuecomment-5900001925) | Общая фича: нет PR/merge/точного проверенного SHA; T011/T012 обязательны. |
| [#7368](https://github.com/yshishenya/graf/issues/7368) / T001 | [Статус](https://github.com/yshishenya/graf/issues/7368#issuecomment-5899966898) | Локальная задача выполнена; исходный критерий требует PR и точный SHA с обязательными проверками. |
| [#7369](https://github.com/yshishenya/graf/issues/7369) / T002 | [Статус](https://github.com/yshishenya/graf/issues/7369#issuecomment-5899988914) | Локальная задача выполнена; исходный критерий требует PR и точный SHA с обязательными проверками. |
| [#7370](https://github.com/yshishenya/graf/issues/7370) / T003 | [Статус](https://github.com/yshishenya/graf/issues/7370#issuecomment-5899990287) | Локальная задача выполнена; исходный критерий требует PR и точный SHA с обязательными проверками. |
| [#7371](https://github.com/yshishenya/graf/issues/7371) / T004 | [Статус](https://github.com/yshishenya/graf/issues/7371#issuecomment-5899991587) | Локальная задача выполнена; исходный критерий требует PR и точный SHA с обязательными проверками. |
| [#7372](https://github.com/yshishenya/graf/issues/7372) / T005 | [Статус](https://github.com/yshishenya/graf/issues/7372#issuecomment-5899992754) | Локальная задача выполнена; исходный критерий требует PR и точный SHA с обязательными проверками. |
| [#7373](https://github.com/yshishenya/graf/issues/7373) / T006 | [Статус](https://github.com/yshishenya/graf/issues/7373#issuecomment-5899994003) | Локальная политика проверена; требуются PR/точный SHA checks и живое прохождение GRAF Dev. |
| [#7374](https://github.com/yshishenya/graf/issues/7374) / T007 | [Статус](https://github.com/yshishenya/graf/issues/7374#issuecomment-5899995202) | Локальная задача выполнена; исходный критерий требует PR и точный SHA с обязательными проверками. |
| [#7375](https://github.com/yshishenya/graf/issues/7375) / T008 | [Статус](https://github.com/yshishenya/graf/issues/7375#issuecomment-5899996273) | Локальная задача выполнена; исходный критерий требует PR и точный SHA с обязательными проверками. |
| [#7376](https://github.com/yshishenya/graf/issues/7376) / T009 | [Статус](https://github.com/yshishenya/graf/issues/7376#issuecomment-5899997425) | Локальная задача выполнена; исходный критерий требует PR и точный SHA с обязательными проверками. |
| [#7377](https://github.com/yshishenya/graf/issues/7377) / T010 | [Статус](https://github.com/yshishenya/graf/issues/7377#issuecomment-5899998688) | Локальная задача выполнена; исходный критерий требует PR и точный SHA с обязательными проверками. |
| [#7378](https://github.com/yshishenya/graf/issues/7378) / T011 | [Статус](https://github.com/yshishenya/graf/issues/7378#issuecomment-5899999693) | Требуются одобрение коммита, PR, governance-fast/macos-pr/pr-metadata на точном SHA и установленный GRAF Dev через harness. |
| [#7379](https://github.com/yshishenya/graf/issues/7379) / T012 | [Статус](https://github.com/yshishenya/graf/issues/7379#issuecomment-5900000611) | Человеческих прохождений 0/5; нужны SC-005 и сопоставимые агрегированные показатели SC-006. |

Кодовая редакция: manifest `328d7805ff57d15de4fdd19b6d3fb92d08a66fbf4a6b59ffaead4362eaced187`, 41 файл. Это не SHA коммита. В комментариях прямо указано, что локальные материалы пока не опубликованы в PR; несуществующие ссылки на файлы PR и CI не создавались.

Обязательный pre-hook `speckit-github-issue-canon-ensure` выполнен успешно. Post-hook `speckit-github-issue-canon-validate`: **OK, 300 Spec Kit issues проверено**. Допуск требований и analyze были получены до первой синхронизации; новое создание или расширение требований в этом closeout не выполнялось.

Проверка завершения с `--expected-sha` и `--verify-live` здесь не заявляется: утвержденного коммита/PR и обязательных доказательств еще нет, поэтому закрытие ни одной задачи не выполнялось. Финансовая приемка F278 и разрешение публичных продаж остаются отдельными.

Текущие локальные результаты и независимые заключения: [review-final.md](review-final.md), [validation.md](validation.md).
