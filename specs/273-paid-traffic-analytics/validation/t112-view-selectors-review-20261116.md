# T112 — независимое ревью переноса выбора проекции

Дата:16.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Основа: `a3ff5b8709dc5da61f4751c4eb3145eb84d9fc9e` плюс два рабочих файла
с хешами ниже. Полоса: существующий `high-risk-product`, узкий изолированный
подшаг T112; серверная граница и рабочее измерение закрыты.

## Решение

**PASS узкой клиентской правки; P1=0, P2=0.** Текущий diff соответствует
выбранному и независимо принятому способу переносить штатный выбор проекции
в собственный POST, сохраняя ограничения query/JSON/видимости. Нового
доверенного источника, параметра разрешения или server-admission в diff нет.
Это не приёмка T112/T113 целиком, runtime, выпуска, T0, трафика или продаж.

## Собственное чтение и выводы

Прочитаны весь diff двух файлов, целиком текущий observer, новые10 причинных
случаев и их окружающий browser harness, неизменный Python wrapper, прежний
собственный server-preflight и применимые §§3–5 result-visibility. Повторно
прочитаны фактические вызовы review из browser и desktop GET.

- Target по-прежнему строится только из уже проверенного canonical own
  `state.path` плюс `/result-viewed` и текущего `location.origin`. Произвольный
  URL из DOM/query, fragment и прежняя целиком query не используются.
- В browser переносится только `summary_format` и `source_result_id`.
  `getAll(key).at(-1)` выбирает последнее значение, соответствуя Starlette
  QueryParams; `undefined` отличает отсутствующий ключ от присутствующего
  пустого последнего значения. Предыдущее непустое не подставляется.
- `new URLSearchParams(state.query)` разбирает актуальный сохранённый query,
  а `target.searchParams.set` заново кодирует выбранное значение. Пробел,
  плюс, кириллица и URL-разделители остаются частью значения, не вторым ключом,
  путём или fragment. Другие поля, включая proof, не переносятся.
- Embedded переносит только `summary_format`, как существующий desktop GET.
  `source_result_id` не начинает выбирать другую проекцию только в POST.
  Поддержка этого выбора desktop GET и новый серверный обработчик этим diff
  не вводятся и не заявляются.
- Перед построением URL сохранены проверки `current`/visibility после
  frame/native await. Они связывают snapshot query/path/root/node/proof/CSRF,
  а для embedded также nonce. Изменение query по-прежнему отменяет старую
  попытку и не даёт автоматического retry при непрерывной видимости.
- JSON остаётся ровно `{proof}`. CSRF/header, credentials same-origin,
  no-store, redirect:error, AbortController и прежний 2s бюджет попытки,
  bounded reply, renewal и отсутствие persistent queue не изменены.
  Обязательная серверная проверка недоверенного выбора/HMAC/access/source
  остаётся будущей частью T112; клиентский перенос её не заменяет.

Harness теперь определяет endpoint по pathname URL, поэтому запросы с query
попадают в тот же перехват и не получают вместо API ответа фиктивный HTML.
Добавленные7 browser случаев покрывают каждый ключ отдельно, оба вместе,
последние дубли, пустые последние, кодирование и исключение остальных query/
fragment. Добавленные3 embedded случая покрывают отсутствие source_result_id,
пустой последний summary_format и выбранный summary_format при наличии
игнорируемого source_result_id. Каждый ждёт ровно один POST, проверяет
canonical pathname, точный список query, пустой hash и JSON только с proof.
Прежний базовый случай отдельно проверяет method/CSRF/полный URL и отсутствие
повтора; прежние freshness/visibility/native случаи сохранены.

Значения `selected`/кодированные разделители в синтетических fixture —
проверка транспортного переноса, а не утверждение, что сервер примет их как
валидный UUID. Сам серверный приём в этой проверке подставлен route harness.

## Прочитанный завершённый тестовый журнал

`/private/tmp/graf-t112-view-selectors-final-20261116.log`, SHA-256
`919497704ab14ba36e2813bff9d7a756da90bb0e5c1c174a7012ea86110e5136`:
**16 passed,1 warning,28.16s**, без skip/failure. Предупреждение прежнее
`PytestAssertRewriteWarning` для `tests.fixtures.postgres_test_database`.
Неизменный wrapper запускает Chromium/WebKit как два параметра, проверяет
нулевой exit дочернего browser runner и начало stdout `PASS:`. Поэтому оба
движка завершили проверку. Сам pytest-журнал не печатает точное полное число
сценариев каждого движка; здесь утверждаются только10 новых прочитанных
случаев и завершение двух движков. Exit внешней executor session reviewer
самостоятельно не опрашивал; завершённый terminal summary прочитан из файла.

Reviewer не запускал тесты повторно и не выдаёт чтение журнала исполнителя
за собственный запуск. Swift/native/приложение и живой browser не запускались.
Чтение не доказывает durable admission, рабочие данные или итоговый серверный
выбор: это намеренно клиентский тест со synthetic accepted reply.

## Сохранённые требования и ограничения

Все13 документов requirements/analyze/checklists прежнего принятого среза
побайтно совпали с `503805cb6188f942adb159ea2bab8560969b7b0e`. Договор
совпадает с принятым observer/native уточнением. Собственный server-preflight
сохранён с тем же содержимым, которое было прочитано в этом диалоге; его
последний раздел явно разрешал эту клиентскую правку и точно описывал last/
empty-last/encoding/allowlist и desktop GET границу. Новых продуктовых
вопросов или изменения reviewer-owned отметок не требуется.

Повторный пересчёт: requirements16/0, security27/0, privacy52/0, infra29/0,
итого **124 отмеченных/0 открытых**. Полное собственное чтение этих124 вопросов
в предыдущем preflight того же диалога используется при совпавших байтах;
исторические записи не выдаются за новую приёмку кода или рабочих требований.

На момент чтения tracked diff содержит только два проверяемых файла.
Серверный admission, новые flags/started_at, proof format и выпускные
настройки не менялись. Recovery отказ, общий T113, POST/render issuance,
операторские и exact-SHA release gates сохраняются отдельно. Рабочая почта
ГРАФ — Postal; проверка другого почтового продукта к этому подшагу не относится.

## Точные SHA-256

| Путь | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` | `7a5215a4794ff01c0662da0953a3f4e79248101008b8e4d558f88ecfb8f9c609` |
| `apps/server/tests/browser/result-visibility.test.cjs` | `bd9f812fa15bdb33f0ec4f46f8654dde113e85a260e451831a5c960aa05c27ce` |
| `apps/server/tests/contract/test_result_visibility_observer.py` | `bcbb2e0e56786872960cd77aa11b15bd8c972566cb180984bc1763bac66ab856` |
| `specs/273-paid-traffic-analytics/contracts/result-visibility.md` | `ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8` |
| `specs/273-paid-traffic-analytics/validation/t112-server-preflight-20261116.md` | `326782d610867430e26a7e97c71803bb1e44e2c57472790c16a8f158f5eabf59` |

Проверяющий изменил только этот отчёт. Код, spec/plan/tasks/checklists,
Git/GitHub, runtime и публикации не менялись им. `git diff --check` для
отчёта прошёл; результаты точного будущего commit/CI этим не заявляются.
