# F140/T048 — требования итогового отказа, 01.11.2026

**Действующий результат: FINAL SCOPED IMPLEMENTATION PASS**, P1 0 / P2 0.
Окончательное дополнение ниже заменяет промежуточный PENDING; история сохранена.

**SCOPED REQUIREMENTS PASS — 6 отмечены / 0 открыты.** Блокирующих пробелов
в требованиях этого среза нет: CRITICAL 0 / HIGH 0. Это допуск к реализации
после analyze/связи issue, не приёмка кода, тестов или закрытия #4903.
Полоса: active Spec Kit, серверный финансовый код; test-only допуск T074
здесь неприменим. Ветка `codex/140-final-renewal-failure`, HEAD
`a20ce7fc008de6df21967361317ed668ce29238b`; feature.json подтверждает F140/T048.

Полностью прочитан новый diff spec/plan/tasks/quickstart и новый checklist;
непосредственно проверены Scope Summary, FR070/SC011, F278 FR009/012/014/041,
contracts/notifications-support и security-privacy-compliance. AGENTS,
конституция, карта, document-reading, spec-kit-flow и product-gates прочитаны;
применимые PR/SHA/base разделы release-and-validation, tracker-policy и
текущего статуса F140/F199/F272 проверены. Весь PRD и весь текущий статус
повторно здесь не читались; полной повторной проверки продукта не заявляется.

| Пункт | Конкретное основание |
| --- | --- |
| CHK001 | Новый spec §T048 задаёт сохранённый отказ→cutoff и поздний отказ после Free/UNKNOWN, включая поздний завершающий отказ. Plan/quickstart требуют обе цепочки. До paid_through оплаченный доступ и прежняя attempt notice сохранены. |
| CHK002 | Spec требует personal workspace, текущего active Owner, operation/invoice/workspace и обоих payer/paid_through снимков, canceled/canceled и provider_id. Просроченная неотправленная scheduled и saved_method_missing исключены из подтверждённого отказа. |
| CHK003 | Spec/plan сохраняют финансовый guard версии согласия, деньги и grants. Отзыв не скрывает исход отправленной операции того же плательщика/периода и не включается письмом. Новый владелец/период исключён; соответствует F278 FR012/041. |
| CHK004 | Заданы renewal:<invoice UUID>:failed, существующая транзакция, rollback, повтор/новый сеанс/конкуренция. Один поздний исход не создаёт attempt и final одновременно; прежняя история попыток/UNKNOWN сохраняется. |
| CHK005 | Исторический переход Free, exact cutoff МСК, отсутствие следующих попыток за истёкший период, safe invoice/access_until/action_path и актуальный /billing/subscription заданы. Нет обещания текущего Free при задержке и pay-again при unresolved платеже. |
| CHK006 | Plan/quickstart требуют настоящий planner/charge в одноразовом PostgreSQL: три отказа→cutoff, UNKNOWN→Free→отказ, поздний третий отказ, отрицательные связи, consent, rollback/повтор/новый сеанс/конкуренция. Настоящие деньги/почта и полная T048/T068/#7524 исключены. |

Чтением traced project_renewal_cutoffs и record_renewal_decline. Sender
вызывает общий decline после проверенного canceled, а также при отсутствии
метода без отправки. Webhook и poll сходятся в apply_confirmed_purchase
после GET/validate_purchase_payment и затем в record_renewal_decline.
Текущий cutoff не создаёт final notice; поздний decline создаёт attempt с
прошедшей датой. Это предмет запланированного исправления, не дефекты требований.

Финансовый guard не ослабляется: отдельный notice helper может принять
исход после его раннего return только для истёкшего уже-Free того же
плательщика/периода. После нормальной обработки final заменяет attempt лишь
после Free. **Provider_id обязателен только для canceled/canceled final**:
UNKNOWN должен сохранить допустимость отсутствующего reference после потери
ответа. Основной агент подтвердил отдельную регрессию known/missing reference.
Оба снимка и Owner проверяются общим helper; слабая unit fixture приводится
к настоящему planner snapshot без ослабления guard.

Проверены events.py/notifications.py: существующая транзакционная очередь,
обязательный PAYMENT_FAILED; allowlist access_until и исторический текст
этого вида ещё предстоит изменить. Новая таблица/служба/платёж не нужны.
Отозванное согласие, деньги, paid_through и grants письмом не меняются.

Пересчитаны восемь исторических списков: **162 отмечены / 58 открыты**;
они не изменены. X4–X7, остальные финансовые и внешние приёмки не закрыты.
Предыдущий T075/T074 PASS не заменяет полномочия, изоляцию, сохранность и
неизвестный исход для этого продуктового кода. T048/#4903, T068/#4922,
#7524, оставшиеся события, фактическая доставка и запуск F140 остаются открыты.

Новый checklist после записи целиком перечитан: **6 отмечены / 0 открыты**.
`git diff --check` PASS. Проверяющий изменил только checklist и этот отчёт;
тесты/БД/провайдер/почта/Dev/runtime/Git/GitHub не запускал и не менял.
RED/GREEN, сохраняемые PostgreSQL доказательства, review/converge и три
обязательных PR gate нового точного SHA/основы ещё предстоят.

## Контрольные суммы прочитанных исходников

- `AGENTS.md`: `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958`.
- `.specify/memory/constitution.md`: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`.
- `docs/agent-guidance/README.md`: `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb`.
- `docs/agent-guidance/document-reading.md`: `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411`.
- `docs/agent-guidance/spec-kit-flow.md`: `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e`.
- `docs/agent-guidance/product-gates.md`: `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`.
- `docs/agent-guidance/release-and-validation.md`: `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f`.
- `docs/agent-guidance/tracker-policy.md`: `9793de5e158283c2d37bdd2b47f0daf4d312a44fd6ffa37cc22ac47f7a0c3472`.
- `specs/140-user-account-billing/spec.md`: `5de7ab89d2aa76b02086a77cd394418b80ae2ff07061b6f3d6af62381d146c76`.
- `specs/140-user-account-billing/plan.md`: `9c66182dabde2bdd21b66bc821ce2ba6c8bda3d38251c290231468044d587e92`.
- `specs/140-user-account-billing/tasks.md`: `a3f36e98acdf3c3cb0fd26fcef1343d2b297ee9c62402a9074ca59d0c1f5d701`.
- `specs/140-user-account-billing/quickstart.md`: `c498c51c6a1024428d2e87f6845ca48a612f2101e82b02f624d63b264afa8e6d`.
- `specs/140-user-account-billing/contracts/notifications-support.md`: `3b5d29fc37d63087a70d05151da42f7bbe873276c98234a77e9826bba0fdac97`.
- `specs/140-user-account-billing/contracts/security-privacy-compliance.md`: `38934189b91e33a070b49e61673020d41530eec3d06a4fad5bd00f3317071cfc`.
- `specs/278-production-billing/spec.md`: `db906afb6bb2ae5f3034e64b77db2eb4ff1ea5c144f5d69e2a5aee0cf6cb7d83`.
- `apps/server/src/twobrain_rec_server/billing/renewal_charge.py`: `93363014b3fb62d073ef94acd59b11e7a43e12a91bfb76bf31bc5567fbacf0ef`.
- `apps/server/src/twobrain_rec_server/billing/notifications.py`: `6a8a4d1e3b3701a16dc7b25c4008db68a6f0b689eeff057c1c1809e84a7d560f`.
- `apps/server/src/twobrain_rec_server/billing/webhook_reconciliation.py`: `ac4e031c610cb9a76c3f5f1866b3879cde7a4563bfab145c263a6774aaa83e66`.
- `apps/server/src/twobrain_rec_server/billing/events.py`: `c4d8b6cdc72c31aa19d0d3a58ce72e6dae28551f8b2784974facc638c75512cf`.


## Промежуточное ревью реализации

**IMPLEMENTATION PENDING**: полный diff кода и тестов прочитан, продуктовых
P1/P2 пока не найдено; неуспешный профиль не принят. RED XML:7 FAIL только
по отсутствию итогового notice; первый GREEN:19 PASS. Полный профиль 473:
472 PASS/1 FAIL, ERROR/SKIP0. Ошибка нового late-rollback сценария —
MissingGreenlet при чтении expired onupdate-поля subscription через общий
_row_snapshot до rollback. Это дефект наблюдения теста, не основание менять
финансовый код. Также initial grant уже создаёт payment_succeeded; после
rollback нужно сравнить весь прежний набор notice, не ожидать только UNKNOWN.
Нужны минимальное исправление, предметный повтор и полный успешный профиль
на окончательных файлах. Требования checklist перечитаны и остаются 6/0;
реализация/сходимость/PR пока не приняты.


## Окончательная независимая проверка реализации

**FINAL SCOPED IMPLEMENTATION PASS — P1 0 / P2 0; ограниченные analyze
и converge PASS (CRITICAL 0 / HIGH 0).** Принят только итоговый отказ T048.
Непосредственно перечитан полный окончательный diff пяти Python-файлов,
новые требования/план/quickstart/tasks, changelog и validation. Все 10 файлов
из final-code-hashes.json самостоятельно пересчитаны и совпали.

Сохраняемый отказ→cutoff и поздний отказ через общий record_renewal_decline
вызывают один общий helper; sender/webhook/poll имеют прежние проверенные
входы. Обе snapshot-связи, workspace/invoice/operation, current active personal
Owner и state/period защищены. Финансовый version-guard, settlement и
_project_free не ослаблены. Ранний return допускает лишь notice уже-Free;
normal path после срока не создаёт attempt одновременно с final. UNKNOWN
сохраняет missing-reference; canceled/canceled требует provider_id.
Исторический текст и безопасный access_until направляют за текущим статусом
в кабинет. Новых денег, grants, схем, служб или зависимостей нет.

Проверены сами XML/журналы: rollback-fixed1 PASS и полный profile-fixed
**473 PASS/0 FAIL/0 ERROR/0 SKIP** (XML 176.816 s; журнал 176.84s). Девять файлов:
planner PostgreSQL60; unit charge108; unit notifications10; notification flow26;
renewal workflow9; resolution contract4; lifecycle2; review regressions172;
return82. Предметный rollback и первый GREEN19 входят в итог 473 и не
суммируются. Оба окончательных журнала подтверждают штатное удаление
одноразового контейнера. Два предупреждения — прежние pytest rewrite и
устаревание fastapi/httpx; ошибок/пропусков ими не скрыто.

Отвергнутый профиль 472/1 сохранён. Исправление добавило await db.refresh
перед чтением server-managed expired subscription fields и точное сравнение
всего отсортированного прежнего набора notices после rollback. До rollback
итоговый notice действительно виден; после отката сохранены исходная оплата,
UNKNOWN и все прежние строки, final отсутствует. Продуктовый код для этого
не менялся; проверки денег/срока/grants не удалены.

Шесть групп требований имеют реализацию и предметное покрытие 6/6. Есть
реальные три синтетических POST через planner/charge до cutoff, восемь
поздних комбинаций, known/missing UNKNOWN, отрицательные связи, новые
сеансы, повтор и оба вида cutoff rollback/конкуренции. Отдельный конкурентный
прогон late decline не заявляется: этот путь использует тот же workspace lock,
терминальный guard и уникальный outbox, а его повтор/rollback проверены.
Неотслеживаемого обязательного остатка в принятом срезе не найдено.
Все 87 исходных строк tasks побайтно совпали с HEAD; T048/T068 остаются [ ].
Остальные события, полная T048/#4903 и T068/#4922, #7524 и 58 общих открытых
пунктов, реальная доставка и запуск F140 не принимаются и не закрываются.
Новый коммит требует свежих governance-fast/macos-pr/pr-metadata точного
SHA/основы через общий валидатор. PR/merge/release/Dev/production не приняты.

Checklist полностью перечитан после записи: **6 отмечены / 0 открыты**.
Проверяющий менял только checklist/этот отчёт; тесты/БД/HTTP/приложение/GitHub
сам не исполнял и не менял. `git diff --check` PASS.

Окончательные контрольные суммы (прежние суммы выше относятся к истории):
- `apps/server/src/twobrain_rec_server/billing/renewal_charge.py`: `ef9f2af007465c1556b8a3f0a86b99f6309ff630ec8e24f738d171dcd9f479d1`.
- `apps/server/src/twobrain_rec_server/billing/notifications.py`: `a993612940adf84a4623342c36b2464306440c6797a9dc947f0917935d7d7c40`.
- `apps/server/tests/integration/test_billing_renewal_planner_postgres.py`: `526c5b7cfbee516c348bf0e7d3fd73e109abb413acab45337c50acab992bce4d`.
- `apps/server/tests/unit/test_renewal_charge.py`: `a243312f2d9ff62d0ac6348a3c73d2ef353fb6eba50d4009be1cbdcc6ae82e33`.
- `apps/server/tests/unit/test_billing_notifications.py`: `b3c60395614dfa0036e56b7166d07fb9df143e6db9caa692ebfdacae9b588230`.
- `specs/140-user-account-billing/validation-renewal-final-failure-20261101.md`: `1d27140472817d8c8f8b1fd9b43eff32414c8d7541b86281acc82bfef4e10f5e`.
- `/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/final-code-hashes.json`: `4fe2fe4edadf8c8fa98b7505bb81edbb6dd2ab2d16dc928c8776d40120113a2c`.
- `/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/profile-fixed.log`: `ec15fcbccd63a9a53517ca996ef9809024ae52a92478987a071b208328f215ec`.
- `/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/profile-fixed.xml`: `2878b090cb96a05cedc16eb3739fbb29c93886ef7f43d660703ca572a2b429ef`.
- `/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/rollback-fixed.log`: `c79964576ec0e19db4598665a554c57e95a5c3ec4708c492971aec9945790dc3`.
- `/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/rollback-fixed.xml`: `c33c1e2f120e6741706000886d14836d073b1571c19286be0a21ac7a6c356bc1`.
