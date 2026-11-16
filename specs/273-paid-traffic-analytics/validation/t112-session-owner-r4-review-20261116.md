# T112 — независимое повторное ревью R4

16.11.2026. Проверяющий `/root/public_counter_readiness_review`.
Рабочая копия `/private/tmp/graf-f273-result-visibility-20261116`.
Основа `45c068813ed7bdadbe5e90ab82b48cab0f28b1c9` плюс проверенный diff.
Полоса существующей F273/T112: `high-risk-product`.

## Решение

**Scoped PASS: P1=0, P2=0. R4 закрыт.**
Это приёмка только сохранения отказа standalone read-only Session owner
после ошибки исходного исполнения/декодирования. Прежние отчёты HOLD и
R1–R3 не переписывались. Полная T112/T113 и включение измерения не приняты.

Полностью прочитаны основной r4-validation, текущий Session source, Session
test и оба diff. Из RED/GREEN прочитаны все строки вне повторяемых Alembic
миграций, включая три отдельных отказа RED, warning, итоговые summaries,
метрики обычного reader и cleanup markers. Журналы не запускались повторно.
Фактические hashes совпали с запросом и основным отчётом.

## Исправление и причина

В `_permit` общий `except BaseException` немедленно устанавливает
`self.failed = self.budget.failed = True` и повторно выбрасывает исходное
исключение. Ошибка `state.invoke_statement()` проходит через эту границу
до того, как reader может её перехватить. Следующий checkpoint отказывает;
новый SQL не допускается; checkpoint после yield не позволяет успешно
завершить owner. Счётчики не возвращаются, повторной попытки чтения нет.
`finally` продолжает очищать `_expected` и `_cursor_pending`.

Одна общая граница охватывает четыре существующих места `_permit`:
управляющую настройку остатка срока, numeric execution, исходное чтение,
два начальных SET. Изменение не вводит новые запросы и не повышает пределы.
Числовой helper оставлен прежним. Положение проекта295ce2c о прекращении
фазы при неизвестном исходе и отсутствии refund/retry перечитано полностью.

`CancelledError`, как и остальные `BaseException`, помечает отказ и затем
сохраняет свой тип благодаря bare raise. Новый обработчик его не подавляет
и не превращает в `ProjectionBudgetExceeded`. Внешний owner по-прежнему
ловит только `Exception`; очистка сохраняется в finally. Существующий
тест отмены входит в GREEN44 и проверяет распространение CancelledError,
отсутствие оставшейся Session/listeners/tasks. Он отменяет ожидание reader
после SQL, а не отдельную зависшую фазу внутри `_permit`; доказательство
для нового обработчика здесь статическое, нового in-flight cancellation
испытания не заявляется.

## Причинная проверка

Три новых случая используют настоящий Python integer digit limit,
действующий в тестовом процессе: он проверен положительным и меньше128KiB.
В PostgreSQL JSON записано целое длины limit+1 цифр. Размер и JSON-shape
проходят числовые фазы; исходный `db.get` получает реальный `ValueError`
декодирования. Reader перехватывает его внутри owner. Варианты раздельно
проверяют последующий checkpoint, чтение и выход без дополнительного вызова.

Важные проверки находятся снаружи sanitizing owner context:
`failures == [True]`, оба failed, rows1/nodes1, учтённые SQL, пустой identity
map, завершённая транзакция и снятые listeners. Непройденный inner
`pytest.raises` является pytest Failed и не маскируется обработчиком обычных
Exception. Реальный RED показывает точные DID NOT RAISE для каждого из трёх
действий, а не сбой fixture. Снаружи также проверен именно `budget.failed`:
одного owner.failed, который устанавливает detach, было бы недостаточно.

| Версия и объём | Прочитанное доказательство |
| --- | --- |
| Исходный source45c068813, новые3 случая | 3FAIL/41deselected,4.87s,runner9s; все3 DID NOT RAISE; cleanup removed |
| Исправленный source, весь Session-файл | 44PASS/0skips,21.05s,runner25s; result pass; cleanup removed |

Основной исполнитель фиксирует terminal19573 EXIT1 для RED и95333 EXIT0
для GREEN. Проверяющий прочитал его полный отчёт и сами журналы, но не
опрашивал terminal handles и не проверял Docker runtime заново. В обоих
журналах один прежний PytestAssertRewriteWarning. Числовые34 теста не
перезапускались: прежний GREEN75 остаётся отдельным доказательством,
нового завершённого общего запуска78 проверок здесь нет.

Полный обычный reader сохранил равенство исходному ответу с600+600
сегментами, JSON, календарём/roster, предыдущей встречей, default pinned
outcomev2 и transcriptv3. Метрики GREEN44: review56SQL/1212rows/1214494bytes/
1263nodes, bindings71SQL/1216rows/1221872bytes/1870nodes. Динамические
учтённые SET объясняют71 вместо67 в предыдущем запуске. Предел128 не вырос.

## Требования и границы

Независимо пересчитаны18 hashes входов: все SAME. Analyze0252da92 неизменен.
Четыре checklist перечитаны для подсчёта: requirements16/0,security27/0,
privacy-measurement52/0,infra29/0 — **124 checked/0 unchecked**. Отметки
не менялись. Собственное чтение оригинальных требований того же диалога
сохраняется; scope не расширен новым сбором, сроком, правом или продуктом.

Полный admission/два INSERT/commit, trusted readiness и свежие identity,
session,legal,source,deletion,writer fences, maximum envelope, HTTP/proof/
renewal, остальные исходы cleanup и вся T113 остаются открытыми.
`_result_period_context` остаётся yield None. Нет общей Python-песочницы
против произвольного прямого DBAPI. Обычный fixture не доказывает maximum
envelope. Рабочие T0/измерение, трафик, регистрации, оплаты, PR/CI и выпуск
настоящим scoped PASS не подтверждаются и не разрешаются.

Записан только этот новый отчёт. Прежние отчёты, code/spec/plan/tasks,
checklists, Git/GitHub, runtime/данные/службы, сайт, Postal и публикации
не менялись; тесты/пробы/сборки, новые агенты и межчатовые сообщения не
запускались. Чужие изменения сохранены. `git diff --check` без замечаний.

## Проверенные контрольные суммы

| Артефакт | SHA-256 |
| --- | --- |
| Session source | `95108da96f1df0c479ad402cc80a563382049f395d276c5976499a8a67874dc8` |
| Session test | `a39d6f250f03c6475dd281e04a794aedab0fca7173ab8410db699fbd75a696bc` |
| Numeric source, без изменения | `f4de665d1329085a320de268445ace87c886ed08febc387cfd4df65e7c0ea718` |
| Numeric test, без изменения | `7b36f0c99cee98af4b867f05bd01ab2117ed589b0dbb8b8cc35531986ce9828a` |
| Основной r4-validation | `1e35fbf6309e258797a592ac42502b85946a2a3349609e28a7cf5c9fbbeba0de` |
| RED3 log | `1f375d1494dae02e384a75d351f94516729428c6b54f19fe9640098fb44f1ceb` |
| GREEN44 log | `659f273e5c2eb22adc9f537b0ad967d829ce26f918feb4e8d3aafc24f6756bf1` |
| Прежний R1–R3 rereview HOLD/R4 | `1429a48947347e85d159e24cbb49de3787633bbc8da5d90564beabd7f592fa95` |
| Проект numeric/Session295ce2c | `295ce2c82c8638ddb9df1fbd5d478f0fefa53ea4b13ef34b6a3b760378a10326` |
