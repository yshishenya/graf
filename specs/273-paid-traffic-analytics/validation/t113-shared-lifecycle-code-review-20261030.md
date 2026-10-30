# F273/T113: независимое ревью общего чтения локальных удалений

Дата: 30.10.2026. Проверяющий `/root/f273_release_boundary`.
Ветка `codex/f273-local-period-20261029`, основа
`8350b688788861d8b35dd304bcf325f7eef305e8`, T113/#7804.
Путь проверки: `high-risk-product`, существующий Spec Kit.

## Решение

**SCOPED CODE REVIEW PASS. Открытых P1: 0, P2: 0.**
Блокирующих дефектов в проверенной связи backup/runtime не найдено.
Это приёмка ограниченного изменения исходного кода и его доказательств.
Полный допуск работающей системы и завершение T113 не подтверждаются.

Полностью прочитаны конечные изменения восьми отслеживаемых файлов,
[отчёт исполнителя](t113-shared-lifecycle-20261030.md),
[проектное заключение](t113-shared-lifecycle-design-review-20261030.md),
precode, затронутые функции с окружающим кодом и профильные журналы.
Неизменные зависимости reader/parser, вызывающие функции и действующие
требования проверены при проектном ревью; их контрольные суммы повторно
сверены по разрешённому пользователем исключению F273.

## Проверенная реализация

- `_local_lifecycle` содержит прежнее фактическое SQL/parser/policy тело.
  Оно принимает только непустые неизменяемые bytes до10МБ и открывает
  собственную read-only repeatable-read транзакцию на переданном соединении.
  Проверяются maintenance context, точные closure/ledger политики и права,
  закреплённые catalog/access, полный closure snapshot, v2 disposition cases,
  покрытие четырёх категорий и реальные остатки. Формула digest сохранена.
- `_backup_lifecycle` сохраняет исходный `private_bytes` и файловые ограничения
  владельца,0700/0600, single-link и10МБ. Повторное чтение и равенство bytes
  выполняются после закрытия транзакции ядра, до возврата прежней пары digest/raw.
- `_runtime_operations` возвращает прежний digest вместе с actual legal bytes
  из уже удержанного `_bound_runtime_file`. Его прежние проверки bytes,
  file/proc/bind identity, guard/access и свежести при выходе сохранены.
  Предел runtime файла остаётся65536байт.
- `_runtime_preflight` сравнивает bytes всех writers отдельно от digests,
  передаёт обязательный `register_raw` и оставляет raw внутри владения в памяти.
  В operations proofs и публичный результат попадают только прежние digests.
  Отдельный тест отвергает разные raw даже при одинаковом подставном digest.
- `_runtime_databases` вызывает ядро на той же уже пониженной физической source
  с `root=snapshot` до yield и после него. Оба вызова находятся вне внешних
  транзакций и создают новые RR snapshots. Повторный digest сравнивается;
  прежние проверки identity/catalog/access, срок и закрытие соединений
  сохранены. В proof добавлен только `lifecycle_sha256`.

Новых подключений для ядра, таблиц, ролей, прав, зависимостей, файловых
обходов или внешнего supplied PASS нет. Accepted category не принимается
как доказательство исполнения даже при пустой таблице. Прежний допустимый
accepted account_closure с реально завершённым purge, правильной хронологией,
полным охватом и отсутствием остатков сохранён. Исторические сроки остаются
`unverified`, действия внешних получателей — `outside_local_scope`.

## Доказательства и точные границы прогонов

Независимо пересчитан весь frozen inventory
`.dev/growth/t113-shared-lifecycle-final-hashes-20261030.json`:
**30/30 совпадают**, SHA-256 самого inventory
`5f280396d87a8fe6784654d7bfe1b3db107846b8d01a6e32121c58ac775def58`.

| Доказательство | Результат и граница |
| --- | --- |
| Общий focused профиль PostgreSQL17 | 358 PASS,37 Linux SKIP,2 предупреждения;395 собранных тестов,179,62с. Проверяет unit operator/replay, native runtime/source lifecycle, coherent copy/restore и непустые four-category/replay consumers. Cleanup подтверждён журналом. |
| Linux actual bound files/settings/runtime | 106 PASS,0 SKIP,0,61с на конечных unit bytes. Не заменяется пропусками Mac. |
| Последняя причинная отмена | На конечных native runtime bytes: cancel_lifecycle/good/lifecycle_closure_changed —3 PASS,2 предупреждения,14,71с. Cleanup подтверждён. |
| Статические проверки исполнителя | Ruff, governance, development-process, fragments успешны;80 локальных Markdown-ссылок без ошибок. |
| Независимая проверка пробелов | `git diff --check` успешна. |

Общий профиль **не приписывается всем конечным bytes native runtime теста**.
Сверена отдельная карта
`.dev/growth/t113-shared-lifecycle-profile-tested-hashes-20261030.json`
(SHA-256 `5b04c808a86511ad0711ea6f1de45486159e573db576c63edb42ce87b604b101`).
Продуктовый код, unit и source/replay тесты совпадают с конечными хешами.
После358 PASS усилен только сценарий отмены native runtime теста:
его прежний хеш `2f6cce67253891ef787a7caa84d5ad641d6d62218456f04bc3be0582d2f09d6c`,
конечный `962411a195e939fe5d9b053cd9df01d9f0711cd6bc51f50828ed44814eaca8c7`.
Последние3 PASS подтверждают конечное усиление и два соседних сценария.

В отмене wrapper лишь устанавливает собственный table lock непосредственно
при входе в оригинальное ядро и затем вызывает оригинал. Наблюдатель ждёт
настоящий `CLOSURE_POLICY_QUERY` по точному source PID, application_name,
wait_event_type=Lock, первым128символам query и locker PID в pg_blocking_pids.
После этого две отмены действительно прерывают запрос внутри read-only RR.
Проверяется отсутствие всех owned preflight соединений; locker rollback/close
и admin close находятся в finally. Обычное ожидание до входа в ядро не принято
за это доказательство.

Linux runner прочитан полностью: используется существующий образ
`sha256:37d27de327e5876b4c890a7e6c3dd98ab8fd89476180d6deb42d262411c1ccbe`,
`--pull=never --network none --read-only --rm`, source/tests/dependencies
монтируются read-only, Docker socket и приложение не передаются. Собственный
одноразовый volume поддерживает ACL; временные pure-Python pytest modules
принадлежат TemporaryDirectory. Runner принимает успех только при нулевом
коде и реально выполненных тестах без skips. Итоговый JSON содержит конечный
unit SHA-256 `6fa2f9c255a1357d5e501f182eb8ed814089c14aa53bfc5db24e64678739736c`.
Это проверка сохранённых доказательств; reviewer runner не запускал.

Неуспешные опыты сохранены и прочитаны; повторяющиеся INFO строки миграций
больших журналов отфильтрованы только при чтении. Unit RED дал2 FAIL/1 PASS
на отсутствии register_raw; native RED дал2 FAIL на отсутствии нового keyword
и ядра. Первая native попытка дала22 PASS/1 FAIL из-за ALLOW_CONNECTIONS из
текущей БД; конечный тест использует admin postgres и восстанавливает исходные
metadata в finally. Linux без stdin не выполнил тесты и не принят;
tmpfs дал103 PASS/3 FAIL из-за отсутствия ACL, затем volume дал полный успех.
Уточнения отмены дали collection error, lock до ядра и неверный SQL prefix;
они не выданы за PASS. Конечный журнал подтверждает причинный сценарий.

## Повторное чтение и контрольные списки

Все117 вопросов перечитаны в рамках этого code review; отметки не менялись.
Они оценивают качество требований, а не выполнение установочных работ.

| Список | Checked | Unchecked | SHA-256 |
| --- | ---: | ---: | --- |
| requirements |16|0|`6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2`|
| privacy-measurement |45|0|`8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f`|
| security |27|0|`57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8`|
| infra |29|0|`998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94`|
| Итого |117|0|Отметки совпадают с проектным ревью.|

Повторно совпали хеши constitution, PRD, current status, product-gates,
spec, operations contract, data-model, restore_replay и legal_basis_lifecycle.
Применимые требования и зависимости перечитаны на проектном этапе; разрешённое
исключение F273 ограничивает повторное чтение неизменного большого baseline.
Полное повторное чтение600КБ истории не заявляется.

## Что остаётся открытым

`full_preflight_not_implemented` и `activation_recovery_unverified` сохранены.
T112/T113/#7804, installed jobs/guard/purge/cron, shell graf-local, полный
preflight, верхние initial/backup/verify/actual-restore/resume, CD/rollback/daily,
рабочие T0/ready/IP/получатели, exact-SHA GitHub CI/Full/release и коммерческие
AC01–AC06 остаются открытыми. Этот reader не подтверждает полный готовый
оператор, удаление у внешних получателей, исторические сроки, трафик или продажи.

Reviewer не запускал tests/SSH/контейнеры/БД/Dev/production и не менял исходники,
spec/plan/tasks/governance/Git/GitHub/публикации. Изменён только этот отчёт.
После записи отчёт перечитан целиком; inventory и checked/unchecked пересчитаны.
