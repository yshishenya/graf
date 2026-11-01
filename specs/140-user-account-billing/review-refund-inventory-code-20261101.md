# Независимое ревью кода и сверка F140/T077 O11 — 01.11.2026

Решение: APPROVE для локальной реализации O11/R1–R6 и перехода к новым
обязательным PR-проверкам. Содержательных замечаний по изменённому коду нет.
Это не завершение T077, полного O6/FR089, всего O8, финансовой сверки или выпуска.

Проверяющий: /root/f140_notification_content_review, дочерний диалог
01a1955c-cb77-78e3-8844-ffeabcb2d594. Владелец реализации: repository-audit.
Рабочая ветка codex/140-observation-refunds; HEAD/base
1d92f88e587f52a9f452d41976e5faacc06d8a68. Полоса реализации:
high-risk-product/active Spec Kit slice; назначение проверяющего — независимое
чтение кода, сохранённых доказательств и отдельная scoped converge-сверка.

Проверяющий записал только этот отчёт. Тесты, сборки, команды, меняющие БД,
приложение, Git/GitHub, commit/PR/release/deploy, не запускались. Успешные
проверки повторно не исполнялись. Чужие изменения сохранены.

## Происхождение контекста и собственные чтения

Первое полное чтение семи оригиналов и неизменного корпуса принадлежит этому
же проверяющему в этом же диалоге. Запись и точные исходные call IDs находятся в
[предыдущем собственном отчёте требований](review-refund-inventory-requirements-20261101.md),
SHA-256 d0ba125929eb5aa1520b684d4f807caf57d4c67da81d6ccd3ebc6349cbbf94c1.
Текущий checksum checklist refund-inventory.md:
d6412b0e3652c125c866f9131e01d1c5c0b065205fb664db5411d08ff3d28230;
перечитан полностью: 10 отмечены / 0 открыты. Оба файла не менялись.

Происхождение перепроверено по настоящим output-блокам журнала
/Users/yshishenya/.codex/sessions/2026/11/01/rollout-2026-11-01T07-27-29-01a1955c-cb77-78e3-8844-ffeabcb2d594.jsonl.
Не просто найдены идентификаторы: текст каждого полного диапазона семи
оригиналов сопоставлен с текущим файлом. Все21диапазон совпал без усечения:
spec — строки журнала5985/5990/5995/6000/6005/6012/6017;
plan6022/6027/6032; tasks6037/6042; quickstart6049/6054/6059/6064;
data-model6069/6074; research6079/6084; contract5964.
Дополнительно сами исходные outputs status1–2385 (строка42), PRD1–1100
(75), PRD1101–1750/1751–2474 (142) точно совпали с текущими оригиналами.
Неусечённое собственное чтение подтверждено содержимым, не чужим заключением.

Все16неизменных входов из таблицы предыдущего отчёта и шесть исходных
зависимостей reconciliation/webhook/model/migration/database/CLI имеют прежние
SHA-256. Старый checksum monitoring.py в отчёте требований относится к состоянию
до реализации; текущий изменённый файл полностью прочитан и закреплён ниже.

После сжатия восстановлены применимые оригиналы по document-reading.md.
Карта текущего собственного чтения:

| Оригиналы и полные применимые разделы | Применимость и вывод чтения |
| --- | --- |
| README, document-reading, product-gates, spec-kit-flow, development-process, tracker-policy целиком | Область, происхождение чтения, независимость, права на один отчёт, неизменность задач и только Refs. Собственные outputs a19507/058e89/e58ab2/77a5b5/c126ff; усечённый совмещённый development-process перечитан целиком в77a5b5. |
| Constitution89–530, включая все семь принципов | Приватность, финансовая/данная границы, отсутствие влияния на capture/Stop/deletion/distribution/UI, обязательный процесс. Outputs058e89/e58ab2. |
| PRD1–150/349–374/688–844/1031–1101/1578–1777/2035–2072/2278–2326/2471–2474 | Общие обещания, диагностика без частного содержимого, сервер/изоляция, audit/privacy, полнота наблюдения, отдельные приёмки и приоритет заменяющего spec. Outputs163fc6/a860a5. |
| current-product-status179–217/451–470/529–622 | F272/F150/F140/F199: не возвращать stop/runtime gates, не выводить текущую оплату/полную приёмку из исторического статуса. Соответствующая часть c126ff прочитана до усечённой части другого документа. |
| release-and-validation171–244/410–443/646–692/758–770 | Профильные проверки, новые exact SHA/base gates, fragment, legacy и сохранение чужой работы. Output28a876. |
| contracts/operator-observation.md O1–O11 целиком | Ровно R1–R6 при всех прежних O1–O10/O6 ограничениях. Два неусечённых outputs0a88f7/d0e6a2. |
| operations-reconciliation, registry-operator-import, security-privacy-compliance, billing-lifecycle целиком | Снимок/роль, финансовая authority, сторонние возвраты, реальные сроки и отдельная сверка. Outputs5c0be4/d855bd. |
| F278 spec Functional Requirements158–203 и учёт приёмки295–302 | FR009/012/014/041: оплаченный срок и реакция≤24ч сохраняются. Полное повторное чтение57edd5/3ed09e/3551a8; усечённая общая попытка не используется как доказательство полноты. |
| F140 spec594–687, plan Technical Context refund, tasks T077 с пояснениями, quickstart refund, research refund и model refund/receipt | Одна исходная задача, семантика inventory, минимум реализации и предметная приёмка; outputs0496e0/3551a8. Неизменные полные оригиналы подтверждены выше. |

Прямые зависимости проверены: вся monitoring.py, CLI/database целиком,
модель refund, реальная миграция0044, writer/extractor и webhook caller;
полные новые тесты, используемые helpers/fixtures, три затронутых прежних PG
сценария и штатный isolated fixture с finally. Новых неразрешённых зависимостей
не обнаружено. Исторические ссылки не разрешают живые финансовые действия,
приложение, миграцию рабочей БД, выпуск или deployment.

## Точные проверенные входы

Сопоставлены текущие байты всех11входов с обновлённым внешним manifest
f140-t077-refund-implementation-validation-20261101.json. Результат11/11MATCH.
SHA-256 самого manifest:
746476b045c5b949c395d59813dbaf1d8b92a265d3ed6e5454fb0e5b786e8a4c.
Manifest и пять пар XML/log лежат во внешнем каталоге доказательств
/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/.

| Путь относительно репозитория | SHA-256 |
| --- | --- |
| specs/140-user-account-billing/spec.md | cadfdaf843487512a774f79eef89e2e3b3c2290904e44045fc9041e832f75818 |
| specs/140-user-account-billing/plan.md | f711fe18badb22d0f73553e22921222eabc49323b2710ee39c6d5b6d40b93fd1 |
| specs/140-user-account-billing/tasks.md | aa7b983a096370377d2b2d036acf5338b4bf49e106480080444e10c9f8466911 |
| specs/140-user-account-billing/quickstart.md | 704e31e671bbff92546bf34708012ce9363bc18f2a7f7193f8fcca66f194d6a7 |
| specs/140-user-account-billing/research.md | f13dc79b559299a4a8d3dc1b88c09a72ce651861e5e63bdbb6dab4bd88c55521 |
| specs/140-user-account-billing/data-model.md | 41c0c0341a5199cefd1027aff0586b0fe829a92b075191403490374313ae577d |
| specs/140-user-account-billing/contracts/operator-observation.md | 1e950b5f60a6b13cdf9eb25994a55118d6f4400b001b7c96651fb1d25f94540f |
| apps/server/src/twobrain_rec_server/billing/monitoring.py | 08d5a34627bf2ff9ff5a32f8803cccbf963f8a490f3ea292f3692e2893a578f1 |
| apps/server/tests/unit/test_billing_monitoring.py | 64e31879b0dd9c2a92574f02f46f6cef5602889fa1f552d59c4e955ca8b26c69 |
| apps/server/tests/integration/test_billing_monitoring_postgres.py | 526499792ebcd39bb9ec63437b127ea8d31431449817b2270e2027baf94d8294 |
| changes/unreleased/F140.yaml | 5ea80f3e5c6826cc9acc444f75e46e81dd14637c5d3333c5983cc653e0e17e94 |

## Независимое кодовое ревью

Полный diff продукта ограничен импортом существующей модели,
_refund_inventory232–244 и подключением семейства280/удалением его прежнего
not_connected. Других финансовых writers, CLI, DDL, RLS, прав или источников
не меняет. Две возможные группы ограничивают объём результата независимо от
количества строк; группировка и подсчёт выполняются в БД одним запросом.

SQL CASE распознаёт совместно succeeded/provider_observation. Если сравнение
даёт SQL NULL, WHEN не истинно и срабатывает ELSE unrecognized: отсутствующее
поле не становится известным исходом. Любая иная комбинация тоже скрыта за
одним закрытым значением. GROUP/ORDER используют именно этот CASE; count равен
сумме непустых групп, пропуска неизвестных строк нет. Частные исходные строки
не материализуются в Python. Запрос не имеет WHERE по дню, environment или
observed_at, не выбирает время, идентификаторы, сумму, валюту, JSON либо связи.

_source получает только две причины, отличные от observed, поэтому coverage
всегда partial. Успешная пустота остаётся count0/groups[] и двумя null;
приоритет unrecognized корректен. Исключения SQL не перехватываются новым
helper: прежний CLI безопасно отказывает всему отчёту. Реальный guard вызывается
до источников, READ ONLY RR/таймеры/ограничение вывода/rollback-close сохранены.

Новые тесты содержательны: реальная migrated PostgreSQL, служебная роль,
FORCE RLS, настоящий CLI/new process, SQL projection и fingerprint.
В schema-сценарии NULL INSERT проверяет настоящие NOT NULL через savepoint;
временное переименование столбца выполняется только в одноразовой БД и
восстанавливается finally. Ни модель, ни миграция ради теста не ослабляются.
Проверка защитного SQL CASE отделена от допустимых строк реальной схемы.

Итоговый pairs-сценарий содержит шесть частичных rows одного invoice:
каждая98765432, все шесть меньше invoice987654321. Три известные пары и три
неизвестные, включая succeeded/webhook, не смешивают transport с row.source.
NULL/прошлое/будущее observed_at и разные environments не меняют inventory.
Один SQL, перехват HTTP/writer/reversal в текущем процессе, отсутствие
частных столбцов, безопасный вывод новых процессов при трёх разных датах и
неизменный fingerprint дают независимые основания отсутствия записи/утечки.
Перехват в одном процессе не выдаётся за сетевую трассу новых процессов:
для них дополнительно проверены исходный путь без egress и stdout/stderr.

Сценарий двух соединений действительно закрепляет первый RR снимок полным
collector до writer commit. Повтор в той же session не видит новую строку;
новая session и новый CLI process видят её. Disposable privileged writer
создаёт синтетические данные; это не обход guard читателя и не live деньги.

Критических/высоких/средних/низких исправимых замечаний в данном diff:0.
Нового слоя, службы, схемы, alias или fallback не добавлено; Legacy Impact
untouched соответствует фактическому коду. Fragment описывает именно строки
и неполноту, не обещает возраст, чеки, финансовую сверку или закрытие #4932.

## Проверка фактических XML и журналов

Разобраны реальные XML всех пяти runs, сверены nodeids, tests/failures/errors/
skips/time/timestamp и SHA-256 XML/log; все10сумм совпали с manifest.
GREEN-журналы прочитаны; RED ImportError и PG assertion подтверждены реальными
failure-элементами/журналом, а не только именем run. Значения одноразового
подключения и сырые captured данные в этот отчёт не переносятся.

| Run | XML tests/failures/errors/skips | Время XML | Результат |
| --- | --- | --- | --- |
| refund-inventory-red-unit3 | 3/3/0/0 | 0.121с | До helper три ImportError из настоящего worktree path. |
| refund-inventory-red-pg1 | 1/1/0/0 | 5.281с | До подключения family source=None, unavailable/not_connected вместо требуемой формы. |
| refund-inventory-unit3 | 3/0/0/0 | 0.036с | Пустота, известные группы и приоритет unknown, SQL-форма/params/privacy. |
| refund-inventory-pg6 | 6/0/0/0 | 36.069с | Три новых PG плюс три затронутых прежних identity/SET ROLE/empty сценария. |
| refund-inventory-pairs-final1 | 1/0/0/0 | 6.966с | Повтор только изменённого pairs nodeid после уточнения суммы частичной строки. suite_name=pytest. |

Latest per nodeid пересчитан непосредственно из XML:9различных PASS,
0FAIL/ERROR/SKIP — 3новых unit +3новых PG +3затронутых прежних PG.
final1 заменяет прежний pairs-результат; это не десятый уникальный PASS.
Каждый GREEN-журнал содержит два прежних предупреждения pytest assert rewrite
и Starlette deprecation, SAWarning нет. Эти предупреждения не объявляются
исправленными данным изменением.

Штатный isolated fixture375–438 создаёт tmpfs PostgreSQL, мигрирует его и
в finally удаляет именно собственный контейнер, включая ошибку setup.
Успешный XML без teardown error согласуется с этим кодом. Дополнительное
чтение docker ps -a показало только старый bootstrap-контейнер3dd32699 от31.10,
новых bootstrap-контейнеров нет. Чужой старый контейнер сохранён.
Проверяющий не подключался к БД и не удалял контейнеры.

## Отдельная независимая scoped converge-сверка

Ниже — собственное сопоставление требований, плана и кода, а не принятие
самопроверки исполнителя. Область O11, не вся F140 или исходный FR089.

| Требование | Реальное покрытие | Итог локального среза |
| --- | --- | --- |
| R1 source/scope/kind и строки inventory | monitoring232–244/280, model/migration без shop_id; PG несколько rows/invoice, оба environment и три report dates | Реализовано. Не текущий магазин и не уникальные платежи/сумма. |
| R2 совместная пара/unknown/NULL/group/order | CASE235–239; три unit nodeids и PG пары с известным status/иным source, исходная NOT NULL | Реализовано. SQL NULL-ветвь безопасна; текущая схема не менялась. |
| R3 partial/null/приоритет/ноль/error | _source85–87, helper240–244; unit+empty/schema CLI | Реализовано. Error не превращается в ноль, оба измерителя null. |
| R4 observed_at/day/env не измеряют сроки | В helper этих столбцов/аргументов нет; PG NULL/future/past/env/day | Реализовано. Возраст/invalid_time_count отсутствуют; сроки O6 не приняты. |
| R5 один SQL/metadata/no-write/прежний снимок | helper/collector/неизменные CLI/database, SQL capture/fingerprint/HTTP-writer traps/роль и RR | Реализовано. Остальные семейства/полномочия не изменены. |
| R6 качество/RED/реальный PG/процесс/review/converge | Собственный reviewer checklist10/0, analyze, исходные tasks, пять XML/log, настоящий код и этот независимый отчёт | Локальная часть покрыта. Новые три exact-SHA/base PR gates остаются обязательным следующим этапом, их PASS здесь не заявлен. |

Семь решений плана сверены отдельно:

| Решение плана | Реализация/доказательство |
| --- | --- |
| Existing collector/model/family | Тот же monitoring.py и ObservedProviderRefund, без нового слоя/службы. |
| Одна SQL aggregation | Один await db.execute, DB GROUP/ORDER; instrumented PG len(sql)==1. |
| CASE совместной пары | Именно AND status/source и закрытый ELSE; unit params/PG неизвестные пары. |
| Не читать время | Отсутствие time/day/env projection/filter/age по коду и PG. |
| Закрытая приватная граница | Только status/source/count; нет writer/egress; SQL/fingerprint/stdout/stderr. |
| Безопасная несовместимая схема | Реальный новый PG schema failure + неизменный общий CLI отказ, без подстановки нулей. |
| Предметная проверка и последующая приёмка | RED/9uniquePASS/independent review; merge gates ещё впереди, release отдельно. |

Семь конституционных принципов сверены отдельно:

| Принцип | Проверка сохранения |
| --- | --- |
| I Capture-first | Capture/audio/package не затронуты; старый routing не возвращается. |
| II Visible consent/control | Record/Stop, локальная видимость/разрешения/автостарт не меняются. |
| III Data/observability boundary | Только metadata aggregation; нет содержимого встреч, секретов, новых внешних зависимостей или финансового egress. |
| IV Deletion truth | Нет новых content artifacts, кешей, retention/deletion либо ложного обещания очистки. |
| V Distribution/update integrity | Нет сборки/подписи/публикации macOS; правила не ослаблены. |
| VI Spec-driven delivery | Текущий scoped checklist/analyze/RED/validation/review доказан; новые exact PR gates остаются. Исторический пропуск чтения до PR7884 не исправляется этим отчётом, весь O8 не PASS. |
| VII Reference fidelity | UI/чужие активы/референс не изменены; независимый внутренний SQL-код без новых assets. |

Новых пропусков реализации, противоречий, непрошенных изменений или новых
задач в O11 не обнаружено. Локальная карта6требований/7решений/7принципов
не означает приёмку ещё не запущенных PR gates. Общий O6/FR089 остаётся
HIGH/partial внутри прежней T077, а не превращается в новую задачу.

## Сохранённый остаток и следующий этап

Самостоятельно сравнены все87полных task lines с HEAD: побайтно одинаковы,
T077 остаётся [ ]. Восемь исторических checklist тоже побайтно равны HEAD:
requirements17/8, operations10/8, security11/6, payments14/6,
launch-readiness32/8, post-plan-readiness25/15, product-market-2026 36/4,
ux17/3; всего162отмечены/58открыты. Их прежние открытые пункты не приняты.

Не завершены чеки/CSV/API/ledger reconciliation, другие источники, постоянные
job/attempt/error/retry counters, регулярность/heartbeat, тревоги/повтор,
сохраняемая реакция O6 с severity/owner/evidence/сроком/решением. Сохраняются
transient15мин/24ч, fair-use≤24ч, receipt canceled немедленно/pending3дня,
registry и F278FR041 реакция≤24ч; оплаченный срок после отзыва не отнимается.
F272/F199 stop/runtime gates не возвращаются.

Только Refs #4932. Live GitHub состояние и issue sync проверяющий не запрашивал;
закрытие #4932 не разрешается этим узким заключением. Перед commit/PR/merge
основной агент сверяет окончательные байты/назначение и получает свежие
обязательные governance-fast/macos-pr/pr-metadata для нового exact SHA и
проверенной основы через общий валидатор. Release/Full/CD/Dev, live provider,
финансовая/ручная/приватностная и полная продуктовая приёмки отдельно.
