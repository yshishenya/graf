# Независимое кодовое ревью T077/credit-ledger — 01.11.2026

Решение: **APPROVE только для локального кода O10/C1–C6**.
Блокирующих и иных содержательных замечаний нет: CRITICAL0/HIGH0/MEDIUM0.
Это независимое кодовое ревью, не завершение T077/O6 и не разрешение выпуска.
Исполнитель `/root/f140_notification_content_review`, тот же диалог
`01a1955c-cb77-78e3-8844-ffeabcb2d594`. Область — O10/C1–C6 F140/T077/#4932,
владелец repository-audit, high-risk-product / active Spec Kit slice.
Ветка `codex/140-observation-credit-ledger`, HEAD
`458e874ddb40b3eb56dbc6535d84ef2e6bd2f8df` плюс проверенные локальные изменения.
Разрешена запись только этого отчёта. Код, тесты, требования, checklist,
fragment, указатель, Git/GitHub, приложение, выпуск и данные не меняются.

## Собственное чтение и неизменность контекста

Собственное полное чтение семи требований и неизменного корпуса выполнено
ранее в этом же диалоге и проверяемо по
`review-credit-ledger-requirements-20261101.md`, SHA-256
`5f8c012a3bc5f2d22122755eace82043a4e53887bc305d9ed2ab65962186ec21`.
Документ содержит исходные строки собственного журнала, карту применимости,
первое полное чтение и зависимости. Это происхождение собственного чтения,
не замена чтением другого агента и не перенос старого O9/O10 PASS на код.

В новом назначении повторно сверены все 11 frozen inputs, 12 ранее прочитанных
основных документов/инструкций/контрактов, billing-lifecycle, собственный
отчёт требований и credit-ledger checklist: содержимое неизменно.
Применимые оригинальные требования и ограничения доступны в контексте
собственных чтений непосредственно предыдущего назначения. Дополнительно
перечитан целиком O10 (contracts/operator-observation.md240–299).

Новые собственные чтения текущего назначения:

| Оригинал | SHA-256 / область | Проверяемый собственный вывод |
| --- | --- | --- |
| apps/server/src/twobrain_rec_server/billing/monitoring.py | `c8080e43f07580e423925f2360814ddc8214909a5641d04fd8bfdf46b2b19f6f` | Отдельный полный `nl -ba`, 1–272, без усечения. |
| apps/server/tests/unit/test_billing_monitoring.py | `2095d4925a11dd36fb8c5268dc0375bfe0908a3dd7eb2fc8e81e26bf17cfe3f1` | Отдельный полный `nl -ba`, 1–141, без усечения. |
| apps/server/tests/integration/test_billing_monitoring_postgres.py | `ac6f07f3e55f85171c7f806eb6b8d8d97cc0dc708e6c4a958dfc1df0fe2744fa` | Полный diff и исходные helper/fixture/affected tests1–250; новые тесты699–880 прочитаны полностью в diff. |
| changes/unreleased/F140.yaml | `6203eedea86e6e34f7ee97a607126a526dd93ff9c11b9aa1ec33d2c9337110dc` | Полный diff9 строк; существующие ограничения сохраняются. |
| cli/billing_monitoring.py; billing/database.py | Неизменные зависимости | Собственные полные cat: общий as_of/guard/RR/read-only/таймауты/cleanup/безопасный отказ. |
| tests/integration/test_billing_registry.py34–59 | Неизменная зависимость fixture | Полный применимый раздел: реальные роли NOSUPERUSER/NOBYPASSRLS и SET ROLE-сценарий. |

Выводы находятся в собственном журнале
`rollout-2026-11-01T07-27-29-01a1955c-cb77-78e3-8844-ffeabcb2d594.jsonl`;
точные команды и текущие байты проверены, сводка другого агента не считается
собственным чтением. Навык code-reviewer прочитан; повторный preflight
исключён явным назначением: pytest/PostgreSQL/Docker не запускались.


Дополнительная зависимость после просмотра fixture: собственное чтение
`tests/fixtures/postgres_test_database.py`295–434/425–437 целиком покрывает
prepare_schema и postgres_isolated_cluster_database_url. Настоящий
`alembic upgrade head`, loopback PostgreSQL17-alpine, отдельные фиксированные
роли и finally removal подтверждаются кодом; это не create_all/SQLite.
Исходники fixture и registry_database побайтно равны HEAD.

## Зафиксированные входы реализации

Повторно вычислены SHA-256 всех 11 файлов; каждый совпал с внешним
`f140-t077-credit-ledger-implementation-validation-20261101.json`.
Первые семь также совпали с собственным допуском требований10/0.

| Путь | SHA-256 |
| --- | --- |
| specs/140-user-account-billing/spec.md | `2cf1269dce138f8aeea8ba3dfd5372df3fdf82f2682bcb335393ae7f143284dd` |
| specs/140-user-account-billing/plan.md | `fbe8556b2f80853c10cb86261de035342743bbb8298bf45674af187dccd36469` |
| specs/140-user-account-billing/tasks.md | `659e788fc6dd71d95330d81358a13cd3f07d09af27ee06df576b2bc9040d2535` |
| specs/140-user-account-billing/quickstart.md | `2ee2f913f9640af1a8729d513d93b08f741c0029a42ebf82d5a4fdac8c8d2ee9` |
| specs/140-user-account-billing/research.md | `367ea8f385b7cbb64cc05e99433c832b4e5e8ea2bc96d53a277ac1a1a64d0f51` |
| specs/140-user-account-billing/data-model.md | `386df316da75fdb96c2fa841c213b567cd5fa05bbc0112ae20d1fb1fb28e9e68` |
| specs/140-user-account-billing/contracts/operator-observation.md | `166ad09e28b8fc4ee822f2d3e59b40925cfee1f685e7f86f30bd9b5025cc471b` |
| apps/server/src/twobrain_rec_server/billing/monitoring.py | `c8080e43f07580e423925f2360814ddc8214909a5641d04fd8bfdf46b2b19f6f` |
| apps/server/tests/unit/test_billing_monitoring.py | `2095d4925a11dd36fb8c5268dc0375bfe0908a3dd7eb2fc8e81e26bf17cfe3f1` |
| apps/server/tests/integration/test_billing_monitoring_postgres.py | `ac6f07f3e55f85171c7f806eb6b8d8d97cc0dc708e6c4a958dfc1df0fe2744fa` |
| changes/unreleased/F140.yaml | `6203eedea86e6e34f7ee97a607126a526dd93ff9c11b9aa1ec33d2c9337110dc` |

Источник контрольных сумм: внешний metadata JSON, SHA-256 `3d75fb06dc3ecdec5e85de5eb7bcfac8322402b7817b12f670d8a28cc6dc3dd7`.
Это привязка к локальным байтам на указанном HEAD, а не к будущему коммиту.
Любое изменение одного из входов требует повторной оценки затронутой части.

## Предметные решения

| Требование | Проверка кода и доказательств | Решение |
| --- | --- | --- |
| C1: inventory/current_state, count строк, jobs null/partial | monitoring199–228 не принимает report_date/shop и читает все доступные строки. _source79–82 задаёт database_inventory/current_state; reason221–222 никогда не observed, поэтому всегда partial. count=sum SQL count; четыре поля227 явно None. PG702/802/840 и процесс с двумя разными датами это проверяют. | PASS |
| C2: ровно шесть состояний и одна неизвестная группа | CREDIT_STATES34 и CASE _closed42–43. Иное/NULL идёт в один литерал unrecognized; group_by/order_by state212–216 даёт только непустые упорядоченные группы, не более7. groups225 и count224 используют те же строки. matured/private-state не выводятся; PG769–772 ожидает одну unknown группу2. days вообще не выбирается: отрицательная reversal731 считается строкой, не долгом. | PASS |
| C3: четыре категории и invalid первым | pending203 ограничивает расчёт pending/available. invalid204 явно покрывает NULL/expiry≤maturity; каждый из трёх остальных filters исключает invalid. На валидных датах expiry≤as_of и expiry>as_of разделяют истёкшие и остальные; для оставшихся maturity≤as_of и maturity>as_of завершают разбиение, так как expiry>maturity. SQL FILTER не считает NULL predicate. Терминальные/unknown исключены из всех четырёх filters. PG708–718/773–778 проверяет maturity±1µs/expiry±1µs/equality/invalid/терминальные и сумму9=2+2+3+2. | PASS |
| C3: точный max/floor, null и будущая maturity | MIN maturity FILTER reached215 и min между группами217 дают самый старый только допустимый достигнутый момент. Выражение220 использует timedelta//timedelta, целое без float/total_seconds и потери микросекунд; reached гарантирует неотрицательность. default=None даёт null при отсутствии. Unit119–141 проверяет максимум120 вместо суммы180 и крайний datetime диапазон315537897599; PG717/873–874 проверяет1µs и ровно0. Будущее остаётся waiting, не invalid_time. | PASS |
| C4: причины, ноль, отказ целого отчёта | Приоритет221–222 строго unrecognized→invalid_schedule→jobs_uninstrumented. Пустой SELECT даёт count0/groups[]/четыре0/ageNone, jobsNone и partial. Unit88–138 и PG793–799 проверяют все причины. PG802–837 отвергает INSERT NULL для state/двух дат, затем rename maturity вызывает только безопасный report_unavailable/exit1; после восстановления count0. Неуспех не подменяется нулями, так как исключение не перехватывается внутри collector. | PASS |
| C5: приватность, только чтение и минимум | SQL212–216 выбирает лишь CASE(state), COUNT/FILTER и MIN maturity; запрещённых колонок, ORM loading, joins и вызовов финансовых функций нет. Один запрос, максимум7 агрегированных строк. Unit104–109 и PG739–785 проверяют один SQL и отсутствие days/refs/IDs/capacity/applied fields; PG785–792 проверяет отсутствие синтетических частных значений в JSON, пустой stderr нового процесса и полные fingerprints до/после. HTTP запрещён sentinel. | PASS |
| C5: guard/RR/as_of/таймауты/cleanup и остальные источники | Новый вызов263 использует тот же db/as_of после guard233; новых transaction/connection/commit/clock нет. CLI, database guard, модели, миграции, права и writers не менялись. AST-сверка существующих функций monitoring показала изменение только collect_billing_report и добавление _credit_ledger: generic _groups/_registry/_free_projection и другие helpers эквивалентны по AST без учёта координат. Новый источник удалён лишь из списка not_connected. Прежние15s/5s/2s/64KiB/500gaps и cleanup сохранены. | PASS |
| C6: настоящие PostgreSQL/CLI/forced RLS/RR | TABLES44–47 добавляет ledger, database fixture50–65 проверяет ENABLE/FORCE RLS для всех восьми таблиц, не отключая защиту. Поэтому повторены3 затронутых теста139/174/207: CLI/new process/no-write, реальные app/worker/superuser deny, RR/read-only/5s/2s до первого hook, SET ROLE/wrong context/mutation denied. PG840–880 держит старый RR до отдельного writer commit, повторный отчёт неизменен, новый session/процесс видит1 строку. | PASS |

Буквальная NULL-ветвь является защитной: реальная схема NOT NULL не ослабляется.
Положительный NULL dataset на PostgreSQL не заявляется; проверены SQL-форма и
отказ INSERT на настоящей схеме. Невозможные positive NULL cases не добавлялись.

Финансовая семантика сохранена: наступившая дата не объявляется eligibility,
успехом/сбоем задания или SLA. Hold/Free/rolling cap не измеряются этим
источником. Ни mature_pending_credits, reverse_credit_for_payment, repair,
expiry/provider/mail/analytics не вызываются; новых внешних соединений нет.
Новая служба, таблица, индекс, schema/CLI parameter или универсальная абстракция
не введены; одна локальная функция достаточна для заявленного источника.

## Проверенные результаты исполнения

Повторно тесты не запускал. Самостоятельно прочитаны сохранённые XML/журналы
в каталоге внешнего metadata JSON. Для каждого из четырёх запусков вычислены
SHA-256 XML и log, сверены с metadata; testcase classname/name и фактические
failure/error/skipped пересчитаны из XML. Это проверка артефактов завершённых
запусков владельца, а не собственный новый запуск или GitHub evidence.

| Запуск | Итог по XML | Содержательная причина/область |
| --- | --- | --- |
| credit-ledger-red-unit4 | 4FAIL,0ERROR,0SKIP | Четыре ImportError отсутствующего _credit_ledger в текущем пути исходника до реализации. |
| credit-ledger-red-pg1 | 1FAIL,0ERROR,0SKIP | Реальный CLI успешен, но family source=None вместо объявленного источника до реализации. Проверены ошибка и XML, весь длинный migration log полным чтением не заявляется. |
| credit-ledger-unit4 | 4PASS,0FAIL/ERROR/SKIP | Новые4: пустота/SQL projection и3 reason cases/max/exact extreme floor. |
| credit-ledger-pg6 | 6PASS,0FAIL/ERROR/SKIP | Новые3 PG и3 затронутых прежних, 32.39s pytest; runner focused status=pass, cleanup=isolated_container_removed. |

Последние успешные node IDs проверены на уникальность: **10 различных PASS**
(7 новых/3 затронутых прежних), не15 за счёт сложения RED/GREEN. Старые
O9/общие наборы в этот итог не включены. В обоих GREEN журналах по2 прежних
предупреждения: assert-rewrite импортированного fixture и Starlette/httpx
Deprecation; SAWarning нет. Выводы не содержат разрешения на повторный Full.
Синтетические реквизиты временной БД из RED-журнала в отчёт не переносятся.

Сохранённый before-code-gates JSON прочитан отдельно: scope6C/1T077/100% и
0 findings; существующая issue4932 OPEN, canon ensure/validate243 PASS без
новых issues. Собственный checklist/отчёт требований остались10/0 и с теми же
суммами. Повторное live GitHub подтверждение в это назначение не входит.

## Границы заключения и оставшаяся работа

APPROVE относится только к проверенному локальному O10. Формальная converge,
проектные проверки/metadata, будущий новый SHA и три GitHub проверки
(governance-fast/macos-pr/pr-metadata) с текущей основой остаются отдельными
воротами основного исполнителя. До явного завершения окна v2026.11.01.3
оператором master не меняется. Этот отчёт не разрешает merge/release/deploy.

87 полных исходных task lines повторно побайтно равны HEAD. Восемь старых
checklist также равны HEAD:162отмечены/58открыты; новый requirements checklist
10/0 не изменён этим кодовым ревью. T077[ ], #4932 и полный FR089/O6HIGHpartial
остаются открытыми: другие семейства/add-on/job attempts/errors/retries,
регулярность/heartbeat, тревоги/повтор и сохраняемая реакция/приёмка не завершены.
Сроки transient15мин/24ч, fair-use≤24ч, receipt canceled немедленно/pending3дня,
registry/F278FR041 реакция≤24ч сохраняются. Исторический пропуск чтения до
PR7884 не исправлен задним числом; whole O8 не PASS. Отменённые F272/F199
stop/runtime gates не возвращаются; оплаченный срок F278FR041 не сокращается.
Частичная связь — только Refs #4932, без closing keywords и без нового issue.

Собственные действия: чтение оригиналов и diff, сверка SHA-256/HEAD/ветки,
пересчёт XML/уникальных node IDs, AST-сравнение существующих функций, сравнение
неизменных зависимостей/87 task lines/8 checklist с HEAD, git diff --check.
Не выполнялись pytest/продуктовый CLI/PostgreSQL/Docker, сборка/приложение,
финансовые операции, Git/GitHub mutation, коммит, PR, слияние или выпуск.

Финальное собственное перечитывание отчёта выполнено по диапазонам1–95/96–конец.
Все11 frozen inputs повторно совпали перед передачей результата. Проверка
пробелов нового отчёта через git diff --no-index --check /dev/null прошла
(код1 при пустом выводе означает только наличие нового файла). Результат
кодового ревью окончательный: APPROVE в указанной области, findings0.


## Независимая сверка scoped converge — 01.11.2026

Результат: **PASS только для согласованности реализации O10**, новых findings0.
Собственное чтение внешнего `f140-t077-credit-ledger-converge-20261101.json`,
SHA-256 `5229f582b65c1f4ee1c5f5b5872deac08248647293462330ff906824a41e5ee0`, сопоставлено с фактическим кодом/тестовыми
артефактами, прочитанными и разобранными выше. Перед этой сверкой повторно
вычислены11 frozen hashes: все совпали; отчёт требований также неизменен.
Полное чтение семи неизменных подтверждённых оригиналов не повторялось.
Точечно перечитаны целые применимые plan83–109, contract O10 и constitution
VII367–404, разрешив зависимость седьмого принципа, а не приняв счётчики JSON
за самостоятельное доказательство.

- **6 реализуемых требований C1–C6:** карта предметных решений этого отчёта
  подтверждает источник/current_state, шесть state/unknown, разбиение и точный
  возраст, причины/ноль/отказ, privacy/read-only и заявленные проверки. C6
  понимается как реализуемая часть с явными последующими воротами; три
  exact-SHA/base PR проверки и весь O8 завершёнными не объявляются.
- **7 решений плана:** одна агрегация существующей таблицы; закрытая state
  группировка; четыре фильтра и MIN допустимой maturity; отказ от ORM/day
  сумм/финансовых helpers; partial/null jobs; сохранённые guard/RLS/RR/
  ограничения без новой схемы/службы; прежняя T077 и установленный порядок
  review/converge/PR gates. Каждое решение соответствует рассмотренным
  строкам monitoring199–228/263 и профильным сценариям; новых недоделок
  внутри этого ограниченного изменения не найдено.
- **7 принципов конституции:** I/II — capture, видимость и Stop не затронуты;
  III — нет meeting content/секретов/нового egress; IV — нет удаления или
  изменения lifecycle; V — нет приложения/публикации пакета; VI — существующий
  high-risk Spec Kit, независимые требования/кодовое ревью и сохранённые
  следующие ворота; VII — UI/референс/активы не меняются и чужой код/материалы
  не вводятся. Это проверка сохранности принципов в данном diff, не общая
  приёмка финансового продукта, capture, UX или дистрибуции.

retained finding FR089/O6HIGHpartial правильно остаётся в исходной T077:
источники, постоянные attempts/errors/retries, регулярность/heartbeat,
тревоги/повтор и сохраняемая реакция не завершены. В JSON `new_tasks=0`
согласуется с отсутствием новой работы вне уже учтённого остатка; дублирующую
задачу добавлять не требуется. T077[ ], #4932,87 исходных строк,58 старых gaps,
исходные сроки и release freeze сохраняются. `whole_feature_outcome=not
converged` верен. Строка JSON об ожидаемом independent review отражает время
его составления; выполненное собственное APPROVE записано выше, остальные
процессные/PR/выпускные ворота она не отменяет.

Сверка не запускала код/тесты/БД/CLI/Git/GitHub и не меняла исходный converge
JSON, task/checklist или общий статус цели. Дополнен только этот отчёт.
