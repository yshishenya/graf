# F140/T048 — независимое ревью реализации reminder, 01.11.2026

**FINAL SCOPED IMPLEMENTATION PASS. Findings: P1 0 / P2 0; иных
предметных замечаний не обнаружено.** Шесть принятых групп требований
покрыты 6/6. Это приёмка узкого producer и шаблона напоминания, не всей
T048/F140, настоящей доставки или GitHub merge/release.

Полоса: active Spec Kit, финансовые события сервера. Ветка
`codex/140-renewal-reminder`, HEAD `887ad8095c97ca80b360f2157e13b8c6541db6bc`.
Проверен весь локальный diff пяти назначенных файлов, реальные planner,
caller worker, outbox и форматирование. Уточнение reminder в собственных
spec/plan/tasks/quickstart и checklist перечитано; их суммы совпали с
независимой приёмкой требований. Применимые FR070–073, notifications-support,
F278 FR014/041 прочитаны непосредственно. Прежние собственные прочитанные
AGENTS, конституция и guidance сверены по суммам; новых изменений в них нет.
Чужое чтение и сообщение о PASS не использовались вместо исходников.

## Привязка требований к окончательному коду

| Требование | Конкретное основание |
| --- | --- |
| CHK001 | renewal_charge.py:336–360 повторно refresh подписки и проверяет personal/state/consent/период, затем scalar текущего personal active Owner после workspace lock. Прежние price/method/receipt/pending проверки и solver окон сохранены. Строка 596 создаёт notice только при новой attempt1; существующая операция/attempt2/3 сюда не попадают. Четыре PostgreSQL случая меняют owner/workspace/membership/period во второй транзакции до lock, включая заполненную identity map. |
| CHK002 | renewal_charge.py:597–608 хеширует workspace/payer/UTC paid_through в UUID5; operation/attempt/authority-version в event_id не входят. Enqueue идёт после добавления родителя/счёта без отдельного commit; existing outbox только flush. PostgreSQL доказывает невидимость до commit, полный rollback, новый сеанс, конкурирующий planner и один event после local retry/нового согласия. |
| CHK003 | Новый код не вызывает провайдера, не меняет деньги, grants, paid-through или authority. Добавлены повторные проверки актуальности прежних границ, а не новый источник финансового разрешения. Worker по-прежнему commit planner и отдельно dispatch. Включение mandatory-kind не требует доставки перед списанием; F278 FR014/041 не меняются. |
| CHK004 | renewal_charge.py:610–617 берёт amount/currency/cycle из того же принятого каталога/подписки, что operation/invoice; validate_plan_version допускает только RUB и payable month/year. notifications.py:255–257 использует int/divmod без float. Строка 603 извлекает только ASCII last4 из точного masked label; иначе общий способ оплаты. Allowlist:392–420 разрешает только ограниченные поля/форматы; action_path фиксирован. Проверены месяц/год, цена с 19 цифрами и ведущими нулями last4, неверная маска, Unicode digits, полный PAN, посторонние поля. |
| CHK005 | notifications.py:264–269 описывает сумму/дату по расписанию на момент события; нет обещания будущего списания/текущего согласия/тарифа. Даты МСК и конец прошлого периода привязаны к сохранённому событию; актуальный статус/управление доступны в кабинете. Поздняя доставка не требует новой службы или финансовой проверки в sender. |
| CHK006 | Сохранён настоящий PostgreSQL planner/outbox под прежним fixture с запретом внешнего HTTP и проверкой maintenance role/RLS. Проверяются неeligible scope/price/consent/method/pending/newer-period, post-lock race, commit/rollback/repeat/concurrency, следующие окна без catchup, три синтетических decline без второго reminder. Настоящие платежи/почта и остальные T048/T068/#7524/launch этим не принимаются. |

При смене ссылки владельца используется scalar ID, который не доверяет
устаревшему ORM Workspace в identity map. Finance dispatch/settlement/grants
не изменены. Обновление unit PlanningDb/PagedDb обслуживает новый scalar
query; тест ограничения страниц не ослаблен, реальная смена Owner отдельно
проверяется PostgreSQL. Новых таблиц, миграций, служб или зависимостей нет.

## Проверка доказательств

Непосредственно прочитаны журнал и XML reminder-focused-v2: **208 PASS,
0 FAIL / 0 ERROR / 0 SKIP**. Это 83 PostgreSQL planner, 108 unit charge,
17 unit notifications. Collection digest:
`bd26b4ee5ad154cc4b5b0c40e01993868ba294c602c4cc09548116a0bcde33c3`.
Единственное предупреждение — pytest rewrite уже импортированного fixture.
Журнал подтверждает штатное удаление одноразового контейнера.

Дополнительно прочитаны reminder-adjacent XML/итог журнала: **231 PASS,
0 FAIL / 0 ERROR / 0 SKIP**: notification flow 26, webhooks 18, purchase
journey 61, quotes 3, storage 4, renewal workflow 9, purchases 80, observation 30.
Контейнер удалён. Это отдельные имена тестов; прежние исторические 473 и
первый профиль не подменяют текущие доказательства.

Проверена история причинности: reminder-test-red имеет один ожидаемый
FAIL отсутствующего notice на настоящем planner; первый reminder-focused
дал 198 PASS / 1 FAIL на PagedDb, не знавшем нового scalar Workspace query.
В окончательном mock query обслуживается, assertions страницы/цены сохранены,
а весь focused-v2 прошёл. Отказ не скрыт и не исправлялся ослаблением
финансовой проверки в продукте.

Дополнительный reminder-lifecycle на момент передачи основным агентом ещё
исполнялся; его PASS этим отчётом не заявлен. Проверяющий сам не запускал
тесты, БД, HTTP, приложение или GitHub. Окончательные обязательные PR checks
нового SHA/основы, merge и release ещё предстоят. Частичные журналы или
внешняя доставка не выдаются за успешную приёмку.

Checklist требований перечитан без изменений: **6 отмечены / 0 открыты**.
58 общих открытых пунктов F140, T048/#4903, T068/#4922 и #7524 этим
результатом не закрываются. В принятом reminder-срезе неотслеживаемого
обязательного остатка не обнаружено; полная сходимость F140 не заявляется.
Проверяющий записал только этот отдельный отчёт. `git diff --check` PASS.

## Точные контрольные суммы рассмотренного изменения

Пять файлов ниже; `git diff --binary -- <эти пять путей>` на указанном HEAD:
**SHA256 diff `5d72be33bb0bd772022e323dab5844de38c5814a190baf0307fa4e1160683601`; 25542 байт.**

| Файл | SHA256 текущего содержимого |
| --- | --- |
| `apps/server/src/twobrain_rec_server/billing/notifications.py` | `d0f664e80b18b0d140ecb6ced6f27415c31e8937903fd03af783df30e5905029` |
| `apps/server/src/twobrain_rec_server/billing/renewal_charge.py` | `5142faae766df0efb1efc13e3efe848a199f16d1709307343a5070a2d7354809` |
| `apps/server/tests/integration/test_billing_renewal_planner_postgres.py` | `afd6640418cb625c8546e44a8cd98fe0c28b3133cf4d0e7aaf68ff6e955c2f1b` |
| `apps/server/tests/unit/test_billing_notifications.py` | `ea7c0f0ba303c8e28389cce1512a90682929e9a4258942f151cf8b1596b1d511` |
| `apps/server/tests/unit/test_renewal_charge.py` | `8f1b63ba0f75ba6edc29df077b6f0415e23323f57f8cd470e9caa473cf54d67b` |

Контрольные суммы доказательств и требований:

- `/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/reminder-focused-v2.log`: `9f3cb06002ed611b2746d0c28b653ec52b953b121465f853ad9a37e7ec13e280`.
- `/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/reminder-focused-v2.xml`: `4903dd057eb8b99388054277ad08d60e29735ba2dfd0cbe3135d897c11dc1383`.
- `/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/reminder-adjacent.log`: `74a89328aa9d9e6b3de869d4a1df3aae1328ddd2b0d94bb20d76755be1b5f595`.
- `/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/reminder-adjacent.xml`: `b67573b171985a6212578d88e64191e5908b0b8fc916269fb04bef732edfb169`.
- `specs/140-user-account-billing/checklists/renewal-reminder.md`: `abfc89a34d05064318d94f1778734325c7b74384279de419e2728b887aed6347`.
- `specs/140-user-account-billing/spec.md`: `44f3d1d2ffdd110a87a85c39e7ebc8cbdf97c4bd18b3e988e2cbf8c1dc5797e0`.
- `specs/140-user-account-billing/plan.md`: `30ca2a01a60ed8e7a7ee7e4221b062e80bd43d11511652470ca291faf964b961`.
- `specs/140-user-account-billing/tasks.md`: `6036a52a1de3fdd667dde4fad6af2c8e5236f94f7f0059510fa0b096b0003518`.
- `specs/140-user-account-billing/quickstart.md`: `a8a40e99036f91b128f9129494e7e1e7b57a334dc73d35c97aea6a38d5ee19fc`.
