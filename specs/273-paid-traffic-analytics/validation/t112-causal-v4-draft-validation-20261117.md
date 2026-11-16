# T112 — проект точного наблюдения normal POST2 и fault POST1

17.11.2026. Автор `/root`. Существующие F273/T112/#7698 и T113/#7804;
полоса `high-risk-product`. Основа до этого checkpoint:
`0b87d4a468f31035ec52cada7f342a5fe482c5dd`.

## Что реализовано

Новая версия4 временного диагностического pytest-plugin реализует проект
из [независимого v2 rereview](t112-repeat-trace-rereview-20261116.md).
[Исходник наблюдателя](t112-causal-trace-v4-20261117.py) сохранён как черновик,
не добавлен в conftest и автоматически не включается. Его SHA-256:
`57f5b85170a858c8cea6890974d4073dd6fb494745a0122e149cf00d566ec846`.
Копия вне дерева `/private/tmp/graf-t112-causal-trace-v4-20261117.py` побайтово
равна сохранённому файлу; версии1–3 сохранены без изменений.

Область fixture — только точный native test
`test_real_commit_acknowledgement_and_idle_return_keep_pair_and_foreign_generation`,
обе параметризации. Для normal подробно наблюдается POST2, для fault — POST1
и достигнутый POST2. Новых HTTP-запросов нет. Источники integration, budget и
рабочий guard закреплены SHA-256 и проверяются до установки tracer.

- Выбранные line/exception events guard/operation/join/unavailable дают
  metadata сроков, cleanup, размеров буфера и состояния собственных задач.
  Coroutine return не выдаётся за окончательное завершение.
- Test-only ASGI adapter делегирует один app и исходные receive/send. Он
  различает send attempted/completed и app return/raise; исключения
  распространяются. В журнал не идут body, headers, URL, proof или SQL.
- Независимые M1/relay сохраняют пустой Context(). Их code objects и точный
  target stream связываются отдельно; HTTP ContextVar не используется как
  доказательство их охвата. Фактический аргумент выбранного M1 timeout_at
  наблюдается до вызова без пересчёта/подмены.
- Снимок сценария на строке1271 снимается до armed=False, отмены watchdog,
  открытия gates и отмены задач. Ранний exception observer имеет отдельный
  snapshot. Счётчики relay до target-binding сохранены по stream ordinal;
  ordinal5 объединяет более поздние потоки, если их окажется больше четырёх.
- До96 записей плюс counters/dropped; в журнал не сохраняются ссылки на
  frames/tasks/owners/исключения, payload и тексты ошибок. Временные ссылки
  fixture очищаются при её завершении.

Наблюдатель пока **не принят независимым ревью и не допущен к HTTP/PG**.
Его полнота и влияние ещё требуют точного чтения. Наличие этого исходника
не доказывает причину прежних отказов и не заменяет проверку реальных frames.

## Реально исполненная ограниченная проверка

[Selfcheck](t112-causal-adapter-selfcheck-20261117.py), SHA-256
`3cc53c8f8463c9475ce57b4124bbcd1d37d1bb48568512bbfc998c0720d09732`.
Из AST извлекаются только пять функций adapter/post/append/task_state/snapshot.
Остальная fixture, её imports application, tracer и реальные HTTP/DB не запускаются.

Исполненная команда использовала две побайтово равные временные копии:

```sh
python3 /private/tmp/graf-t112-causal-adapter-selfcheck-20261117.py   /private/tmp/graf-t112-causal-trace-v4-20261117.py
```

EXIT0, stdout:
`causal_adapter_selfcheck=PASS cases=10 network_calls=0 database_calls=0`.
Это результат завершённого exec_command в текущем диалоге. Результат также
транскрибирован в `/private/tmp/graf-t112-causal-adapter-selfcheck-20261117.json`;
это явная транскрипция, а не перенаправленный исходный журнал процесса.

Десять случаев: normal POST1 без подробных событий, normal POST2 и fault POST1
с успешным send, исходная ошибка app, ошибка/отмена send, original post success/
error/cancel с identity и ContextVar reset, cap96/dropped4 на100 попытках записи.
Проверяется ровно одно делегирование app/post и сохранение аргументов и объектов
сообщений. Синтетическое private body/headers не попадает в records.
Синтаксис разобран AST; статический поиск не нашёл вызовов json()/all_tasks()/
sleep()/read()/execute() в plugin. Это ограниченная проверка делегирования,
не упражнение trace branches и не приёмка приложения.

## Оставшийся gate

Подготовлено поручение существующему reviewer:
`/private/tmp/graf-t112-causal-v4-review-request-20261117.txt`.
**Файл поручения не является доставкой, живым процессом или verified wait.**
Новый FINAL по точной версии4 ещё не получен. Следующее необходимое действие —
реально передать поручение существующему `/root/public_counter_readiness_review`
и разобрать его заключение. Новых агентов не создавать. До PASS не исполнять
наблюдатель с HTTP/PostgreSQL. После PASS возможен только один адресный опыт
двух native параметризаций; общий87 не назначен. Исходные сроки2s/work1.5s/
cleanup0.5s, F/B, caps, locks и assertions не изменялись.

В текущем проходе18 прежних input hashes SAME, prerequisite с tasks PASS,
issue7698 OPEN и содержит T112. Требования/проект/договоры в применимых разделах
прочитаны; reviewer-owned отметки не менялись. Прежние scoped PASS v3/P2-D01
и checkout/P2-01 не принимают новую версию4 автоматически.

## Что остаётся неизвестным

Причины исторического repeated unavailable, нового normal POST2 без завершённого
ASGI-ответа и раннего fault response_held timeout не установлены. Прежние
65PASS/22FAIL не повторялись и не заменены selfcheck10PASS. Новый отчёт Метрики
за завершённую неделю не прочитан: UI-действия после чтения документации в этом
проходе не выполнялись, неисправность кабинета/CUA/Mac этим не установлена.

Рабочий код, сайт/контент/вёрстка, Postal, nginx/DNS/Compose, службы, backups и
настройки не менялись. Настоящий ingest._result_period_context остаётся yield None.
T112/T113/T098/restore/readiness/T0 и коммерческие критерии открыты. Внешние
визиты/регистрации/оплаты этим checkpoint не доказаны. Выпуска/PR/merge/CD нет.
