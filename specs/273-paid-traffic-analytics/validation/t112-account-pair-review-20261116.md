# T112 — проверка общей транзакции и пары account-вех

Дата: 16.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: `/private/tmp/graf-f273-result-visibility-20261116`.
Основа: `46c989b959856c836ab0c2fc5ef0aeb255992a07`.
Полоса: изолированный подшаг существующей `high-risk-product` F273/T112.
Использован навык `code-reviewer`; собственные тесты и сборки не запускались.

## Решение и граница

**PASS изолированного подшага общей границы транзакции и атомарной пары;
P1=0, P2=0 в этой области.** Реализация соответствует ранее принятому
`t112-server-admission-design-20261116.md` и условиям серверного preflight:
один существующий ProductAnalyticsIngestService, прежний SQL-примитив,
один владелец commit и настоящий закрытый источник периода T113.

Это не PASS всего серверного T112. HTTP-вход, выдача/обновление proof,
полный свежий verifier, session/membership/device/Meeting/source fences,
совокупный бюджет тела запроса/подключения/SQL/очистки и runtime T113 пока
не принимаются. В частности, подставленный callback теста не становится
доказательством свежей проверки доступа. Новый код не подключён к route,
render или рабочему сбору, а действующий `_result_period_context` всегда
возвращает `None`.

## Что проверено в коде

- `ingest_authenticated()` использует общий `_account_transaction()` и
  `_admit_event()`. Его прежние проверки principal/identity/source сохранены;
  оба result/value имени по-прежнему дают `trigger_unverified`. Обычный JSON
  не может передать callback, trusted-флаг или дату периода.
- `_account_transaction()` получает сессию из выбранного внутреннего
  контекста. Для result-пути допустим только непустой aware `started_at`,
  не находящийся в будущем, и обязательный свежий `recheck`. Нет settings,
  текущей даты или фиктивного периода, открывающих настоящий runtime context.
  Сам общий helper не создаёт вторую таблицу, ledger или доставщик.
- `admit_result_view()` допускает только существующий session principal,
  его workspace и две фиксированные поверхности. До callback применяется
  shared `FOR SHARE` к активному UserIdentity. Полученный binding повторно
  связывается с principal по owner, workspace, auth session и session device.
  Это дополнительная привязка; она не заменяет будущий fresh verifier.
- Callback исполняется внутри общего контекста на той же DB-сессии и с его
  доверенным началом периода. Текущий настоящий `yield None` не позволяет
  вызвать callback даже при искусственно открытом legal gate теста.
- Две вехи строятся только прежними построителями и проходят прежний каталог,
  безопасную identity и общий `admit_account_milestone()`. Первая result-веха
  и первая value-веха записываются последовательно на одной сессии; commit
  выполняется один раз после обеих операций и свежей повторной проверки.
- `_admit_event()` передаёт прежнему SQL-примитиву callback `before_insert`.
  Общий gate и внутренний recheck вызываются после ожидания identity lock,
  непосредственно перед каждой вставкой, и ещё раз перед commit. Перемена
  допуска/ошибка второй операции выходит из сессионного контекста без commit,
  откатывая весь новый набор. Ранее принятые решения не переписываются.
- Набор получателей вычисляется прежним provider delivery gate. Ни callback,
  ни admission не вызывают transport. Legal gate не изменён и по-прежнему
  безусловно содержит `activation_recovery_unverified`.
- Неизвестный commit возвращает `False`, не повторяя SQL автоматически.
  Следующая новая попытка показа разрешает прежние account-ключи обычным
  идемпотентным SQL-примитивом. В событие не попадают proof, binding, текст
  встречи или частные source/result ID.
- `first_recording_completed` выводится из binding источника, а не из
  `cabinet_web`/`cabinet_desktop`. Доказанный manual upload сохраняет `false`,
  неизвестный capture не добавляет поле. Атрибуция остаётся `unknown`.

`Exception` закрывает ошибки аналитики без раскрытия exception text.
Внешний `asyncio.CancelledError` в Python 3.13 не поглощается этой веткой:
отмена вызывающей задачи распространяется после выхода из контекстов.

## Проверенные тесты и доказательства

Полностью прочитан новый `test_result_view_admission.py`, включая фикстуры
и подстановки, а также действующий ingress-профиль и SQL-примитив.
Положительные сценарии подставляют внутренний `_result_period_context`.
Прежняя фикстура `isolated_admission` отдельно открывает legal/provider gates
только в тестовом процессе и запрещает транспорт. Это изолированная проверка,
не runtime receipt.

Callback положительного теста действительно вызывает
`load_result_view_bindings()` и `verify_result_view_proof()` с HMAC.
Однако `review` берётся из ранее созданной тестовой проекции: callback
не реализует повторное кабинетное чтение под полным набором session/Meeting/
source fences. Тест не выдаётся за полный свежий verifier.

Проверенные сценарии нового файла:

- настоящий закрытый context не вызывает callback и не оставляет строки;
- browser/desktop, неизвестный capture, повтор сохраняет исходный payload;
- уже существующая result-веха другого показа сохраняется при добавлении value;
- подмена owner/workspace/session/device binding не оставляет решения;
- занятая identity блокировка и закрытый аккаунт не запускают verifier;
- отсутствующий/naive/future started_at либо отсутствие recheck не дают допуска;
- отзыв периода после записи пары откатывает её перед commit;
- ошибка второй вставки, gate перед второй вставкой и доказанная ошибка commit
  не оставляют новой частичной пары;
- потеря подтверждения уже исполненного commit не вызывает повтор; следующая
  новая попытка сохраняет прежние ключи и payload;
- две независимые DB-сессии получают одну пару;
- отсутствие факта/медленный callback не оставляют новых строк или работающего
  callback; внешняя отмена прекращает callback и распространяется вызывающему.

Прочитан завершившийся журнал
`/private/tmp/graf-t112-account-pair-final-20261116.log`:
**106 passed, 1 warning in 87.80s**; wrapper зафиксировал
`postgres_test_phase=focused status=pass duration_seconds=91`,
`postgres_test_cleanup=isolated_container_removed`,
`postgres_test_result=pass mode=focused partitioned=false shard=none`.
Предупреждение — прежний `PytestAssertRewriteWarning` импортированной
PostgreSQL fixture. Самостоятельный запуск/повтор тестов не выполнялся;
выход PTY-сессии основного агента этим чтением не проверяется.

SHA-256 журнала:
`0a0cc016b911272ee9fdd7061efd5de1b1a4487141cec7370aa4441d456332fd`.

## Что ещё не доказано

Внешний timeout 2 секунды охватывает текущий внутренний вызов; внутренний
timeout 1,5 секунды оставляет резерв на выход из DB-контекста. Для result-пути
заданы `lock_timeout=250ms` и `statement_timeout=500ms`. Тест показывает
ограниченный callback и реальный отказ занятой identity блокировки, но пока
не доказывает весь будущий HTTP-путь, насыщенный DB pool, медленное подключение,
медленный commit/rollback/close и отсутствие переживающей полный бюджет
DB-сессии во всех этих случаях. После подключения полного server path эти
сценарии остаются частью принятого требования; текущий PASS их не закрывает.

Будущий положительный `_result_period_context` должен удерживать настоящий
T113 filesystem/DB fences до commit и cleanup. Будущий verifier должен внутри
этой же границы заново проверять действующие session/device/membership,
владельца, доступ, выбранную GET-проекцию, HMAC и цепочку источника под общим
Meeting fence, без внутреннего commit. Настоящих реализаций этих частей этот
срез не содержит и не имитирует настройкой.

Не приняты: выдача и renewal proof; разбор тела/query/CSRF/ответы HTTP;
гонки всех writers с fresh verifier; production T113/recovery/restore;
local_only/T0; полный T112/T113, GitHub/merge/релиз/production, трафик и продажи.
Списки проверки, требования, план и задачи не изменены и выполненными
по этому отчёту не отмечаются.

## Точный срез

| Источник | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/product_analytics/ingest.py` | `78b6a0e90c4effe516385768fdcd73d9b6ae47a233cf33bb834a742b06c5e150` |
| `apps/server/tests/contract/test_result_view_admission.py` | `2f5cb12ac816f849b9ce1b3a63e4d653636106c39b8db8efe1e61438de63dd6e` |
| `specs/273-paid-traffic-analytics/contracts/result-visibility.md` | `ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8` |
| `specs/273-paid-traffic-analytics/validation/t112-server-admission-design-20261116.md` | `d32db25b482bf3fe4007aa37cc2539db964754c1e953fe3a10743940ae9122c9` |
| `apps/server/src/twobrain_rec_server/product_analytics/legal_basis_gate.py` | `adb849aca8b9c71a763e567fa507c6be797a84cefcb4460e24b55b3814dd85d1` |
| `apps/server/src/twobrain_rec_server/product_analytics/milestones.py` | `f6fa054826632f5f6f40c16fd8449f05ea82c35f64750f3e5fea26480ee31f02` |

Повторно сверены неизменные договор/проект и относящиеся прежние условия
server preflight. Использовано ранее разрешённое целевое чтение F273;
новая полная приёмка всей истории PRD/статуса не заявляется. Проверяющий
изменил только настоящий отчёт; чужой код и доказательства сохранены.
