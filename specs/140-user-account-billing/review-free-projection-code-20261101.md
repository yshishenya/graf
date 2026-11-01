# Независимое кодовое ревью T077/free_projection — 01.11.2026

**Результат: APPROVE только реализации O9/P1–P6.** Замечаний к этому
срезу: CRITICAL 0 / HIGH 0 / MEDIUM 0 / LOW 0. Полный FR-089/O6 остаётся
прежним **HIGH / partial** в исходной T077/#4932; новой задачи нет.

Исполнитель `/root/f140_notification_content_review`, независимое назначение
основного `/root`; владелец реализации repository-audit. Рабочая копия
`f140-referral-reversal/crisp`, ветка `codex/140-observation-coverage`, HEAD
`b64cd4ce490081437e460376884214519949e723`.
Полоса реализации — `active Spec Kit slice / high-risk-product`;
это ревью только чтением с разрешением записать данный отчёт.

## Основания решения

Полностью прочитаны текущие monitoring.py, оба изменённых тестовых файла,
F140.yaml, неизменённые CLI и maintenance guard. Проверен diff четырёх
исходных файлов. Конкретные выводы:

| Требование | Проверка реализации и доказательства |
| --- | --- |
| P1: источник | monitoring.py95–140 и228: точный action, database_inventory/event_window; count считает строки. Другие current_state семейства и общая partial не изменены. Семейство не выдаётся за все Free paths, число оплат или своевременность. |
| P2: календарь | monitoring.py102–113: обе московские полуночи отдельно переводятся в UTC, затем используется min(end,as_of). SQL124 исключает точный as_of и end. Unit проверяет исторический 25-часовой московский день26.10.2014; PostgreSQL — start−1µs/start/as_of−1µs/as_of/as_of+1µs/end−1µs/end и точные start/end расчёта. |
| P3: группы | monitoring.py116–125: target_kind проверяется совместно с ровно тремя парами. SQL CASE при FALSE либо NULL даёт одну безопасную пару unrecognized/unrecognized. В PostgreSQL проверены невозможная blocked/unknown_pending, NULL reason, иной target и произвольные приватные исходные значения. Count равен сумме групп; порядок детерминирован. |
| P4: неполнота | monitoring.py126–139: NULL считается по всему доступному action inventory; >=as_of считается только в выбранном [start,end). Основные группы этих строк не содержат. Приоритет unrecognized → undated_time → at_or_after_as_of → window_open → empty/observed совпадает с контрактом; ветви empty и observed взаимно исключаются по count. Все количества сохраняются. PostgreSQL последовательно проверяет каждый приоритет, пустой открытый и закрытый день. |
| P5: недоступность | monitoring.py97–111: атомарно сохраняются null границы при overflow; ошибка date.max при вычислении следующего дня и UTC overflow date.min дают unavailable. Будущий день возвращается до audit SQL, что отдельно проверено AsyncMock. Реальный CLI сохраняет чтение других семейств; удалённый столбец audit даёт безопасный отказ целого отчёта. |
| P6: безопасность | Две агрегирующие SQL-команды выбирают только закрытые группы/количества, без metadata_json/target_ref/IDs. Guard предшествует источникам; CLI фиксирует as_of до подключения и сохраняет READ ONLY REPEATABLE READ до hook/первого SELECT. Guard/RLS/таймауты/cleanup/лимиты не менялись. Реальные роли/SET ROLE/неверный контекст/попытка DELETE перепроверены затронутыми тестами. Новых служб, зависимостей, таблиц, разрешений или сетевого пути нет. |

Поздний commit проверен настоящими двумя соединениями
(integration/test_billing_monitoring_postgres.py648–697): writer начинает
транзакцию, reader закрепляет RR-снимок до INSERT, PostgreSQL default now()
совпадает с transaction_timestamp(), commit наступает позже. Старый снимок
не меняется, новый видит событие, новый CLI-процесс тоже видит его.
Закрытый календарный день здесь моделируется явно заданным as_of после end;
реальное прохождение полуночи или commit после такой реальной полуночи
не заявляется. Это соответствует принятому quickstart.

До и после чтения/двух новых процессов сравниваются снимки всех семи
предметных таблиц, теперь включая audit. Синтетические приватные значения
не попадают в JSON, stderr нового процесса пуст. Перехват SQL проверяет
отсутствие частных колонок; in-process HTTP запрещён. Новый код содержит
только SQL SELECT и календарный расчёт, не вызывает почту/provider/analytics.

## Фактические журналы выполнения

Самостоятельно прочитаны сохранённые PG6.xml/log и unit4.xml/log:
исходный неусечённый вывод `e265d9`. Разобраны XML и сравнен полный набор
имён с implementation-validation JSON: **10 уникальных PASS, 0 FAIL,
0 ERROR, 0 SKIP** — семь новых случаев и три затронутых прежних повтора.
PG:6 за34,479с; unit:4 за0,033с. По два предупреждения pytest/Starlette,
не отказы. PG runner явно завершил
`postgres_test_cleanup=isolated_container_removed`.

RED XML подтверждают четыре unit failure из-за отсутствующего helper и
один PostgreSQL failure на прежнем source=null; соответствующие причины
прочитаны в журналах. RED PG остановлен после первого отказа и не считается
тремя выполненными случаями. Старые26+3/498 и другие PASS не прибавляются.
Новых pytest/Docker/CLI-прогонов это ревью не запускало.

По записи исполнителя после PG PASS удалён только неиспользуемый
sqlalchemy.select из тестового импорта; исполняемый collector не менялся.
Текущие четыре исходных хеша совпали с замороженной записью. Это локальное
доказательство байтов, не замена последующих GitHub exact-SHA/base gates.

| Сохранённый артефакт | SHA-256 |
| --- | --- |
| free-projection-pg6-20261101.xml | `6bc93c98171ab6e61629d79d9263ebc1f8eef4c8746833fad63aa6a2ac077bf5` |
| free-projection-pg6-20261101.log | `c6f8b160ca61bfcb43bc893b451130fffd91d7ba2958f2bf13bc5a311a023d07` |
| free-projection-unit4-20261101.xml | `38a7754d57f89288dae8c5bf763571d9b8581206165aedae083fe6151241490b` |
| free-projection-unit4-20261101.log | `dd16fd7696a5282a7cf79eb2b6afc6d5a5c069263efe90c3d3d4dbc2795564e0` |

Полные имена имеют префикс `f140-t077-`; внешнее хранилище доказательств —
`graf-f140-final-failure` за01.11.2026. Исходные секретоподобные значения
одноразового RED-стенда в этот отчёт не копируются.

## Чтение и процесс

Собственные первоначальные полные чтения того же дочернего диалога
`01a1955c-cb77-78e3-8844-ffeabcb2d594` сохранены в
[предыдущем отчёте требований](review-free-projection-requirements-20261101.md).
Это собственные чтения, а не чтение `/root`. Сейчас проверены фактические
исходные tool outputs своего диалога: все диапазоны семи документов
побайтно совпали (`9c67ea`). Восстановлены собственные полные PRD1–1100
(call_a2212eb8b63549c9bb27b94fe012e440), PRD1101–1750/1751–2474
(call_8d96fe89ade44fa5a623776881199f94; оба фрагмента отдельно совпали),
current status целиком (call_10637b7ccba74d8c981ba819ecc3fb5b),
конституция и product-gates. Хеши12 поддерживающих документов вновь
совпали с прежним отчётом (`2035a5`). Усечённые совмещённые выводы не
использованы вместо полного чтения.

После восстановления повторно прочитаны оригиналы применимых разделов:

- O1–O9 целиком; новые разделы spec/plan/tasks/quickstart/research/data-model
  и reviewer-owned checklist (`a3fdee`, `b5fabd`).
- Конституция I/II, IV/VI, Platform/Development/Governance и product-gates
  целиком (`cfcaa8`): сохранение денег/данных/полномочий, metadata-only,
  ограничения захвата и независимые ворота.
- PRD13/14,25/26,31,39 (`9658af`): диагностическая приватность, audit,
  observability и приоритет уточняющей спецификации.
- Operations/security contracts (`cfcaa8`), registry contract целиком и
  current status F140/F199 (`4cd7a6`): общий магазин, реальные роли,
  финансовая приёмка и сохраняемый остаток не подменяются счётчиком.
- README/document-reading (`a0de49`, `6f2a7e`), development-process целиком,
  spec-kit-flow implement/converge, release lanes/PR/Git/evidence
  (`07e30f`): владение отчётом, выбранная полоса и точные PR gates.

Прямые применимые зависимости разрешены этой картой и прежними
подтверждёнными собственными чтениями. Нового затрагивания финансовых
путей F278, приложения, capture, удаления, поставщика или выпуска нет;
их отдельная приёмка этим отчётом не расширяется.

Прочитаны scoped analyze/converge JSON и отдельный отчёт реализации.
Analyze:6 требований/1 исходная задача/100%/0 новых замечаний;
converge:6 требований/7 решений плана/7 принципов, без новых gaps.
Их граница совпадает с настоящими изменениями. Предметное независимое
ревью требований осталось **10 отмечены/0 открыты**. Новые семь собственных
полных чтений `/root` до этого кода отдельно перечислены в current-reading
verification JSON; это процессное доказательство исполнителя, не мои чтения.
Исторический пропуск обязательного чтения до первоначального кода PR7884
сохранён, задним числом не исправлен и за полный O8 PASS не выдан.

## Одиннадцать замороженных входов

Все строки сверены с
`f140-t077-free-projection-implementation-validation-20261101.json`.
Повторное совпадение требуется перед передачей итогового решения.

| Путь | SHA-256 |
| --- | --- |
| apps/server/src/twobrain_rec_server/billing/monitoring.py | `b8caa43321df419cb63a3d2e065e6491caf677812f82a282b5ec0b35086afa6e` |
| apps/server/tests/unit/test_billing_monitoring.py | `ae7d0542d41af78ac4a914be163e4211e1bbf18de0240ac0d09033a353f6d2da` |
| apps/server/tests/integration/test_billing_monitoring_postgres.py | `6e0e749f4b74f9a8f062bd64d819df814152ff5e0d43b4f8cf5f743ee9dd8672` |
| changes/unreleased/F140.yaml | `fbcb273fc7c1ef5188717c9089bbc74bf903e247c8bf6171ae8f8e17efca253f` |
| specs/140-user-account-billing/spec.md | `4516377b78239a51f9051db67d642be204f6a157d0f9d88f4bf9f8301b9d0a6d` |
| specs/140-user-account-billing/plan.md | `51a5b24a4a457c10ccbe958db02c1feb337953b628423207502de03e2bf0de2a` |
| specs/140-user-account-billing/tasks.md | `c7df79a639522a32a04ac7ff1e404eab0414405279dd525dd70a57d6e5983cc2` |
| specs/140-user-account-billing/quickstart.md | `3f1e479e82c4a9ccdd9dd56e0bc656930a0e9147b6558154285efbfe1368c823` |
| specs/140-user-account-billing/research.md | `7d91d2ae9038473df1af0183260d02f2bc5d6c5b968fb04b6b23a4827a1aca8c` |
| specs/140-user-account-billing/data-model.md | `7cbf5b850191062e9ff6421164a12ad86483928b294319944858bdf5f735a5f5` |
| specs/140-user-account-billing/contracts/operator-observation.md | `13fdc6afd96714e27590ed4c8cf49fd30182bc1c18bb96e162bcf8f085ca218b` |

## Граница результата

T077 остаётся `[ ]`; #4932 остаётся OPEN по текущим материалам основного
исполнителя. GitHub это ревью не меняло и отдельного live-запроса не делало.
Все87 исходных task lines и58 прежних общих checklist gaps сохраняются.
Полный O6/FR089, остальные источники, постоянные показатели, регулярность,
heartbeat, тревоги/retry и сохраняемая реакция с owner/severity/evidence/
сроком/закрытием этим срезом не завершены. PR допускает только `Refs #4932`.

До слияния обязательны governance-fast/macos-pr/pr-metadata на новом точном
SHA и проверенной основе через общий валидатор. Нет нового Full/CD,
production, GRAF Dev, ручной/финансовой приёмки или закрытия issue.
Разрешённая запись — только этот отчёт; код/тесты/требования/checklists/
fragment/Git/GitHub/данные не изменялись. Повторять успешные тесты для
данного документа не требуется.
