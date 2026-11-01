# Независимая проверка требований F140/T077 O14 — 01.11.2026

Исполнитель /root/f140_notification_content_review; собственный диалог
01a1955c-cb77-78e3-8844-ffeabcb2d594. Ветка codex/140-observation-deletion;
HEAD/base 2d279420b9f825c55eb5d03734de2528df5a46ea.
Полоса high-risk-product/repository-audit. Только качество требований до кода.
Решение: PASS качества требований D1–D6/O14. Подтверждены все 10 пунктов
независимого списка; 10 отмечены, 0 не отмечены. Новых CRITICAL/HIGH замечаний
в этой области: 0/0. Это допуск к реализации, не приёмка кода или закрытие #4932.

## Собственное полное чтение изменённых оригиналов

| Путь | SHA-256 | Неусечённое чтение |
| --- | --- | --- |
| specs/140-user-account-billing/spec.md | 8a8d94be081a0ebabff22c6dbca2e410b99fa51340bd414233d12776d5b78cfa | 1–100:789fad;101–200:1aa754;201–300:44eb94;301–400:221baf;401–490:78c2ab;491–600:4d6875;601–760:124ed4;761–915:0deb0c. Полностью, запись сразу после завершения. |
| specs/140-user-account-billing/plan.md | 7834d0b0f9913771e03a41a3590f6fb5975748bae14bed5b8552eda836623646 | 1–155:90004b;156–315:111219;316–475:4a3184;476–628:d60609. Полностью, запись сразу после завершения. |
| specs/140-user-account-billing/tasks.md | 61bcbcd1efa9aa0f09b41d7b1a2390e110fb987427f91393facc224ef2232afb | 1–145:7773e3;146–310:45a691;311–461:ec2f38. Полностью, запись сразу после завершения. |
| specs/140-user-account-billing/quickstart.md | 7f7a6a4176532e87e7469cba8fd7fad50f8ba9f7bd06f427050c66398238962d | 1–190:a031e4;191–380:1c965f;381–570:5a3e20;571–755:1ca458;756–847:b2e9c4. Полностью, запись сразу после завершения. |
| specs/140-user-account-billing/research.md | 598c7a7d14198b88e13d11ffee7dbc579cb38db5592ec92bcdc3fdd9b7c05267 | 1–165:77e85a;166–335:cfb8dc;336–499:2d483c. Полностью, запись сразу после завершения. |
| specs/140-user-account-billing/data-model.md | 1209f5a0eec28df8a02c7d555c0bdf571a9facbf3f334674c2064c2b0dbafe83 | 1–160:e52683;161–315:adf58f;316–452:088eee. Полностью, запись сразу после завершения. |
| specs/140-user-account-billing/contracts/operator-observation.md | cb1b7f5b54a5f2f3fb1297ddba5b189053e798629b196b555f45b8baccd789f2 | 1–180:32850f;181–360:d86ed3;361–524:41af28. Полностью, запись сразу после завершения. |

## Происхождение чтения и нормативная проверка

Собственные 29 неусечённых выводов семи изменённых оригиналов из таблицы выше
сопоставлены побайтно с их диапазонами в текущих файлах: output79666e.
Повторная сверка семи полных SHA:5689a6,7/7 совпали. Ни отдельный пересказ,
ни усечённый вывод не использовались как доказательство полного чтения.

Неизменный контекст восстановлен из собственного журнала диалога
01a1955c-cb77-78e3-8844-ffeabcb2d594 и собственных receipt/refund review reports.
Уточнение карты прежнего чтения: журнал42/call_10637b7ccba74d8c981ba819ecc3fb5b
содержит current-product-status1–2385; журнал75/call_a2212eb8b63549c9bb27b94fe012e440
содержит PRD1–1100; журнал142/call_8d96fe89ade44fa5a623776881199f94,
части0+1 вместе, содержит PRD1101–2474. Сравнение настоящих байтов outputs с
оригиналами:5a3c3d/1c6d9e. Это корректная карта диапазонов вместо неточного
распределения PRD по номерам записей в прежних отчётах.

Для O14 дополнительно собственноручно перечитаны оригиналы:

- AGENTS.md целиком:1b37ce; document-reading.md целиком:85c2d8;
  README/spec-kit-flow/product-gates целиком:8fc0b9;
  development-process/tracker-policy целиком:194873.
- Конституция89–530:044408. PRD1–150/349–374/688–749:35044b;
  750–844/1031–1101:1c6d9e;1102–1147/1488–1542/2035–2072/2278–2326/
  2471–2474:5a3c3d;1578–1777:cb30b9;1446–1452:628936.
- current-product-status179–217/451–470/529–622:47206f;
  release-and-validation171–244/410–443/646–692/758–770:934ea7.
- operations-reconciliation/security-privacy-compliance/registry-operator-import
  целиком:2ba2ef; billing-lifecycle/entitlement-degradation целиком:c5151e;
  F278spec158–203/295–302:58b836.

Усечённые a3fcaa/135313/562c73/426422 не засчитаны за полное чтение; применимые
разделы затем покрыты неусечёнными выводами. Шестнадцать нормативных входов
из таблицы «Контрольные суммы неизменных входов» собственного
review-refund-inventory-requirements-20261101.md повторно совпали:8fc0b9/5689a6.
Это не утверждение о неизменности старого monitoring.py: он закономерно
изменялся предыдущими принятыми областями; его текущая сумма приведена ниже.

## Решение по каждому пункту

| Пункт | Решение и конкретное основание |
| --- | --- |
| CHK001 | PASS. O14/D1: точный root source=fair_use_reviews,meeting_deletion_requests; самостоятельный values.deletion/source=meeting_deletion_requests. Оба database_inventory/current_state. Все видимые строки без report_date/created_at/accepted_at/completed_at/failed_at фильтров; count измеряет запросы, а не уникальные встречи, людей или завершённые удаления. Spec725–737, plan85–91, model3–12 согласованы. |
| CHK002 | PASS. D2 и research10–14 явно ограничивают известные группы requested/deleting/active_purge_complete/retryable_failed. Default requested проверен в модели и migration0007; единственный найденный constructor service225 задаёт deleting, записи371/685/1673 — retryable_failed,433/797 — active_purge_complete. Остальные значения, включая NULL/complete/terminal_failed/none, дают одну безопасную unrecognized без исходного значения. Groups сортируются по state, count=sum(groups.count). Более широкий DeletionState не расширяет allowlist; статический поиск не доказывает полноту динамических или исторических writers. |
| CHK003 | PASS. D3 и spec731–733 прямо ограничивают active_purge_complete сохранённым состоянием запроса. Service430–439/794–802 сохраняет завершение активной очистки отдельно от других границ. ConstitutionIV/PRD25 требуют различать первичные объекты, backup/local/MediaScribe/post-egress и сохраняемую по операторской политике Generation Call/Langfuse/Temporal. O14 не принимает эти результаты и не объявляет сохранённую наблюдаемость ошибкой очистки. |
| CHK004 | PASS. D3/model9–12 запрещают читать completed_at и выводить даты, возраст, SLA или долю успеха. artifact_completion/deadline_status/job_attempts/job_errors/job_retries в nested values остаются null; reaction также null по D4. Даты в строках не дают доказательства результата удаления. Quickstart96–98 включает future/infinity/NULL и независимость от report_date. |
| CHK005 | PASS. D4: nested всегда partial, reason=unrecognized при такой группе, иначе artifact_and_deadline_uninstrumented. Root всегда partial; unrecognized любого источника приоритетнее invalid_schedule fair-use, затем deletion_details_and_reaction_uninstrumented. Пустой доступный источник=count0/groups[]/partial. Ошибка схемы/доступа отвергает весь CLI, не превращается в пустой успех. Plan/quickstart92–105 сохраняют это различие. |
| CHK006 | PASS. D4, spec729–730 и plan89–91 разделяют сущности. Старые fair-use count/groups/pending_review сохраняются отдельно; count запросов к ним не прибавляется. Недостаток данных о реакции остаётся reaction=null. Generic _groups зависит от timestamp и не используется для нового источника. |
| CHK007 | PASS как достаточность ограничений. D5/plan85–108 разрешают один helper и одну SQL state/count агрегацию в прежнем monitoring.py, вызов из прежнего fair-use collector. IDs/связи/request_source/reasons/confirmation_boundary/policy/metadata/времена/объекты не выбираются. Writers/purge/retention/repair/egress запрещены; новых схем/прав/зависимостей нет. Прежние maintenance guard, forced RLS, один UTC as_of/READ ONLY REPEATABLE READ, общий15с/statement5с/lock2с/500gaps/64KiB и rollback/close остаются. Guard/CLI перечитаны целиком, но исполнение здесь не проверялось. |
| CHK008 | PASS. Model/research/plan95–99 различают настоящее ограничение migration0007 NOT NULL/defaultrequested и отсутствие явного nullable=False в объявлении модели; из последнего не выводится фактическая nullable-семантика ORM. Миграция целиком задаёт ENABLE/FORCE RLS с maintenance predicate. Quickstart95–97 требует реальную мигрированную схему, отказ NULL INSERT отдельно и defensive SQL VALUES отдельно. Положительная схема не ослабляется ради NULL-теста. |
| CHK009 | PASS как полнота плана проверки. D6/quickstart87–109: до кода допуск/analyze, затем RED; настоящие PostgreSQL/CLI/FORCE RLS/NOT NULL; четыре состояния и объединённые unknown/NULL; private sentinels; два RR снимка/новый процесс; no-write/fingerprint; ошибки схемы и роли. Прежняя integration fixture/fingerprint расширяется моделью request, FK-схему создаёт штатный runner, строки синтетические. Затронутые fair-use/identity/SET ROLE/READ ONLY случаи обязательны. Неподверженные успешные наборы не повторяются и повторы не суммируются; очистка только своего runner через finally. Это не сообщение об исполненных тестах. |
| CHK010 | PASS. D6 и все семь документов задают независимый reviewer-owned допуск → scoped analyze → исходная #4932 → RED/код/профильные проверки → независимый code review/converge/exact SHA/base gates. Нет новой задачи или issue. T077 и T070 остаются [ ];87 полных task lines побайтно равны HEAD. Старые19checklists неизменны,256 отмечены/58 открыты. Полный O6/FR089, прежние сроки и исторический пробел O8 не объявлены выполненными. Для этой частичной области допустимо только Refs #4932. |

## Проверенные предпосылки исходников

Это статическая проверка соответствия требований существующим структурам,
а не исполнение SQL, проверка текущих прав production или доказательство RLS.
Модель deletion прочитана целиком:cb30b9; migration0007 целиком, enum и writers:
a6a1d7/bc1c8d; collector/fixture:bc1c8d; guard/CLI целиком:c04485;
0102/tenant_context:2ba2ef; штатный PostgreSQL runner:47206f/c5151e.

| Путь | SHA-256 при допуске |
| --- | --- |
| apps/server/src/twobrain_rec_server/db/models/deletion.py | `fc535eaefb2eb265cae174508dcb06b548a3df3dc1f4bd54fb68a50d79ff4d27` |
| apps/server/src/twobrain_rec_server/db/migrations/versions/0007_retention_deletion_execution.py | `6ade5be83afcd81c29b944651c3a08ac1916e1f0a6b037277f4a744e23da886c` |
| apps/server/src/twobrain_rec_server/domain/statuses.py | `e0456469a0f7ff628a1abce0af12008803e8b14b96742c45f54296aa5b0a60b7` |
| apps/server/src/twobrain_rec_server/deletion/service.py | `4534012daa4f54dfe5fd58cc8bba5674c4771e9c108697c34820b4a3c5b3aa00` |
| apps/server/src/twobrain_rec_server/billing/monitoring.py | `c8118e504aa00a2d12dbb5d218151fa37328e8d56ac58ae875c7b56883ba4bd9` |
| apps/server/src/twobrain_rec_server/billing/database.py | `b75f7a35952b8725ac1017e926ddea3449f480c71de0d6b3a7f83ae49fe6197f` |
| apps/server/src/twobrain_rec_server/cli/billing_monitoring.py | `68ca13c2e36f1958124d2a60300b326941d73f34d481f4834afe18abac1aab55` |
| apps/server/src/twobrain_rec_server/db/migrations/versions/0102_summary_sharing.py | `348b0cb15331eb1423818afaae6b9e66e7a0e0c86da1ae5cc24d39410e34ef5a` |
| apps/server/src/twobrain_rec_server/db/tenant_context.py | `a42161e70629b4c2ffd916110fece8f764e2e2569ea258d2ce7fda335eee3bd7` |
| apps/server/tests/integration/test_billing_monitoring_postgres.py | `424cd2dc473962c47ba4204d444dd202e906b7b1405c7aa9519fb662d9781876` |
| apps/server/tests/integration/test_billing_registry.py | `e80244f0f946392227b1c508ed2a900dd925fab2a26e3ef8529f721839981bef` |
| apps/server/tests/fixtures/postgres_test_database.py | `9975596c2901035e2f58fe16481a19d1bc4d3924e8b3a00b1da69cfe80df505b` |

## Остаток и предел допуска

Повторная собственная проверка5689a6: семь SHA требований совпали; все87/87
полных исходных строк задач равны HEAD2d279420b9f825c55eb5d03734de2528df5a46ea;
19 прежних списков побайтно равны HEAD,256 отмечены/58 не отмечены.
Новый список deletion-inventory отдельно:10 отмечены/0 не отмечены.

T077/#4932 остаётся открытой: весь O6/FR089 не реализован этим обзором.
Открыты полнота источников, сохраняемые attempts/errors/retries, регулярные
heartbeat/alerts/retry и сохраняемый путь реакции
detected→contained→owner_assigned→notified→investigating→resolved|accepted_risk.
Сроки сохранены: transient15мин/24ч, fair-use≤24ч, receipt canceled немедленно/
pending3дня, registry/F278FR041 реакция≤24ч. Цель PRD25 первичной очистки
eligible artifacts≤24ч новым inventory не измеряется. T070 отдельна.
Исторический пропуск чтения до кода PR7884 не исправлен: весь O8 не PASS.

Этот reviewer изменил только checklists/deletion-inventory.md и данный отчёт.
Код, тесты, остальные требования, старые checklist, tasks, governance,
Git/GitHub, БД, GRAF Dev, пользовательские данные, Full/CD и релизы не менялись.
Тесты не запускались; GitHub live-состояние не проверялось. Допуск не заменяет
scoped analyze/сверку исходной issue до кода и все последующие RED, настоящие
проверки, независимые code review/converge и три exact SHA/base PR gates.
