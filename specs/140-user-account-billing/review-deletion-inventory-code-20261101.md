# Независимое ревью кода и сверка converge F140/T077 O14 — 01.11.2026

Исполнитель /root/f140_notification_content_review, собственный диалог
01a1955c-cb77-78e3-8844-ffeabcb2d594. Полоса high-risk-product/repository-audit.
Копия f140-referral-reversal/crisp; ветка codex/140-observation-deletion;
HEAD/base2d279420b9f825c55eb5d03734de2528df5a46ea.
Решение: APPROVE кода O14 и PASS отдельной сверки scoped converge.
Открытых новых замечаний CRITICAL/HIGH/MEDIUM/LOW:0/0/0/0.
Это локальное ревью ограниченной реализации, не разрешение закрыть #4932
или пропустить будущие проверки точного PR SHA и основы.
Разрешённая запись — только этот отчёт. Тесты не повторять.

## Собственное чтение и происхождение

Собственный requirements report SHA256
1c2c516deb34fdc5acb90d30d2f1f76eb184718e93f85c1672e6f74391a8c5d4 и
checklist SHA256440f29373b973f31b91ca6d7c5e5bebf8515330ee0937d3b5da060e2e23ddcab
сверены фактически:6a39cf; тот же исполнитель и диалог подтверждены session_meta
собственного журнала. Все7 изменённых оригиналов требований неизменны; прежнее
собственное полное чтение повторно используется только после проверки происхождения
и сумм, с восстановлением применимых оригиналов. Document-reading прочитан
целиком заново:0d38a7. Навык code-reviewer прочитан: d3b1bc/6aa07f;
усечённые части общего вывода не засчитываются за чтение отсутствующих частей.

| Новый полностью прочитанный документ | SHA-256 | Неусечённые собственные выводы |
| --- | --- | --- |
| apps/server/src/twobrain_rec_server/billing/monitoring.py | `70f9e403a1a3204f0d49f0891ceabbd559229091b7701508853e8ee75fc2a34d` | 1–190:f44287;191–374:4b5a0c. Полностью; запись сразу после полного чтения. |
| apps/server/tests/unit/test_billing_monitoring.py | `03c0c13de1a698deb6ed28a11775ad46ddcba922e0a9400dfb6a3041778a72f8` | 1–287:3ee096. Полностью; запись сразу после полного чтения. |
| apps/server/tests/integration/test_billing_monitoring_postgres.py | `b91641d81d7aface7eacad99fceed1573aa41e93ee6657a3961078aeacfc0bf6` | 1–225/1454–1630:65d018;216–500:589e4a;501–790:506a1a;791–1050:beebf5;1051–1270:1ecc7c;1271–1453:fd0646. Полностью; запись сразу после завершения чтения. |
| changes/unreleased/F140.yaml | `2cb75f1c135d3d022aac0157da2e45ffb936038ef5d54ce697cf65028dcffdf8` | целиком:fd0646. Полностью; запись сразу после завершения чтения. |
| specs/140-user-account-billing/converge-deletion-inventory-20261101.md | `3d2f4a81ef280ad626425dd74d631e9b6d57c464e0ab6fec2a47ab4845661af8` | целиком:fd0646. Полностью; запись сразу после завершения чтения. |
| specs/140-user-account-billing/t077-deletion-inventory-validation-20261101.md | `55ef9a8dfa214979dc0cfcea105fec44aaa5dbc1c27d28046b7be83aec530117` | целиком:fd0646. Полностью; запись сразу после завершения чтения. |

## Восстановление применимых требований и зависимостей

Семь обязательных оригиналов из собственного requirements report повторно
проверены не только по SHA:29/29 неусечённых исходных выводов фактически
сопоставлены с текущими диапазонами в своём журнале, output e19284.
Собственная session_meta и прежние отчёт/список подтверждены6a39cf;
10 отмеченных/0 не отмеченных пунктов допуска остаются неизменными.
Применимые требования доступны в текущем контексте и дополнительно перечитаны:
O14D1–D6 целиком:abcab6; plan83–110/quickstart85–109/research1–23/model1–13:
a029f2 (эти целые разделы присутствуют в выводе). O1–O4/O6–O8:a029f2,
O5 дополнен cacb36; исходные сроки O6/O8 повторно270398.

Карта нормативных зависимостей остаётся из собственного requirements report:
конституционные I–VII, privacy/deletion/наблюдаемость PRD25–26,
ограничения текущего статуса и product-gates, порядок Spec Kit, tracker и PR
gates. Все16 нормативных SHA из прежней таблицы повторно совпали.
Для проверки кода восстановлены конституция89–259:b65117,
260–530:76d99d с дополнением425–459:cacb36/460–530:270398;
PRD1578–1777:270398; текущий статус179–217/529–570:bccb2e;
release-and-validation171–244/758–770:bccb2e. Базовые полные собственные
чтения и остальные применимые разделы доказаны предыдущим отчётом, не чтением
другого исполнителя. Усечённые d3b1bc/6aa07f/753d04/a029f2/76d99d и общий
вывод387f9a+98c62b не выдаются за полностью прочитанные отсутствующие части.

Прочитан весь текущий monitoring.py, весь unit и весь integration monitoring
файл по указанным диапазонам. Зависимости модели, migration0007, enum/writers,
_source/_closed, guard, CLI, session/transaction-local context и штатный
runner проверены по исходникам. Неизменные guard/CLI, схема и writers совпали
с собственными ранее прочитанными версиями (6a39cf); новый полный model:b37fe1.
CLI/guard оригиналы присутствуют387f9a, session/context:b37fe1;
fixture ролей и runner/finally:387f9a, prepare_schema296–320:c1e8bb.
prepare_schema вызывает настоящий Alembic upgrade head, не create_all.
Migration0007 определяет NOT NULL/defaultrequested и ENABLE/FORCE RLS;
helper maintenance сохраняется до0102, поиск более поздних замен:bccb2e.
Bootstrap runtime database roles288–325:270398 сохраняет прежний grant
служебной роли на все таблицы/последовательности и default privileges.
Это статическое доказательство отсутствия нужды в новых правах, не проверка
прав установленного production. Новых миграций, ролей и настроек нет.

## Самостоятельное ревью D1–D6

| Требование | Исход и проверенные основания |
| --- | --- |
| D1 | PASS. monitoring288–299 использует именно MeetingDeletionRequest/state, без WHERE, дат и аргумента дня; один запрос GROUP BY/ORDER BY CASE и count. _source даёт database_inventory/current_state. Root325 и nested294 имеют точные разные source. PG1512–1590 исполняет настоящий CLI из новых процессов с1999/2026/2099 report_date и сравнивает всё семейство; запросы одного meeting считаются отдельными строками. |
| D2 | PASS. DELETION_STATES39 содержит ровно requested/deleting/active_purge_complete/retryable_failed. _closed47–48 SQLCASE направляет всё остальное, включая SQLNULL, в один unrecognized. SELECT сортирует по этой группе, count=sum(count). PG1512–1590 проверяет восемь реальных строк:4known+complete/terminal_failed/none/private-state; вывод ровно5групп с4unknown. Отдельный SQLVALUES проверяет NULL+private-state как2unknown и deleting как1. Реальная NOT NULL схема отдельно отвергает INSERT NULL в1473–1509. Общий enum не подменяет закрытый набор. |
| D3 | PASS. Код и docstring не объявляют фактическое удаление;288–299 возвращает только группы/число и пять None:artifact_completion/deadline_status/job_attempts/job_errors/job_retries. completed_at/возраст/успехи/SLA не читаются. Fragment явно отделяет active_purge_complete от фактической очистки, backup/local/external и retained Generation Call/Langfuse/Temporal. PG пустота и unit3 проверяют форму, PG состояния сnull/future/infinity датами выполняются без их чтения. T070/приватностная приёмка не подменяются этим inventory. |
| D4 | PASS. _source84–87 даёт partial для обоих новых reason; nested ни в одной ветви не observed. Root322–324:unknown fair-use или deletion выше invalid_schedule, затем deletion_details_and_reaction_uninstrumented. Старые fair-use count/groups/pending_review сохранены отдельно, reactionNone; deletion count8 при fair-use count1 проверены вместе с invalid_schedule1 и rootunknown. Empty проверяется точной формой. Ошибка имени state даёт failure(report_unavailable)/exit1 и пустой stderr через настоящий subprocess, затем схема восстановлена finally. Затронутые fair-use тесты сохраняют старые buckets и приоритет unknown самого fair-use. |
| D5 | PASS. Production diff — import,4state, один helper288–299 (12 строк от def до последнего выражения,14 добавленных строк с разделяющими пустыми), включение в прежний collector. Одна агрегация, ни одного private/time поля или SELECT ORM-объектов; нет новых служб/зависимостей/writers/egress. PG считает ровно1SQL по requests и отвергает WHERE/ID/reasons/metadata/времена; guards на HTTP/request_meeting_deletion и no-write fingerprint остаются. Это дополняет статическую проверку, а не доказывает перехватом любой возможный внешний вызов. Guard334 выполняется до предметных чтений. Единая READ ONLY RR/as_of/15с/5с/2с/500gaps/64KiB/cleanup не изменена; identity/SETROLE/READONLY регрессии есть в finalPG9. |
| D6 | PASS локальной последовательности. Мой независимый допуск10/0 предшествует RED; scoped analyze6req/1task/100%/0findings и существующая #4932 сохранены в отчётах. RED подтверждает отсутствие helper3ImportError и старый root source1assertion; RED returncode не сохранён и не выдан за PASS. Final15unique,6new+9affected,безfail/error/skip; hashes/nodeids/XML/log/настоящие exit0 проверены ниже. PG1593–1630 доказывает старый RR snapshot0 после commit, новый snapshot1, новый CLI process1; fingerprint не меняется. Реальный runnerfinally очищает только свой UUID контейнер.87 полных task lines/T077[ ]/T070[ ]/старые58gaps сохранены. Это ревью закрывает независимый code/converge шаг; точные PR gates остаются будущими. |

## Проверка исходных результатов и происхождения запуска

Внешний manifest прочитан0d38a7 и фактически сверен6a39cf/753d04:
11/11 frozen inputs совпали с рабочими файлами;8/8 контрольных сумм четырёх
XML/log пар совпали. XML распарсены стандартным ElementTree: точные suite
attributes и classname::name всех testcase равны manifest. Final testcase
не содержат failure/error/skipped. Наборы финальных nodeids не пересекаются:
15различных=6new+9affected. Конкретные ожидаемые assertions сверены с исходниками,
поэтому один лишь зелёный XML не принят за достаточное доказательство.

| Набор | Результат | Предел доказательства |
| --- | --- | --- |
| f140-deletion-red-unit3 | 3failure/0error/0skip,0.108с | ImportError отсутствующего helper в owned monitoring.py. История RED; pytest returncode неизвестен. |
| f140-deletion-red-pg1 | 1failure/0error/0skip,4.968с | Старый source fair_use_reviews вместо составного. История RED; pytest returncode неизвестен. |
| f140-deletion-unit6 | 6PASS/0failure/0error/0skip,0.050с |3новых параметризованных случая+3затронутых fair-use. |
| f140-deletion-pg9 | 9PASS/0failure/0error/0skip,46.808с |3новых PGсценария+4fair-use+2identity/context/readonly. |

Оба final log имеют два известных предупреждения: PytestAssertRewriteWarning
для fixture module и StarletteDeprecationWarning по httpx. SAWarning отсутствует.
Полные nodeids и8hashes сохранены в исходном manifest; они проверены753d04.
Сырой тестовый connection URL и содержимое отказов в этот отчёт не копируются.
Тесты мной не запускались.

Настоящие outputs отдельно извлечены из журнала основного исполнителя
01a140f0-8073-7de0-bc68-03d1ac57ff06, а не приняты со слов manifest:
45ac8a/cc3620. В записи200193/call_3dafa81231274b37995429e36b70d8b5
виден subprocess.run из owned apps/server/.venv с PYTHONPATH=src:., сохранением
XML/log и sys.exit(r.returncode). Unit final622fe7,запись200196:
pytest_returncode0/outerexit0. PG worker session50457 завершается в
70fe5d,запись200226/call_50f776405eed4ebd8ba17d358d935b9e:
pytest_returncode0/outerexit0. Это конечный результат того же процесса.

При проверке обнаружена и сообщена владельцу неточная ссылка во внешнем
runner-output-provenance: c4940a/200218 был промежуточным running ответом,
а не PG final. Владелец исправил ссылку на70fe5d/200226 и сохранил correction;
исправление прочитаноcacb36. Код, frozen11 и исходные результаты не менялись,
тесты не повторялись. Замечание к происхождению доказательства устранено;
открытых замечаний к коду на его основании нет.

Cleanup проверен отдельно: baseline9 имён в0a29e6/200069 и последующий полный
список9имён в204c7f/200317/call_6a6920c8f0c14a3794185d56ad48978c совпадают
побайтно после сортировки (45ac8a/cc3620/e19284). Промежуточный dfd332 был
фильтрованным списком только postgres-test-bootstrap; за весь список он не
выдаётся. Старый чужой контейнер31.10 и Dev/AIRIS сохранены; новых своих
контейнеров не осталось. Fixturefinally375–445 проверяет returncode удаления
строго своего UUID имени. Это подтверждает cleanup окружения проверки,
не удаление пользовательских встреч и не полный runtime аудит Dev/AIRIS.

## Независимая сверка scoped converge

converge-deletion-inventory-20261101.md и validation report прочитаны целиком
fd0646; ниже собственное сопоставление, не принятие их PASS без проверки.
Шесть D требованиям соответствуют реализации и15finalcase выше. D6 корректно
называет будущие PR gates и не объявляет полную T077 завершённой.

| Семь решений plan | Проверка реализации |
| --- | --- |
| Переиспользование | Тот же monitoring/fair-use/CLI и _closed/_source; нет нового слоя. |
| Одна агрегация | Один db.execute(select(CASEstate,count).group_by/order_by),PGфиксирует1SQL. |
| Закрытые группы |4known+1unknown,без общего enum;реальные unknown и defensiveNULL исполнены. |
| Раздельные сущности |Rootfair-use counts/buckets прежние;deletion вложена отдельно,reactionNone. |
| Мигрированная fixture |TABLES/fingerprint добавляет request,FK Meeting/Device синтетические;Alembichead/NOTNULL/FORCERLS;SQLVALUESне ослабляет схему. |
| Профиль |3новых unit+3PG;3старых unit+6PG;15уникальных,не повтор всех прежних наборов. |
| Порядок |Независимый requirementsPASS/analyze/исходнаяissue/RED→код/профиль→это independentreview/converge→будущие exactPR gates. |

| Принцип конституции | Независимый результат |
| --- | --- |
| I Capture-first |Сбор/аудио/нативный путь и удалённый legacy не затронуты;diffтолько серверное внутреннее чтение. |
| II Visible consent/control |UI/настройки/Record/Stop/разрешения не изменены;нового captureнет. |
| III Observability/data boundaries |В БД выбирается закрытый state/count;нет content/credentials/egress/новой очистки GenerationCall/Langfuse/Temporal. |
| IV Deletion truth |Сохранённый active_purge_complete не доказательство фактического удаления;детали/SLAunknown,retainedobservability явно сохранена. |
| V Public distribution |Нет macOSсборок,подписи,публикации,appcastилирелиза;distributiongates не ослаблены. |
| VI Spec-driven gates |Текущий high-risk slice использует исходную T077,уточнённые7docs,независимый10/0,analyze,RED/PG;триexactPRgatesещёвпереди. |
| VII Reference fidelity |ПользовательскийUI/референс/ассеты не меняются;нет сторонних заимствованных материалов. |

Итог сверки:6/6 требований,7/7 решений plan,7/7 принципов в области O14
согласованы. Новых missing/partial/contradicts/unrequested findings:0.
Существующий HIGH partial полного FR089/O6 остаётся в T077, не исчезает из-за
этой оценки. Converge и validation report не дают оснований закрывать #4932.

## Контрольные суммы внешних доказательств

| Файл | SHA-256 |
| --- | --- |
| f140-t077-deletion-implementation-validation-20261101.json | `ba8efa6c32fe040500705d39ee07655a3731ba87dca60bd508766d8c736b82f3` |
| f140-t077-deletion-runner-output-provenance-20261101.json | `cd53c166ad0ae158e7860e793c786beb2721a7d7149cc351da5471baf0ae6d9b` |
| f140-t077-deletion-cleanup-verification-20261101.json | `6dd5630519501ea15316b658c09c2c3c19f98d20ad0f35651c5e90f3f038cefa` |

## Пределы и следующий шаг

T077[ ]/#4932, полный O6/FR089 и отдельная T070 остаются открытыми. Полнота
источников, storage/add-on/финансовая сверка, сохраняемые attempts/errors/retries,
регулярность/heartbeat/alerts/retry и реакция
detected→contained→owner_assigned→notified→investigating→resolved|accepted_risk
ещё требуют реализации/приёмки исходной задачи. Нет новой issue или дублирующей task.
Сроки transient15мин/24ч, fair-use≤24ч, receiptcanceledнемедленно/pending3дня,
registry/F278FR041≤24ч и PRD25primarypurge≤24ч не приняты этим обзором.
Исторический пропуск O8 до PR7884 не исправлен и не объявлен PASS.
87/87 полных исходных task lines и19прежнихchecklists256отмечены/58открыты
сохранены; мой deletion checklist остаётся10/0. Допустима только Refs #4932.

Reviewer изменил только этот отчёт. Код, тесты, требования, checklists,
Git/GitHub/БД/Dev/данные/Full/CD/релизы не менял; GitHub live не запрашивал.
Здесь не подтверждаются production-права,реальные данные/удаление,финансовая,
ручная или выпускная приёмка. Следующий шаг владельца — финальная сверка
неизменности inputs,коммит/PR и governance-fast/macos-pr/pr-metadata с общим
валидатором точного SHA/base. APPROVE не заменяет эти обязательные проверки.
