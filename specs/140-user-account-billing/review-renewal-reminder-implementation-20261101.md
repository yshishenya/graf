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

## Окончательная независимая проверка совместного изменения — 01.11.2026

**SCOPED IMPLEMENTATION PASS. Новых P1/P2 0; CRITICAL 0 / HIGH 0.
Checklist полностью перечитан: 6 отмечены / 0 открыты.** В пределах
напоминания все шесть групп требований сходятся с кодом и доказательствами;
неотслеживаемого обязательного остатка среза не обнаружено. Полная F140
этим решением не принимается. Исторические результаты выше сохранены.

Полоса: active Spec Kit, серверные финансовые события. Непосредственно
проверены текущий feature.json, reminder-приложения spec/plan/tasks/quickstart,
шесть требований checklist, весь reminder diff относительно исправленного
родителя, разрешённые конфликты и окружающие planner/outbox/events.
Существующий отчёт требований использован как контекст, а не замена чтению.

Первоначальная совместная основа —
`7d7e21377e6a1ac49f905011ffced668e1fe1b68`, reminder source —
`b89ac05084057ce0d3beb49f5999ea9a31b15c5c`. До изменений reviewer-файлов
самостоятельно пересчитаны 14 SHA256 и сравнены с
`reminder-on-fixed-parent-hashes.json`: **14/14 совпали**. С прежней
`reminder-pre-transfer-hashes.json` совпадают 11 файлов; изменены ровно
renewal_charge.py, PostgreSQL planner test и F140 fragment. Их diff
непосредственно прочитан: это ожидаемое исправление позднего ответа родителя
и сохранение reminder assertion в общей проверке, без новой логики переноса.

### Совместное поведение и границы

Текущие personal active Owner и оплаченный период повторно проверяются после
workspace lock/refresh; scalar Workspace ID не доверяет старому ORM-объекту.
Сохранены прежние consent, accepted composed price, method, receipt contact,
pending payment и последовательные окна. Reminder создаётся только вместе с
новой допустимой первой операцией в [−72,−48) часах; повтор существующей
операции и пропущенные окна не создают догоняющее сообщение.

Stable event включает workspace/payer/paid_through, не operation/attempt или
версию согласия. Существующая очередь только flush в транзакции вызывающего;
commit/new session, повтор, конкуренция, rollback, local retry и новое
согласие проверены на PostgreSQL. Нет новой таблицы, службы или зависимости.
Напоминание не вводит новое платёжное разрешение и не ждёт доставки перед
dispatch. Допустимая сумма передаётся целыми minor units, копия форматируется
без float; month/year, даты МСК и фиксированный путь кабинета сохраняются.
Из маски извлекается только ASCII last4, остальной masked_label в сообщение
не попадает. Исторический текст остаётся правдивым после последующего
успеха/отказа/отзыва; текущий статус предложено смотреть в кабинете.

Исправление родителя сохранено: canceled классифицируется по observation time
после POST и повторного lock/refresh, явный now остаётся явным. В четырёх
вариантах explicit/early/late/late-cutoff-worker события entered/release
сбрасываются на каждой попытке; третий POST действительно задерживается,
отдельная session видит processing, а cutoff-worker сохраняет Free до ответа.
Поздний ответ создаёт final failure без старого обещания доступа; повтор не
отправляет POST и не удваивает события. Все эти проверки теперь дополнительно
подтверждают одно сохранённое upcoming-событие. Родительский P2 не возвращён.

### Общий набор и сохранность имён

Проверяющий самостоятельно прочитал завершённые reminder-combined.log/XML:
**711 различных PASS, 18 файлов, 0 FAIL / 0 ERROR / 0 SKIP**, 219.27 секунды.
Collection digest:
`40c71a4f9f78d9775417543a309dfce73c007f9571f2511a944516300b9d04a6`.
Журнал заканчивается focused status=pass и isolated_container_removed.
Два предупреждения: повторный import pytest fixture и существующая
Starlette/httpx deprecation; они не выдаются за новые проверки.

| Файл тестов | PASS |
| --- | ---: |
| contract/test_renewal_resolution | 4 |
| e2e/test_billing_test_shop | 3 |
| integration/test_billing_notification_flow | 26 |
| integration/test_billing_purchase_journey | 61 |
| integration/test_billing_purchase_quotes | 3 |
| integration/test_billing_purchase_storage | 4 |
| integration/test_billing_renewal_planner_postgres | 86 |
| integration/test_billing_return | 82 |
| integration/test_billing_review_regressions | 172 |
| integration/test_billing_webhooks | 18 |
| integration/test_renewal_lifecycle | 2 |
| integration/test_subscription_controls | 2 |
| unit/test_billing_notifications | 17 |
| unit/test_billing_purchase_observation | 30 |
| unit/test_billing_purchases | 80 |
| unit/test_billing_renewal_workflow | 9 |
| unit/test_notification_preferences | 4 |
| unit/test_renewal_charge | 108 |

Имена из XML сопоставлены с race-profile-v2 (476), reminder-focused-v2 (208),
reminder-adjacent (231), reminder-lifecycle (15). Их пересекающиеся результаты
не складываются. Все актуальные имена сохранены; единственное отсутствующее
старое непараметризованное three_confirmed_declines заменено четырьмя
перечисленными вариантами. В общем наборе нет дублированных имён или
необъяснимых новых/утраченных случаев. Это отдельная проверка состава, а не
вывод только из итогового счётчика.

### Окончательный перенос и контрольные суммы

Два reminder-коммита окончательно перенесены на squash master
`9de7feeaaaacaf7cfa1ad6618501eb4fd4edd4ed`. Самостоятельно проверены HEAD
`0adfecf1fe1e290ccf051fab4d726c055c1ffc37`, merge-base и пустой diff между
принятым b89ac050 и новым HEAD. **Всё Git-дерево побайтно совпадает**, tree
до/после `6335b0115834ad6115a07f7b43c5d1bf1cee7009`. Manifest переноса прочитан
отдельно; проверка выполнена также непосредственно Git, не только по его
заявлению. 13 рабочих файлов оставались неизменными на момент записи;
четырнадцатый validation основной агент ожидаемо дополнил текущими фактами.
После этой сверки reviewer изменяет только checklist и этот отчёт.

Пять принятых Python-файлов на окончательной основе:

| Файл | SHA256 |
| --- | --- |
| apps/server/src/twobrain_rec_server/billing/notifications.py | `d0f664e80b18b0d140ecb6ced6f27415c31e8937903fd03af783df30e5905029` |
| apps/server/src/twobrain_rec_server/billing/renewal_charge.py | `80019b6afae68a7a7f848931a20fcd1091946bec688d7fb3fbf374a07f4ac12c` |
| apps/server/tests/integration/test_billing_renewal_planner_postgres.py | `c329efdcfe9ed37b8d1b96e5a39541ad0e6e44393d7f9c70d5be34dfb6d0b04a` |
| apps/server/tests/unit/test_billing_notifications.py | `ea7c0f0ba303c8e28389cce1512a90682929e9a4258942f151cf8b1596b1d511` |
| apps/server/tests/unit/test_renewal_charge.py | `8f1b63ba0f75ba6edc29df077b6f0415e23323f57f8cd470e9caa473cf54d67b` |

`git diff --binary <окончательная основа> HEAD -- <эти пять путей>`:
25556 байт, SHA256
`7c211879415d315cc26114c54546f28029a54e38469d9c80b65a1747c367c2db`.
Принятый F140 fragment:
`b916139cd686b3b8b52309f4702090d4e9455409c74679bba08ac61fcd0af0ba`.
Суммы spec/plan/tasks/quickstart и отчёта требований выше по-прежнему совпали.

Внешние доказательства в
`/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/`:

- reminder-combined.log: `e2fd1ddd775f86c40a497aaafd2ba362ea501dc32c37414ab500f84f0d991d28`.
- reminder-combined.xml: `382126f0e43168dfa4af593c4c7d9112acf9c60ddacc6b6dd556a429a39fbae8`.
- reminder-on-fixed-parent-hashes.json: `840d03a9127428d978ab25aa8be60d923b2866ad0ea4ba762947346f94388e66`.
- reminder-post-squash-transfer.json: `23cb448c7b9ceb0459f7044621cb9add0022563131eed0c0793e67fee4670aa6`.

Повторять этот профиль после тождественного переноса не требуется. Итоговый
коммит документов всё равно требует новых governance-fast/macos-pr/pr-metadata
точного SHA и действительной основы через общий validate-pr-checks.py.
Эти GitHub gates, обновление PR, merge и выпуск данным отчётом не подтверждены.
Полная T048/#4903, T068/#4922, #7524, фактическая доставка, 58 общих открытых
пунктов, реальные платежи/почта, GRAF Dev и публичный запуск остаются открыты.

Проверяющий не запускал тесты, БД, HTTP, сборку или приложение и не менял
код/план/tasks/общие checklists/GitHub/Git. Записаны только два назначенных
reviewer-файла. Checklist после записи полностью перечитан:
**6 отмечены / 0 открыты**; `git diff --check` PASS.
