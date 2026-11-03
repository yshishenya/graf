# Независимая проверка кода и отдельная сверка O15 — 02.11.2026

Исполнитель `/root/f140_notification_content_review`, диалог
`01a1955c-cb77-78e3-8844-ffeabcb2d594`, рабочая копия
`f140-referral-reversal/crisp`, ветка `codex/140-observation-storage`,
HEAD/base `4c7924ea69ac6c0968d563988b884a0ecc75ba21`.
Полоса high-risk-product, существующая T077/#4932, только O15/S1–S6.
Разрешена запись только этого отчёта и reviewer-owned storage checklist.
Тесты/БД/контейнеры/приложение/CI/GitHub/commits не запускаются и не меняются.

## Происхождение контекста и собственное чтение

Требования gate10/0 уже отдельно принят; собственный отчёт
`review-storage-projection-requirements-20261102.md`, SHA-256
`ec01386321cdee1e89dfccd843626c4352e133f89e8f7b9ec00cd8c66377a256`.
Его происхождение — тот же исполнитель и диалог; полное чтение/восстановление
оригиналов и реальные локаторы зафиксированы там. Контекст после этого
назначения не сжимался. Семь окончательных документов и четыре новых
файла реализации совпали с manifest11/11 (собственный вывод4ffbc6).
Нормативные16/16 SHA повторно совпали826e97. Применимость прежняя:
storage/финансы/retention/privacy/RLS/READ ONLY RR/общие пределы/отдельная
приёмка и точный SHA/base PR; принцип/захват/AI/публичный запуск не меняются.
Процедура document-reading прочитана целиком135633. Skills code-reviewer
и speckit-converge целиком7c8546/c56e14; extensions.yml целикомf96d17,
before_converge/after_converge hooks отсутствуют. Итоговые решения ниже.

- monitoring.py: собственный полный оригинал1–457 прочитан без усечения
  f0491d(1–120),896884(121–240),68dc11(241–340),bffd7f(341–457),
  SHA-256 `a2d3423e537329b622234d5d127306eb36b473b31c475bc82d4d8f9760edfdfa`.
  Область: весь collector, существующие families/source/closed semantics,
  guard-first и новое storage; это статическая проверка, не запуск.
- Новый PG diff целиком9b8c75; это навигация, не замена чтения оригиналов.
  Смешанный выводa1b69b усечён, в доказательство полного чтения не входит.
- unit/test_billing_monitoring.py: полный оригинал1–385 собственными
  неусечёнными05c03b(1–150),7e1595(151–285),92c525(286–385), SHA-256
  `e4ba5081df4d681d551d4d1a908232d648c51d1c3a7fa7d07b15a521fd1d4e8c`.
  Область: старые границы и все три новых сценария, явные аргументы,
  целочисленная точность, причины неизвестности и предел до helpers.

- integration/test_billing_monitoring_postgres.py: самостоятельно прочитаны
  полные новые сценарии и их непосредственные зависимости:1–170(580a4c),
  171–315(d078e7),1654–1755(725ed8),1756–1855(dc99a5),
  1856–1955(21dc7b),1956–2047(d0b7f7); deletion_meeting1479–1495
  восстановлен e21a58. SHA-256 всего файла
  `1c750a0f1756d4dd3b74691ed13462d239644637099e2518e4eb9a6a6f86d4ce`.
  Неизменённые старые сценарии316–1478/1496–1653 не объявляются заново
  прочитанными или повторно исполненными этим назначением.
- CLI целиком e0d9fd; identity guard целиком ef21fd. Их SHA и прежние
  helpers/storage/models/миграция совпадают с собственным requirements review.
  Оригинал storage1–145 b06a4c и180–215 0e391b, полный
  effective_paid_storage310–410 a8795c восстановлены для сопоставления.
  Это прежние SELECT helpers; writers не вызываются новым collector.
- Непосредственная цепочка настоящей изолированной БД: registry fixture
  и roles1–58 прочитаны593506; isolated runner375–438 b6784a,
  prepare_schema296–318 7651b6. Создаётся PostgreSQL17-alpine на loopback,
  Alembic upgrade head; finally удаляет только собственный случайный container
  с volumes, ошибка удаления не скрывается. Fixture проверяет FORCE RLS
  каждого source table и не ослабляет production схему/политику.
- F140.yaml целиком fc5eb9, SHA-256
  `fa27b553fa37dbfa020acdfbf54e17940b2fff7f624e0e4bebc7115b711b886f`.
  Ограничения проекции/неполноты и открытая #4932 сохранены.

## Независимая проверка фактических доказательств

Каталог внешних материалов:
`/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure`.
Manifest `f140-t077-storage-implementation-validation-20261102.json` прочитан
целиком1c4ec2; текущие11 входов совпали4ffbc6. Проверены сами XML и журналы,
не только таблица manifest: все12 SHA-256 (6 XML +6 log) совпали,
реальные nodeids/status совпали с cases каждого прогона (1b2eb2).
Усечённый смешанный d1b8f6 не используется как полная запись проверки.

| Прогон | Фактический результат XML и журнала | Exit |
| --- | --- | --- |
| storage-unit-red | 3 FAIL,0ERROR,0SKIP: отсутствуют новый collector/import helper | 1 |
| storage-pg-red | 1 FAIL,0ERROR,0SKIP: source остаётся None вместо storage inventory | 1 |
| storage-unit-final | 3 PASS,0FAIL/ERROR/SKIP | 0 |
| storage-pg-initial | 6 PASS/3 FAIL,0ERROR/SKIP: конфликт synthetic personal owner | 1 |
| storage-pg-correction1 | 1 PASS/2 FAIL,0ERROR/SKIP: catalog trigger и synthetic NULL date type | 1 |
| storage-pg-correction2 | 2 PASS,0FAIL/ERROR/SKIP | 0 |

Независимая свёртка по каждому nodeid, заменяя только его неуспешный исход:
**12 различных итоговых PASS =3 новых unit +6 новых PG +3 затронутых PG**;
итоговых FAIL/ERROR/SKIP=0. Не заявляется один сплошной зелёный PG запуск:
два промежуточных ненулевых exit сохранены; успешные проверки не повторялись.
Прежние наборы O1–O14 к12 не прибавляются.

Причинный исход до кода подтверждён XML/логами; для Unit RED/PG RED/Unit FINAL
проверены непосредственно реальные tool outputs основного диалога
01a140f0-8073-7de0-bc68-03d1ac57ff06, а не только файл-указатель.
Собственная проверка4f0482 нашла точные объекты runner result:

- строка202276/call_59bd514a837f403c92a991410c60e075/chunk1c5f41/exit1;
- строка202292/call_887c0847f7d0427f8140281a7d23a4e1/chunk337a3f/exit1:
  это завершение session25076, не первый ответ running;
- строка202308/call_2a8dc7cbc35043e9a88c58c1d8776ac4/chunk12701a/exit0.
Соседние exit0 относятся к чтению журнала и не подменяют exit pytest.
PG run JSON initial/correction1/correction2 отдельно содержат команды,
точные nodeids и exit1/1/0; их SHA:
`d0343d56828db06af17ccc8f2db14284c667f99eddacc5e1e86b952e9920f60d`,
`8d71a6a689efbcc24a02f20826daf99e32e43492b5554a88129f7dd0d39b612a`,
`3dd1df6767cb9f661f9a1af39ed2680dbd773a86d32e8aaf19cf111014d90daa`.

Fixture исправлена без ослабления схемы: дополнительные пространства
corporate не нарушают уникального personal owner;40ГБ/month/version2 и
реальная catalog price_amount согласованы с trigger; все-NULL synthetic
VALUES даты явно timestamptz. Исходные соответствующие SQL ошибки прочитаны
в XML, эти три причины не выдаются за ошибки нового расчёта или обходы RLS.

No-write проверяется реальными fingerprint до/после по18 таблицам,
включая WorkspaceSubscription с PKworkspace_id, storage reservations,
grants, TrackArtifact/UploadSession; assertions достигнуты в итоговых PASS.
Настоящий READONLY mutation probe и app/worker/superuser/SETROLE/неверный
контекст проверены отдельно. Повтор CLI требует пустой stderr; запрет
private markers/денежного sentinel проверяется в stdout; исключения
возвращают только закрытый result_code, без SQL/URL/traceback.

Cleanup подтверждён сохранёнными полными наборами: initial baseline и after
побайтно равны,79 контейнеров, SHA-256 обоих
`eb0121525c2b9d8180edbad6d5c5b3f71d896a40914bf7a15a3399a505e47f56`.
В correction1 и correction2 независимо сравнены все79 исходных и конечных
строк: множества равны, added0/removed0 (1b2eb2). Чужой существовавший bootstrap
сохранён. Это проверка сохранённых фактов запусков; собственный Docker/БД
сейчас не запускались.

## Code review — APPROVE

Проверены текущие оригиналы, не только diff или зелёные результаты.
Новых actionable findings CRITICAL/HIGH/MEDIUM/LOW не выявлено.

| Область | Вывод и проверяемое основание |
| --- | --- |
| Область и полный предел | monitoring341–377: aggregation всех видимых reservations, outer join всех workspace без day/shop/environment, limit501 и whole ReportLimitError до helpers. Нет sampling/maintenance batch. |
| Existing source semantics | monitoring389–397 и три оригинальных helper: общий as_of, явные workspace/capacity/reserved; canonical profile/suffix/finalized-nonarchive исключение; active reservation expiry строго >as_of или NULL; финансовый helper не изменён. |
| Unknown/capacity | monitoring380–391: missing отдельно от NULL/unknown plan; только relevant trial/personal nonfinite dates делают capacity unavailable; NULL сохраняет Free fallback, Free не использует даты; неположительная helper capacity не подставляется. |
| Counts и totals | monitoring345–359/400–410: invalid counted once, nullable bytes целиком при invalid/unknown/unavailable, counts независимы; expiry==as_of истёк, nonfinite проверен SQL, группы закрыты и отсортированы. Точные integer суммы без float. |
| JSON и приватность | monitoring368–374/405–411: узкие поля вместо целого ORM; финансовый snapshot только внутри прежнего helper; его два falsy fallback не изменены. Ни refs/keys/IDs, ни snapshot/контакты/деньги в результат не попадают. |
| Полнота и безопасный отказ | _source всегда partial при четырёх закрытых reason, reconciliation_gaps=null; CLI общий report_unavailable/exit1 при schema/helper failure. Не утверждается объектная или финансовая сверка. |
| Identity/транзакция/пределы | collect guard первым; прежний CLI задаёт READONLY RR/5с/2с до hooks, один15с включает helper и cleanup,64KiB и500gaps прежние. Новая ветка не добавляет бюджет или привилегии. |
| Реальные приёмочные случаи | 3unit/6newPG/3affectedPG покрывают args/точность, branches capacity, reserves/NULL/infinities, falsy/truthy failures, canonical exclusion, RR поздний commit/newprocess,500–501 и cancellation нового helper. |
| Простота и сохранность | Один collector74 строки плюс существующие imports/константа; нет новых abstractions/services/schema/dependencies/writers. Изменение fixture локально тестам; финансовые helpers и product права не переписаны. |
| Границы завершения | Fragment/contract/task требуют Refs4932, T077/T070/O6/58gaps открыты; approval относится только к этой реализации O15, не ко всему issue и не к выпуску. |

Итого code review: **10 областей проверены,10 подтверждены,0 новых замечаний**.
Storage requirements checklist остаётся отдельным прежним gate10/0;
проверка кода не переписывает историю O8 до PR7884 и не исправляет её задним числом.


## Отдельная scoped converge — текущий код против намерения

Выполнена после самостоятельного code-review решения выше по действующему
`.agents/skills/speckit-converge/SKILL.md`. Область намерения — O15/S1–S6,
семь решений plan §T077 storage и семь принципов конституции; это не новая
полная приёмка всей F140. Требования/spec/plan/tasks взяты из собственных
полных оригиналов с совпавшими SHA, текущая реализация оценена по коду,
а не по diff или истории. Git сравнение не используется как основание converge.

Инициализация адаптирована к запрету иных записей: буквальная команда skill
с `--require-spec` не поддерживается текущим check-prerequisites.sh; кроме
того, обычный режим get_feature_paths может записать feature.json.
Скрипт целиком прочитан abeaaa; выполнен только чистый
`check-prerequisites.sh --json --paths-only` (80f106), получен ожидаемый
FEATURE_DIR140. Наличие spec/plan/tasks проверено непосредственно e74441.
Таким образом, проверка обязательных файлов сделана без запуска неподдержанного
флага и без изменения feature state. Конфигурация extensions.yml прочитана,
YAML отдельно успешно разобран safe_load (6fb64f); hooks — map,
before/after_converge списки отсутствуют.
Новых задач не создаётся: новых непокрытых работ текущего среза нет, а полный
известный остаток уже принадлежит исходной открытой T077.

| Требование | Оценка текущей реализации |
| --- | --- |
| S1: область/источники/предел | Выполнено: все видимые workspace outer join и reservations, шесть источников,501 whole failure до helper, database_inventory/current_state без report day/shop фильтров. Unit boundary и реальный CLI500–501 PASS. |
| S2: существующие byte projections | Выполнено: три неизменных helper с общим as_of и явными аргументами. Проверены фактические capacity ветви и exact used888/reserved90→989/140 после нового снимка; финансовая семантика не меняется. |
| S3: неизвестность/итоги | Выполнено: missing/NULL/unknown/nonfinite/nonpositive разделены, нет default capacity/известного subtotal, все три суммыnull; empty0. Unit/PG independent expected cases PASS. |
| S4: резервы | Выполнено: закрытые группы/count/invalid/expired независимо, NULLexpiry действует, равенство истекло, infinities SQL; defensive NULL отдельно от настоящих NOTNULL, counts не заменяют bytes. |
| S5: приватность/безопасный отказ | Выполнено: узкая подписка, неизменные falsy snapshot fallback и общий whole CLI failure при неподдерживаемой форме/helper/schema. No-write/private sentinel/empty stderr assertions PASS; новые внешние вызовы отсутствуют. |
| S6: partial/приёмка/границы | Выполнено в локальном срезе: точный приоритет reason и null reconciliation,12 разных профильных PASS, настоящий guard/RLS/RR/новый процесс/предел/cancellation. PR проверки и приёмка выпуска отдельно; источник не объявляет весь O6 или financial/object сверку выполненными. |

| Решение плана | Оценка текущего кода |
| --- | --- |
| P1 один collector в прежнем monitoring | Выполнено; один _storage_inventory, общие _source/_closed/ReportLimitError, нет новой abstraction/schema/dependency. |
| P2 SQL aggregation + narrow outer join501 | Выполнено; counts агрегируются SQL, даты представлены finite values/flags, не полный ORM. |
| P3 existing helpers/row/один as_of | Выполнено; SQL row даёт нужные атрибуты; maintenance writers/locks/repair не вызываются новым collector. |
| P4 exact null/reasons/falsy JSON/failure | Выполнено; source/поля/nullable totals соответствуют data-model/контракту, отдельного JSON-валидатора нет. |
| P5 maintenance/FORCE RLS/READONLY RR/privacy | Выполнено; guard первым, прежний wrapper/единые пределы/cleanup сохраняются; реальные отрицательные проверки PASS. |
| P6 штатный PG runner/реальная схема/локальная fixture | Выполнено; PG17 Alembic head, forced RLS/NOTNULL, synthetic NULL без изменения таблиц; свой cluster finally удалён, чужие сохранены. |
| P7 узкая последовательность/проверки/сохранение tracker | Локальный код/причинные RED/независимый review и эта converge выполнены.87 строк/T077[ ]/58gaps/O6 сохранены. Exact PR SHA/base проверки остаются следующим отдельным допуском, локальная сверка их не заменяет. |

| Принцип конституции | Применимость и вывод |
| --- | --- |
| I Capture-First MVP Integrity | Проверен: изменения вне pipeline записи; удалённые механизмы/новые способы захвата не возвращены. Новых обязанностей реализации capture этот срез не создаёт. |
| II Visible Consent And User Control | Проверен: отчёт внутренний, нет новой передачи содержимого/тайного действия/изменения пользовательского управления; финансы и права только читаются. |
| III Plaintext Observability For Internal MVP | Применим, соблюдён: существующий защищённый внутренний путь, metadata-only закрытые counts/байты; refs/секреты/raw content/новый egress отсутствуют. |
| IV Deletion Truth And Lifecycle Accounting | Применим, соблюдён: stored bytes не доказательство физического purge/retention; нет writers, договорные ограничения/внешние данные не объявляются удалёнными. |
| V Public macOS Distribution And Update Integrity | Проверен как неприменимый к новой реализации: сборка/подпись/Sparkle/выпуск не изменяются; локальный review не выдаётся за эти проверки. |
| VI Spec-Driven Delivery With Testable Gates | Применим: текущий срез имеет собственный requirements gate10/0, причинные RED, реальные профильные PASS и независимые review/converge. Последующие PR gates обязательны; исторический O8 пропуск до PR7884 не принимается и не исправляется этой записью. |
| VII Reference-Fidelity Product Design | Проверен как неприменимый к новому выводу: пользовательский UI/IA/assets не меняются, ссылка на референс не подменяет кодовую/приватностную приёмку. |

### Convergence findings и метрики

Текущий узкий срез: **6/6 требований,7/7 решений плана,7/7 принципов
оценены;20/20 пунктов рассмотрены,0 новых actionable gaps**.
По новым типам missing/partial/contradicts/unrequested:0/0/0/0;
по новым severity CRITICAL/HIGH/MEDIUM/LOW:0/0/0/0.
Результат: **scoped converged** для buildable реализации O15/S1–S6.
Это не заявление «вся F140/spec/T077 завершена».

| Сохранённый остаток | Тип/важность | Текущее доказательство | Учёт |
| --- | --- | --- | --- |
| O6/FR089 полное наблюдение и реакция | partial / HIGH | monitoring431 unknown_duration=null,337 reaction=null,410 reconciliation_gaps=null,452 ingress unavailable; требуемые полные показатели/регулярность/heartbeat/тревоги/сохраняемая реакция не приняты. Прямой O6 оригинал00833a сохраняет все сроки. | Исходная T077/#4932, tasks253 и314–323 остаются `[ ]`; новой задачи или дублирующей issue нет. |

Ничего не дописано в tasks.md: прежняя открытая T077 уже содержит этот
известный остаток, новых actionable работ локального среза нет. Контрольная
сумма tasks после сверки осталась
`a943ed0fd4e362e315681f418b19b1daefc5ef71ceb843b573606db3c71aaa98`.
Не добавлен пустой Convergence header. T070,58 прежних gaps и историческая
неприёмка O8 до PR7884 сохраняются отдельно. Before/after_converge hooks
отсутствуют; коммиты и taskstoissues не запускались.

## Проверенный окончательный снимок и передача

Повтор e74441:11/11 frozen inputs совпали; requirements checklist перечитан
и остался10 checked/0 unchecked. Текущий внешний manifest SHA-256
`ec81afee21a3f897a171d7c893763f8d2d90c13569a3162df09223b0bfe517d9`;
добавленные основным ссылки на runner/context не изменили11 inputs/runs.

| Файл | SHA-256 |
| --- | --- |
| specs/140-user-account-billing/spec.md | `b91ed5dbeb9a0d068bbc80df426da15efd96a6c5f4637ccd7839f20ddbb1bde2` |
| specs/140-user-account-billing/plan.md | `b4358e5bd276bca94d40aaabd5f60ec15cb69be916f5a2887b5fe66b0c92511f` |
| specs/140-user-account-billing/tasks.md | `a943ed0fd4e362e315681f418b19b1daefc5ef71ceb843b573606db3c71aaa98` |
| specs/140-user-account-billing/quickstart.md | `4df451d75bd010fce512a39fc91fdaabdcadae22da3db5d261d00ac2abbea3c2` |
| specs/140-user-account-billing/research.md | `f6465313da5c96ff0c0d8ed78f3cae471c9824e0148e4f23595cd2352a05ecd0` |
| specs/140-user-account-billing/data-model.md | `e245def932eb1b4c6ff8b6052980624cf52df0e694c643437469f6604aad5ecc` |
| specs/140-user-account-billing/contracts/operator-observation.md | `411f95d513457110e150cc0be2a665857a88d60aeaf721a71ba2063aa9d692a6` |
| apps/server/src/twobrain_rec_server/billing/monitoring.py | `a2d3423e537329b622234d5d127306eb36b473b31c475bc82d4d8f9760edfdfa` |
| apps/server/tests/unit/test_billing_monitoring.py | `e4ba5081df4d681d551d4d1a908232d648c51d1c3a7fa7d07b15a521fd1d4e8c` |
| apps/server/tests/integration/test_billing_monitoring_postgres.py | `1c750a0f1756d4dd3b74691ed13462d239644637099e2518e4eb9a6a6f86d4ce` |
| changes/unreleased/F140.yaml | `fa27b553fa37dbfa020acdfbf54e17940b2fff7f624e0e4bebc7115b711b886f` |

Следующий шаг основного — обязательные scoped repository checks и
точные governance-fast/macos-pr/pr-metadata на новом PR source SHA и
проверенной основе. Их успех этот независимый отчёт не предрешает.
Выпуск/развёртывание/Dev/реальные деньги/полное закрытие #4932 сюда не входят.
Изменён только этот отчёт; reviewer-owned checklist оставлен без изменения.

Последний контроль6fb64f:11 frozen files и четыре shared helper/CLI/guard
SHA неизменны; YAML разобран успешно. Requirements checklist перечитан
целиком f77726:10 отмечены/0 открыты, изменять его не потребовалось.
Итог отчёта — APPROVE code review и scoped converged6/7/7;
полный O6 сохраняется partial/HIGH в существующей T077 без нового дубля.
